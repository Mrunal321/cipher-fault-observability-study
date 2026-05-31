# Abstract v2 (granularity-controlled reframe)

**Working title:** *How Much of Synthesis-Induced Fault Behavior Is Real?
A Granularity-Controlled Study of Majority-Based Cipher Circuits*

---

Recent work characterizes the fault behavior of cryptographic circuits by
injecting single-bit faults at gate outputs and measuring per-vector
observability metrics across synthesis flows. We show that such metrics, as
commonly applied, are confounded by a variable that has nothing to do with
fault resistance: the *granularity* of the gate-level representation.

Using 15 standard cipher primitives (PRESENT, GIFT, PRINCE, SIMON, Keccak-χ,
and Speck/ARX) under three representations — truth-table LUTs (AOIG), 2-input
AND-Inverter Graphs (AIG), and Majority-Inverter Graphs (MIG) — we demonstrate
that the average per-vector
fault detection probability (AvgDP) is strongly associated with decomposition
granularity (Spearman ρ = −0.85 between nodes-per-output and AvgDP). As a
direct consequence, the apparent "fault-masking benefit" of majority synthesis
**reverses sign with the choice of baseline**: a mean 13% AvgDP *reduction*
against an undecomposed LUT baseline becomes a 21% *increase* against a
same-granularity AIG baseline. The effect is baseline-dependent rather than a
standalone property of majority logic.

We then identify what *is* representation-invariant. Restricting faults to the
realisable adversarial target — the gates that drive primary outputs — yields a
target-layer AvgDP of exactly 1.000 across all three representations and all
evaluated circuits (mean spread 0.000): under a realistic targeted-fault model, synthesis
representation has no effect on fault observability. A further result is
robust to representation: ARX primitives exhibit ~1.9× the avalanche
breadth of substitution primitives, stable across all three flows, an
architecture-level rather than synthesis-level property.

We give guidelines for reporting fault metrics that are comparable across
synthesis flows, and release all netlists, campaigns, and analysis scripts.
