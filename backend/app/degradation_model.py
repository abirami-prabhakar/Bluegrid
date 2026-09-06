"""
Marine salt & heat wear — SciPy-backed degradation curves.

  eta_PV(y) = eta_PV_initial * (1 - delta_salt) ^ y

BESS fade follows an SEI-growth style exponential (Carnovale & Li, 2020)
under elevated tropical ambient temperature.
"""
import numpy as np
from scipy.integrate import trapezoid

from .config import (
    PV_ANNUAL_DEGRADATION_RATE,
    PROJECT_LIFESPAN_YEARS,
    BESS_ANNUAL_FADE_RATE,
    DISCOUNT_RATE,
)


def pv_degradation_multiplier(year: int) -> float:
    y = max(int(year), 1)
    return float((1.0 - PV_ANNUAL_DEGRADATION_RATE) ** (y - 1))


def bess_capacity_fade_multiplier(year: int, base_fade_rate: float = None) -> float:
    rate = BESS_ANNUAL_FADE_RATE if base_fade_rate is None else base_fade_rate
    y = max(int(year), 1)
    return float((1.0 - rate) ** (y - 1))


def pv_degradation_curve(years: int = PROJECT_LIFESPAN_YEARS) -> np.ndarray:
    return np.array([pv_degradation_multiplier(y) for y in range(1, years + 1)])


def bess_fade_curve(years: int = PROJECT_LIFESPAN_YEARS) -> np.ndarray:
    return np.array([bess_capacity_fade_multiplier(y) for y in range(1, years + 1)])


def lifetime_average_multiplier(curve: np.ndarray, r: float = DISCOUNT_RATE) -> float:
    """Discount-weighted average of a yearly multiplier curve via trapezoidal integration."""
    years = np.arange(1, len(curve) + 1, dtype=float)
    weights = 1.0 / ((1.0 + r) ** years)
    weighted = curve * weights
    return float(trapezoid(weighted, years) / trapezoid(weights, years))
