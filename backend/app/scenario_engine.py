"""
Ties together Steps 1-6 of the pipeline into a single callable:
given an island + capacity mix, run the full 8,760-hour simulation and
return every metric needed by the frontend / report / TOPSIS ranking.
"""
from typing import Dict, Optional
import numpy as np

from .config import (
    LOAD_KW,
    IMPACT_BENEFITS,
    SDG_TAGS,
    RESEARCH_REFERENCES,
    PIPELINE_STEPS,
)
from .data_ingestion import generate_hourly_resource_data
from .generation_model import build_generation_dataframe
from .otec_model import otec_net_output_kw
from .dispatch_sim import simulate_dispatch, compute_lolp
from .degradation_model import (
    pv_degradation_multiplier as pv_fade,
    bess_capacity_fade_multiplier,
)
from .financial import (
    compute_capex,
    compute_annual_opex,
    compute_lcoe,
    compute_lifetime_lcoe,
    compute_co2_avoided_tons_per_year,
    diesel_subsidy_inr_per_year,
)
from .topsis import rank_scenarios


def run_scenario(
    island_key: str,
    solar_kw: float,
    wind_kw: float,
    otec_kw: float,
    bess_kwh: float,
    pv_multiplier: float = None,
    load_kw: float = LOAD_KW,
    degradation_year: int = 1,
) -> Dict:
    pv_mult = pv_fade(degradation_year) if pv_multiplier is None else pv_multiplier
    bess_mult = bess_capacity_fade_multiplier(degradation_year)
    effective_bess = bess_kwh * bess_mult

    # --- Step 1: Resource ingestion ---
    resource_df = generate_hourly_resource_data(island_key)

    # --- Step 2: Renewable generation model ---
    gen_df = build_generation_dataframe(
        resource_df, solar_kw, wind_kw, pv_mult
    )

    otec_net, otec_gross, otec_parasitic = otec_net_output_kw(
        otec_kw,
        gen_df["sea_surface_temp_c"].values,
        gen_df["deep_sea_temp_c"].values,
    )
    gen_df["otec_gross_kw"] = otec_gross
    gen_df["otec_parasitic_kw"] = otec_parasitic

    # --- Steps 4 & 5: BESS simulation + load/reliability check ---
    dispatch_df = simulate_dispatch(gen_df, otec_net, effective_bess, load_kw)
    lolp_pct, shortfall_hours = compute_lolp(dispatch_df)

    # --- Step 6: Cost & performance analysis ---
    solar_annual_kwh = float(dispatch_df["solar_gen_kw"].sum())
    wind_annual_kwh = float(dispatch_df["wind_gen_kw"].sum())
    otec_annual_kwh = float(dispatch_df["otec_net_kw"].sum())
    bess_throughput_kwh = float(
        dispatch_df["bess_charge_kw"].sum() + dispatch_df["bess_discharge_kw"].sum()
    )
    energy_served_kwh = float((dispatch_df["load_kw"] - dispatch_df["unmet_load_kw"]).sum())
    diesel_displaced_kwh = energy_served_kwh

    capex = compute_capex(solar_kw, wind_kw, otec_kw, bess_kwh)
    annual_opex = compute_annual_opex(
        solar_annual_kwh, wind_annual_kwh, otec_annual_kwh, bess_throughput_kwh
    )
    lcoe = compute_lcoe(capex, annual_opex, energy_served_kwh)
    lcoe_lifetime = compute_lifetime_lcoe(
        capex,
        solar_annual_kwh,
        wind_annual_kwh,
        otec_annual_kwh,
        bess_throughput_kwh,
        energy_served_kwh,
    )
    co2_avoided_tons = compute_co2_avoided_tons_per_year(diesel_displaced_kwh)

    return {
        "island": island_key,
        "pipeline_steps": PIPELINE_STEPS,
        "inputs": {
            "solar_kw": solar_kw,
            "wind_kw": wind_kw,
            "otec_kw": otec_kw,
            "bess_kwh": bess_kwh,
        },
        "degradation": {
            "year": degradation_year,
            "pv_multiplier": pv_mult,
            "bess_multiplier": bess_mult,
            "effective_bess_kwh": effective_bess,
        },
        "lolp_pct": lolp_pct,
        "shortfall_hours": shortfall_hours,
        "capex": capex,
        "annual_opex": annual_opex,
        "lcoe": lcoe,
        "lcoe_lifetime": lcoe_lifetime,
        "co2_avoided_tons_per_year": co2_avoided_tons,
        "diesel_subsidy_avoided_inr_per_year": diesel_subsidy_inr_per_year(diesel_displaced_kwh),
        "solar_annual_kwh": solar_annual_kwh,
        "wind_annual_kwh": wind_annual_kwh,
        "otec_annual_kwh": otec_annual_kwh,
        "energy_served_kwh": energy_served_kwh,
        "diesel_displaced_kwh": diesel_displaced_kwh,
        "otec_parasitic_mean_kw": float(np.mean(otec_parasitic)),
        "otec_gross_mean_kw": float(np.mean(otec_gross)),
        "representative_24h": _mean_representative_day(dispatch_df),
        "monsoon_stress_24h": _lowest_net_generation_day(dispatch_df),
        "impact_benefits": IMPACT_BENEFITS,
        "sdg_tags": SDG_TAGS,
        "references": RESEARCH_REFERENCES,
        "hourly": dispatch_df,
    }


