# E14a — CIS-2 design memo: extending receipt discipline to floating-point inference

Prepared 2026-08-28 for Aefinity AI's research loop. Scope: can CIS-1's
bit-identical, cross-ISA, per-step-receipted decode discipline
(`~/projects/alice-aegis/docs/CIS-1_SPEC_v1.0.md`, ledger rows A31–A40 in
`~/projects/alice-aegis/program/RESEARCH_LEDGER.md`) be extended from
ternary/integer-only inference to floating-point (bf16 weights, fp32
compute) inference, with the same cross-ISA bit-identity property?

This memo does not report any measurement of Aefinity's own work. Every
number attributed to prior art is cited; anything not independently
verified in this sweep is labeled REPORTED, not VERIFIED.

**Context recap (for readers who have not read CIS-1 v1.0.3):** CIS-1's
axiom is "every reduction in the decode path is a sum of *integers* whose
worst case provably fits its accumulator" — integer addition is associative,
so any implementation may reorder/vectorize/parallelize freely and still be
bit-identical (§1). Its "receipt"/"witness" is a SHA-256-chained commitment
over every decode step's full logit vector plus the generated token ids and
artifact hashes, independently re-derivable by a third, `no_std`,
zero-dependency verifier crate (`cis-verify`, ledger A37/A38) on a different
ISA (A32, A39) and inside a no-OS unikernel (A40). CIS-2's question is
whether that same discipline — a normative op spec + a bit-identical
digest + an independent verifier — survives when the arithmetic is IEEE-754
floating point rather than integer, because floating-point addition is
**not** associative and CIS-1's central trick (§1's axiom) has no direct
floating-point analogue.

---

## 1. Prior art survey

### 1.1 Thinking Machines, "Defeating Nondeterminism in LLM Inference" (Sept 2025)

