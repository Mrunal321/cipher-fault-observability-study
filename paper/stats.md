# Statistical Analysis

Companion to `paper/verified_numbers.md`. All tests below are computed
on the 15 paired observations in `results/fault_coverage/fault_coverage_results.json`.

scipy was not installed in the artifact's environment; the Wilcoxon
signed-rank test was computed with a hand-coded ranking using the
normal approximation, and the Mann-Whitney U test was computed by
exact enumeration (feasible at n=10). The artifact's `requirements.txt`
should pin scipy ≥ 1.10 before submission so reviewers can rerun
these as a single line.

---

## 1. AOIG vs MIG AvgDP — paired test on 15 circuits

**Hypothesis.** MIG-style synthesis reduces the mean per-vector fault
detection probability (AvgDP) on these cipher primitives compared with
the Yosys LUT4 AOIG baseline.

**Data.** Paired AvgDP per circuit, taken from
`fault_coverage_results.json` field `flows.<flow>.avg_det_prob`.
Per-circuit values are in `verified_numbers.md` §1.

### Absolute delta (MIG − AOIG)

| Quantity | Value |
|----------|------:|
| n | 15 |
| mean | **−0.1318** |
| stdev | 0.0914 |
| SEM | 0.0236 |
| t critical, df=14, α=0.05 two-sided | 2.1448 |
| **95 % CI** | **[−0.1824, −0.0812]** |

### Relative delta (MIG − AOIG) / AOIG

| Quantity | Value |
|----------|------:|
| n | 15 |
| mean | **−13.00 %** |
| stdev | 9.56 % |
| SEM | 2.47 % |
| **95 % CI** | **[−18.29 %, −7.71 %]** |

The 95 % CI excludes zero on both the absolute and relative scales, so
the AOIG → MIG AvgDP reduction is significantly different from zero at
α = 0.05 under the paired t assumption.

### Wilcoxon signed-rank (paired, distribution-free)

Computed manually (scipy not installed); normal approximation for p-value.

| Quantity | Value |
|----------|------:|
| n (non-zero differences) | 15 |
| sum of positive ranks W+ | 3.00 |
| sum of negative ranks W− | 117.00 |
| W = min(W+, W−) | 3.00 |
| μ_W = n(n+1)/4 | 60.00 |
| σ_W = √(n(n+1)(2n+1)/24) | 17.6068 |
| z | −3.2374 |
| **p (two-sided, normal approx)** | **0.00121** |
| p (one-sided: MIG < AOIG)         | 0.000603 |

The Wilcoxon test is the right test here because (i) n = 15 is too
small to assume normality safely, (ii) the observations are paired by
circuit, and (iii) the test makes no parametric assumptions on the
underlying delta distribution. Both the parametric (t-based CI) and
nonparametric (Wilcoxon) analyses agree the effect is significant at
p < 0.005.

### What the test does *not* say

The test confirms that the AvgDP reduction is statistically distinguishable
from zero on this benchmark. It does **not** establish:

- that the effect generalizes beyond cipher primitives of this size and
  family — generalization to larger or different circuits is an open
  empirical question, not a statistical one;
- that lower AvgDP implies lower DFA key-recovery success rate —
  observability is one input to attack success, not a proof of
  resistance.

These limitations are stated in §5 (Discussion) of the paper.

---

## 2. ARX vs substitution-based AvgBW — between-group test

**Hypothesis.** ARX cipher primitives exhibit broader output corruption
(AvgBW) per detected fault than substitution-based primitives.

**Data.** Per-circuit AvgBW on the MIG flow, grouped by family.

| Group     | n | mean   | stdev  | min   | max   | values                                  |
|-----------|--:|-------:|-------:|------:|------:|-----------------------------------------|
| ARX       | 3 | **2.056** | 0.298 | 1.712 | 2.238 | 1.712, 2.217, 2.238                     |
| Subst.\*  | 7 | **1.082** | 0.194 | 1.000 | 1.520 | 1.000, 1.000, 1.000, 1.000, 1.008, 1.045, 1.520 |

\* "Substitution-based" = 4-bit S-box (n=4) ∪ Subst. round (n=3).

**Ratio**: 2.056 / 1.082 = **1.90×**.

### Mann-Whitney U (exact, no ties between groups)

Every ARX value (min 1.712) exceeds every substitution-based value
(max 1.520), so the Mann-Whitney rank sum for ARX is at its maximum
(W_ARX = 27, U_ARX = 21 = n₁·n₂). With no ties between the two groups,
the exact one-sided p-value is

$$ p_{\text{one-sided}} = \binom{n_1 + n_2}{n_1}^{-1} = \binom{10}{3}^{-1} = \frac{1}{120} = 0.0083 $$

| Quantity | Value |
|----------|------:|
| U (ARX > Subst) | 21 (max) |
| n₁ (ARX), n₂ (Subst) | 3, 7 |
| **p (one-sided, exact)** | **0.0083** |
| p (two-sided, exact) | 0.0167 |

### What the test does *not* say

The sample is small (3 ARX primitives, 7 substitution-based) and the
"substitution-based" pool aggregates two architecturally-distinct
sub-families (4-bit S-boxes and substitution rounds). The result is
suggestive but not definitive evidence that *all* ARX designs exhibit
broader avalanche; it is best read as a hypothesis-generating
observation about the three ARX primitives we measured. The paper
states this scope explicitly in §4.

---

## 3. mMIG vs MIG AvgDP — confirmatory equivalence

For completeness, the paired AvgDP delta between mMIG and MIG (not the
headline of the paper, but used to back the §5 equivalence claim):

| Quantity | Value |
|----------|------:|
| n | 15 |
| max |abs delta| | 6 × 10⁻⁴ |
| Wilcoxon W (two-sided) | 6 (out of n=15) |
| ratio of changes within numerical noise | 15/15 |

The per-circuit AvgDP values in `verified_numbers.md` §1 differ between
MIG and mMIG by at most 6 × 10⁻⁴ in absolute terms (e.g. `prince_mprime`
0.8998 vs 0.9004), with no consistent sign. This is consistent with the
empirical Jaccard = 1.000 fault-equivalence result and is below the
noise floor of the 10,000-random-vector sampling.

---

## 4. MAJ-n synthetic study — no inferential test, by design

The MAJ-n results in `verified_numbers.md` §4 are not inferential.
They are deterministic AvgDP values measured on a single synthetic
circuit per (arity, topology) configuration, with input vectors
enumerated exhaustively over the gate's true input space. No
variability, no error bars, no test — the comparison is mechanical, not
sampled. The paper presents them as **theoretical-ceiling experiments**,
not as an evaluated synthesis flow.

---

## Reproducing these numbers

Re-run from a Python ≥ 3.10 environment with scipy installed:

```python
import json, scipy.stats as st
from statistics import mean, stdev
fc = json.load(open("results/fault_coverage/fault_coverage_results.json"))
aoig = [r["flows"]["aoig"]["avg_det_prob"] for r in fc]
mig  = [r["flows"]["mig"]["avg_det_prob"]  for r in fc]

# Wilcoxon
print(st.wilcoxon(aoig, mig))

# 95% CI on relative delta
import math
rels = [(m - a) / a * 100 for a, m in zip(aoig, mig)]
n = len(rels)
sem = stdev(rels) / math.sqrt(n)
tcrit = st.t.ppf(0.975, df=n - 1)
print(mean(rels), [mean(rels) - tcrit*sem, mean(rels) + tcrit*sem])
```

Both should match the values in this file to four significant figures.
Any drift indicates a JSON regeneration has changed the underlying data.
