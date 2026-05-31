# Installation & Setup

## Python environment

Python 3.10+ with:

```bash
pip install -r requirements.txt
```

This installs:
- `numpy >= 1.24` (vectorized fault simulation)
- `matplotlib >= 3.7` (figure generation)

No other Python dependencies are required for the fault-analysis or
paper-artifact-generation paths.

## blif2mig_2 binary (only needed for the FPGA flow)

The FPGA campaign (`scripts/run_jetc_benchmark.py`) invokes our
`blif2mig_2` synthesis tool, built from a fork of the mockturtle logic
synthesis library that adds the mMIG optimization passes. The
fault-analysis path does **not** need this — it uses the frozen
optimized BLIFs in `results/fpga_benchmark/`.

To rebuild from source:

```bash
# 1. Clone the base mockturtle at the right commit.
git clone https://github.com/lsils/mockturtle.git
cd mockturtle
git checkout 9f3a6c94327ee26a7cdcd998a38f5bb2131b956a

# 2. Apply our mMIG patch (shipped in the artifact at vendor/).
git apply --reject /path/to/artifact/vendor/mockturtle-mmig.patch

# 3. Build blif2mig_2.
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DMOCKTURTLE_EXAMPLES=ON
cmake --build . --target blif2mig_2 -j$(nproc)
# Binary appears at build/examples/blif2mig_2
```

See [vendor/README.md](vendor/README.md) for details on the patch
(204 KB, 6346 lines, against commit
`9f3a6c94327ee26a7cdcd998a38f5bb2131b956a`).

The MIG optimization flow used in the paper is area-mode
`dac19_compat` (`--mode=area --mig-flow=dac19_compat`): a fixed schedule
of stock mockturtle passes — algebraic depth rewriting, MIG
resubstitution, cut rewriting with `mig_npn_resynthesis`, and
refactoring. The exact 18-step schedule is reproduced in the paper
(§3, Table "MIG schedule"); the invocation is `run_mig()` in
[scripts/run_jetc_benchmark.py](scripts/run_jetc_benchmark.py). No
minority gates are introduced (the mMIG path is not used in this paper).

## Vivado (only needed for the FPGA flow)

Vivado 2023.2 (or any version supporting Spartan-7 `xc7s100fgga676-2`).
The `vivado` command must be on `$PATH`, or installed at one of the
standard locations:
- `/tools/Xilinx/Vivado/<version>/bin/vivado`
- `/opt/Xilinx/Vivado/<version>/bin/vivado`
- `/usr/local/Xilinx/Vivado/<version>/bin/vivado`

The benchmark script auto-discovers Vivado at any of these paths.

The TCL script at [vivado/run_metrics.tcl](vivado/run_metrics.tcl) is
self-contained and runs in Vivado batch mode (`vivado -mode batch -source`).
It does the synthesis, place, and route, then writes a JSON of metrics
(LUT counts, logic levels, delay breakdown, dynamic power).

## LaTeX (only needed to build the paper PDF)

TeX Live ≥ 2022 with `IEEEtran` document class and the `tikz`,
`booktabs`, `siunitx`, `microtype`, and `hyperref` packages.

```bash
cd paper/tex
pdflatex main && bibtex main && pdflatex main && pdflatex main
# main.pdf is the 6-page submission draft.
```

Compile once on a TeX-enabled machine before submission and inspect
warnings. The repository intentionally still contains TODO placeholders
for the author block, public artifact URL, acknowledgments, and several
bibliography entries.

## yosys (optional)

Only the AOIG flow's BLIF→Verilog conversion uses yosys. If you only
want to reproduce the fault-analysis results, yosys is not required.

```bash
sudo apt install yosys      # Ubuntu/Debian
brew install yosys          # macOS
```

## Verifying the install

After the above:

```bash
cd /path/to/mmig-host-artifact

# Smoke test: should complete in under a minute and writes a subset
# aggregate JSON instead of clobbering the canonical 15-circuit file
python3 scripts/run_fault_coverage.py --circuits present_sbox

# Headline-number consistency check
python3 scripts/verify_headline_numbers.py

# Regenerate all paper artifacts from frozen JSONs
python3 scripts/gen_paper_tables.py
python3 scripts/gen_paper_figures.py
ls paper/tables/   # expect generated .tex tables
ls paper/figures/  # expect generated .pdf + .png figures
```

If `gen_paper_figures.py` complains about LaTeX rendering, comment out
the `text.usetex` setting in that file's `plt.rcParams.update(...)`
block — the default uses matplotlib's mathtext, no system LaTeX needed.
