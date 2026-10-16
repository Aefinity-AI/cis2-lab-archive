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
