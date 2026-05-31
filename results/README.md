# Results Directory

This directory contains frozen outputs for the active AOIG, AIG, and MIG experiments.

## `fpga_benchmark/`

Per-circuit BLIFs and FPGA metric JSONs:

- `<circuit>_aoig.blif`
- `<circuit>_aig.blif`
- `<circuit>_mig_maj_opt.blif`
- `aoig/<circuit>_aoig_metrics.json`
- `mig/<circuit>_mig_metrics.json`

## `fault_coverage/`

Fault-campaign and summary JSONs:

- `fault_coverage_results.json`: all-site fault metrics for AOIG and MIG
- `<circuit>_aoig_fault.json`, `<circuit>_mig_fault.json`: per-circuit metrics
- `summary_metrics.json`: AOIG-to-MIG AvgDP and ARX/substitution summaries
- `granularity_baseline.json`: AIG-to-MIG small-gate control
- `invariant_metric.json`: target-layer and ARX/substitution controls
- `majN/majN_fault_study.json`: synthetic MAJ-n chain/tree study

Regenerate active summaries with:

```bash
./reproduce.sh
```
