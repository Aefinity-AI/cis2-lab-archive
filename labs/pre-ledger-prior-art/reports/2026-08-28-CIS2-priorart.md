# CIS-2 Prior-Art / Novelty Memo — fp32 Transformer Cross-Language/Cross-ISA Bit-Identical Spec

Date: 2026-08-28
Scope: arXiv, ACL/[venue]/[venue]/SC/[venue]/[venue] venues, GitHub, vendor blogs. Window: back to 2023, weighted toward Jun–Aug 2026.
Method: web search only (no venue-native crawling of ACL Anthology / [venue] proceedings directly — see Limitations).

## The claim under test

A normative fp32 transformer forward-pass spec such that independent implementations — different languages (Rust, C), different ISAs (x86_64, aarch64), different compilers (gcc, clang, 20 opt/target configs) — produce a **bit-identical full-logit witness digest**, matching a PyTorch oracle within tolerance. Determinism forced by: FTZ/DAZ, round-to-nearest-even, no-FMA, scalar left-to-right reductions, pinned polynomial transcendentals with hex coefficients. Verified by a receipt any third party recomputes.

The load-bearing, unusual combination is: (1) a **written spec**, not a shared codebase; (2) **cross-language AND cross-ISA** reproduction, not just cross-run-same-binary; (3) **full logit vector** bit-identity (not just top-1 token or sampled-text match); (4) CPU-only, portable, no vendor-silicon dependency; (5) third-party-recomputable receipt as the verification artifact.

## Candidates found, and the sharp distinction

### (a) Reproducible/deterministic LLM inference (GPU-batch-invariance line)

