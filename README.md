# Granularity-Controlled Fault Observability in Majority-Based Cipher Circuits — HOST 2026 Artifact

This repository contains the reproducibility artifact for our HOST 2026
submission. We characterize per-vector fault observability of 15 cipher
primitives under LUT/AOIG, AIG, MIG, and mMIG representations and report
which fault metrics survive granularity-controlled comparisons (FC%, AvgDP,
AvgBW — see [`paper/metrics.md`](paper/metrics.md)).

> **Citation**: *[Author list, Title, HOST 2026 — placeholder until camera-ready]*
>
> **TODO before submission**: author list, affiliations, contact email,
> camera-ready BibTeX entry, acknowledgments. Do not commit invented
> values; leave the TODO markers visible until the real values are
> provided. See [`paper/tex/main.tex`](paper/tex/main.tex) for the
> author and acknowledgments blocks, and
> [`paper/tex/sections/6_conclusion.tex`](paper/tex/sections/6_conclusion.tex)
> for the public artifact URL placeholder.

## Headline results

1. **Granularity controls reverse the original headline**: the
   AOIG→MIG AvgDP reduction is real for the Yosys LUT-style AOIG
   baseline (mean −13.0%, 13/15 circuits reduced), but the
   same-granularity AIG control reverses the sign: AIG→MIG changes
   AvgDP by a mean of +21.44% with 0/15 circuits reduced. Target-layer
   AvgDP is 1.000 across AOIG/AIG/MIG/mMIG for the evaluated circuits.
   The artifact therefore frames all-site AvgDP as representation-
   sensitive, not as a standalone fault-resistance metric.
2. **mMIG is fault-equivalent to MIG (empirical)**: across all 15
   circuits, the *set* of faulty outputs producible by any single
   bit-flip is identical between MIG and mMIG for every tested input
   vector (Jaccard = 1.000; exhaustive for small circuits, fixed
   10,000-vector sample for large circuits). Consistent with a
   polarity-equivalent (De Morgan) relationship between the two
   networks. Designers can apply mMIG's 7–33% inverter reduction on
   the circuits where minority insertion changes inverter count
   without altering the fault observability profile reported here.
3. **Cipher architecture predicts avalanche breadth**: ARX primitives
   exhibit 1.90× broader output corruption per detected fault (mean
   AvgBW = 2.06) than substitution-based primitives (mean = 1.08).
   Architecture-level observation; algebraic exploitability of these
   broader differences is out of scope.
4. **Forward path — MAJ-n primitives**: synthetic MAJ3/MAJ5/MAJ7
   experiments show an additional 18–62% AvgDP reduction at higher
   arity, motivating evaluation with native MAJ-n libraries on
   majority-native technologies.

The benchmark spans 15 cipher primitives from PRESENT, GIFT, PRINCE,
SIMON, Keccak-χ, and Speck/ARX, evaluated on Spartan-7 (Vivado 2023.2)
with full FPGA + fault campaigns. **All metrics are defined precisely
in [`paper/metrics.md`](paper/metrics.md)** — they vary independently
and the paper text uses them with that distinction enforced.

## Repository layout

```
.
├── scripts/                       # Reproduction scripts
│   ├── run_jetc_benchmark.py        FPGA campaign (15 circuits × 3 flows)
│   ├── run_fault_coverage.py        Per-gate fault coverage measurement
│   ├── run_dualrail_diversity.py    Per-input fault sensitivity correlation
│   ├── verify_dualrail_equiv.py     Stronger MIG/mMIG faulty-output set test
│   ├── maj_arity_fault_study.py     Synthetic MAJ3/5/7 study
│   ├── gen_paper_tables.py          Renders LaTeX tables from result JSONs
│   └── gen_paper_figures.py         Renders matplotlib figures from result JSONs
├── src/fault/dfa/                 # Combinational simulator & fault injector
│   ├── blif_parser.py
│   ├── simulator.py
│   └── fault_injector.py
├── vivado/run_metrics.tcl          # Vivado TCL — paper-style FPGA metrics
├── data/cipher_blif/               # 15 input cipher BLIF circuits
│   ├── present/  gift/  prince/
│   ├── simon/   keccak/  arx/
├── results/                       # Frozen result data
│   ├── fpga_benchmark/             FPGA metric JSONs + optimized BLIFs
│   └── fault_coverage/             Fault coverage / dual-rail / MAJ-n JSONs
└── paper/                         # Paper artifacts
    ├── tables/                     LaTeX tables (auto-generated)
    ├── figures/                    PDF + PNG figures (auto-generated)
    ├── tex/                        LaTeX source for the submission
    │   ├── main.tex                IEEEtran conference, 6 pages
    │   ├── sections/               One file per section (1_intro … 6_conclusion)
    │   ├── figures/pipeline.tex    tikz pipeline figure (§3)
    │   └── references.bib          Bibliography (TODO: verify entries)
    ├── mechanism_example/          Worked masking trace for §3
    ├── verified_numbers.md         Independent recomputation of every headline number
    ├── stats.md                    Wilcoxon, 95% CI, Mann-Whitney U
    ├── outliers.md                 Why Keccak-χ doesn't fit the headline
    ├── style_notes.md              HOST-venue voice calibration
    ├── abstract.md                 Plain-text abstract
    ├── outline.md                  Section outline with table/figure refs
    └── metrics.md                  Precise definitions of FC%, AvgDP, AvgBW
```

