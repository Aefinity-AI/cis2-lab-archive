# 2. Related work

**Companion paper.** CIS-1 (`https://github.com/Aefinity-AI/alice-aegis/blob/main/docs/paper/paper.md`) specifies a frozen,
all-integer transformer decode semantics for ternary/quantized models, and shows cross-ISA
bit-identity falls out of choosing an associative arithmetic (bounded fixed-point integers). CIS-2
addresses the complementary, larger case — ordinary fp32 models, where the arithmetic itself is
not associative and every degree of freedom must be pinned explicitly rather than inherited from
the type system. Wording, receipt structure, and disclosure conventions in this paper are adapted
directly from CIS-1's; §5 and §8 note the specific places CIS-2 is currently weaker (fewer
independent implementations of a standing verifier tool, no physical non-cloud aarch64 leg).

**GPU run-to-run determinism (same-stack).** Thinking Machines Lab's "Defeating Nondeterminism in LLM Inference" (blog post + `batch_invariant_ops`) argues that batch-size-dependent reduction order, not floating-point non-associativity itself, is the dominant cause of nondeterminism in GPU-served LLM inference, and ships batch-invariant RMSNorm/matmul/attention kernels that give bit-identical output across repeated runs at fixed batch size, on one hardware/software stack. [removed 2026-10-17: unverified prior-art characterization] MarginGate (arXiv:2605.30218) layers sparse margin-triggered verification on top of batch-invariant serving to catch drift cheaply. All of these solve **run-to-run determinism within one serving stack** — the same GPU, the same kernels, repeated. None claims or attempts cross-language or cross-ISA reproduction from a written specification, and none defines a full-logit-vector, third-party-recomputable receipt; a bit-identical result on one stack says nothing about what a second, independently-built implementation on different silicon would compute. CIS-2's problem is orthogonal to this line: it is CPU-only, and its determinism claim is across implementations and ISAs, not across repeated runs of one binary (though same-process repeat-run determinism is also a stated CIS-2 conformance clause, spec §12.4).

[removed 2026-10-17: unverified prior-art characterization]

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
verification, and (iv) a full-logit bit-identical, third-party-recomputable receipt. [removed 2026-10-17: unverified prior-art characterization] The remaining candidates address adjacent but
distinct problems — same-stack run-to-run determinism, correctly-rounded math-library
construction, thread-count reduction reproducibility, or provenance attestation.
