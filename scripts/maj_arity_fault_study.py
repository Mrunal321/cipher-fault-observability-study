#!/usr/bin/env python3
"""
maj_arity_fault_study.py — Measure the fault-resilience ceiling of
higher-arity majority gates (MAJ3 vs MAJ5 vs MAJ7).

We bypass synthesis entirely and construct synthetic BLIF circuits with
MAJn primitives as single 5-input or 7-input truth-table gates.  Then
we run the same single-bit-flip campaign as on the cipher circuits.

This isolates the *gate-level masking* effect from synthesis variance.

Three experiments:
  1. SINGLE-GATE   — one MAJn gate, exhaustive faults
                     Confirms theoretical per-input masking probability.
  2. CHAIN         — depth-D chain of MAJn gates
                     Measures end-to-end propagation through depth.
  3. EQUAL-GATES   — K MAJn gates arranged in a balanced tree
                     Same gate count, different arity.

For each, we compute:
  - per-input masking ratio (theoretical: 0.500 for MAJ3, 0.625 for MAJ5,
    ≈0.687 for MAJ7)
  - end-to-end fault coverage
  - mean output Hamming distance per detectable fault

If MAJ5 chains show measurably lower propagation than MAJ3 chains at the
same depth, the higher-arity direction is worth full synthesis investment.
"""

from __future__ import annotations

import json
import sys
from itertools import product
from pathlib import Path
from typing import Dict, Any, List

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from fault.dfa.blif_parser import parse_blif
from run_fault_coverage import (
    build_luts, sim_vectorized, output_matrix,
)

# ---------------------------------------------------------------------------
# Synthetic BLIF generation
# ---------------------------------------------------------------------------

def maj_cover_rows(arity: int) -> List[str]:
    """Return BLIF cover rows for a MAJ-arity gate (output=1 iff majority of
    inputs are 1)."""
    rows = []
    thresh = arity // 2 + 1   # need >= half + 1 ones (since arity odd)
    for combo in product((0, 1), repeat=arity):
        if sum(combo) >= thresh:
            rows.append("".join(str(c) for c in combo) + " 1")
    return rows


def gen_single_majn(arity: int) -> str:
    """One MAJ-arity gate, arity inputs, 1 output."""
    inputs = [f"x{i}" for i in range(arity)]
    blif  = f".model maj{arity}_single\n"
    blif += f".inputs {' '.join(inputs)}\n"
    blif += ".outputs y0\n"
    blif += f".names {' '.join(inputs)} y0\n"
    blif += "\n".join(maj_cover_rows(arity)) + "\n"
    blif += ".end\n"
    return blif


def gen_chain(arity: int, depth: int) -> str:
    """Chain of `depth` MAJ-arity gates.

    g1 = MAJn(x0, x1, ..., x_{n-1})
    g2 = MAJn(g1, x_n, x_{n+1}, ..., x_{n+n-2})    # adds n-1 new inputs
    ...
    output = g_depth
    """
    new_per_gate = arity - 1
    n_inputs     = arity + new_per_gate * (depth - 1)
    inputs       = [f"x{i}" for i in range(n_inputs)]

    blif  = f".model maj{arity}_chain_d{depth}\n"
    blif += f".inputs {' '.join(inputs)}\n"
    blif += f".outputs g{depth}\n"

    rows = maj_cover_rows(arity)
    cur = 0
    prev_out = None
    for level in range(1, depth + 1):
        if level == 1:
            gate_in = inputs[cur:cur + arity]; cur += arity
        else:
            gate_in = [prev_out] + inputs[cur:cur + new_per_gate]
            cur += new_per_gate
        gname = f"g{level}"
        blif += f".names {' '.join(gate_in)} {gname}\n"
        blif += "\n".join(rows) + "\n"
        prev_out = gname

    blif += ".end\n"
    return blif


