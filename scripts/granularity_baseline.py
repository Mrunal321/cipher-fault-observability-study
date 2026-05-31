#!/usr/bin/env python3
"""
granularity_baseline.py — Same-granularity AvgDP control for AOIG -> MIG.

The headline AvgDP reduction (mean -13%, README finding 1) compares a Yosys
LUT/truth-table "AOIG" netlist against a fully MAJ3-decomposed MIG netlist.
In the LUT baseline each output bit is a *single* undecomposed node, so the
only detectable fault sites are the output functions themselves -> dp = 1.0
on 13/15 circuits by construction. The MIG average additionally includes many
interior MAJ3 nodes whose dp < 1. The reduction may therefore be a granularity
(node-count / mix-shift) artifact rather than a property of majority logic.

This script removes that confound: it re-synthesizes each circuit into a
2-input AND-Inverter Graph (AIG) via `yosys ... abc -g AND`, so the baseline
is decomposed to the same primitive-gate granularity class as the MIG. It then
runs the identical single-bit-flip campaign on the AIG and the existing MIG and
reports how much of the AvgDP gap survives.

Outputs:
  results/fpga_benchmark/<name>/<name>_aig.blif   (generated AIG netlists)
  results/fault_coverage/granularity_baseline.json
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from fault.dfa.blif_parser import parse_blif_file

# Reuse the exact campaign machinery from the headline script.
sys.path.insert(0, str(REPO / "scripts"))
from run_fault_coverage import (  # noqa: E402
    CIRCUITS,
    BLIF_DIR,
    BENCH_DIR,
    make_test_vectors,
    run_fault_campaign,
)
import random  # noqa: E402

OUT_DIR = REPO / "results" / "fault_coverage"
SEED = 42

YOSYS_SCRIPT = """\
read_blif {raw}
hierarchy -auto-top
flatten
proc
techmap
opt
abc -g AND
opt_clean
write_blif {out}
"""


def gen_aig(raw_blif: Path, out_blif: Path) -> None:
    """Synthesize a 2-input AIG BLIF from a raw truth-table BLIF via yosys."""
    out_blif.parent.mkdir(parents=True, exist_ok=True)
    script = YOSYS_SCRIPT.format(raw=raw_blif, out=out_blif)
    proc = subprocess.run(
        ["yosys", "-q", "-p", script],
        capture_output=True, text=True,
    )
    if proc.returncode != 0 or not out_blif.exists():
        raise RuntimeError(
            f"yosys failed for {raw_blif.name}:\n{proc.stderr or proc.stdout}"
        )


def mig_blif(name: str) -> Path:
    return BENCH_DIR / name / f"{name}_mig_maj_opt.blif"


def aig_blif(name: str) -> Path:
    return BENCH_DIR / name / f"{name}_aig.blif"


def campaign(blif: Path) -> dict:
    circ = parse_blif_file(str(blif))
    rng = random.Random(SEED)
    test_mat = make_test_vectors(len(circ.inputs), rng)
    return run_fault_campaign(circ, test_mat)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    hdr = (f"{'Circuit':<18}| {'AIG_g':>6} {'AIG_dp':>7} | "
           f"{'MIG_g':>6} {'MIG_dp':>7} | {'dp delta %':>10}")
    print()
    print(hdr)
    print("-" * len(hdr))

    rows = []
    for name, raw_rel in CIRCUITS:
        raw = BLIF_DIR / raw_rel
        aig = aig_blif(name)
        mig = mig_blif(name)
        if not mig.exists():
            print(f"{name:<18}| SKIP (no MIG: {mig.name})")
            continue

        gen_aig(raw, aig)
        a = campaign(aig)
        m = campaign(mig)

        ad, md = a["avg_det_prob"], m["avg_det_prob"]
        # Same sign convention as finding_1: (mig - base)/base * 100
        delta = 100.0 * (md - ad) / ad if ad else float("nan")

        print(f"{name:<18}| {a['total_faults']:>6} {ad:>7.4f} | "
              f"{m['total_faults']:>6} {md:>7.4f} | {delta:>+10.2f}")

        rows.append({
            "circuit": name,
            "aig_total_faults": a["total_faults"],
            "aig_detectable": a["detectable"],
            "aig_avgdp": ad,
            "aig_fault_coverage": a["fault_coverage"],
            "mig_total_faults": m["total_faults"],
            "mig_detectable": m["detectable"],
            "mig_avgdp": md,
            "mig_fault_coverage": m["fault_coverage"],
            "aig_to_mig_pct": round(delta, 2),
        })

    # Aggregate
    deltas = [r["aig_to_mig_pct"] for r in rows]
    n_red = sum(1 for d in deltas if d < 0)
    mean_d = sum(deltas) / len(deltas) if deltas else 0.0
    summary = {
        "baseline": "yosys abc -g AND (2-input AIG), same-granularity control",
        "n_circuits": len(rows),
        "n_with_reduction": n_red,
        "mean_pct_change": round(mean_d, 2),
        "note": ("Compare against the LUT-baseline finding_1 mean of -13.0% "
                 "(13/15 reduced). The gap that survives here is the part of "
                 "the AvgDP effect not explained by synthesis granularity."),
    }

    print("-" * len(hdr))
    print(f"AIG->MIG: mean dp change = {mean_d:+.2f}%  "
          f"({n_red}/{len(rows)} circuits reduced)")
    print(f"LUT->MIG (headline)     = -13.00%  (13/15 reduced)")
    print()

    out = OUT_DIR / "granularity_baseline.json"
    out.write_text(json.dumps({"rows": rows, "summary": summary}, indent=2))
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
