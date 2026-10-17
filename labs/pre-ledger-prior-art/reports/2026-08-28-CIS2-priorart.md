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

- [removed 2026-10-17: unverified prior-art characterization]

- **MarginGate: Sparse Margin-Triggered Verification for Batch-Invariant LLM Inference** (arXiv:2605.30218). Verification scheme layered on top of batch-invariant serving to catch drift cheaply. — [arXiv:2605.30218](https://arxiv.org/pdf/2605.30218)
  **Distinction:** verification-by-sampling/margin-triggering within one serving stack; not cross-ISA/cross-language, not a spec, not full-logit digest.

### (b) Cross-platform floating-point reproducibility (CPU/ISA-portable)

- [removed 2026-10-17: unverified prior-art characterization]

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
- [removed 2026-10-17: unverified prior-art characterization]
- No direct confirmation of the unconfirmed GitHub "bit-exact by construction" Rust+CUDA repo; treat as a loose end, not a finding.

## NOVELTY VERDICT: CLEAR

[removed 2026-10-17: unverified prior-art characterization]

## Three closest works

1. [removed 2026-10-17: unverified prior-art characterization]
2. Thinking Machines Lab, "Defeating Nondeterminism in LLM Inference" — https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/ (+ https://github.com/thinking-machines-lab/batch_invariant_ops)
3. [removed 2026-10-17: unverified prior-art characterization]

## Single citation most needing explicit distinguishing in the paper

[removed 2026-10-17: unverified prior-art characterization]
