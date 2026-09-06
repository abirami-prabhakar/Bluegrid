"""
Step 3 (ranking support) — TOPSIS Multi-Criteria Decision Analysis

Implements true vector normalization + weighted Euclidean distance to
ideal-best / ideal-worst, NOT a simple weighted-sum score.

  r_ij = x_ij / sqrt(sum_k x_kj^2)
  v_ij = w_j * r_ij,  sum_j w_j = 1.0
  D_i+ = sqrt(sum_j (v_ij - v_j+)^2)
  D_i- = sqrt(sum_j (v_ij - v_j-)^2)
  C_i  = D_i- / (D_i+ + D_i-)
"""
from typing import List, Dict
import numpy as np

from .config import TOPSIS_WEIGHTS, TOPSIS_BENEFIT_METRICS, TOPSIS_COST_METRICS


def rank_scenarios(scenarios: List[Dict[str, float]]) -> List[Dict]:
    """
    scenarios: list of dicts, each with keys matching TOPSIS_WEIGHTS
               (lcoe, capex, lolp, co2_avoided) plus any metadata.
    Returns the same list, each dict augmented with 'topsis_score' and
    'rank' (1 = best), sorted best-first.
    """
    metrics = list(TOPSIS_WEIGHTS.keys())
    m = len(scenarios)
    if m == 0:
        return []

    # Build raw decision matrix x_ij
    X = np.array([[s[metric] for metric in metrics] for s in scenarios], dtype=float)

    # --- Vector normalization: r_ij = x_ij / sqrt(sum_k x_kj^2) ---
    denom = np.sqrt((X ** 2).sum(axis=0))
    denom[denom == 0] = 1e-12
    R = X / denom

    # --- Weighted matrix: v_ij = w_j * r_ij ---
    weights = np.array([TOPSIS_WEIGHTS[metric] for metric in metrics])
    V = R * weights

    # --- Ideal best / worst per column, respecting benefit vs cost direction ---
    ideal_best = np.zeros(len(metrics))
    ideal_worst = np.zeros(len(metrics))
    for j, metric in enumerate(metrics):
        col = V[:, j]
        if metric in TOPSIS_BENEFIT_METRICS:
            ideal_best[j] = col.max()
            ideal_worst[j] = col.min()
        else:  # cost metric -> lower is better
            ideal_best[j] = col.min()
            ideal_worst[j] = col.max()

    # --- Euclidean distances ---
    d_plus = np.sqrt(((V - ideal_best) ** 2).sum(axis=1))
    d_minus = np.sqrt(((V - ideal_worst) ** 2).sum(axis=1))

    denom_c = d_plus + d_minus
    denom_c[denom_c == 0] = 1e-12
    scores = d_minus / denom_c

    order = np.argsort(-scores)  # descending, closest to 1.0 first
    ranks = np.empty(m, dtype=int)
    ranks[order] = np.arange(1, m + 1)

    out = []
    for i, s in enumerate(scenarios):
        enriched = dict(s)
        enriched["topsis_score"] = float(scores[i])
        enriched["rank"] = int(ranks[i])
        out.append(enriched)

    out.sort(key=lambda d: d["rank"])
    return out
