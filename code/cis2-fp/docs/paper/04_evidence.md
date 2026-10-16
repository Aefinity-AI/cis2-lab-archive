# 4. Evidence

No timing or throughput number appears anywhere below; every figure is an identity or accuracy
claim (Rule A). Every digest is quoted from a checked-in report file or a named CI run.

**TODO — unsourced-number check.** None. Every digest, token id, and byte count below was found
verbatim in at least one of the cited files. See the self-check at the end of this document.

## Evidence table, E15b → E15i

| Row | What | Result | Source |
|---|---|---|---|
| E15b m1 | Rust fp32 reference, in-process + cross-process repeat, same host | `run1_witness_digest == run2_witness_digest = 830d972dbfb0b5598015f33571d08623d2b05d8e239b8d0288562d9ac9786907`; `argmax_digest = 0b9c8f3ac90d0b9cd5f1719ac327dca1fc639fd87468305fccebbe3d56f67aff`; same-host determinism only, pre-RoPE-fix, no cross-ISA claim | `docs/E15b_REFERENCE_RESULT.md` |
| E15b m1.5 | Correctness vs. PyTorch/`transformers==5.16.1` fp32 oracle (`torch==2.13.0+cpu`) | 16/16 greedy token match `[28, 665, 436, 253, 1838, 8180, 3365, 14176, 30, 2306, 4161, 281, 253, 2066, 2291, 351]`; step-0 full-vocab (n=49152) `max_abs_diff = 8.96453857421875e-05` (vocab idx 40082, rust `5.486028671264648` vs oracle `5.486118316650391`), relative `≈3.98e-06` against a pre-registered `<1e-2` bar | `docs/E15b_m1p5_CORRECTNESS.md`, `scripts/oracle_compare.py` |
| E15b m1.5 (RoPE fix) | Post-fix reference digest: `inv_freq` switched from host `f64::powf` to pinned `exp_pinned` | `CIS2_REF digest=ba88708bf4159a4057d4eef727820ebc5ce1744ae334bfe0cc0776e03509dd0f`; `inv_freq table_digest=da9f6dcfde0425588815509e874515cdcd3d6b8818b6d0136590052e7bbf6f12`; `argmax_digest` unchanged from pre-fix run (no token flip) | `docs/E15b_m1p5_CORRECTNESS.md` |
| E15c | Cross-ISA CI matrix (x86_64 `ubuntu-latest` + aarch64 `ubuntu-24.04-arm`, same commit, non-cached, full pipeline each leg) | Both legs identical: `CIS2_REF digest=ba88708bf4...09dd0f`, `table_digest=0bf9257bc56c4588cb4003e1a105b60169e152222ec734811d0a58e66e1cdeca`, `inv_freq table_digest=da9f6dcf...52e7bb`; run `33171752921`, jobs `98850338683` (x86_64) / `98850338874` (aarch64), commit `f83e8dd86a2d7a78c4618f690d1395e0cc5364eb`, both legs `rustc 1.98.0 (88d9e12ae 2026-08-18)` | `~/projects/claudius-maximus/state/reports/2026-08-28-E15c-verify.md` §4, `.github/workflows/e15c-cross-isa.yml` |
| E15c adversarial | Rebuild variants: `RUSTFLAGS="-C opt-level=0"` and `RUSTFLAGS="-C target-cpu=native"` (FMA-capable local host) | All three build variants (default, opt-level=0, target-cpu=native) give identical `CIS2_REF digest=ba88708b...09dd0f` and identical `inv_freq table_digest=da9f6dcf...52e7bb`; 0 FMA instructions (`objdump -d \| grep -icE "vfmadd\|vfnmadd\|vfmsub\|vfnmsub"`) in every variant | `2026-08-28-E15c-verify.md` §3 |
| E15e | Clean-room attempt #1, from the design memo only (no spec doc existed yet) | Weight/config/tokenizer sha256 and tokenization `[6403, 1980, 253, 655]` MATCH; 16/16 greedy token ids MATCH; `argmax_digest = 0b9c8f3ac90d0b9cd5f1719ac327dca1fc639fd87468305fccebbe3d56f67aff` MATCH; `CIS2_REF` (`241a73387b22b4f81cd96094efeb6603c3f88a0d10c9fca9a7a1feff5fd7d7bf`) and `inv_freq_table_digest` (`6d20bb9d2a7ec35a70fcc399fed93e17664fa74f95942d9ec77f17ae7a882668`) MISMATCH against target; own cross-ISA self-consistency confirmed (CI run `33190989443`) | `docs/E15e_CLEANROOM_RESULT.md` |
| E15f | Normative spec v0.1 written to close E15e's gaps (digest byte encoding, transcendental coefficients as spec text, RoPE `inv_freq` construction, RMSNorm multiply order) | Spec written; two residual reference weaknesses found and queued for E15h (`LN_THETA` literal overstated as config-general; table digests not folded into the receipt; artifact hashes hashed as hex-ASCII not raw bytes) | `docs/CIS2_SPEC_v0.1.md`, `~/projects/claudius-maximus/state/reports/2026-08-28-CIS2-RESULT.md` |
| E15g | Clean-room attempt #2, from `CIS2_SPEC_v0.1.md` text only, `src/`/`verify/` never opened | All 4 digests MATCH on both ISAs, first attempt, 0 of 3 allotted fix attempts used: `CIS2_REF=ba88708bf4...09dd0f`, `argmax_digest=0b9c8f3a...`, `table_digest=0bf9257bc5...`, `inv_freq_table_digest=da9f6dcf...`; 16/16 generated token ids identical; 0 FMA instructions on both legs | `docs/E15g_CLEANROOM_V2_RESULT.md`, CI run `33192338105` |
| E15g-audit | Independence audit of the E15g clean-room crate | INDEPENDENT verdict: weighted verbatim-line overlap 68/378 = 18.0% (`fpenv.rs` 11/32, `main.rs` 33/252, `math.rs` 24/94), attributable to spec-pinned constants/algorithm steps and generic Rust idioms; single fresh-authorship commit `7eb7ac5` (no rename/copy detected); fresh re-dispatch (run `33192908940`) reproduces `CIS2_REF=ba88708bf4...09dd0f` and `inv_freq table_digest=da9f6dcf...` on both ISAs; one soft spot flagged (identifiers `pin_ftz_daz`/`widen_bf16` match src exactly and are not literal spec-body tokens, plausibly convergent naming, not proven) | `~/projects/claudius-maximus/state/reports/2026-08-28-E15g-audit.md` |
| E15h | Reference refactor to v0.2: table digests folded into `CIS2_REF`, raw-byte artifact-hash binding, theta-general `ln_pinned` RoPE | New preregistered digest `CIS2_REF digest v0.2 = a0c563ef804f50413b7fb6619ae4afe9b51b1ffa7655e944221393e85d6261da`; `table_digest=465d358ccd63721256dbd2abbc77ad5de755adf3230635f95b12b1727dfa1ea3` (changed set of hashed coefficients); `inv_freq_table_digest=da9f6dcfde...` (unchanged from v0.1); `argmax_digest=0b9c8f3ac9...` (unchanged); two sequential runs bit-identical (`runs_identical=true`) | `docs/E15h_REFACTOR_v0.2_RESULT.md`, commit `f227b43` |
| E15i | Spec v0.2 document written (full v0.1 body + E15h's three changes, changelog, updated §13 test vectors) and E15d(a)/(b)/(c) rerun against the v0.2 reference | E15d(a): 20/20 compiler-invariance cells match `CIS2_REF=a0c563ef...` and `inv_freq_table_digest=da9f6dcfde...`, 0 FMA in every cell (run `33195649908`, after fixing an unrelated CI grep bug found in run `33195027040`); E15d(b): 5 prompts × gen_toks=128, x86_64==aarch64 on all 5 (run `33195030116`, digests `e8d4f83f...`/`e805baec...`/`cf1ef40e...`/`ee124779...`/`135f50b5...`); E15d(c): Qwen2.5-0.5B (`rope_theta=1000000`) cross-ISA at gen_toks=16 (`2c9f6235...`) and 128 (`dccd55e6...`), plus 16/16 oracle match (run `33195032954`) | `~/projects/claudius-maximus/state/reports/2026-08-28-E15i-result.md`, `docs/E15d_v0.2_DIGESTS.md` |
| E15h-verify2 | Clean-room verifier crate (`verify2`, from E15g) updated and rerun from spec v0.2 text only | MATCH: `CIS2_REF=a0c563ef...` on both ISAs, run `33194049057` | `~/projects/claudius-maximus/state/reports/2026-08-28-CIS2-RESULT.md` (12:35 CT update) |

## The clean-room story, told plainly

The evidence table above is not a monotonic sequence of successes — it is a memo-only attempt that
failed, followed by a spec that closed the failure's exact gaps, followed by a spec-only attempt
that succeeded on the first try. That arc is the strongest single piece of evidence that the CIS-2
*document*, not just the reference binary, is what carries the contract:

1. **E15e (memo-only, MISMATCH).** An implementer working from the E14a design memo alone — never
   opening `src/` — reproduced the artifact hashes, the tokenization, and all 16 greedy token ids
   exactly, but its `CIS2_REF` and `inv_freq_table_digest` did not match. The mismatch was
   localized (not guessed at): weight identity, tokenization, and the discrete argmax decisions all
   agreed, so the divergence had to be in the fp32 logit bit patterns themselves — traced to two
   specific gaps the memo left unstated: the transcendental route (the memo recommended a
   correctly-rounded route but named no concrete coefficients, so two implementations choosing
   route (b) "by fiat" had nothing to converge on) and the RoPE `inv_freq` construction, which the
   memo never specified at all (`docs/E15e_CLEANROOM_RESULT.md`, "Verdict: MISMATCH, but an
   informative one").
2. **A normative spec was written (v0.1) to close exactly those gaps** — hex-pinned transcendental
   coefficients in the spec body itself, the RoPE `inv_freq` formula stated explicitly, and the
   receipt's exact byte encoding spelled out (`docs/CIS2_SPEC_v0.1.md`).
3. **E15g (spec-only, MATCH first try).** A second clean-room implementer, given `CIS2_SPEC_v0.1.md`
   text only and never opening `src/`, `tests/`, or the E15e clean-room crate, reproduced all four
   digests bit-for-bit on both ISAs, zero of the three allotted fix attempts used
   (`docs/E15g_CLEANROOM_V2_RESULT.md`).
4. **An independence audit (E15g-audit)** then checked whether "spec-only" was actually true rather
   than assumed: git history shows single fresh-commit authorship with no rename/copy signal,
   verbatim-line overlap with the reference (18.0% weighted) is attributable to spec-mandated
   constants and generic Rust idioms rather than copied code, and a fresh CI re-dispatch reproduced
   the same digests again — with one honestly-flagged soft spot (two identifier names match the
   reference exactly and are not literal spec-body tokens; plausibly convergent naming from the
   spec's own vocabulary, not disproven)
   (`~/projects/claudius-maximus/state/reports/2026-08-28-E15g-audit.md`).

## v0.1 → v0.2: a header-binding change, not a numeric change

`CIS2_REF` changed from v0.1's `ba88708bf4159a4057d4eef727820ebc5ce1744ae334bfe0cc0776e03509dd0f` to
v0.2's `a0c563ef804f50413b7fb6619ae4afe9b51b1ffa7655e944221393e85d6261da`. This is deliberately **not**
evidence of a changed computation: `generated_token_ids` and `argmax_digest`
(`0b9c8f3ac90d0b9cd5f1719ac327dca1fc639fd87468305fccebbe3d56f67aff`) are byte-identical across v0.1
and v0.2 — "none of v0.2's three changes touch what the model actually computes, only how the
receipt hashes it" (`docs/CIS2_SPEC_v0.2.md` §16). The three v0.2 changes are receipt-format changes:
(1) folding the two transcendental-table digests into the `CIS2_REF` seed, ahead of the artifact
hashes, so a receipt mismatch can be caused by a divergent transcendental table and not just a
divergent logit; (2) generalizing the RoPE `ln(theta)` construction from a `rope_theta==100000.0`-only
literal to a spec-pinned `ln_pinned` polynomial valid for any `rope_theta` (validated on both
`100000.0` and `1000000.0`, `docs/E15d_v0.2_DIGESTS.md`); (3) feeding the three artifact hashes as
their raw 32 bytes rather than their 64-character hex-ASCII string into the witness chain. `
table_digest` also changed (`0bf9257bc5...` → `465d358ccd...`), but for a different, narrower
reason: the *set* of coefficients it hashes grew to include the new `ln` polynomial table, not
because of the raw-bytes change (`CIS2_SPEC_v0.2.md` §6.6). `inv_freq_table_digest` is
byte-identical across v0.1 and v0.2 for SmolLM2-135M (`da9f6dcfde0425588815509e874515cdcd3d6b8818b6d0136590052e7bbf6f12`
in both) — evidence that switching from the bare literal to `ln_pinned(rope_theta)` did not move
this specific model's RoPE table at all (`CIS2_SPEC_v0.2.md` §7.2).

---

**Source map**
- Full digest table: `docs/E15b_REFERENCE_RESULT.md`, `docs/E15b_m1p5_CORRECTNESS.md`,
  `docs/E15e_CLEANROOM_RESULT.md`, `docs/E15g_CLEANROOM_V2_RESULT.md`,
  `docs/E15h_REFACTOR_v0.2_RESULT.md`, `docs/E15d_v0.2_DIGESTS.md`.
- Independence audit: `~/projects/claudius-maximus/state/reports/2026-08-28-E15g-audit.md`.
- Adversarial verification: `~/projects/claudius-maximus/state/reports/2026-08-28-E15c-verify.md`.
- v0.1→v0.2 changelog: `docs/CIS2_SPEC_v0.2.md` §16, Appendix A/B.
