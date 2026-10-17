# Paper outline — "CIS-2: a normative fp32 contract that makes floating-point transformer inference bit-identical across x86_64 and aarch64"

Drafted 2026-08-28 by Claudius Maximus (Fable) from `docs/E14a`-equivalent design memo
(`~/projects/claudius-maximus/state/reports/2026-08-28-E14a-cis2-fp-design.md`),
`docs/E15b_REFERENCE_RESULT.md`, `docs/E15b_m1p5_CORRECTNESS.md`, the E15c adversarial-verification
report (`~/projects/claudius-maximus/state/reports/2026-08-28-E15c-verify.md`), and the
definitive-win-candidates critic notes
(`~/projects/claudius-maximus/state/reports/2026-08-28-definitive-win-candidates.md`). Mirrors
`~/projects/alice-aegis/docs/CIS1_PAPER_OUTLINE.md` and `docs/paper/*.md` in structure, voice, and
Rule-B discipline: **every number below carries a file:line or a CI run id; nothing here is a new
claim.** Published 2026-10-16 as part of the CIS-2 archive.

Working title alternatives:
- *CIS-2: a normative fp32 contract for bit-identical transformer inference across ISAs*
- *Floating point does not have to be nondeterministic: a portable receipt for fp32 LLM decode*

Target: arXiv preprint (cs.LG + cs.CR), same track as the CIS-1 paper; positioned explicitly as
CIS-1's companion (§7) — CIS-1 covers ternary/integer inference, CIS-2 covers the much larger
class of ordinary fp32/bf16 models. **NOT yet ready to submit** — see the "what would make this
definitive" checklist (end of this file) and the weakest-points list in the return summary.

---

## Claim (one paragraph, conservative)

CIS-2 is a normative arithmetic contract — fixed reduction order, no FMA contraction, pinned
transcendental routes that avoid platform libm entirely, pinned FTZ/DAZ denormal handling, and
exact bf16→fp32 widening — for the fp32 forward pass of a standard Llama-architecture decoder,
such that a conforming reference implementation is **bit-identical across x86_64 and aarch64**:
identical SHA-256 witness chains over the full per-step logit vector (not just argmax token ids),
on the same commit, same non-cached CI build, on both ISAs. This is demonstrated today on
`HuggingFaceTB/SmolLM2-135M` (135M parameters, bf16 checkpoint, fp32 compute) over a 16-token
greedy decode, matching an independent PyTorch/`transformers` fp32 oracle's argmax decisions
16/16 and its step-0 full-vocab logits to ~4e-6 relative error. It has **not** been demonstrated
at longer sequence lengths, on a second model family, under independently varied compiler
toolchains beyond a single CI run's shared `rustc` version, or with a formally specified verifier
cost/threat model written into a spec document (as opposed to informally in this report) — see §4
and §8.

**Integer identity is expected; float identity is not.** CIS-1's central trick — every reduction
is a sum of exact integers, and integer addition is associative — makes bit-identity nearly free:
any legal reordering, any SIMD width, any ISA gives the same sum. Floating-point addition is
*not* associative, so "bit-identical across ISAs" for fp32 is not a restatement of a property the
arithmetic already has; it requires actively removing every source of reduction-order and
transcendental-routing freedom that IEEE 754 otherwise leaves unspecified (memo §2). This is the
paper's actual contribution: not that floats *can* be made deterministic (Thinking Machines'
batch-invariance work already shows that on GPUs, same-hardware only — see §2), but that a
specific, narrow, auditable contract achieves it **across ISAs**, which no prior art reviewed
claims.

---

## 1. Introduction — the problem is stated, not motivated by hype

- Two machines running "the same fp32 model" on different ISAs (or different compilers, or
  different SIMD widths) can disagree at the logit level even with identical weights and identical
  source, because IEEE-754 floating-point addition is not associative and several operations
  (rsqrt, exp, sin/cos) are only *faithfully* rounded, not *correctly* rounded, in ordinary libm
  implementations — meaning there is no standard way to *prove* what an fp32 model computed on a
  named machine, only to reproduce it approximately.
