require("dotenv").config({ path: require("path").resolve(__dirname, "../../.env") });
require("dotenv").config();

const express = require("express");
const cors = require("cors");
const db = require("./db");
const redis = require("./redis");

const FASTAPI = process.env.FASTAPI_URL || "http://127.0.0.1:8500";
const PORT = Number(process.env.GATEWAY_PORT || 3001);

const app = express();
app.use(cors({ origin: true }));
app.use(express.json({ limit: "8mb" }));

async function engine(path, options = {}) {
  const res = await fetch(`${FASTAPI}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  return res;
}

function asyncHandler(fn) {
  return (req, res) => fn(req, res).catch((err) => {
    console.error(err);
    res.status(502).json({
      error: "Gateway error",
      detail: err.message,
      hint: "Is FastAPI running on port 8500? Postgres/Redis via docker compose?",
    });
  });
}

app.get("/api/health", asyncHandler(async (_req, res) => {
  const health = { gateway: "ok", engine: false, postgres: false, redis: false };
  try {
    const r = await engine("/");
    health.engine = r.ok;
  } catch (_) {}
  try {
    await db.pool.query("SELECT 1");
    health.postgres = true;
  } catch (_) {}
  try {
    await redis.getRedis();
    health.redis = true;
  } catch (_) {}
  res.json(health);
}));

app.get("/api/meta", asyncHandler(async (_req, res) => {
  const r = await engine("/api/meta");
  res.status(r.status).json(await r.json());
}));

app.get("/api/islands", asyncHandler(async (_req, res) => {
  const cached = await redis.cacheGet("islands").catch(() => null);
  if (cached) return res.json({ ...cached, cache: "redis" });
  const r = await engine("/api/islands");
  const body = await r.json();
  try {
    await db.upsertIslands(body.islands || {});
    await redis.cacheSet("islands", body, 600);
  } catch (e) {
    console.warn("Island persist skipped:", e.message);
  }
  res.status(r.status).json(body);
}));

app.get("/api/data/live-status", asyncHandler(async (_req, res) => {
  const r = await engine("/api/data/live-status");
  res.status(r.status).json(await r.json());
}));

app.post("/api/scenarios/simulate", asyncHandler(async (req, res) => {
  const key = `sim:${JSON.stringify(req.body)}`;
  const cached = await redis.cacheGet(key).catch(() => null);
  if (cached) return res.json({ ...cached, cache: "redis" });

  const r = await engine("/api/scenarios/simulate", {
    method: "POST",
    body: JSON.stringify(req.body),
  });
  const body = await r.json();
  try {
    await redis.cacheSet(key, body, 1800);
    await redis.cacheSet(`last:${req.body.island || "kadmat"}`, body, 3600);
    const row = await db.saveScenario(body);
    body.scenario_id = row.id;
  } catch (e) {
    console.warn("Persist skipped:", e.message);
  }
  res.status(r.status).json(body);
}));

app.get("/api/scenarios/hourly", asyncHandler(async (req, res) => {
  const island = req.query.island || "kadmat";
  const limit = req.query.limit_hours || 168;
  const r = await engine(`/api/scenarios/hourly?island=${island}&limit_hours=${limit}`);
  res.status(r.status).json(await r.json());
}));

app.post("/api/scenarios/optimize", asyncHandler(async (req, res) => {
  const r = await engine("/api/scenarios/optimize", {
    method: "POST",
    body: JSON.stringify(req.body || {}),
    signal: AbortSignal.timeout(120000),
  });
  res.status(r.status).json(await r.json());
}));

app.get("/api/scenarios/topsis", asyncHandler(async (req, res) => {
  const island = req.query.island || "kadmat";
  const r = await engine(`/api/scenarios/topsis?island=${island}`);
  res.status(r.status).json(await r.json());
}));

app.post("/api/scenarios/rank", asyncHandler(async (req, res) => {
  const r = await engine("/api/scenarios/rank", {
    method: "POST",
    body: JSON.stringify(req.body),
  });
  res.status(r.status).json(await r.json());
}));

app.get("/api/scenarios/history", asyncHandler(async (_req, res) => {
  try {
    res.json({ scenarios: await db.listScenarios() });
  } catch (e) {
    res.json({ scenarios: [], note: e.message });
  }
}));

app.get("/api/scenarios/export/:kind", asyncHandler(async (req, res) => {
  const island = req.query.island || "kadmat";
  const kind = req.params.kind === "csv" ? "csv" : "pdf";
  const r = await engine(`/api/scenarios/export/${kind}?island=${island}`);
  const buf = Buffer.from(await r.arrayBuffer());
  res.setHeader("Content-Type", kind === "csv" ? "text/csv" : "application/pdf");
  res.setHeader(
    "Content-Disposition",
    `attachment; filename=bluegrid_${island}_report.${kind}`
  );
  res.send(buf);
}));

async function boot() {
  try {
    await db.initDb();
    console.log("Postgres schema ready");
  } catch (e) {
    console.warn("Postgres unavailable — gateway will still proxy FastAPI:", e.message);
  }
  try {
    await redis.getRedis();
    console.log("Redis connected");
  } catch (e) {
    console.warn("Redis unavailable — responses will not be cached:", e.message);
  }
  app.listen(PORT, () => {
    console.log(`Blue Grid gateway on http://127.0.0.1:${PORT}`);
  });
}

boot();
