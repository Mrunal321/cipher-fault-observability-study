# Granularity-Controlled Fault Observability in Majority-Based Cipher Circuits - HOST 2026 Artifact

This repository contains the reproducibility artifact for our HOST 2026
submission. We characterize per-vector fault observability of 15 cipher
primitives under LUT/AOIG, AIG, and MIG representations and report
which fault metrics survive granularity-controlled comparisons (FC%, AvgDP,
AvgBW; see [`paper/metrics.md`](paper/metrics.md)).

> **Citation**: *[Author list, title, HOST 2026 - placeholder until camera-ready]*
>
> **TODO before submission**: author list, affiliations, contact email,
> anonymous artifact link, camera-ready BibTeX entry, acknowledgments. Do not commit invented
> values; leave the TODO markers visible until the real values are
> provided. See [`paper/tex/main.tex`](paper/tex/main.tex) for the
> anonymous author block and [`paper/tex/sections/1_introduction.tex`](paper/tex/sections/1_introduction.tex)
> for the artifact-link placeholder.

## Main results

1. **Granularity controls reverse the AOIG-to-MIG comparison**: the
   AOIG→MIG AvgDP reduction is real for the Yosys LUT-style AOIG
   baseline (mean −13.0%, 13/15 circuits reduced), but the
   decomposed-AIG control reverses the sign: AIG→MIG changes
   AvgDP by a mean of +21.44% with 0/15 circuits reduced. Target-layer
   AvgDP is 1.000 across LUT/AOIG, AIG, and MIG for the evaluated circuits.
   The artifact therefore frames all-site AvgDP as representation-
   sensitive, not as a standalone fault-resistance metric.
2. **Cipher architecture predicts avalanche breadth**: ARX primitives
   exhibit 1.90× broader output corruption per detected fault (mean
   AvgBW = 2.06) than substitution-based primitives (mean = 1.08).
   Architecture-level observation; algebraic exploitability of these
   broader differences is out of scope.
3. **Forward path - MAJ-n primitives**: synthetic MAJ3/MAJ5/MAJ7
   experiments show an additional 18–62% AvgDP reduction at higher
   arity, motivating evaluation with native MAJ-n libraries on
   majority-native technologies.

The benchmark spans 15 cipher primitives from PRESENT, GIFT, PRINCE,
SIMON, Keccak-χ, and Speck/ARX, evaluated on Spartan-7 (Vivado 2023.2)
with full FPGA + fault campaigns. **All metrics are defined precisely
in [`paper/metrics.md`](paper/metrics.md)**; they vary independently
and the paper text uses them with that distinction enforced.

## Repository layout

```
.
├── scripts/                       # Reproduction scripts
│   ├── run_jetc_benchmark.py        FPGA campaign (15 circuits × 3 flows)
│   ├── run_fault_coverage.py        Per-gate fault coverage measurement
│   ├── run_dualrail_diversity.py    Legacy MIG/mMIG sensitivity correlation
│   ├── verify_dualrail_equiv.py     Legacy MIG/mMIG faulty-output set test
│   ├── maj_arity_fault_study.py     Synthetic MAJ3/5/7 study
│   ├── gen_paper_tables.py          Renders LaTeX tables from result JSONs
│   └── gen_paper_figures.py         Renders matplotlib figures from result JSONs
├── src/fault/dfa/                 # Combinational simulator & fault injector
│   ├── blif_parser.py
│   ├── simulator.py
│   └── fault_injector.py
├── vivado/run_metrics.tcl          # Vivado TCL for paper-style FPGA metrics
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
    │   ├── main.tex                IEEEtran conference paper source
    │   ├── sections/               One file per section (1_intro … 6_conclusion)
    │   ├── figures/pipeline.tex    tikz pipeline figure (§3)
    │   └── references.bib          Bibliography (TODO: verify entries)
    ├── mechanism_example/          Worked masking trace for §3
    ├── verified_numbers.md         Independent recomputation of quoted numbers
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

# Synthetic MAJ-arity study (regenerates BLIFs + metrics)
python3 scripts/maj_arity_fault_study.py

# Extract positive-result analysis (MIG observability reduction + ARX dichotomy)
python3 scripts/analyze_implicit_countermeasure.py

# Check the abstract/README summary numbers against generated JSONs
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

Requires Vivado 2023.2 (or compatible) and a built `blif2mig_2` binary.
The paper uses the stock mockturtle MIG path exposed by that driver;
the experimental mMIG path in the vendor patch is not used in the paper.
See [INSTALL.md](INSTALL.md) for build notes.

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
| `paper/tables/representation_robustness.tex`      | Target-layer + ARX ratio controls     |
| `paper/tables/arx_dichotomy.tex`                  | Cipher-family avalanche               |
| `paper/tables/majn_arity.tex`                     | Higher-arity study                    |
| `paper/figures/granularity_curve.pdf`             | AvgDP vs decomposition granularity    |
| `paper/figures/arx_dichotomy.pdf`                 | ARX vs Subst. AvgBW                   |

## License

No license file is currently included. Add the intended license before
making the repository public. The included cipher BLIFs are derivative
artifacts of publicly available cipher specifications.
