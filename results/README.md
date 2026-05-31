# Frozen Result Data

## `fpga_benchmark/<circuit>/`

For each of the 15 circuits, three subdirectories `aoig/`, `mig/`, `mmig/`
contain Vivado metric JSONs with this schema:

```json
{
  "synth_luts":        int,    "synth_lut1": int,
  "logic_levels":      int,    "impl_luts":  int,    "impl_lut1": int,
  "delay_ns":          float,  "logic_ns":   float,  "route_ns":  float,
  "logic_power_mw":    float,  "signal_power_mw": float,
  "dynamic_power_mw":  float
}
```

The top-level circuit directory also holds three optimized BLIF files
that the fault-analysis scripts read:

- `<circuit>_aoig.blif`              raw input (also used as AOIG baseline)
- `<circuit>_mig_maj_opt.blif`       MIG optimized (area-mode, dac19_compat)
- `<circuit>_mmig_mmig_opt.blif`     mMIG optimized (area + compress2rs + advanced + seeding)

**Note**: `keccak_chi_64row` has structural BLIFs but no Vivado metrics —
its 640 I/Os exceed the xc7s100fgga676-2 pin budget, so Vivado's IO placer
fails. Paper tables mark this row N/A.

## `fault_coverage/`

- `fault_coverage_results.json` — single-bit-flip campaign, 15 circuits × 3 flows
- `dualrail_diversity.json`     — per-input sensitivity Pearson correlation (MIG vs mMIG)
- `dualrail_equivalence.json`   — Jaccard test on faulty-output sets per input vector
- `granularity_baseline.json`   — same-granularity AIG→MIG control; reverses the
                                  LUT-baseline AOIG→MIG AvgDP sign
- `invariant_metric.json`       — target-layer and representation-robust checks
- `<circuit>_<flow>_fault.json` — per-circuit fault campaign details
- `majN/majN_fault_study.json`  — synthetic MAJ3/MAJ5/MAJ7 study (single gate, chain, tree)
- `majN/maj*.blif`              — synthetic BLIFs generated for the MAJ-n study

### Schema highlights

`fault_coverage_results.json`:
```json
{
  "circuit": "present_sbox",
  "flows": {
    "aoig|mig|mmig": {
      "total_faults":   int,        // gate-output fault sites
      "detectable":     int,        // faults observable on >= 1 vector
      "masked":         int,        // never observable
      "fault_coverage": percent,    // detectable / total
      "masking_rate":   percent,    // masked / total
      "avg_breadth":    float,      // mean output-bit Hamming distance per detection
      "avg_det_prob":   float,      // mean P(detect | fault) over test vectors
      "n_test_vectors": int
    }
  }
}
```

`dualrail_equivalence.json`:
```json
{
  "circuit": "present_sbox",
  "n_test_vectors":      int,
  "identical_per_input": int,       // # vectors where MIG and mMIG produce identical
                                    //   sets of reachable faulty outputs
  "identical_frac":      [0,1],
  "avg_jaccard":         [0,1],     // 1.0 = sets identical
  "mig_only_outputs":    int,       // outputs reachable only in MIG (= 0 everywhere)
  "mmig_only_outputs":   int,       // = 0 everywhere
  "diversity_present":   bool       // false on every circuit
}
```

`majN/majN_fault_study.json`:
```json
{
  "single": [ {"arity": 3, "theory_mask": float, "fault_coverage": ..., "avg_det_prob": ...}, ... ],
  "chain":  [ {"arity": 3, "depth": 5, ...}, ... ],
  "tree":   [ {"arity": 3, "depth": 3, ...}, ... ],
  "params": { "chain_depth": 5, "tree_depth": 3 }
}
```

## Reproducing

```bash
python3 scripts/run_fault_coverage.py        # rewrites all _fault.json + main results
python3 scripts/run_dualrail_diversity.py    # rewrites dualrail_diversity.json
python3 scripts/verify_dualrail_equiv.py     # rewrites dualrail_equivalence.json
python3 scripts/maj_arity_fault_study.py     # rewrites majN/
python3 scripts/granularity_baseline.py      # rewrites granularity_baseline.json + AIG BLIFs
python3 scripts/invariant_metric.py          # rewrites invariant_metric.json
```
