# Vendor — Mockturtle Patch

`mockturtle-mmig.patch` is the patch we apply to upstream
[mockturtle](https://github.com/lsils/mockturtle) to obtain the
`blif2mig_2` synthesis tool used by the FPGA benchmark
(`scripts/run_jetc_benchmark.py`).

## Base commit

```
9f3a6c94327ee26a7cdcd998a38f5bb2131b956a
```

## Contents

The patch adds:

- 12 new mMIG-specific algorithm headers under
  `include/mockturtle/algorithms/`: `mmig_optimizer.hpp`,
  `mmig_algebraic_rewriting.hpp`, `mmig_balancing.hpp`,
  `mmig_cec_guard.hpp`, `mmig_cone_polarity_flip.hpp`,
  `mmig_cut_rewriting.hpp`, `mmig_exact_rewriting.hpp`,
  `mmig_inv_optimization.hpp`, `mmig_inv_propagation.hpp`,
  `mmig_minority_seeding.hpp`, `mmig_refactoring.hpp`,
  `mmig_resubstitution.hpp`.
- The `blif2mig_2` example driver under
  `examples/blif2mig_2.cpp`.
- Eight modifications to existing files to register the new
  mMIG node traits, expose MIN3 handling in the Verilog reader/writer
  and BLIF I/O, and wire up the mMIG resubstitution pass.

## Applying the patch

```bash
# 1. Clone the base mockturtle at the right commit.
git clone https://github.com/lsils/mockturtle.git
cd mockturtle
git checkout 9f3a6c94327ee26a7cdcd998a38f5bb2131b956a

# 2. Apply the patch.  --reject leaves .rej files on any hunk that
#    fails so you can inspect them; the patch is generated cleanly
#    against the base commit and should apply without rejects.
git apply --reject /path/to/mockturtle-mmig.patch

# 3. Build blif2mig_2.
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DMOCKTURTLE_EXAMPLES=ON
cmake --build . --target blif2mig_2 -j$(nproc)

# 4. Use it:
./examples/blif2mig_2 input.blif output_base \
    --mode=area --mig-flow=dac19_compat \
    --enable-mmig --mmig-cec --mmig-advanced \
    --mmig-flow=compress2rs --mmig-advanced-rounds=3 \
    --mmig-seed=both --mmig-seed-budget=200 --mmig-seed-rounds=3
```

## Verifying the patch matches what produced the JSONs in results/

The frozen optimized BLIFs under `results/fpga_benchmark/*/`
were produced by this exact patched mockturtle. To verify on your
machine:

```bash
# Pick a small circuit
./examples/blif2mig_2 \
    data/cipher_blif/present/present_sbox.blif \
    /tmp/check_present_sbox \
    --mode=area --mig-flow=dac19_compat \
    --enable-mmig --mmig-cec --mmig-advanced \
    --mmig-flow=compress2rs --mmig-advanced-rounds=3 \
    --mmig-seed=both --mmig-seed-budget=200 --mmig-seed-rounds=3

diff /tmp/check_present_sbox_mmig_opt.blif \
     results/fpga_benchmark/present_sbox/present_sbox_mmig_mmig_opt.blif
# Should produce no output.
```

## Caveats

- The patch is generated with `git diff HEAD` after `git add -N`-ing
  the new files; binary diffs (none expected, but possible) are
  handled by including the `--binary` mode in the generation script.
- We do not include the standalone fork as a GitHub repository in
  this artifact; the patch is the canonical form. If a public fork
  exists at submission time, the README at the artifact root should
  link to it.
- Patch size: 204 KB, 6346 lines.
