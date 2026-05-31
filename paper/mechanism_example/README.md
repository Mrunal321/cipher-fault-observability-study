# Worked Masking Example

Companion to §3 of the paper. Concrete trace of one bit-flip fault
through one downstream MAJ3 gate, with every input vector enumerated,
to make the non-controlling-input masking mechanism inspectable rather
than asserted.

## Files

- `trace.json` — machine-readable per-vector trace, generated from
  `results/fpga_benchmark/present_sbox/present_sbox_mig_maj_opt.blif`
  by enumerating all 16 inputs of `present_sbox` and forcing a
  BIT_FLIP at `new_n12`. Fields:
  - `circuit`, `flow`, `fault_site`, `downstream`
  - `fanout_of_g` = 1  (the fault has exactly one downstream consumer,
    which is what makes the trace clean)
  - `n_test_vectors` = 16
  - `masking_at_h` = 8, `propagating_at_h` = 8, `reaching_PO` = 8
  - `dp` = 0.5 (matches the theoretical MAJ3 per-input masking
    probability)
  - `trace[]` = 16 per-vector rows
- `figure_masking.tex` — tikz source for Fig.~\ref{fig:masking-example}
  in §3 of the paper. Draws $g$ (fault site, MAJ3 with bubble on the
  downstream edge), the inputs to $h$, $h$ itself, and an annotation
  with the masking rule.
- `table_trace.tex` — LaTeX source for Tab.~\ref{tab:masking-trace}, a
  16-row trace that the reader can verify line by line.

## Why this example

We wanted a single fault site whose dp would be determined entirely by
masking at one downstream gate, with no multi-path complications. The
search criteria were:

1. Pick a fault site $g$ with exactly one downstream consumer (so
   $\mathrm{dp}(g)$ is a pure function of how that consumer behaves).
2. The consumer $h$ must be a 3-input gate so the masking has a clean
   "non-controlling" interpretation.
3. The dp value should be 0.5 — the theoretical MAJ3 per-input masking
   probability — so the example matches the prediction exactly.

The pair `new_n12 → new_n15` in `present_sbox` MIG satisfies all
three. We checked every gate in the netlist; 11 satisfy (1) and (2);
this one is the closest to dp = 0.5 (it's exactly 0.5).

## Cross-check

To regenerate `trace.json`:

```bash
python3 -c "
import sys, json, numpy as np
sys.path.insert(0, 'src'); sys.path.insert(0, 'scripts')
from fault.dfa.blif_parser import parse_blif_file
from run_fault_coverage import build_luts, sim_vectorized

c = parse_blif_file('results/fpga_benchmark/present_sbox/present_sbox_mig_maj_opt.blif')
luts = build_luts(c)
N = 16
mat = np.array([[(i >> (3 - j)) & 1 for j in range(4)] for i in range(N)], dtype=np.uint8)
ff = sim_vectorized(c, luts, mat)
flipped = (ff['new_n12'] ^ 1).astype(np.uint8)
f  = sim_vectorized(c, luts, mat, overrides={'new_n12': flipped})
diff = sum((f[o] != ff[o]).astype(int).sum() > 0 for o in c.outputs)
print('vectors with PO diff:', sum(1 for i in range(N) if any(f[o][i] != ff[o][i] for o in c.outputs)))
"
# Expect:  vectors with PO diff: 8
```

The number 8 anchors the example: 8 vectors mask, 8 propagate, dp = 0.5,
matches the MAJ3 theoretical prediction.
