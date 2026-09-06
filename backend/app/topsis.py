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

try:
    from .config import TOPSIS_WEIGHTS, TOPSIS_BENEFIT_METRICS, TOPSIS_COST_METRICS
except ImportError:
    from config import TOPSIS_WEIGHTS, TOPSIS_BENEFIT_METRICS, TOPSIS_COST_METRICS


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


if __name__ == "__main__":
    print("=" * 72)
    print("  Blue Grid — TOPSIS Multi-Criteria Decision Analysis (Hwang & Yoon 1981)")
    print("=" * 72)
    print("\nDecision Weights:")
    for metric, w in TOPSIS_WEIGHTS.items():
        kind = "Benefit (+)" if metric in TOPSIS_BENEFIT_METRICS else "Cost (-)"
        print(f"  • {metric:<14} Weight = {w:.2f}  [{kind}]")

    sample_scenarios = [
        {
            "label": "1. Zero-Outage (PuLP Optimal)",
            "solar_kw": 3200, "wind_kw": 3000, "otec_kw": 680, "bess_kwh": 16000,
            "lcoe": 10.52, "capex": 86.7e7, "lolp": 0.00, "co2_avoided": 7183.0
        },
        {
            "label": "2. Deck Reference Baseline",
            "solar_kw": 2400, "wind_kw": 1200, "otec_kw": 400, "bess_kwh": 8000,
            "lcoe": 6.82, "capex": 47.0e7, "lolp": 28.57, "co2_avoided": 6044.0
        },
        {
            "label": "3. Solar + Battery Only",
            "solar_kw": 3500, "wind_kw": 0, "otec_kw": 0, "bess_kwh": 12000,
            "lcoe": 6.67, "capex": 37.3e7, "lolp": 38.58, "co2_avoided": 5340.0
        },
        {
            "label": "4. Wind + OTEC + Battery",
            "solar_kw": 0, "wind_kw": 1800, "otec_kw": 600, "bess_kwh": 10000,
            "lcoe": 10.43, "capex": 50.7e7, "lolp": 87.21, "co2_avoided": 1240.0
        }
    ]

    print(f"\nEvaluating {len(sample_scenarios)} Microgrid Configurations:\n")
    ranked = rank_scenarios(sample_scenarios)

    header = f"{'Rank':<6} {'Scenario Configuration':<32} {'Score (Ci)':<12} {'LCOE (Rs/u)':<13} {'LOLP (%)':<10} {'CAPEX':<12} {'CO2 Saved':<12}"
    print(header)
    print("-" * len(header))
    for r in ranked:
        capex_str = f"Rs {r['capex']/1e7:.1f} Cr"
        co2_str = f"{r['co2_avoided']:,.0f} t/yr"
        print(f"#{r['rank']:<5} {r['label']:<32} {r['topsis_score']:<12.4f} Rs {r['lcoe']:<10.2f} {r['lolp']:<9.2f}% {capex_str:<12} {co2_str:<12}")

    print("\nInterpretation:")
    winner = ranked[0]
    print(f"  -> Winner: {winner['label']} (Closeness Score: {winner['topsis_score']:.4f})")
    print(f"  -> Mathematical formula: Ci = D- / (D+ + D-), where D- is Euclidean distance to worst, D+ to best.")
    print("=" * 72)
