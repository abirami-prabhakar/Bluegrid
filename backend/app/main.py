"""
Blue Grid — FastAPI simulation engine (called by the Express gateway).

Endpoints:
  GET  /api/islands
  POST /api/scenarios/simulate
  GET  /api/scenarios/hourly
  POST /api/scenarios/optimize
  POST /api/scenarios/rank
  GET  /api/data/live-status
  GET  /api/meta
"""
from typing import List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from .config import (
    ISLANDS,
    LOAD_KW,
    PIPELINE_STEPS,
    IMPACT_BENEFITS,
    SDG_TAGS,
    RESEARCH_REFERENCES,
)
from .scenario_engine import (
    run_scenario,
    hourly_records_for_api,
    comparison_topsis,
)
from .optimizer import optimize_capacity_mix
from .topsis import rank_scenarios
from .reporting import build_pdf_report, build_csv_report

app = FastAPI(title="Blue Grid Engine", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_LAST_RESULT_CACHE = {}


class ScenarioRequest(BaseModel):
    island: str = "kadmat"
    solar_kw: float = 2400
    wind_kw: float = 1200
    otec_kw: float = 400
    bess_kwh: float = 8000
    degradation_year: int = 1


class OptimizeRequest(BaseModel):
    island: str = "kadmat"
    solar_range_kw: List[float] = [500, 1000, 1500, 2000, 2500, 3000]
    wind_range_kw: List[float] = [200, 600, 1000, 1400, 1800]
    otec_range_kw: List[float] = [0, 200, 400, 600]
    bess_range_kwh: List[float] = [2000, 4000, 6000, 8000, 10000, 12000]
    max_lolp_pct: float = 0.5


class RankRequest(BaseModel):
    scenarios: List[ScenarioRequest]


def _public_result(result: dict) -> dict:
    _LAST_RESULT_CACHE[result["island"]] = result
    return {k: v for k, v in result.items() if k != "hourly"}


@app.get("/api/meta")
def meta():
    return {
        "name": "Blue Grid",
        "event": "Ocean Hackathon",
        "team": "CODEQUADRANTS",
        "pipeline_steps": PIPELINE_STEPS,
        "impact_benefits": IMPACT_BENEFITS,
        "sdg_tags": SDG_TAGS,
        "references": RESEARCH_REFERENCES,
        "load_kw": LOAD_KW,
        "data_mode": "synthetic_niot_gsa_shaped",
    }


@app.get("/api/islands")
def get_islands():
    return {"islands": ISLANDS, "load_kw": LOAD_KW}


@app.post("/api/scenarios/simulate")
def simulate(req: ScenarioRequest):
    result = run_scenario(
        req.island,
        req.solar_kw,
        req.wind_kw,
        req.otec_kw,
        req.bess_kwh,
        degradation_year=req.degradation_year,
    )
    return _public_result(result)


@app.get("/api/scenarios/hourly")
def get_hourly(island: str = "kadmat", limit_hours: Optional[int] = 168):
    result = _LAST_RESULT_CACHE.get(island)
    if result is None:
        result = run_scenario(island, 2400, 1200, 400, 8000)
        _LAST_RESULT_CACHE[island] = result
    return {
        "records": hourly_records_for_api(result["hourly"], limit_hours),
        "representative_24h": result.get("representative_24h", []),
        "monsoon_stress_24h": result.get("monsoon_stress_24h", []),
    }


@app.post("/api/scenarios/optimize")
def optimize(req: OptimizeRequest):
    return optimize_capacity_mix(
        req.island,
        req.solar_range_kw,
        req.wind_range_kw,
        req.otec_range_kw,
        req.bess_range_kwh,
        req.max_lolp_pct,
    )


@app.get("/api/scenarios/topsis")
def topsis_last(island: str = "kadmat"):
    result = _LAST_RESULT_CACHE.get(island)
    if result is None:
        result = run_scenario(island, 2400, 1200, 400, 8000)
        _LAST_RESULT_CACHE[island] = result
    ranked = comparison_topsis(result)
    result["topsis_ranking"] = ranked
    return {"ranked": ranked}


@app.post("/api/scenarios/rank")
def rank(req: RankRequest):
    scenarios = []
    for s in req.scenarios:
        result = run_scenario(s.island, s.solar_kw, s.wind_kw, s.otec_kw, s.bess_kwh)
        scenarios.append(
            {
                "label": f"{s.island}-S{s.solar_kw}-W{s.wind_kw}-O{s.otec_kw}-B{s.bess_kwh}",
                "lcoe": result["lcoe"],
                "capex": result["capex"],
                "lolp": result["lolp_pct"],
                "co2_avoided": result["co2_avoided_tons_per_year"],
            }
        )
    return {"ranked": rank_scenarios(scenarios)}


@app.get("/api/data/live-status")
def live_status():
    return {
        "wind_feed": {"source": "synthetic_niot_lidar_shaped", "live": False},
        "solar_feed": {"source": "synthetic_gsa_ghi_shaped", "live": False},
        "ocean_temp_feed": {"source": "synthetic_niot_otec_profile", "live": False},
        "note": "Live NIOT LiDAR / Global Solar Atlas credentials are not configured. "
                "Hourly series are physically shaped from published island resource "
                "profiles (wind, GHI, 28°C-class surface / deep-sea ΔT) and remain "
                "drop-in replaceable with live APIs.",
    }


@app.get("/api/scenarios/export/pdf")
def export_pdf(island: str = "kadmat"):
    result = _LAST_RESULT_CACHE.get(island)
    if result is None:
        result = run_scenario(island, 2400, 1200, 400, 8000)
        _LAST_RESULT_CACHE[island] = result
    pdf_bytes = build_pdf_report(result)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=bluegrid_{island}_report.pdf"},
    )


@app.get("/api/scenarios/export/csv")
def export_csv(island: str = "kadmat"):
    result = _LAST_RESULT_CACHE.get(island)
    if result is None:
        result = run_scenario(island, 2400, 1200, 400, 8000)
        _LAST_RESULT_CACHE[island] = result
    csv_text = build_csv_report(result)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=bluegrid_{island}_report.csv"},
    )


@app.get("/")
def root():
    return {"status": "Blue Grid engine running", "docs": "/docs"}
