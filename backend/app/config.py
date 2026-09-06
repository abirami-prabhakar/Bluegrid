"""
Blue Grid — Central configuration for all physical, financial, and
algorithmic constants used across the simulation engines.

Keeping every constant here (instead of scattered through the codebase)
means judges/reviewers can inspect every assumption in one place, and
it's the single place to tune the model.
"""

HOURS_PER_YEAR = 8760
PROJECT_LIFESPAN_YEARS = 20
LOAD_KW = 1000.0  # Fixed 1 MW AC continuous demand

# ---------------------------------------------------------------------------
# OTEC (Ocean Thermal Energy Conversion) — thermodynamics & pumping
# ---------------------------------------------------------------------------
SEAWATER_DENSITY_KG_M3 = 1028.0       # rho
GRAVITY_M_S2 = 9.81                   # g
PUMP_EFFICIENCY = 0.82                # eta_pump (0.80–0.85 range)
COLD_WATER_PIPE_LENGTH_M = 1000.0     # depth of cold water intake
CARNOT_EFFICIENCY_FACTOR = 0.55       # fraction of Carnot limit OTEC plants
                                       # typically achieve (realistic OTEC
                                       # is nowhere near ideal Carnot)
MIN_OTEC_DELTA_T_C = 22.0             # OTEC requires deltaT >= 22C to be viable

# ---------------------------------------------------------------------------
# Marine degradation (salt spray + tropical heat wear)
# ---------------------------------------------------------------------------
PV_ANNUAL_DEGRADATION_RATE = 0.015    # delta_salt, 1.5%/year

# ---------------------------------------------------------------------------
# BESS (Battery Energy Storage System)
# ---------------------------------------------------------------------------
BESS_SOC_MIN_FRACTION = 0.20          # 20% floor
BESS_SOC_MAX_FRACTION = 1.00          # 100% ceiling
BESS_CHARGE_EFFICIENCY = 0.922        # eta_charge  (sqrt of 0.85 RTE)
BESS_DISCHARGE_EFFICIENCY = 0.922     # eta_discharge
BESS_ROUND_TRIP_EFFICIENCY = BESS_CHARGE_EFFICIENCY * BESS_DISCHARGE_EFFICIENCY
BESS_C_RATE = 0.5                    # max charge/discharge power = C-rate * energy
BESS_ANNUAL_FADE_RATE = 0.02         # SEI-growth style tropical fade (Carnovale & Li)

# ---------------------------------------------------------------------------
# Financial — Levelized Cost of Energy / Capital Recovery Factor
# ---------------------------------------------------------------------------
DISCOUNT_RATE = 0.08                  # r
CAPEX_PER_KW = {
    "solar": 45000.0,   # INR/kW installed (floating solar, incl. mounts)
    "wind": 65000.0,    # INR/kW installed
    "otec": 350000.0,   # INR/kW installed (early-stage OTEC is capital heavy)
    "bess": 18000.0,    # INR/kWh installed
}
OPEX_PER_KWH = {
    "solar": 0.15,   # INR/kWh generated (O&M)
    "wind": 0.25,
    "otec": 0.60,
    "bess": 0.10,
}
CO2_AVOIDED_PER_KWH_DIESEL_KG = 0.82   # kg CO2 per kWh of diesel displaced
DIESEL_UTILITY_COST_INR_PER_KWH = 22.5  # govt landed cost midpoint of ₹20–25/unit
DIESEL_SUBSIDIZED_TARIFF_INR_PER_KWH = 4.5  # sold at ₹3–6/unit

# Capacity bounds used by the PuLP mix optimizer (kW / kWh)
OPTIMIZE_BOUNDS = {
    "solar_kw": (0.0, 5000.0),
    "wind_kw": (0.0, 3000.0),
    "otec_kw": (0.0, 1000.0),
    "bess_kwh": (0.0, 16000.0),
}

