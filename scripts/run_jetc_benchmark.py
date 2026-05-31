#!/usr/bin/env python3
"""
run_jetc_benchmark.py — AOIG vs MIG vs mMIG paper-style benchmark.

Runs 15 cipher/S-box circuits through three synthesis flows and produces a
comparison table matching the JETC paper format (Tables 2-7):

  Structural: Gates, Inv (inverted edges), MIN nodes
  FPGA:       Synth LUT, Logic Levels, Impl LUT, Delay ns, Logic ns, Route ns
  Power:      Logic mW, Signal mW, Dyn mW

Flows:
  AOIG  — raw BLIF → yosys AIG → Vivado  (And-Inverter Graph baseline)
  MIG   — blif2mig_2 depth-MIG → Vivado
  mMIG  — blif2mig_2 chain-mMIG (depth-MIG → identity-mMIG) → Vivado

Usage:
  python3 scripts/run_jetc_benchmark.py \\
      --binary /path/to/blif2mig_2 \\
      [--out-dir results/fpga_benchmark] \\
      [--no-vivado]          skip Vivado (structural metrics only)
      [--circuits present_sbox gift_sbox ...]   override circuit list
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

BLIF_DIR = REPO / "data" / "cipher_blif"
VIVADO_TCL = REPO / "vivado" / "run_metrics.tcl"
PART = "xc7s100fgga676-2"
CLK_PERIOD_NS = 10.0   # 10 ns = 100 MHz; cipher is combinational, clock just anchors timing

# ---------------------------------------------------------------------------
# Benchmark circuit list
# ---------------------------------------------------------------------------
# (relative to BLIF_DIR)
DEFAULT_CIRCUITS: List[str] = [
    # 4-bit S-boxes (XOR-heavy, best mMIG candidates)
    "present/present_sbox.blif",
    "gift/gift_sbox.blif",
    "prince/prince_sbox.blif",
    "prince/prince_sbox_inv.blif",
    # Round functions / primitives
    "gift/gift_subcells.blif",     # 16× 4-bit S-box in parallel
    "gift/gift_round.blif",
    "present/present_round.blif",
    "prince/prince_mprime.blif",   # PRINCE M' (XOR-heavy linear layer)
    # SIMON (AND-rotation-XOR structure)
    "simon/simon32_round.blif",
    "simon/simon64_round.blif",
    # Keccak χ (NOT-AND; benefits from minority complement)
    "keccak/keccak_chi_5bit.blif",
    "keccak/keccak_chi_64row.blif",
    # ARX ciphers
    "arx/speck32_round.blif",
    "arx/speckey_box.blif",
    "arx/marx2_box.blif",
    # Note: aes_sbox (8-input tables) and prince_subcells (.subckt) skipped
    # — blif2mig_2 cannot handle them without pre-processing
]

# ---------------------------------------------------------------------------
# blif2mig_2 invocation helpers
# ---------------------------------------------------------------------------

def _parse_network_block(text: str, header: str) -> Dict[str, Any]:
    """
    Extract Gate/Inv/Depth stats from a blif2mig_2 output section.
    header examples: 'Optimized MIG', 'Optimized mMIG', 'Original MIG'
    """
    result: Dict[str, Any] = {}
    # Find the section
    pat = re.compile(
        r"===\s*" + re.escape(header) + r"\s*===\s*\n"
        r"PIs=(\d+)\s+POs=(\d+)\s+Gates=(\d+)\s+Depth=(\d+)\s*\n"
        r"GateTypes:\s*MAJ=(\d+)\s+MIN=(\d+).*?\n"
        r".*?InvEdges\(total\)=(\d+)",
        re.S,
    )
    m = pat.search(text)
    if m:
        result["pis"]   = int(m.group(1))
        result["pos"]   = int(m.group(2))
        result["gates"] = int(m.group(3))
        result["depth"] = int(m.group(4))
        result["maj"]   = int(m.group(5))
        result["min"]   = int(m.group(6))
        result["inv"]   = int(m.group(7))
    return result


def run_mig(blif_in: Path, out_base: Path) -> Tuple[Optional[Path], Dict[str, Any]]:
    """Run area-MIG optimization. Returns (output_blif, stats_dict)."""
    cmd = [
        str(BINARY), str(blif_in), str(out_base),
        "--mode=area",
        "--mig-flow=dac19_compat",
    ]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0

    out_blif = Path(str(out_base) + "_maj_opt.blif")
    # Also parse the pre-optimization stats as AOIG baseline
    aoig_stats = _parse_network_block(r.stdout + r.stderr, "Original MIG")
    mig_stats = _parse_network_block(r.stdout + r.stderr, "Optimized MIG")
    mig_stats["runtime_s"] = elapsed
    mig_stats["ok"] = r.returncode == 0 and out_blif.exists()
    if not mig_stats["ok"]:
        mig_stats["error"] = (r.stderr or r.stdout)[-500:]
    return (out_blif if mig_stats["ok"] else None), mig_stats, aoig_stats


def run_mmig_direct(blif_in: Path, out_base: Path) -> Tuple[Optional[Path], Dict[str, Any]]:
    """
    Direct single-pass mMIG optimization from the original BLIF.
    Uses area mode so gate count cannot increase — matches the paper's
    standard AOIG→mMIG comparison methodology.
    compress2rs mMIG flow: robust across all cipher families.
    """
    cmd = [
        str(BINARY), str(blif_in), str(out_base),
        "--mode=area",
        "--mig-flow=dac19_compat",
        "--enable-mmig",
        "--mmig-cec",
        "--mmig-advanced",
        "--mmig-flow=compress2rs",
        "--mmig-advanced-rounds=3",
        "--mmig-seed=both",
        "--mmig-seed-budget=200",
        "--mmig-seed-rounds=3",
    ]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0

    out_blif = Path(str(out_base) + "_mmig_opt.blif")
    stats = _parse_network_block(r.stdout + r.stderr, "Optimized mMIG")
    stats["runtime_s"] = elapsed
    stats["ok"] = r.returncode == 0 and out_blif.exists()
    if not stats["ok"]:
        stats["error"] = (r.stderr or r.stdout)[-500:]
    return (out_blif if stats["ok"] else None), stats


# ---------------------------------------------------------------------------
# AOIG (And-Inverter Graph) baseline
# ---------------------------------------------------------------------------
# We use blif2mig_2's "Original MIG" stats as the AOIG baseline.
# This is the circuit as read from BLIF before any optimization — it represents
# the input network structure and gives a fair pre-optimization comparison point.
# For Vivado AOIG, we run on the raw input BLIF (converted directly to Verilog).

def parse_raw_blif_stats(blif_path: Path) -> Dict[str, Any]:
    """Count PI/PO/gates from a raw BLIF (truth-table format)."""
    text = blif_path.read_text()
    pis = pos = gates = 0
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(".inputs"):
            pis += len(s.split()) - 1
        elif s.startswith(".outputs"):
            pos += len(s.split()) - 1
        elif s.startswith(".names"):
            n_inputs = len(s.split()) - 2   # .names + N inputs + 1 output
            if n_inputs >= 1:
                gates += 1
    return {"pis": pis, "pos": pos, "gates": gates, "inv": 0,
            "maj": 0, "min": 0, "depth": 0}


# ---------------------------------------------------------------------------
# Vivado measurement
# ---------------------------------------------------------------------------

def _which_vivado() -> Optional[str]:
    p = shutil.which("vivado")
    if p:
        return p
    for base in ("/tools/Xilinx", "/opt/Xilinx", "/usr/local/Xilinx"):
        bp = Path(base) / "Vivado"
        if not bp.is_dir():
            continue
        for v in sorted(bp.iterdir(), reverse=True):
            vb = v / "bin" / "vivado"
            if vb.exists():
                return str(vb)
    return None


def blif_to_verilog_wrapper(blif_path: Path, out_v: Path, top: str = "top",
                            direct_v: Optional[Path] = None) -> None:
    """Wrap a Verilog netlist in I/O flip-flop registers for Vivado timing.

    If direct_v is given (blif2mig_2 gate-level .v), uses it as the core instead
    of running yosys — this preserves the MAJ/MIN gate structure for Vivado.
    Otherwise converts BLIF → Verilog via yosys.
    """
    if direct_v and direct_v.exists():
        raw = direct_v.read_text()
    else:
        yosys = shutil.which("yosys")
        if not yosys:
            raise RuntimeError("yosys not found")
        tmp_v = out_v.with_suffix(".raw.v")
        script = f"read_blif {blif_path}; write_verilog {tmp_v}"
        r = subprocess.run([yosys, "-q", "-p", script], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"yosys failed: {r.stderr}")
        raw = tmp_v.read_text()
        tmp_v.unlink(missing_ok=True)

    # blif2mig_2 names the module "top"; yosys uses the BLIF model name.
    # Rename to cipher_core so our wrapper can use "top" as the outer module.
    m = re.search(r"module\s+\\?(\w+)\s*\(([^)]*)\)", raw)
    if not m:
        raise RuntimeError("no module declaration found in Verilog")
    raw = raw.replace(m.group(1), "cipher_core", 1)

    # Handle both yosys style ("input a;") and blif2mig_2 style ("input a, b, c;")
    inputs: List[str] = []
    for m2 in re.finditer(r"^\s*input\s+([\w\s,]+);", raw, re.M):
        inputs.extend(tok.strip().lstrip("\\") for tok in re.split(r"[\s,]+", m2.group(1)) if tok.strip())
    outputs: List[str] = []
    for m2 in re.finditer(r"^\s*output\s+([\w\s,]+);", raw, re.M):
        outputs.extend(tok.strip().lstrip("\\") for tok in re.split(r"[\s,]+", m2.group(1)) if tok.strip())
    if not inputs or not outputs:
        raise RuntimeError("no inputs/outputs found in Verilog")

    port_list    = ", ".join(["clk"] + inputs + outputs)
    pi_decls     = "\n".join(f"  input  {p};" for p in inputs)
    po_decls     = "\n".join(f"  output reg {p};" for p in outputs)
    pi_regs      = "  reg " + ", ".join(f"{p}_r" for p in inputs) + ";"
    po_wires     = "  wire " + ", ".join(f"{p}_w" for p in outputs) + ";"
    pi_assigns   = "\n".join(f"    {p}_r <= {p};" for p in inputs)
    po_assigns   = "\n".join(f"    {p} <= {p}_w;" for p in outputs)
    core_inst_pi = ", ".join(f".{p}({p}_r)" for p in inputs)
    core_inst_po = ", ".join(f".{p}({p}_w)" for p in outputs)

    wrapper = f"""
