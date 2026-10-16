# Bit-identical transformer inference from a written spec: three implementations, two ISAs, one digest

**Justin B. Thompson**
Aefinity AI Inc., Orange, Texas

2026-08-28

# Bit-identical transformer inference from a written spec: three implementations, two ISAs, one digest

**Justin B. Thompson**
Aefinity AI Inc., Orange, Texas

2026-08-28

## Abstract

Floating-point transformer inference is treated as unavoidably nondeterministic across hardware:
parallel reduction order, FMA contraction, and platform math libraries all differ between x86_64
and aarch64, and between compilers, so "the same model on the same input" usually means "output
that agrees to within a tolerance," not bit-for-bit. We show this is not a property of IEEE-754
binary32 arithmetic, but a property of leaving its degrees of freedom unpinned. CIS-2 is a
normative specification — reduction order, FMA contraction, denormal handling, and transcendental
routing all pinned by fiat — for the fp32 decode path of a standard (non-ternary, non-quantized)
transformer. Three implementations, written independently from the spec text alone by isolated AI
coding agents (Claude, via Claude Code, operated by one human author, on a single day) in two
languages (Rust, C11), reproduce a single SHA-256 witness digest folded over the complete fp32
logit vector at every decode step — not just the argmax token — bit-for-bit, on a pinned test
vector (SmolLM2-135M, a 16-token greedy decode), across x86_64 and aarch64 (both clean-rooms) and
across gcc and clang (the C clean-room). The reference implementation alone additionally holds
across a 20-cell compiler/optimization-level matrix, a second model family (Qwen2.5-0.5B/1.5B),
and decode horizons up to 512 tokens — legs the clean-rooms have not yet reproduced. The clean-room process itself is part of the evidence: a first independent attempt from a
design memo alone failed to converge, exposing spec gaps (five, per the clean-room's own
accounting; the two load-bearing ones were the transcendental coefficient route and the RoPE
`inv_freq` construction); a second attempt from
the corrected spec converged on the first try; a third, cross-language attempt in C converged on
every value except the top-level witness digest, and diagnosing that residual mismatch exposed a
genuine self-contradiction in the spec's own prose (a witness-chain byte-ordering clause that
did not match the reference it purported to describe) — not a numerics bug. Fixing the spec text
closed the gap on the first retry. We report this history in full, including the mismatches,
because a specification whose own failure modes are legible and fixable is stronger evidence of
sufficiency than a specification that happened to work once. We report no timing or throughput
numbers: this is a verifiability and safety result, not a performance result. We situate CIS-2
against the closest prior work, a GPU-vendor-silicon-table-emulation scheme (arXiv:2606.00279)
that shares the goal of bit-exact inference verification but not the mechanism, the platform
scope, or the multi-implementation structure, and against same-stack GPU determinism work
(Thinking Machines Lab's batch-invariant kernels, LLM-42, MarginGate) that solves run-to-run
determinism within one serving stack rather than cross-platform, cross-language reproduction from
a written contract. We report the result's honest limits without softening them: the scope is
fp32 scalar reference code (not a fast kernel), CPU-only, greedy decoding, models up to 1.5B
parameters, and a RoPE trigonometric range reduction whose accuracy against a high-precision
oracle degrades beyond roughly 512 tokens even though its bit-for-bit determinism does not; a
consumer-device (phone-class) aarch64 leg remains open.
The specification, the reference implementation, both clean-room verifiers, and the CI and
hardware logs are released under Apache-2.0 (repository `Aefinity-AI/cis2-spec`).


# 1. Introduction

Ask two machines to run "the same" floating-point language model on the same prompt and, in
general, you will get two different sets of logits. The weights are identical; the arithmetic is
not. IEEE-754 binary32 addition and multiplication are not associative, so a parallel reduction
summed in a different order produces a different bit pattern; a fused multiply-add contracts two
roundings into one wherever a compiler or a vector unit decides it can; IEEE 754-2019 §9.2 only
*recommends* — and requires nothing of — correctly-rounded `exp`/`sin`/`cos`/`ln`, and the actual
behavior of a platform's `exp`/`sin`/`cos`/`ln` is governed by the C standard, not IEEE-754, so two
C-conforming math libraries are permitted to disagree in the last bit (or more) with no standard
either one is violating; and denormal-number handling defaults differ between x86_64 (MXCSR) and
aarch64 (FPCR) hardware. Each disagreement is small — a few
units in the last place — and each is also decisive: greedy decoding is a chain of argmax
operations over a vocabulary of tens of thousands of entries, and one flipped comparison changes
every token that follows. In production practice, "reproducible" for a floating-point model
means "close," and "close" is not a thing a third party can check without also trusting the
checker's own arithmetic.

This is the companion problem to the one our earlier paper, CIS-1, solved for integer-only
ternary inference (`https://github.com/Aefinity-AI/alice-aegis/blob/main/docs/paper/paper.md`). CIS-1's mechanism was to choose
an arithmetic — bounded fixed-point integers — that is exactly associative, so pinning the type
system was sufficient for cross-ISA bit-identity; no reduction-order discipline was needed because
integer addition does not care about order. That mechanism does not exist for the much larger
class of models that actually ship in fp32 or bf16: ordinary dense transformers with real-valued
weights, softmax attention, and continuous nonlinearities. For that class, bit-identity cannot
fall out of the arithmetic itself. It has to be pinned by fiat, clause by clause, and then checked.

**CIS-2 is that specification.** It fixes every degree of freedom IEEE-754 binary32 leaves open on
the transformer decode path: round-to-nearest-even everywhere; flush-to-zero/denormals-as-zero
pinned and readback-verified on both x86_64 (MXCSR bits) and aarch64 (FPCR.FZ); zero FMA
contraction, enforced by disassembly inspection, not merely by source-level intent; scalar,
strictly left-to-right reduction order for every dot product, sum, and normalization; and
`exp`/`sin`/`cos`/`ln` computed as pinned Cephes-pattern polynomials over hex-specified
coefficient bit patterns, calling no platform math library at all — sidestepping, by
construction rather than by hoping two math libraries happen to agree, the general class of
cross-architecture libm divergence documented in glibc's own regression-testing infrastructure:
glibc ships per-architecture allowed-error tables for its transcendental functions
(`sysdeps/<arch>/libm-test-ulps` in the glibc source tree), which differ by architecture precisely
because the project does not guarantee identical rounding for these functions across its supported
targets. `sqrt` and division need no such pinning: IEEE-754 mandates
correct rounding for both, so any conformant hardware unit already agrees bit-for-bit. A
receipt — a SHA-256 witness chain over the two transcendental coefficient-table digests, the
three model artifact hashes, the prompt tokens, and the complete fp32 logit vector at every decode
step (not just the chosen token) — lets a third party check the claim by recomputing it, without
trusting the party that minted the receipt.

**Provenance disclosure.** All three implementations discussed below — the Rust reference, the
Rust clean-room (`verify2`), and the C11 clean-room (`verify3`) — were written by isolated AI
coding agents (Claude, via Claude Code), operated by one human author (this paper's sole author),
on a single day, 2026-08-28. "Independent" in this paper means what each clean-room agent's file-access
log shows: neither ever opened `src/`, nor the sibling clean-room's directory, before producing its
result (Appendix A). It is the read-logs and the resulting digests, not organizational or temporal
separation between humans, that carry the independence claim. §8 states the specific limitation
this raises that a human-clean-room precedent would not: an AI implementer carries pretraining
knowledge of the exact third-party libraries a spec might describe, which can substitute for
reading the spec text on an ambiguous point.

**The central experiment is not "does our implementation reproduce its own digest," which would
prove nothing about the spec.** It is: given only the spec text — never the reference source —
does an independent implementer, in a different language, converge on the
same digest? We ran this three times. The first attempt worked from a design memo, not a
finished spec, and used no shared code: it reproduced every discrete decision (token ids,
argmax digest) but its full-logit witness digest did not match, because the memo left several things
genuinely unstated (five, per the clean-room's own accounting) — most importantly, which
concrete transcendental coefficients to use, and how to build the rotary-embedding frequency
table. That mismatch was not a failure of the exercise; it located
exactly what the memo needed to say and did not. We wrote those gaps into a normative spec
and ran a second clean-room attempt, in Rust, from the spec text alone: it matched on the first
try, on both ISAs. We then ran a third clean-room attempt, in C — a different language, to test
whether "spec-sufficient" generalizes past one implementer's toolchain habits — and it matched
every value (transcendental tables, argmax token stream, all sixteen generated token ids) except
the single top-level witness digest. Rather than treat that as either a pass or a silent
near-miss, we localized it: a layer-by-layer side channel showed the entire forward pass was
already bit-identical between the C and Rust implementations, which meant the divergence had to
be in how the receipt itself was assembled. It was: the spec's own prose described the witness
chain's byte order differently from what the reference actually computed — a documentation defect,
not a numerics defect, and the C implementation had faithfully transcribed the wrong prose. Fixing
the spec's item order for the receipt's five witness-chain seed inputs (the three artifact
hashes and the two transcendental-table digests, §12.1) closed the gap on the next run, on all
four {x86_64, aarch64} × {gcc, clang} cells. We report every stage of this, including the two failures,
because a specification that surfaces and survives its own errors under adversarial reimplementation
is stronger evidence than one that has only ever been tried once, by the person who wrote it.

**Scale, breadth, and horizon.** Beyond the two clean-room legs, the reference contract holds at
Qwen2.5-1.5B (near-1.5B-parameter scale, a QKV-bias architecture distinct from the pinned
SmolLM2-135M model), and at decode horizons up to 512 tokens, all cross-ISA identical; a
512-token generation from Qwen2.5-1.5B also matches a PyTorch fp32 oracle within tolerance. A
separate numerical-accuracy audit found that the RoPE sine/cosine range reduction — required to
stay in pure fp32 with no FMA — loses accuracy against a correctly-rounded oracle as position
grows, reaching roughly 1e-4 relative error by position 19 and far worse toward the model's
maximum context length; this does not affect the *determinism* claim (both ISAs still agree
bit-for-bit at any position) but does bound the *accuracy* claim to the horizons actually
validated against an oracle (§8).

**What this paper claims, precisely, and what it does not.** It claims: a written, normative fp32
transformer-decode specification such that at least three genuinely independent implementations —
isolated AI coding agents, two languages, converging without access to each other's source —
produce a bit-identical full-logit witness digest on a pinned test vector, across x86_64 and
aarch64, and, for the C implementation, across gcc and clang; and such that the reference
implementation alone additionally holds across a 20-cell compiler/optimization-level matrix, a
second model family, and horizons to 512 tokens, matching a PyTorch fp32 oracle within tolerance
at the horizons checked. It does not claim any speed advantage, any
optimized kernel, GPU support, sampling beyond greedy decoding, or a consumer-device
(phone-class) aarch64 result — that leg is open (§8). We report no timing number anywhere in this
paper: the claim is about determinism and verifiability, not throughput.


# 2. Related work

**Companion paper.** CIS-1 (`https://github.com/Aefinity-AI/alice-aegis/blob/main/docs/paper/paper.md`) specifies a frozen,
all-integer transformer decode semantics for ternary/quantized models, and shows cross-ISA
bit-identity falls out of choosing an associative arithmetic (bounded fixed-point integers). CIS-2
addresses the complementary, larger case — ordinary fp32 models, where the arithmetic itself is
not associative and every degree of freedom must be pinned explicitly rather than inherited from
the type system. Wording, receipt structure, and disclosure conventions in this paper are adapted
directly from CIS-1's; §5 and §8 note the specific places CIS-2 is currently weaker (fewer
independent implementations of a standing verifier tool, no physical non-cloud aarch64 leg).

**GPU run-to-run determinism (same-stack).** Thinking Machines Lab's "Defeating Nondeterminism in
LLM Inference" (blog post + `batch_invariant_ops`) argues that batch-size-dependent reduction
order, not floating-point non-associativity itself, is the dominant cause of nondeterminism in
GPU-served LLM inference, and ships batch-invariant RMSNorm/matmul/attention kernels that give
bit-identical output across repeated runs at fixed batch size, on one hardware/software stack.
LLM-42 (arXiv:2601.17768) achieves deterministic decoding under dynamic batching via a
decode-verify-rollback scheduling protocol on top of SGLang, without rewriting GPU kernels.
MarginGate (arXiv:2605.30218) layers sparse margin-triggered verification on top of
batch-invariant serving to catch drift cheaply. All three solve **run-to-run determinism within
one serving stack** — the same GPU, the same kernels, repeated. None claims or attempts
cross-language or cross-ISA reproduction from a written specification, and none defines a
full-logit-vector, third-party-recomputable receipt; a bit-identical result on one stack says
nothing about what a second, independently-built implementation on different silicon would
compute. CIS-2's problem is orthogonal to this line: it is CPU-only, and its determinism claim is
across implementations and ISAs, not across repeated runs of one binary (though same-process
repeat-run determinism is also a stated CIS-2 conformance clause, spec §12.4).

**Closest prior work: GPU-silicon-emulation bit-exactness.** Cankaya, "Bit-Exact AI Inference
Verification Without Performance Tradeoffs" (arXiv:2606.00279, [venue] 2026 workshop best
paper) is the single closest candidate in *goal*: third-party-checkable bit-exact verification of
an inference result. Its mechanism is the opposite of CIS-2's. Cankaya exhaustively probes
NVIDIA's Special Function Units via inline PTX and caches their exact hardware outputs (e.g., a
4 GB table mapping every 32-bit input for `MUFU.EX2`), then emulates that specific silicon's
transcendental behavior in software to check a GPU inference run against itself without needing
matching GPU hardware at verify time. This is **emulating one vendor's non-standard hardware
math**, tested only on NVIDIA GPUs (A100, L40, L40S, H100; the paper's own stated limitation is
"Only NVIDIA GPUs"), verified against that same vendor's cuBLAS/CUTLASS — a single implementation
and codebase, on one hardware vendor's silicon; no independent reimplementation is reported. There
is no written specification for a second party
to implement from, no cross-language claim, no CPU or cross-ISA claim, and — per a full-text
read of both preprint versions, not the abstract alone — no full-logit-vector digest: the
proposed receipt is a single interior-tensor cryptographic fingerprint, described as a proposal
citing external hashing work, not a built and demonstrated third-party recompute protocol. CIS-2
takes the opposite approach at every one of these axes: it avoids depending on any vendor's
non-standard lookup-table hardware behavior entirely, by using pinned polynomial transcendentals
that any IEEE-754-conformant scalar CPU unit reproduces identically; it is defined as a written
document reimplemented from text by independent parties; it spans two CPU ISAs and two languages;
and its receipt folds the complete per-step logit vector, not one interior tensor, and is
actually built, run, and cross-checked (§4–§5), not proposed.