def gen_balanced_tree(arity: int, depth: int) -> str:
    """Balanced MAJ-arity tree of given depth.

    Level 1: arity^(depth-1) leaf gates, each consuming `arity` primary inputs
    Level 2: arity^(depth-2) gates, each consuming `arity` level-1 outputs
    ...
    Level depth: 1 gate (root)
    """
    rows = maj_cover_rows(arity)
    n_leaves = arity ** (depth - 1)
    n_inputs = arity * n_leaves
    inputs   = [f"x{i}" for i in range(n_inputs)]

    blif  = f".model maj{arity}_tree_d{depth}\n"
    blif += f".inputs {' '.join(inputs)}\n"
    blif += f".outputs root\n"

    current_level: List[str] = []
    # Level 1: arity primary inputs per gate
    for g in range(n_leaves):
        gname = f"L1_{g}"
        in_slice = inputs[g * arity:(g + 1) * arity]
        blif += f".names {' '.join(in_slice)} {gname}\n"
        blif += "\n".join(rows) + "\n"
        current_level.append(gname)

    # Higher levels
    for lvl in range(2, depth + 1):
        next_level = []
        n_gates    = len(current_level) // arity
        for g in range(n_gates):
            in_slice = current_level[g * arity:(g + 1) * arity]
            gname = f"L{lvl}_{g}" if lvl < depth else "root"
            blif += f".names {' '.join(in_slice)} {gname}\n"
            blif += "\n".join(rows) + "\n"
            next_level.append(gname)
        current_level = next_level

    blif += ".end\n"
    return blif


# ---------------------------------------------------------------------------
# Fault campaign on a synthetic BLIF
# ---------------------------------------------------------------------------

def run_campaign(blif_text: str, n_random: int = 50_000, seed: int = 42) -> Dict[str, Any]:
    circuit = parse_blif(blif_text)
    luts    = build_luts(circuit)
    n_in    = len(circuit.inputs)

    # Test vectors
    if n_in <= 20:
        N = 1 << n_in
        mat = np.zeros((N, n_in), dtype=np.uint8)
        for i in range(N):
            for j in range(n_in):
                mat[i, j] = (i >> (n_in - 1 - j)) & 1
        test_matrix = mat
    else:
        rng = np.random.default_rng(seed)
        test_matrix = rng.integers(0, 2, size=(n_random, n_in), dtype=np.uint8)

    N      = test_matrix.shape[0]
    ff_sig = sim_vectorized(circuit, luts, test_matrix)
    ff_out = output_matrix(circuit, ff_sig)

    n_gates       = len(circuit.gates)
    detectable    = 0
    sum_det_prob  = 0.0
    sum_breadth   = 0.0
    for gate in circuit.gates:
        correct = ff_sig[gate.output]
        flipped = (correct ^ 1).astype(np.uint8)
        faulty  = sim_vectorized(circuit, luts, test_matrix,
                                 overrides={gate.output: flipped})
        fout    = output_matrix(circuit, faulty)
        diff    = (fout != ff_out)
        per_vec = diff.sum(axis=1)
        detect  = (per_vec > 0)
        n_det   = int(detect.sum())
        if n_det > 0:
            detectable   += 1
            sum_det_prob += n_det / N
            sum_breadth  += float(diff[detect].sum()) / n_det

    fc       = 100.0 * detectable / n_gates if n_gates else 0.0
    avg_dp   = sum_det_prob / detectable if detectable else 0.0
    avg_br   = sum_breadth  / detectable if detectable else 0.0

    return {
        "n_inputs":       int(n_in),
        "n_gates":        int(n_gates),
        "n_test_vectors": int(N),
        "detectable":     int(detectable),
        "fault_coverage": round(fc, 2),
        "avg_det_prob":   round(avg_dp, 4),
        "avg_breadth":    round(avg_br, 4),
    }


# ---------------------------------------------------------------------------
# Theoretical per-input masking
# ---------------------------------------------------------------------------