RESEARCH_REFERENCES = [
    {
        "id": "pypsa",
        "text": "PyPSA (Brown, Hörsch & Schlachtberger, 2018) — open-source power system optimization toolbox",
        "url": "https://doi.org/10.5334/jors.188",
    },
    {
        "id": "topsis",
        "text": "TOPSIS (Hwang & Yoon, 1981) — MCDA ranking method",
        "url": None,
    },
    {
        "id": "otec-pipe",
        "text": "OTEC Cold-Water-Pipe Losses (Aresti et al., ICTAM 2024) — heat loss & parasitic pumping model",
        "url": "https://ktisis.cut.ac.cy/handle/20.500.14279/33492",
    },
    {
        "id": "bess-fade",
        "text": "Li-ion Capacity Fade at High Temp (Carnovale & Li, 2020) — SEI-growth driven battery degradation",
        "url": "https://doi.org/10.1016/j.egyai.2020.100032",
    },
    {
        "id": "niot-kavaratti",
        "text": "NIOT OTEC-Desalination Plant, Kavaratti — operational reference (29°C surface vs 5°C deep-sea)",
        "url": "https://www.drishtiias.com/daily-updates/daily-news-analysis/otec-plant-in-lakshadweep",
    },
]

PIPELINE_STEPS = [
    "Resource Data Ingestion",
    "Renewable Generation Model",
    "Energy Mix Optimization",
    "Battery Storage Simulation",
    "Load & Reliability Check",
    "Cost & Performance Analysis",
    "Interactive Planner & Recommendation",
]

IMPACT_BENEFITS = [
    {
        "action": "Eliminates Island Diesel Dependency",
        "domain": "Environmental",
        "detail": "Prevents CO2 emissions, eliminates marine fuel spill risk",
    },
    {
        "action": "Accurate Ocean Thermal Modeling",
        "domain": "Economic",
        "detail": "Saves crores in diesel subsidy & fuel transport logistics",
    },
    {
        "action": "Guarantees 24/7 Grid Reliability",
        "domain": "Social",
        "detail": "Uninterrupted power to homes, hospitals, schools, desalination plants",
    },
    {
        "action": "Optimizes Clean Energy Budgets",
        "domain": "Strategic",
        "detail": "Protects islands from monsoon fuel supply disruptions",
    },
]

SDG_TAGS = [
    "SDG 6 — Clean Water & Sanitation",
    "SDG 7 — Affordable & Clean Energy",
    "SDG 9 — Industry, Innovation & Infrastructure",
    "SDG 13 — Climate Action",
    "SDG 14 — Life Below Water",
]

# ---------------------------------------------------------------------------
# TOPSIS — Multi-Criteria Decision Analysis weights
# ---------------------------------------------------------------------------
# Metrics: LCOE (lower better), CAPEX (lower better), LOLP (lower better),
# CO2 avoided (higher better)
TOPSIS_WEIGHTS = {
    "lcoe": 0.35,
    "capex": 0.25,
    "lolp": 0.25,
    "co2_avoided": 0.15,
}
TOPSIS_BENEFIT_METRICS = {"co2_avoided"}   # higher is better
TOPSIS_COST_METRICS = {"lcoe", "capex", "lolp"}  # lower is better

# ---------------------------------------------------------------------------
# Islands — location + resource profile seeds (for synthetic data ingestion)
# ---------------------------------------------------------------------------
ISLANDS = {
    "kadmat": {
        "name": "Kadmat",
        "latitude": 11.23,
        "longitude": 72.78,
        "mean_wind_speed_ms": 6.5,
        "monsoon_wind_boost_ms": 2.0,
        "mean_ghi_kwh_m2_day": 5.2,
        "sea_surface_temp_c": 29.0,
        "deep_sea_temp_c": 7.0,
    },
    "kavaratti": {
        "name": "Kavaratti",
        "latitude": 10.57,
        "longitude": 72.64,
        "mean_wind_speed_ms": 6.2,
        "monsoon_wind_boost_ms": 2.2,
        "mean_ghi_kwh_m2_day": 5.3,
        "sea_surface_temp_c": 29.5,
        "deep_sea_temp_c": 6.5,
    },
    "minicoy": {
        "name": "Minicoy",
        "latitude": 8.28,
        "longitude": 73.04,
        "mean_wind_speed_ms": 7.0,
        "monsoon_wind_boost_ms": 2.5,
        "mean_ghi_kwh_m2_day": 5.1,
        "sea_surface_temp_c": 28.5,
        "deep_sea_temp_c": 7.5,
    },
}
