# Metric Definitions

These three metrics characterize *different* aspects of fault behavior
and are not interchangeable. They can vary independently — e.g. a
circuit with higher FC% can have lower AvgDP, and that is not a
contradiction. The paper text reuses these exact definitions; this
file is the single source of truth.

Let $C$ be a combinational circuit with primary inputs $I$ and primary
outputs $O$. Let $G(C) = \{g_1, \dots, g_n\}$ be the set of internal
signals (each driven by one gate). Let $\mathcal{P}$ be the set of input
test vectors used (exhaustive when $|I| \le 20$; otherwise 10,000
random vectors).

For a vector $P \in \mathcal{P}$ and fault site $g \in G(C)$, let
$\text{out}(P)$ be the fault-free primary outputs and
$\text{out}_g(P)$ be the primary outputs when $g$ is bit-flipped.

A fault $g$ is *detected on $P$* iff $\text{out}_g(P) \ne \text{out}(P)$.
A fault $g$ is *detectable* iff it is detected on at least one
$P \in \mathcal{P}$.

## Fault Coverage (FC%)

$$
\mathrm{FC}(C) \;=\; \frac{|\{g \in G(C) : g \text{ is detectable}\}|}{|G(C)|} \times 100\%
$$

The fraction of fault sites that are observable for *some* input vector.
Bounded $[0\%, 100\%]$. Higher means more fault sites *can* in principle
be exploited.

## Average per-vector Detection Probability (AvgDP)

For each detectable fault $g$, define
$$
\mathrm{dp}(g) \;=\; \frac{|\{P \in \mathcal{P} : g \text{ is detected on } P\}|}{|\mathcal{P}|}
$$

Then
$$
\mathrm{AvgDP}(C) \;=\; \frac{1}{|\{g \text{ detectable}\}|} \sum_{g \text{ detectable}} \mathrm{dp}(g)
$$

The mean probability that a *random* test vector exposes a *random*
detectable fault. Bounded $[0, 1]$. Higher means each fault is
detected on a larger fraction of input space (more attack opportunities
per fault).

## Average Breadth (AvgBW)

For each (detectable) fault $g$ and detecting vector $P$, define the
Hamming distance
$$
\mathrm{hd}(g, P) \;=\; |\{ o \in O : \text{out}_g(P)[o] \ne \text{out}(P)[o] \}|
$$

Average across all (fault, vector) detection events:
$$
\mathrm{AvgBW}(C) \;=\; \frac{\sum_{g \text{ det.}} \sum_{P: g \text{ det on } P} \mathrm{hd}(g, P)}{\sum_{g \text{ det.}} |\{P: g \text{ det on } P\}|}
$$

The mean number of primary-output bits flipped when a fault is detected.
Bounded $[1, |O|]$. Higher means each detection event reveals more
output bits.

## How they vary independently

A circuit with many decomposed internal gates (MIG, mMIG) typically has
**high FC%** (many fault sites are reachable to the outputs) but **low
AvgDP** (each fault is masked on many inputs by downstream majority
gates).

A circuit with monolithic gates (AOIG LUT4) typically has **lower FC%**
(fewer total fault sites, and constants are not detectable) but **high
AvgDP** (each fault site is close to a primary output, so detection on
any given input is common).

AvgBW depends on the diffusion structure of the circuit itself
(carry chains, S-box width, permutation layers), and is largely
independent of FC% and AvgDP. Our ARX-vs-substitution result (§6) is
a finding about AvgBW only.

## What this paper does not measure

- **End-to-end key recovery success rate under DFA**: we measure fault
  observability, not algebraic exploitability of the resulting output
  differences. A circuit with higher AvgDP and higher AvgBW provides
  more raw fault information per query, but whether that information
  is algebraically useful for key recovery depends on the cipher's
  structure and round count (out of scope for this study).
- **Multi-bit, delay, or timing fault models**: BIT_FLIP at gate
  outputs only.
- **Transistor-level effects**: ionization tracks, glitch injection,
  voltage glitching — all out of scope.

We therefore use the term *fault observability reduction* (not "fault
countermeasure") for the AOIG → MIG effect, to keep the claim strictly
to what the metrics measure.
