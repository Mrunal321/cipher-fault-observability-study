#!/usr/bin/env python3
"""
run_fault_coverage.py - Single-bit-flip fault coverage for AOIG and MIG.

For each circuit and each flow we inject every single-bit-flip fault at every
gate-output wire and measure how many of those faults are observable at the
primary outputs on at least one test vector.

Metrics reported per (circuit, flow):
  total_faults   — injectable fault sites (gate output wires)
  detectable     — faults visible on >= 1 test vector
  fault_coverage — detectable / total_faults * 100 %
  masked         — faults invisible on every test vector (majority-gate masking)
  masking_rate   — masked / total_faults * 100 %
  avg_breadth    — mean # output bits flipped per (detectable fault, detecting vector)
  avg_det_prob   — mean fraction of test vectors that detect a fault
                   (given it is detectable at all)

Fault model: BIT_FLIP — flip the gate output value on that wire.
Test vectors:  exhaustive for n_inputs <= 20  (up to 1 M vectors)
               10 000 random samples otherwise
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from fault.dfa.blif_parser import Circuit, parse_blif_file

# ---------------------------------------------------------------------------
# Circuit list
# ---------------------------------------------------------------------------

CIRCUITS = [
    # name,              raw BLIF path (under data/cipher_blif)
    ("present_sbox",    "present/present_sbox.blif"),
    ("gift_sbox",       "gift/gift_sbox.blif"),
    ("prince_sbox",     "prince/prince_sbox.blif"),
    ("prince_sbox_inv", "prince/prince_sbox_inv.blif"),
    ("gift_subcells",   "gift/gift_subcells.blif"),
    ("gift_round",      "gift/gift_round.blif"),
    ("present_round",   "present/present_round.blif"),
    ("prince_mprime",   "prince/prince_mprime.blif"),
    ("simon32_round",   "simon/simon32_round.blif"),
    ("simon64_round",   "simon/simon64_round.blif"),
    ("keccak_chi_5bit", "keccak/keccak_chi_5bit.blif"),
    ("keccak_chi_64row","keccak/keccak_chi_64row.blif"),
    ("speckey_box",     "arx/speckey_box.blif"),
    ("speck32_round",   "arx/speck32_round.blif"),
    ("marx2_box",       "arx/marx2_box.blif"),
]

BENCH_DIR = REPO / "results" / "fpga_benchmark"
BLIF_DIR  = REPO / "data" / "cipher_blif"

EXHAUSTIVE_LIMIT = 20   # use 2^n if n_inputs <= this
N_RANDOM         = 10_000
SEED             = 42

# ---------------------------------------------------------------------------
# Numpy-vectorised gate simulator
# ---------------------------------------------------------------------------

def _build_lut(gate) -> np.ndarray:
    """Pre-compute a 2^k output lookup table for a gate with k inputs."""
    k = len(gate.inputs)
    if k == 0:
        val = gate.cover[0][1] if gate.cover else 0
        return np.array([val], dtype=np.uint8)
    size = 1 << k
    lut = np.zeros(size, dtype=np.uint8)
    for cube, out_val in gate.cover:
        for idx in range(size):
            ok = True
            for j, ch in enumerate(cube):
                bit = (idx >> (k - 1 - j)) & 1
                if ch == "1" and bit != 1:
                    ok = False; break
                if ch == "0" and bit != 0:
                    ok = False; break
            if ok:
                lut[idx] = out_val
    return lut


def build_luts(circuit: Circuit) -> Dict[str, np.ndarray]:
    return {g.output: _build_lut(g) for g in circuit.gates}


def sim_vectorized(
    circuit: Circuit,
    luts: Dict[str, np.ndarray],
    input_matrix: np.ndarray,          # (N, n_inputs) uint8
    overrides: Optional[Dict[str, np.ndarray]] = None,  # signal -> (N,) uint8
) -> Dict[str, np.ndarray]:
    """
    Simulate circuit on N test vectors simultaneously.
    overrides: forced signal values (applied after the gate that drives it fires).
    Returns: dict signal -> (N,) uint8 value array.
    """
    N = input_matrix.shape[0]
    sig: Dict[str, np.ndarray] = {}

    for j, name in enumerate(circuit.inputs):
        sig[name] = input_matrix[:, j]

    if overrides:
        for name, v in overrides.items():
            if name in circuit.inputs:
                sig[name] = v

    for gate in circuit.topo_order():
        k = len(gate.inputs)
        lut = luts[gate.output]

        if k == 0:
            sig[gate.output] = np.full(N, lut[0], dtype=np.uint8)
        else:
            idx = np.zeros(N, dtype=np.int32)
            for inp in gate.inputs:
                idx = (idx << 1) | sig.get(inp, np.zeros(N, dtype=np.uint8)).astype(np.int32)
            val = lut[idx]
            if overrides and gate.output in overrides:
                val = overrides[gate.output]
            sig[gate.output] = val

    return sig


def output_matrix(circuit: Circuit, sig: Dict[str, np.ndarray]) -> np.ndarray:
    """Stack primary output arrays into (N, n_outputs) uint8."""
    return np.stack([sig[o] for o in circuit.outputs], axis=1)

# ---------------------------------------------------------------------------
# Test vector generation
# ---------------------------------------------------------------------------

def make_test_vectors(n_inputs: int, rng: random.Random) -> np.ndarray:
    """Return (N, n_inputs) uint8 test matrix."""
    if n_inputs <= EXHAUSTIVE_LIMIT:
        N = 1 << n_inputs
        mat = np.zeros((N, n_inputs), dtype=np.uint8)
        for i in range(N):
            for j in range(n_inputs):
                mat[i, j] = (i >> (n_inputs - 1 - j)) & 1
        return mat
    # Random sampling
    N = N_RANDOM
    mat = np.zeros((N, n_inputs), dtype=np.uint8)
    for i in range(N):
        v = rng.getrandbits(n_inputs)
        for j in range(n_inputs):
            mat[i, j] = (v >> (n_inputs - 1 - j)) & 1
    return mat

# ---------------------------------------------------------------------------
# Fault campaign
# ---------------------------------------------------------------------------

def run_fault_campaign(
    circuit: Circuit,
    test_matrix: np.ndarray,
) -> Dict[str, Any]:
    """
    Run single-bit-flip campaign on all gate outputs.
    Returns metrics dict.
    """
    luts   = build_luts(circuit)
    N      = test_matrix.shape[0]
    n_outs = len(circuit.outputs)

    # Fault-free simulation
    ff_sig = sim_vectorized(circuit, luts, test_matrix)
    ff_out = output_matrix(circuit, ff_sig)  # (N, n_outs)

    total     = 0
    detectable = 0
    total_breadth   = 0.0
    total_det_pairs = 0
    total_det_prob  = 0.0
    n_detectable_faults = 0

    for gate in circuit.gates:
        fault_sig = gate.output
        correct_vals = ff_sig[fault_sig]  # (N,) uint8

        # Flipped value for each vector
        flipped = (correct_vals ^ 1).astype(np.uint8)

        # Re-simulate with the fault injected at this gate's output
        faulty_sig = sim_vectorized(
            circuit, luts, test_matrix,
            overrides={fault_sig: flipped},
        )
        faulty_out = output_matrix(circuit, faulty_sig)  # (N, n_outs)

        # Hamming distance per vector (number of output bits that differ)
        diff = (faulty_out != ff_out)                    # (N, n_outs) bool
        per_vector_dist = diff.sum(axis=1)               # (N,) int

        detecting = per_vector_dist > 0                  # (N,) bool
        n_detect  = detecting.sum()

        total += 1
        if n_detect > 0:
            detectable += 1
            # Breadth: mean output bits affected across detecting vectors only
            total_breadth   += diff[detecting].sum() / n_detect
            total_det_pairs += n_detect
            total_det_prob  += n_detect / N
            n_detectable_faults += 1

    masked = total - detectable
    fc     = 100.0 * detectable / total if total else 0.0
    mr     = 100.0 * masked     / total if total else 0.0
    avg_br = total_breadth / n_detectable_faults if n_detectable_faults else 0.0
    avg_dp = total_det_prob / n_detectable_faults if n_detectable_faults else 0.0

    return {
        "total_faults":    total,
        "detectable":      detectable,
        "masked":          masked,
        "fault_coverage":  round(fc,  2),
        "masking_rate":    round(mr,  2),
        "avg_breadth":     round(avg_br, 4),
        "avg_det_prob":    round(avg_dp, 4),
        "n_test_vectors":  N,
    }

# ---------------------------------------------------------------------------
# BLIF path resolution
# ---------------------------------------------------------------------------

def blif_paths(name: str) -> Dict[str, Path]:
    d = BENCH_DIR / name
    return {
        "aoig": d / f"{name}_aoig.blif",
        "mig":  d / f"{name}_mig_maj_opt.blif",
    }

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Fault coverage: AOIG vs MIG")
    p.add_argument("--out-dir", default="results/fault_coverage",
                   help="Output directory")
    p.add_argument("--circuits", nargs="+",
                   help="Restrict to specific circuit names")
    p.add_argument("--no-aoig", action="store_true",
                   help="Skip AOIG flow (different gate granularity)")
    return p.parse_args()


def main():
    args = parse_args()
    out_dir = REPO / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)
    if args.circuits:
        known = {name for name, _ in CIRCUITS}
        unknown = sorted(set(args.circuits) - known)
        if unknown:
            raise SystemExit(
                "Unknown circuit(s): "
                + ", ".join(unknown)
                + "\nKnown circuits: "
                + ", ".join(name for name, _ in CIRCUITS)
            )

    circuits = [c for c in CIRCUITS
                if args.circuits is None or c[0] in args.circuits]

    all_results = []

    # Header
    hdr = (f"{'Circuit':<22} {'Flow':<6} | {'N_gates':>7} {'Det':>6} "
           f"{'FC%':>7} {'Masked%':>8} {'AvgBW':>7} {'AvgDP':>7}")
    sep = "-" * len(hdr)
    print()
    print(hdr)
    print(sep)

    for name, raw_blif_rel in circuits:
        paths = blif_paths(name)
        flows = ["aoig", "mig"] if not args.no_aoig else ["mig"]
        circ_results: Dict[str, Any] = {"circuit": name, "flows": {}}

        last_flow_printed = False
        for flow in flows:
            blif_p = paths[flow]
            if not blif_p.exists():
                print(f"{name:<22} {flow.upper():<6} | SKIP (no BLIF: {blif_p.name})")
                continue

            circuit = parse_blif_file(str(blif_p))
            n_in    = len(circuit.inputs)
            test_mat = make_test_vectors(n_in, rng)

            metrics = run_fault_campaign(circuit, test_mat)

            label = name if not last_flow_printed else ""
            print(
                f"{label:<22} {flow.upper():<6} | "
                f"{metrics['total_faults']:>7} {metrics['detectable']:>6} "
                f"{metrics['fault_coverage']:>7.2f} {metrics['masking_rate']:>8.2f} "
                f"{metrics['avg_breadth']:>7.4f} {metrics['avg_det_prob']:>7.4f}"
            )
            last_flow_printed = True

            circ_results["flows"][flow] = metrics

            # Per-circuit JSON
            circ_json = out_dir / f"{name}_{flow}_fault.json"
            circ_json.write_text(json.dumps(metrics, indent=2))

        all_results.append(circ_results)
        print()

    # Full runs update the canonical aggregate file. Restricted smoke tests
    # write a subset aggregate so they cannot leave the artifact half-populated.
    if args.circuits is None and not args.no_aoig:
        results_path = out_dir / "fault_coverage_results.json"
    else:
        slug = "_".join(args.circuits or ["all"])
        if len(slug) > 80:
            slug = "subset"
        suffix = "_no_aoig" if args.no_aoig else ""
        results_path = out_dir / f"fault_coverage_results_{slug}{suffix}.json"
    results_path.write_text(json.dumps(all_results, indent=2))

    print()
    print(f"Results saved to: {results_path}")


if __name__ == "__main__":
    main()
