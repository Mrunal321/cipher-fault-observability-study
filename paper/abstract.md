# Abstract Draft

**Working title:** *How Much of Synthesis-Induced Fault Behavior Is Real?
A Granularity-Controlled Study of Majority-Based Cipher Circuits*

Recent fault-characterization studies inject single-bit faults at gate
outputs and compare per-vector observability metrics across synthesis flows.
We show that, as commonly applied, these metrics are strongly confounded by
the granularity of the gate-level representation.

Using 15 cipher primitives from PRESENT, GIFT, PRINCE, SIMON, Keccak-χ, and
Speck/ARX, we compare truth-table LUT, 2-input AIG, MIG, and mMIG
representations under the same gate-output bit-flip model. The apparent
benefit of majority synthesis reverses sign with the baseline: relative to
the LUT-style AOIG baseline, MIG reduces AvgDP by 13.0% on average; relative
to a same-granularity AIG baseline, MIG increases AvgDP by 21.4%, with no
circuit showing a reduction.

Restricting faults to output-driving gates yields target-layer AvgDP = 1.000
across all four representations on the evaluated circuits. Two findings remain robust to
representation: ARX primitives exhibit about 1.9× broader output corruption
per detected fault than substitution-based primitives, and mMIG is
empirically fault-equivalent to MIG on every tested vector while reducing
inverters where minority insertion applies.

We conclude with reporting guidelines for synthesis-flow fault metrics and
release all netlists, campaigns, generated tables, and headline-number checks.
