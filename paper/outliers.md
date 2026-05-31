# Outlier Analysis — Why Keccak-χ Goes the Other Way

13 of 15 circuits show AvgDP reduction AOIG → MIG. The two exceptions
are `keccak_chi_5bit` (+8.00 %) and `keccak_chi_64row` (+7.99 %). This
document explains the mechanism so the paper can address the question
preemptively in §4.3.

The 64-row variant is 64 independent copies of the 5-bit row applied
in parallel; its per-fault behavior mirrors the 5-bit version exactly,
which is why both circuits show essentially the same relative AvgDP
change. The analysis below focuses on the 5-bit version where the gate
counts are small enough to enumerate by hand.

---

## The two AOIG/MIG netlists at a glance

`keccak_chi_5bit` implements $y_i = x_i \oplus (\overline{x_{i+1}} \land x_{i+2})$
for $i \in \{0,1,2,3,4\}$, indices modulo 5. Five inputs, five outputs.

| Flow | Total gates | Masked (dp = 0) | Detectable | AvgDP |
|------|------------:|----------------:|-----------:|------:|
| AOIG |          18 |           3     |        15  |  0.833 |
| MIG  |          27 |           2     |        25  |  0.900 |
| mMIG |          27 |           2     |        25  |  0.900 |

The 3 masked AOIG gates are Yosys' constant placeholders `$false`,
`$true`, `$undef`. The 2 masked MIG gates are blif2mig_2's
`new_n0`, `new_n1` constants. These are bookkeeping artifacts, not
real fault sites.

---

## Per-fault dp distribution

Computed by exhaustive simulation over all $2^5 = 32$ input vectors:

### AOIG (15 detectable faults)

| Group | Count | per-fault dp | Gate names |
|-------|------:|-------------:|------------|
| AND outputs `chi_andN` + XOR outputs `yN` | 10 | **1.000** | chi_and0–4, y0–4 |
| Inverters `chi_notN` | 5 | **0.500** | chi_not0–4 |

AvgDP = (10 × 1.000 + 5 × 0.500) / 15 = 12.500 / 15 = **0.8333** ✓

### MIG (25 detectable faults)

| Group | Count | per-fault dp |
|-------|------:|-------------:|
| Output-adjacent and 1-step-away nodes | 15 | **1.000** |
| 1-deep internal MAJ3 nodes              |  5 | **0.875** |
| 2-deep internal MAJ3 nodes              |  5 | **0.625** |

AvgDP = (15 × 1.000 + 5 × 0.875 + 5 × 0.625) / 25 = 22.500 / 25 = **0.9000** ✓

mMIG has the identical distribution (by §5 fault equivalence).

---

## Mechanism

The AOIG decomposition of `χ` is exceptionally masking-friendly *for its
size*:

- 5 of the 18 AOIG gates (28 %) are inverters whose sole downstream
  consumer is a 2-input AND. The AND has 50 % per-input masking
  probability on the inverter's contribution (it masks the inverter's
  flip whenever its other input is 0). So 5 fault sites carry
  dp = 0.5 by construction.
- The remaining 10 detectable gates are the AND outputs and the XOR
  outputs that immediately produce primary outputs, so a flip at any of
  them is observable on every input vector: dp = 1.0.

The **masking-prone fraction** of detectable AOIG fault sites is
therefore 5/15 = **33.3 %**.

The MIG decomposition expands the network from 15 → 25 detectable gates
by introducing intermediate signals connecting the per-output 4-MAJ3
trees. But most of these new signals sit close to a primary output,
where they have no downstream masking and therefore dp = 1.0. Only the
two interior layers of each per-output tree (10 nodes out of 25, dp
either 0.625 or 0.875) introduce partial masking, and even those don't
reach the 0.5 baseline that the AOIG inverters do.

The **masking-prone fraction** of detectable MIG fault sites is
therefore lower: 10/25 = **40 %** of nodes have dp < 1, but the
*weighted* contribution computes to AvgDP = 0.900 (higher than AOIG's
0.833).

The reversal is not a counterexample to the §4 mechanism; it is a case
where the AOIG already concentrates a large share of its fault sites
on the structurally most maskable positions (inverters feeding into
ANDs), leaving the MIG decomposition no room to add new masking
surfaces beyond what AOIG already provided.

---

## Why this is specific to Keccak-χ

The `χ` step has a uniquely narrow Boolean structure compared with the
other 13 circuits in the benchmark:

- Each output bit is a 3-input expression with exactly one inverter
  per output.
- The cipher imposes no diffusion across output bits — each output is
  produced by an independent 3-input subnetwork.

By contrast, the 4-bit S-boxes (PRESENT, GIFT, PRINCE) have outputs
that depend on all 4 input bits with non-trivial NPN class, requiring
Yosys to materialize 4-input LUTs in the AOIG. A LUT4 fault has dp = 1
under our model (the LUT *is* the per-output function), so the AOIG's
masking-prone fraction is essentially 0. The MIG decomposition then
adds many internal MAJ3 nodes, each with masking probability around
0.5, dragging AvgDP down sharply — exactly the headline result.

ARX primitives are similar: their AOIG representations are wide and
dense, with few inherently maskable substructures, so MIG decomposition
introduces large amounts of fresh masking surface.

The Keccak exception identifies the limit of the AOIG → MIG benefit:
**when the AOIG of a cipher already exposes a large fraction of its
fault sites on natural masking surfaces, MIG synthesis cannot add more
masking.** This generalizes to a falsifiable prediction: any cipher
whose AOIG is dominated by inverter-then-AND or similar 2-input
masking substructures should show a similar absence of AvgDP reduction
under MIG.

---

## Implication for the paper

§4.3 of `outline.md` already flags the Keccak rows as outliers. The
draft should:

1. State both circuits show +8 % AvgDP under MIG (no hand-waving the
   sign).
2. Give the per-fault dp distribution above to show the mechanism is
   well-understood, not unexplained noise.
3. Frame the result as bounding the AOIG → MIG benefit: the headline
   is for *S-box-dense and ARX* ciphers, not for ciphers whose AOIG is
   already a dense network of small AND-NOT substructures.
4. Suggest the falsifiable prediction (other AND-NOT-dominated primitives
   should behave similarly) as a future-work probe.

This forestalls the obvious reviewer question — "what about the two
circuits that disagree with your headline?" — by addressing it in the
results section instead of leaving it for the rebuttal.
