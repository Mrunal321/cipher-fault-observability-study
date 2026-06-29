#!/usr/bin/env python3
"""
invariant_metric.py - Evaluate target-layer and ARX/substitution controls.

granularity_baseline.py showed that AvgDP over *all* gate sites is strongly
associated with decomposition granularity (Spearman rho = -0.85; sign of the AOIG->MIG
effect flips with the baseline). This script tests two controls:

1. TARGET-LAYER INVARIANCE.  A realistic DFA adversary targets a specific
   intermediate value, not a uniformly-random internal gate. The realisable
   fault set is the gates that drive primary outputs (the target layer).
   We compute AvgDP and AvgBW restricted to those gates, for every flow.
   If the target-layer metric is ~constant across flows, that is the
   defensible, threat-model-aligned statement for the target layer.

2. FINDING-3 SURVIVAL (AvgBW).  The ARX-vs-substitution avalanche-breadth
   result is computed on the same netlists, so it must be re-checked against
   the same-granularity AIG baseline before it can be kept.

Flows compared per circuit: aoig (LUT truth-table), aig (2-input AIG), mig.

Output: results/fault_coverage/invariant_metric.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from fault.dfa.blif_parser import Circuit, parse_blif_file  # noqa: E402
from run_fault_coverage import (  # noqa: E402
    CIRCUITS, BENCH_DIR, build_luts, sim_vectorized,
    output_matrix, make_test_vectors,
)
import random  # noqa: E402

OUT_DIR = REPO / "results" / "fault_coverage"
SEED = 42

# Family labels for the ARX-vs-substitution check (from implicit_countermeasure.json).
FAMILY = {
    "present_sbox": "Sbox", "gift_sbox": "Sbox", "prince_sbox": "Sbox",
    "prince_sbox_inv": "Sbox", "gift_subcells": "Subst", "gift_round": "Subst",
    "present_round": "Subst", "simon32_round": "SIMON",
    "simon64_round": "SIMON", "keccak_chi_5bit": "Keccak", "keccak_chi_64row": "Keccak",
    "speckey_box": "ARX", "speck32_round": "ARX", "marx2_box": "ARX",
}


def flow_blif(name: str, flow: str) -> Path:
    d = BENCH_DIR / name
    return {
        "aoig": d / f"{name}_aoig.blif",
        "aig":  d / f"{name}_aig.blif",
        "mig":  d / f"{name}_mig_maj_opt.blif",
    }[flow]


def campaign_split(circuit: Circuit, test_mat: np.ndarray) -> dict:
    """Single-bit-flip campaign returning metrics split into ALL gate sites
    vs. TARGET-LAYER gate sites (gates whose output is a primary output)."""
    luts = build_luts(circuit)
    N = test_mat.shape[0]
    out_set = set(circuit.outputs)

    ff_sig = sim_vectorized(circuit, luts, test_mat)
    ff_out = output_matrix(circuit, ff_sig)

    def acc():
        return {"n": 0, "det": 0, "dp_sum": 0.0, "bw_sum": 0.0}

    allg, tgt = acc(), acc()

    for gate in circuit.gates:
        correct = ff_sig[gate.output]
        flipped = (correct ^ 1).astype(np.uint8)
        fsig = sim_vectorized(circuit, luts, test_mat,
                              overrides={gate.output: flipped})
        fout = output_matrix(circuit, fsig)
        diff = (fout != ff_out)
        per_vec = diff.sum(axis=1)
        detecting = per_vec > 0
        n_det = int(detecting.sum())

        is_tgt = gate.output in out_set
        for bucket, active in ((allg, True), (tgt, is_tgt)):
            if not active:
                continue
            bucket["n"] += 1
            if n_det > 0:
                bucket["det"] += 1
                bucket["dp_sum"] += n_det / N
                bucket["bw_sum"] += diff[detecting].sum() / n_det

    def finalize(b):
        det = b["det"]
        return {
            "total": b["n"],
            "detectable": det,
            "avgdp": round(b["dp_sum"] / det, 4) if det else None,
            "avgbw": round(b["bw_sum"] / det, 4) if det else None,
        }

    return {"all": finalize(allg), "target": finalize(tgt)}


def main() -> None:
    flows = ["aoig", "aig", "mig"]
    # keccak_chi_64row is 64 identical parallel copies of keccak_chi_5bit, and
    # simon64_round mirrors simon32_round (confirmed near-identical metrics in
    # implicit_countermeasure.json). They add ~no information here but dominate
    # runtime on the large AIG netlists, so skip them for this analysis.
    skip = {"keccak_chi_64row", "simon64_round"}
    rows = []

    hdr = (f"{'Circuit':<17}{'flow':<6}| {'all_dp':>7} {'tgt_dp':>7} | "
           f"{'all_bw':>7} {'tgt_bw':>7}")
    print()
    print(hdr)
    print("-" * len(hdr))

    for name, _ in CIRCUITS:
        if name in skip:
            continue
        rec = {"circuit": name, "family": FAMILY.get(name, "?"), "flows": {}}
        for flow in flows:
            bp = flow_blif(name, flow)
            if not bp.exists():
                continue
            circ = parse_blif_file(str(bp))
            rng = random.Random(SEED)
            tm = make_test_vectors(len(circ.inputs), rng)
            m = campaign_split(circ, tm)
            rec["flows"][flow] = m
            print(f"{name:<17}{flow:<6}| "
                  f"{str(m['all']['avgdp']):>7} {str(m['target']['avgdp']):>7} | "
                  f"{str(m['all']['avgbw']):>7} {str(m['target']['avgbw']):>7}")
        rows.append(rec)
        print()

    # ---- Analysis 1: target-layer dp invariance across flows ----
    print("=" * 60)
    print("TARGET-LAYER AvgDP across flows (should be ~invariant)")
    print("=" * 60)
    spreads = []
    for r in rows:
        dps = [r["flows"][f]["target"]["avgdp"] for f in flows
               if f in r["flows"] and r["flows"][f]["target"]["avgdp"] is not None]
        if len(dps) >= 2:
            spread = max(dps) - min(dps)
            spreads.append(spread)
            print(f"{r['circuit']:<17} {[f'{d:.3f}' for d in dps]}  spread={spread:.3f}")
    mean_spread = sum(spreads) / len(spreads) if spreads else float("nan")
    print(f"\nMean target-layer AvgDP spread across flows = {mean_spread:.4f}")
    print("(small spread => observability at the realistic target is "
          "representation-invariant)")

    # ---- Analysis 2: finding-3 (ARX vs Subst AvgBW) under each flow ----
    print()
    print("=" * 60)
    print("FINDING 3 survival: mean ALL-site AvgBW by family, per flow")
    print("=" * 60)
    fam_check = {}
    for flow in flows:
        byfam = {}
        for r in rows:
            if flow not in r["flows"]:
                continue
            bw = r["flows"][flow]["all"]["avgbw"]
            if bw is None:
                continue
            byfam.setdefault(r["family"], []).append(bw)
        means = {fam: round(sum(v) / len(v), 3) for fam, v in byfam.items()}
        arx = means.get("ARX")
        subst_vals = [bw for fam in ("Sbox", "Subst", "Perm")
                      for bw in byfam.get(fam, [])]
        subst = round(sum(subst_vals) / len(subst_vals), 3) if subst_vals else None
        ratio = round(arx / subst, 3) if (arx and subst) else None
        fam_check[flow] = {"by_family": means, "arx": arx,
                           "subst": subst, "arx_over_subst": ratio}
        print(f"{flow:<6} ARX={arx}  Subst={subst}  ARX/Subst={ratio}x")

    summary = {
        "target_layer_mean_spread": round(mean_spread, 4),
        "finding3_by_flow": fam_check,
    }
    (OUT_DIR / "invariant_metric.json").write_text(
        json.dumps({"rows": rows, "summary": summary}, indent=2))
    print(f"\nSaved: {OUT_DIR / 'invariant_metric.json'}")


if __name__ == "__main__":
    main()
