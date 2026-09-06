const { createClient } = require("redis");

let client = null;
let redisUnavailable = false;

async function getRedis() {
  if (redisUnavailable) throw new Error("Redis unavailable");
  if (client && client.isOpen) return client;
  client = createClient({
    url: process.env.REDIS_URL || "redis://127.0.0.1:6379",
    socket: { connectTimeout: 2000, reconnectStrategy: false },
  });
  client.on("error", () => {}); // suppress per-event noise
  try {
    await client.connect();
  } catch (err) {
    redisUnavailable = true;
    client = null;
    throw new Error("Redis unavailable");
  }
  return client;
}

async function cacheSet(key, value, ttlSec = 3600) {
  try {
    const r = await getRedis();
    await r.set(key, JSON.stringify(value), { EX: ttlSec });
  } catch (_) {
    // Redis offline — skip cache write silently
  }
}

async function cacheGet(key) {
  try {
    const r = await getRedis();
    const raw = await r.get(key);
    return raw ? JSON.parse(raw) : null;
  } catch (_) {
    return null;
  }
}

module.exports = { getRedis, cacheSet, cacheGet };
