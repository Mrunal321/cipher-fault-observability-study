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

## Run Everything

```bash
./reproduce.sh
```

For a full recomputation of the fault campaign and AIG control:

```bash
./reproduce.sh --full
```

Full mode is slower and expects `yosys` on `PATH`.
