"""
Step 3: Energy Mix Optimization (PuLP linear program).

Decision variables: Solar, Wind, OTEC, BESS capacities plus hourly
dispatch (charge / discharge / SoC). Capacity factors are taken from the
same hourly generation and OTEC net-power models used in the 8,760-hour
simulator — the LP does not invent a different physics.

After CBC returns a mix, the mix is re-validated with the chronological
NumPy dispatch (LOLP on the true 8,760-hour trace).
"""
from typing import Dict
import pulp

from .config import (
    LOAD_KW,
    CAPEX_PER_KW,
    OPEX_PER_KWH,
    DISCOUNT_RATE,
    PROJECT_LIFESPAN_YEARS,
    BESS_SOC_MIN_FRACTION,
    BESS_CHARGE_EFFICIENCY,
    BESS_DISCHARGE_EFFICIENCY,
    BESS_C_RATE,
    OPTIMIZE_BOUNDS,
    HOURS_PER_YEAR,
)
from .data_ingestion import generate_hourly_resource_data
from .generation_model import solar_power_kw, wind_power_kw
from .otec_model import otec_net_output_kw
from .financial import capital_recovery_factor


def _unit_capacity_factors(island_key: str):
    resource = generate_hourly_resource_data(island_key)
    solar_cf = solar_power_kw(resource["ghi_wm2"].values, 1.0)
    wind_cf = wind_power_kw(resource["wind_speed_ms"].values, 1.0)
    otec_net, _, _ = otec_net_output_kw(
        1.0,
        resource["sea_surface_temp_c"].values,
        resource["deep_sea_temp_c"].values,
    )
    return solar_cf, wind_cf, otec_net


