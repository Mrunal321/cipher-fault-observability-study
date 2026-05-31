# HOST 2026 Paper Outline

**Working title**: *How Much of Synthesis-Induced Fault Behavior Is Real?
A Granularity-Controlled Study of Majority-Based Cipher Circuits*

## Core Message

All-site gate-output fault metrics are strongly affected by representation
granularity. The original LUT/AOIG→MIG AvgDP reduction is reproducible, but
it reverses under a same-granularity AIG baseline. The defensible contribution
is therefore methodological: report fault metrics with the fault-site
population and use controlled baselines before claiming synthesis-induced
fault resistance.

## Findings

1. **Baseline sign flip**: LUT/AOIG→MIG gives a mean −13.0% AvgDP change
   on 13/15 circuits, but AIG→MIG gives +21.44% with 0/15 reductions.
2. **Target-layer invariant**: restricting faults to output-driving gates
   yields target-layer AvgDP = 1.000 across LUT/AIG/MIG/mMIG on the evaluated
   circuits.
3. **mMIG/MIG equivalence**: faulty-output sets are identical on every tested
   vector (Jaccard = 1.000), so mMIG's inverter reduction can be applied
   where it changes inverter count without changing measured fault behavior.
4. **Architecture-level ARX breadth**: ARX primitives show about 1.9x broader
   output corruption than substitution-based primitives across representations.
5. **Forward path**: synthetic native MAJ-5/MAJ-7 experiments reduce AvgDP
   relative to MAJ-3 in matched topologies, motivating native MAJ-n library
   evaluation rather than inference from MAJ-3 decompositions.

## Section Plan

1. **Introduction**: motivate synthesis-flow fault metrics, then introduce
   representation granularity as the confound.
2. **Background**: AOIG/LUT, AIG, MIG, mMIG; DFA observability metrics; MAJ-n
   context.
3. **Benchmark, Metrics, and Methodology**: 15 circuits, four representations,
   all-site vs target-layer metrics, single gate-output bit-flip simulator.
4. **Results**:
   - Granularity confound and sign flip:
     `paper/tables/granularity_confound.tex`,
     `paper/figures/granularity_curve.pdf`
   - Target-layer invariant:
     `paper/tables/representation_robustness.tex`
   - MIG/mMIG equivalence:
     `paper/tables/dualrail_equivalence.tex`,
     `paper/figures/dualrail_jaccard.pdf`
   - ARX breadth:
     `paper/tables/arx_dichotomy.tex`,
     `paper/figures/arx_dichotomy.pdf`
   - MAJ-n forward path:
     `paper/tables/majn_arity.tex`
5. **Discussion**: reporting guidelines, robust claims, limits.
6. **Conclusion**: all-site metrics need controlled baselines; robust findings
   remain useful.

## TODO Before Submission

- [ ] Author block, affiliations, acknowledgments.
- [ ] Public artifact URL in methodology and conclusion.
- [ ] Camera-ready citation in `README.md`.
- [ ] Verify bibliography entries and remove TODO notes in `references.bib`.
- [ ] Compile `paper/tex/main.tex` on a TeX-enabled machine and fix page-budget
      or float issues.
- [ ] Decide whether to retain supporting old AOIG/MIG tables in the artifact
      only, or include them in an appendix/supplement.
