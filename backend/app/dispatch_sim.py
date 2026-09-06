"""
Step 4: Battery Storage Simulation
Step 5: Load & Reliability Check

Runs the full 8,760-hour chronological dispatch:
  - Renewables serve load first (Solar + Wind + OTEC)
  - Surplus charges the battery (respecting SoC bounds & charge efficiency)
  - Deficit is covered by battery discharge (respecting SoC bounds &
    discharge efficiency)
  - Any remaining shortfall is "unmet load" -> feeds directly into LOLP

SoC recurrence:
  SoC(t+1) = SoC(t) + (P_charge(t) * eta_charge) - (P_discharge(t) / eta_discharge)
Bounds:
  0.20 * C_BESS <= SoC(t) <= 1.00 * C_BESS

LOLP:
  LOLP = ( sum_t 1[P_available(t) < P_load(t)] / 8760 ) * 100%
"""
import numpy as np
import pandas as pd

from .config import (
    LOAD_KW,
    BESS_SOC_MIN_FRACTION,
    BESS_SOC_MAX_FRACTION,
    BESS_CHARGE_EFFICIENCY,
    BESS_DISCHARGE_EFFICIENCY,
    BESS_C_RATE,
    HOURS_PER_YEAR,
)


def simulate_dispatch(
    gen_df: pd.DataFrame,
    otec_net_kw: np.ndarray,
    bess_capacity_kwh: float,
    load_kw: float = LOAD_KW,
) -> pd.DataFrame:
    """
    gen_df must contain 'solar_gen_kw' and 'wind_gen_kw' columns aligned
    hour-by-hour with otec_net_kw.

    Returns a DataFrame with full hourly dispatch results including SoC,
    charge/discharge power, unmet load, and a boolean shortfall flag.
    """
    n = len(gen_df)
    assert n == len(otec_net_kw), "otec_net_kw length must match gen_df"

    soc_min = BESS_SOC_MIN_FRACTION * bess_capacity_kwh
    soc_max = BESS_SOC_MAX_FRACTION * bess_capacity_kwh
    max_power_kw = BESS_C_RATE * bess_capacity_kwh if bess_capacity_kwh > 0 else 0.0

    soc = np.zeros(n)
    charge_kw = np.zeros(n)
    discharge_kw = np.zeros(n)
    unmet_kw = np.zeros(n)
    available_kw = np.zeros(n)

    # Start battery half-full (a reasonable initial condition)
    current_soc = 0.5 * bess_capacity_kwh if bess_capacity_kwh > 0 else 0.0

    solar = gen_df["solar_gen_kw"].values
    wind = gen_df["wind_gen_kw"].values

    for t in range(n):
        renewable_supply = solar[t] + wind[t] + otec_net_kw[t]
        net = renewable_supply - load_kw  # positive = surplus, negative = deficit

        if net >= 0:
            # Surplus -> attempt to charge battery
            headroom_kwh = soc_max - current_soc
            # charging power limited by 1-hour timestep -> kWh == kW here
            charge_power = min(
                net,
                headroom_kwh / BESS_CHARGE_EFFICIENCY if bess_capacity_kwh > 0 else 0.0,
                max_power_kw,
            )
            charge_power = max(charge_power, 0.0)
            current_soc += charge_power * BESS_CHARGE_EFFICIENCY
            charge_kw[t] = charge_power
            available_kw[t] = load_kw  # fully served
        else:
            deficit = -net
            available_energy_kwh = max(current_soc - soc_min, 0.0)
            # how much can we discharge this hour, respecting efficiency & SoC floor
            max_discharge_power = available_energy_kwh * BESS_DISCHARGE_EFFICIENCY if bess_capacity_kwh > 0 else 0.0
            discharge_power = min(deficit, max_discharge_power, max_power_kw)
            discharge_power = max(discharge_power, 0.0)
            current_soc -= discharge_power / BESS_DISCHARGE_EFFICIENCY
            discharge_kw[t] = discharge_power
            served = renewable_supply + discharge_power
            available_kw[t] = served
            unmet_kw[t] = max(load_kw - served, 0.0)

        current_soc = np.clip(current_soc, soc_min if bess_capacity_kwh > 0 else 0.0, soc_max)
        soc[t] = current_soc

    result = gen_df.copy()
    result["otec_net_kw"] = otec_net_kw
    result["load_kw"] = load_kw
    result["bess_soc_kwh"] = soc
    result["bess_charge_kw"] = charge_kw
    result["bess_discharge_kw"] = discharge_kw
    result["available_kw"] = available_kw
    result["unmet_load_kw"] = unmet_kw
    result["shortfall"] = unmet_kw > 1e-6
    return result


def compute_lolp(dispatch_df: pd.DataFrame) -> float:
    """
    LOLP = (count of shortfall hours / 8760) * 100%
    Implemented as the exact indicator-function summation — no sampling.
    """
    n = len(dispatch_df)
    shortfall_hours = int(dispatch_df["shortfall"].sum())
    return (shortfall_hours / n) * 100.0, shortfall_hours
