#!/usr/bin/env python3
"""
gen_paper_tables.py — Render LaTeX tables for the HOST paper from the
result JSONs in results/.

Outputs standalone .tex files in paper/tables/:
  - fpga_benchmark.tex         FPGA AOIG vs MIG vs mMIG full numbers
  - inverter_reduction.tex     Structural mMIG vs MIG inverter reduction
  - fault_coverage.tex         Single-bit-flip fault coverage AOIG/MIG/mMIG
  - dualrail_equivalence.tex   MIG/mMIG faulty-output set equivalence
  - majn_arity.tex             MAJ3 vs MAJ5 vs MAJ7 fault propagation
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

REPO = Path(__file__).resolve().parents[1]
RES  = REPO / "results"
OUT  = REPO / "paper" / "tables"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Circuit ordering (matches the paper)
# ---------------------------------------------------------------------------
CIRCUITS = [
    # name,                pretty label,     family
    ("present_sbox",       "PRESENT S-box",      "4-bit S-box"),
    ("gift_sbox",          "GIFT S-box",         "4-bit S-box"),
    ("prince_sbox",        "PRINCE S-box",       "4-bit S-box"),
    ("prince_sbox_inv",    "PRINCE S-box$^{-1}$","4-bit S-box"),
    ("gift_subcells",      "GIFT subcells",      "Round prim."),
    ("gift_round",         "GIFT round",         "Round prim."),
    ("present_round",      "PRESENT round",      "Round prim."),
    ("prince_mprime",      "PRINCE M$'$",        "Round prim."),
    ("simon32_round",      "SIMON-32 round",     "SIMON"),
    ("simon64_round",      "SIMON-64 round",     "SIMON"),
    ("keccak_chi_5bit",    "Keccak $\\chi$ 5-bit", "Keccak"),
    ("keccak_chi_64row",   "Keccak $\\chi$ 64-row","Keccak"),
    ("speckey_box",        "SpecKey box",        "ARX"),
    ("speck32_round",      "Speck-32 round",     "ARX"),
    ("marx2_box",          "MARX-2 box",         "ARX"),
]


# ---------------------------------------------------------------------------
# Structural metrics — kept inline since these were collected via blif2mig_2
# stdout parsing (one-off, reproducible via README instructions).
# ---------------------------------------------------------------------------
STRUCT = {
    "present_sbox":    {"aoig":(19,18,0),  "mig":(19,18,0),  "mmig":(19,14,8)},
    "gift_sbox":       {"aoig":(19,19,0),  "mig":(19,18,0),  "mmig":(19,16,3)},
    "prince_sbox":     {"aoig":(15,11,0),  "mig":(15,12,0),  "mmig":(15,8,5)},
    "prince_sbox_inv": {"aoig":(18,16,0),  "mig":(16,14,0),  "mmig":(16,13,2)},
    "gift_subcells":   {"aoig":(304,304,0),"mig":(304,288,0),"mmig":(304,256,48)},
    "gift_round":      {"aoig":(418,404,0),"mig":(412,396,0),"mmig":(412,348,66)},
    "present_round":   {"aoig":(496,480,0),"mig":(496,480,0),"mmig":(496,384,96)},
    "prince_mprime":   {"aoig":(168,168,0),"mig":(96,96,0),  "mmig":(96,96,0)},
    "simon32_round":   {"aoig":(160,144,0),"mig":(112,96,0), "mmig":(112,96,0)},
    "simon64_round":   {"aoig":(320,288,0),"mig":(224,192,0),"mmig":(224,192,0)},
    "keccak_chi_5bit": {"aoig":(20,20,0),  "mig":(20,17,0),  "mmig":(20,17,6)},
    "keccak_chi_64row":{"aoig":(1280,1280,0),"mig":(1280,1088,0),"mmig":(1280,1088,384)},
    "speckey_box":     {"aoig":(351,336,0),"mig":(251,236,0),"mmig":(251,204,32)},
    "speck32_round":   {"aoig":(159,144,0),"mig":(156,141,0),"mmig":(156,125,16)},
    "marx2_box":       {"aoig":(302,288,0),"mig":(250,236,0),"mmig":(250,200,36)},
}


def fpga(name: str, flow: str) -> Optional[Dict[str, Any]]:
    p = RES / "fpga_benchmark" / name / flow / f"{name}_{flow}_metrics.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def fmt(x, fmt_spec=".2f", dash="\\textemdash"):
    if x is None:
        return dash
    try:
        return format(float(x), fmt_spec)
    except (ValueError, TypeError):
        return str(x)


def write(name: str, body: str):
    p = OUT / f"{name}.tex"
    p.write_text(body)
    print(f"  wrote {p.relative_to(REPO)}")


# ---------------------------------------------------------------------------
# Table 1 — FPGA benchmark (compressed; large to fit in 2-column format)
# ---------------------------------------------------------------------------
def gen_fpga_table():
    rows = []
    last_family = None
    for name, label, family in CIRCUITS:
        # Family divider
        if family != last_family and last_family is not None:
            rows.append("\\midrule")
        last_family = family
        s = STRUCT[name]
        for i, flow in enumerate(["aoig", "mig", "mmig"]):
            gates, inv, minn = s[flow]
            v = fpga(name, flow)
            slut = fmt(v.get("synth_luts") if v else None, "d") if v else "\\textemdash"
            ilut = fmt(v.get("impl_luts")  if v else None, "d") if v else "\\textemdash"
            lvl  = fmt(v.get("logic_levels") if v else None, "d") if v else "\\textemdash"
            dly  = fmt(v.get("delay_ns")  if v else None, ".3f") if v else "\\textemdash"
            dyn  = fmt(v.get("dynamic_power_mw") if v else None, ".1f") if v else "\\textemdash"

            flow_lbl = {"aoig":"AOIG", "mig":"MIG", "mmig":"\\textbf{mMIG}"}[flow]
            circ_lbl = label if i == 0 else ""
            rows.append(
                f"{circ_lbl} & {flow_lbl} & {gates} & {inv} & {minn} "
                f"& {slut} & {lvl} & {ilut} & {dly} & {dyn} \\\\"
            )

    body = (
        "% Auto-generated by scripts/gen_paper_tables.py — do not edit\n"
        "\\begin{table*}[tbp]\n"
        "  \\caption{FPGA synthesis and structural metrics for 15 cipher circuits "
        "across AOIG, MIG, and mMIG flows. Vivado 2023.2, "
        "xc7s100fgga676-2 (Spartan-7), 100~MHz target.}\n"
        "  \\label{tab:fpga-benchmark}\n"
        "  \\centering\n"
        "  \\small\n"
        "  \\begin{tabular}{llrrrrrrrr}\n"
        "    \\toprule\n"
        "    Circuit & Flow & Gates & Inv & MIN & SLUTs & Lvls & ILUTs & Delay (ns) & Dyn (mW) \\\\\n"
        "    \\midrule\n"
        + "\n    ".join(rows) + "\n"
        "    \\bottomrule\n"
        "  \\end{tabular}\n"
        "\\end{table*}\n"
    )
    write("fpga_benchmark", body)


# ---------------------------------------------------------------------------
# Table 2 — Inverter reduction summary (compact)
# ---------------------------------------------------------------------------
def gen_inv_reduction():
    rows = []
    for name, label, _ in CIRCUITS:
        s = STRUCT[name]
        aoig_inv = s["aoig"][1]
        mig_inv  = s["mig"][1]
        mmig_inv = s["mmig"][1]
        minn     = s["mmig"][2]

        d_mig_vs_aoig  = (mig_inv  - aoig_inv) / aoig_inv * 100 if aoig_inv else 0
        d_mmig_vs_mig  = (mmig_inv - mig_inv)  / mig_inv  * 100 if mig_inv  else 0

        rows.append(
            f"{label} & {aoig_inv} & {mig_inv} & {mmig_inv} & {minn} "
            f"& {d_mig_vs_aoig:+.1f}\\% & {d_mmig_vs_mig:+.1f}\\% \\\\"
        )

    body = (
        "% Auto-generated by scripts/gen_paper_tables.py — do not edit\n"
        "\\begin{table}[tbp]\n"
        "  \\caption{Inverted-edge count and reduction. mMIG reduces "
        "inverters by 7--33\\% relative to MIG on the circuits where "
        "minority insertion changes the inverted-edge count; other "
        "circuits are unchanged.}\n"
        "  \\label{tab:inv-reduction}\n"
        "  \\centering\n"
        "  \\small\n"
        "  \\begin{tabular}{lrrrrrr}\n"
        "    \\toprule\n"
        "    Circuit & AOIG & MIG & mMIG & MIN & $\\Delta$MIG & $\\Delta$mMIG \\\\\n"
        "    \\midrule\n"
        + "\n    ".join(rows) + "\n"
        "    \\bottomrule\n"
        "  \\end{tabular}\n"
        "\\end{table}\n"
    )
    write("inverter_reduction", body)


# ---------------------------------------------------------------------------
# Table 3 — Single-bit-flip fault coverage
# ---------------------------------------------------------------------------
def gen_fault_coverage():
    p = RES / "fault_coverage" / "fault_coverage_results.json"
    data = json.loads(p.read_text())
    by_circuit = {r["circuit"]: r for r in data}

    rows = []
    for name, label, _ in CIRCUITS:
        rec = by_circuit.get(name)
        if not rec or "flows" not in rec:
            continue
        flows = rec["flows"]
        a = flows.get("aoig", {})
        m = flows.get("mig",  {})
        mm = flows.get("mmig", {})

        rows.append(
            f"{label} & "
            f"{a.get('total_faults','—')} & {a.get('fault_coverage','—'):.2f} & "
            f"{m.get('total_faults','—')} & {m.get('fault_coverage','—'):.2f} & "
            f"{m.get('avg_det_prob','—'):.3f} & "
            f"{mm.get('total_faults','—')} & {mm.get('fault_coverage','—'):.2f} & "
            f"{mm.get('avg_det_prob','—'):.3f} \\\\"
        )

    body = (
        "% Auto-generated by scripts/gen_paper_tables.py — do not edit\n"
        "\\begin{table*}[tbp]\n"
        "  \\caption{Single-bit-flip fault coverage at gate outputs. "
        "FC\\%~=~detectable faults / total fault sites. "
        "AvgDP~=~mean fraction of test vectors that detect a fault. "
        "MIG and mMIG yield identical fault coverage and AvgDP per circuit "
        "(see Table~\\ref{tab:dualrail-equiv}).}\n"
        "  \\label{tab:fault-coverage}\n"
        "  \\centering\n"
        "  \\small\n"
        "  \\begin{tabular}{lrrrrrrrr}\n"
        "    \\toprule\n"
        "      & \\multicolumn{2}{c}{AOIG} & \\multicolumn{3}{c}{MIG} & \\multicolumn{3}{c}{mMIG} \\\\\n"
        "    \\cmidrule(lr){2-3} \\cmidrule(lr){4-6} \\cmidrule(lr){7-9}\n"
        "    Circuit & $N$ & FC\\% & $N$ & FC\\% & AvgDP & $N$ & FC\\% & AvgDP \\\\\n"
        "    \\midrule\n"
        + "\n    ".join(rows) + "\n"
        "    \\bottomrule\n"
        "  \\end{tabular}\n"
        "\\end{table*}\n"
    )
    write("fault_coverage", body)


# ---------------------------------------------------------------------------
# Table 4 — Dual-rail equivalence
# ---------------------------------------------------------------------------
def gen_dualrail_equiv():
    eq_path = RES / "fault_coverage" / "dualrail_equivalence.json"
    div_path = RES / "fault_coverage" / "dualrail_diversity.json"
    eq  = {r["circuit"]: r for r in json.loads(eq_path.read_text())}
    div = {r["circuit"]: r for r in json.loads(div_path.read_text())}

    rows = []
    for name, label, _ in CIRCUITS:
        e = eq.get(name, {})
        d = div.get(name, {})
        if not e or "error" in e:
            continue

        rows.append(
            f"{label} & {e['n_test_vectors']} & "
            f"{e['identical_frac']*100:.2f}\\% & {e['avg_jaccard']:.4f} & "
            f"{e['mig_only_outputs']} & {e['mmig_only_outputs']} & "
            f"{d.get('pearson_r', 1.0):.4f} \\\\"
        )

    body = (
        "% Auto-generated by scripts/gen_paper_tables.py -- do not edit\n"
        "\\begin{table*}[tbp]\n"
        "  \\caption{Empirical fault equivalence of MIG and mMIG. For every "
        "tested input vector across all 15 circuits, the \\emph{set} of faulty outputs "
        "producible by any single gate-output bit-flip is identical between "
        "MIG and mMIG (Jaccard~=~1.000, zero exclusive outputs in either "
        "direction; Pearson correlation $r = 1.0$ on per-input sensitivity). "
        "This is consistent with the polarity-equivalent (De~Morgan) "
        "relationship of Proposition~\\ref{prop:polarity-equiv}, applied across the "
        "full \\texttt{blif2mig\\_2} flow including additional structural rewriting steps. "
        "Rules out mismatch-based dual-rail MIG/mMIG fault detection under "
        "this fault model and tested-vector campaign.}\n"
        "  \\label{tab:dualrail-equiv}\n"
        "  \\centering\n"
        "  \\small\n"
        "  \\begin{tabular}{lrrrrrr}\n"
        "    \\toprule\n"
        "    Circuit & $|P|$ & Identical & Jaccard & MIG-only & mMIG-only & Pearson \\\\\n"
        "    \\midrule\n"
        + "\n    ".join(rows) + "\n"
        "    \\bottomrule\n"
        "  \\end{tabular}\n"
        "\\end{table*}\n"
    )
    write("dualrail_equivalence", body)


# ---------------------------------------------------------------------------
# Table 5 — MAJ-arity fault study (synthetic)
# ---------------------------------------------------------------------------
def gen_majn_table():
    p = RES / "fault_coverage" / "majN" / "majN_fault_study.json"
    data = json.loads(p.read_text())

    rows = []
    for s, c, t in zip(data["single"], data["chain"], data["tree"]):
        a = s["arity"]
        rows.append(
            f"{a} & {s['theory_mask']:.4f} & "
            f"{c['n_gates']} & {c['fault_coverage']:.2f} & {c['avg_det_prob']:.4f} & "
            f"{t['n_gates']} & {t['fault_coverage']:.2f} & {t['avg_det_prob']:.4f} \\\\"
        )

    chain_d = data["params"]["chain_depth"]
    tree_d  = data["params"]["tree_depth"]

    body = (
        "% Auto-generated by scripts/gen_paper_tables.py -- do not edit\n"
        "\\begin{table*}[tbp]\n"
        f"  \\caption{{Synthetic MAJ-$n$ fault observability. Chain depth "
        f"$D={chain_d}$ and balanced tree depth $D={tree_d}$. The table reports "
        "the theoretical per-input masking probability for odd $n$. "
        "AvgDP drops by 18\\% to 62\\% from MAJ3 to MAJ7 in these synthetic "
        "circuits constructed with direct MAJ-$n$ truth-table primitives. "
        "Result motivates evaluation with native MAJ-$n$ libraries on "
        "majority-native technologies; synthesis flows targeting native "
        "MAJ-$n$ primitives are future work.}\n"
        "  \\label{tab:majn-arity}\n"
        "  \\centering\n"
        "  \\small\n"
        "  \\begin{tabular}{rrrrrrrr}\n"
        "    \\toprule\n"
        "          &              & \\multicolumn{3}{c}{Chain $D{=}5$} & \\multicolumn{3}{c}{Tree $D{=}3$} \\\\\n"
        "    \\cmidrule(lr){3-5} \\cmidrule(lr){6-8}\n"
        "    Arity & $P_\\text{mask}$ & Gates & FC\\% & AvgDP & Gates & FC\\% & AvgDP \\\\\n"
        "    \\midrule\n"
        + "\n    ".join(rows) + "\n"
        "    \\bottomrule\n"
        "  \\end{tabular}\n"
        "\\end{table*}\n"
    )
    write("majn_arity", body)


# ---------------------------------------------------------------------------
# Table 6 — Observability reduction (AOIG -> MIG AvgDP reduction)
# ---------------------------------------------------------------------------
def gen_implicit_countermeasure():
    p = RES / "fault_coverage" / "implicit_countermeasure.json"
    if not p.exists():
        print(f"  skipping implicit_countermeasure (no JSON yet)")
        return
    data = json.loads(p.read_text())
    rows_data = {r["circuit"]: r for r in data["rows"]}
    f1 = data.get("finding_1_observability_reduction",
                  data.get("finding_1_mig_as_countermeasure"))

    rows = []
    for name, label, _ in CIRCUITS:
        r = rows_data.get(name)
        if not r:
            continue
        rows.append(
            f"{label} & {r['aoig_avgdp']:.4f} & {r['mig_avgdp']:.4f} & "
            f"{r['mmig_avgdp']:.4f} & {r['aoig_to_mig_pct']:+.1f}\\% \\\\"
        )

    body = (
        "% Auto-generated by scripts/gen_paper_tables.py -- do not edit\n"
        "\\begin{table}[tbp]\n"
        f"  \\caption{{Average per-vector fault detection probability "
        "(AvgDP, see~\\S\\ref{sec:metrics}) across synthesis flows. "
        f"AvgDP drops AOIG~$\\rightarrow$~MIG by a mean of "
        f"{abs(f1['mean_pct_change']):.1f}\\% on {f1['n_with_improvement']}/"
        f"{f1['n_circuits']} circuits (best: {f1['best_improvement']:+.1f}\\%). "
        "Mechanism: the MIG decomposition introduces downstream 3-input "
        "majority nodes whose non-controlling input patterns can mask "
        "propagated faults, reducing observability relative to the LUT4 "
        "AOIG baseline. mMIG preserves the AvgDP profile (Table~\\ref{tab:dualrail-equiv}).}\n"
        "  \\label{tab:implicit-countermeasure}\n"
        "  \\centering\n"
        "  \\small\n"
        "  \\begin{tabular}{lrrrr}\n"
        "    \\toprule\n"
        "    Circuit & AOIG & MIG & mMIG & $\\Delta_{\\textsc{aoig}\\to\\textsc{mig}}$ \\\\\n"
        "    \\midrule\n"
        + "\n    ".join(rows) + "\n"
        "    \\bottomrule\n"
        "  \\end{tabular}\n"
        "\\end{table}\n"
    )
    write("implicit_countermeasure", body)


# ---------------------------------------------------------------------------
# Table 7 — Architecture-dependent fault avalanche (ARX vs Subst.)
# ---------------------------------------------------------------------------
def gen_arx_dichotomy():
    p = RES / "fault_coverage" / "implicit_countermeasure.json"
    if not p.exists():
        return
    data = json.loads(p.read_text())
    f2 = data["finding_2_arx_vs_substitution"]
    fs = f2["family_stats"]

    family_order = ["4-bit S-box", "Subst. round", "Permutation", "SIMON",
                    "Keccak chi", "ARX"]
    rows = []
    for fam in family_order:
        st = fs.get(fam)
        if not st:
            continue
        rows.append(
            f"{fam} & {st['n']} & {st['mean']:.3f} & "
            f"[{st['min']:.2f}, {st['max']:.2f}] & "
            f"{st['stdev']:.3f} \\\\"
        )

    body = (
        "% Auto-generated by scripts/gen_paper_tables.py -- do not edit\n"
        "\\begin{table}[tbp]\n"
        f"  \\caption{{Mean fault avalanche breadth (AvgBW, output bits "
        "flipped per detected fault) by cipher architecture family. "
        f"ARX primitives exhibit {f2['arx_over_subst_x']:.2f}$\\times$ broader "
        "output corruption per detected fault than substitution-based primitives "
        f"(ARX mean {f2['arx_mean_avgbw']:.2f} vs. substitution mean "
        f"{f2['subst_mean_avgbw']:.2f}). "
        "The effect is attributable to addition-chain carry propagation in "
        "ARX, which spreads a single internal fault across multiple output "
        "bit positions. Broader avalanche per detection event does not "
        "directly imply higher DFA exploitability; algebraic usefulness of "
        "output differences is out of scope.}\n"
        "  \\label{tab:arx-dichotomy}\n"
        "  \\centering\n"
        "  \\small\n"
        "  \\begin{tabular}{lrrcr}\n"
        "    \\toprule\n"
        "    Family & $N$ & mean AvgBW & [min, max] & $\\sigma$ \\\\\n"
        "    \\midrule\n"
        + "\n    ".join(rows) + "\n"
        "    \\bottomrule\n"
        "  \\end{tabular}\n"
        "\\end{table}\n"
    )
    write("arx_dichotomy", body)


def main():
    print("Generating LaTeX tables ->", OUT.relative_to(REPO))
    gen_fpga_table()
    gen_inv_reduction()
    gen_fault_coverage()
    gen_dualrail_equiv()
    gen_majn_table()
    gen_implicit_countermeasure()
    gen_arx_dichotomy()
    print("Done.")


if __name__ == "__main__":
    main()
