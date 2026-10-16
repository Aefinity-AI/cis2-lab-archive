# 5. Verification model, threat model, and limitations

This section, like §4, carries no timing or throughput number; every figure below is an identity
claim (Rule A).

## Receipt contents at v0.2

A CIS-2 v0.2 witness chain (`CIS2_REF`, spec §12.1) is one continuous SHA-256 stream over, in
order: the coefficient-table digest (`table_digest`, spec §6.6, 32 raw bytes), the RoPE
`inv_freq` table digest (`inv_freq_table_digest`, spec §7.2, 32 raw bytes), the three artifact
hashes (`weights_sha256`, `tokenizer_sha256`, `config_sha256`, each 32 raw bytes — raw bytes, not
64-character hex-ASCII, as of v0.2, spec §12.1 item 3, closing v0.1's §14.2 gap), the prompt token
ids (`u32` little-endian, 4 bytes each), and then, per decode step, the full fp32 logit vector's
raw bit pattern (`v.to_bits().to_le_bytes()`, 49,152 entries × 4 bytes = 196,608 bytes per step for
this vocabulary size, spec §12.1 item 7a) plus the chosen `next_token_id` (4 bytes). A separate,
independently-hashed `argmax_digest` (token ids only, prompt + all generated) is also computed and
printed but is not an input to `CIS2_REF` (spec §12.2, §12.3). Finalized once, `CIS2_REF` at v0.2
for the pinned SmolLM2-135M / `"Once upon a time"` / 16-token test vector is
`a0c563ef804f50413b7fb6619ae4afe9b51b1ffa7655e944221393e85d6261da` (spec §13.1). **The receipt does
not retain the per-step logits themselves** — only their SHA-256 fold survives — exactly as CIS-1's
receipt does not retain per-step logit vectors either
(`~/projects/alice-aegis/docs/paper/05_receipt.md`, "Verification model").

The receipt binds two things a CIS-1-style receipt does not need to bind separately: the two
transcendental-table digests. This is deliberate (spec §14.3, closing v0.1's corresponding gap): a
`CIS2_REF` match alone previously could not distinguish "an implementation using the exact pinned
polynomial coefficients" from "an implementation whose different coefficients happened to produce
the same logits on this one test vector" — v0.2 makes the coefficient tables themselves part of
what must match. The residual caveat, stated in the spec itself: a `CIS2_REF` *mismatch* still does
not, by itself, localize *which* of the five seed inputs (2 table digests + 3 artifact hashes)
diverged — a verifier wanting to localize a mismatch must still compare the individual digests,
all of which are printed alongside `CIS2_REF` (spec §12.3, §14.3).

## Verification cost = one decode, not succinct

Mirroring CIS-1's own wording (`~/projects/alice-aegis/docs/paper/05_receipt.md`, "Verification
model"): a verifier is an independent implementation of the CIS-2 contract that recomputes the
entire forward pass from the artifact bytes and the declared prompt, and compares its own witness
chain against the claimed one. **Verification cost is one full deterministic decode** — there is no
check cheaper than re-running it, and per-step logits are not stored anywhere for a verifier to
spot-check against; the chain is the only compressed artifact. This is stated as a limitation, not
hidden: CIS-2, like CIS-1, is not a succinct proof system.

**Unlike CIS-1, no separate, zero-shared-code standalone verifier crate exists for CIS-2 today.**
CIS-1's `cis-verify` (`~/projects/alice-aegis/docs/paper/05_receipt.md`, "A37") is a distinct,
`no_std`+alloc crate with zero dependency on `aegis-core`. CIS-2's closest analogue is `verify2`
(built in E15g, audited in E15g-audit) — a genuinely independent, from-spec-text implementation
that reproduces every v0.1 and v0.2 digest bit-for-bit
(`docs/E15g_CLEANROOM_V2_RESULT.md`, CI run `33194049057` for the v0.2 rerun) — but this repo's
Appendix A/B language is careful to distinguish that from a *conformance-checking verifier tool*:
`verify2` was built once, as an independence exercise, and is not (yet) maintained as a standing
verifier a third party would run against an arbitrary claimed receipt. The oracle comparison
(E15b m1.5, PyTorch/`transformers`, 16/16 token match, step-0 logit relative diff ≈3.98e-06) is a
*correctness* check against a different, non-conforming implementation (torch uses its own BLAS
reduction order and libm) — it should not be conflated with a CIS-2 conformance verifier.

## Threat model

Adapted directly from CIS-1's (`~/projects/alice-aegis/docs/paper/05_receipt.md`, "Threat model"):

- **Forgery** requires a chain value consistent with SHA-256 preimage resistance — as in CIS-1,
  breaking SHA-256 or already knowing the true forward-pass output.
- **A divergent implementation** of the CIS-2 contract — wrong reduction order, a slipped-in FMA, a
  different transcendental table, FTZ/DAZ not actually pinned — produces a different logit vector
  at whatever step it first diverges, folding forward through the rest of the chain. The E15c
  adversarial rebuilds (`target-cpu=native` on FMA-capable hardware, `opt-level=0`) are evidence
  this *would* be caught — digest and 0-FMA-instruction count both held under both variants
  (`~/projects/claudius-maximus/state/reports/2026-08-28-E15c-verify.md` §3) — not proof no other
  divergence class exists, since only two rebuild variants were tried.
- **Out of scope**: model weight provenance (only the three sha256 artifact hashes are checked,
  spec §2.1); whether the prompt is secret (hashed in the clear, spec §12.1 item 6, matching CIS-1's
  own convention).
- **Where a reviewer should push, stated here rather than only below**: (a) the contract has been
  independently reimplemented twice from text (E15e from a memo, which failed to converge; E15g
  from the spec, which converged first try) plus one independence audit
  (`2026-08-28-E15g-audit.md`) — this is fewer independent implementations than CIS-1's two
  clean-room implementers (A31) plus its standalone `cis-verify` crate (A37); CIS-2 has the
  clean-room precedent but not yet the standing-verifier-tool precedent. (b) "bit-identical" means
  full-logit-vector bit-identical across two CI-hosted runner instances (`ubuntu-latest`,
  `ubuntu-24.04-arm`) on one commit per run — reproduced across multiple separate CI runs and a
  20-cell compiler-invariance matrix at v0.2 (`docs/E15d_v0.2_DIGESTS.md`), but not yet on
  independently-varying compiler *versions* pinned by a `rust-toolchain.toml` (none exists in this
  repo as of this writing — `~/projects/claudius-maximus/state/reports/2026-08-28-E15c-verify.md`,
  "Overall verdict" caveat), nor on physical (non-cloud-runner) aarch64 hardware, nor on a third
  ISA. (c) the verifier-cost claim ("one full decode, no cheaper check") is asserted by analogy to
  CIS-1's own wording, not independently measured for CIS-2's reference — no wall-clock number for
  a CIS-2 verification run appears in any log this document draws on (Rule A: none reported, so
  none claimed).

## Limitations

- **fp32 scalar reference, not a fast kernel.** No SIMD-optimized implementation has been built or
  shown to match the reference's bits; gate 6 of the contract (§3, "everything else is free") is
  stated but "not yet exercised" against any optimized kernel
  (`docs/CIS2_PAPER_OUTLINE.md` §3 row 6). CIS-1's own experience (A26/A27,
  `~/projects/alice-aegis/docs/paper/03_semantics.md` §6) shows this is where real engineering cost
  and real divergence risk lives; CIS-2 has not yet paid that cost or found that risk.
- **135M and 0.5B parameter models only.** `HuggingFaceTB/SmolLM2-135M` is the pinned §13.1 test
  vector; `Qwen/Qwen2.5-0.5B` (`rope_theta=1000000`) is informative second-model evidence
  (`docs/E15d_bc_RESULT.md`, `docs/CIS2_SPEC_v0.2.md` §0), not itself a normative test vector. No
  model above 0.5B parameters has been run through this reference.
- **Greedy decoding only.** No sampling, no temperature, no top-k/top-p (spec §3.4, §0); this
  matches CIS-1's own non-goal (CIS-1 spec §10, cited in `CIS2_SPEC_v0.2.md` §0).
- **CPU only.** No GPU path exists or is claimed; the entire motivating problem this contract
  responds to (cross-hardware nondeterminism, batch invariance) is largely a GPU-kernel
  phenomenon in prior art, and CIS-2 has not shown its contract is relevant to, let alone
  achievable on, GPU kernels.
- **Cloud CI runners only, no physical aarch64 leg.** Both aarch64 results in this document are
  hosted GitHub Actions runners (`ubuntu-24.04-arm`); no phone or physical Raspberry-Pi-class board
  has run this reference, unlike CIS-1's own physical-iron legs
  (`~/projects/alice-aegis/docs/paper/05_receipt.md`, A33/A34). Cloud-runner legs are identity
  evidence only, per CIS-1's own convention for naming such legs precisely.
- **Transcendental route is "pinned by fiat," not "correctly-rounded by construction."** Spec §6.2's
  own text is explicit that route (b) — the pinned Cephes-pattern polynomial actually used — was a
  fallback: no published Rust crate/binding for a correctly-rounded route (a) library (CORE-MATH,
  RLIBM) was found on crates.io when this was built. Two independent implementations that each
  independently chose route (b) would need to copy the exact same coefficients to converge; this is
  precisely the gap E15e's mismatch traced to before the spec pinned the coefficients as text.
- **`ln_pinned`'s validated domain is a finite tested set, not a general accuracy proof** (spec
  §14.1): validated to ≤2e-6 relative tolerance against host `f64::ln` at
  `x ∈ {0.001, 0.1, 0.5, 0.999, 1.0, 1.5, 2.0, 10.0, 100.0, 100_000.0, 1_000_000.0}`; the two values
  that matter for this document's pinned models (`100_000.0`, `1_000_000.0`) are both in that set,
  but a `rope_theta` far outside it is unvalidated.
- **Trig polynomial accuracy is validated only for `|x| ≲ 14`** (spec §14.4); adequate for this
  document's fixed 20-position decodes, but the two-part-π range reduction has not been
  stress-tested at larger magnitudes.
- **No hard compiler-version pin.** No `rust-toolchain.toml` exists in this repo; CI legs have
  landed on the same `rustc` version by chance across every run reported here, not by a structural
  pin (`~/projects/claudius-maximus/state/reports/2026-08-28-E15c-verify.md`, "Overall verdict").
- **No standing, independently-maintained verifier tool**, as distinct from the one-time clean-room
  exercises (E15e, E15g) described in §4 — see "verification cost" above.

---

**Source map**
- Receipt format and byte encoding: `docs/CIS2_SPEC_v0.2.md` §12.1–§12.4.
- Verification-model and threat-model wording pattern: `~/projects/alice-aegis/docs/paper/05_receipt.md`.
- Adversarial rebuild evidence: `~/projects/claudius-maximus/state/reports/2026-08-28-E15c-verify.md`.
- Independence audit: `~/projects/claudius-maximus/state/reports/2026-08-28-E15g-audit.md`.
- Known gaps: `docs/CIS2_SPEC_v0.2.md` §14, Appendix B.
