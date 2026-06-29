# Installation

## Python

Use Python 3.10 or newer.

```bash
python3 -m pip install -r requirements.txt
```

The Python path installs NumPy and Matplotlib. NumPy is required for the vectorized fault simulator. Matplotlib is only needed for optional local plotting or MAJ-n study extensions.

## Optional Tools

`yosys` is required only if you want to regenerate the AIG BLIF controls with:

```bash
python3 scripts/granularity_baseline.py
```

Vivado 2023.2 is required only if you want to rerun FPGA implementation metrics using `vivado/run_metrics.tcl`. The repository already includes frozen BLIFs and JSON outputs needed for the fault-observability experiments.

## Verify The Artifact

```bash
./reproduce.sh
```

This recomputes the active summaries from the shipped frozen JSON outputs and
verifies the paper-facing headline numbers.

For full regeneration of the fault campaigns and AIG controls:

```bash
./reproduce.sh --full
```

The full workflow is slower and expects `yosys` on `PATH`. The AIG
granularity-control regeneration is sensitive to the exact Yosys/ABC version;
the paper-facing numbers are therefore checked against the frozen outputs
included in the repository.
