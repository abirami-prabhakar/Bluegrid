"""
Step 2: Renewable Generation Model

Converts raw resource data (wind speed, GHI) into hourly generation
(kW) for a given installed capacity, using standard technology power
curves / capacity-factor relationships.
"""
import numpy as np
import pandas as pd


def wind_power_kw(wind_speed_ms: np.ndarray, capacity_kw: float) -> np.ndarray:
    """
    Simplified turbine power curve:
      - cut-in at 3 m/s
      - rated power reached at 11 m/s
      - cut-out (safety shutdown) at 25 m/s
      - cubic ramp between cut-in and rated speed (P proportional to v^3)
    """
    cut_in, rated, cut_out = 3.0, 11.0, 25.0
    v = np.asarray(wind_speed_ms, dtype=float)
    power = np.zeros_like(v)

    ramp_mask = (v >= cut_in) & (v < rated)
    power[ramp_mask] = capacity_kw * ((v[ramp_mask] - cut_in) / (rated - cut_in)) ** 3

    rated_mask = (v >= rated) & (v <= cut_out)
    power[rated_mask] = capacity_kw

    # above cut_out -> 0 (already zero by default)
    return np.clip(power, 0, capacity_kw)


def solar_power_kw(ghi_wm2: np.ndarray, capacity_kw: float,
                    panel_efficiency: float = 0.20,
                    reference_irradiance_wm2: float = 1000.0) -> np.ndarray:
    """
    Standard PV yield model: output scales linearly with GHI relative
    to standard test condition irradiance (1000 W/m^2), scaled by
    installed nameplate capacity and panel efficiency de-rate.
    """
    ghi = np.asarray(ghi_wm2, dtype=float)
    output = capacity_kw * (ghi / reference_irradiance_wm2) * (panel_efficiency / 0.20)
    return np.clip(output, 0, capacity_kw)


def capacity_factor(power_kw: np.ndarray, capacity_kw: float) -> np.ndarray:
    if capacity_kw <= 0:
        return np.zeros_like(power_kw)
    return np.clip(power_kw / capacity_kw, 0, 1)


def apply_pv_degradation(power_kw: np.ndarray, degradation_multiplier: float) -> np.ndarray:
    """Apply a single year's PV degradation multiplier (0-1) to solar output."""
    return power_kw * degradation_multiplier


def build_generation_dataframe(
    resource_df: pd.DataFrame,
    solar_capacity_kw: float,
    wind_capacity_kw: float,
    pv_degradation_multiplier: float = 1.0,
) -> pd.DataFrame:
    df = resource_df.copy()
    df["solar_gen_kw"] = apply_pv_degradation(
        solar_power_kw(df["ghi_wm2"].values, solar_capacity_kw),
        pv_degradation_multiplier,
    )
    df["wind_gen_kw"] = wind_power_kw(df["wind_speed_ms"].values, wind_capacity_kw)
    return df
