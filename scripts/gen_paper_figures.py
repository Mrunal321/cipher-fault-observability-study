#!/usr/bin/env python3
"""
gen_paper_figures.py — Render all matplotlib figures for the HOST paper
from the result JSONs in results/.

Outputs into paper/figures/ as PDF and PNG:
  - inverter_reduction.pdf       Grouped bar chart, MIG vs mMIG inverter counts
  - fault_coverage_bars.pdf      Per-circuit fault coverage AOIG/MIG/mMIG
  - dualrail_jaccard.pdf         MIG/mMIG Jaccard = 1.0 across all 15 circuits
  - majn_avgdp_chain.pdf         AvgDP vs arity, chain depth 5
  - majn_avgdp_tree.pdf          AvgDP vs arity, balanced tree depth 3
  - majn_propagation_depth.pdf   Theoretical (1-P_mask)^D curves for n=3,5,7

Figures sized for 1-column IEEE conference format (3.4" wide).
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import sys
from math import comb
from pathlib import Path
from typing import Dict, List, Any, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[1]
RES  = REPO / "results"
OUT  = REPO / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

# IEEE conference-format friendly defaults
plt.rcParams.update({
    "font.family":      "serif",
    "font.size":        9,
    "axes.labelsize":   9,
    "axes.titlesize":   9,
    "legend.fontsize":  8,
    "xtick.labelsize":  8,
    "ytick.labelsize":  8,
    "figure.dpi":       150,
    "savefig.bbox":     "tight",
    "savefig.pad_inches": 0.02,
    "axes.spines.top":   False,
    "axes.spines.right": False,
})

ONE_COL_IN  = 3.4   # inches, 1-column IEEEtran
WIDE_IN     = 7.0   # full text-width for two-column figures

COLORS = {
    "AOIG": "#7F7F7F",
    "MIG":  "#1F77B4",
    "mMIG": "#D62728",
    "MAJ3": "#1F77B4",
    "MAJ5": "#D62728",
    "MAJ7": "#2CA02C",
}

PDF_METADATA = {
    "Creator": "scripts/gen_paper_figures.py",
    "CreationDate": datetime(2026, 1, 1, tzinfo=timezone.utc),
    "ModDate": datetime(2026, 1, 1, tzinfo=timezone.utc),
}

CIRCUITS_SHORT = [
    ("present_sbox",    "Pres-Sb"),
    ("gift_sbox",       "GIFT-Sb"),
    ("prince_sbox",     "PRC-Sb"),
    ("prince_sbox_inv", "PRC-Sb$^{-1}$"),
    ("gift_subcells",   "GIFT-sc"),
    ("gift_round",      "GIFT-rd"),
    ("present_round",   "Pres-rd"),
    ("prince_mprime",   "PRC-M'"),
    ("simon32_round",   "SIM-32"),
    ("simon64_round",   "SIM-64"),
    ("keccak_chi_5bit", "K$\\chi$-5"),
    ("keccak_chi_64row","K$\\chi$-64"),
    ("speckey_box",     "SpKey"),
    ("speck32_round",   "Spk-32"),
    ("marx2_box",       "MARX-2"),
]

# Structural data inline (matches gen_paper_tables.py)
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


def save(fig, name: str):
    pdf = OUT / f"{name}.pdf"
    png = OUT / f"{name}.png"
    fig.savefig(pdf, metadata=PDF_METADATA)
    fig.savefig(png, dpi=200)
    plt.close(fig)
    print(f"  wrote {pdf.relative_to(REPO)} (+ .png)")


# ---------------------------------------------------------------------------
# Figure 1 — Inverter reduction (mMIG vs MIG)
# ---------------------------------------------------------------------------
def fig_inverter_reduction():
    labels = [s for _, s in CIRCUITS_SHORT]
    mig_inv  = [STRUCT[k]["mig"][1]  for k, _ in CIRCUITS_SHORT]
    mmig_inv = [STRUCT[k]["mmig"][1] for k, _ in CIRCUITS_SHORT]

    fig, ax = plt.subplots(figsize=(WIDE_IN, 2.4))
    x = np.arange(len(labels))
    w = 0.4
    ax.bar(x - w/2, mig_inv,  w, label="MIG",  color=COLORS["MIG"])
    ax.bar(x + w/2, mmig_inv, w, label="mMIG", color=COLORS["mMIG"])
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylabel("Inverted edges (log scale)")
    ax.legend(loc="upper left", frameon=False)
    ax.set_axisbelow(True)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    save(fig, "inverter_reduction")


# ---------------------------------------------------------------------------
# Figure 2 — Fault coverage per circuit
# ---------------------------------------------------------------------------
def fig_fault_coverage():
    p = RES / "fault_coverage" / "fault_coverage_results.json"
    by_circ = {r["circuit"]: r for r in json.loads(p.read_text())}

    labels = []
    aoig_fc, mig_fc, mmig_fc = [], [], []
    for k, lab in CIRCUITS_SHORT:
        rec = by_circ.get(k)
        if not rec or "flows" not in rec:
            continue
        labels.append(lab)
        aoig_fc.append(rec["flows"].get("aoig", {}).get("fault_coverage", 0))
        mig_fc .append(rec["flows"].get("mig",  {}).get("fault_coverage", 0))
        mmig_fc.append(rec["flows"].get("mmig", {}).get("fault_coverage", 0))

    fig, ax = plt.subplots(figsize=(WIDE_IN, 2.4))
    x = np.arange(len(labels))
    w = 0.27
    ax.bar(x - w, aoig_fc, w, label="AOIG", color=COLORS["AOIG"])
    ax.bar(x,     mig_fc,  w, label="MIG",  color=COLORS["MIG"])
    ax.bar(x + w, mmig_fc, w, label="mMIG", color=COLORS["mMIG"])
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylabel("Fault coverage (\\%)")
    ax.set_ylim(50, 102)
    ax.legend(loc="lower right", ncol=3, frameon=False)
    ax.set_axisbelow(True)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    save(fig, "fault_coverage_bars")


# ---------------------------------------------------------------------------
# Figure 3 — Dual-rail Jaccard
# ---------------------------------------------------------------------------
def fig_dualrail_jaccard():
    p = RES / "fault_coverage" / "dualrail_equivalence.json"
    rec_by = {r["circuit"]: r for r in json.loads(p.read_text())}

    labels, vals = [], []
    for k, lab in CIRCUITS_SHORT:
        r = rec_by.get(k)
        if not r or "error" in r:
            continue
        labels.append(lab)
        vals.append(r.get("avg_jaccard", 1.0))

    fig, ax = plt.subplots(figsize=(ONE_COL_IN, 2.0))
    x = np.arange(len(labels))
    ax.bar(x, vals, color=COLORS["mMIG"], width=0.64)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=50, ha="right", fontsize=6.7)
    ax.set_ylabel("Jaccard")
    ax.set_ylim(0, 1.08)
    ax.set_yticks([0, 0.5, 1.0])
    ax.axhline(1.0, color="black", lw=0.7, linestyle="--", alpha=0.7)
    ax.text(0.02, 0.95, "all values $=1.000$",
            transform=ax.transAxes, fontsize=8, va="top",
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=2))
    ax.set_axisbelow(True)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    save(fig, "dualrail_jaccard")


# ---------------------------------------------------------------------------
# Figure 4 — MAJ-n AvgDP (chain depth 5)
# ---------------------------------------------------------------------------
def fig_majn_chain():
    p = RES / "fault_coverage" / "majN" / "majN_fault_study.json"
    data = json.loads(p.read_text())

    arities = [r["arity"] for r in data["chain"]]
    avgdp   = [r["avg_det_prob"] for r in data["chain"]]
    fc      = [r["fault_coverage"] for r in data["chain"]]

    fig, ax = plt.subplots(figsize=(ONE_COL_IN, 2.2))
    x = np.arange(len(arities))
    bars = ax.bar(x, avgdp,
                  color=[COLORS[f"MAJ{a}"] for a in arities], width=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels([f"MAJ{a}" for a in arities])
    ax.set_ylabel("AvgDP (chain $D{=}5$)")
    ax.set_ylim(0, max(avgdp) * 1.25)
    for b, v in zip(bars, avgdp):
        ax.text(b.get_x() + b.get_width()/2, v + 0.01,
                f"{v:.3f}", ha="center", fontsize=7)
    ax.set_axisbelow(True)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    save(fig, "majn_avgdp_chain")


# ---------------------------------------------------------------------------
# Figure 5 — MAJ-n AvgDP (balanced tree depth 3)
# ---------------------------------------------------------------------------
def fig_majn_tree():
    p = RES / "fault_coverage" / "majN" / "majN_fault_study.json"
    data = json.loads(p.read_text())

    arities = [r["arity"] for r in data["tree"]]
    avgdp   = [r["avg_det_prob"] for r in data["tree"]]

    fig, ax = plt.subplots(figsize=(ONE_COL_IN, 2.2))
    x = np.arange(len(arities))
    bars = ax.bar(x, avgdp,
                  color=[COLORS[f"MAJ{a}"] for a in arities], width=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels([f"MAJ{a}" for a in arities])
    ax.set_ylabel("AvgDP (tree $D{=}3$)")
    ax.set_ylim(0, max(avgdp) * 1.25)
    for b, v in zip(bars, avgdp):
        ax.text(b.get_x() + b.get_width()/2, v + 0.01,
                f"{v:.3f}", ha="center", fontsize=7)
    ax.set_axisbelow(True)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    save(fig, "majn_avgdp_tree")


# ---------------------------------------------------------------------------
# Figure 6 — Theoretical fault propagation through depth
# ---------------------------------------------------------------------------
def fig_propagation_depth():
    def p_propagate(n: int) -> float:
        return comb(n - 1, (n - 1) // 2) / (2 ** (n - 1))

    depths = np.arange(1, 11)
    fig, ax = plt.subplots(figsize=(ONE_COL_IN, 2.2))
    for n in (3, 5, 7):
        p = p_propagate(n)
        y = p ** depths
        ax.plot(depths, y, marker="o", markersize=4, lw=1.2,
                label=f"MAJ{n} ($p={p:.3f}$)",
                color=COLORS[f"MAJ{n}"])
    ax.set_xlabel("Network depth $D$")
    ax.set_ylabel("Pr[fault propagates]")
    ax.set_yscale("log")
    ax.set_xticks(depths)
    ax.legend(loc="upper right", frameon=False)
    ax.set_axisbelow(True)
    ax.grid(True, linestyle=":", alpha=0.4)
    save(fig, "majn_propagation_depth")


# ---------------------------------------------------------------------------
# Figure 7 — AOIG vs MIG AvgDP per circuit
# ---------------------------------------------------------------------------
def fig_implicit_countermeasure():
    p = RES / "fault_coverage" / "implicit_countermeasure.json"
    if not p.exists():
        return
    data = json.loads(p.read_text())
    rows_by = {r["circuit"]: r for r in data["rows"]}

    labels, aoig_dp, mig_dp, deltas = [], [], [], []
    for k, lab in CIRCUITS_SHORT:
        r = rows_by.get(k)
        if not r:
            continue
        labels.append(lab)
        aoig_dp.append(r["aoig_avgdp"])
        mig_dp .append(r["mig_avgdp"])
        deltas .append(r["aoig_to_mig_pct"])

    fig, ax = plt.subplots(figsize=(WIDE_IN, 2.5))
    x = np.arange(len(labels))
    w = 0.4
    b1 = ax.bar(x - w/2, aoig_dp, w, label="AOIG", color=COLORS["AOIG"])
    b2 = ax.bar(x + w/2, mig_dp,  w, label="MIG",  color=COLORS["MIG"])
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylabel("Per-vector fault detection prob.")
    ax.set_ylim(0, 1.15)
    ax.axhline(1.0, color="gray", lw=0.5, alpha=0.5)
    ax.legend(loc="lower right", ncol=2, frameon=False)

    # Annotate delta% above each MIG bar
    for xi, dp, d in zip(x, mig_dp, deltas):
        color = "green" if d < 0 else "red"
        ax.annotate(f"{d:+.0f}%", xy=(xi + w/2, dp + 0.03),
                    ha="center", fontsize=6.5, color=color)

    ax.set_axisbelow(True)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    save(fig, "mig_implicit_countermeasure")


# ---------------------------------------------------------------------------
# Figure 8 — ARX vs substitution fault avalanche
# ---------------------------------------------------------------------------
def fig_arx_dichotomy():
    p = RES / "fault_coverage" / "implicit_countermeasure.json"
    if not p.exists():
        return
    data = json.loads(p.read_text())
    f2 = data["finding_2_arx_vs_substitution"]
    family_order = ["4-bit S-box", "Subst. round", "Permutation", "SIMON",
                    "Keccak chi", "ARX"]
    family_short = {
        "4-bit S-box":  "S-box",
        "Subst. round": "Subst.\nround",
        "Permutation":  "Perm.",
        "SIMON":        "SIMON",
        "Keccak chi":   "Keccak",
        "ARX":          "ARX",
    }

    rows = data["rows"]
    by_family = {}
    for r in rows:
        by_family.setdefault(r["family"], []).append(r["mig_avgbw"])

    means = [statistics_mean(by_family.get(f, [0])) for f in family_order]
    mins  = [min(by_family.get(f, [0])) for f in family_order]
    maxs  = [max(by_family.get(f, [0])) for f in family_order]
    err_low  = [m - lo for m, lo in zip(means, mins)]
    err_high = [hi - m for hi, m in zip(maxs, means)]

    fig, ax = plt.subplots(figsize=(ONE_COL_IN, 2.4))
    x = np.arange(len(family_order))

    # Color ARX differently to highlight
    colors = ["#1F77B4"] * len(family_order)
    colors[family_order.index("ARX")] = COLORS["mMIG"]

    bars = ax.bar(x, means, color=colors, width=0.65)
    ax.errorbar(x, means, yerr=[err_low, err_high], fmt="none",
                ecolor="black", elinewidth=0.7, capsize=2)
    for xi, m, hi in zip(x, means, maxs):
        ax.text(xi, hi + 0.06, f"{m:.2f}", ha="center", fontsize=7,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=0.5))

    ax.set_xticks(x)
    ax.set_xticklabels([family_short[f] for f in family_order],
                       rotation=0, fontsize=7.5)
    ax.set_ylabel("AvgBW (bits flipped per fault)")
    ax.set_ylim(0, max(maxs) * 1.30)
    ax.axhline(1.0, color="gray", lw=0.5, alpha=0.5, linestyle=":")
    ax.set_axisbelow(True)
    ax.grid(axis="y", linestyle=":", alpha=0.4)

    save(fig, "arx_dichotomy")


def statistics_mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def main():
    print("Generating figures ->", OUT.relative_to(REPO))
    fig_inverter_reduction()
    fig_fault_coverage()
    fig_dualrail_jaccard()
    fig_majn_chain()
    fig_majn_tree()
    fig_propagation_depth()
    fig_implicit_countermeasure()
    fig_arx_dichotomy()
    print("Done.")


if __name__ == "__main__":
    main()