def _mean_representative_day(dispatch_df) -> list:
    df = dispatch_df.copy()
    df["hour_of_day"] = df["hour_index"] % 24
    cols = [
        "solar_gen_kw", "wind_gen_kw", "otec_net_kw", "otec_gross_kw",
        "otec_parasitic_kw", "load_kw", "bess_soc_kwh", "unmet_load_kw",
    ]
    grouped = df.groupby("hour_of_day")[cols].mean().reset_index()
    grouped = grouped.rename(columns={"hour_of_day": "hour_index"})
    return grouped.to_dict(orient="records")


def _lowest_net_generation_day(dispatch_df) -> list:
    df = dispatch_df.copy()
    df["day"] = df["hour_index"] // 24
    daily = df.groupby("day")[["solar_gen_kw", "wind_gen_kw", "otec_net_kw"]].sum()
    daily["net"] = daily.sum(axis=1)
    worst = int(daily["net"].idxmin())
    slice_df = df[df["day"] == worst]
    cols = [
        "hour_index", "solar_gen_kw", "wind_gen_kw", "otec_net_kw",
        "otec_gross_kw", "otec_parasitic_kw", "bess_soc_kwh",
        "bess_charge_kw", "bess_discharge_kw", "available_kw",
        "unmet_load_kw", "load_kw",
    ]
    return slice_df[cols].to_dict(orient="records")


def hourly_records_for_api(dispatch_df, limit_hours: Optional[int] = None):
    """Convert hourly dataframe into a lightweight list of dicts for JSON."""
    df = dispatch_df if limit_hours is None else dispatch_df.head(limit_hours)
    cols = [
        "hour_index", "solar_gen_kw", "wind_gen_kw", "otec_net_kw",
        "otec_gross_kw", "otec_parasitic_kw",
        "bess_soc_kwh", "bess_charge_kw", "bess_discharge_kw",
        "available_kw", "unmet_load_kw", "load_kw",
    ]
    present = [c for c in cols if c in df.columns]
    return df[present].to_dict(orient="records")


def comparison_topsis(current: Dict) -> list:
    """Rank the current mix against three planner baselines (same island)."""
    island = current["island"]
    inp = current["inputs"]
    baselines = [
        ("current", inp["solar_kw"], inp["wind_kw"], inp["otec_kw"], inp["bess_kwh"]),
        ("deck_reference", 2400, 1200, 400, 8000),
        ("solar_bess", 3500, 0, 0, 12000),
        ("wind_otec_bess", 0, 1800, 600, 10000),
    ]
    scenarios = []
    for label, s, w, o, b in baselines:
        result = current if label == "current" else run_scenario(island, s, w, o, b)
        scenarios.append(
            {
                "label": label,
                "solar_kw": s,
                "wind_kw": w,
                "otec_kw": o,
                "bess_kwh": b,
                "lcoe": result["lcoe"],
                "capex": result["capex"],
                "lolp": result["lolp_pct"],
                "co2_avoided": result["co2_avoided_tons_per_year"],
            }
        )
    return rank_scenarios(scenarios)
