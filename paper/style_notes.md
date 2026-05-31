# Writing-Voice Calibration — HOST / Fault-Attack Conference Style

Patterns extracted by reading full text or abstracts of recent papers
in the same neighborhood (HOST, TCHES, related venues). The paper
should match these patterns; original sentences only — do not copy
phrasing from the samples.

## Papers actually read (full text)

| Tag | Paper | Venue / arXiv |
|-----|-------|---------------|
| SYNFI  | Nasahl et al., *SYNFI: Pre-Silicon Fault Analysis of an Open-Source Secure Element* | TCHES 2022 / arXiv 2205.04775 |
| SCFI   | Nasahl et al., *SCFI: State Machine Control-Flow Hardening Against Fault Attacks* | ICCAD/DAC 2022 / arXiv 2208.01356 |
| HLS    | Koufopoulou et al., *Security and Reliability Evaluation of Countermeasures Implemented Using HLS* | DATE 2023 / arXiv 2312.06268 |

## Papers seen only as titles + abstracts (HOST 2025 program)

- "Betrayed by Light: How Photon Emission Microscopy Empowers Register Bit-Level Laser Attacks on Microcontrollers" (Perrin, Dutertre, Rigaud — HOST 2025, pp. 35–45)
- "ReFID: A System-Aware Remote Fault-Injection Attack Detection & Mitigation for Secure Heterogeneous System" (Shuvo et al. — HOST 2025, pp. 46–56)
- "ML-EMFI: A Machine Learning-Driven Pre-Silicon Electromagnetic Fault Injection Security Evaluation for Robust IC Design" (Sarker et al. — HOST 2025, pp. 57–66)

The three full-text papers are the source of every pattern below;
the abstract-only papers confirm topic framing and title conventions
but contribute nothing to the prose-level style analysis.

---

## 1. How the intro opens

Always with a one-sentence definitional claim in **present tense**:

- SYNFI §1: "In a fault attack, an adversary induces a fault into a chip to manipulate the execution of the circuit."
- SCFI §1: "Fault attacks are active, physical attacks that allow an adversary to manipulate the execution of a digital circuit."
- HLS §I: "High-Level Synthesis (HLS) tools can effectively enhance the productivity for the design of complex digital circuits…"

The pattern: *Subject* + *active verb* + *what it does*. No throat-clearing
("In the modern era of…"), no banner phrases. The reader learns what
the paper is about in one sentence.

The second sentence then adds the immediately-relevant detail (the
mechanism, or the consequence). The third sentence introduces the
problem.

**For our paper**: open §1 with one sentence defining DFA or the
synthesis-flow choice question, not with a preamble about
cryptographic hardware being important.

## 2. Contribution lists

Two valid forms. Pick one and stick to it.

**Bulleted (SYNFI):**
> In summary, our contributions are:
> - We present and implement SYNFI, an open-source framework capable of performing a pre-silicon fault analysis at the gate-level…
> - We identified several fault attack vectors for the unprotected AES module…
> - We verified with SYNFI that a selection of the most security-critical OpenTitan IP blocks hardened against faults provides the expected security…

Each bullet starts with **"We"** + a verb (`present`, `identify`,
`verify`, `evaluate`, `propose`). Past tense is used for *completed*
analytical work; present tense for *the artifact* being introduced.

**Prose paragraph (SCFI):**
> In this paper, we introduce SCFI, a scalable mitigation approach probabilistically protecting the control-flow of finite-state machines against multi-fault attacks. SCFI ensures that any control-flow deviation … is detected with a high probability …

Single dense paragraph, no bullets. Less common in HOST submissions —
the bulleted form is more idiomatic.

**For our paper**: bulleted contribution list. Four items
(observability reduction, mMIG equivalence, ARX dichotomy,
MAJ-n forward direction). Each starts with "We characterize…" /
"We show…" / "We identify…" / "We propose…" — declarative verbs, no
"we provide a comprehensive study of."

## 3. How results are reported

Three patterns coexist:

