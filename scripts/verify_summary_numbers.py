#!/usr/bin/env python3
"""
Verify the reported summary numbers against the frozen/generated JSON data.

This is a submission-readiness guard: it fails loudly if the values used in
the abstract/README drift from the result files.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results" / "fault_coverage"
sys.path.insert(0, str(REPO / "scripts"))

def load_json(path: Path):
    return json.loads(path.read_text())


def check(condition: bool, message: str, failures: list[str]) -> None:
    if condition:
        print(f"PASS  {message}")
    else:
        print(f"FAIL  {message}")
        failures.append(message)


def close(actual: float, expected: float, tol: float = 1e-2) -> bool:
    return abs(actual - expected) <= tol


def pct_drop(new: float, old: float) -> float:
    return (new - old) / old * 100.0


def main() -> int:
    failures: list[str] = []

    implicit = load_json(RES / "summary_metrics.json")
    rows = implicit["rows"]
    reductions = [r["aoig_to_mig_pct"] for r in rows]
    improved = [x for x in reductions if x < 0]
    mean_reduction = sum(reductions) / len(reductions)

    check(len(rows) == 14, "summary rows cover 14 circuits", failures)
    check(len(improved) == 12, "AOIG -> MIG AvgDP reduction occurs on 12/14 circuits", failures)
    check(close(mean_reduction, -13.21, 0.02), "mean AOIG -> MIG AvgDP change is -13.21%", failures)
    check(close(min(reductions), -23.68, 0.05), "best AOIG -> MIG AvgDP drop is -23.7%", failures)
    check(close(max(reductions), 8.00, 0.05), "worst AOIG -> MIG AvgDP change is +8.0%", failures)

    f2 = implicit["finding_2_arx_vs_substitution"]
    check(close(f2["arx_mean_avgbw"], 2.06, 0.01), "ARX mean AvgBW is 2.06", failures)
    check(close(f2["subst_mean_avgbw"], 1.08, 0.01), "substitution mean AvgBW is 1.08", failures)
    check(close(f2["arx_over_subst_x"], 1.90, 0.01), "ARX/substitution AvgBW ratio is 1.90x", failures)

    majn = load_json(RES / "majN" / "majN_fault_study.json")
    chain = {r["arity"]: r for r in majn["chain"]}
    tree = {r["arity"]: r for r in majn["tree"]}
    maj_reductions = [
        pct_drop(chain[5]["avg_det_prob"], chain[3]["avg_det_prob"]),
        pct_drop(chain[7]["avg_det_prob"], chain[3]["avg_det_prob"]),
        pct_drop(tree[5]["avg_det_prob"], tree[3]["avg_det_prob"]),
        pct_drop(tree[7]["avg_det_prob"], tree[3]["avg_det_prob"]),
    ]
    check(close(abs(max(maj_reductions)), 18.12, 0.05), "smallest MAJ-n AvgDP reduction is 18.1%", failures)
    check(close(abs(min(maj_reductions)), 61.87, 0.05), "largest MAJ-n AvgDP reduction is 61.9%", failures)

    granularity_path = RES / "granularity_baseline.json"
    if granularity_path.exists():
        granularity = load_json(granularity_path)
        summary = granularity["summary"]
        check(len(granularity["rows"]) == 14, "small-gate AIG control covers 14 circuits", failures)
        check(summary["n_with_reduction"] == 0, "AIG -> MIG AvgDP reduction occurs on 0/14 circuits", failures)
        check(close(summary["mean_pct_change"], 21.54, 0.02), "AIG -> MIG mean AvgDP change is +21.54%", failures)

    invariant_path = RES / "invariant_metric.json"
    if invariant_path.exists():
        invariant = load_json(invariant_path)
        check(close(invariant["summary"]["target_layer_mean_spread"], 0.0, 1e-6),
              "target-layer AvgDP spread is zero across evaluated representations", failures)

    if failures:
        print()
        print(f"{len(failures)} summary-number check(s) failed.")
        return 1

    print()
    print("All summary-number checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