The canonical recent reference. Its claim: LLM inference servers are
nondeterministic from a user's point of view not primarily because of
concurrent atomic-add races, but because GPU reduction *kernels lack batch
invariance* — a kernel's numerical result depends on the batch size it is
called with, and batch size varies nondeterministically with concurrent
server load, so the same prompt on the same weights on the same hardware
can decode differently run to run ([Thinking Machines Lab blog](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/), Sept 2025;
summary via [Simon Willison](https://simonwillison.net/2025/Sep/11/defeating-nondeterminism/)).
The fix: batch-invariant kernels for RMSNorm (fixed data-parallel strategy,
no split-reductions), matmul (fixed tile size / tensor-core instruction
selection independent of batch shape), and attention (fixed split-size
strategy) — released as PyTorch code
(`thinking-machines-lab/batch_invariant_ops`) demonstrated on Qwen3-8B under
vLLM, reportedly producing bit-identical output across 1,000 repeated runs
of the *same* server, same hardware ([Thinking Machines Lab](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/); overhead
figures reported by third-party summaries at roughly 2x slowdown in the
initial release, ~61.5% throughput cost, reduced to ~34.35% after SGLang
integrated the kernels with CUDA graphs — [Medium/Siddhant Gupta](https://medium.com/@siddhantg314/defeating-nondeterminism-in-llm-inference-in-practice-38a7dd1e4112),
[LMSYS/SGLang blog](https://www.lmsys.org/blog/2025-09-22-sglang-deterministic/); overhead figures are REPORTED by
secondary sources, not independently reproduced by this sweep).

**What it does NOT give:** batch invariance is explicitly a same-hardware,
same-software-stack guarantee — "identical results regardless of the load
the server is serving concurrently," not identical results across GPU
generations, across CPU vs. GPU, or across x86 vs. aarch64. It targets GPU
tensor-core reduction-order variance induced by *scheduling*, not the
ISA-level and compiler-level fp sources CIS-2 must pin (§2 below). It is
also floating-point-specific engineering discipline (fixed kernel shapes),
not a normative spec with an independent verifier or a cryptographic
receipt — there is no third-party re-derivation artifact analogous to
`cis-verify`.

### 1.2 Follow-ups to batch invariance

- LMSYS/SGLang, "Towards Deterministic Inference in SGLang and Reproducible
  RL Training," Sept 2025 — integrates Thinking Machines' batch-invariant
  kernels with CUDA graphs, reporting reduced overhead (~34.35% vs. the
  original ~61.5%) and connects determinism to reproducible RL training
  stability. ([lmsys.org](https://www.lmsys.org/blog/2025-09-22-sglang-deterministic/))
- "MarginGate: Sparse Margin-Triggered Verification for Batch-Invariant LLM
  Inference," arXiv:2605.30218 — builds a verification scheme *on top of*
  batch invariance (checking only near-margin decisions); presupposes
  batch-invariant kernels already exist, does not itself solve cross-ISA
  identity. UNVERIFIED beyond abstract by this sweep. ([arXiv](https://arxiv.org/pdf/2605.30218))
- [removed 2026-10-17: unverified prior-art characterization]
- [removed 2026-10-17: unverified prior-art characterization]
  cross-ISA bit-identity spec. UNVERIFIED beyond abstract. ([arXiv](https://arxiv.org/pdf/2606.21023))
- "DiFR: Inference Verification Despite Nondeterminism," arXiv:2511.20621 —
  explicitly targets verifying inference *without* assuming determinism
  (statistical/tolerance-based verification), the opposite design point
  from CIS-1/CIS-2's bit-exact receipt; useful as the "give up on
  bit-exactness, verify approximately" alternative to weigh against §3.
  UNVERIFIED beyond abstract. ([arXiv](https://arxiv.org/pdf/2511.20621))
- "EigenAI: Deterministic Inference, Verifiable Results," arXiv:2602.00182
  — a more recent (2026) determinism + verifiability proposal; title
  suggests direct overlap with CIS-2's goals. Not fetched in full by this
  sweep — **flag for a follow-up read before CIS-2 §1 is finalized**, since
  it may already occupy part of this design space. UNVERIFIED. ([arXiv](https://arxiv.org/html/2602.00182))
- "Toward Reproducible Cross-Backend Compatibility for Deep Learning: A
  Configuration-First Framework with Three-Tier Verification,"
  arXiv:2509.06977 — cross-backend (not necessarily cross-ISA) DL
  reproducibility framework; general-DL scope, not LLM-decode-specific.
  UNVERIFIED beyond abstract. ([arXiv](https://arxiv.org/pdf/2509.06977))

### 1.3 zkML cost figures (EZKL and comparators)

zkML proves *that* an inference was computed correctly without revealing
weights/inputs, using zero-knowledge proof systems over arithmetized neural
nets — a different trust model than CIS-1/2 (cryptographic proof vs.
bit-exact independent re-execution), useful as the cost baseline for "what
does a strong integrity guarantee cost if you don't get to assume
determinism."

- EZKL translates ONNX models into arithmetic circuits (zk-SNARK backend).
  Proving time reportedly scales super-linearly, roughly O(k·N log N) in
  parameter count N with a large constant k (often cited 10³–10⁴); proving
  times for transformer/LLM-scale models are reported in the
  minutes-to-hours range per inference. ([emergentmind.com/EZKL summary](https://www.emergentmind.com/topics/ezkl))
- zkLLM (LLaMA-2-13B): REPORTED 986 s for commitment generation and 803 s
  for proving *per forward pass*; extrapolated to a 2000-token generation,
  roughly 23 days commitment + 18 days proving. This is the clearest
  concrete cost figure found in this sweep and is dramatically more
  expensive than any deterministic-recompute approach (CIS-1's or a fp
  analogue), by many orders of magnitude. UNVERIFIED beyond
  secondary-source abstract; primary zkLLM paper not fetched by this sweep.
  ([emergentmind.com/zkLLM summary](https://www.emergentmind.com/topics/zkllm))
- NANOZK reportedly achieves a 228x speedup over EZKL on an MLP-512
  configuration (33 s vs. >75 min) — evidence the field is improving
  quickly, but still far from CIS-1/CIS-2's target (verifier work
  comparable to, or cheaper than, one forward pass; `cis-verify`'s
  measured convenience figure was ~1.4 s for a full receipt-plus-selftest
  run on a small model, ledger A37 — not a benchmark claim, cited here only
  to show the order of magnitude gap vs. zkML). ([arXiv:2603.18046](https://arxiv.org/pdf/2603.18046))
- Survey: "A Survey of Zero-Knowledge Proof Based Verifiable Machine
  Learning," arXiv:2502.18535 — broad literature map of the zkML space.
  UNVERIFIED beyond abstract. ([arXiv](https://arxiv.org/pdf/2502.18535))

**What zkML does NOT give:** cross-ISA bit-identical *reproduction* of the
original computation — it proves a computation was done correctly relative
to committed inputs/circuit, typically without the verifier re-running
anything resembling the original floating-point forward pass, and current
LLM-scale costs (days per generation, per zkLLM above) make it unusable as
an every-decode-step receipt at CIS-1's granularity. It is a different
answer to a related but distinct question ("was this computed correctly"
vs. "can any independent party get the identical bits back").

### 1.4 NVIDIA confidential computing / TEE attestation for inference

- NVIDIA Hopper-generation GPUs (H100/H200) support a confidential-computing
  mode: command buffers, kernels, and PCIe CPU↔GPU transfers are encrypted
  and authenticated via a bounce buffer, with attestation giving a
  cryptographic assertion that the TEE is genuine and configured as
  expected; requires a host CPU TEE (Intel TDX or similar) for full
  attestation. Overhead is reported as generally under 5% for typical LLM
  queries, dominated by data-transfer cost rather than in-GPU compute.
  ([arXiv:2509.18886, "Confidential LLM Inference: Performance and Cost
  Across CPU and GPU TEEs"](https://arxiv.org/pdf/2509.18886); [arXiv:2505.16501, "Performance of Confidential
  Computing GPUs"](https://arxiv.org/pdf/2505.16501); [Intel Community blog on Intel TDX + NVIDIA H100
  attestation](https://community.intel.com/t5/Blogs/Products-and-Solutions/Security/Seamless-Attestation-of-Intel-TDX-and-NVIDIA-H100-TEEs-with/post/1525587); overhead figure REPORTED by secondary summary, not
  independently verified by this sweep.)

**What TEE attestation does NOT give:** it attests *that a genuine,
correctly-configured GPU ran the workload confidentially* — a hardware
root of trust about *what ran*, not a claim that the numeric result is
reproducible bit-for-bit on different hardware. It is complementary to,
not competing with, a bit-identity spec: a TEE could attest that CIS-2's
verifier ran, but does not itself solve floating-point cross-ISA
nondeterminism. It also requires trusting the silicon vendor's attestation
root, which CIS-1's "kilobyte-TCB, no_std, re-derivable by a third
implementation" design explicitly tries to avoid depending on (spec §10:
"Machine attestation (TPM/measured boot): separate layer").

### 1.5 Cross-platform deterministic floating-point reduction (the closest technical relatives)

- **ReproBLAS** (UC Berkeley/BeBOP): computes a reproducible sum of
  floating-point numbers independent of summation order, by splitting
  numbers into slices ("bins") along predefined exponent-range boundaries
  and summing each bin exactly; the `ReproRed` reduction algorithm gives
  bit-identical results under varying core counts by fixing an order
  independent of the communication/parallelization pattern, and applies to
  any associative reduction. ([GitHub: willow-ahrens/ReproBLAS](https://github.com/willow-ahrens/ReproBLAS); [SC13
  workshop paper](https://sc13.supercomputing.org/sites/default/files/WorkshopsArchive/pdfs/wp141s1.pdf); Demmel & Nguyen, "Fast Reproducible Floating-Point
  Summation," and "Algorithms for Efficient Reproducible Floating Point
  Summation," ACM TOMS 2020 — [ACM DOI](https://dl.acm.org/doi/10.1145/3389360), [UC Berkeley TR](https://www2.eecs.berkeley.edu/Pubs/TechRpts/2016/EECS-2016-121.html))
  Reported cost: summing n words with a 6-word reproducible accumulator
  needs roughly 9n floating-point ops (arithmetic/compare/abs) plus ~3n
  bitwise ops — i.e., a documented, bounded constant-factor overhead per
  reduction, not a super-linear blowup. This is the most directly relevant
  prior art for CIS-2 §3's reduction-order question: it proves
  order-independent-yet-bit-reproducible floating-point summation is
  achievable at bounded cost, using a mechanism (fixed exponent bins) quite
  different from CIS-1's (exact integers).
- **ExBLAS**: an alternative reproducible-BLAS approach combining "long
  accumulators" (very wide fixed-point accumulators covering the full
  exponent range) with floating-point expansions and error-free
  transformations, for reproducible and accurate BLAS-level operations.
  ([ResearchGate summary of ExBLAS](https://www.researchgate.net/publication/288828110_ExBLAS_Reproducible_and_Accurate_BLAS_Library))
  Notably, ExBLAS's "long accumulator" idea is structurally close to what
  CIS-2 will likely need for RMSNorm/attention reductions if it wants
  exactness rather than merely order-independence — worth reading in full
  before drafting CIS-2 §5's reduction procedure.
- **What ReproBLAS/ExBLAS give:** order-independent, bit-reproducible
  floating-point *reduction* (sums/dot products), which is necessary but
  not sufficient for CIS-2 — LLM forward passes also need RoPE
  (sin/cos), softmax/SiLU (exp), and rsqrt (RMSNorm) pinned (§2), which
  reproducible-summation work does not address; and neither project
  targets a *cryptographic per-step receipt* or an *independent
  from-spec verifier* the way CIS-1 does.
- **CORE-MATH** (Inria): a project demonstrating feasibility of a fully
  correctly-rounded elementary-function library (exp, log, sin, cos, tan,
  atan, pow, etc. in binary32/binary64), where "correctly rounded" means
  the result equals the infinite-precision result rounded once to the
  target format — proven by exhaustive search for binary32 univariate
  functions, and checked against known hard cases for larger/bivariate
  ones. Because correct rounding is a total function of the *input bits
  and target format only*, two correctly-rounded implementations must
  agree bit-for-bit on any input, regardless of ISA — this is exactly the
  property CIS-2 needs for exp()/sin()/cos()/rsqrt() if it chooses the
  correctly-rounded route in §3. IEEE 754 currently only *recommends*
  (does not mandate) correctly-rounded elementary functions, though a 2029
  revision working group is reportedly discussing mandating it.
  ([core-math.gitlabpages.inria.fr](https://core-math.gitlabpages.inria.fr/); [FAQ](https://core-math.gitlabpages.inria.fr/faq.html); [FPBench talk
  slides, Zimmermann/Sibidanov](https://members.loria.fr/PZimmermann/talks/core-math-fpbench.pdf))
- **RLIBM** (Rutgers, Nagarakatte et al.): a research program building
  correctly-rounded elementary functions for *multiple* representations
  (float32, bfloat16, TensorFloat-32, posits) and multiple rounding modes
  from a single generated polynomial approximation, explicitly motivated
  by portability/reproducibility of applications that use these functions.
  RLIBM's bfloat16/TF32 coverage is directly relevant to CIS-2 since the
  target arithmetic is bf16-widened-to-fp32. ([RLibm project page](https://people.cs.rutgers.edu/~sn349/rlibm/); RLIBM-32,
  arXiv:2104.04043; RLIBM-PROG, [arXiv:2111.12852](https://arxiv.org/pdf/2111.12852); RLibm-MultiRound,
  [arXiv:2504.07409](https://arxiv.org/pdf/2504.07409))
- **CR-LIBM** (predecessor, correctly-rounded elementary function library,
  earlier academic project) — cited by RLIBM/CORE-MATH as prior work;
  UNVERIFIED beyond the ResearchGate abstract found by this sweep.
  ([ResearchGate](https://www.researchgate.net/publication/252186392_CR-LIBM_A_correctly_rounded_elementary_function_library))
- **What CORE-MATH/RLIBM give:** deterministic, cross-implementation-
  agreeing transcendental functions *if* both sides use a correctly-rounded
  implementation (or the identical pinned LUT+polynomial, CIS-1-style).
  They do NOT give a full inference-pipeline spec, a reduction-order
  discipline, or a receipt/verifier format — they solve exactly one of
  CIS-2's several fp-nondeterminism sources (transcendentals; §2 below),
  and (per CIS-1's own §3 discipline of "reference implementations are
  definitive, optimized kernels conform by matching bits") a
  correctly-rounded exp/sin/cos, if adopted, would need to be the
  *reference*, not merely "a good approximation."
- **"Deterministic ONNX" / general reproducible-ML surveys.** No dedicated
  "deterministic ONNX Runtime" project was found; ONNX Runtime itself does
  not provide bit-exactness guarantees across execution providers or
  hardware (auto-selected convolution algorithms — GEMM vs. Winograd vs.
  FFT — are explicitly non-deterministic; [microsoft/onnxruntime GitHub](https://github.com/microsoft/onnxruntime)).
  General surveys of the problem: "Reproducibility is the New Copyleft:
  Defining AGI-oriented Reproducible Builds," arXiv:2606.03019 (frames
  reproducible ML/AI builds as a policy/tooling problem, broader than
  inference-only determinism, UNVERIFIED beyond abstract, [arXiv](https://arxiv.org/pdf/2606.03019)).
  One search summary claimed "portable C engines using software-emulated
  floating-point can produce bit-equivalent predictions across platforms"
  and that "approaches that force deterministic floating-point reduction
  orders sacrifice throughput and fundamentally fail to generalize across
  disparate GPU vendors" — this is a plausible-sounding secondary-source
  synthesis, not traced to a single primary source by this sweep; treat as
  UNVERIFIED and re-derive independently before citing in CIS-2 itself.

### 1.6 IEEE 754-2019 and reproducibility

IEEE 754-2019 §11 explicitly addresses reproducibility: "for operations
specified in the normative part of the standard, numerical results and
exceptions are uniquely determined by the values of the input data,
sequence of operations, and destination formats, all under user control" —
i.e., **the standard itself only guarantees bit-identity given a fixed
sequence of operations**; it does not make floating-point addition
associative, and it explicitly states that reproducible results require
cooperation from language standards, compilers, and programmers, not just
hardware conformance. IEEE 754-2019 added recommended (not mandatory)
"augmented" addition/subtraction/multiplication operations to support
building higher precision and reproducible reductions in software, and
recommends (but again does not mandate) that language standards define
reduction operations per format with implementations free to associate in
any order or evaluate in a wider format unless a reproducible variant is
requested. ([IEEE 754-2019 standard page](https://standards.ieee.org/standard/754-2019.html); background paper, [IEEE Computer
background PDF](https://grouper.ieee.org/groups/msc/ANSI_IEEE-Std-754-2019/background/ieee-computer.pdf))

**What IEEE 754 gives CIS-2:** confirmation that *within a single, fixed
sequence of correctly-rounded IEEE-754 operations*, results are bit-exact
by standard — which is exactly the design point CIS-2 needs to exploit
(§3): pin the sequence, and the standard's own conformance requirement
does the rest for every basic op (+, −, ×, /, sqrt, fma — all mandatory
correctly-rounded ops under 754). It does NOT extend that guarantee to
transcendentals (recommended, not mandatory, to be correctly rounded — see
§1.5/CORE-MATH) or to compiler-level reassociation (fp-contract, fast-math
— see §2), both of which sit outside the standard's normative core and
must be pinned by CIS-2 itself.

---

## 2. Sources of fp nondeterminism in a Llama-architecture forward pass

Target architecture assumed: standard pre-norm Llama-style decoder (RMSNorm
→ RoPE-rotated multi-head/grouped-query attention with causal softmax →
residual add → RMSNorm → SwiGLU MLP → residual add, repeated per layer,
final RMSNorm + LM head), matching SmolLM2-135M (§4). Compute assumed fp32;
weights bf16, widened to fp32 on load or per-op.

| Op | fp nondeterminism source | Differs x86 vs. aarch64, same source, same compiler settings? |
|---|---|---|
| **Matmul / dot product (attention proj, MLP, LM head)** | **Reduction order**: naive loop-order summation is associative in exact math but not in fp; different loop tiling/blocking/vector width changes rounding at every partial sum. **SIMD width**: AVX2 (8-wide f32) vs. AVX-512 (16-wide) vs. NEON (4-wide f32) partitions the reduction into different-sized chunks by default with naive/auto-vectorized code, changing rounding, even for hand-identical *scalar* source if the compiler auto-vectorizes differently per target. **FMA contraction**: see below. | **Yes, if left unconstrained.** Scalar, sequential-order code compiled by the same compiler with FMA disabled and no auto-vectorization reassociation should, in principle, be reduction-order-identical across ISAs — this is the CIS-2 lever (§3): eliminate SIMD-width and blocking as sources by mandating a fixed, e.g. strictly left-to-right, scalar accumulation order in the *reference*, and requiring optimized kernels to match that reference bit-for-bit (CIS-1's own §6 discipline, reused). |
| **RMSNorm (rsqrt)** | `1/sqrt(mean(x²)+eps)` — a transcendental (rsqrt). Hardware fast-rsqrt approximations (x86 `rsqrtps`/`vrsqrt14ps`, ARM `frsqrte`) are *not* correctly rounded and differ in their approximation polynomial/Newton-refinement steps between vendors and even between microarchitecture generations of the same vendor. A correctly-rounded `1/sqrt` via `sqrtf` (mandatory-correctly-rounded under IEEE 754) followed by mandatory-correctly-rounded division is portable; a "fast" hardware reciprocal-sqrt instruction is not. | **Yes for fast/approximate rsqrt instructions; no for `1.0f / sqrtf(x)` via the mandatory correctly-rounded ops**, provided the compiler is not permitted to substitute the fast approximate instruction (this substitution is itself a real risk under `-ffast-math`/`-Ofast`, and is exactly what a normative "forbid fast-math" rule (§3) must rule out explicitly). |
| **RoPE (sin/cos)** | `sin`/`cos` are recommended-but-not-mandatory-correctly-rounded under IEEE 754 (§1.6); libm implementations (glibc, musl, macOS libm, MSVC, LLVM's compiler-rt) differ by up to 1 ULP or more on hard cases, and vectorized/table-based sincos implementations differ further. | **Yes**, unless CIS-2 pins either (a) a correctly-rounded sin/cos (CORE-MATH/RLIBM, §1.5/§3) as the *normative* reference, or (b) a CIS-1-style fixed LUT+polynomial with a digest over the table (spec §5.7/§5.9's `exp` LUT and RoPE table precedent, already proven at the integer level). |
| **Softmax (exp, max-subtract, reduction)** | Same `exp` transcendental issue as RoPE, compounded with a reduction (denominator sum) that inherits the matmul reduction-order issue above; the max-subtraction step for numerical stability is itself exact (max is order-independent) but interacts with which lane computed the max first in a parallel reduction (tie-breaking on equal maxima across lanes can differ). | **Yes**, same two causes (transcendental rounding + reduction order) apply; max-subtraction itself is safe if implemented as a strict sequential or fixed-tree max, matching the reduction-order fix already required for matmul. |
| **SiLU / SwiGLU (exp)** | `silu(x) = x·sigmoid(x) = x / (1+exp(-x))` — same `exp` issue as above. | Yes, same fix (pinned exp) applies. |
| **Residual adds** | Simple elementwise fp add — no reduction, no transcendental. Genuinely just IEEE-754 addition, which is a mandatory correctly-rounded operation and therefore bit-identical across any conformant fp32 hardware for the *same two operands in the same order* — i.e., not a real nondeterminism source **provided FMA contraction with a neighboring multiply is forbidden** (see FMA row) and both ISAs support IEEE-754 binary32 addition per spec (they do). | **No**, if FMA contraction is forbidden and operand order is fixed (residual order is inherently fixed — it's `x + f(x)`, not a reduction). |
| **bf16 → fp32 conversion** | bf16 is fp32's top 16 bits (1 sign + 8 exponent + 7 mantissa) with the low 16 mantissa bits truncated at *training/storage* time; widening bf16 → fp32 by zero-padding the low 16 mantissa bits is an *exact*, lossless, deterministic bit operation (not a rounding operation) — there is no rounding choice to make. | **No** — this is an exact bit-pattern operation (left-shift by 16 into the fp32 mantissa field), identical on any conformant integer/bit-manipulation hardware, independent of ISA. The only nondeterminism risk is a buggy or non-exact widening implementation (e.g., accidentally routing through a "convert-and-round" library path instead of an exact bit-shift) — CIS-2's normative contract should specify the exact bit operation, not "convert bf16 to fp32" as prose. |
| **Denormals / FTZ / DAZ** | Whether subnormal (denormal) results are flushed to zero (FTZ) or computed with full IEEE-754 gradual underflow differs by *default hardware behavior*: ARM NEON always operates in flush-to-zero mode by hardware default (denormal outputs become signed zero); x86 SSE/AVX does **not** flush to zero by default — gradual underflow (full denormal support) is the IEEE-754-conformant default, and FTZ/DAZ require explicitly setting MXCSR bits (e.g. via `_MM_SET_FLUSH_ZERO_MODE`). This is a genuine, silent, hardware-level default divergence between the two ISAs. | **Yes, potentially — this is one of the more dangerous cross-ISA divergences for CIS-2** and, unlike the reduction-order issues above, is not something the reference implementation's loop structure can fix; it must be pinned as an explicit *hardware mode* requirement (§3): either force FTZ=on/DAZ=on on x86 to match NEON's hardware default, or verify no denormal ever arises at the numeric ranges the target model produces (the latter is closer to CIS-1's "headroom is proof, not hope" philosophy — bound the ranges and panic loudly on violation, rather than trust it never happens). Sources: [ARM NEON flush-to-zero mode docs](https://developer.arm.com/documentation/den0018/latest/NEON-Instruction-Set-Architecture/Flush-to-zero-mode); [Intel FTZ/DAZ compiler option docs](https://www.cis.uoguelph.ca/~wgardner/intel_docs/compilers/compiler_c/main_cls/copts/common_options/option_ftz.htm); general discussion at [gist: Enable flushing denormals to zero in Rust](https://gist.github.com/GabrielMajeri/545042ee4f956d5b2141105eb6a505a9). |
| **Compiler flags (`-ffast-math`, `fp-contract`)** | `-ffast-math`/`-Ofast` license the compiler to reassociate fp expressions, assume no NaN/Inf, substitute approximate reciprocal/rsqrt hardware instructions, and contract multiply+add into FMA — any of which breaks bit-identity across codegen backends/ISAs. `fp-contract` (C standard's `FP_CONTRACT` pragma / Clang's `-ffp-contract=`) specifically governs whether `a*b+c` is fused into one rounding step (FMA) or evaluated as two separately-rounded ops; Clang 14+ defaults `-ffp-contract=on`, meaning contraction happens **within a single expression/statement** by default in C/C++ (not across statements) unless explicitly disabled. | Yes for both — `-ffast-math` is a strict superset of danger and must be an absolute prohibition; `fp-contract`'s *default-on* behavior in C/C++ toolchains is a real, easy-to-miss source of cross-build divergence, since whether the compiler *has* an FMA instruction to contract into differs by target (x86 needs AVX2+FMA3 feature flags; aarch64 NEON/ASIMD has FMA as a baseline ISA feature on essentially all real aarch64 cores) — so identical C source with default fp-contract could legally fuse on aarch64 and not on x86 without `-march` flags, producing different rounding. **Rust specifically is safer here by construction**: Rust has no `-ffast-math`-equivalent flag (rejected/not implemented specifically because it "can change the bitwise result of floating point math compared to the reference"), and **rustc/LLVM does not auto-contract `a*b+c` into an FMA instruction** — contraction only happens if the programmer explicitly calls `f32::mul_add`/`f64::mul_add`, which lowers to LLVM's `llvm.fma` intrinsic; ordinary `a*b+c` source lowers to separate `fmul`+`fadd` IR ops and stays separately rounded regardless of target FMA availability. (Sources: [Rust `f32::mul_add` docs](https://doc.rust-lang.org/1.61.0/std/primitive.f32.html); [rustc `intrinsics::fmuladdf32` docs](https://doc.rust-lang.org/nightly/core/intrinsics/fn.fmuladdf32.html), noting the *intrinsic itself* — not ordinary `*`/`+` — is the one construct with target-dependent fuse-or-not behavior, and that even the intrinsic is unspecified/context-dependent, which is exactly why CIS-2 should not use it in the reference; general LLVM fp-contract background: [LLVM discourse, "FP contraction (FMA) on by default"](https://discourse.llvm.org/t/fp-contraction-fma-on-by-default/64975); [llvm-dev RFC thread on `-fp-contract=off`](https://groups.google.com/g/llvm-dev/c/nBiCD5KvYW0/m/PWcNUdZ4DAAJ).) **Precise answer to the memo's question:** with Rust, no `-ffast-math` flag, and source that never calls `.mul_add()`, LLVM does not introduce FMA contraction on its own — the `fmul`+`fadd` pair is emitted and separately rounded on every target, x86 and aarch64 alike. The risk surface is narrow and controllable (audit for `.mul_add()` calls; there is no ambient flag to accidentally leave on). |

**Summary of the controllable vs. hazardous split:** residual adds and
bf16→fp32 widening are non-issues (exact ops, no rounding choice) — no
normative pinning needed beyond stating them precisely. Matmul/softmax
reduction order and Rust's FMA behavior are controllable by source-level
discipline (fixed loop order, avoid `.mul_add()`) with no need to fight the
compiler. RMSNorm/RoPE/softmax/SiLU transcendentals are the hard problem —
they require either adopting a correctly-rounded math library as the
normative reference (§1.5/§3) or a CIS-1-style pinned LUT (§3). Denormal
handling (FTZ/DAZ) is the most likely to be silently wrong, because it is a
*hardware default divergence*, not a code-visible choice — this deserves an
explicit CIS-2 test (feed adversarially small activations and diff x86 vs.
aarch64 output) before any other work, since a spec section can state a
policy but only a targeted experiment can confirm neither platform's
hardware default silently violates it.

---

## 3. Proposed normative fp32 contract — CIS-2 draft §5

This section proposes text and tradeoffs for CIS-2's normative operations
section, modeled on CIS-1 §5's structure (reference implementation is
definitive; optimized kernels conform by matching bits, not loops).

### 3.1 Reduction order

**Proposal: fixed pairwise-tree reduction, not strict sequential.**

Two candidate normative reduction orders for any sum of N floating-point
values (dot products, RMSNorm sum-of-squares, softmax denominator):

- **(a) Strict sequential (left-to-right) accumulation.** Simplest to
  specify and to match with a scalar reference loop. Downside: poor
  cache/ILP behavior if an optimized kernel must match it exactly bit-for-
  bit (no reassociation allowed at all means an optimized kernel is nearly
  as slow as the reference for large N, defeating much of the point of an
  optimized kernel — though CIS-1's own experience (ledger A26) shows
  scalar-vs-vector cost differences are microarchitectural, not doctrinal,
  so this may be an acceptable cost, not a blocker).
  - Verifier-friendliness: **highest** — a reference implementation is one
    `for` loop; a from-spec-text reimplementation (CIS-1's A31 clean-room
    precedent) is trivial to get bit-exact on the first attempt.
- **(b) Fixed pairwise-tree (recursive halving) reduction, à la ReproBLAS's
  binned approach but simpler (no binning, just a canonical tree shape
  independent of N's factorization, e.g. via a fixed padding-to-power-of-2
  rule).** Downside: more complex to specify precisely (padding rule for
  non-power-of-2 N must be normative, or two conforming implementations
  disagree on tree shape); more complex for a from-spec clean-room
  reimplementer to get exactly right on the first attempt (a plausible
  regression from CIS-1's A31 result).
  - Upside: pairwise trees are closer to what real SIMD/blocked kernels
    naturally compute, so an *optimized* kernel is more likely to be
    expressible as "the same tree, just parallelized" rather than "an
    entirely different, slower, sequential shadow path that must be run to
    match the reference" — this matters because CIS-1's own kernels
    (`cis_avx2`/`cis_neon`) achieve speed by computing the *actual*
    parallel operation, not by degrading to scalar; a floating-point
    kernel that has to abandon its natural SIMD reduction shape to match a
    strictly sequential reference loses more relative performance than an
    integer kernel does (integer reduction is exact either way; fp
    reduction shape changes the *answer*, not just the speed).

**Recommendation for the draft:** start with **(a) strict sequential** for
the reference implementation and the conformance digest, exactly as
CIS-1's philosophy prescribes ("the reference is definitive... optimized
kernels conform by matching its bits, not by copying its loops" — CIS-1
§5) — but flag explicitly, as an open question for CIS-2 v0.2, whether a
fixed-tree reference is worth the added specification complexity once
E14b/c produce a first working scalar Rust implementation and its actual
wall-clock cost is measured (no number is asserted here; this is a
decision to make with data, not before it). This mirrors how CIS-1 itself
deferred witness-format freezing (§10) until a working prototype existed.

### 3.2 Forbid FMA contraction

**Proposal: normative — no FMA anywhere in the reference or in conforming
optimized kernels**, for the reasons in §2's compiler-flags row: FMA
changes the rounding of `a*b+c` from two roundings to one, and whether an
FMA instruction is even *available* differs by target unless explicit ISA
feature flags are set, making "does this expression fuse" a target-
dependent question if left to the compiler's default. Concretely for the
Rust reference implementation: never call `f32::mul_add`/`f64::mul_add`;
write `a*b + c` in ordinary Rust, which LLVM does not auto-contract absent
an explicit fast-math flag Rust does not offer (§2, cited). This should be
enforced mechanically (a lint or `grep` gate in CI for `.mul_add(` in the
CIS-2 reference crate, analogous to CIS-1's CI digest gates), not just
stated in prose — a normative rule with no gate is the exact failure mode
CIS-1's v1.0.1–v1.0.3 errata history (ledger A31/A35) repeatedly found:
under-specified or unenforced constraints are where clean-room
reimplementations diverge.

Cost: essentially free on Rust/LLVM (§2) since it is already the default
behavior for ordinary arithmetic; the discipline is "don't call
`.mul_add()`," not "fight the compiler."

### 3.3 Transcendental functions: correctly-rounded vs. pinned LUT+polynomial

Two options, both viable, with different tradeoffs — this is the section
most worth prototyping both ways in E14b before locking the spec:

**(a) Correctly-rounded, via CORE-MATH or RLIBM.** Adopt a
correctly-rounded `exp`, `sin`, `cos`, `sqrt`(for rsqrt) as the normative
reference for §5's RoPE/softmax/SiLU/RMSNorm ops. Because "correctly
rounded" is a total function of input bits and target format (§1.5),
**any** correctly-rounded implementation — CORE-MATH's, RLIBM's, or a
from-spec reimplementation of either's published algorithm — must agree
bit-for-bit with any other correctly-rounded implementation, by
definition, with no table digest or pinning mechanism needed at all. This
is a meaningfully stronger and cleaner property than CIS-1's LUT approach:
CIS-1 needs a table digest because its pinned LUT is *one arbitrary choice
among many* that happens to be normative by fiat; a correctly-rounded
function's bit pattern is *mathematically forced*, so two independent
correctly-rounded implementations converge without coordination.
Cost: correctly-rounded elementary functions are typically slower than
libm's "faithfully rounded" (≤1 ULP but not guaranteed exact-to-nearest)
approximations — CORE-MATH's own stated goal is competitive speed with
current libm, "as efficient or even faster," but this is a project goal,
not yet a universally measured result across every function/platform in
this sweep, and should be benchmarked directly for the specific functions
CIS-2 needs (`exp`, `sin`, `cos`, `sqrt`/rsqrt) rather than assumed.
Verifier-friendliness: **potentially highest of all options** — no table
digest, no LUT provenance to audit, "did you use a correctly-rounded
implementation" is a checkable/testable property (exhaustive test for
binary32, per CORE-MATH's own methodology) independent of the codebase.

**(b) CIS-1-style pinned LUT + polynomial with a table digest.** Directly
reuse CIS-1's precedent (spec §5.7's exp LUT, §5.9's RoPE tables, both
already digest-pinned integer artifacts — `exp LUT 0x66C2A0EEB8C2DC43`,
`RoPE 0xD8345EBF01E990FA`, ledger A37) but re-derive analogous fp32 tables:
a fixed polynomial approximation (e.g., minimax or Remez-optimized,
pinned coefficients as exact fp32 bit patterns) plus a fixed
argument-reduction procedure (range-reduce to a small interval, table
lookup + polynomial correction), with the *coefficients themselves*
included in the receipt's binding (the table-digest pattern CIS-1 already
uses). This is more work to build from scratch (design/fit/validate a new
polynomial approximation rather than reuse an existing correctly-rounded
library) and reintroduces the "arbitrary choice that must be pinned by
fiat, not derived" property (a acceptable choice may still not match
another team's independently-designed pinned LUT even if both are
individually reasonable, unlike (a)'s converge-by-construction property).
Advantage: full control over accuracy/speed tradeoff and precedent
already proven at CIS-1's integer level (three independent implementations
converged on the pinned exp LUT, ledger A31/A37) — the organizational
machinery (digest a table, cite it in the spec, CI-gate it) is already
built and battle-tested.

**Recommendation:** prototype **(a)** first for E14b (adopt an existing
correctly-rounded `libm`-equivalent — CORE-MATH publishes reference C
implementations; a Rust port or FFI binding is the concrete next step),
because it removes an entire class of "did our two implementations pick
the same arbitrary polynomial" risk that CIS-1's own errata history shows
is exactly where clean-room reimplementations diverge (ledger A31's
`from_ratio` gaps). Fall back to (b) only if a correctly-rounded
implementation cannot be sourced/ported for a needed function at
acceptable performance, in which case CIS-2 should say so explicitly and
cite the perf number that drove the fallback (not assumed, not asserted
here).

### 3.4 Denormal handling

**Proposal: normative — pin FTZ=on, DAZ=on for all fp32 arithmetic in the
decode path, on every ISA**, rather than relying on "the ranges never
produce denormals" (unlike CIS-1's headroom-is-proof approach for integer
overflow, denormal *avoidance*-by-range-argument is fragile for fp32
because gradient/underflow behavior is much harder to bound tightly than
integer accumulator width, and the failure mode — silent divergence
between platforms that differ only in their *default* FTZ/DAZ state,
§2 — is exactly the CIS-1 M7 motivating incident's shape: "the same
engine, same weights, same machine flipped real decoded tokens... purely
from f32 accumulation order" (CIS-1 spec, Motivation). Concretely: set
`_MM_SET_FLUSH_ZERO_MODE`/`_MM_SET_DENORMALS_ZERO_MODE` (x86, MXCSR bits)
at process start to match NEON's hardware-default FTZ behavior (§2), and
verify via a targeted adversarial test (feed the smallest representable
positive normal times a value that would underflow to denormal, on both
ISAs, diff the outputs) as part of E14b, not merely asserted in the spec
text. Cost: negligible (a startup-time control-register write on x86;
no-op on aarch64, since NEON is already FTZ by hardware default) —
this is a case where pinning is nearly free, unlike the reduction-order or
transcendental questions.

### 3.5 bf16 → fp32 exact widening

**Proposal: normative — the widening is bit-shift, not conversion.**
`f32::from_bits((bf16_bits as u32) << 16)` (zero-extend the bf16 16-bit
pattern into the high half of an f32 bit pattern) is exact by
construction: bf16's exponent field is the same width and bias as fp32's
(8 bits), so there is no exponent range issue, and the 7 mantissa bits
occupy fp32's top 7 mantissa bits exactly, with the low 16 mantissa bits
defined as zero — no rounding, no library call, no room for a
platform-dependent "convert" routine to disagree. This should be stated
as the literal bit operation in CIS-2's §5, not as prose like "convert
bf16 to fp32," precisely because CIS-1's own errata history (A31, A32
erratum entries) shows that operations left as prose rather than
bit-exact procedure are where independent implementations diverge.

### 3.6 What stays entirely unconstrained (implementation freedom, CIS-1 §6 precedent)

Consistent with CIS-1's philosophy of pinning outcomes, not loop
structures: memory layout, tiling/blocking granularity, thread/SIMD
parallelization strategy, and instruction selection are all free, **as
long as the reduction order and transcendental bit-patterns computed match
the reference exactly for every input** — the same "vectorize freely,
match bits unconditionally" contract as CIS-1 §6, restated for fp32. This
is important to state explicitly in CIS-2 so the spec is not read as
"forbid all optimization," which it does not need to be.

---

## 4. Target model: SmolLM2-135M

Confirmed directly from the model's published `config.json`
([HuggingFaceTB/SmolLM2-135M on Hugging Face](https://huggingface.co/HuggingFaceTB/SmolLM2-135M), `config.json` fetched
2026-08-28):

```json
{
  "architectures": ["LlamaForCausalLM"],
  "hidden_size": 576,
  "intermediate_size": 1536,
  "num_hidden_layers": 30,
  "num_attention_heads": 9,
  "num_key_value_heads": 3,
  "hidden_act": "silu",
  "rms_norm_eps": 1e-05,
  "rope_theta": 100000,
  "rope_interleaved": false,
  "max_position_embeddings": 8192,
  "tie_word_embeddings": true,
  "torch_dtype": "bfloat16",
  "vocab_size": 49152,
  "model_type": "llama"
}
```

**Architecture summary:** 30-layer Llama-family decoder, hidden size 576,
9 query heads / 3 KV heads (grouped-query attention, group size 3),
head_dim = 576/9 = 64, SwiGLU MLP with intermediate size 1536, RMSNorm
(eps 1e-5), RoPE with theta=100000 and non-interleaved layout, tied input/
output embeddings, vocab size 49152. Activation function `silu` confirms
the SiLU/SwiGLU op in §2's table applies directly. Stored in bf16
(`torch_dtype: bfloat16`), matching CIS-2's stated bf16-weights/fp32-
compute target exactly.

**File format and size on disk:** single `model.safetensors` file, 269 MB
([HuggingFaceTB/SmolLM2-135M file listing](https://huggingface.co/HuggingFaceTB/SmolLM2-135M/tree/main), fetched 2026-08-28). At
~135M parameters (per the model's name and repo description) stored in 2
bytes/param (bf16), 135M × 2 ≈ 270 MB is consistent with the observed file
size — confirms the checkpoint is genuinely bf16 on disk, not fp32
truncated-and-relabeled.

**fp32 RAM need estimate (arithmetic, not measured):** widening every
weight to fp32 doubles storage: 135M params × 4 bytes ≈ 540 MB for weights
alone. Add activations (hidden size 576 × sequence length, small relative
to weights for this model size) and any duplicate buffers a
reference-then-verify design keeps resident (e.g., holding both the bf16
source and fp32-widened copy briefly), and a working estimate of
**roughly 600 MB–1 GB peak resident fp32 memory** for a straightforward,
unoptimized scalar Rust implementation is reasonable — well within the
project's known 6.4 GB total RAM constraint (`~/.claude/CLAUDE.md`
machine notes; also noted in this repo's own `CLAUDE.md`: "RAM is 6.4 GB
total; check `free -m` before starting anything heavy"). This is an
arithmetic estimate, not a measurement — E14b should record actual peak
RSS the first time the reference implementation runs.

**Why this model is a reasonable CIS-2 target:** small enough to widen
fully to fp32 and run scalar Rust decode steps at interactive-ish speed
without needing to worry about RAM headroom on this machine; large enough
(30 real transformer layers, real GQA, real SwiGLU) to exercise every op
in §2's table, unlike a toy 2-layer model that might not surface e.g. the
RMSNorm/rsqrt precision issues at realistic activation magnitudes;
publicly available with a permissive, well-documented HF card, matching
CIS-1's own precedent of building on public checkpoints (BitNet-2B) rather
than training something bespoke.

**Fallback candidates if unsuitable** (not investigated in depth by this
sweep — listed for completeness):
- **SmolLM2-360M** or **SmolLM2-1.7B** — same family, same architecture
  shape, larger, for a "does CIS-2's fp discipline hold up at a bigger
  scale" follow-on once the 135M leg is proven, mirroring CIS-1's own M7 →
  BitNet-2B scaling pattern (ledger A21 → A35).
- **HuggingFaceTB/SmolLM-135M (v1)** — the predecessor model; explicitly
  flagged as a possible naming confusion in one of the search results
  found during this sweep ([pytorch/executorch issue #18828](https://github.com/pytorch/executorch/issues/18828), "Should
  'smollm2' alias point at HuggingFaceTB/SmolLM-135M (v1) or
  SmolLM2-135M?") — worth double-checking the exact repo ID
  (`HuggingFaceTB/SmolLM2-135M`, confirmed above) is what any tooling
  actually downloads before E14b begins, since the names are easy to
  conflate.
- **TinyLlama-1.1B** or a similarly small standard Llama-architecture
  checkpoint, if SmolLM2's GQA (3 KV heads) turns out to complicate the
  first E14b implementation more than a standard multi-head-attention
  (KV heads = Q heads) model would — GQA is not architecturally harder to
  spec, but is one more axis of "does the reference get this exactly
  right" to debug simultaneously with the fp contract itself; deferring
  GQA to a second model is a legitimate scope-reduction if E14b timeline
  pressure appears.

---

## 5. Experiment plan (E14b/c/d)

Following CIS-1's own precedent (op-level digest → cross-ISA CI →
independent verifier → receipt → physical iron), staged as:

**E14b — scalar Rust reference implementation + op-level digest.**
- Implement, in Rust, scalar-only (no explicit SIMD intrinsics — the same
  "reference is definitive, optimized kernels conform later" split as
  CIS-1 §5), every op in §2's table for the SmolLM2-135M forward pass:
  embedding lookup, bf16→fp32 exact widening (§3.5), RMSNorm (rsqrt via
  §3.3's chosen transcendental route), RoPE (sin/cos, §3.3), GQA attention
  (QK^T score matmul with §3.1's reduction order, softmax with §3.3's exp
  and §3.1's reduction, V-mix matmul), residual adds (§2, exact), SwiGLU
  MLP (gate/up projections, SiLU via §3.3, elementwise multiply,
  down-projection), final RMSNorm, LM head matmul, argmax.
- Mechanically enforce §3.2 (no `.mul_add()`) and §3.4 (FTZ/DAZ pinned at
  process start on x86; verify NEON default on aarch64) via CI grep-gate
  and a targeted denormal adversarial test, not prose alone — direct
  reuse of CIS-1's "under-specified constraints are where implementations
  diverge" lesson (ledger A31 errata pattern).
- Emit two digest types, deliberately matching CIS-1's existing witness
  format so `cis-verify`-family tooling can be extended rather than
  rebuilt from scratch:
  - **Argmax-token digest**: FNV-1a-64 (or SHA-256, TBD — CIS-1 uses
    FNV-1a for Tier 2/3 op-level digests and SHA-256 for the witness
    chain; CIS-2 should probably go straight to SHA-256 throughout, since
    fp32 logits are the whole point of interest and a stronger hash costs
    nothing meaningful at this model size) over the LE bytes of every
    generated token id, prompt included — direct fp analogue of CIS-1's
    Tier 3 `CIS_DECODE digest=...` (spec §8).
  - **Per-step full-logit-vector SHA-256 chain**, matching the CIS-1
    witness/receipt format exactly (`tests/golden/witness_v1_*.receipt`
    structure: artifact hashes bound in, then a chained SHA-256
    commitment over every decode step's full logit vector) — except the
    logit vector is now `[f32; vocab_size]` bit patterns rather than
    `[i64; vocab_size]` exact integers. This is the artifact CIS-2 needs
    for the same claim CIS-1 makes at A32/A39: "a receipt minted on one
    ISA verifies bit-for-bit on another."
- Preregistered pass bar for E14b: op-level digest identical across **two
  sequential runs on the same host** (the CIS-1 A31-equivalent bar — prove
  the implementation is at least deterministic with itself before asking
  about cross-ISA) before any aarch64 work begins.

**E14c — cross-ISA CI leg.**
- Direct reuse of CIS-1's existing GitHub Actions pattern
  (`arm-digest.yml`, `bitnet2b-receipt.yml` in `~/projects/alice-aegis/.github/workflows/`)
  and its `ubuntu-24.04-arm` hosted-runner leg (ledger A32, A38, A39): run
  the E14b binary, unmodified source, on both `ubuntu-latest` (x86-64) and
  `ubuntu-24.04-arm` (aarch64) GitHub-hosted runners, compare the argmax-
  token digest and the full logit-chain digest.
- Preregistered pass bar: both digests bit-identical across the two ISAs,
  first attempt, matching CIS-1's A32 framing exactly.
- If this fails on first attempt (plausible, unlike CIS-1's ternary case,
  because this is new terrain — §2's denormal-default divergence and
  §3.3's transcendental-implementation-availability risk are both live
  candidates for a first-attempt miss), the CI failure text should, like
  CIS-1's own workflow, "instruct preserving a mismatch as a finding,
  never weakening the gate" (CIS-1 spec §8) — a first-attempt cross-ISA
  divergence is itself a publishable finding about which of §2's sources
  actually bites in practice, not just an implementation bug to silently
  patch around.

**E14d — independent verifier + physical/no-OS legs (stretch, after
E14b/c pass).**
- Extend or fork `cis-verify` (`~/projects/alice-aegis/cis-verify/`,
  ~4,700 lines, `no_std`+alloc, zero external deps, ledger A37/A38) to
  parse and re-derive CIS-2 fp32 receipts the same way it does CIS-1
  integer receipts — a from-spec-text, engine-independent re-derivation,
  the same "third implementation" precedent.
- If E14b/c succeed and time/RAM permit, repeat CIS-1's physical-iron and
  no-OS-unikernel legs (A33/A34/A40 precedent) for the fp32 receipt —
  explicitly a stretch goal, not part of the core preregistered claim,
  since it depends on E14b/c succeeding at all and this model's fp32
  memory footprint (§4) fitting the existing kit-image tooling.

### Preregistered kill/negative line

Per this program's Rule A discipline (identity/quality claims must be
falsifiable, no post-hoc weakening — the same discipline visible
throughout the CIS-1 ledger, e.g. A35's explicit +5% PPL kill line before
the BitNet-2B full-integer run):

- **Primary kill criterion:** if, after implementing §3's normative
  contract in full (fixed reduction order, no FMA, pinned
  transcendental route, pinned denormal handling, exact bf16 widening)
  and mechanically enforcing every gate in §3.2/§3.4, the argmax-token
  digest **still** differs between the x86-64 and aarch64 GitHub Actions
  legs on two consecutive attempts (i.e., not a flaky CI artifact), CIS-2
  as scoped is **negative**: floating-point bit-identity across ISAs is
  not achievable with a source-level-only contract on commodity hardware,
  and the finding should be published as such (a real, useful negative
  result — "here is exactly which of §2's sources survives every pinning
  attempt" — not buried).
- **Secondary/softer kill criterion:** if bit-identity is achieved but
  only by disabling denormal flushing consistency in a way that produces
  measurably wrong (not just non-bit-identical) numeric output — i.e., if
  §3.4's fix trades cross-ISA identity for a correctness regression on
  either platform — that specific fix is negative even if the digest
  passes, and CIS-2 must say so rather than declare victory on the digest
  alone.
- **What would make the result uninteresting even if positive** (see §6).

---

## 6. Risks and what would make the result uninteresting

- **The correctly-rounded-transcendental route (§3.3a) may not have a
  usable Rust implementation or binding at acceptable speed.** CORE-MATH
  ships C reference code; a Rust FFI binding or port is real, unbudgeted
  work, and if it turns out to be meaningfully slower than a
  faithfully-rounded libm for `exp`/`sin`/`cos` at the volume a 30-layer,
  every-decode-step forward pass needs, CIS-2 may be forced into the
  pinned-LUT fallback (§3.3b) by default rather than by choice — which is
  fine, but should be reported as a forced fallback, not framed as the
  preferred design if §3.3a was never actually tried.
- **If bit-identity is achieved only because SmolLM2-135M's particular
  weight/activation distribution never exercises the hard cases** —
  denormal-adjacent activations, hard-to-round transcendental arguments,
  near-tie softmax/argmax decisions — the result would be true but
  **uninteresting**: it would say "this contract works for this one
  model's typical inputs," not "this contract is sound." E14b/c should
  include an adversarial input sweep (deliberately tiny/large activations,
  inputs chosen to land near known libm hard-to-round cases) rather than
  relying only on natural-language-prompt decode, mirroring how CIS-1's
  own kernel work (§6.1's `−128` hazard) treats "handles the hazard the
  well-behaved caller wouldn't produce" as the actual bar, not an
  afterthought.
- **If the result depends on a specific compiler version's fp-contract
  default** (§2's Clang-14-defaults-on finding is Clang/LLVM-specific;
  rustc's non-contraction behavior should be re-verified against the
  specific rustc/LLVM version actually used in E14b, not assumed to hold
  forever — LLVM's fp-contract defaults have changed before and could
  change again), a positive CIS-2 result that is silently version-pinned
  without saying so is a reproducibility hazard of exactly the kind CIS-2
  exists to eliminate elsewhere in the stack. The reference crate should
  pin and state its `rustc`/LLVM version the same way CIS-1's receipts pin
  artifact hashes.
- **Thinking Machines' batch-invariance work (§1.1) is same-hardware only
  and therefore not a competing claim** — but if a reviewer conflates
  "deterministic across concurrent load on one GPU" with "deterministic
  across ISAs," CIS-2's actual contribution (cross-ISA, not just
  cross-batch-size) could be under-appreciated or, conversely,
  over-claimed if CIS-2's own writeup is not precise about which
  nondeterminism source it addresses. The §2 table's per-op breakdown
  exists specifically to keep this distinction sharp in the eventual
  paper.
- **zkML and TEE approaches (§1.3/§1.4) solve a different, arguably
  harder, threat model** (an adversarial/untrusted executor) at much
  higher cost; CIS-2, like CIS-1, only solves "did two honest but
  independent parties, on different hardware, get the same numeric
  answer," not "prove to a skeptic you ran the computation at all
  without them re-running it." This scope limitation should stay explicit
  in CIS-2's own "not claimed" section (mirroring CIS-1 spec §10), because
  the receipt format's resemblance to a cryptographic commitment invites
  over-reading it as a stronger integrity guarantee than it is.
- **RAM/scale honesty:** the §4 fp32 RAM estimate (~600 MB–1 GB) is
  arithmetic, not measured, and this machine has 6.4 GB total RAM shared
  with other running work (per this repo's own `CLAUDE.md`) — if E14b's
  actual peak RSS is meaningfully higher than estimated (e.g., due to
  duplicate buffers, debug-build bloat, or an inefficient first-draft
  implementation), that is itself worth recording rather than silently
  reducing scope without a note.

---

## Sources

- [Thinking Machines Lab, "Defeating Nondeterminism in LLM Inference"](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/)
- [Simon Willison, summary of the above](https://simonwillison.net/2025/Sep/11/defeating-nondeterminism/)
- [Medium/Siddhant Gupta, "Defeating nondeterminism in LLM inference, in practice"](https://medium.com/@siddhantg314/defeating-nondeterminism-in-llm-inference-in-practice-38a7dd1e4112)
- [LMSYS/SGLang blog, "Towards Deterministic Inference in SGLang and Reproducible RL Training"](https://www.lmsys.org/blog/2025-09-22-sglang-deterministic/)
- [arXiv:2605.30218, MarginGate](https://arxiv.org/pdf/2605.30218)
- [arXiv:2601.17768, LLM-42](https://arxiv.org/pdf/2601.17768)
- [arXiv:2606.21023, HEAL](https://arxiv.org/pdf/2606.21023)
- [arXiv:2511.20621, DiFR](https://arxiv.org/pdf/2511.20621)
- [arXiv:2602.00182, EigenAI](https://arxiv.org/html/2602.00182)
- [arXiv:2509.06977, cross-backend reproducibility framework](https://arxiv.org/pdf/2509.06977)
- [emergentmind.com, EZKL summary](https://www.emergentmind.com/topics/ezkl)
- [emergentmind.com, zkLLM summary](https://www.emergentmind.com/topics/zkllm)
- [arXiv:2603.18046, NANOZK](https://arxiv.org/pdf/2603.18046)
- [arXiv:2502.18535, ZK-verifiable-ML survey](https://arxiv.org/pdf/2502.18535)
- [arXiv:2509.18886, Confidential LLM Inference: Performance and Cost Across CPU and GPU TEEs](https://arxiv.org/pdf/2509.18886)
- [arXiv:2505.16501, Performance of Confidential Computing GPUs](https://arxiv.org/pdf/2505.16501)
- [Intel Community blog, Intel TDX + NVIDIA H100 attestation](https://community.intel.com/t5/Blogs/Products-and-Solutions/Security/Seamless-Attestation-of-Intel-TDX-and-NVIDIA-H100-TEEs-with/post/1525587)
- [GitHub, willow-ahrens/ReproBLAS](https://github.com/willow-ahrens/ReproBLAS)
- [SC13 workshop paper, ReproBLAS](https://sc13.supercomputing.org/sites/default/files/WorkshopsArchive/pdfs/wp141s1.pdf)
- [ACM TOMS, "Algorithms for Efficient Reproducible Floating Point Summation"](https://dl.acm.org/doi/10.1145/3389360)
- [UC Berkeley TR EECS-2016-121, reproducible summation and BLAS](https://www2.eecs.berkeley.edu/Pubs/TechRpts/2016/EECS-2016-121.html)
- [ResearchGate, ExBLAS: Reproducible and Accurate BLAS Library](https://www.researchgate.net/publication/288828110_ExBLAS_Reproducible_and_Accurate_BLAS_Library)
- [CORE-MATH project page](https://core-math.gitlabpages.inria.fr/)
- [CORE-MATH FAQ](https://core-math.gitlabpages.inria.fr/faq.html)
- [CORE-MATH FPBench talk slides](https://members.loria.fr/PZimmermann/talks/core-math-fpbench.pdf)
- [RLibm project page](https://people.cs.rutgers.edu/~sn349/rlibm/)
- [arXiv:2111.12852, RLIBM-PROG](https://arxiv.org/pdf/2111.12852)
- [arXiv:2504.07409, RLibm-MultiRound](https://arxiv.org/pdf/2504.07409)
- [ResearchGate, CR-LIBM](https://www.researchgate.net/publication/252186392_CR-LIBM_A_correctly_rounded_elementary_function_library)
- [GitHub, microsoft/onnxruntime](https://github.com/microsoft/onnxruntime)
- [arXiv:2606.03019, "Reproducibility is the New Copyleft"](https://arxiv.org/pdf/2606.03019)
- [IEEE 754-2019 standard page](https://standards.ieee.org/standard/754-2019.html)
- [IEEE Computer background PDF on 754-2019](https://grouper.ieee.org/groups/msc/ANSI_IEEE-Std-754-2019/background/ieee-computer.pdf)
- [Rust f32 docs (mul_add)](https://doc.rust-lang.org/1.61.0/std/primitive.f32.html)
- [rustc intrinsics::fmuladdf32 docs](https://doc.rust-lang.org/nightly/core/intrinsics/fn.fmuladdf32.html)
- [LLVM discourse, "FP contraction (FMA) on by default"](https://discourse.llvm.org/t/fp-contraction-fma-on-by-default/64975)
- [llvm-dev RFC, "change -fp-contract=off to actually disable FMAs"](https://groups.google.com/g/llvm-dev/c/nBiCD5KvYW0/m/PWcNUdZ4DAAJ)
- [ARM developer docs, NEON flush-to-zero mode](https://developer.arm.com/documentation/den0018/latest/NEON-Instruction-Set-Architecture/Flush-to-zero-mode)
- [Intel compiler docs, FTZ option](https://www.cis.uoguelph.ca/~wgardner/intel_docs/compilers/compiler_c/main_cls/copts/common_options/option_ftz.htm)
- [Gist, "Enable flushing denormals to zero in Rust"](https://gist.github.com/GabrielMajeri/545042ee4f956d5b2141105eb6a505a9)
- [HuggingFaceTB/SmolLM2-135M model card and files](https://huggingface.co/HuggingFaceTB/SmolLM2-135M)
- [HuggingFaceTB/SmolLM2-135M config.json (raw)](https://huggingface.co/HuggingFaceTB/SmolLM2-135M/raw/main/config.json)
- [HuggingFaceTB/SmolLM2-135M file tree](https://huggingface.co/HuggingFaceTB/SmolLM2-135M/tree/main)
- [pytorch/executorch issue #18828, SmolLM/SmolLM2 naming](https://github.com/pytorch/executorch/issues/18828)
- Internal (read, not modified): `~/projects/alice-aegis/docs/CIS-1_SPEC_v1.0.md`
- Internal (read, not modified): `~/projects/alice-aegis/program/RESEARCH_LEDGER.md` (rows A31–A40)
- Internal (read, not modified): `~/projects/alice-aegis/cis-verify/`
- Internal (read, not modified): `~/projects/claudius-maximus/state/reports/2026-08-27-cis1-related-work.md`
