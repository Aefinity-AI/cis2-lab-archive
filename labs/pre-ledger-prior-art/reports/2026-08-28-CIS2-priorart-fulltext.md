# CIS-2 Prior-Art Row 10 — Full-Text Read: arXiv:2606.00279 (Cankaya)

Date: 2026-08-28
Method: Full-text fetch of https://arxiv.org/html/2606.00279v2 (HTML rendering, both v1/v2 available; v2 dated 5 Jun 2026), plus abstract page https://arxiv.org/abs/2606.00279 and author code repo https://github.com/NaciCankaya/hardware_rounding_error_predictor. This supersedes the abstract-only pass in state/reports/2026-08-28-CIS2-priorart.md item (b)/#1.

Context: paper won best-paper at [venue] 2026 workshop (confirms visibility/must-cite status, does not change scope).

## (1) What is bit-exact across?

**NVIDIA GPUs only, specifically GPU generations/models, via software emulation of NVIDIA's Special Function Units (SFU).** Quote: "We tested our emulator on LLM activations (Qwen3-4B) against GPU ground truth computed using CUTLASS kernel libraries and ... against cuBLAS." Tested hardware: A100, L40, L40S, H100 — all NVIDIA. Explicit stated limitation: "Only NVIDIA GPUs." No AMD/Intel GPU, no cross-vendor claim, no cross-ISA CPU claim, no cross-language claim (single Python/CUDA codebase, single author).

## (2) Written spec + independent reimplementation, or one tool verifying itself?

**One tool verifying itself.** The "spec" is a cached hardware table, not a normative document: "we cached their exact hardware outputs (e.g. a 4GB table mapping every 32-bit input for MUFU.EX2)." Source is a single-author GitHub repo (github.com/NaciCankaya/hardware_rounding_error_predictor); no second independent implementation exists or is claimed. Verification target is NVIDIA's own cuBLAS/CUTLASS — i.e., checking one vendor's silicon against a cached recording of that same vendor's silicon, not convergence of independent implementations toward a shared abstract spec.

## (3) CPU / fp32 / cross-ISA?

**Not covered as a reproduction target.** CPUs appear only as the machine that *runs the emulator/statistical sampler* — "Verifying enough samples ... requires only tens to hundreds of CPUs running continuously" — not as a platform being proven bit-identical to GPU output for its own sake, and no x86_64-vs-aarch64 cross-ISA claim appears anywhere in the text.

## (4) Determinism mechanism: emulate one vendor's hardware math, or portable IEEE arithmetic?

**Emulates one vendor's non-standard hardware math (NVIDIA MUFU LUTs), not portable IEEE-754 arithmetic.** Quote: "By exhaustively probing these instructions via inline PTX, we cached their exact hardware outputs ... ensuring bit-exact SFU emulation without needing GPU access at verification time." This is the exact opposite move from CIS-2: CIS-2 deliberately avoids depending on any one vendor's non-standard LUT/SFU behavior by using pinned polynomial transcendentals with hex coefficients that any IEEE-754-compliant scalar unit reproduces identically.

## (5) Third-party-recomputable receipt/digest?

**Proposed, not implemented.** Quote: "A cryptographic hash ... of a single tensor deep in the computational chain ... serves as a highly collision-resistant fingerprint for the entire upstream computation." This is a conceptual sketch (citing Karvonen et al. 2025 for the hashing idea), with no demonstrated receipt format, no worked third-party recompute protocol, and — per the full text — no full-logit-vector digest at all (it's a single interior tensor fingerprint, framed as an anomaly/audit signature, not a bit-identical full-output witness).

## Sharp contrast table

| Axis | Cankaya 2606.00279 (full text) | CIS-2 |
|---|---|---|
| Hardware scope | NVIDIA GPUs only (A100/L40/L40S/H100), explicit "Only NVIDIA GPUs" limitation | CPU-only, cross-ISA x86_64 + aarch64 |
| Implementation diversity | 1 codebase, 1 author, self-verified against same vendor's cuBLAS/CUTLASS | ≥2 independent codebases, 2 languages (Rust, C), converging from a written spec |
| Determinism source | Cached NVIDIA MUFU SFU lookup tables (silicon-specific, requires PTX probing) | Pinned polynomial transcendentals, hex coefficients, portable under IEEE-754 RNE/FTZ/DAZ, no-FMA |
| Spec artifact | None — a hardware table, not a normative document | Written spec, independently reimplemented |
| Output granularity | Single interior tensor fingerprint (audit signature framing) | Full logit vector, bit-identical |
| Receipt | Proposed/cited-as-idea only, not built | Actually specified and third-party recomputable |

## Newer-paper check (Jul–Aug 2026)

Searched for citations/close relatives post-dating 2606.00279. No paper found that is closer to CIS-2's claim than the original. Nearest tangential hit, arXiv:2607.26316 ("Route-Block Membership Selects Packed-AWQ Arithmetic") — different problem (quantization-format arithmetic selection mechanism study), not cross-ISA/cross-language bit-exact fp32 reproduction; not competing. arXiv:2608.02774 ("Privacy-Preserving AI Verification via Minimal Information Disclosure") is about verification-under-privacy-constraints, orthogonal (no cross-platform reproducibility claim); not competing. No new candidate displaces or narrows the prior sweep's verdict.

## VERDICT: CONFIRMED DISTINCT

Full-text read strengthens, not weakens, the abstract-level conclusion. The paper is explicitly and narrowly NVIDIA-GPU-silicon-emulation scoped ("Only NVIDIA GPUs"), single-implementation, no written spec, no cross-ISA/cross-language claim, and its "receipt" is an unimplemented proposal for a single interior-tensor hash, not a full-logit third-party-recomputable witness. Nothing in the full text threatens CIS-2's novelty (fp32, cross-ISA x86_64+aarch64, cross-language Rust+C, spec-first with independent convergence, portable pinned arithmetic, recomputable full-logit witness digest). No BLOCKER filed.

## Honesty note

Full text was retrieved and read (HTML rendering of v2, arxiv.org/html/2606.00279v2), not just the abstract — this closes the "did not verify full text" limitation flagged in the prior abstract-only report. This is now a full de-risk of row 10 for this single closest candidate, not a partial one.

## Sources

- https://arxiv.org/abs/2606.00279
- https://arxiv.org/html/2606.00279v2
- https://arxiv.org/pdf/2606.00279
- https://github.com/NaciCankaya/hardware_rounding_error_predictor
- Prior abstract-level sweep: state/reports/2026-08-28-CIS2-priorart.md
