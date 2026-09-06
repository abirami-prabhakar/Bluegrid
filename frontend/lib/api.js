const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:3001";

async function json(res) {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getMeta() {
  return json(await fetch(`${API}/api/meta`));
}

export async function getIslands() {
  return json(await fetch(`${API}/api/islands`));
}

export async function getLiveStatus() {
  return json(await fetch(`${API}/api/data/live-status`));
}

export async function simulate(body) {
  return json(
    await fetch(`${API}/api/scenarios/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
  );
}

export async function getHourly(island, limitHours = 168) {
  return json(
    await fetch(`${API}/api/scenarios/hourly?island=${island}&limit_hours=${limitHours}`)
  );
}

export async function optimize(island) {
  return json(
    await fetch(`${API}/api/scenarios/optimize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ island, max_lolp_pct: 0.5 }),
    })
  );
}

export async function getTopsis(island) {
  return json(await fetch(`${API}/api/scenarios/topsis?island=${island}`));
}

export async function getHistory() {
  return json(await fetch(`${API}/api/scenarios/history`));
}

export function exportUrl(kind, island) {
  return `${API}/api/scenarios/export/${kind}?island=${island}`;
}

export { API };