- **Thinking Machines Lab, "Defeating Nondeterminism in LLM Inference"** (blog, Sep 2025) + `batch_invariant_ops` GitHub repo. Claim: batch-size-dependent reduction order, not FP non-associativity + scheduling, is the main cause of run-to-run nondeterminism in GPU serving; ships batch-invariant RMSNorm/matmul/attention kernels; shows bit-identical outputs across 1,000 repeated runs of Qwen3-8B **on one GPU setup**. — [thinkingmachines.ai](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/), [GitHub](https://github.com/thinking-machines-lab/batch_invariant_ops)
  **Distinction:** single hardware/software stack, run-to-run determinism at fixed batch size, GPU kernel engineering. No cross-language, no cross-ISA, no written spec for independent reimplementation, no full-logit digest, no receipt. Not prior art for the claim; it's the widely-cited motivating problem statement, useful to cite as "the problem this displaces," not as competing work.

- **LLM-42: Enabling Determinism in LLM Inference with Verified Speculation** (arXiv:2601.17768, Jan 2026; Microsoft, GitHub `microsoft/llm-42`, built on SGLang). Claim: decode-verify-rollback scheduling protocol achieves deterministic decoding under dynamic batching without rewriting GPU kernels. — [arXiv:2601.17768](https://arxiv.org/abs/2601.17768), [GitHub](https://github.com/microsoft/llm-42)
  **Distinction:** same-stack determinism (single serving engine, GPU), a scheduling trick not a numeric spec. No cross-language/cross-ISA claim, no full-logit bit-identity across independent implementations, no receipt/verification artifact for third parties.

- **MarginGate: Sparse Margin-Triggered Verification for Batch-Invariant LLM Inference** (arXiv:2605.30218). Verification scheme layered on top of batch-invariant serving to catch drift cheaply. — [arXiv:2605.30218](https://arxiv.org/pdf/2605.30218)
  **Distinction:** verification-by-sampling/margin-triggering within one serving stack; not cross-ISA/cross-language, not a spec, not full-logit digest.

### (b) Cross-platform floating-point reproducibility (CPU/ISA-portable)

- **Cankaya, "Bit-Exact AI Inference Verification Without Performance Tradeoffs"** (arXiv:2606.00279, v1 29 May 2026 / v2 5 Jun 2026). Claim: bitwise-precise recomputation of GPU inference (vLLM, HF transformers) is achievable without perf-degrading determinism flags, by caching exact silicon lookup-table outputs of NVIDIA MUFU (RSQ/EX2/RCP) transcendental units and emulating them in software; shown across multiple NVIDIA GPU variants without needing matching hardware at verify time. — [arXiv:2606.00279](https://arxiv.org/abs/2606.00279)
  **This is the closest candidate found.** It shares the goal (third-party recomputable bit-exact verification of an AI inference result) and the mechanism-of-attack (pin down the non-portable/non-standard low-level numeric primitives — for them, GPU MUFU lookup tables; for CIS-2, x87/SSE transcendentals and FMA contraction). **Sharp distinction:** Cankaya's approach is GPU-vendor-specific silicon-table emulation across NVIDIA GPU *variants* (still one ISA family, one vendor, one software stack: vLLM/HF); it is not cross-language (no Rust vs C), not cross-ISA in the CPU sense (no x86_64 vs aarch64), and is not built from a human-written normative spec independently reimplemented by separate codebases — it's emulation/caching of one reference implementation's hardware behavior, not multi-implementation convergence to a shared abstract spec. It also is not evidenced (from the abstract/available text) to check the *full logit vector*; framed as auditing accumulated rounding error as a signature, closer to an anomaly-detection framing than a bit-identical full-tensor witness digest. **This is the single citation that most needs distinguishing in the CIS-2 paper.**

- **CORE-MATH** and **RLIBM family** (RLIBM-32, RLIBM-PROG, RLIBM-MultiRound — arXiv:2104.04043, 2111.12852, 2504.07409, GitHub `rutgers-apl/rlibm-all`). Claim: generate correctly-rounded (0.5-ULP) elementary-function implementations for fp32/other formats, portable because IEEE-754 basic ops are correctly rounded on x86-64/ARM/RISC-V by standard. — [arXiv:2104.04043](https://arxiv.org/abs/2104.04043)
  **Distinction:** these are math-library-construction papers (how to build correctly-rounded transcendentals), a *tool* CIS-2's pinned-polynomial approach could cite/use, not a competing claim about transformer-forward-pass reproducibility. CIS-2 deliberately does NOT claim correct rounding of transcendentals (that would still leave cross-ISA hardware sqrt/div rounding differences in some corners) — it claims a specific *pinned polynomial with hex coefficients*, sidestepping libm entirely. No overlap in claim scope, only adjacent tooling.

- **ReproBLAS / Intel CNR (Conditional Numerical Reproducibility, MKL)** — pre-rounding/1-Reduction techniques (Ahrens/Nguyen/Demmel, UC Berkeley) and Intel's MKL CNR mode. Claim: reproducible parallel reduction sums/BLAS across thread counts and (for CNR) across some Intel CPU generations, at a real perf cost (up to ~2x slowdown reported). — [Intel oneMKL docs](https://intel.com/content/www/us/en/develop/documentation/onemkl-linux-developer-guide/top/obtaining-numerically-reproducible-results/reproducibility-conditions.html)
  **Distinction:** thread-count / core-count reproducibility of a linear-algebra kernel library, vendor-scoped (Intel-to-Intel), not cross-ISA (Intel to ARM), not cross-language, no transformer-level full-logit claim, no independent-reimplementation-from-spec framing.

- **Randompack: Cross-Platform Reproducible RNG and Distribution Sampling** (arXiv:2605.05099). Tangential — reproducible sampling, not forward-pass determinism. Not competing.

### (c) Spec-driven / clean-room replication of ML numerics

No paper or repo found that frames the deliverable as "a written normative numeric spec, independently reimplemented in ≥2 languages on ≥2 ISAs, verified to bit-identical full-output." Search for clean-room/independent-reimplementation + bit-exact neural-network framing returned only formal-verification-of-quantized-networks work (bit-vector SAT/PSPACE-hardness results, e.g. arXiv:2012.08185) and ANN-to-SNN bit-exact equivalence work (arXiv:2601.21279) — different problem (equivalence between two *architectures*, not cross-platform reproduction of one architecture). No hits.

### (d) Verifiable/attested inference receipts, ML supply-chain (SLSA/in-toto)

- General LLM supply-chain attestation literature (arXiv:2602.19021 scalability risk; arXiv:2603.02512 module repositories; Laminator hardware-attested ML property cards arXiv:2406.17548; Kettle attested builds arXiv:2605.08363) discusses attesting *that* a given model/input produced a given output (provenance/non-repudiation, often via hardware TEEs or signed metadata), not *numeric reproducibility of the computation itself* across independent codebases/hardware. — [arXiv:2602.19021](https://arxiv.org/pdf/2602.19021), [arXiv:2406.17548](https://arxiv.org/pdf/2406.17548)
  **Distinction:** these are attestation/provenance schemes (trust the attestor/hardware), whereas CIS-2's receipt is designed to be *recomputed from scratch* by a skeptical third party with no trust in any attestor — a stronger, orthogonal property. No overlap in mechanism.

- **"Reproducibility is the New Copyleft: Defining AGI-oriented Reproducible Builds"** (arXiv:2606.03019). Claim: defines "reproducible builds" for AGI systems as bit-exact reconstructability from declared inputs (code, data, weights, hyperparameters, toolchain, hardware config) — a *build/compilation* reproducibility framework (akin to Reproducible-Builds.org for software), drawing on deterministic-inference research as one input. — [arXiv:2606.03019](https://arxiv.org/abs/2606.03019)
  **Distinction:** policy/framework paper about *what counts as reproducible* at the artifact/build level; does not itself provide or evaluate a numeric spec, and explicitly includes "hardware configuration" as a *pinned* input rather than proving cross-ISA equivalence — i.e., it assumes you fix the hardware, exactly the constraint CIS-2 claims to lift. Worth a citation as related framing, not as competing technical claim.

### GitHub scan

One relevant hit: a "from-scratch Rust+CUDA inference engine, bit-exact by construction" (NVFP4/MoE/MTP, tuned against one RTX 5090 Laptop) surfaced in search snippets but could not be independently confirmed/re-fetched in this pass (title only, no stable URL captured). Even taking the snippet at face value: single language (Rust+CUDA), single GPU target, no cross-ISA/cross-language claim, no spec-plus-independent-reimplementation structure, no third-party-recomputable receipt. Flagged for a follow-up direct GitHub search pass if time allows, but on current evidence does not threaten the claim.

## Limitations of this pass

- Web search only; did not directly crawl ACL Anthology, [venue]/[venue]/[venue] proceedings pages, or run arXiv's own search API — relied on general web search surfacing arXiv/venue results, which is usually adequate for high-visibility work but can miss workshop papers or non-indexed venue PDFs.
- ~~Did not verify full text of arXiv:2606.00279 beyond abstract-level fetch.~~ **CLOSED 2026-08-28** by `2026-08-28-CIS2-priorart-fulltext.md`, which read the v2 full text (arxiv.org/html/2606.00279v2) and the author's repo. Verdict CONFIRMED DISTINCT: the paper is explicitly scoped "Only NVIDIA GPUs", is one self-verifying codebase with no normative document, and its receipt is an unbuilt proposal over a single interior tensor. Re-confirmed independently 2026-09-09. Do not re-open this as an unexamined threat.
- No direct confirmation of the unconfirmed GitHub "bit-exact by construction" Rust+CUDA repo; treat as a loose end, not a finding.

## NOVELTY VERDICT: CLEAR

No candidate found combines (i) a written normative fp32 spec, (ii) independent multi-language reimplementation, (iii) cross-ISA (x86_64/aarch64) verification, and (iv) full-logit bit-identical digest with third-party-recomputable receipt. The closest work (Cankaya, arXiv:2606.00279) is GPU-vendor-silicon-emulation-based and single-stack; the rest is single-hardware run-to-run determinism (Thinking Machines/LLM-42/MarginGate), math-library tooling (CORE-MATH/RLIBM), reduction-library reproducibility (ReproBLAS/CNR), or build/provenance attestation (SLSA/in-toto/Kettle/Laminator) — each addresses an adjacent but distinct problem. No blocker filed; this is a "clear" verdict, not "threatened."

## Three closest works

1. Cankaya, "Bit-Exact AI Inference Verification Without Performance Tradeoffs" — arXiv:2606.00279 — https://arxiv.org/abs/2606.00279
2. Thinking Machines Lab, "Defeating Nondeterminism in LLM Inference" — https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/ (+ https://github.com/thinking-machines-lab/batch_invariant_ops)
3. Gond et al., "LLM-42: Enabling Determinism in LLM Inference with Verified Speculation" — arXiv:2601.17768 — https://arxiv.org/abs/2601.17768

## Single citation most needing explicit distinguishing in the paper

**arXiv:2606.00279 (Cankaya, "Bit-Exact AI Inference Verification Without Performance Tradeoffs")** — closest in *goal* (third-party bit-exact verification of inference), must be explicitly distinguished on: GPU-silicon-emulation vs. CPU-portable pinned-arithmetic spec; single-vendor/single-stack vs. cross-language+cross-ISA; anomaly-signature framing vs. full-logit bit-identical digest; trust-the-cached-hardware-table vs. reimplement-from-a-written-spec.
