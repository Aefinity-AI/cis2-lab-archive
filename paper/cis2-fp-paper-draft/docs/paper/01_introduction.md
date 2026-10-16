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