def theoretical_input_masking(arity: int) -> float:
    """
    Probability that flipping ONE input does not change MAJn output,
    given uniformly-random values on the other inputs.

    Flip changes output iff the other inputs are tied (exactly arity//2 ones)
    OR the flipped input is the deciding one.  For odd arity n:
      P(propagate) = C(n-1, (n-1)/2) / 2^(n-1)
      P(masked)    = 1 - P(propagate)
    """
    from math import comb
    n = arity
    p_propagate = comb(n - 1, (n - 1) // 2) / (2 ** (n - 1))
    return 1.0 - p_propagate


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    out_dir = REPO / "results" / "fault_coverage" / "majN"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Persist generated BLIFs for transparency
    def save_blif(name: str, text: str):
        (out_dir / f"{name}.blif").write_text(text)

    arities = [3, 5, 7]

    # ---- Experiment 1: single gate ----
    print("\n" + "=" * 72)
    print("Experiment 1 — Single MAJn gate (exhaustive test)")
    print("=" * 72)
    print(f"{'Arity':>5} | {'P_mask(theory)':>14} | {'N_gates':>7} {'Det':>5} {'FC%':>6} {'AvgDP':>7}")
    single_rows = []
    for a in arities:
        text = gen_single_majn(a)
        save_blif(f"maj{a}_single", text)
        r = run_campaign(text)
        pm = theoretical_input_masking(a)
        print(f"{a:>5} | {pm:>14.4f} | {r['n_gates']:>7} {r['detectable']:>5} "
              f"{r['fault_coverage']:>6.2f} {r['avg_det_prob']:>7.4f}")
        single_rows.append({"arity": a, **r, "theory_mask": pm})

    # ---- Experiment 2: depth-D chain ----
    print("\n" + "=" * 72)
    print("Experiment 2 — MAJn chain, depth 5  (fault propagation through depth)")
    print("=" * 72)
    print(f"{'Arity':>5} | {'N_in':>4} {'N_gates':>7} {'FC%':>6} {'AvgDP':>7} {'AvgBW':>7}")
    chain_rows = []
    DEPTH = 5
    for a in arities:
        text = gen_chain(a, DEPTH)
        save_blif(f"maj{a}_chain_d{DEPTH}", text)
        r = run_campaign(text)
        print(f"{a:>5} | {r['n_inputs']:>4} {r['n_gates']:>7} "
              f"{r['fault_coverage']:>6.2f} {r['avg_det_prob']:>7.4f} {r['avg_breadth']:>7.4f}")
        chain_rows.append({"arity": a, "depth": DEPTH, **r})

    # ---- Experiment 3: balanced tree, same depth, different fan-in ----
    print("\n" + "=" * 72)
    print("Experiment 3 — Balanced MAJn tree, depth 3")
    print("=" * 72)
    print(f"{'Arity':>5} | {'N_in':>4} {'N_gates':>7} {'FC%':>6} {'AvgDP':>7}")
    tree_rows = []
    TREE_DEPTH = 3
    for a in arities:
        text = gen_balanced_tree(a, TREE_DEPTH)
        save_blif(f"maj{a}_tree_d{TREE_DEPTH}", text)
        r = run_campaign(text)
        print(f"{a:>5} | {r['n_inputs']:>4} {r['n_gates']:>7} "
              f"{r['fault_coverage']:>6.2f} {r['avg_det_prob']:>7.4f}")
        tree_rows.append({"arity": a, "depth": TREE_DEPTH, **r})

    # ---- Final summary ----
    print("\n" + "=" * 72)
    print("Summary — MAJ-arity vs fault propagation")
    print("=" * 72)
    print(f"{'':5} {'Single':>10} {'Chain':>20} {'Tree':>20}")
    print(f"{'Arity':5} {'mask(thy)':>10} {'FC%':>8} {'AvgDP':>8} {'FC%':>8} {'AvgDP':>8} {'AvgBW':>5}")
    print("-" * 72)
    for a, sr, cr, tr in zip(arities, single_rows, chain_rows, tree_rows):
        print(
            f"{a:5} {sr['theory_mask']:>10.4f} "
            f"{cr['fault_coverage']:>8.2f} {cr['avg_det_prob']:>8.4f} "
            f"{tr['fault_coverage']:>8.2f} {tr['avg_det_prob']:>8.4f} {tr['avg_breadth']:>5.2f}"
        )

    # Save JSON
    results = {
        "single":    single_rows,
        "chain":     chain_rows,
        "tree":      tree_rows,
        "params": {
            "chain_depth": DEPTH,
            "tree_depth":  TREE_DEPTH,
        },
    }
    (out_dir / "majN_fault_study.json").write_text(json.dumps(results, indent=2))
    print(f"\nResults: {out_dir / 'majN_fault_study.json'}")
    print(f"BLIFs:   {out_dir}/maj*_*.blif")


if __name__ == "__main__":
    main()