## Reproducing the results

See [INSTALL.md](INSTALL.md) for dependencies and setup.

### Quick path (no Vivado required, a few minutes)

The fault-analysis results are reproducible from the optimized BLIFs in
`results/fpga_benchmark/` without re-running the FPGA flow:

```bash
# Single-bit-flip fault coverage on all 15 circuits × 3 flows
python3 scripts/run_fault_coverage.py

# Dual-rail diversity correlation
python3 scripts/run_dualrail_diversity.py

# Definitive equivalence check (Jaccard test)
python3 scripts/verify_dualrail_equiv.py

# Synthetic MAJ-arity study (regenerates BLIFs + metrics)
python3 scripts/maj_arity_fault_study.py

# Extract positive-result analysis (MIG observability reduction + ARX dichotomy)
python3 scripts/analyze_implicit_countermeasure.py

# Check the abstract/README headline numbers against generated JSONs
python3 scripts/verify_headline_numbers.py

# Granularity-controlled reframe checks
python3 scripts/granularity_baseline.py
python3 scripts/invariant_metric.py
python3 scripts/gen_reframe_tables.py
python3 scripts/gen_granularity_figure.py

# Render all paper tables and figures from JSONs
python3 scripts/gen_paper_tables.py
python3 scripts/gen_paper_figures.py
```

### Full path (with Vivado, ~1 hour)

Requires Vivado 2023.2 (or compatible) and a built `blif2mig_2` binary —
see [INSTALL.md](INSTALL.md) for the mockturtle build instructions.

```bash
python3 scripts/run_jetc_benchmark.py \
    --binary /path/to/mockturtle/build/examples/blif2mig_2 \
    --out-dir results/fpga_benchmark \
    --skip-existing
```

## Paper artifacts

The main paper tables/figures and supporting generated artifacts are ready
to `\input{}`:

| File                                              | Paper reference                       |
|---------------------------------------------------|---------------------------------------|
| `paper/tables/granularity_confound.tex`           | Baseline sign-flip result             |
| `paper/tables/representation_robustness.tex`      | Target-layer + robust ARX ratio       |
| `paper/tables/dualrail_equivalence.tex`           | MIG/mMIG equivalence check            |
| `paper/tables/arx_dichotomy.tex`                  | Cipher-family avalanche               |
| `paper/tables/majn_arity.tex`                     | Higher-arity study                    |
| `paper/tables/fpga_benchmark.tex`                 | Full FPGA numbers                     |
| `paper/figures/granularity_curve.pdf`             | AvgDP vs decomposition granularity    |
| `paper/figures/dualrail_jaccard.pdf`              | Equivalence Jaccard                   |
| `paper/figures/arx_dichotomy.pdf`                 | ARX vs Subst. AvgBW                   |
| `paper/figures/majn_avgdp_chain.pdf`              | MAJ-n chain                           |
| `paper/figures/majn_avgdp_tree.pdf`               | MAJ-n tree                            |
| `paper/figures/majn_propagation_depth.pdf`        | Theoretical propagation               |

## License

Source code released under the MIT License (see `LICENSE`). The included
cipher BLIFs are derivative artifacts of publicly available cipher
specifications.
