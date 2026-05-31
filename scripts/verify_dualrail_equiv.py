#!/usr/bin/env python3
"""
verify_dualrail_equiv.py — Stronger test of MIG/mMIG fault equivalence.

For each tested input vector P:
  - Enumerate all distinct faulty outputs produced by any single-bit-flip
    fault in MIG.
  - Same for mMIG.
  - Compare the SETS.

If the sets are equal for every tested P → MIG and mMIG are empirically
fault-equivalent in this campaign; the benchmark provides no evidence
for dual-rail diversity under this model.

If the sets differ → dual-rail diversity exists; report quantitatively.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Set, Tuple, Dict, Any, List

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from fault.dfa.blif_parser import parse_blif_file
from run_fault_coverage import (
    build_luts, sim_vectorized, output_matrix,
    CIRCUITS, blif_paths,
    EXHAUSTIVE_LIMIT, N_RANDOM, SEED,
)


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


def faulty_output_sets(circuit, luts, test_matrix) -> List[Set[int]]:
    """
    For each test vector P, return the SET of distinct faulty outputs
    (encoded as int) reachable by any single-bit-flip fault.

    Includes the fault-free output (representing "no fault detected"
    or "fault masked").
    """
    N = test_matrix.shape[0]
    n_out = len(circuit.outputs)

    ff_sig = sim_vectorized(circuit, luts, test_matrix)
    ff_out = output_matrix(circuit, ff_sig)  # (N, n_out)

    # Pack outputs into a single int per vector for hashing
    def pack(mat):
        result = np.zeros(mat.shape[0], dtype=np.int64)
        for j in range(mat.shape[1]):
            result = (result << 1) | mat[:, j].astype(np.int64)
        return result

    ff_packed = pack(ff_out)
    per_input_sets: List[Set[int]] = [set([int(ff_packed[i])]) for i in range(N)]

    for gate in circuit.gates:
        correct = ff_sig[gate.output]
        flipped = (correct ^ 1).astype(np.uint8)

        faulty_sig = sim_vectorized(
            circuit, luts, test_matrix,
            overrides={gate.output: flipped},
        )
        faulty_out = output_matrix(circuit, faulty_sig)
        faulty_packed = pack(faulty_out)
        for i in range(N):
            per_input_sets[i].add(int(faulty_packed[i]))

    return per_input_sets


def analyze(name: str) -> Dict[str, Any]:
    paths = blif_paths(name)
    if not (paths["mig"].exists() and paths["mmig"].exists()):
        return {"circuit": name, "error": "missing BLIF"}

    mig  = parse_blif_file(str(paths["mig"]))
    mmig = parse_blif_file(str(paths["mmig"]))

    n_in = len(mig.inputs)
    test_matrix = make_test_vectors(n_in)
    N = test_matrix.shape[0]

    mig_sets  = faulty_output_sets(mig,  build_luts(mig),  test_matrix)
    mmig_sets = faulty_output_sets(mmig, build_luts(mmig), test_matrix)

    # Compare per-input
    identical_count = 0
    mig_extra_total = 0
    mmig_extra_total = 0
    union_total = 0
    intersection_total = 0

    for i in range(N):
        s_mig  = mig_sets[i]
        s_mmig = mmig_sets[i]
        if s_mig == s_mmig:
            identical_count += 1
        mig_extra_total  += len(s_mig - s_mmig)
        mmig_extra_total += len(s_mmig - s_mig)
        union_total      += len(s_mig | s_mmig)
        intersection_total += len(s_mig & s_mmig)

    avg_jaccard = (intersection_total / union_total) if union_total else 1.0

    return {
        "circuit": name,
        "n_test_vectors": int(N),
        "identical_per_input": identical_count,
        "identical_frac":    round(identical_count / N, 4),
        "avg_jaccard":       round(float(avg_jaccard), 4),
        "mig_only_outputs":  int(mig_extra_total),
        "mmig_only_outputs": int(mmig_extra_total),
        "diversity_present": (mig_extra_total + mmig_extra_total) > 0,
    }


def main():
    out_dir = REPO / "results" / "fault_coverage"
    out_dir.mkdir(parents=True, exist_ok=True)

    hdr = (f"{'Circuit':<22} | {'Nvec':>6} | {'Identical%':>10} | "
           f"{'Jaccard':>8} | {'MIG-only':>9} {'mMIG-only':>10} | Verdict")
    print()
    print(hdr)
    print("-" * len(hdr))

    results = []
    for name, _ in CIRCUITS:
        rec = analyze(name)
        results.append(rec)
        if "error" in rec:
            print(f"{name:<22} | ERROR: {rec['error']}")
            continue
        verdict = "EQUIVALENT" if not rec["diversity_present"] else "DIVERGENT"
        print(
            f"{rec['circuit']:<22} | {rec['n_test_vectors']:>6} | "
            f"{rec['identical_frac']*100:>9.2f}% | "
            f"{rec['avg_jaccard']:>8.4f} | "
            f"{rec['mig_only_outputs']:>9} {rec['mmig_only_outputs']:>10} | "
            f"{verdict}"
        )

    out_json = out_dir / "dualrail_equivalence.json"
    out_json.write_text(json.dumps(results, indent=2))
    print()
    print(f"Saved: {out_json}")


if __name__ == "__main__":
    main()
