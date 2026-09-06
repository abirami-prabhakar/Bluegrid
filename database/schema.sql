-- ============================================================================
-- BLUE GRID — PostgreSQL Production Database Schema
-- Event: Ocean Hackathon | Team: CODEQUADRANTS
-- Target System: Lakshadweep Island Multi-Energy Microgrid Planning
-- Database Name: bluegrid
-- ============================================================================

-- Table 1: Islands (Master Geographic & Oceanographic Resource Metadata)
CREATE TABLE IF NOT EXISTS islands (
    key VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    mean_wind_speed_ms DOUBLE PRECISION NOT NULL,
    monsoon_wind_boost_ms DOUBLE PRECISION NOT NULL,
    mean_ghi_kwh_m2_day DOUBLE PRECISION NOT NULL,
    sea_surface_temp_c DOUBLE PRECISION NOT NULL,
    deep_sea_temp_c DOUBLE PRECISION NOT NULL,
    params JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table 2: Scenarios (Simulation Execution Results & Financial Metrics)
CREATE TABLE IF NOT EXISTS scenarios (
    id SERIAL PRIMARY KEY,
    island_key VARCHAR(50) NOT NULL REFERENCES islands(key) ON DELETE CASCADE,
    scenario_name VARCHAR(150),
    solar_kw DOUBLE PRECISION NOT NULL,
    wind_kw DOUBLE PRECISION NOT NULL,
    otec_kw DOUBLE PRECISION NOT NULL,
    bess_kwh DOUBLE PRECISION NOT NULL,
    lolp_pct DOUBLE PRECISION NOT NULL,
    shortfall_hours INTEGER NOT NULL,
    capex DOUBLE PRECISION NOT NULL,
    annual_opex DOUBLE PRECISION NOT NULL,
    lcoe DOUBLE PRECISION NOT NULL,
    lcoe_lifetime DOUBLE PRECISION NOT NULL,
    co2_avoided DOUBLE PRECISION NOT NULL,
    diesel_subsidy_saved_inr DOUBLE PRECISION,
    result_json JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table 3: Hourly Ingestion Time Series (8,760 Hours per Island)
CREATE TABLE IF NOT EXISTS hourly_resource_timeseries (
    id BIGSERIAL PRIMARY KEY,
    island_key VARCHAR(50) NOT NULL REFERENCES islands(key) ON DELETE CASCADE,
    hour_index INTEGER NOT NULL,
    wind_speed_ms DOUBLE PRECISION NOT NULL,
    ghi_wm2 DOUBLE PRECISION NOT NULL,
    sea_surface_temp_c DOUBLE PRECISION NOT NULL,
    deep_sea_temp_c DOUBLE PRECISION NOT NULL,
    delta_t_c DOUBLE PRECISION GENERATED ALWAYS AS (sea_surface_temp_c - deep_sea_temp_c) STORED,
    CONSTRAINT uq_island_hour UNIQUE (island_key, hour_index)
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_scenarios_island ON scenarios(island_key);
CREATE INDEX IF NOT EXISTS idx_scenarios_lcoe ON scenarios(lcoe);
CREATE INDEX IF NOT EXISTS idx_scenarios_lolp ON scenarios(lolp_pct);
CREATE INDEX IF NOT EXISTS idx_hourly_timeseries ON hourly_resource_timeseries(island_key, hour_index);
