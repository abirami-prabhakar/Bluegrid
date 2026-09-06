"""
Step 6: Cost & Performance Analysis

  CRF = [r(1+r)^n] / [(1+r)^n - 1]
  Year-1 LCOE uses energy actually served (not assumed 100% load).
  20-year LCOE discounts year-by-year OPEX and degraded energy.
"""
from .config import (
    DISCOUNT_RATE,
    PROJECT_LIFESPAN_YEARS,
    CAPEX_PER_KW,
    OPEX_PER_KWH,
    CO2_AVOIDED_PER_KWH_DIESEL_KG,
    DIESEL_UTILITY_COST_INR_PER_KWH,
    DIESEL_SUBSIDIZED_TARIFF_INR_PER_KWH,
)
from .degradation_model import pv_degradation_curve, bess_fade_curve


def capital_recovery_factor(r: float = DISCOUNT_RATE, n: int = PROJECT_LIFESPAN_YEARS) -> float:
    return (r * (1 + r) ** n) / ((1 + r) ** n - 1)


def compute_capex(solar_kw: float, wind_kw: float, otec_kw: float, bess_kwh: float) -> float:
    return (
        solar_kw * CAPEX_PER_KW["solar"]
        + wind_kw * CAPEX_PER_KW["wind"]
        + otec_kw * CAPEX_PER_KW["otec"]
        + bess_kwh * CAPEX_PER_KW["bess"]
    )


def compute_annual_opex(
    solar_annual_kwh: float,
    wind_annual_kwh: float,
    otec_annual_kwh: float,
    bess_throughput_kwh: float,
) -> float:
    return (
        solar_annual_kwh * OPEX_PER_KWH["solar"]
        + wind_annual_kwh * OPEX_PER_KWH["wind"]
        + otec_annual_kwh * OPEX_PER_KWH["otec"]
        + bess_throughput_kwh * OPEX_PER_KWH["bess"]
    )


def compute_lcoe(
    capex: float,
    annual_opex: float,
    energy_served_kwh: float,
    r: float = DISCOUNT_RATE,
    n: int = PROJECT_LIFESPAN_YEARS,
) -> float:
    """LCOE from CRF using energy actually served in the simulated year."""
    served = max(float(energy_served_kwh), 1e-9)
    crf = capital_recovery_factor(r, n)
    return ((capex * crf) + annual_opex) / served


def compute_lifetime_lcoe(
    capex: float,
    year1_solar_kwh: float,
    year1_wind_kwh: float,
    year1_otec_kwh: float,
    year1_bess_throughput_kwh: float,
    year1_energy_served_kwh: float,
    r: float = DISCOUNT_RATE,
    n: int = PROJECT_LIFESPAN_YEARS,
) -> float:
    """
    NPV(costs) / NPV(energy) over n years.
    Solar kWh and BESS throughput follow SciPy degradation/fade curves;
    wind and OTEC held at year-1 (no equivalent fade model in the deck refs).
    Energy served is scaled by the BESS fade factor as a conservative reliability proxy.
    """
    pv = pv_degradation_curve(n)
    bess = bess_fade_curve(n)
    npv_cost = capex
    npv_energy = 0.0
    for i in range(n):
        disc = (1.0 + r) ** (i + 1)
        solar_y = year1_solar_kwh * float(pv[i])
        bess_y = year1_bess_throughput_kwh * float(bess[i])
        opex_y = compute_annual_opex(solar_y, year1_wind_kwh, year1_otec_kwh, bess_y)
        npv_cost += opex_y / disc
        served_y = year1_energy_served_kwh * (0.85 + 0.15 * float(bess[i]))
        npv_energy += served_y / disc
    return npv_cost / max(npv_energy, 1e-9)


def compute_co2_avoided_tons_per_year(diesel_displaced_kwh: float) -> float:
    return (diesel_displaced_kwh * CO2_AVOIDED_PER_KWH_DIESEL_KG) / 1000.0


def diesel_subsidy_inr_per_year(diesel_displaced_kwh: float) -> float:
    gap = DIESEL_UTILITY_COST_INR_PER_KWH - DIESEL_SUBSIDIZED_TARIFF_INR_PER_KWH
    return diesel_displaced_kwh * gap
