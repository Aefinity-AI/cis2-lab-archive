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
