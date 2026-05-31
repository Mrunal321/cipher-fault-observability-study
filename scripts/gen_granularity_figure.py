#!/usr/bin/env python3
"""
gen_granularity_figure.py — Headline figure for the granularity-controlled
reframe: AvgDP is a monotone function of decomposition granularity.

Plots nodes-per-output (x, log scale) vs AvgDP (y) for every (circuit, flow)
point across the three representations (LUT, AIG, MIG), with the Spearman
rank correlation annotated. This replaces the old "AOIG vs MIG headline" Fig 1.

Output: paper/figures/granularity_curve.{pdf,png}
"""

from __future__ import annotations
from datetime import datetime, timezone
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from fault.dfa.blif_parser import parse_blif_file  # noqa: E402

FC = REPO / "results" / "fault_coverage"
BENCH = REPO / "results" / "fpga_benchmark"
OUT = REPO / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif", "font.size": 9, "axes.labelsize": 9,
    "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
})

BLIF = {
    "aoig": "{n}_aoig.blif", "aig": "{n}_aig.blif",
    "mig": "{n}_mig_maj_opt.blif", "mmig": "{n}_mmig_mmig_opt.blif",
}
STYLE = {
    "aoig": ("LUT/AOIG", "o", "#888888"),
    "aig":  ("AIG",      "s", "#1f77b4"),
    "mig":  ("MIG",      "^", "#d62728"),
}

PDF_METADATA = {
    "Creator": "scripts/gen_granularity_figure.py",
    "CreationDate": datetime(2026, 1, 1, tzinfo=timezone.utc),
    "ModDate": datetime(2026, 1, 1, tzinfo=timezone.utc),
}


def n_outputs(name: str, flow: str) -> int:
    p = BENCH / name / BLIF[flow].format(n=name)
    return len(parse_blif_file(str(p)).outputs)


def collect():
    """Return dict flow -> (xs nodes/output, ys avgdp)."""
    inv = json.load(open(FC / "invariant_metric.json"))
    pts = {f: ([], []) for f in STYLE}
    for r in inv["rows"]:
        name = r["circuit"]
        no = n_outputs(name, "mig")
        for flow in STYLE:
            if flow not in r["flows"]:
                continue
            m = r["flows"][flow]["all"]
            dp = m["avgdp"]
            if dp is None:
                continue
            pts[flow][0].append(m["total"] / no)
            pts[flow][1].append(dp)
    return pts


def spearman(xs, ys):
    def rank(v):
        s = sorted(range(len(v)), key=lambda i: v[i]); r = [0]*len(v)
        for i, idx in enumerate(s): r[idx] = i
        return r
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    d2 = sum((rx[i]-ry[i])**2 for i in range(n))
    return 1 - 6*d2/(n*(n*n-1))


def main():
    pts = collect()
    all_x = [x for f in pts for x in pts[f][0]]
    all_y = [y for f in pts for y in pts[f][1]]
    rho = spearman(all_x, all_y)

    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    for flow, (label, marker, color) in STYLE.items():
        xs, ys = pts[flow]
        ax.scatter(xs, ys, s=26, marker=marker, c=color, label=label,
                   edgecolors="k", linewidths=0.3, alpha=0.85, zorder=3)

    ax.set_xscale("log")
    ax.set_xlabel("Decomposition granularity (gate nodes / output)")
    ax.set_ylabel("AvgDP (all-site)")
    ax.set_ylim(0.55, 1.03)
    ax.grid(True, which="both", ls=":", lw=0.4, alpha=0.6)
    ax.text(0.97, 0.95, f"Spearman $\\rho = {rho:+.2f}$",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8.5, bbox=dict(boxstyle="round,pad=0.25",
                                    fc="white", ec="0.6", lw=0.5))
    ax.legend(loc="lower left", frameon=True, framealpha=0.9, ncol=2)
    fig.tight_layout(pad=0.3)
    fig.savefig(OUT / "granularity_curve.pdf", dpi=200, bbox_inches="tight",
                metadata=PDF_METADATA)
    fig.savefig(OUT / "granularity_curve.png", dpi=200, bbox_inches="tight")
    print(f"Spearman rho = {rho:.3f}")
    print(f"Wrote {OUT/'granularity_curve.pdf'} (+ .png)")


if __name__ == "__main__":
    main()