def optimize_capacity_mix_pulp(
    island_key: str,
    max_lolp_pct: float = 0.0,
    time_limit_s: int = 90,
    hour_stride: int = 1,
) -> Dict:
    """
    Chronological LP on hourly (or strided-hourly) steps.
    hour_stride=1 is a true 8,760-hour LP. Stride > 1 still walks the
    year in time order (not monthly averages) to keep CBC tractable.
    """
    solar_cf, wind_cf, otec_cf = _unit_capacity_factors(island_key)
    hours = list(range(0, HOURS_PER_YEAR, max(1, hour_stride)))
    n = len(hours)
    dt = float(hour_stride)  # SoC update in equivalent hours

    crf = capital_recovery_factor(DISCOUNT_RATE, PROJECT_LIFESPAN_YEARS)
    unmet_penalty = 1e5  # INR per unmet kWh — pushes LOLP toward 0

    prob = pulp.LpProblem("blue_grid_capacity_mix", pulp.LpMinimize)
    solar = pulp.LpVariable("solar_kw", *OPTIMIZE_BOUNDS["solar_kw"])
    wind = pulp.LpVariable("wind_kw", *OPTIMIZE_BOUNDS["wind_kw"])
    otec = pulp.LpVariable("otec_kw", *OPTIMIZE_BOUNDS["otec_kw"])
    bess = pulp.LpVariable("bess_kwh", *OPTIMIZE_BOUNDS["bess_kwh"])

    p_s = [pulp.LpVariable(f"ps_{t}", lowBound=0) for t in hours]
    p_w = [pulp.LpVariable(f"pw_{t}", lowBound=0) for t in hours]
    p_o = [pulp.LpVariable(f"po_{t}", lowBound=0) for t in hours]
    ch = [pulp.LpVariable(f"ch_{t}", lowBound=0) for t in hours]
    dis = [pulp.LpVariable(f"dis_{t}", lowBound=0) for t in hours]
    soc = [pulp.LpVariable(f"soc_{t}", lowBound=0) for t in hours]
    unmet = [pulp.LpVariable(f"un_{t}", lowBound=0) for t in hours]

    capex = (
        solar * CAPEX_PER_KW["solar"]
        + wind * CAPEX_PER_KW["wind"]
        + otec * CAPEX_PER_KW["otec"]
        + bess * CAPEX_PER_KW["bess"]
    )
    opex = pulp.lpSum(
        p_s[i] * dt * OPEX_PER_KWH["solar"]
        + p_w[i] * dt * OPEX_PER_KWH["wind"]
        + p_o[i] * dt * OPEX_PER_KWH["otec"]
        + (ch[i] + dis[i]) * dt * OPEX_PER_KWH["bess"]
        for i in range(n)
    )
    penalty = pulp.lpSum(unmet[i] * dt * unmet_penalty for i in range(n))
    prob += capex * crf + opex + penalty

    load = LOAD_KW
    for i, t in enumerate(hours):
        prob += p_s[i] <= solar * float(solar_cf[t])
        prob += p_w[i] <= wind * float(wind_cf[t])
        prob += p_o[i] <= otec * float(otec_cf[t])
        prob += p_s[i] + p_w[i] + p_o[i] + dis[i] + unmet[i] - ch[i] >= load
        prob += ch[i] <= bess * BESS_C_RATE
        prob += dis[i] <= bess * BESS_C_RATE
        prob += soc[i] <= bess
        prob += soc[i] >= BESS_SOC_MIN_FRACTION * bess
        if i == 0:
            prob += soc[i] == 0.5 * bess + ch[i] * dt * BESS_CHARGE_EFFICIENCY - dis[i] * dt / BESS_DISCHARGE_EFFICIENCY
        else:
            prob += soc[i] == soc[i - 1] + ch[i] * dt * BESS_CHARGE_EFFICIENCY - dis[i] * dt / BESS_DISCHARGE_EFFICIENCY

    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=time_limit_s, threads=4)
    status = prob.solve(solver)
    status_name = pulp.LpStatus.get(status, str(status))

    if solar.value() is None:
        return {
            "engine": "pulp_cbc",
            "status": status_name,
            "best": None,
            "note": "PuLP did not return a feasible mix. Try a higher LOLP allowance or wider bounds.",
        }

    mix = {
        "solar_kw": round(float(solar.value()), 1),
        "wind_kw": round(float(wind.value()), 1),
        "otec_kw": round(float(otec.value()), 1),
        "bess_kwh": round(float(bess.value()), 1),
    }
    from .scenario_engine import run_scenario

    validated = run_scenario(
        island_key, mix["solar_kw"], mix["wind_kw"], mix["otec_kw"], mix["bess_kwh"]
    )
    lp_unmet_hours = sum(1 for i in range(n) if (unmet[i].value() or 0) > 1e-6)

    best = {
        **mix,
        "lolp_pct": validated["lolp_pct"],
        "capex": validated["capex"],
        "lcoe": validated["lcoe"],
        "lcoe_lifetime": validated["lcoe_lifetime"],
        "co2_avoided": validated["co2_avoided_tons_per_year"],
        "lp_status": status_name,
        "lp_unmet_steps": lp_unmet_hours,
        "hour_stride": hour_stride,
        "max_lolp_pct_requested": max_lolp_pct,
    }
    return {
        "engine": "pulp_cbc",
        "status": status_name,
        "best": best,
        "feasible_count": 1 if validated["lolp_pct"] <= max(max_lolp_pct, 1e-9) or validated["lolp_pct"] == 0 else 0,
        "evaluated_count": 1,
        "top_candidates": [best],
        "validated": {
            k: v for k, v in validated.items() if k != "hourly"
        },
    }


def optimize_capacity_mix(
    island_key: str,
    solar_range_kw=None,
    wind_range_kw=None,
    otec_range_kw=None,
    bess_range_kwh=None,
    max_lolp_pct: float = 0.5,
    top_n: int = 5,
) -> Dict:
    """
    Deck optimizer: PuLP chronological LP, then NumPy 8,760-hour validation.
    Grid-search ranges from the API are ignored for the solve (kept on the
    signature so existing clients do not break) and stored on the payload.
    """
    # Stride 3 keeps a full-year chronological trace (~2920 steps) solvable
    # by CBC in a live demo; validation is always the true 8760-hour loop.
    result = optimize_capacity_mix_pulp(
        island_key, max_lolp_pct=max_lolp_pct, hour_stride=3
    )
    result["requested_ranges"] = {
        "solar_range_kw": solar_range_kw,
        "wind_range_kw": wind_range_kw,
        "otec_range_kw": otec_range_kw,
        "bess_range_kwh": bess_range_kwh,
        "top_n": top_n,
    }
    return result
