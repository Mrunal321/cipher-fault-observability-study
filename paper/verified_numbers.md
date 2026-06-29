# Verified Headline Numbers

This note records the paper-facing values recomputed from the shipped JSON
outputs in `results/fault_coverage/`. The programmatic guard is:

```bash
python3 scripts/verify_summary_numbers.py
```

## AOIG to MIG AvgDP

Source: `results/fault_coverage/summary_metrics.json`.

| Circuit | AOIG AvgDP | MIG AvgDP | AOIG to MIG |
|---|---:|---:|---:|
| present_sbox | 1.0000 | 0.7853 | -21.47% |
| gift_sbox | 1.0000 | 0.8315 | -16.85% |
| prince_sbox | 1.0000 | 0.7632 | -23.68% |
| prince_sbox_inv | 1.0000 | 0.7688 | -23.12% |
| gift_subcells | 1.0000 | 0.8316 | -16.84% |
| gift_round | 1.0000 | 0.8320 | -16.80% |
| present_round | 1.0000 | 0.8017 | -19.83% |
| prince_mprime | 1.0000 | 0.8997 | -10.03% |
| simon32_round | 1.0000 | 0.8889 | -11.11% |
| simon64_round | 1.0000 | 0.8891 | -11.09% |
| keccak_chi_5bit | 0.8333 | 0.9000 | +8.00% |
| keccak_chi_64row | 0.8332 | 0.9000 | +8.02% |
| speck32_round | 1.0000 | 0.8752 | -12.48% |
| speckey_box | 1.0000 | 0.8613 | -13.87% |
| marx2_box | 1.0000 | 0.8616 | -13.84% |

Summary:

- 13/15 circuits have lower all-site AvgDP under MIG than AOIG.
- Mean AOIG to MIG AvgDP change: -13.00%.
- Best drop: -23.68% on `prince_sbox`.
- Worst change: +8.02% on `keccak_chi_64row`.

## AIG Granularity Control

Source: `results/fault_coverage/granularity_baseline.json`.

- Baseline: `yosys abc -g AND` 2-input AIG, small-gate control.
- AIG to MIG reductions: 0/15 circuits.
- Mean AIG to MIG AvgDP change: +21.44%.

This is the core caution in the paper: the LUT/AOIG-to-MIG all-site AvgDP
reduction is reproducible for that baseline, but it reverses under a
decomposed-AIG baseline with comparable small-gate granularity.

## Target-Layer Control

Source: `results/fault_coverage/invariant_metric.json`.

- Target-layer AvgDP mean spread across LUT/AOIG, AIG, and MIG: 0.0000.
- Target-layer AvgDP is 1.000 for every evaluated flow/circuit pair.

## ARX Versus Substitution AvgBW

Sources: `results/fault_coverage/summary_metrics.json` and
`results/fault_coverage/invariant_metric.json`.

- MIG-flow ARX mean AvgBW: 2.06.
- MIG-flow substitution mean AvgBW: 1.08.
- ARX/substitution ratio: 1.90x.
- The ratio is stable across the representation controls:
  - LUT/AOIG: 1.846x.
  - AIG: 1.857x.
  - MIG: 1.923x.

## MAJ-n Synthetic Study

Source: `results/fault_coverage/majN/majN_fault_study.json`.

| Experiment | MAJ3 AvgDP | MAJ5 AvgDP | MAJ7 AvgDP |
|---|---:|---:|---:|
| single gate | 1.0000 | 1.0000 | 1.0000 |
| chain, depth 5 | 0.3875 | 0.3173 | 0.2899 |
| tree, depth 3 | 0.3656 | 0.2057 | 0.1394 |

The observed reductions from MAJ-3 to MAJ-5/7 span 18.1% to 61.9% in the
matched chain/tree experiments.
