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
