"""
Blue Grid — Standalone TOPSIS Evaluation Runner
Team: CODEQUADRANTS | Ocean Hackathon
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.topsis import rank_scenarios, TOPSIS_WEIGHTS, TOPSIS_BENEFIT_METRICS
from app.scenario_engine import run_scenario, comparison_topsis

def main():
    print("=" * 80)
    print("  BLUE GRID — TOPSIS Multi-Criteria Decision Analysis (Hwang & Yoon 1981)")
    print("=" * 80)
    print("\n[Step 1] Evaluation Criteria & Normalized Weights:")
    for metric, w in TOPSIS_WEIGHTS.items():
        kind = "Benefit (+ higher better)" if metric in TOPSIS_BENEFIT_METRICS else "Cost (- lower better)"
        print(f"  • {metric:<16} : {w:.2f}  [{kind}]")

    island = "kadmat"
    print(f"\n[Step 2] Simulating Real 8,760-Hour Scenarios for Island: {island.title()}...")
    
    # Run the reference scenario
    ref_scenario = run_scenario(island, solar_kw=2400, wind_kw=1200, otec_kw=400, bess_kwh=8000)
    
    # Run TOPSIS comparison across baselines
    ranked = comparison_topsis(ref_scenario)

    print(f"\n[Step 3] TOPSIS Ranking Results (Sorted Best to Worst):\n")
    header = f"{'Rank':<6} {'Scenario':<20} {'Score (Ci)':<12} {'LCOE (Rs/kWh)':<15} {'LOLP (%)':<11} {'CAPEX':<14} {'CO2 Saved':<12}"
    print(header)
    print("-" * len(header))
    for r in ranked:
        capex_str = f"Rs {r['capex']/1e7:.2f} Cr"
        co2_str = f"{r['co2_avoided']:,.0f} t/yr"
        print(f"#{r['rank']:<5} {r['label']:<20} {r['topsis_score']:<12.4f} Rs {r['lcoe']:<12.2f} {r['lolp']:<10.2f}% {capex_str:<14} {co2_str:<12}")

    print("\n" + "=" * 80)
    print("Interpretation:")
    print("  • Ci is the Relative Closeness to the Ideal Solution: Ci = D- / (D+ + D-)")
    print("  • A score closer to 1.0 indicates a superior balance of Cost, Reliability, and Carbon.")
    print("=" * 80)

if __name__ == "__main__":
    main()