**Correctly-rounded elementary functions.** CORE-MATH and the RLIBM family (RLIBM-32,
RLIBM-PROG, RLIBM-MultiRound; arXiv:2104.04043, 2111.12852, 2504.07409) generate 0.5-ULP
correctly-rounded implementations of elementary functions, portable because IEEE-754's basic
operations are correctly rounded by standard on x86_64/ARM/RISC-V. This is adjacent tooling CIS-2
deliberately did not adopt: at the time the reference was built, no published Rust crate exposed a
correctly-rounded route for the functions needed, so CIS-2 pins a specific Cephes-pattern
polynomial with hex-specified coefficients instead of claiming correct rounding. This is a
narrower, more mechanical property — "these exact coefficients, transcribed byte-for-byte" rather
than "the unique correctly-rounded answer" — and is exactly what the receipt's coefficient-table
digest is for (§3, §5): it lets a verifier detect a differently-tabled implementation even when
its logits happen to coincide on one test vector.

**Reduction-order reproducibility.** ReproBLAS and Intel's MKL Conditional Numerical
Reproducibility mode give reproducible parallel-reduction sums across thread counts, and, for
CNR, across some Intel CPU generations, at a documented performance cost. This is vendor-scoped
(Intel-to-Intel) and thread-count-scoped, not cross-ISA (Intel-to-ARM) and not a transformer-level
full-logit claim.

**Attestation and supply-chain provenance.** A body of work on ML supply-chain attestation
(Laminator, arXiv:2406.17548; Kettle, arXiv:2605.08363; general scalability/module-repository
risk work, arXiv:2602.19021, 2603.02512) and build reproducibility framing for AI systems
("Reproducibility is the New Copyleft," arXiv:2606.03019) addresses *provenance* — attesting that
a declared input produced a declared output, typically via hardware attestation or signed
metadata, with hardware/toolchain configuration itself often treated as a pinned, trusted input.
CIS-2's receipt is orthogonal and stronger in one specific sense: it is designed to be
**recomputed from scratch** by a skeptical verifier trusting no attestor and no fixed hardware
configuration, at the cost of one full deterministic decode (§5) rather than a signature check.

**Polynomial provenance, numerical-perturbation testing, language-level pinning, and industry
practice.** CIS-2's pinned transcendental route (§3 gate 5, §6.5) is not a novel numerical method:
the range-reduction-plus-Horner-polynomial pattern and the polynomial coefficients themselves are
Moshier's Cephes library (Moshier 1992); CIS-2's contribution is pinning that specific,
pre-existing construction as normative spec text and binding its coefficient table into a
third-party-recomputable receipt, not inventing a new approximation. Route (b) — Cephes-pattern
polynomials over hex-pinned coefficients — was chosen over route (a) — a correctly-rounded
library — for *pinnability*, not because no correctly-rounded route existed in principle: CORE-MATH
(§2, above) is written in C and could in principle be bound from Rust or compiled directly for a
C implementation, but no such binding existed in this project's toolchain at build time, and a
correctly-rounded C dependency would not by itself resolve the receipt's need to bind an exact,
auditable coefficient table the way spec text does. Verificarlo (Denis, de Oliveira Castro, and
Petit 2016) and the reproducible-summation line (Demmel and Nguyen 2013; Ahrens, Demmel, and
Nguyen 2020, extending the ReproBLAS work already discussed above) address an orthogonal question
— *how sensitive* a floating-point computation is to rounding-order perturbation, via Monte Carlo
arithmetic instrumentation or reproducible-summation algorithms — rather than *pinning* every
degree of freedom by fiat and checking the result bit-for-bit; CIS-2 could, in principle, use
Verificarlo-style perturbation testing as an additional adversarial check that its pinned gate list
is complete, an avenue not explored here. Java's `strictfp` (JLS 17, restored to always-on
semantics by JEP 306) is the closest prior *language-level* precedent for pinning floating-point
determinism, but addresses a narrower problem — disabling x87 80-bit extended-precision leakage
into nominally 32/64-bit results — not reduction order, FMA contraction, or transcendental
routing, which CIS-2 additionally pins. The same underlying problem (cross-machine fp32
nondeterminism breaking bit-exact replay) is long-standing, informally documented industry practice
in networked/lockstep game simulation (Fiedler 2010), typically solved per-project via ad hoc
integer or fixed-point conversion rather than a written, third-party-verifiable fp32 specification.
Finally, `-ffp-contract=off` and the C standard's `STDC FP_CONTRACT` pragma are the
compiler/language-level *requests* to disable FMA contraction; CIS-2's no-FMA gate (§3 gate 3, §6.3)
does not rely on either being honored — it verifies the absence of FMA instructions by
disassembling the actual release binary, because a pragma or flag is a request a toolchain is free
to ignore, not a guarantee.

**Novelty summary.** No candidate found in this search combines (i) a written normative fp32
numeric spec, (ii) independent multi-language reimplementation, (iii) cross-ISA (x86_64/aarch64)
verification, and (iv) a full-logit bit-identical, third-party-recomputable receipt. The closest
work is GPU-vendor-silicon-emulation-based, single-implementation, and receipt-as-proposal
(arXiv:2606.00279, distinguished in detail above); the remaining candidates address adjacent but
distinct problems — same-stack run-to-run determinism, correctly-rounded math-library
construction, thread-count reduction reproducibility, or provenance attestation.


# 3. The CIS-2 normative contract

CIS-2 (`docs/CIS2_SPEC_v0.2.md`, current version **v0.2.1**, DRAFT/HELD private, Aefinity-AI/cis2-fp) rests on the opposite
axiom from CIS-1's (`https://github.com/Aefinity-AI/alice-aegis/blob/main/docs/paper/03_semantics.md` §3): IEEE-754 binary32
addition and multiplication are *not* associative, so bit-identity across ISAs cannot fall out of
the arithmetic itself the way it does for exact integers. Every degree of freedom IEEE 754 leaves
unspecified — reduction order, FMA contraction, transcendental routing, denormal handling — has to
be pinned by fiat and enforced mechanically.

**Version note.** The spec file this paper cites throughout is now at **v0.2.1**: a doc-only revision that fully pins the byte-level BPE tokenizer (§3.1, closing H3 BLOCKER-2, gate 8 below; H4 result). Separately, and prior to that version bump, §12.1's own prose was corrected in place to fix the witness-chain item-order self-contradiction the C clean-room's mismatch exposed (gate 7 below; see §4/§6.7 for the full story) — this correction is folded into the v0.2 text itself rather than tracked as its own version number, per the spec's own changelog discipline (§16). Neither change moves any digest in §13.1 — `CIS2_REF`, `table_digest`, `inv_freq_table_digest`, and `argmax_digest` are byte-identical throughout — which is why this paper cites the receipt mechanics as "v0.2" (unchanged since the tables/order were fixed) while citing the spec file itself as v0.2.1 (current, tokenizer-complete).

> **Definition (bit-identical fp32 decode, CIS-2 §13.2).** Fix a model checkpoint (identified by
> the three artifact SHA-256 hashes of §2.1), a prompt, and a decode length. Two conforming CIS-2
> implementations are *bit-identical* on this input iff, for every decode step, each computes the
> same **full fp32 logit vector** — every one of the 49,152 vocabulary entries' raw bit patterns,
> not just the argmax token id — and selects the same argmax token. The witness chain
> (`CIS2_REF`, spec §12.1) is a deterministic SHA-256 fold of exactly that state: the two
> transcendental-table digests, the three artifact hashes, the prompt token ids, and then, per
> step, the full logit vector's raw bytes plus the chosen token id — so equal `CIS2_REF` digests is
> equivalent to bit-identical decode. Covered: the full logit vector at every step, not an
> argmax-only summary — spec §12.1 item 7a is explicit that this is "a much harder bar than
> argmax-only" (`Appendix B: E15c-verify` item 1). Not
> covered: KV-cache byte layout (spec §3.5 states caching is a conformance-neutral memoization
> choice, not part of the pinned math); sampling (greedy/argmax only, spec §3.4); any `rope_theta`
> or sequence length outside the validated set (spec §14.1, §14.4).

## The gate list

Six clauses of spec §1/§5/§6 are load-bearing; each is stated below with its spec section and its
enforcement mechanism in this repo.

| # | Gate | Spec § | Enforcement (file:line / CI) |
|---|---|---|---|
| 1 | **FTZ/DAZ pinned on before any decode-path arithmetic** — x86-64 MXCSR bits 15 (FTZ) and 6 (DAZ) set via direct register read-modify-write (not `_mm_setcsr` wrappers); aarch64 FPCR bit 24 (FZ) via `mrs`/`msr fpcr`. Readback-asserted, not merely "we called the setter." | CIS2_SPEC_v0.2.md §1.3 | `denormal::pin_ftz_daz()`, called `src/main.rs:305` before any weight/decode arithmetic; adversarial unit test `ftz_daz_pinned_and_denormal_input_flushed` (`src/denormal.rs`), `black_box`-guarded so LLVM cannot fold the subnormal op away; passing on both ISAs in CI (`Appendix B: E15c-verify` item 2). |
| 2 | **Round-to-nearest-even (RNE) everywhere, no other rounding mode set.** | CIS2_SPEC_v0.2.md §1.2 | IEEE-754 default; not independently toggled anywhere in `src/`. |
| 3 | **No FMA contraction anywhere** — every `a*b + c` is two separate, separately-rounded operations; `f32::mul_add` is never called. | CIS2_SPEC_v0.2.md §1.4 | `src/math.rs:40-58` (`dot_seq`/`sum_seq`, `let p = a[i]*b[i]; acc = acc + p;` as two statements). Mechanical grep gate `tests/no_mul_add.rs` + disassembly gate `scripts/no_fma_gate.sh` (`objdump` for `vfmadd\|vfnmadd\|vfmsub\|vfnmsub\|fmadd\|fmsub`). Adversarially rebuilt with `RUSTFLAGS="-C target-cpu=native"` on FMA-capable hardware: 0 FMA instructions, digest unchanged (Appendix B: E15c-verify item 3). Re-confirmed at v0.2 across a 20-cell `{opt-level 0,1,2,3,s} × {generic,native} × {x86_64,aarch64}` matrix, 0 FMA in every cell (`docs/E15d_v0.2_DIGESTS.md`, run 33195649908). |
| 4 | **Scalar left-to-right reductions** — every dot product and sum (matvec rows, RMSNorm sum-of-squares, softmax denominator, V-mix) folds strictly in index order `0..n-1`; no pairwise tree, no chunking, no reassociation. | CIS2_SPEC_v0.2.md §5.1, §5.3 | `dot_seq` (`src/math.rs:40`), `sum_seq` (`src/math.rs:52`) — plain `for` loops, scalar accumulator. Regression test `dot_seq_is_order_sensitive_by_design` (`src/math.rs:437`) asserts the pinned order specifically: dotting `[1e8, 1.0, -1e8]` against `[1.0, 1.0, 1.0]` in this exact order gives `0.0_f32` (the `1.0` term is lost to rounding against the `1e8` partial sum); any other order gives a different, nonzero answer. |
| 5 | **Pinned polynomial transcendentals with hex coefficients, and no platform libm call** — `exp`/`sin`/`cos`/`ln` are libm-free Cephes-pattern range-reduction + fixed-degree Horner polynomials over hex-pinned `f32` coefficient bit patterns; `sqrt`/`/` use the IEEE-754-mandatory correctly-rounded hardware ops directly (no table needed, since any conformant IEEE-754 implementation already agrees bit-for-bit on these); `rsqrt` is computed as the composition of two such correctly-rounded ops (`1.0/x.sqrt()`), which is deterministic and cross-ISA-identical but is not itself guaranteed correctly rounded (composing two correctly-rounded operations does not, in general, yield a correctly-rounded composite result). | CIS2_SPEC_v0.2.md §6.1–§6.5 | `exp_pinned` (`src/math.rs:100`), `ldexp_exact` (`src/math.rs:139`), `sin_pinned`/`cos_pinned` (`src/math.rs:206`/`218`), `ln_pinned` (`src/math.rs:272`) with `frexp_exact` (`src/math.rs:259`) and coefficients `LOG_SQRTHF`/`LOG_Q1`/`LOG_Q2`/`LOG_P[0..9]` (`src/math.rs:240-254`); `rsqrt_cr` (`src/math.rs:66`). Coefficient-table digest `table_digest()` (`src/math.rs:342`) prints `465d358ccd63721256dbd2abbc77ad5de755adf3230635f95b12b1727dfa1ea3` at v0.2 (spec §6.6). Zero calls to platform libm `exp`/`sin`/`cos`/`ln` confirmed (`Appendix B: E15c-verify` item 2: "sidesteps the general class of cross-architecture libm divergence — documented in glibc's own per-architecture `libm-test-ulps` tables — entirely, by construction"). |
| 6 | **Pinned general `ln(theta)` for RoPE `inv_freq`, not a bare per-model literal** — `inv_freq[i] = exp_pinned(-(2i/head_dim)·ln_pinned(rope_theta))`, `ln_pinned` valid for any `rope_theta` read from `config.json`, not hardcoded to one value. | CIS2_SPEC_v0.2.md §7.1 (new in v0.2, closes v0.1 §14.1) | `src/main.rs:345` (`let ln_theta = math::ln_pinned(rope_theta as f32);`), `rope_theta` read at `src/main.rs:331`, `inv_freq` loop `src/main.rs:346-354`, digest `inv_freq_table_digest` computed `src/main.rs:358-365`. Validated on SmolLM2-135M (`rope_theta=100000`, digest bit-identical to the v0.1 literal-based construction — `docs/E15h_REFACTOR_v0.2_RESULT.md`) and Qwen2.5-0.5B (`rope_theta=1000000`, `docs/E15d_bc_RESULT.md`). |
| 7 | **Raw-byte digest binding, in a spec-corrected order** — the witness chain (`CIS2_REF`) folds the three artifact hashes then the two transcendental-table digests, all as their **raw 32 bytes**, not their 64-character hex-ASCII rendering; the coefficient-table digest and `inv_freq` table digest are inputs to `CIS2_REF` itself, not merely printed alongside it. | CIS2_SPEC_v0.2.md §12.1 (new in v0.2, closes v0.1 §12.1/§14.2/§14.3; item order corrected post-E15k, see §4) | `sha256_file` returns `[u8; 32]` (`src/main.rs:245`); witness seeding order `weights_sha256`, `tokenizer_sha256`, `config_sha256`, `table_digest`, `inv_freq_table_digest` then prompt tokens (`src/main.rs`, spec §12.1/Appendix A, corrected `docs/E15k_DIVERGENCE_LOCALIZATION.md`); display-only hex helper via local `hex::encode`. |
| 8 | **Byte-level BPE tokenization pinned normatively, not delegated to "call the library."** The byte↔unicode remap, the GPT-2/ByteLevel pretokenizer regex plus this checkpoint's `Digits(individual_digits=true)` pre-split, and the rank-ordered/leftmost-tie-break BPE merge loop are specified as an algorithm, transcribed from the `tokenizers` crate's own source, not merely cited by version number. | CIS2_SPEC_v0.2.md §3.1 (v0.2.1, closes H3 BLOCKER-2) | Spec §3.1.1–§3.1.6; `tokenizers` crate v0.23.1 cited as a normative fallback for residual edge cases only (same pattern as citing SHA-256 as an external standard); verified against the checkpoint's actual `tokenizer.json` (sha256-matched) and the pinned prompt's token ids `[6403, 1980, 253, 655]` (`Appendix B: H4-result`). |
| 9 | **Compiler toolchain pinned**, not left to whatever `rustc` a given CI runner happens to have installed. | `rust-toolchain.toml` (channel `1.98.0`, `x86_64-unknown-linux-gnu` + `aarch64-unknown-linux-gnu` targets, `profile = "minimal"`) | Present at repo root; closes the "no hard compiler-version pin" caveat carried in earlier drafts of this paper and in `Appendix B: E15c-verify`'s "Overall verdict." |