module {top}({port_list});
  input clk;
{pi_decls}
{po_decls}
{pi_regs}
{po_wires}

  always @(posedge clk) begin
{pi_assigns}
{po_assigns}
  end

  cipher_core u_core({core_inst_pi}, {core_inst_po});
endmodule
"""
    out_v.write_text(raw + wrapper)


SKIP_EXISTING: bool = False   # set from args


def run_vivado_metrics(blif_path: Path, out_dir: Path, label: str,
                       direct_v: Optional[Path] = None) -> Dict[str, Any]:
    """
    Convert BLIF to Verilog, run Vivado with run_metrics.tcl, return parsed JSON.
    Returns dict with keys: synth_luts, logic_levels, impl_luts, delay_ns, etc.
    On failure returns dict with 'error' key.
    """
    vivado = _which_vivado()
    if not vivado:
        return {"error": "vivado not found"}

    out_dir.mkdir(parents=True, exist_ok=True)
    verilog = out_dir / f"{label}.v"
    json_out = out_dir / f"{label}_metrics.json"
    log_out  = out_dir / f"{label}_vivado.log"

    if SKIP_EXISTING and json_out.exists():
        try:
            return json.loads(json_out.read_text())
        except json.JSONDecodeError:
            pass  # fall through to re-run

    try:
        blif_to_verilog_wrapper(blif_path, verilog, direct_v=direct_v)
    except RuntimeError as e:
        return {"error": str(e)}

    args = [
        vivado, "-mode", "batch", "-nojournal", "-nolog",
        "-source", str(VIVADO_TCL),
        "-tclargs",
        "--verilog", str(verilog),
        "--top", "top",
        "--part", PART,
        "--period", str(CLK_PERIOD_NS),
        "--out-json", str(json_out),
    ]

    with tempfile.TemporaryDirectory(prefix="vivado_metrics_") as td:
        with open(log_out, "w") as lf:
            r = subprocess.run(
                args, cwd=td, stdout=lf, stderr=subprocess.STDOUT,
                text=True, timeout=600,
            )

    if r.returncode != 0 or not json_out.exists():
        return {"error": f"vivado rc={r.returncode}; see {log_out}"}

    try:
        return json.loads(json_out.read_text())
    except json.JSONDecodeError as e:
        return {"error": f"bad JSON: {e}"}


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

_HEADER = (
    f"{'Circuit':<22} {'Flow':<6} | "
    f"{'Gates':>6} {'Inv':>5} {'MIN':>4} | "
    f"{'SLUTs':>6} {'Lvls':>5} {'ILUTs':>6} | "
    f"{'Delay':>7} {'Logic':>6} {'Route':>6} | "
    f"{'Dyn mW':>7}"
)
_SEP = "-" * len(_HEADER)


def _fmt_row(label: str, flow: str, s: Dict[str, Any], v: Dict[str, Any]) -> str:
    def _f(d: Dict, k: str, fmt: str = "") -> str:
        val = d.get(k)
        if val is None or val == "":
            return "—"
        if fmt:
            return format(float(val), fmt)
        return str(val)

    gates = _f(s, "gates")
    inv   = _f(s, "inv")
    minn  = _f(s, "min")
    slut  = _f(v, "synth_luts")
    lvls  = _f(v, "logic_levels")
    ilut  = _f(v, "impl_luts")
    dly   = _f(v, "delay_ns",  ".3f")
    lgns  = _f(v, "logic_ns",  ".3f")
    rtns  = _f(v, "route_ns",  ".3f")
    dyn   = _f(v, "dynamic_power_mw", ".2f")

    return (
        f"{label:<22} {flow:<6} | "
        f"{gates:>6} {inv:>5} {minn:>4} | "
        f"{slut:>6} {lvls:>5} {ilut:>6} | "
        f"{dly:>7} {lgns:>6} {rtns:>6} | "
        f"{dyn:>7}"
    )


def print_table(rows: List[Dict]) -> None:
    print()
    print(_HEADER)
    print(_SEP)
    last_circuit = None
    for row in rows:
        if last_circuit and row["circuit"] != last_circuit:
            print()
        last_circuit = row["circuit"]
        print(_fmt_row(
            row["circuit"], row["flow"],
            row.get("struct", {}),
            row.get("vivado", {}),
        ))
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

BINARY: Path = Path("")   # set from --binary arg


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="AOIG vs MIG vs mMIG paper-style benchmark.",
    )
    p.add_argument("--binary", required=True,
                   help="Path to compiled blif2mig_2 binary")
    p.add_argument("--out-dir", default="results/fpga_benchmark",
                   help="Output directory for optimized BLIFs and Vivado results")
    p.add_argument("--no-vivado", action="store_true",
                   help="Skip Vivado; report structural metrics only")
    p.add_argument("--circuits", nargs="+",
                   help="Override circuit list (relative paths under data/cipher_blif/)")
    p.add_argument("--flows", nargs="+", choices=["aoig", "mig", "mmig"],
                   default=["aoig", "mig", "mmig"],
                   help="Which flows to run")
    p.add_argument("--skip-existing", action="store_true",
                   help="Skip Vivado runs where the metric JSON already exists")
    return p.parse_args()


def main() -> None:
    global BINARY, SKIP_EXISTING

    args = parse_args()
    BINARY = Path(args.binary)
    SKIP_EXISTING = args.skip_existing
    if not BINARY.exists():
        sys.exit(f"ERROR: binary not found: {BINARY}")

    out_dir = REPO / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    circuits = args.circuits or DEFAULT_CIRCUITS
    do_vivado = not args.no_vivado and (_which_vivado() is not None)
    if not args.no_vivado and not do_vivado:
        print("WARN: Vivado not found; running structural metrics only.")

    all_rows: List[Dict] = []
    json_results: List[Dict] = []

    for circ_rel in circuits:
        blif_in = BLIF_DIR / circ_rel
        if not blif_in.exists():
            print(f"SKIP: {circ_rel} — file not found")
            continue

        label = blif_in.stem  # e.g. "present_sbox"
        circ_dir = out_dir / label
        circ_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"Circuit: {label}  ({circ_rel})")
        print(f"{'='*60}")

        aoig_struct: Dict[str, Any] = {}
        aoig_vivado: Dict[str, Any] = {}
        mig_blif: Optional[Path] = None
        mig_struct: Dict[str, Any] = {}
        mig_vivado: Dict[str, Any] = {}
        mmig_blif: Optional[Path] = None
        mmig_struct: Dict[str, Any] = {}
        mmig_vivado: Dict[str, Any] = {}

        # ---- MIG (also captures AOIG pre-opt stats) ----
        if "mig" in args.flows or "aoig" in args.flows:
            print(f"  [MIG]  running blif2mig_2 depth optimization…")
            mig_blif, mig_struct, aoig_struct = run_mig(blif_in, circ_dir / f"{label}_mig")
            if mig_struct.get("ok") is False:
                print(f"    WARN: blif2mig_2 MIG failed: {mig_struct.get('error', '')[:120]}")

        # ---- AOIG Vivado (raw input BLIF → Verilog, no MIG optimization) ----
        if "aoig" in args.flows and do_vivado:
            print(f"  [AOIG] running Vivado on raw BLIF…")
            aoig_vivado = run_vivado_metrics(blif_in, circ_dir / "aoig", label + "_aoig")
            if "error" in aoig_vivado:
                print(f"    WARN: Vivado AOIG failed: {aoig_vivado['error'][:120]}")

        # ---- MIG Vivado ----
        if "mig" in args.flows and mig_blif and do_vivado:
            print(f"  [MIG]  running Vivado (gate-level .v)…")
            mig_v = mig_blif.with_suffix(".v")  # blif2mig_2 writes _maj_opt.v alongside _maj_opt.blif
            mig_vivado = run_vivado_metrics(mig_blif, circ_dir / "mig", label + "_mig",
                                            direct_v=mig_v if mig_v.exists() else None)
            if "error" in mig_vivado:
                print(f"    WARN: Vivado MIG failed: {mig_vivado['error'][:120]}")

        # ---- mMIG (direct single-pass, same input as MIG) ----
        if "mmig" in args.flows:
            print(f"  [mMIG] running direct mMIG optimization…")
            mmig_blif, mmig_struct = run_mmig_direct(blif_in, circ_dir / f"{label}_mmig")
            if mmig_struct.get("ok") is False:
                print(f"    WARN: blif2mig_2 mMIG failed: {mmig_struct.get('error', '')[:120]}")
            if mmig_blif and do_vivado:
                print(f"  [mMIG] running Vivado (gate-level .v)…")
                mmig_v = mmig_blif.with_suffix(".v")  # blif2mig_2 writes _mmig_opt.v
                mmig_vivado = run_vivado_metrics(mmig_blif, circ_dir / "mmig", label + "_mmig",
                                                 direct_v=mmig_v if mmig_v.exists() else None)
                if "error" in mmig_vivado:
                    print(f"    WARN: Vivado mMIG failed: {mmig_vivado['error'][:120]}")

        if "aoig" in args.flows:
            all_rows.append({"circuit": label, "flow": "AOIG",
                             "struct": aoig_struct, "vivado": aoig_vivado})
        if "mig" in args.flows:
            all_rows.append({"circuit": label, "flow": "MIG",
                             "struct": mig_struct, "vivado": mig_vivado})
        if "mmig" in args.flows:
            all_rows.append({"circuit": label, "flow": "mMIG",
                             "struct": mmig_struct, "vivado": mmig_vivado})

        # Save per-circuit JSON
        json_results.append({
            "circuit": label,
            "circuit_rel": circ_rel,
            "aoig": {"struct": aoig_struct, "vivado": aoig_vivado},
            "mig":  {"struct": mig_struct,  "vivado": mig_vivado},
            "mmig": {"struct": mmig_struct, "vivado": mmig_vivado},
        })

    # Print table
    print_table(all_rows)

    # Save full results JSON
    results_json = out_dir / "jetc_results.json"
    results_json.write_text(json.dumps(json_results, indent=2))
    print(f"Results saved to: {results_json}")

    # Print delta summary (mMIG vs MIG)
    print_delta_summary(all_rows)


def print_delta_summary(rows: List[Dict]) -> None:
    print("\n=== mMIG vs MIG delta summary ===")
    print(f"{'Circuit':<22}  {'ΔGates':>8}  {'ΔInv':>8}  {'ΔSLUT':>8}  {'ΔDelay':>8}  MIN")
    print("-" * 70)

    mig_map  = {r["circuit"]: r for r in rows if r["flow"] == "MIG"}
    mmig_map = {r["circuit"]: r for r in rows if r["flow"] == "mMIG"}

    for circ in sorted(mig_map.keys()):
        if circ not in mmig_map:
            continue
        mg = mig_map[circ]["struct"]
        mm = mmig_map[circ]["struct"]
        mv = mig_map[circ]["vivado"]
        mmv = mmig_map[circ]["vivado"]

        def pct(a, b, key):
            va, vb = a.get(key), b.get(key)
            if va is None or vb is None or va == 0:
                return "—"
            return f"{(vb - va) / va * 100:+.1f}%"

        def abs_delta(a, b, key):
            va, vb = a.get(key), b.get(key)
            if va is None or vb is None:
                return "—"
            return f"{vb - va:+.3f}" if isinstance(va, float) else f"{vb - va:+d}"

        dg   = pct(mg, mm, "gates")
        di   = pct(mg, mm, "inv")
        ds   = pct(mv, mmv, "synth_luts")
        dd   = abs_delta(mv, mmv, "delay_ns")
        minn = mm.get("min", "—")
        print(f"{circ:<22}  {dg:>8}  {di:>8}  {ds:>8}  {dd:>8}  {minn}")


if __name__ == "__main__":
    main()
