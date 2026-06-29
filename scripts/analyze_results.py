#!/usr/bin/env python3
"""
analyze_results.py - Summarize the active fault-observability results.

  Finding 1: MIG synthesis reduces per-vector fault observability
             relative to the AOIG baseline. AvgDP drops by a mean of
             13% from AOIG to MIG on 13/15 circuits because downstream
             majority gates mask propagated faults on non-controlling
             input patterns.

  Finding 2: Cipher architecture predicts fault avalanche breadth.
             ARX ciphers show 2.06 mean output bits flipped per fault
             (AvgBW); substitution-based and Keccak primitives show 1.00.
             A 2x dichotomy attributable to addition-chain carry propagation.

These are computed from existing JSONs, so no re-simulation is needed.
Output: results/fault_coverage/summary_metrics.json and a printable summary.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Dict, Any, List

REPO = Path(__file__).resolve().parents[1]
RES  = REPO / "results"

# ---------------------------------------------------------------------------
# Cipher-architecture taxonomy
# ---------------------------------------------------------------------------
FAMILY = {
    "present_sbox":     "4-bit S-box",
    "gift_sbox":        "4-bit S-box",
    "prince_sbox":      "4-bit S-box",
    "prince_sbox_inv":  "4-bit S-box",
    "gift_subcells":    "Subst. round",
    "gift_round":       "Subst. round",
    "present_round":    "Subst. round",
    "prince_mprime":    "Permutation",
    "simon32_round":    "SIMON",
    "simon64_round":    "SIMON",
    "keccak_chi_5bit":  "Keccak chi",
    "keccak_chi_64row": "Keccak chi",
    "speck32_round":    "ARX",
    "speckey_box":      "ARX",
    "marx2_box":        "ARX",
}

ARX_FAMILIES   = ("ARX",)
SUBST_FAMILIES = ("4-bit S-box", "Subst. round")


def main() -> None:
    fc = json.loads((RES / "fault_coverage" / "fault_coverage_results.json").read_text())
    by_name = {r["circuit"]: r for r in fc}

    rows: List[Dict[str, Any]] = []
    for name, family in FAMILY.items():
        rec = by_name.get(name)
        if not rec or "flows" not in rec:
            continue
        aoig = rec["flows"].get("aoig", {})
        mig  = rec["flows"].get("mig",  {})
        if not aoig or not mig:
            continue

        a_dp  = aoig.get("avg_det_prob", 0.0)
        m_dp  = mig .get("avg_det_prob", 0.0)
        rel_aoig_to_mig = ((m_dp - a_dp) / a_dp * 100.0) if a_dp else 0.0

        rows.append({
            "circuit":             name,
            "family":              family,
            "aoig_avgdp":          a_dp,
            "mig_avgdp":           m_dp,
            "aoig_to_mig_pct":     rel_aoig_to_mig,
            "aoig_avgbw":          aoig.get("avg_breadth", 0.0),
            "mig_avgbw":           mig .get("avg_breadth", 0.0),
            "aoig_fault_coverage": aoig.get("fault_coverage", 0.0),
            "mig_fault_coverage":  mig .get("fault_coverage", 0.0),
        })

    # ----- Finding 1: AvgDP reduction -----
    reductions = [r["aoig_to_mig_pct"] for r in rows]
    n_improved = sum(1 for x in reductions if x < 0)
    summary_1 = {
        "n_circuits":          len(rows),
        "n_with_improvement":  n_improved,
        "mean_pct_change":     statistics.mean(reductions),
        "median_pct_change":   statistics.median(reductions),
        "best_improvement":    min(reductions),
        "best_circuit":        rows[reductions.index(min(reductions))]["circuit"],
        "worst_improvement":   max(reductions),
        "worst_circuit":       rows[reductions.index(max(reductions))]["circuit"],
    }

    # ----- Finding 2: AvgBW by architecture family -----
    by_family: Dict[str, List[float]] = {}
    for r in rows:
        by_family.setdefault(r["family"], []).append(r["mig_avgbw"])

    family_stats = {}
    for fam, vals in by_family.items():
        family_stats[fam] = {
            "n":     len(vals),
            "mean":  round(statistics.mean(vals), 6),
            "stdev": round(statistics.pstdev(vals) if len(vals) > 1 else 0.0, 6),
            "min":   round(min(vals), 6),
            "max":   round(max(vals), 6),
        }

    arx_mean = statistics.mean(
        v for f in ARX_FAMILIES   for v in by_family.get(f, [])
    )
    subst_mean = statistics.mean(
        v for f in SUBST_FAMILIES for v in by_family.get(f, [])
    )
    summary_2 = {
        "family_stats":     family_stats,
        "arx_mean_avgbw":   round(arx_mean, 6),
        "subst_mean_avgbw": round(subst_mean, 6),
        "arx_over_subst_x": round(arx_mean / subst_mean if subst_mean else 0.0, 6),
    }

    # ----- Save & print -----
    output = {
        "rows":              rows,
        "finding_1_observability_reduction":    summary_1,
        "finding_2_arx_vs_substitution":        summary_2,
    }
    out_path = RES / "fault_coverage" / "summary_metrics.json"
    out_path.write_text(json.dumps(output, indent=2))

    print("=" * 78)
    print("RESULT 1 - AOIG-to-MIG all-site AvgDP comparison")
    print("=" * 78)
    print(f"  {summary_1['n_with_improvement']}/{summary_1['n_circuits']} circuits "
          f"show AvgDP reduction AOIG → MIG")
    print(f"  Mean Δ AvgDP : {summary_1['mean_pct_change']:+.2f}%")
    print(f"  Median Δ AvgDP : {summary_1['median_pct_change']:+.2f}%")
    print(f"  Best  : {summary_1['best_circuit']:<22} ({summary_1['best_improvement']:+.1f}%)")
    print(f"  Worst : {summary_1['worst_circuit']:<22} ({summary_1['worst_improvement']:+.1f}%)")

    print()
    print("=" * 78)
    print("RESULT 2 - Fault avalanche breadth: ARX vs substitution-based")
    print("=" * 78)
    print(f"  {'Family':<18} {'n':>3} {'mean AvgBW':>11} {'min':>6} {'max':>6}")
    print(f"  {'-'*18} {'---':>3} {'-'*11:>11} {'-'*6:>6} {'-'*6:>6}")
    for fam, st in family_stats.items():
        print(f"  {fam:<18} {st['n']:>3} {st['mean']:>11.3f} {st['min']:>6.2f} {st['max']:>6.2f}")
    print()
    print(f"  ARX mean AvgBW   : {summary_2['arx_mean_avgbw']:.3f}")
    print(f"  Subst mean AvgBW : {summary_2['subst_mean_avgbw']:.3f}")
    print(f"  ARX over Subst   : {summary_2['arx_over_subst_x']:.2f}x")

    print()
    print(f"Saved: {out_path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