Everything else — memory layout, tiling, thread/SIMD strategy, instruction selection — is free
(spec §1.4/§15 item 6 is silent on it) as long as the pinned reduction order and transcendental bit
patterns match exactly; no optimized (SIMD) kernel has yet been built against this contract (§8,
limitations).

**A hostile question this gate list must answer.** "Of course scalar fp32 is deterministic once
you ban FMA and pin a reduction order — that's not a discovery, it's arithmetic." This is true and
is not the contribution. The contribution is threefold and only shows up in §4–§5: (1) enumerating
the *complete* set of gates needed — nine of them, found empirically because early attempts to
skip one (transcendental routing, RoPE `inv_freq` generality, witness byte order) each produced a
real, localized mismatch when an independent implementer worked from an incomplete description;
(2) writing that enumeration down as a document a second and third party, in two different
languages, can implement from without ever reading the reference source, and having them converge;
and (3) a receipt format that lets a fourth party who trusts none of the first three verify the
claim by recomputing it, at the cost of one full decode. None of the nine gates individually is
surprising; the empirical claim is that this specific list is *sufficient*, demonstrated by
independent convergence rather than assumed.

## Mechanism

CIS-1's mechanism (`03_semantics.md`) is that integer addition is associative, so pinning the
*type system* (bounded accumulators) is sufficient; CIS-2 cannot use that shortcut, because fp32
addition is not associative. CIS-2's mechanism is instead the conjunction of the nine gates above:
gate 4 removes reduction-order freedom, gate 3 removes the FMA-vs-separate-rounding degree of
freedom, gates 5–6 remove transcendental-routing freedom (by avoiding platform libm entirely
rather than hoping two libms agree), gate 1 removes the x86-vs-aarch64 hardware default divergence
in denormal handling, gate 8 removes tokenization ambiguity (a source of divergence that is not
IEEE-754-related at all, but is just as capable of changing every downstream token), gate 9 removes
compiler-version drift as a residual, unstructured coincidence, and gate 7 makes the receipt bind
the exact transcendental coefficients used, not just the resulting logits — so a receipt holder can
detect a differently-tabled but
coincidentally-similar implementation, not just a differently-computed one. Two of the six IEEE-754
basic operations (`sqrt`, `/`) need no pinning at all, because they are mandatory-correctly-rounded
by the standard itself (spec §1.6) — the same is not true of `exp`/`sin`/`cos`/`ln`, which the
standard leaves at merely faithfully-rounded, and that gap is precisely why gates 5–6 exist.

---

**Source map**
- Definition and full-logit-vector digest scope: `docs/CIS2_SPEC_v0.2.md` §12.1, §13.2.
- FTZ/DAZ, RNE, no-FMA: spec §1.2–§1.5.
- Reduction order: spec §5.1, §5.3.
- Transcendentals and coefficient digest: spec §6.1–§6.6.
- RoPE `ln_pinned` generalization: spec §7.1, §16 (v0.2 changelog).
- Raw-byte witness binding: spec §12.1, §14.2, §14.3 (closed gaps).


# 4. Evidence

No timing or throughput number appears anywhere below; every figure is an identity or accuracy
claim (Rule A). Every digest is quoted from a checked-in report file or a named CI run.

**TODO — unsourced-number check.** None. Every digest, token id, and byte count below was found
verbatim in at least one of the cited files. See the self-check at the end of this document.

## Evidence table, E15b → E15i