| Pattern | Use case | Example |
|---------|----------|---------|
| "We observe X" / "Our results show X" | Direct empirical claim | "Our evaluation shows that SCFI provides strong protection guarantees…" |
| "Our analysis revealed Y" (past tense) | Completed investigation | "Our in-depth analysis of the tested modules revealed that the AES module is highly susceptible to fault attacks." |
| "X holds for N/M circuits, with mean Y" (declarative present) | Tabulated quantitative summary | rare in intros, common in results sections |

The HOST register **avoids**:
- "we believe" in results paragraphs (acceptable in conclusion / future work)
- "we feel" anywhere
- "interestingly" / "surprisingly" as standalone adverbs

**For our paper**: results section §4 uses past tense for the
campaign ("We injected single-bit-flip faults at every gate output of
all 15 circuits across the three flows") and present tense for the
findings ("13 of 15 circuits show an AvgDP reduction…"). Avoid
"interesting" / "surprising"; let the numbers carry the surprise.

## 4. Figure / table captions

Captions are **complete sentences**, not noun phrases. They open with
a noun phrase describing the artifact and then expand into one or two
sentences of context.

SCFI examples:
- Fig 1: "General structure of a state machine." (very short — for a definitional figure)
- Fig 3: "Mapping of valid and invalid input tuples to a valid or invalid next state." (descriptive, one sentence)

SYNFI is longer:
- Captions of 3–4 sentences describing exactly what is plotted, the axes' meaning, and the takeaway.

**For our paper**: a measurement figure caption should say what is on
each axis, what each color/series means, and the one-sentence
takeaway. Table captions should additionally state which JSON the
numbers come from (so the reader knows the data lineage).

Don't write captions as instructions ("As shown in Figure X, …"); let
the caption stand alone.

## 5. Threat-model and scope statements

When present as a dedicated section (SCFI §3), the threat model:
- Opens with: "We consider a powerful adversary capable of…"
- Names the attacker's capabilities concretely (number of faults, spatial/temporal granularity, fault model).
- Distinguishes attacker description from assumptions: SCFI §3.1 "Attacker Description".

SYNFI doesn't have a dedicated section — it threads the threat model
through §1 and §2 with sentences like "fault models comprising single
and multiple faults injected into various locations."

**For our paper**: dedicated short threat-model paragraph in §3 (no
need for a whole section at our page budget). Pattern:
> *We assume an adversary who can inject one BIT_FLIP fault per
> evaluation at any single gate output of the combinational netlist
> and observe the corresponding primary outputs. We do not model
> multi-bit, delay, or transistor-level faults; these are out of
> scope.*

Note the explicit "out of scope" clause — HOST reviewers expect this.

## 6. Citation density and placement

- Intro: 1–2 citations per paragraph, clustered after a claim:
  "fault attacks have been demonstrated against [X, Y, Z]".
- Related work: dense — 5+ citations per paragraph, each tied to a
  specific contrast or comparison.
- Methodology: sparse — only for prior techniques being reused.
- Results: very sparse — typically zero unless comparing numbers.
- Discussion / future work: medium density.

Both citation styles appear in the corpus: TCHES-style alphanumeric
keys (`[BS97, PQ03, DEK+18]`) and ACM-style numerics (`[15, 20, 21]`).
HOST uses **numeric**, ordered by appearance, via `IEEEtran.bst`.

**For our paper**: numeric, IEEEtran. Aim for 18–25 references in 6
pages; cluster citations at the end of multi-source claims rather
than inline.

## 7. Hedging — where and how much

Hedging is **rare** and lives in three specific places:

1. **Limitations / scope**: "We do not model X." / "This is out of
   scope."
2. **Generalization claims**: "These results suggest that…" not "These
   results prove that…"
3. **Forward-looking statements** (future work, conclusion):
   "We believe / expect / anticipate…" — allowed only outside the
   measurement sections.

In measurement sections, statements are flat declarative:
- ✓ "AvgDP drops by 13.0 % on average."
- ✗ "Our measurements indicate that AvgDP appears to drop by approximately 13 % on average."

## 8. Field vocabulary the paper should use

Terms of art from the HOST register, used the way the corpus uses them:

| Term | Meaning in context |
|------|--------------------|
| fault site | gate output (or wire) where a fault is injected |
| fault cone | the set of primary outputs a fault can influence |
| fault model | the formal specification (BIT_FLIP, stuck-at, transient, …) |
| controlling input | a value that determines a gate's output regardless of other inputs |
| non-controlling input | the complementary state — the input would matter |
| input-output relation | the function the circuit implements |
| post-synthesis netlist | the gate-level netlist after synthesis |
| observability / observable | whether a fault can be seen at primary outputs |
| propagation | the act of a fault reaching primary outputs |
| countermeasure | any hardware-level defense against an attack |
| evaluation testbench | the simulation harness used to inject faults |

Use these, not paraphrases. Don't write "the chance the fault is
caught" when you mean "the per-vector detection probability."

## 9. Banned phrases and AI tells

The user's bar removes these — they appear in some HOST papers but
read as filler. Avoid in *our* paper:

- "delve" — never
- "leverage" / "leverages" — replace with "use" or "exploit"
- "moreover" / "furthermore" — replace with a paragraph break or a
  direct connector ("This implies…")
- "it is important to note that" — delete
- "plays a crucial role" — replace with the specific role
- "in the realm of" — delete
- "comprehensive" as a self-adjective — never describe our own work
  that way
- "novel" — describe the actual difference instead
- Restating the previous sentence in different words — write each
  point once

## 10. Paragraph rhythm

The corpus papers vary paragraph length deliberately:
- **Topic-statement paragraphs** (start of a section): 2–3 sentences,
  lead with the claim.
- **Walk-through paragraphs** (middle of a methodology section): 5–8
  sentences, technical detail.
- **Closing paragraphs** (end of a section): 2–4 sentences,
  summarize and bridge.

Do not write uniform three-sentence paragraphs throughout. Let the
material dictate the length.

## 11. Voice summary for our paper

The paper should read as if a senior PhD student in hardware security
wrote it: precise, declarative, willing to state limitations
explicitly, and unafraid to flag a negative-but-useful boundary
result (the mMIG equivalence). Every quantitative claim carries a
verified number and a scope qualifier in the same sentence; every
mechanism claim has a concrete supporting example (the worked masking
trace in §3 anchors §4). Avoid adjectives where a measurement exists.

## 12. Sample paragraphs in this register

For calibration, here are *original* paragraphs in the target register
that match the patterns above. These are not copied from any paper —
they are model outputs in our voice.

### Sample intro opening (10 lines)

> Differential Fault Analysis recovers cryptographic secrets by
> inducing transient faults during cipher execution and comparing the
> resulting corrupted outputs against correct ones. The information
> available to the attacker — how many fault sites a circuit exposes,
> how often a random input vector reveals each fault, and how many
> output bits each fault corrupts — depends on more than the cipher
> algorithm. It also depends on the gate-level representation chosen
> by the synthesis flow. This dependence has not been systematically
> measured. We close that gap for 15 standard cryptographic primitives
> synthesized through three majority-based flows on the same FPGA
> target.

### Sample results opening

> We measured per-vector fault detection probability (AvgDP) under
> single gate-output BIT_FLIP injection for each of the 15 circuits
> in three synthesis flows. The MIG flow reduced AvgDP relative to
> the AOIG baseline on 13 of the 15 circuits, with mean reduction
> 13.0 % (95 % CI [−18.3, −7.7], Wilcoxon p = 0.0012). The reduction
> reaches 23.7 % on PRESENT S-box; the two exceptions are Keccak-χ
> 5-bit and 64-row, which show a +8.0 % increase, explained in §4.3.

### Sample threat-model paragraph

> We adopt a single-fault threat model. The adversary injects exactly
> one BIT_FLIP at one gate-output wire of the combinational netlist
> per evaluation and observes the resulting primary outputs. We do
> not model multi-bit faults, transistor-level effects, glitch
> injection, delay faults, or end-to-end key-recovery attacks; these
> are out of scope.

These samples illustrate the register; the actual paper text in §1–§6
will be written from scratch in the same voice but with section-
specific content.
