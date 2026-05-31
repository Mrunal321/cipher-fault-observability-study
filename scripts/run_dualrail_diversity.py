#!/usr/bin/env python3
"""
run_dualrail_diversity.py — MIG/mMIG dual-rail diversity analysis.

Question: when MIG and mMIG implement the same circuit, do they have
DIFFERENT per-input fault sensitivity profiles?

If they do (low correlation across tested input patterns), running both in
parallel and comparing outputs catches faults that one alone would miss.
If they don't (high correlation), dual-rail with diverse implementations
shows no advantage in this campaign over running the same implementation twice.

Per circuit we measure:
  - sens_MIG(P)   = # MIG gates whose single-bit-flip fault propagates
                    to a primary output on input vector P
  - sens_mMIG(P)  = same for mMIG
  - correlation   = Pearson(sens_MIG, sens_mMIG) across all P
  - diversity     = 1 - correlation
  - attack_gain   = max_P sens(P) / mean_P sens(P)   (single-rail)
                    vs same for dual-rail combined, on the tested vectors
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from fault.dfa.blif_parser import Circuit, parse_blif_file
# Reuse simulator helpers from the fault coverage script
sys.path.insert(0, str(REPO / "scripts"))
from run_fault_coverage import (
    build_luts, sim_vectorized, output_matrix,
    EXHAUSTIVE_LIMIT, N_RANDOM, SEED,
    CIRCUITS, BENCH_DIR, blif_paths,
)

# ---------------------------------------------------------------------------
# Per-input fault sensitivity
# ---------------------------------------------------------------------------

def per_input_sensitivity(
    circuit: Circuit,
    luts: Dict[str, np.ndarray],
    test_matrix: np.ndarray,
) -> np.ndarray:
    """
    Return (N,) int array.  Entry P = number of gate-output faults that
    propagate to >=1 primary output on input vector P.
    """
    N = test_matrix.shape[0]

    ff_sig = sim_vectorized(circuit, luts, test_matrix)
    ff_out = output_matrix(circuit, ff_sig)         # (N, n_out)

    sens = np.zeros(N, dtype=np.int32)

    for gate in circuit.gates:
        correct = ff_sig[gate.output]
        flipped = (correct ^ 1).astype(np.uint8)

        faulty_sig = sim_vectorized(
            circuit, luts, test_matrix,
            overrides={gate.output: flipped},
        )
        faulty_out = output_matrix(circuit, faulty_sig)

        any_diff = (faulty_out != ff_out).any(axis=1).astype(np.int32)
        sens += any_diff

    return sens


# ---------------------------------------------------------------------------
# Test-vector generation (mirrors run_fault_coverage)
# ---------------------------------------------------------------------------

def make_test_vectors(n_inputs: int) -> np.ndarray:
    if n_inputs <= EXHAUSTIVE_LIMIT:
        N = 1 << n_inputs
        mat = np.zeros((N, n_inputs), dtype=np.uint8)
        for i in range(N):
            for j in range(n_inputs):
                mat[i, j] = (i >> (n_inputs - 1 - j)) & 1
        return mat
    rng = np.random.default_rng(SEED)
    return rng.integers(0, 2, size=(N_RANDOM, n_inputs), dtype=np.uint8)


# ---------------------------------------------------------------------------
# Diversity analysis per circuit
# ---------------------------------------------------------------------------

def pearson(a: np.ndarray, b: np.ndarray) -> float:
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    if a.std() == 0 or b.std() == 0:
        return 1.0
    return float(np.corrcoef(a, b)[0, 1])


def analyze(name: str) -> Dict[str, Any]:
    paths = blif_paths(name)
    mig_blif  = paths["mig"]
    mmig_blif = paths["mmig"]
    if not (mig_blif.exists() and mmig_blif.exists()):
        return {"circuit": name, "error": "missing BLIF"}

    mig  = parse_blif_file(str(mig_blif))
    mmig = parse_blif_file(str(mmig_blif))

    n_in = len(mig.inputs)
    if n_in != len(mmig.inputs):
        return {"circuit": name, "error": "input count mismatch"}

    test_matrix = make_test_vectors(n_in)
    N = test_matrix.shape[0]

    sens_mig  = per_input_sensitivity(mig,  build_luts(mig),  test_matrix)
    sens_mmig = per_input_sensitivity(mmig, build_luts(mmig), test_matrix)

    n_mig  = len(mig.gates)
    n_mmig = len(mmig.gates)

    # Per-input fraction of propagating faults
    frac_mig  = sens_mig  / n_mig  if n_mig  else sens_mig.astype(float)
    frac_mmig = sens_mmig / n_mmig if n_mmig else sens_mmig.astype(float)

    r = pearson(sens_mig, sens_mmig)

    # Dual-rail: count a fault as detectable on input P if it propagates in
    # EITHER implementation (since the other rail provides the correct output).
    # Total fault sites = n_mig + n_mmig.
    dual_count = sens_mig + sens_mmig
    dual_total = n_mig + n_mmig
    dual_frac  = dual_count / dual_total if dual_total else dual_count.astype(float)

        # "Attacker's best tested input" = input maximising propagation rate
    # Lower max = harder to attack
    return {
        "circuit": name,
        "n_test_vectors": int(N),
        "n_mig_gates":    int(n_mig),
        "n_mmig_gates":   int(n_mmig),

        # Single-rail per-input sensitivity (fraction of gates propagating)
        "mig_mean":  round(float(frac_mig.mean()),  4),
        "mig_max":   round(float(frac_mig.max()),   4),
        "mig_min":   round(float(frac_mig.min()),   4),
        "mig_std":   round(float(frac_mig.std()),   4),

        "mmig_mean": round(float(frac_mmig.mean()), 4),
        "mmig_max":  round(float(frac_mmig.max()),  4),
        "mmig_min":  round(float(frac_mmig.min()),  4),
        "mmig_std":  round(float(frac_mmig.std()),  4),

        # Diversity
        "pearson_r":     round(r, 4),
        "diversity":     round(1.0 - r, 4),

        # Dual-rail combined
        "dual_mean":   round(float(dual_frac.mean()), 4),
        "dual_max":    round(float(dual_frac.max()),  4),
        "dual_min":    round(float(dual_frac.min()),  4),

        # Per-input divergence: |sens_MIG(P) - sens_mMIG(P)| / (n_mig + n_mmig)
        # Measures how differently the two implementations respond per input.
        "abs_divergence_mean": round(
            float(np.abs(sens_mig - sens_mmig).mean() / (n_mig + n_mmig)), 4
        ),
        "abs_divergence_max": round(
            float(np.abs(sens_mig - sens_mmig).max()  / (n_mig + n_mmig)), 4
        ),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Dual-rail MIG/mMIG diversity analysis")
    p.add_argument("--out-dir", default="results/fault_coverage",
                   help="Output directory")
    p.add_argument("--circuits", nargs="+",
                   help="Restrict to specific circuit names")
    return p.parse_args()


def main():
    args = parse_args()
    out_dir = REPO / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = [c[0] for c in CIRCUITS
               if args.circuits is None or c[0] in args.circuits]

    hdr = (f"{'Circuit':<22} | {'N_in':>5} {'Nvec':>7} | "
           f"{'MIGmean':>8} {'MIGmax':>7} | {'mMIGmean':>9} {'mMIGmax':>8} | "
           f"{'Pearson':>8} {'Divers':>7} | {'AbsDiv':>7}")
    sep = "-" * len(hdr)
    print()
    print(hdr)
    print(sep)

    all_results: List[Dict[str, Any]] = []
    for name in targets:
        rec = analyze(name)
        all_results.append(rec)
        if "error" in rec:
            print(f"{name:<22} | ERROR: {rec['error']}")
            continue
        print(
            f"{name:<22} | "
            f"{rec['n_mig_gates']:>5} {rec['n_test_vectors']:>7} | "
            f"{rec['mig_mean']:>8.4f} {rec['mig_max']:>7.4f} | "
            f"{rec['mmig_mean']:>9.4f} {rec['mmig_max']:>8.4f} | "
            f"{rec['pearson_r']:>8.4f} {rec['diversity']:>7.4f} | "
            f"{rec['abs_divergence_mean']:>7.4f}"
        )

    out_json = out_dir / "dualrail_diversity.json"
    out_json.write_text(json.dumps(all_results, indent=2))
    print()
    print(f"Saved: {out_json}")

    # Verdict summary
    print()
    print("=" * 80)
    print("Verdict (per circuit)")
    print("=" * 80)
    print(f"{'Circuit':<22}  {'Pearson':>8}  {'Diversity':>10}  Verdict")
    print("-" * 70)
    for rec in all_results:
        if "error" in rec:
            continue
        r = rec["pearson_r"]
        if r > 0.95:
            v = "NO measured diversity — MIG and mMIG mask the same tested patterns"
        elif r > 0.80:
            v = "weak diversity — small dual-rail benefit"
        elif r > 0.50:
            v = "moderate diversity — dual-rail gives meaningful coverage"
        else:
            v = "STRONG measured diversity — dual-rail provides distinct coverage"
        print(f"{rec['circuit']:<22}  {r:>8.4f}  {rec['diversity']:>10.4f}  {v}")


if __name__ == "__main__":
    main()
