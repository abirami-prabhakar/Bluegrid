const { Pool } = require("pg");

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 5,
  connectionTimeoutMillis: 3000,
});
pool.on("error", () => {});

async function initDb() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS islands (
      key TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      latitude DOUBLE PRECISION,
      longitude DOUBLE PRECISION,
      mean_wind_speed_ms DOUBLE PRECISION,
      monsoon_wind_boost_ms DOUBLE PRECISION,
      mean_ghi_kwh_m2_day DOUBLE PRECISION,
      sea_surface_temp_c DOUBLE PRECISION,
      deep_sea_temp_c DOUBLE PRECISION,
      params JSONB
    );
    CREATE TABLE IF NOT EXISTS scenarios (
      id SERIAL PRIMARY KEY,
      island_key TEXT NOT NULL,
      solar_kw DOUBLE PRECISION,
      wind_kw DOUBLE PRECISION,
      otec_kw DOUBLE PRECISION,
      bess_kwh DOUBLE PRECISION,
      lolp_pct DOUBLE PRECISION,
      shortfall_hours INTEGER,
      capex DOUBLE PRECISION,
      annual_opex DOUBLE PRECISION,
      lcoe DOUBLE PRECISION,
      lcoe_lifetime DOUBLE PRECISION,
      co2_avoided DOUBLE PRECISION,
      result_json JSONB,
      created_at TIMESTAMPTZ DEFAULT NOW()
    );
  `);
}

async function upsertIslands(islands) {
  for (const [key, row] of Object.entries(islands)) {
    await pool.query(
      `INSERT INTO islands (key, name, latitude, longitude, mean_wind_speed_ms,
        monsoon_wind_boost_ms, mean_ghi_kwh_m2_day, sea_surface_temp_c,
        deep_sea_temp_c, params)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
       ON CONFLICT (key) DO UPDATE SET
         name = EXCLUDED.name,
         latitude = EXCLUDED.latitude,
         longitude = EXCLUDED.longitude,
         mean_wind_speed_ms = EXCLUDED.mean_wind_speed_ms,
         monsoon_wind_boost_ms = EXCLUDED.monsoon_wind_boost_ms,
         mean_ghi_kwh_m2_day = EXCLUDED.mean_ghi_kwh_m2_day,
         sea_surface_temp_c = EXCLUDED.sea_surface_temp_c,
         deep_sea_temp_c = EXCLUDED.deep_sea_temp_c,
         params = EXCLUDED.params`,
      [
        key,
        row.name,
        row.latitude,
        row.longitude,
        row.mean_wind_speed_ms,
        row.monsoon_wind_boost_ms,
        row.mean_ghi_kwh_m2_day,
        row.sea_surface_temp_c,
        row.deep_sea_temp_c,
        JSON.stringify(row),
      ]
    );
  }
}

async function saveScenario(result) {
  const inp = result.inputs || {};
  const res = await pool.query(
    `INSERT INTO scenarios (
        island_key, solar_kw, wind_kw, otec_kw, bess_kwh, lolp_pct,
        shortfall_hours, capex, annual_opex, lcoe, lcoe_lifetime, co2_avoided, result_json
      ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
      RETURNING id`,
    [
      result.island,
      inp.solar_kw,
      inp.wind_kw,
      inp.otec_kw,
      inp.bess_kwh,
      result.lolp_pct,
      result.shortfall_hours,
      result.capex,
      result.annual_opex,
      result.lcoe,
      result.lcoe_lifetime,
      result.co2_avoided_tons_per_year,
      JSON.stringify(result),
    ]
  );
  return res.rows[0];
}

async function listScenarios(limit = 20) {
  const res = await pool.query(
    `SELECT id, island_key, solar_kw, wind_kw, otec_kw, bess_kwh,
            lolp_pct, capex, lcoe, co2_avoided, created_at
     FROM scenarios ORDER BY id DESC LIMIT $1`,
    [limit]
  );
  return res.rows;
}

module.exports = { pool, initDb, upsertIslands, saveScenario, listScenarios };
