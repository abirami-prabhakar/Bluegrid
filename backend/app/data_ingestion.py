"""
Step 1: Resource Data Ingestion

In production this module polls:
  - NIOT LiDAR wind feed
  - Global Solar Atlas (GSA) GHI API
  - NIOT ocean temperature profile service

Since we don't have live API credentials wired up in this environment,
this module generates physically-realistic SYNTHETIC hourly data seeded
from each island's real published resource profile (mean wind speed,
GHI, sea surface / deep sea temperature). The rest of the pipeline is
identical whether the DataFrame comes from here or a live feed — swap
this module out for the real API client without touching anything
downstream.
"""
import numpy as np
import pandas as pd

from .config import HOURS_PER_YEAR, ISLANDS


def _hour_of_year_arrays(hours: int = HOURS_PER_YEAR):
    t = np.arange(hours)
    day_of_year = (t // 24) % 365
    hour_of_day = t % 24
    return t, day_of_year, hour_of_day


def _monsoon_weight(day_of_year: np.ndarray) -> np.ndarray:
    """
    Returns 0..1 weight peaking during the June-Sept monsoon window
    (day ~152 to ~273), used to boost wind speed and cut solar GHI.
    """
    peak_day = 210.0
    width = 60.0
    return np.exp(-0.5 * ((day_of_year - peak_day) / width) ** 2)


def generate_hourly_resource_data(island_key: str, seed: int = 42) -> pd.DataFrame:
    """
    Produces an HOURS_PER_YEAR-row DataFrame with columns:
        hour_index, wind_speed_ms, ghi_wm2, sea_surface_temp_c,
        deep_sea_temp_c
    """
    if island_key not in ISLANDS:
        raise ValueError(f"Unknown island '{island_key}'. Options: {list(ISLANDS)}")

    island = ISLANDS[island_key]
    rng = np.random.default_rng(seed)
    t, day_of_year, hour_of_day = _hour_of_year_arrays()
    monsoon = _monsoon_weight(day_of_year)

    # --- Wind speed: base + monsoon boost + diurnal + noise ---
    diurnal_wind = 0.6 * np.sin((hour_of_day - 14) / 24 * 2 * np.pi)
    wind_speed = (
        island["mean_wind_speed_ms"]
        + island["monsoon_wind_boost_ms"] * monsoon
        + diurnal_wind
        + rng.normal(0, 0.8, size=len(t))
    )
    wind_speed = np.clip(wind_speed, 0, None)

    # --- GHI: strong diurnal (zero at night), cloud loss during monsoon ---
    daylight = np.clip(np.sin((hour_of_day - 6) / 12 * np.pi), 0, None)
    daylight[(hour_of_day < 6) | (hour_of_day > 18)] = 0.0
    peak_ghi_wm2 = island["mean_ghi_kwh_m2_day"] * 1000 / 6.0  # rough peak scaling
    cloud_factor = 1.0 - 0.55 * monsoon  # monsoon clouds cut GHI ~55% at peak
    ghi = peak_ghi_wm2 * daylight * cloud_factor
    ghi *= 1.0 + rng.normal(0, 0.05, size=len(t))
    ghi = np.clip(ghi, 0, None)

    # --- Ocean temperatures: fairly stable, slight seasonal drift ---
    seasonal_drift = 0.5 * np.sin((day_of_year / 365) * 2 * np.pi)
    sea_surface_temp = island["sea_surface_temp_c"] + seasonal_drift + rng.normal(0, 0.1, len(t))
    deep_sea_temp = island["deep_sea_temp_c"] + rng.normal(0, 0.05, len(t))

    return pd.DataFrame(
        {
            "hour_index": t,
            "wind_speed_ms": wind_speed,
            "ghi_wm2": ghi,
            "sea_surface_temp_c": sea_surface_temp,
            "deep_sea_temp_c": deep_sea_temp,
        }
    )
