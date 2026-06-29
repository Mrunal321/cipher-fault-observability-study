# Fault Observability in FPGA-Mapped Cipher Circuits Synthesized from AIG and MIG Representations

This repository contains the code, input circuits, frozen experiment outputs, and verification scripts for a granularity-controlled fault-observability study on cipher circuits.

The active study compares three gate-level representations:

- `aoig`: Yosys-emitted LUT/truth-table style BLIFs
- `aig`: decomposed 2-input AND-inverter graph controls
- `mig`: 3-input majority-inverter graph netlists

The repository is meant to reproduce the paper's fault-observability experiments and regenerate the JSON summaries used by the study.

## Main Results

- The AOIG-to-MIG AvgDP reduction is baseline-dependent: AOIG to MIG gives a mean `-13.21%` change, while AIG to MIG gives a mean `+21.54%` change.
- Target-layer AvgDP is `1.000` across LUT/AOIG, AIG, and MIG for the evaluated circuits.
- ARX primitives produce broader output corruption per detected fault than substitution-based primitives: `2.06` versus `1.08` output bits on average, ratio `1.90x`.
- Synthetic MAJ-3/5/7 experiments show `18-62%` AvgDP reductions with higher arity in matched chains and trees.

## Repository Layout

```text
data/cipher_blif/          input BLIF circuits
src/fault/dfa/             BLIF parser, simulator, and fault injection code
scripts/                   experiment and summary scripts
results/fpga_benchmark/    frozen AOIG/AIG/MIG BLIFs and FPGA metric JSONs
results/fault_coverage/    frozen fault-campaign JSONs
vivado/                    optional Vivado metrics TCL
reproduce.sh               one-command reproduction entry point
```

## Quick Start

```bash
python3 -m pip install -r requirements.txt
./reproduce.sh
```

By default, `reproduce.sh` recomputes the active summaries from the shipped
frozen JSON outputs and verifies the paper-facing headline numbers. This is the
recommended artifact check for reviewers.

Use `./reproduce.sh --full` to rerun the fault campaigns and regenerate the AIG
granularity-control data. Full regeneration requires `yosys`; the decomposed
AIG controls are sensitive to the exact Yosys/ABC version, so the paper-facing
numbers are guarded against the shipped frozen outputs.

## Key Commands

```bash
# Recompute summary metrics from existing JSONs and verify headline numbers
./reproduce.sh

# Rerun the full gate-output fault campaign
python3 scripts/run_fault_coverage.py

# Rerun the AIG granularity control; requires yosys
python3 scripts/granularity_baseline.py

# Recompute target-layer and ARX/substitution controls
python3 scripts/invariant_metric.py

# Rerun synthetic MAJ-n experiments
python3 scripts/maj_arity_fault_study.py
```