- Prior art on determinism largely targets a narrower or orthogonal problem:
  - **Batch invariance** (Thinking Machines Lab, Sept 2025) fixes GPU reduction kernels so the
    *same server* gives bit-identical output regardless of concurrent batch size — an explicitly
    same-hardware, same-software-stack guarantee, not a cross-ISA one
    ([Thinking Machines Lab blog](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/);
    memo §1.1).
  - [removed 2026-10-17: unverified prior-art characterization]
  - [removed 2026-10-17: unverified prior-art characterization]
  - **glibc libm cross-platform divergence**: transcendental functions (`sin`, `cos`, `exp`) are
    only faithfully rounded (≤1 ULP, not exact-to-nearest) under IEEE 754 §1.6 (memo §1.6), and
    glibc's x86_64 and aarch64 implementations are separate codebases that can and do disagree by
    a ULP on hard cases — the exact mechanism CIS-2 §3.3 sidesteps by using a self-contained,
    libm-free pinned polynomial route rather than hoping platform libms agree (E15c verification
    report, item 2: "zero calls to platform libm exp/sin/cos... sidesteps the classic
    glibc-x86-vs-aarch64 transcendental divergence bug class entirely, by construction").
- Contribution list (one line each, pointing to a section):
  1. A normative fp32 arithmetic contract (CIS-2 §3-equivalent, memo §3) — fixed reduction order,
     no FMA, libm-free pinned transcendentals, pinned FTZ/DAZ, exact bf16 widening — whose
     conformance is a SHA-256 witness chain over the full per-step logit vector (§3).
  2. A working Rust reference implementation of the full contract for a real Llama-family
     checkpoint (SmolLM2-135M, 30 layers, GQA, SwiGLU, tied embeddings), not a toy kernel (§4, E15b).
  3. Independent-oracle correctness: 16/16 greedy token match against PyTorch/`transformers`' own
     fp32 forward pass, step-0 full-vocab logit agreement to ~4e-6 relative, well inside a
     pre-registered 1e-2 bar (§4, E15b m1.5).
  4. Cross-ISA bit-identity of the full witness chain — not just argmax — reproduced in the same
     CI run on x86_64 and aarch64 hosted runners, same commit, non-cached, full pipeline each leg
     (§4, E15c; digest `CIS2_REF digest=ba88708b...09dd0f`).
  5. Adversarial checks that the mechanism, not luck, produces the result: rebuild with
     `target-cpu=native` on FMA-capable hardware still shows zero FMA instructions and an
     unchanged digest (§4, E15c item 3); the no-FMA and no-libm-transcendental gates are mechanical
     (grep + `objdump`), not asserted in prose (§3).
  6. The cost of verification, stated honestly: no succinct proof exists; verification is one full
     deterministic decode by an independent implementation, and per-step logits are not stored —
     only their SHA-256 fold survives (§5, mirroring CIS-1's verification-model wording).
- What is **not** claimed, up front (full list in §6/§8): no timing/throughput number; fp32 only
  (no int8/bf16-compute path); one 135M model; greedy decoding only; 16 generated tokens; one CPU
  family per ISA leg; CPU-only (no GPU); scalar reference, not a fast kernel.

## 2. Background and related work

- **IEEE 754-2019 and reproducibility** (memo §1.6): addition, subtraction, multiplication,
  division, and sqrt are mandatory correctly-rounded; `sin`/`cos`/`exp` are recommended but not
  mandatory correctly-rounded, which is precisely why libm implementations diverge and why CIS-2
  cannot simply say "use IEEE 754 floats" the way CIS-1 says "use exact integers."
- **Cross-platform reproducible floating-point summation** — ReproBLAS's binned reduction
  ([Demmel & Nguyen, ACM TOMS 2020](https://dl.acm.org/doi/10.1145/3389360); [UC Berkeley TR](https://www2.eecs.berkeley.edu/Pubs/TechRpts/2016/EECS-2016-121.html))
  and ExBLAS's long-accumulator approach
  ([ExBLAS summary](https://www.researchgate.net/publication/288828110_ExBLAS_Reproducible_and_Accurate_BLAS_Library))
  prove order-independent-yet-reproducible fp summation is achievable at bounded cost (~9n flops
  per ReproBLAS's own figure) — the closest technical relatives to CIS-2 §3.1's reduction-order
  question, using a different mechanism (exponent binning / wide fixed-point accumulators) than
  CIS-2's current choice (strict sequential order, memo §3.1 option (a)).
- **zkML** (EZKL, zkLLM) proves a computation was done correctly relative to committed
  inputs/circuit without necessarily re-executing the original floating-point forward pass;
  reported costs are 3-6 orders of magnitude more expensive per inference than deterministic
  re-execution (zkLLM: REPORTED ~803s proving per forward pass, extrapolating to ~18 days for a
  2000-token generation — memo §1.3, UNVERIFIED beyond secondary source) — a different trust model
  (cryptographic proof vs. bit-exact independent replay), cited as the cost baseline CIS-2's
  verification model (§5) is far cheaper than.
- **TEE/confidential-computing attestation** (NVIDIA Hopper CC mode, Intel TDX) attests that a
  genuine, correctly configured accelerator ran a workload confidentially — a hardware root of
  trust about *what ran*, not a claim that the numeric result is cross-platform reproducible; it
  requires trusting a silicon vendor's attestation root, which CIS-1/CIS-2's "re-derivable by an
  independent, `no_std`, zero-shared-code verifier" design explicitly avoids depending on (memo
  §1.4).
- **DiFR** (arXiv:2511.20621) explicitly gives up on bit-exactness and verifies approximately —
  the opposite design point from CIS-1/CIS-2's bit-exact receipt (memo §1.2, UNVERIFIED beyond
  abstract) — worth citing as the alternative CIS-2 is choosing not to take.
- **Sharpest differentiator, stated plainly**: no work reviewed in this sweep (memo §1, the
  definitive-win-candidates critic pass) makes a structural cross-ISA bit-identical claim for
  floating-point LLM inference with an independently re-derivable receipt. Batch invariance is
  same-hardware; [removed 2026-10-17: unverified prior-art characterization] zkML and TEE
  attestation answer a different question. This gap, not a speed or size claim, is CIS-2's stated
  contribution (definitive-win-candidates synthesis, ranked option 1).

## 3. The CIS-2 normative contract (memo §3, as gates with file:line where enforced)

Modeled on CIS-1 §5/§6: the reference implementation is definitive; optimized kernels conform by
matching bits, not by copying loop structure (memo §3.6). Six gates, each with where it is
enforced today:

| # | Gate | Enforcement (this repo) | Status |
|---|---|---|---|
| 1 | **Reduction order** — strict left-to-right sequential accumulation for every dot product / sum (dot products, RMSNorm sum-of-squares, softmax denominator); no chunking/tree structure. | `dot_seq`/`sum_seq` — plain `for` loops, `src/math.rs:40` (`dot_seq`), `src/math.rs:52` (`sum_seq`); regression test `dot_seq_is_order_sensitive_by_design` (`src/math.rs:329`) asserts the pinned order specifically, not just "some" order (E15b result: `[1e8,1,-1e8]·[1,1,1] = 0.0`, only correct left-to-right). | Enforced, tested. Memo §3.1 flags fixed-tree reduction (ReproBLAS-style) as an open v0.2 question, not yet decided. |
| 2 | **No FMA contraction anywhere** — `a*b + c` must lower to separate `fmul`+`fadd`, never `.mul_add()`/`llvm.fma`. | Mechanical grep gate `tests/no_mul_add.rs` + disassembly gate `scripts/no_fma_gate.sh` (objdump for `vfmadd\|vfnmadd\|vfmsub\|vfnmsub\|fmadd\|fmsub`). E15c adversarially rebuilt with `RUSTFLAGS="-C target-cpu=native"` on FMA-capable hardware: 0 FMA instructions in `.text`, digest unchanged (E15c-verify report item 3). | Enforced, mechanically gated, adversarially confirmed. |
| 3 | **Transcendentals: libm-free pinned polynomial route** (memo §3.3 route (b), not route (a) correctly-rounded CORE-MATH/RLIBM — no published Rust crate/binding for either was found on crates.io at E15b time). `exp`/`sin`/`cos` via Cephes-pattern range-reduction + fixed-degree polynomial; `rsqrt` via `1.0/x.sqrt()` (both IEEE-754-mandatory correctly-rounded ops, no libm call). | `exp_pinned`/`sin_pinned`/`cos_pinned`, `src/math.rs:100` onward; `rsqrt_cr`, `src/math.rs:66`; table digest `0bf9257bc5...` printed and matched identically on both CI legs (E15c-verify item 4). Zero calls to platform libm `exp`/`sin`/`cos` (E15c-verify item 2). | Enforced. Route (a), the mathematically-forced correctly-rounded alternative, was not attempted — flagged as a real gap (§6, §8): route (b) is "an arbitrary choice pinned by fiat," not convergent-by-construction. |
| 4 | **Denormal handling: FTZ=on, DAZ=on on every ISA** — pinned as an explicit hardware-mode requirement rather than argued away by range bounds (unlike CIS-1's integer headroom-is-proof approach), because FTZ/DAZ is a genuine *hardware default divergence* between x86 (gradual underflow by IEEE-754-conformant default) and aarch64 NEON (FTZ by hardware default). | `src/denormal.rs:25` (`pin_ftz_daz`, x86_64 MXCSR bits 15/6 via inline asm) and the aarch64 FPCR.FZ leg (E15c commit `f83e8dd`, "aarch64 FPCR.FZ pin"); readback-asserted at `src/main.rs:228` before any decode-path arithmetic; adversarial unit test `ftz_daz_pinned_and_denormal_input_flushed` (`src/denormal.rs`, `black_box`-guarded so LLVM cannot fold the subnormal op away) confirmed passing on both ISAs in CI (E15c-verify item 2). | Enforced on both ISAs, CI-gated. |
| 5 | **bf16→fp32 widening = exact bit-shift**, not a rounding "conversion." | `widen_bf16`, `src/math.rs:33`, literally `f32::from_bits((bits as u32) << 16)`; test `widen_bf16_exact` (`src/math.rs:292`). | Enforced, tested. |
| 6 | **Everything else is free** (memory layout, tiling, thread/SIMD strategy, instruction selection) as long as the reduction order and transcendental bit patterns match the reference exactly — the same "vectorize freely, match bits unconditionally" contract as CIS-1 §6. | Not yet exercised: no optimized (SIMD) kernel exists yet, only the scalar reference (§6, limitations). | Stated, not yet tested against an optimized kernel. |

**Conformance = one digest**: `CIS2_REF digest` (`src/main.rs:414`, `witness_digest`) is a SHA-256
chain over the three artifact hashes (weights/config/tokenizer) + prompt token ids, then per
generation step the **full fp32 logit vector's raw bit pattern** (all 49,152 vocab entries,
`v.to_bits().to_le_bytes()`) plus the argmax token id — the E15c report is explicit that this is
"a much harder bar than argmax-only" (E15c-verify item 1).

## 4. Evidence table (stub — mark existing vs. pending)

| Row | What | Status | Digest / result | Source |
|---|---|---|---|---|
| E15b m1 | Rust fp32 reference, in-process + cross-process repeat, same host | **EXISTS** | `run1_witness_digest == run2_witness_digest` = `830d972d...9786907` (pre-RoPE-fix); same-host determinism only, no cross-ISA claim | `docs/E15b_REFERENCE_RESULT.md` |
| E15b m1.5 | Correctness vs. PyTorch/`transformers` fp32 oracle | **EXISTS** | 16/16 greedy token match; step-0 full-vocab max abs diff `8.96e-05`, relative `~3.98e-06` (bar was `<1e-2`) | `docs/E15b_m1p5_CORRECTNESS.md`, `scripts/oracle_compare.py` |
| E15b m1.5 (RoPE fix) | Post-fix reference digest (pinned `exp_pinned` for `inv_freq`, not host `f64::powf`) | **EXISTS** | `CIS2_REF digest=ba88708b...09dd0f`; argmax digest unchanged from pre-fix run (no token flip) | `docs/E15b_m1p5_CORRECTNESS.md` |
| E15c | Cross-ISA CI matrix (x86_64 + aarch64, same commit, non-cached) | **EXISTS** | Both legs: `CIS2_REF digest=ba88708b...09dd0f`, table digest `0bf9257bc5...`, `inv_freq table_digest=da9f6dcf...`; run 33171752921, commit `f83e8dd8` | E15c-verify report; `.github/workflows/e15c-cross-isa.yml` |
| E15c adversarial | `target-cpu=native` rebuild on FMA-capable x86 host; `opt-level=0` rebuild | **EXISTS** | Both variants: identical digest, 0 FMA instructions | E15c-verify report item 3 |
| E15d(a) | Compiler invariance (opt-level x target-cpu x ISA matrix) | **IN PROGRESS** | Branch `cm/e15d-compiler-invariance` has 2 commits past E15c (CI matrix + trigger fix, commit `d1cfa7f`); no completion report read by this outline pass | `cm/e15d-compiler-invariance` branch log |
| E15d(b) | 128-token decode (vs. current 16) | **PENDING** | Branch `cm/e15d-longer-and-second-model` exists but has made zero commits past E15c HEAD as of this outline | branch log (identical HEAD to E15c) |
| E15d(c) | Second model family | **PENDING** | Same branch, same status — not started | branch log |
| Phone leg | Physical mobile-ARM device (distinct from cloud aarch64 CI runners) | **PENDING** | Not found in any cis2-fp doc or branch as of this outline; CIS-1's own phone leg (E5) is referenced as "running" in the definitive-win-candidates report but for the *integer* line, not CIS-2 | `2026-08-28-definitive-win-candidates.md`, Fable-decision note |
| rust-toolchain pin | Exact `rustc` version pinned in CI (not "whatever `stable` resolves to today") | **PENDING — flagged risk** | Both E15c legs happened to resolve to `rustc 1.98.0 (88d9e12ae 2026-08-18)` in the same run; no `rust-toolchain.toml` exists; E15c-verify report's overall verdict names this the one open caveat | E15c-verify report, "Overall verdict" |

## 5. Verification model and threat model

Mirrors CIS-1 paper §5's wording, restated for fp32 (`~/projects/alice-aegis/docs/paper/05_receipt.md`):

**Verification model.** A CIS-2 witness chain contains the three artifact hashes, the prompt
tokens, and per-step full logit-vector bit patterns folded into a SHA-256 chain — it does not
retain the logits themselves, only their fold, exactly as CIS-1's receipt does. A verifier is an
independent implementation of the contract that recomputes the entire forward pass from the
artifact bytes and the declared prompt, and compares its own chain against the claimed one.
Verification cost is **one full deterministic decode** — there is no check cheaper than
re-running it, and this is stated as a limitation, not hidden: CIS-2, like CIS-1, is not a
succinct proof system. Unlike CIS-1 (§5, A37/A38), **no separate, zero-shared-code `cis-verify`-
equivalent crate exists yet for CIS-2** — the only implementation of the contract today is the
reference itself (§8); the oracle comparison (E15b m1.5, PyTorch/`transformers`) is a correctness
check against a *different, non-conforming* implementation, not a conformance-checking verifier of
the CIS-2 contract, and should not be conflated with one in the paper's wording.

Threat model (adapted from CIS-1 §5):
- A forged witness needs a chain value consistent with SHA-256 preimage resistance, as in CIS-1.
- A divergent implementation of the CIS-2 contract (wrong reduction order, an FMA slipped in, a
  different transcendental route, FTZ/DAZ not pinned) produces a different logit vector at
  whatever step it first diverges, folding forward through the rest of the chain — the E15c
  adversarial rebuilds (target-cpu=native, opt-level=0) are evidence this *would* be caught, not
  proof no other divergence class exists, since only two rebuild variants were tried and no
  independent-authorship reimplementation (CIS-1's A31/A37 clean-room precedent) has been attempted
  for CIS-2 yet.
- Out of scope: model weight provenance; whether the prompt is secret (hashed in the clear, as in
  CIS-1).
- **Where a reviewer should push, stated here rather than only in §8**: (a) the contract has one
  reimplementation (the reference itself) — CIS-1's strongest evidence for implementability-from-
  text was two *independent* clean-room implementations (A31) plus a third standalone verifier
  (A37); CIS-2 has neither yet. (b) "bit-identical" here means full-logit-vector bit-identical
  across two CI-hosted runner instances on one commit in one run — it has not been tested across
  independently-varying compiler versions (only incidental agreement, per the toolchain-pin
  caveat above), nor on physical (non-cloud-runner) aarch64 hardware, nor on a third ISA. (c) the
  verifier-cost claim ("one full decode, no cheaper check") is asserted by analogy to CIS-1, not
  measured for CIS-2's actual reference — no wall-clock number for a CIS-2 verification run has
  been reported in any log this outline pass read (Rule A: no timing was reported, so none is
  claimed here either).

## 6. Limitations — blunt

- **fp32 only.** No int8/bf16-compute path; the model's weights are bf16 but all compute claimed
  bit-identical is fp32 (memo §4).
- **One 135M model.** SmolLM2-135M only; no second architecture or scale tested (E15d(c) pending,
  §4).
- **Greedy decoding, 16 tokens.** No sampling, no longer sequences tested (E15d(b) pending, §4).
- **CPU-only.** No GPU path; the entire motivating problem (batch invariance, §2) is GPU-centric,
  and CIS-2 has not shown its contract extends to, or is even relevant for, GPU kernels.
- **Scalar reference implementation, not a fast kernel.** No SIMD-optimized implementation has
  been built or shown to match the reference's bits (contract gate 6, §3, "not yet exercised");
  CIS-1's own experience (A26/A27) shows this is where real engineering cost and real
  divergence risk lives, and CIS-2 has not yet paid that cost or found that risk.
- **One CI run, one incidental toolchain match.** Cross-ISA identity is demonstrated on one commit,
  one non-cached CI run, with both legs resolving to the same `rustc` version by chance, not by
  a hard pin (§4 evidence table; E15c-verify report "Overall verdict").
- **No independent verifier crate, no independent reimplementation.** Unlike CIS-1's A31 (two
  clean-room implementers) and A37 (a standalone `cis-verify` crate), CIS-2's only implementation
  is the single reference crate; the PyTorch oracle comparison establishes correctness against a
  different, non-conforming implementation, not conformance-verification of the CIS-2 contract
  itself (§5).
- **Transcendental route is the "arbitrary, pinned by fiat" one, not the "convergent by
  construction" one.** Memo §3.3 recommended prototyping route (a) (correctly-rounded, via
  CORE-MATH/RLIBM) first, specifically because it removes "did our two implementations pick the
  same arbitrary polynomial" risk; E15b used route (b) instead because no Rust crate/binding for
  either library was found on crates.io at the time. This is a real, named gap, not a footnote.
- **No phone/mobile-ARM leg, no third ISA.** Both aarch64 results are hosted CI runners
  (`ubuntu-24.04-arm`), named as precisely as the platform allows, per CIS-1's own convention for
  cloud-runner legs (`docs/paper/08_limitations.md`, "Cloud-runner legs are identity evidence
  only").

## 7. Relation to CIS-1 — why the pair matters

CIS-1 (ternary/integer, `~/projects/alice-aegis`) and CIS-2 (fp32, this repo) are deliberately a
matched pair, not two unrelated results: CIS-1 shows bit-identity is *nearly free* to obtain for a
narrow but real model class (ternary-weight, integer-activation transformers) because its
arithmetic is exact; CIS-2 tests whether the same discipline — normative spec, digest
conformance, independent verifier, cross-ISA CI gate — survives when the arithmetic is ordinary
IEEE-754 float, which is the overwhelming majority of deployed models. A reviewer who accepts
CIS-1 but dismisses it as "only works because integers are associative" should find CIS-2's
partial-but-real progress on the much harder floating-point case the more informative half of the
pair. CIS-2 is earlier-stage: it lacks CIS-1's independent-verifier and clean-room-reimplementation
evidence (§5, §6) and its cross-model/cross-length breadth (§4) — the paper should say this
plainly rather than borrow CIS-1's maturity by association.

## 8. Reproducibility appendix

```bash
# Reference build + self-check (from cis2-fp repo root, weights/ populated — see below)
export PATH="$HOME/.cargo/bin:$PATH"
cd ~/projects/cis2-fp

curl -sS -L -o weights/config.json     https://huggingface.co/HuggingFaceTB/SmolLM2-135M/resolve/main/config.json
curl -sS -L -o weights/tokenizer.json  https://huggingface.co/HuggingFaceTB/SmolLM2-135M/resolve/main/tokenizer.json
curl -sS -L -o weights/model.safetensors https://huggingface.co/HuggingFaceTB/SmolLM2-135M/resolve/main/model.safetensors
# sha256 model.safetensors == 80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1

cargo test --release
./scripts/no_fma_gate.sh
nice -n 10 ./target/release/cis2_ref   # prints CIS2_REF digest=ba88708b...09dd0f (post-RoPE-fix)

# Oracle correctness check
python3 -m venv .venv-oracle && .venv-oracle/bin/pip install torch==2.13.0+cpu \
  --index-url https://download.pytorch.org/whl/cpu transformers==5.16.1 safetensors==0.8.0
nice -n 10 .venv-oracle/bin/python scripts/oracle_compare.py /tmp/oracle_step0_logits.f32le

# Cross-ISA CI (already run, not required to reproduce locally without an aarch64 host):
# gh api repos/Aefinity-AI/cis2-fp/actions/jobs/98850338683/logs   # x86_64 leg
# gh api repos/Aefinity-AI/cis2-fp/actions/jobs/98850338874/logs   # aarch64 leg
# run 33171752921, commit f83e8dd86a2d7a78c4618f690d1395e0cc5364eb
```

Repo: `Aefinity-AI/cis2-fp` (private). Branches: `cm/e15b-fp32-reference`, `cm/e15c-cross-isa`
(this outline's base), `cm/e15d-compiler-invariance`, `cm/e15d-longer-and-second-model`. Golden
digest: `CIS2_REF digest=ba88708bf4159a4057d4eef727820ebc5ce1744ae334bfe0cc0776e03509dd0f`. Table
digests: coefficient table `0bf9257bc5...`, `inv_freq` table `da9f6dcfde0425588815509e874515cdcd3d6b8818b6d0136590052e7bbf6f12`.

---

## What would make this definitive — checklist

- [ ] Pin an exact `rustc` version via `rust-toolchain.toml` in CI, so cross-ISA agreement is
      structural, not incidental to one run landing on the same `stable` release.
- [ ] Build a second, independently-authored implementation of the CIS-2 contract (CIS-1's A31
      clean-room precedent) and show it converges on the same witness digest without reference
      access.
- [ ] Build a standalone verifier crate with zero shared code with the reference (CIS-1's A37
      `cis-verify` precedent), and measure its actual wall-clock cost on the CIS-2 model.
- [ ] Complete E15d(a) (compiler invariance across opt-level x target-cpu, independently varied,
      not just incidentally matched) and report its result, not just its branch existing.
- [ ] Complete E15d(b) (longer decode, e.g. 128 tokens) and E15d(c) (second model family) — both
      currently unstarted branches, not in-progress work.
- [ ] Get a physical (non-cloud-runner) aarch64 leg — a phone or a Raspberry-Pi-class board — to
      match CIS-1's A33/A34 physical-iron evidence; today's aarch64 legs are cloud CI runners only.
- [ ] Decide and prototype transcendental route (a) (correctly-rounded CORE-MATH/RLIBM port) per
      memo §3.3's original recommendation, or explicitly justify staying on route (b) with a
      measured performance number, not an assumed one.
- [ ] Write CIS-2 as an actual frozen spec document (analogous to CIS-1's `CIS-1_SPEC_v1.0.md`),
      not only a design memo plus a working reference — the contract currently lives in code and
      an internal report, not in a citable, versioned spec text.
- [ ] Precisely define "bit-identical" in the spec text itself (full-logit-vector, not argmax;
      one CI run, not independently-built binaries) — per the definitive-win-candidates critic's
      point 3 ("bit-identical needs a rigorous definition... or reviewers will dismiss it as
      unrigorous") and the task brief's explicit instruction to do so here.

---

## 6-line arXiv abstract draft

We specify CIS-2, a normative fp32 arithmetic contract for transformer decoding — fixed
left-to-right reduction order, forbidden FMA contraction, libm-free pinned transcendentals, pinned
FTZ/DAZ denormal handling, and exact bf16-to-fp32 widening — under which a conforming
implementation is bit-identical across x86_64 and aarch64. We give a reference implementation for
SmolLM2-135M whose full per-step logit-vector witness chain reproduces exactly across both ISAs in
CI, and whose greedy decode matches an independent PyTorch/transformers fp32 oracle on all 16
generated tokens with step-0 logits agreeing to ~4e-6 relative error. Unlike GPU batch-invariance
work, which guarantees determinism only on fixed hardware, CIS-2 targets cross-ISA identity
directly, at the cost of a scalar-only reference and a narrow evidence base we report without
qualification. We treat this as a companion to CIS-1's integer-only result: floating point can be
made cross-ISA bit-identical, but, unlike exact integers, only by actively removing every degree
of freedom IEEE 754 otherwise leaves open — and we list precisely which degrees of freedom we have
not yet closed.

---

## Work plan (research/drafting only — no `ev run` measurements taken or required for this outline)

1. Justin: decide whether route (a) (correctly-rounded transcendentals) is worth prototyping before
   any submission decision, since it changes §3's central design choice.
2. cm-builder: complete E15d(a)/(b)/(c) before this outline's evidence table (§4) can move any row
   from PENDING/IN PROGRESS to EXISTS.
3. cm-researcher: a clean-room second-implementer pass (CIS-1 A31 precedent) is the single highest-
   leverage missing piece per §5/checklist — no measurement needed to start, just a second author
   given the design memo's §3 text only.
4. Clear the checklist above before any arXiv submission. Published 2026-10-16 as part of the CIS-2 archive.
