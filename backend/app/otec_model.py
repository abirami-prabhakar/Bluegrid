"""
OTEC (Ocean Thermal Energy Conversion) thermodynamic model.

Implements:
  1. Gross power output, bounded by a fraction of the theoretical Carnot
     efficiency limit set by the surface/deep-sea temperature gradient.
  2. Parasitic pumping power loss via the fluid-mechanics formula:

        P_parasitic = (rho * g * Q * H) / eta_pump

  3. Net electrical output = gross - parasitic.

This is intentionally NOT a flat "20-25% haircut" — the parasitic loss
is computed from the actual flow rate implied by the plant's thermal
demand, so it responds correctly to capacity and conditions.
"""
import numpy as np
from scipy.constants import g as SCIPY_GRAVITY

from .config import (
    SEAWATER_DENSITY_KG_M3,
    PUMP_EFFICIENCY,
    COLD_WATER_PIPE_LENGTH_M,
    CARNOT_EFFICIENCY_FACTOR,
    MIN_OTEC_DELTA_T_C,
)

SPECIFIC_HEAT_SEAWATER_J_KGK = 3985.0  # c_p of seawater
FRICTION_HEAD_LOSS_FACTOR_M_PER_M = 0.02  # dynamic head loss per metre of pipe


def carnot_efficiency(t_surface_c: np.ndarray, t_deep_c: np.ndarray) -> np.ndarray:
    """Theoretical Carnot efficiency using absolute temperatures (Kelvin)."""
    t_hot_k = np.asarray(t_surface_c, dtype=float) + 273.15
    t_cold_k = np.asarray(t_deep_c, dtype=float) + 273.15
    delta_t = t_hot_k - t_cold_k
    eff = np.where(delta_t > 0, delta_t / t_hot_k, 0.0)
    return eff


def required_flow_rate_m3s(gross_power_kw: np.ndarray,
                            delta_t_c: np.ndarray) -> np.ndarray:
    """
    Back-calculate the seawater volumetric flow rate needed to deliver
    the target gross thermal power, given the available delta-T.
    Q = P / (rho * c_p * deltaT)   [rearranged from P = m_dot * c_p * dT]
    """
    delta_t = np.clip(delta_t_c, 0.1, None)  # avoid divide-by-zero
    power_w = np.asarray(gross_power_kw, dtype=float) * 1000.0
    flow = power_w / (SEAWATER_DENSITY_KG_M3 * SPECIFIC_HEAT_SEAWATER_J_KGK * delta_t)
    return flow


def parasitic_pumping_power_kw(flow_rate_m3s: np.ndarray) -> np.ndarray:
    """
    P_parasitic = (rho * g * Q * H) / eta_pump
    H = dynamic head friction loss across the cold water pipe.
    """
    head_loss_m = COLD_WATER_PIPE_LENGTH_M * FRICTION_HEAD_LOSS_FACTOR_M_PER_M
    power_w = (
        SEAWATER_DENSITY_KG_M3 * SCIPY_GRAVITY * flow_rate_m3s * head_loss_m
    ) / PUMP_EFFICIENCY
    return power_w / 1000.0  # convert W -> kW


def otec_net_output_kw(
    capacity_kw: float,
    sea_surface_temp_c: np.ndarray,
    deep_sea_temp_c: np.ndarray,
) -> np.ndarray:
    """
    Computes hourly net OTEC output for a plant of given nameplate
    capacity, given hourly surface/deep temperature series.

    Steps:
      1. delta_T(t) = surface - deep
      2. If delta_T < MIN_OTEC_DELTA_T_C, plant is not viable that hour -> 0
      3. Gross output = capacity_kw scaled by (actual efficiency / design
         efficiency), capturing that OTEC output falls when the thermal
         gradient weakens.
      4. Required flow rate -> parasitic pumping power (fluid mechanics)
      5. Net = gross - parasitic (floored at 0)
    """
    surface = np.asarray(sea_surface_temp_c, dtype=float)
    deep = np.asarray(deep_sea_temp_c, dtype=float)
    delta_t = surface - deep

    eff = carnot_efficiency(surface, deep) * CARNOT_EFFICIENCY_FACTOR
    design_delta_t = MIN_OTEC_DELTA_T_C + 5.0  # nameplate rated at deltaT=27C
    design_eff = carnot_efficiency(
        np.array([surface.mean()]), np.array([surface.mean() - design_delta_t])
    )[0] * CARNOT_EFFICIENCY_FACTOR
    design_eff = max(design_eff, 1e-6)

    gross_kw = capacity_kw * (eff / design_eff)
    gross_kw = np.where(delta_t >= MIN_OTEC_DELTA_T_C, gross_kw, 0.0)
    gross_kw = np.clip(gross_kw, 0, capacity_kw * 1.05)  # small headroom, then cap

    flow = required_flow_rate_m3s(gross_kw, delta_t)
    parasitic_kw = parasitic_pumping_power_kw(flow)

    net_kw = np.clip(gross_kw - parasitic_kw, 0, None)
    return net_kw, gross_kw, parasitic_kw