| Row | What | Result | Source |
|---|---|---|---|
| E15b m1 | Rust fp32 reference, in-process + cross-process repeat, same host | `run1_witness_digest == run2_witness_digest = 830d972dbfb0b5598015f33571d08623d2b05d8e239b8d0288562d9ac9786907`; `argmax_digest = 0b9c8f3ac90d0b9cd5f1719ac327dca1fc639fd87468305fccebbe3d56f67aff`; same-host determinism only, pre-RoPE-fix, no cross-ISA claim | `docs/E15b_REFERENCE_RESULT.md` |
| E15b m1.5 | Correctness vs. PyTorch/`transformers==5.16.1` fp32 oracle (`torch==2.13.0+cpu`) | 16/16 greedy token match `[28, 665, 436, 253, 1838, 8180, 3365, 14176, 30, 2306, 4161, 281, 253, 2066, 2291, 351]`; step-0 full-vocab (n=49152) `max_abs_diff = 8.96453857421875e-05` (vocab idx 40082, rust `5.486028671264648` vs oracle `5.486118316650391`), relative `≈3.98e-06` against a pre-registered `<1e-2` bar | `docs/E15b_m1p5_CORRECTNESS.md`, `scripts/oracle_compare.py` |
| E15b m1.5 (RoPE fix) | Post-fix reference digest: `inv_freq` switched from host `f64::powf` to pinned `exp_pinned` | `CIS2_REF digest=ba88708bf4159a4057d4eef727820ebc5ce1744ae334bfe0cc0776e03509dd0f`; `inv_freq table_digest=da9f6dcfde0425588815509e874515cdcd3d6b8818b6d0136590052e7bbf6f12`; `argmax_digest` unchanged from pre-fix run (no token flip) | `docs/E15b_m1p5_CORRECTNESS.md` |
| E15c | Cross-ISA CI matrix (x86_64 `ubuntu-latest` + aarch64 `ubuntu-24.04-arm`, same commit, non-cached, full pipeline each leg) | Both legs identical: `CIS2_REF digest=ba88708bf4...09dd0f`, `table_digest=0bf9257bc56c4588cb4003e1a105b60169e152222ec734811d0a58e66e1cdeca`, `inv_freq table_digest=da9f6dcf...52e7bb`; run `33171752921`, jobs `98850338683` (x86_64) / `98850338874` (aarch64), commit `f83e8dd86a2d7a78c4618f690d1395e0cc5364eb`, both legs `rustc 1.98.0 (88d9e12ae 2026-08-18)` | `Appendix B: E15c-verify` §4, `.github/workflows/e15c-cross-isa.yml` |
| E15c adversarial | Rebuild variants: `RUSTFLAGS="-C opt-level=0"` and `RUSTFLAGS="-C target-cpu=native"` (FMA-capable local host) | All three build variants (default, opt-level=0, target-cpu=native) give identical `CIS2_REF digest=ba88708b...09dd0f` and identical `inv_freq table_digest=da9f6dcf...52e7bb`; 0 FMA instructions (`objdump -d \| grep -icE "vfmadd\|vfnmadd\|vfmsub\|vfnmsub"`) in every variant | Appendix B: E15c-verify §3 |
| E15e | Clean-room attempt #1, from the design memo only (no spec doc existed yet) | Weight/config/tokenizer sha256 and tokenization `[6403, 1980, 253, 655]` MATCH; 16/16 greedy token ids MATCH; `argmax_digest = 0b9c8f3ac90d0b9cd5f1719ac327dca1fc639fd87468305fccebbe3d56f67aff` MATCH; `CIS2_REF` (`241a73387b22b4f81cd96094efeb6603c3f88a0d10c9fca9a7a1feff5fd7d7bf`) and `inv_freq_table_digest` (`6d20bb9d2a7ec35a70fcc399fed93e17664fa74f95942d9ec77f17ae7a882668`) MISMATCH against target; own cross-ISA self-consistency confirmed (CI run `33190989443`) | `docs/E15e_CLEANROOM_RESULT.md` |
| E15f | Normative spec v0.1 written to close E15e's gaps (digest byte encoding, transcendental coefficients as spec text, RoPE `inv_freq` construction, RMSNorm multiply order) | Spec written; two residual reference weaknesses found and queued for E15h (`LN_THETA` literal overstated as config-general; table digests not folded into the receipt; artifact hashes hashed as hex-ASCII not raw bytes) | `docs/CIS2_SPEC_v0.1.md`, `Appendix B: CIS2-RESULT` |
| E15g | Clean-room attempt #2, from `CIS2_SPEC_v0.1.md` text only, `src/`/`verify/` never opened | All 4 digests MATCH on both ISAs, first attempt, 0 of 3 allotted fix attempts used: `CIS2_REF=ba88708bf4...09dd0f`, `argmax_digest=0b9c8f3a...`, `table_digest=0bf9257bc5...`, `inv_freq_table_digest=da9f6dcf...`; 16/16 generated token ids identical; 0 FMA instructions on both legs | `docs/E15g_CLEANROOM_V2_RESULT.md`, CI run `33192338105` |
| E15g-audit | Independence audit of the E15g clean-room crate | INDEPENDENT verdict: weighted verbatim-line overlap 68/378 = 18.0% (`fpenv.rs` 11/32, `main.rs` 33/252, `math.rs` 24/94), attributable to spec-pinned constants/algorithm steps and generic Rust idioms; single fresh-authorship commit `7eb7ac5` (no rename/copy detected); fresh re-dispatch (run `33192908940`) reproduces `CIS2_REF=ba88708bf4...09dd0f` and `inv_freq table_digest=da9f6dcf...` on both ISAs; one soft spot flagged (identifiers `pin_ftz_daz`/`widen_bf16` match src exactly and are not literal spec-body tokens, plausibly convergent naming, not proven) | `Appendix B: E15g-audit` |
| E15h | Reference refactor to v0.2: table digests folded into `CIS2_REF`, raw-byte artifact-hash binding, theta-general `ln_pinned` RoPE | New preregistered digest `CIS2_REF digest v0.2 = a0c563ef804f50413b7fb6619ae4afe9b51b1ffa7655e944221393e85d6261da`; `table_digest=465d358ccd63721256dbd2abbc77ad5de755adf3230635f95b12b1727dfa1ea3` (changed set of hashed coefficients); `inv_freq_table_digest=da9f6dcfde...` (unchanged from v0.1); `argmax_digest=0b9c8f3ac9...` (unchanged); two sequential runs bit-identical (`runs_identical=true`) | `docs/E15h_REFACTOR_v0.2_RESULT.md`, commit `f227b43` |
| E15i | Spec v0.2 document written (full v0.1 body + E15h's three changes, changelog, updated §13 test vectors) and E15d(a)/(b)/(c) rerun against the v0.2 reference | E15d(a): 20/20 compiler-invariance cells match `CIS2_REF=a0c563ef...` and `inv_freq_table_digest=da9f6dcfde...`, 0 FMA in every cell (run `33195649908`, after fixing an unrelated CI grep bug found in run `33195027040`); E15d(b): 5 prompts × gen_toks=128, x86_64==aarch64 on all 5 (run `33195030116`, digests `e8d4f83f...`/`e805baec...`/`cf1ef40e...`/`ee124779...`/`135f50b5...`); E15d(c): Qwen2.5-0.5B (`rope_theta=1000000`) cross-ISA at gen_toks=16 (`2c9f6235...`) and 128 (`dccd55e6...`), plus 16/16 oracle match (run `33195032954`) | `Appendix B: E15i-result`, `docs/E15d_v0.2_DIGESTS.md` |
| E15h-verify2 | Clean-room verifier crate (`verify2`, from E15g) updated and rerun from spec v0.2 text only | MATCH: `CIS2_REF=a0c563ef...` on both ISAs, run `33194049057` | `Appendix B: CIS2-RESULT` (12:35 CT update) |
| H3 | Adversarial spec audit for remaining under-specified operations | Found 2 BLOCKERs: (1) §16 changelog/Appendix A witness-order self-contradiction (doc-only, no digest change); (2) tokenizer BPE/pretokenizer not pinned normatively | `Appendix B: SLAM-DUNK-CRITERIA` row 7, commit `bbea1df` |
| H4 | Spec §3.1 rewritten (v0.2.1) to pin byte-level BPE tokenization as an algorithm, closing H3 BLOCKER-2 | No `generated_token_ids`/digest change; tokenizer sha256 and pinned prompt token ids `[6403, 1980, 253, 655]` reproduced from the spec's own algorithm text, cross-checked against a Python `tokenizers` binding | `Appendix B: H4-result`, `CIS2_SPEC_v0.2.md` §3.1 |
| E15j | Clean-room attempt #3, in **C11** (`verify3/`), from `CIS2_SPEC_v0.2.md` text only — a different language and a fresh implementer, `src/`/`verify/`/`verify2/` never opened | `table_digest`, `inv_freq_table_digest`, `argmax_digest`, and all 16 `generated_token_ids` MATCH bit-for-bit on all 4 cells ({x86_64,aarch64}×{gcc,clang}); top-level `CIS2_REF` MISMATCH (`a532d4a4a88a15221ea6b6e211daa36aecf6fb64fefa5f85f065252008927d65` vs. expected `a0c563ef...`), same on all 4 cells; 0 FMA instructions on all 4 cells | `docs/E15j_CLEANROOM_C_RESULT.md`, run `33197817365` |
| E15k pass 1 | Layer-by-layer side-channel digest comparison (embedding, all 30 blocks' post-attention/post-MLP states, final norm, full pre-argmax logit vector) between the C clean-room and the Rust reference, decode steps 0–1 | All ~124 dumped tensors bit-identical between the two independent implementations — rules out RMSNorm, RoPE, attention, MLP, final norm, and the LM-head matvec as the divergence source | `docs/E15k_DIVERGENCE_LOCALIZATION.md` |
| E15k pass 2 | Root-cause diagnosis of the residual `CIS2_REF` mismatch, given that the entire forward pass was already proven bit-identical | The five 32-byte witness-chain seed inputs (3 artifact hashes + 2 table digests) were themselves already bit-identical between C and Rust; the divergence was that spec §12.1's prose specified a different *item order* than the reference binary actually used. The C implementation was a **faithful, correct transcription of the spec as written** — the spec text itself was wrong, confirmed because the unmodified reference binary (already cross-compiler/cross-ISA validated at v0.2, `docs/E15d_v0.2_DIGESTS.md`) is the source of the pinned `CIS2_REF`, not the prose | `docs/E15k_DIVERGENCE_LOCALIZATION.md` |
| E15k fix + rerun | Spec §12.1 item order corrected to match the reference (weights, tokenizer, config, table, inv_freq); `verify3/model.c` corrected to match | **Full 4/4 cross-language MATCH**: all four cells print `CIS2_VERIFY3 digest=a0c563ef804f50413b7fb6619ae4afe9b51b1ffa7655e944221393e85d6261da` and `conformance=PASS` | `docs/E15k_DIVERGENCE_LOCALIZATION.md`, run `33200155942` |
| H2 | Transcendental accuracy characterization: pinned §6 functions ported line-for-line to Python (`numpy.float32`), oracle = mpmath 60-digit + correctly-rounded-fp32 neighbor search, measured on the exact grid the two pinned test vectors use | `rsqrt_cr`: 0 ULP measured on the tested grid (composition of two individually correctly-rounded ops; not guaranteed correctly rounded in general, see §6.5). `exp_pinned`: ≤1 ULP, 1.19e-7 rel, over the RoPE grid and x∈[-40,40]. `ln_pinned`: 0 ULP at both pinned `rope_theta` values (1e5, 1e6). `sin_pinned`/`cos_pinned`: up to **1104 ULP / 1.00e-4 relative error** at position ≤19 on the SmolLM2 grid — root cause is catastrophic cancellation in the two-constant range reduction (`reduce_2pi`), not polynomial inadequacy; determinism unaffected (both ISAs still bit-identical), accuracy-only finding | `Appendix B: H2-result`, `docs/H2_TRANSCENDENTAL_RIGOR.md`, `CIS2_SPEC_v0.2.md` §6.7 |
| H1 | Scale (Qwen2.5-1.5B, ~1.5B params), breadth (3rd checkpoint, QKV-bias architecture), and horizon (512 tokens) cross-ISA CI, plus 512-token oracle-correctness check | All 9 CI jobs SUCCESS. Literal digests pulled directly from run `33214545380`'s job logs (not reproduced in `Appendix B: H1-result` itself, which reports only pass/fail verdicts): Qwen2.5-1.5B `CIS2_REF` identical on both ISAs at gen_toks=16 (`5670920223a840d3...347776`), gen_toks=128 (`7b6f177ca8d2bec2...138068`), and gen_toks=512 (`f2f0c8a05da25eb7...9a3c1d`), with matching `argmax_digest` at each horizon (`c2c9f689...`, `940db72d...`, `270018a1...` respectively) and shared `table_digest=465d358ccd...` (same coefficient table as SmolLM2) and `inv_freq_table_digest=02908dae2c...` (Qwen's own RoPE table, distinct from SmolLM2's); SmolLM2-135M `CIS2_REF` identical on both ISAs at gen_toks=512 (`27d319bb77be096e...c7653a4`, `argmax_digest=bd544507...be7bc4f6`); Qwen2.5-1.5B 512-token oracle check: `max_abs_diff=6.473064422607422e-05` at vocab idx 19896 (rust `1.8892077207565308` vs oracle `1.8891429901123047`), relative diff `2.445408220505891e-06 < 0.01`, and all 512 greedy-decoded tokens match the oracle | `Appendix B: H1-result`, CI run `33214545380` (job logs fetched directly via `gh api repos/Aefinity-AI/cis2-fp/actions/jobs/{id}/logs`, not expired) |

## The clean-room story, told plainly

The evidence table above is not a monotonic sequence of successes — it is a memo-only attempt that
failed, followed by a spec that closed the failure's exact gaps, followed by a spec-only attempt
that succeeded on the first try. That arc is direct evidence that the CIS-2 *document*, not just
the reference binary, is what carries the contract:

1. **E15e (memo-only, MISMATCH).** An implementer working from the E14a design memo alone — never
   opening `src/` — reproduced the artifact hashes, the tokenization, and all 16 greedy token ids
   exactly, but its `CIS2_REF` and `inv_freq_table_digest` did not match. The mismatch was
   localized (not guessed at): weight identity, tokenization, and the discrete argmax decisions all
   agreed, so the divergence had to be in the fp32 logit bit patterns themselves. `docs/
   E15e_CLEANROOM_RESULT.md` (the source-of-truth report for this leg) enumerates five spec gaps
   the memo left unstated; the two load-bearing ones were the transcendental route (the memo
   recommended a correctly-rounded route but named no concrete coefficients, so two implementations
   choosing route (b) "by fiat" had nothing to converge on) and the RoPE `inv_freq` construction,
   which the memo never specified at all. The other three (digest byte-encoding ambiguity, an
   unstated RMSNorm multiply-order choice believed not to be the actual cause, and an unrelated CI
   branch-history process gap) are lower-severity or non-numeric and are listed in full in that
   report ("Verdict: MISMATCH, but an informative one").
2. **A normative spec was written (v0.1) to close exactly those gaps** — hex-pinned transcendental
   coefficients in the spec body itself, the RoPE `inv_freq` formula stated explicitly, and the
   receipt's exact byte encoding spelled out (`docs/CIS2_SPEC_v0.1.md`).
3. **E15g (spec-only, MATCH first try).** A second clean-room implementer, given `CIS2_SPEC_v0.1.md`
   text only and never opening `src/`, `tests/`, or the E15e clean-room crate, reproduced all four
   digests bit-for-bit on both ISAs, zero of the three allotted fix attempts used
   (`docs/E15g_CLEANROOM_V2_RESULT.md`).
4. **An independence audit (E15g-audit)** then checked whether "spec-only" was actually true rather
   than assumed: git history shows single fresh-commit authorship with no rename/copy signal,
   verbatim-line overlap with the reference (18.0% weighted) is attributable to spec-mandated
   constants and generic Rust idioms rather than copied code, and a fresh CI re-dispatch reproduced
   the same digests again — with one honestly-flagged soft spot (two identifier names match the
   reference exactly and are not literal spec-body tokens; plausibly convergent naming from the
   spec's own vocabulary, not disproven)
   (`Appendix B: E15g-audit`).

## The C clean-room: a cross-language mismatch that traced to the spec's own prose, not the numerics

The Rust-to-Rust clean-room story above (E15e → E15g) proves the spec is sufficient for a second
Rust implementer. It does not, by itself, prove the spec is sufficient across languages: a
second Rust implementer inherits Rust's own defaults (e.g., how `f32` arithmetic and integer
overflow behave, what the standard library's `to_le_bytes` does) that a spec author might have
left implicit without realizing it. A third clean-room attempt, in C11 (`verify3/`, E15j), tested
exactly that, with a fresh implementer who never opened `src/`, `verify/`, or `verify2/`.

1. **E15j (C, from spec v0.2 text only): three-of-four match, one mismatch, reported honestly as
   partial, not massaged into a pass.** The C implementation reproduced `table_digest`,
   `inv_freq_table_digest`, `argmax_digest`, and all 16 `generated_token_ids` bit-for-bit, on all
   four {x86_64, aarch64} × {gcc, clang} cells, with zero FMA instructions in every cell's
   disassembly. Its top-level `CIS2_REF` witness digest did not match. Because the argmax digest
   and the full 20-token sequence (4 prompt + 16 generated) matched exactly, the forward pass was
   very likely computing something extremely close to correct — but `CIS2_REF` additionally folds
   in the complete 49,152-entry fp32 logit vector at every step, which is a strictly harder bar
   than argmax agreement, and something in that finer-grained comparison diverged
   (`docs/E15j_CLEANROOM_C_RESULT.md`).
2. **E15k pass 1: localization, not guessing.** An env-gated per-layer digest side-channel
   (`CIS2_DUMP_LAYERS`), added to both the C and Rust implementations as informative
   instrumentation (not part of conformance), dumped a SHA-256 digest of the token embedding,
   every one of the 30 transformer blocks' post-attention and post-MLP hidden states, the final
   norm output, and the full pre-argmax logit vector, at decode steps 0 and 1. All roughly 124
   dumped tensors matched bit-for-bit between the two implementations. This ruled out RMSNorm,
   RoPE, attention, the MLP, the final norm, and the LM-head projection as the source — the
   entire forward pass, at the tensor level, was already provably identical.
3. **E15k pass 2: the defect was in the spec's prose, not either implementation's numerics.**
   With the forward pass cleared, the only remaining candidate was how the receipt itself is
   assembled. Direct inspection found it immediately: the Rust reference feeds the witness chain
   in the order weights-hash, tokenizer-hash, config-hash, then the two table digests; spec
   §12.1's written prose described the reverse group order (table digests first, then the three
   artifact hashes) — and the C implementation had transcribed that prose faithfully. Every one of
   the five 32-byte inputs was already proven bit-identical (item 2, plus each digest already
   individually compared in E15j); SHA-256 is order-sensitive, so hashing the same five blocks in
   a different sequence produces a completely unrelated 32-byte result, with no partial credit for
   "close." Because the actual reference binary — already independently validated cross-ISA and
   across a 20-cell compiler matrix at v0.2 — computes the correct order, the fault was
   conclusively in the document, not the reference and not the C clean-room.
4. **This is the strongest single piece of evidence in this paper.** A spec bug that a from-text
   clean-room in a second language surfaced, that was diagnosed by ruling out every numeric
   candidate before concluding it was documentation, and that was fixed by reordering the spec's
   five witness-chain seed items (the three artifact hashes and the two transcendental-table
   digests, §12.1) to match the reference, and rerunning — after which all four {x86_64, aarch64} × {gcc, clang} cells reproduced
   `CIS2_REF = a0c563ef804f50413b7fb6619ae4afe9b51b1ffa7655e944221393e85d6261da` exactly
   (`docs/E15k_DIVERGENCE_LOCALIZATION.md`, CI run `33200155942`) — is direct, adversarially
   obtained evidence that the specification, once corrected, is sufficient for a from-text-only
   implementer working in an entirely different language and toolchain. We report this as a bug
   found and fixed, in the open, rather than omitting the E15j intermediate mismatch from this
   paper — the honest arc (mismatch, localization, spec fix, full match) is more informative than
   a paper that reports only the final, clean result.

## v0.1 → v0.2: a header-binding change, not a numeric change

`CIS2_REF` changed from v0.1's `ba88708bf4159a4057d4eef727820ebc5ce1744ae334bfe0cc0776e03509dd0f` to
v0.2's `a0c563ef804f50413b7fb6619ae4afe9b51b1ffa7655e944221393e85d6261da`. This is deliberately **not**
evidence of a changed computation: `generated_token_ids` and `argmax_digest`
(`0b9c8f3ac90d0b9cd5f1719ac327dca1fc639fd87468305fccebbe3d56f67aff`) are byte-identical across v0.1
and v0.2 — "none of v0.2's three changes touch what the model actually computes, only how the
receipt hashes it" (`docs/CIS2_SPEC_v0.2.md` §16). The three v0.2 changes are receipt-format changes:
(1) folding the two transcendental-table digests into the `CIS2_REF` seed, ahead of the artifact
hashes, so a receipt mismatch can be caused by a divergent transcendental table and not just a
divergent logit; (2) generalizing the RoPE `ln(theta)` construction from a `rope_theta==100000.0`-only
literal to a spec-pinned `ln_pinned` polynomial valid for any `rope_theta` (validated on both
`100000.0` and `1000000.0`, `docs/E15d_v0.2_DIGESTS.md`); (3) feeding the three artifact hashes as
their raw 32 bytes rather than their 64-character hex-ASCII string into the witness chain. `
table_digest` also changed (`0bf9257bc5...` → `465d358ccd...`), but for a different, narrower
reason: the *set* of coefficients it hashes grew to include the new `ln` polynomial table, not
because of the raw-bytes change (`CIS2_SPEC_v0.2.md` §6.6). `inv_freq_table_digest` is
byte-identical across v0.1 and v0.2 for SmolLM2-135M (`da9f6dcfde0425588815509e874515cdcd3d6b8818b6d0136590052e7bbf6f12`
in both) — evidence that switching from the bare literal to `ln_pinned(rope_theta)` did not move
this specific model's RoPE table at all (`CIS2_SPEC_v0.2.md` §7.2).

---

**Source map**
- Full digest table: `docs/E15b_REFERENCE_RESULT.md`, `docs/E15b_m1p5_CORRECTNESS.md`,
  `docs/E15e_CLEANROOM_RESULT.md`, `docs/E15g_CLEANROOM_V2_RESULT.md`,
  `docs/E15h_REFACTOR_v0.2_RESULT.md`, `docs/E15d_v0.2_DIGESTS.md`.
- Independence audit: `Appendix B: E15g-audit`.
- Adversarial verification: `Appendix B: E15c-verify`.
- v0.1→v0.2 changelog: `docs/CIS2_SPEC_v0.2.md` §16, Appendix A/B.
- C clean-room and its resolved mismatch: `docs/E15j_CLEANROOM_C_RESULT.md`,
  `docs/E15k_DIVERGENCE_LOCALIZATION.md`, CI runs `33197817365` and `33200155942`.
- Transcendental accuracy characterization: `Appendix B: H2-result`,
  `docs/H2_TRANSCENDENTAL_RIGOR.md`.
- Scale/breadth/horizon: `Appendix B: H1-result`, CI run `33214545380`.
- Tokenizer pin: `Appendix B: H4-result`.


# 5. Verification model, threat model, and limitations

This section, like §4, carries no timing or throughput number; every figure below is an identity
claim (Rule A).

## Receipt contents at v0.2

A CIS-2 v0.2 witness chain (`CIS2_REF`, spec §12.1, item order corrected post-E15k) is one
continuous SHA-256 stream over, in order: the three artifact hashes (`weights_sha256`,
`tokenizer_sha256`, `config_sha256`, each 32 raw bytes — raw bytes, not 64-character hex-ASCII, as
of v0.2, spec §12.1 items 1–3, closing v0.1's §14.2 gap), the coefficient-table digest
(`table_digest`, spec §6.6, 32 raw bytes), the RoPE `inv_freq` table digest
(`inv_freq_table_digest`, spec §7.2, 32 raw bytes), the prompt token
ids (`u32` little-endian, 4 bytes each), and then, per decode step, the full fp32 logit vector's
raw bit pattern (`v.to_bits().to_le_bytes()`, 49,152 entries × 4 bytes = 196,608 bytes per step for
this vocabulary size, spec §12.1 item 7a) plus the chosen `next_token_id` (4 bytes). A separate,
independently-hashed `argmax_digest` (token ids only, prompt + all generated) is also computed and
printed but is not an input to `CIS2_REF` (spec §12.2, §12.3). Finalized once, `CIS2_REF` at v0.2
for the pinned SmolLM2-135M / `"Once upon a time"` / 16-token test vector is
`a0c563ef804f50413b7fb6619ae4afe9b51b1ffa7655e944221393e85d6261da` (spec §13.1). **The receipt does
not retain the per-step logits themselves** — only their SHA-256 fold survives — exactly as CIS-1's
receipt does not retain per-step logit vectors either
(`https://github.com/Aefinity-AI/alice-aegis/blob/main/docs/paper/05_receipt.md`, "Verification model").

The receipt binds two things a CIS-1-style receipt does not need to bind separately: the two
transcendental-table digests. This is deliberate (spec §14.3, closing v0.1's corresponding gap): a
`CIS2_REF` match alone previously could not distinguish "an implementation using the exact pinned
polynomial coefficients" from "an implementation whose different coefficients happened to produce
the same logits on this one test vector" — v0.2 makes the coefficient tables themselves part of
what must match. The residual caveat, stated in the spec itself: a `CIS2_REF` *mismatch* still does
not, by itself, localize *which* of the five seed inputs (2 table digests + 3 artifact hashes)
diverged — a verifier wanting to localize a mismatch must still compare the individual digests,
all of which are printed alongside `CIS2_REF` (spec §12.3, §14.3).

## Verification cost = one decode, not succinct

Mirroring CIS-1's own wording (`https://github.com/Aefinity-AI/alice-aegis/blob/main/docs/paper/05_receipt.md`, "Verification
model"): a verifier is an independent implementation of the CIS-2 contract that recomputes the
entire forward pass from the artifact bytes and the declared prompt, and compares its own witness
chain against the claimed one. **Verification cost is one full deterministic decode** — there is no
check cheaper than re-running it, and per-step logits are not stored anywhere for a verifier to
spot-check against; the chain is the only compressed artifact. This is stated as a limitation, not
hidden: CIS-2, like CIS-1, is not a succinct proof system.

**Unlike CIS-1, no separate, zero-shared-code standalone verifier crate exists for CIS-2 today.**
CIS-1's `cis-verify` (`https://github.com/Aefinity-AI/alice-aegis/blob/main/docs/paper/05_receipt.md`, "A37") is a distinct,
`no_std`+alloc crate with zero dependency on `aegis-core`. CIS-2 now has two independent
from-spec-text analogues instead of one: `verify2` (Rust, built in E15g, audited in E15g-audit),
which reproduces every v0.1 and v0.2 digest bit-for-bit
(`docs/E15g_CLEANROOM_V2_RESULT.md`, CI run `33194049057` for the v0.2 rerun); and `verify3` (C11,
built in E15j from spec v0.2 text alone, a different implementer and a different language), which
after the spec-defect fix documented in §4 also reproduces every digest bit-for-bit on all four
{x86_64, aarch64} × {gcc, clang} cells (CI run `33200155942`). Both are still, in this repo's
Appendix A/B language, independence exercises rather than *conformance-checking verifier tools*:
each was built once, and neither is maintained as a standing verifier a third party would run
against an arbitrary claimed receipt without further packaging work. The oracle comparison
(E15b m1.5, PyTorch/`transformers`, 16/16 token match, step-0 logit relative diff ≈3.98e-06) is a
*correctness* check against a different, non-conforming implementation (torch uses its own BLAS
reduction order and libm) — it should not be conflated with a CIS-2 conformance verifier.

## Threat model

Adapted directly from CIS-1's (`https://github.com/Aefinity-AI/alice-aegis/blob/main/docs/paper/05_receipt.md`, "Threat model"):

- **Forgery** requires a chain value consistent with SHA-256 preimage resistance — as in CIS-1,
  breaking SHA-256 or already knowing the true forward-pass output.
- **A divergent implementation** of the CIS-2 contract — wrong reduction order, a slipped-in FMA, a
  different transcendental table, FTZ/DAZ not actually pinned — produces a different logit vector
  at whatever step it first diverges, folding forward through the rest of the chain. The E15c
  adversarial rebuilds (`target-cpu=native` on FMA-capable hardware, `opt-level=0`) are evidence
  this *would* be caught — digest and 0-FMA-instruction count both held under both variants
  (`Appendix B: E15c-verify` §3) — not proof no other
  divergence class exists, since only two rebuild variants were tried.
- **Out of scope**: model weight provenance (only the three sha256 artifact hashes are checked,
  spec §2.1); whether the prompt is secret (hashed in the clear, spec §12.1 item 6, matching CIS-1's
  own convention).
- **Provenance, stated plainly.** All three implementations (reference, `verify2`, `verify3`)
  were written by isolated AI coding agents (Claude, via Claude Code), operated by one human
  author, on a single day, 2026-08-28. Independence here means what each clean-room agent's
  file-access log shows — it never opened `src/` or the sibling clean-room's directory (Appendix
  A) — not different human authorship or elapsed time between attempts (§1, §8 discuss the
  specific limitation this raises: an AI implementer's pretraining knowledge of third-party
  libraries a spec might describe).
- **Where a reviewer should push, stated here rather than only below**: (a) the contract has now
  been independently reimplemented three times from text — E15e from a design memo, which failed
  to converge and located spec gaps (five, per that leg's own report); E15g from the corrected
  spec, in Rust, which converged on the first try; E15j from the spec, in C, a different language,
  which converged on every value except the top-level witness digest, whose diagnosis (§4) located
  a genuine self-contradiction in the spec's own prose, fixed and reconfirmed (E15k) — plus one
  independence audit of the Rust clean-room (Appendix B: E15g-audit). This is comparable in count to CIS-1's
  two clean-room implementers (A31) plus its standalone `cis-verify` crate (A37), and is
  cross-language where CIS-1's clean-room legs were not; CIS-2 still lacks CIS-1's
  standing-verifier-tool precedent (a maintained, `no_std` verifier a third party runs against an
  arbitrary receipt, rather than a one-time clean-room exercise). (b) "bit-identical" means
  full-logit-vector bit-identical across CI-hosted runner instances (`ubuntu-latest`,
  `ubuntu-24.04-arm`) — reproduced across multiple separate CI runs, a 20-cell compiler-invariance
  matrix at v0.2 (`docs/E15d_v0.2_DIGESTS.md`), and, as of this document, a compiler-*version* pin
  via `rust-toolchain.toml` (channel `1.98.0`, both targets) closing the earlier "no hard
  compiler-version pin" gap — but still not on physical (non-cloud-runner) aarch64 hardware, and
  not on a third ISA; a consumer-device (phone-class) aarch64 leg remains open (§8). (c) the
  verifier-cost claim ("one full decode, no cheaper check") is asserted by analogy to CIS-1's own
  wording, not independently measured for CIS-2's reference — no wall-clock number for a CIS-2
  verification run appears in any log this document draws on (Rule A: none reported, so none
  claimed).

## Limitations

- **fp32 scalar reference, not a fast kernel.** No SIMD-optimized implementation has been built or
  shown to match the reference's bits; gate 6 of the contract (§3, "everything else is free") is
  stated but "not yet exercised" against any optimized kernel
  (`docs/CIS2_PAPER_OUTLINE.md` §3 row 6). CIS-1's own experience (A26/A27,
  `https://github.com/Aefinity-AI/alice-aegis/blob/main/docs/paper/03_semantics.md` §6) shows this is where real engineering cost
  and real divergence risk lives; CIS-2 has not yet paid that cost or found that risk.
- **135M is the only normative test vector; up to ~1.5B parameters is the validated range, not an
  unbounded claim.** `HuggingFaceTB/SmolLM2-135M` is the pinned §13.1 test vector.
  `Qwen/Qwen2.5-0.5B` (`rope_theta=1000000`) and `Qwen2.5-1.5B` are informative second- and
  third-checkpoint evidence — cross-ISA identical and oracle-correct at 1.5B scale, at decode
  horizons of 16/128/512 tokens (`Appendix B: H1-result`)
  — but neither is a §13.1 normative test vector. No model above ~1.5B parameters, and no
  grouped-query-attention architecture, has been run through this reference.
- **Greedy decoding only.** No sampling, no temperature, no top-k/top-p (spec §3.4, §0); this
  matches CIS-1's own non-goal (CIS-1 spec §10, cited in `CIS2_SPEC_v0.2.md` §0).
- **CPU only.** No GPU path exists or is claimed; the entire motivating problem this contract
  responds to (cross-hardware nondeterminism, batch invariance) is largely a GPU-kernel
  phenomenon in prior art, and CIS-2 has not shown its contract is relevant to, let alone
  achievable on, GPU kernels.
- **Cloud CI runners only, no physical aarch64 leg.** Both aarch64 results in this document are
  hosted GitHub Actions runners (`ubuntu-24.04-arm`); no phone or physical Raspberry-Pi-class board
  has run this reference, unlike CIS-1's own physical-iron legs
  (`https://github.com/Aefinity-AI/alice-aegis/blob/main/docs/paper/05_receipt.md`, A33/A34). Cloud-runner legs are identity
  evidence only, per CIS-1's own convention for naming such legs precisely.
- **Transcendental route is "pinned by fiat," not "correctly-rounded by construction."** Spec §6.2's
  own text is explicit that route (b) — the pinned Cephes-pattern polynomial actually used — was a
  fallback: no published Rust crate/binding for a correctly-rounded route (a) library (CORE-MATH,
  RLIBM) was found on crates.io when this was built. Two independent implementations that each
  independently chose route (b) would need to copy the exact same coefficients to converge; this is
  precisely the gap E15e's mismatch traced to before the spec pinned the coefficients as text.
- **`ln_pinned`'s validated domain is a finite tested set, not a general accuracy proof** (spec
  §14.1): validated to ≤2e-6 relative tolerance against host `f64::ln` at
  `x ∈ {0.001, 0.1, 0.5, 0.999, 1.0, 1.5, 2.0, 10.0, 100.0, 100_000.0, 1_000_000.0}`; the two values
  that matter for this document's pinned models (`100_000.0`, `1_000_000.0`) are both in that set,
  but a `rope_theta` far outside it is unvalidated.
- **Trig polynomial accuracy degrades with position; determinism does not.** A dedicated
  characterization (H2) found the RoPE sine/cosine range reduction — constrained to pure fp32,
  no FMA, no f64 staging — loses accuracy against a correctly-rounded oracle as position grows:
  up to 1104 ULP / ~1.00e-4 relative error by position 19 on the pinned test vector's grid, via
  catastrophic cancellation in the two-constant range reduction, and reaching ≥0.58 relative error
  projected toward the model's maximum position (8192) — informative only, since no test vector
  this document validates decodes that far. This is an *accuracy*, not a *determinism*, finding:
  both ISAs still agree bit-for-bit regardless of position. Separately, a 512-token oracle
  comparison against PyTorch (H1) found the drift tolerable within tolerance at that horizon, so
  the accuracy claim is bounded to ≤512 tokens as validated, not to the `|x| ≲ 14` figure carried
  from earlier drafts of this spec, which undersold how far the accuracy claim actually reaches
  before degrading. A future spec revision with an accurate range reduction (e.g., Payne–Hanek or
  f64-staged reduction) would be required before claiming oracle accuracy beyond ~512 tokens.
- **Compiler toolchain is now pinned** (`rust-toolchain.toml`, channel `1.98.0`, both targets),
  closing the earlier "no hard compiler-version pin" gap; CI legs before this pin existed landed on
  the same `rustc` version by chance, not by a structural guarantee
  (`Appendix B: E15c-verify`, "Overall verdict").
- **No standing, independently-maintained verifier tool**, as distinct from the one-time clean-room
  exercises (E15e, E15g, E15j) described in §4 — see "verification cost" above.
- **No physical consumer-device (phone-class) aarch64 leg.** All aarch64 results in this document
  are hosted CI runners; a real consumer aarch64 device reproducing the digest is an open item,
  blocked on unrelated tooling (`Appendix B: SLAM-DUNK-CRITERIA`
  row 8).
- **Transcendental route is pinned by fiat, not correctly rounded.** As stated in §2 (related
  work) and spec §6.2: no published correctly-rounded Rust library was adopted; the Cephes-pattern
  polynomial is the pinned route, and its exact coefficients — not merely its output — are made
  part of the receipt (spec §6.6, §12.1) specifically because two implementations choosing "a
  correctly-rounded-in-spirit route" independently would not otherwise be guaranteed to converge.

---

**Source map**
- Receipt format and byte encoding: `docs/CIS2_SPEC_v0.2.md` §12.1–§12.4.
- Verification-model and threat-model wording pattern: `https://github.com/Aefinity-AI/alice-aegis/blob/main/docs/paper/05_receipt.md`.
- Adversarial rebuild evidence: `Appendix B: E15c-verify`.
- Independence audit: `Appendix B: E15g-audit`.
- Known gaps: `docs/CIS2_SPEC_v0.2.md` §14, Appendix B.
- C clean-room / spec-defect resolution: `docs/E15j_CLEANROOM_C_RESULT.md`, `docs/E15k_DIVERGENCE_LOCALIZATION.md`.
- Transcendental accuracy: `Appendix B: H2-result`.
- Scale/breadth/horizon: `Appendix B: H1-result`.
- Slam-dunk criteria (row 8 phone leg open): `Appendix B: SLAM-DUNK-CRITERIA`.


# 6. Mechanism, in detail

§3 states the nine gates as a contract; this section walks through how each is actually enforced
at the instruction and byte level, and how the witness chain composes them into one checkable
value — including the one place the mechanism itself was found to be misdescribed.

## 6.1 Denormal handling: FTZ/DAZ pinned and readback-verified

IEEE-754 binary32 subnormal numbers are handled differently by default on the two ISAs this
contract targets: x86_64 SSE/AVX units read the MXCSR control register (bit 15 = FTZ,
flush-to-zero on output; bit 6 = DAZ, denormals-as-zero on input), while aarch64 NEON/FP units
read FPCR bit 24 (FZ). Left at hardware defaults, whether a subnormal intermediate value is
flushed to zero or kept can differ between the two ISAs on the exact same arithmetic sequence.
CIS-2 pins both bits on before any decode-path arithmetic runs, via a direct register
read-modify-write (not a wrapper function whose correctness a caller must assume) — and then
**reads the register back** to assert the bits actually took, rather than merely asserting "we
called the setter and did not error." An adversarial unit test feeds a genuine subnormal value
through a `black_box`-guarded operation (so the compiler cannot constant-fold the subnormal away
at compile time) and asserts it flushes to zero, on both ISAs, in CI.

## 6.2 Round-to-nearest-even

CIS-2 does not set any rounding-mode control bit: IEEE-754's default rounding mode, and the
default assumed by essentially every conforming CPU floating-point unit at process start, is
round-to-nearest-even. The contract's requirement here is negative — that nothing in the decode
path changes the rounding mode away from this default — verified by absence rather than presence
(no rounding-mode-control call appears anywhere in the decode path's source).

## 6.3 No FMA contraction, enforced by disassembly

Fused multiply-add computes `a*b + c` with a single rounding, rather than rounding the product
and then rounding the sum separately — a real accuracy improvement, and exactly the kind of
compiler- or hardware-introduced degree of freedom this contract cannot tolerate, because whether
a given `a*b+c` gets contracted depends on optimization level, target CPU flags, and instruction
scheduling, none of which is under a spec author's control unless explicitly forbidden. CIS-2
writes every multiply-accumulate as two separate statements (`let p = a[i]*b[i]; acc = acc + p;`)
and never calls `f32::mul_add`, but does not stop at trusting the source: a disassembly gate
(`objdump -d` filtered for `vfmadd`/`vfnmadd`/`vfmsub`/`vfnmsub` on x86_64 and `fmadd`/`fmsub` on
aarch64) runs against the actual release binary in CI, and a mechanical grep test additionally
scans the source tree for `mul_add` calls. This was adversarially rebuilt with
`RUSTFLAGS="-C target-cpu=native"` on FMA-capable local hardware specifically to give the compiler
every opportunity to contract — the resulting binary still shows zero FMA instructions and an
unchanged digest, and the same check passes across a 20-cell `{opt-level 0,1,2,3,s} ×
{target-cpu generic,native} × {x86_64,aarch64}` matrix.

## 6.4 Scalar, strictly left-to-right reductions

Every dot product, sum-of-squares, and weighted accumulation in the decode path — matrix-vector
rows, RMSNorm's sum of squares, softmax's normalizing denominator, the attention value-mix — folds
in a plain `for` loop over index order `0..n-1`, one scalar accumulator, no pairwise-tree
reduction, no SIMD-lane reordering, no chunked partial sums recombined afterward. This matters
because fp32 addition is not associative: summing the same set of numbers in two different valid
orders can produce two different, both individually "correct," results. A regression test makes
this concrete rather than asserting it abstractly: dotting `[1e8, 1.0, -1e8]` against `[1.0, 1.0,
1.0]` in the pinned left-to-right order returns exactly `0.0_f32` (the middle `1.0` term is
entirely lost to rounding against the `1e8` partial sum before the `-1e8` term arrives), while
almost any other valid summation order returns a different, nonzero answer for the same three
numbers. Pinning order this precisely, and testing that the precision loss is exactly what pinning
predicts, is the direct fp32 analogue of CIS-1's bounded-integer-accumulator gate — except CIS-2
cannot get away with pinning only the type, because the type here (`f32`) does not make the
answer order-independent on its own.

## 6.5 Pinned transcendentals: Cephes-pattern polynomials, hex-specified coefficients, no libm

IEEE-754 mandates that `sqrt` and division be *correctly rounded* — the unique closest
representable result — so any conformant hardware unit already agrees bit-for-bit on these two
operations across ISAs; CIS-2 pins nothing further for `sqrt`/`/` and uses the hardware
instruction directly. `rsqrt_cr` (spec §6.1) is the composition of two such correctly-rounded
operations, `1.0 / x.sqrt()`; this composition is deterministic and cross-ISA-identical by
construction (both component operations are individually correctly rounded on any conformant
hardware), but the composite result is not itself guaranteed correctly rounded — composing two
correctly-rounded operations does not, in general, yield a correctly-rounded answer to the
composite function. IEEE 754-2019 §9.2 makes no rounding guarantee at all for `exp`, `sin`, `cos`,
and `ln` — it only *recommends*, and does not require, correctly-rounded results for these
functions; the actual behavior of a platform's implementation is governed by the C standard, not
IEEE-754, and glibc's own regression-testing infrastructure documents that its `libm` does not
guarantee identical rounding for these functions across architectures (glibc ships separate,
per-architecture allowed-error tables, `sysdeps/<arch>/libm-test-ulps`, precisely because observed
behavior differs by target). CIS-2 sidesteps this class of divergence entirely rather than trying
to characterize and match it: it never calls a platform
math library for any of the four functions, computing each instead as a Cephes-pattern range
reduction followed by a fixed-degree Horner-scheme polynomial evaluation, over coefficients
specified in the spec text as exact hexadecimal `f32` bit patterns (not decimal literals, which
would themselves be a source-to-binary rounding ambiguity). A dedicated numerical characterization
against a 60-digit `mpmath` oracle plus correctly-rounded-fp32 neighbor search (H2) found
`exp_pinned` accurate to ≤1 ULP and `ln_pinned` exactly 0 ULP at both pinned `rope_theta` values
used in this document's test vectors — but also found `sin_pinned`/`cos_pinned` reaching up to
1104 ULP (~1.00e-4 relative error) by decode position 19 on the pinned model's grid, traced to
catastrophic cancellation in the two-constant range reduction (`reduce_2pi`) rather than to the
polynomial itself, an accuracy limitation stated in full in §8 that does not affect the
determinism claim — the same wrong-by-1104-ULP value is still computed identically on both ISAs,
every time.

## 6.6 Theta-general RoPE `inv_freq`

Rotary position embeddings require `inv_freq[i] = theta^(-2i/head_dim)`, computed once per model
and reused every decode step. An earlier internal version of this construction hardcoded the
natural log of one specific `rope_theta` value as a literal, which technically worked for the one
model tested but silently made the "general spec" claim false for any other checkpoint. v0.2
replaced the literal with `inv_freq[i] = exp_pinned(-(2i/head_dim) · ln_pinned(rope_theta))`,
computed from whatever `rope_theta` value is actually read out of the checkpoint's `config.json`
— validated against two different `rope_theta` values (100,000 for SmolLM2-135M, 1,000,000 for
Qwen2.5-0.5B/1.5B) and confirmed to reproduce the same `inv_freq_table_digest` on SmolLM2 as the
older literal-based construction, i.e., generalizing the formula did not silently move the one
value already validated.

## 6.7 The witness chain, §12.1, and the defect the C clean-room exposed

The receipt (`CIS2_REF`) is one continuous SHA-256 hash object, fed in order and finalized once —
not a step-wise re-hash of `running_digest || new_data`, which would be a different and weaker
construction. The five 32-byte seed values are the three artifact hashes (weights, tokenizer,
config, each as raw bytes) followed by the two transcendental table digests (the pinned
coefficient table, then the RoPE `inv_freq` table); then every prompt token id as little-endian
`u32`; then, per decode step, the complete 49,152-entry fp32 logit vector's raw bit pattern
(`v.to_bits().to_le_bytes()` for every vocabulary entry, in index order — not just the winning
entry) followed by the chosen token id.

This exact order is itself the mechanism's one documented failure and repair. The spec's own
prose, as originally written, described the five seed items in the *reverse* group order (table
digests first, then artifact hashes) — a documentation error that did not match what the reference
binary actually computed, and was invisible until a from-spec-text clean-room implementer in a
different language (C, `verify3/`) transcribed the prose faithfully and produced every downstream
value correctly except the final witness digest, because SHA-256 output is a discontinuous
function of input order: five already-bit-identical 32-byte blocks fed in a different sequence
produce a completely unrelated hash, with no partial credit. Diagnosing this required first
proving, layer by layer, that the forward pass itself was already bit-identical between the two
implementations (ruling out every numeric candidate), which left only the receipt-assembly step
as the remaining explanation — found, confirmed against the unmodified and independently
cross-ISA/cross-compiler-validated reference binary as the source of truth, and fixed by
correcting the spec's prose (not the reference, which was already correct) and the C
implementation to match. Full detail and the CI evidence for this repair are in §4.

---

**Source map**
- FTZ/DAZ: `CIS2_SPEC_v0.2.md` §1.3; `Appendix B: E15c-verify` item 2.
- No-FMA gate: `CIS2_SPEC_v0.2.md` §1.4; `docs/E15d_v0.2_DIGESTS.md`.
- Reduction order: `CIS2_SPEC_v0.2.md` §5.1, §5.3.
- Transcendentals and accuracy characterization: `CIS2_SPEC_v0.2.md` §6.1–§6.7;
  `Appendix B: H2-result`.
- RoPE `inv_freq` generalization: `CIS2_SPEC_v0.2.md` §7.1–§7.2.
- Witness chain and its corrected order: `CIS2_SPEC_v0.2.md` §12.1;
  `docs/E15j_CLEANROOM_C_RESULT.md`; `docs/E15k_DIVERGENCE_LOCALIZATION.md`.


# 7. Why it matters

**The problem this displaces.** Deployed floating-point language models are, today, essentially
un-auditable at the bit level: a claim of the form "this specific model, given this specific
input, produced this specific output" cannot be checked by a third party without either trusting
the party that ran it, or re-running the same model on the same vendor's hardware and hoping the
scheduler, batch size, and kernel library line up closely enough to reproduce a "close" answer.
That gap matters most exactly where it is hardest to close: safety evaluations, red-team
transcripts, incident post-mortems, and any setting where "what did the model actually compute"
is a question with legal or safety weight, not just a curiosity. CIS-2 shows this gap is not
inherent to floating-point arithmetic — it is inherent to leaving IEEE-754's degrees of freedom
unpinned, which is a choice, not a law of nature.

**Verifiable inference receipts.** The concrete deliverable is a receipt format any third party
can recompute: given the three model artifact hashes, the prompt, and the claimed decode length,
an independent CIS-2-conforming implementation reproduces the same 32-byte witness digest by
actually re-running the decode, not by checking a signature or trusting an attestation. This is a
stronger property than the attestation-based supply-chain literature (§2) typically offers,
because it requires trusting no hardware root-of-trust and no attesting party — only that SHA-256
is not broken and that the verifier's own implementation is itself conformant, which is exactly
the property this paper spends §4–§5 establishing evidence for via independent, from-spec-text
reimplementation.

**Safety and audit framing.** A receipt that a skeptical third party can recompute from scratch is
useful in exactly the settings where trust is scarce: a regulator or auditor examining whether a
deployed model produced the output a vendor claims it produced; a red-team exercise where the
transcript needs to be reproducible bit-for-bit on independent infrastructure, not merely
"similar" within some tolerance a defender chooses after the fact; an incident investigation where
"did the model actually compute this, or was the log altered" needs an answer that does not
require trusting the party under investigation. None of this requires CIS-2 models to be fast,
large, or state-of-the-art — it requires the numerical contract underneath them to be pinned
precisely enough that "recompute it and compare" is a meaningful, cheap-relative-to-the-question
(if not cheap-in-absolute-terms, §5) way to check a claim.

**Supply chain.** A model artifact plus a CIS-2 spec version plus a witness digest is a
self-contained, checkable claim about what a specific checkpoint computes on a specific input,
independent of which vendor's inference stack produced it. This is a narrower and more mechanical
property than general ML supply-chain provenance schemes (§2's discussion of Laminator, Kettle,
and related attestation work), which typically bind a declared input to a declared output via a
trusted attestor or hardware root-of-trust; CIS-2's receipt instead lets a party with no prior
trust relationship to either the model provider or the hardware verify the claim by paying the
cost of one full decode themselves.

**What this is not, stated plainly.** This is not a speed result, a compression result, or a
claim that CIS-2-conforming inference is competitive with an optimized production kernel — no
optimized (SIMD, GPU) implementation exists yet, and §8 states this without qualification. It is
not a claim of general applicability to arbitrarily large models, sampling-based decoding, or
architectures beyond the two families and the parameter range actually tested. It is a claim about
what is achievable, in principle and in a working reference, for the specific and narrow property
of bit-identical, third-party-verifiable fp32 transformer decode — offered as a foundation a
faster, more general implementation could later be built and checked against, not as that
implementation itself. Funding and adoption questions around this work are technology-neutral:
the contribution is the specification and the demonstrated convergence of independent
implementations toward it, not a product, a company, or a procurement claim of any kind.


# 8. Limitations

Stated without softening, in the order a hostile reviewer would ask about them. Full evidence and
source citations for each item are in §5's "Limitations" subsection and the source map below; this
section is the canonical, consolidated list.

1. **fp32 scalar reference, not a fast kernel.** No SIMD-optimized, GPU, or otherwise
   performance-engineered implementation of this contract has been built or shown to reproduce the
   reference's bits. The contract's §3 gate list states that memory layout, tiling, and vector
   strategy are free as long as the pinned bits match — but that freedom has not yet been
   exercised by an actual optimized kernel, so it is a design intention, not a demonstrated result.
2. **CPU only.** No GPU code path exists or is claimed. The motivating problem this contract
   responds to overlaps substantially with a GPU-kernel phenomenon in prior work (§2), and CIS-2
   has not shown its mechanism transfers to, or is even relevant on, GPU execution.
3. **Model scale validated up to ~1.5B parameters, not unbounded.** The only *normative* test
   vector is `HuggingFaceTB/SmolLM2-135M`. `Qwen2.5-0.5B` and `Qwen2.5-1.5B` are informative,
   cross-ISA-identical and oracle-correct additional evidence, spanning a second architecture
   (QKV-bias attention) and roughly an order of magnitude more parameters than the pinned vector —
   but no model above ~1.5B parameters, and no grouped-query-attention architecture, has been run
   through this reference at all.
4. **Greedy decoding only.** No sampling, temperature, top-k, or top-p decoding is defined or
   tested; this matches CIS-1's own explicit non-goal.
5. **RoPE trigonometric accuracy degrades with position; determinism does not.** The sine/cosine
   range reduction, constrained to pure fp32 with no FMA and no f64 staging, loses accuracy
   against a correctly-rounded oracle as decode position grows — characterized at up to 1104 ULP
   (~1.00e-4 relative error) by position 19 on the pinned test vector's grid, and projected to
   exceed 0.58 relative error toward the model's maximum context length. A 512-token oracle
   comparison against PyTorch found this drift still tolerable within the checked tolerance at that
   horizon, so the **accuracy** claim (agreement with a high-precision or PyTorch oracle) is
   validated only up to roughly 512 tokens. The **determinism** claim (both ISAs compute the same
   bits, however wrong or right) is unaffected by this at any position — this is an accuracy
   limitation, not a reproducibility one, and the two should not be conflated.
6. **The transcendental route is pinned by fiat, not correctly rounded.** No published
   correctly-rounded Rust implementation of the needed functions was available when this reference
   was built; CIS-2 pins a specific Cephes-pattern polynomial and hex-specified coefficients
   instead, and binds the exact coefficient table into the receipt (rather than only the resulting
   logits) precisely because two implementations both aiming for "a correctly-rounded-in-spirit
   route" independently would not otherwise be guaranteed to converge to the same bits.
7. **No physical, consumer-device aarch64 leg.** All aarch64 evidence in this paper comes from
   hosted cloud CI runners (`ubuntu-24.04-arm`). A real consumer aarch64 device (phone-class
   hardware) reproducing the digest is an explicitly open item at the time of writing, blocked on
   unrelated device tooling, not on any known numerical or spec issue.
8. **No standing, independently-maintained verifier tool.** Two from-spec-text clean-room
   implementations exist (Rust `verify2`, C `verify3`), each of which reproduces every conformance
   digest bit-for-bit — but both were built once, as independence exercises, and neither is
   packaged or maintained as a tool a third party could point at an arbitrary claimed CIS-2 receipt
   today without additional engineering.
9. **Verification is one full decode, not succinct.** There is no cheaper check than re-running
   the entire deterministic decode and comparing witness digests; per-step logits are not retained
   anywhere for a spot-check, only their SHA-256 fold. This is a design choice inherited from
   CIS-1's own receipt philosophy, stated as a limitation rather than a proof-system property.
10. **Independence, honestly qualified — these are AI agents operated by one human, not separate
    human implementers.** All three implementations (reference, `verify2`, `verify3`) were written
    by isolated AI coding agents (Claude, via Claude Code), operated by one human author, on a
    single day, 2026-08-28. The independence claim rests on each clean-room agent's file-access log
    (Appendix A) showing it never opened `src/` or the sibling clean-room's directory, and on the
    resulting digests — not on organizational or temporal separation between humans. This raises a
    caveat that a human-clean-room precedent (e.g., CIS-1's) would not: an AI implementer carries
    pretraining knowledge of the exact third-party libraries and algorithms a spec might describe,
    which can substitute for reading the spec text on an ambiguous point without the implementer
    (or a reviewer) being able to tell the difference from the output alone. Concretely,
    `verify3`'s byte-level BPE tokenizer was written from the model's general pretraining knowledge
    of the Hugging Face `tokenizers` crate's internals *before* spec §3.1 was written and pinned
    (v0.2.1), and has not since been re-derived from §3.1's text alone to check whether pretrained
    knowledge or the spec text is what actually produced the matching tokenizer — an open item, not
    resolved in this pass. Separately, the three clean-room legs (§4) establish that the spec text
    is sufficient for these particular implementers; they do not establish independence from each
    other in every dimension (e.g., all three implementers also share the same publicly-cited
    underlying algorithms, such as the `tokenizers` crate's BPE specification, and the same SHA-256
    standard) — the claim is "independently reimplemented from the spec, by isolated agents," not
    "invented the underlying cryptographic and tokenization primitives from nothing," which was
    never the intended scope.

None of these limitations is hidden elsewhere in the paper's prose; each is repeated, with its
evidence, in §5.

---

**Source map**
- Items 3, 5: `Appendix B: H1-result`,
  `Appendix B: H2-result`, `docs/H2_TRANSCENDENTAL_RIGOR.md`.
- Item 6: `CIS2_SPEC_v0.2.md` §6.2, §12.1, §12.3.
- Item 7: `Appendix B: SLAM-DUNK-CRITERIA` row 8.
- Item 8: `docs/E15g_CLEANROOM_V2_RESULT.md`, `docs/E15j_CLEANROOM_C_RESULT.md`, `docs/E15k_DIVERGENCE_LOCALIZATION.md`.
- Item 10: `Appendix B: H4-result`.


# 9. Reproducibility

Repository: `Aefinity-AI/cis2-spec` (specification, reference `src/`, `verify2/`, `verify3/`, `docs/`, `hardware_logs/`; Apache-2.0
alongside this paper per the publish decision). Branch for this paper's evidence:
`cm/cis2-paper-draft`, merged from `main` at commit range ending `395ebdb`. Spec version: `docs/CIS2_SPEC_v0.2.md` at v0.2.1 (tokenizer §3.1 fully pinned, doc-only over v0.2; digests unchanged, §3). Toolchain pin:
`rust-toolchain.toml` (channel `1.98.0`, targets `x86_64-unknown-linux-gnu` and
`aarch64-unknown-linux-gnu`).

## 9.1 Rust reference (`src/`), primary test vector

```
mkdir -p weights
curl -sSf -L -o weights/config.json     https://huggingface.co/HuggingFaceTB/SmolLM2-135M/resolve/main/config.json
curl -sSf -L -o weights/tokenizer.json  https://huggingface.co/HuggingFaceTB/SmolLM2-135M/resolve/main/tokenizer.json
curl -sSf -L -o weights/model.safetensors https://huggingface.co/HuggingFaceTB/SmolLM2-135M/resolve/main/model.safetensors
echo "80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1  weights/model.safetensors" | sha256sum -c -
cargo test --release
./scripts/no_fma_gate.sh
cargo build --release
./target/release/cis2-fp weights/model.safetensors weights/config.json weights/tokenizer.json
```

Expected output includes:

```
CIS2_REF digest=a0c563ef804f50413b7fb6619ae4afe9b51b1ffa7655e944221393e85d6261da prompt_idx=0 prompt_toks=4 gen_toks=16 dtype=fp32
table_digest=465d358ccd63721256dbd2abbc77ad5de755adf3230635f95b12b1727dfa1ea3
inv_freq_table_digest=da9f6dcfde0425588815509e874515cdcd3d6b8818b6d0136590052e7bbf6f12
argmax_digest=0b9c8f3ac90d0b9cd5f1719ac327dca1fc639fd87468305fccebbe3d56f67aff
generated_token_ids=[28,665,436,253,1838,8180,3365,14176,30,2306,4161,281,253,2066,2291,351]
```

reproduced on both x86_64 (`ubuntu-latest`) and aarch64 (`ubuntu-24.04-arm`) in CI run
`33171752921` (jobs `98850338683`/`98850338874`), and again after the v0.2 receipt-format change
in the E15i/E15d(a) 20-cell compiler-invariance matrix, CI run `33195649908`.

## 9.2 C11 clean-room (`verify3/`), cross-language check

```
cd verify3
make CC=gcc      # or CC=clang
objdump -d cis2_verify3 | grep -Ei 'vfmadd|vfnmadd|vfmsub|vfnmsub|fmadd|fmsub|fmla|fmls'   # expect no matches
./cis2_verify3 ../weights/model.safetensors ../weights/config.json ../weights/tokenizer.json
```

Expected output (all four {x86_64, aarch64} × {gcc, clang} cells, post-E15k spec fix):

```
CIS2_VERIFY3 digest=a0c563ef804f50413b7fb6619ae4afe9b51b1ffa7655e944221393e85d6261da prompt_idx=0 prompt_toks=4 gen_toks=16 dtype=fp32
CIS2_VERIFY3 conformance=PASS
```

CI run `33200155942` (workflow `.github/workflows/e15k-divergence-localization.yml`); the
pre-fix, three-of-four-match state is preserved for the record in run `33197817365`
(`.github/workflows/e15j-cleanroom-c.yml`).

## 9.3 Rust clean-room (`verify2/`), independence audit

Built from `CIS2_SPEC_v0.1.md`/`v0.2.md` text alone by a separate implementer, `src/`/`verify/`
never opened; reruns the same reference build/test sequence as §9.1 against `verify2/`'s own
`Cargo.toml`. Expected `CIS2_REF` and `inv_freq_table_digest` identical to §9.1's values on both
ISAs. CI run `33194049057` (v0.2 rerun); independence findings (verbatim-line overlap 18.0%,
attributable to spec-pinned constants, not copying) in
`Appendix B: E15g-audit`.

## 9.4 Scale/breadth/horizon (Qwen2.5-1.5B, 512-token) — reference implementation only

Workflow `.github/workflows/h1-scale-breadth.yml`, CI run `33214545380` (9 jobs, all SUCCESS):
cross-ISA digest equality for Qwen2.5-1.5B at `gen_toks ∈ {16, 128, 512}`, cross-ISA digest
equality for SmolLM2-135M at `gen_toks = 512`, and a 512-token oracle-correctness comparison
against PyTorch fp32 for Qwen2.5-1.5B. This leg exercises the Rust reference implementation only;
neither clean-room (`verify2`, `verify3`) has been run against Qwen2.5-1.5B or at these longer
horizons. `Appendix B: H1-result` reports only pass/fail verdicts; the literal hex digests below
were pulled directly from run `33214545380`'s job logs (`gh api
repos/Aefinity-AI/cis2-fp/actions/jobs/{id}/logs`), not from any summary report, since the run's
artifacts are not expired at the time of this writing:

```
Qwen2.5-1.5B  gen_toks=16   CIS2_REF=5670920223a840d33fcd1dd0154c8f650b09e73a6c5a0066b848a0dd1b347776  argmax_digest=c2c9f68961ac669f888e369fb851ffbb31fb9b359de4204bd8825d955264c5b9
Qwen2.5-1.5B  gen_toks=128  CIS2_REF=7b6f177ca8d2bec21dedb40296386efb9b7fc4a65e582a23df7edbd361138068  argmax_digest=940db72dcc2f48cc83f386214016aea758166d8f26848e984b4e2f5adef24b0d
Qwen2.5-1.5B  gen_toks=512  CIS2_REF=f2f0c8a05da25eb7f2cf4f24b4ed7d9d866d84f8053ee577826e6cde869a3c1d  argmax_digest=270018a12c07641b00e03e39fdefe746229de11cf941800892e8849a878b4def
Qwen2.5-1.5B  table_digest=465d358ccd63721256dbd2abbc77ad5de755adf3230635f95b12b1727dfa1ea3 (unchanged vs. SmolLM2 — shared transcendental table)
Qwen2.5-1.5B  inv_freq_table_digest=02908dae2c15329014dd986fec8033e03427fba0935b04b864ab2bc75fe3bc44 (rope_theta=1000000, distinct from SmolLM2's table)
SmolLM2-135M  gen_toks=512  CIS2_REF=27d319bb77be096e34b34c8bd490b6ed53b56300049a4a92d683e9969c7653a4  argmax_digest=bd54450756235fe4d2e06f0310fcaeaeb1aba3d6a5c19f485f080767be7bc4f6
Qwen2.5-1.5B  512-tok oracle: max_abs_diff=6.473064422607422e-05 at idx=19896 (rust=1.8892077207565308, oracle=1.8891429901123047), relative diff=2.445408220505891e-06 < 0.01, all 512 tokens match
```

All values above matched bit-for-bit between the `ubuntu-latest` (x86_64) and `ubuntu-24.04-arm`
(aarch64) jobs of run `33214545380`; the aggregate jobs (`aggregate-qwen15b`, `aggregate-smollm2-512`)
printed `PASS` for both comparisons.

## 9.5 Transcendental accuracy characterization (no CI run — offline analysis)

`docs/H2_TRANSCENDENTAL_RIGOR.md` documents a Python port of §6's pinned functions
(`numpy.float32`, matching rounding semantics) checked against an `mpmath` 60-digit oracle plus
correctly-rounded-fp32 neighbor search; this is an analysis script, not a CI-gated build, and is
included in the repository for direct re-run.

## 9.6 What this section does not claim

No wall-clock timing, throughput, or performance number is reported for any of the above builds or
runs, per Rule A. Every command above re-derives an identity claim (a digest) or an accuracy claim
(an ULP/relative-error figure against an oracle), not a speed claim.


# 10. References

- N. Cankaya. "Bit-Exact AI Inference Verification Without Performance Tradeoffs." arXiv:2606.00279
  (v1 29 May 2026, v2 5 Jun 2026). [venue] 2026 workshop best paper.
  https://arxiv.org/abs/2606.00279 — code: https://github.com/NaciCankaya/hardware_rounding_error_predictor

- Thinking Machines Lab. "Defeating Nondeterminism in LLM Inference." Blog post, Sep 2025.
  https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/ — code:
  https://github.com/thinking-machines-lab/batch_invariant_ops

- Gond et al. "LLM-42: Enabling Determinism in LLM Inference with Verified Speculation."
  arXiv:2601.17768 (Jan 2026). https://arxiv.org/abs/2601.17768 — code: https://github.com/microsoft/llm-42

- "MarginGate: Sparse Margin-Triggered Verification for Batch-Invariant LLM Inference."
  arXiv:2605.30218. https://arxiv.org/pdf/2605.30218

- CORE-MATH project. Correctly-rounded elementary function implementations.

- RLIBM family: "RLIBM-32," "RLIBM-PROG," "RLIBM-MultiRound." arXiv:2104.04043, arXiv:2111.12852,
  arXiv:2504.07409. Code: https://github.com/rutgers-apl/rlibm-all

- Ahrens, Nguyen, Demmel et al. ReproBLAS; Intel oneMKL Conditional Numerical Reproducibility
  (CNR) mode documentation.
  https://intel.com/content/www/us/en/develop/documentation/onemkl-linux-developer-guide/top/obtaining-numerically-reproducible-results/reproducibility-conditions.html

- "Randompack: Cross-Platform Reproducible RNG and Distribution Sampling." arXiv:2605.05099.

- "Laminator: hardware-attested ML property cards." arXiv:2406.17548.

- "Kettle: attested builds for ML supply chains." arXiv:2605.08363.

- "LLM supply-chain attestation scalability risk." arXiv:2602.19021.

- "Module repositories for ML supply chains." arXiv:2603.02512.

- "Reproducibility is the New Copyleft: Defining AGI-oriented Reproducible Builds."
  arXiv:2606.03019. https://arxiv.org/abs/2606.03019

- S. L. Moshier. *Cephes Mathematical Function Library*, 1992 (and subsequent releases). The
  range-reduction-plus-polynomial pattern and the polynomial coefficients CIS-2's `exp`/`sin`/
  `cos`/`ln` are built from are Moshier's; CIS-2's contribution is pinning them as spec text and
  binding them into a receipt, not originating the numerical method. http://www.netlib.org/cephes/

- J. Demmel, H. D. Nguyen. "Fast Reproducible Floating-Point Summation." *21st IEEE Symposium on
  Computer Arithmetic*, 2013. Introduces ReproBLAS's reproducible-summation approach; cited in §2
  alongside the follow-on TOMS paper below as adjacent, thread-count/vendor-scoped reduction-order
  reproducibility work, distinct from CIS-2's cross-ISA, cross-language, full-logit claim.

- P. Ahrens, J. Demmel, H. D. Nguyen. "Efficient Reproducible Floating Point Summation and BLAS."
  *ACM Transactions on Mathematical Software (TOMS)*, 2020.

- Y. Denis, P. de Oliveira Castro, E. Petit. "Verificarlo: Checking Floating Point Accuracy through
  Monte Carlo Arithmetic." *IEEE 23rd Symposium on Computer Arithmetic*, 2016. Perturbation-based
  numerical-stability analysis tooling — an orthogonal approach to CIS-2's pin-and-verify
  determinism claim (Verificarlo asks "how sensitive is this computation to rounding," CIS-2 asks
  "does this computation reproduce the same rounding everywhere").

- Java Language Specification (JLS 17), `strictfp` and JEP 306 ("Restore Always-Strict
  Floating-Point Semantics"). The closest prior *language-level* pinning precedent to CIS-2's
  approach: `strictfp` mandates IEEE-754-strict (non-extended-precision) semantics for `float`/
  `double` operations in a method or class, but does not pin reduction order, FMA contraction, or
  transcendental routing the way CIS-2's spec does — it removes one specific historical JVM
  degree of freedom (80-bit x87 extended precision leaking into `float`/`double` results), not
  the full set CIS-2 addresses.

- G. Fiedler. "Floating Point Determinism," *Gaffer On Games*, 2010.
  https://gafferongames.com/post/floating_point_determinism/ — an industry (networked-game
  lockstep simulation) discussion of exactly the same underlying problem (cross-machine fp32
  nondeterminism breaking deterministic replay/rollback), addressed informally and per-project
  rather than as a written, third-party-verifiable specification.

- `-ffp-contract=off` (GCC/Clang) and the C standard's `STDC FP_CONTRACT` pragma: the
  compiler/language-level mechanisms for disabling FMA contraction that CIS-2's no-FMA gate (§3
  gate 3, §6.3) is disassembly-verified to actually achieve, rather than merely requested via
  compiler flag or pragma.

- N. Shibata, K. Petrogalli. "SLEEF: A Portable Vectorized Library of C Standard Mathematical
  Functions." *IEEE Transactions on Parallel and Distributed Systems*, 2020. A portable,
  vectorized elementary-function library; adjacent tooling in the same design space as
  CORE-MATH/RLIBM (§2) — SLEEF targets vectorized performance with documented ULP bounds rather
  than a normatively pinned, receipt-bound coefficient table.

- D. Goldberg. "What Every Computer Scientist Should Know About Floating-Point Arithmetic." *ACM
  Computing Surveys*, 1991. Background reference for the IEEE-754 rounding, associativity, and
  cancellation properties this paper's numerics discussion (§1, §6, §7) assumes as known.

- J. B. Thompson. "Bit-identical transformer inference across ISAs, with a verifiable decode
  receipt, demonstrated on bare metal" (CIS-1). Aefinity AI Inc., 2026-08-27. This project's
  companion paper; `https://github.com/Aefinity-AI/alice-aegis/blob/main/docs/paper/paper.md`.

- CIS-2 normative specification: `docs/CIS2_SPEC_v0.2.md` (this repository, v0.2.1 with tokenizer
  pin, `Aefinity-AI/cis2-fp`).

- HuggingFaceTB/SmolLM2-135M, Qwen/Qwen2.5-0.5B, Qwen/Qwen2.5-1.5B (Hugging Face model hub) — the
  three checkpoints this paper's evidence is built on.

- `tokenizers` crate v0.23.1 (Hugging Face) — source transcribed into spec §3.1's normative
  byte-level BPE algorithm.

- Brad Conte, `crypto-algorithms` (public domain) — vendored SHA-256 implementation used in the
  C11 clean-room (`verify3/`).

## Appendix A: reference source map

`src/*.rs:line` citations throughout this paper point into the reference implementation
(`src/`), released alongside the spec and both clean-room verifiers (`verify2/`, `verify3/`)
under Apache-2.0 in the public repository (`github.com/Aefinity-AI/cis2-spec`, §9). These are
ordinary source citations, not appendix-only material, now that the reference is public.

## Appendix B: internal operator-log citations

Several claims in this paper are additionally corroborated by dated internal operator reports —
working notes written during development, not part of the public release — cited here by short
label rather than by their private filesystem path. Every fact drawn from these reports is also
stated in full, with its evidence, in this paper's own body (the citations below are provenance,
not a dependency a reader needs to resolve to check the paper's claims). Labels used inline as
"Appendix B: `<label>`":

| Label | Original report | What it corroborates |
|---|---|---|
| `E15c-verify` | 2026-08-28-E15c-verify.md | Cross-ISA CI matrix result, adversarial FMA/opt-level rebuilds, toolchain-pin gap closure (§3 gate 1/3/9, §4, §6). |
| `E15g-audit` | 2026-08-28-E15g-audit.md | Independence audit of the `verify2` Rust clean-room (verbatim-line-overlap analysis, git-history authorship check) (§4, §5, §9). |
| `E15i-result` | 2026-08-28-E15i-result.md | 20-cell compiler-invariance matrix, 5-prompt gen_toks=128 cross-ISA legs, Qwen2.5-0.5B cross-ISA + oracle legs, all on the Rust reference (§4). |
| `H1-result` | 2026-08-28-H1-result.md | Qwen2.5-1.5B scale/breadth/512-token-horizon cross-ISA CI and oracle check, reference only (§4, §8, §9); literal digests pulled independently from CI run `33214545380` are quoted directly in §4/§9 of this paper rather than relying on this report alone. |
| `H2-result` | 2026-08-28-H2-result.md | Transcendental accuracy characterization against an mpmath oracle (§4, §6, §8). |
| `H4-result` | 2026-08-28-H4-result.md | Byte-level BPE tokenizer pin (spec §3.1, v0.2.1) validated against the checkpoint's tokenizer and the pinned prompt's token ids (§3, §8). |
| `CIS2-RESULT` | 2026-08-28-CIS2-RESULT.md | Rolling task-result log; the specific v0.1 spec-writing and `verify2` v0.2 rerun entries cited in §4 (E15f, E15h-verify2 rows). |
| `SLAM-DUNK-CRITERIA` | CIS2-SLAM-DUNK-CRITERIA.md | Row-by-row publication-readiness checklist; rows 7 and 8 (tokenizer BLOCKER, phone-class aarch64 leg open) are cited in §4/§5/§8. |
