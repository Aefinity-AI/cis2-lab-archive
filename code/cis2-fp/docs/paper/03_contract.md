# 3. The CIS-2 normative contract

CIS-2 (`docs/CIS2_SPEC_v0.2.md`, DRAFT/HELD private, Aefinity-AI/cis2-fp) rests on the opposite
axiom from CIS-1's (`~/projects/alice-aegis/docs/paper/03_semantics.md` §3): IEEE-754 binary32
addition and multiplication are *not* associative, so bit-identity across ISAs cannot fall out of
the arithmetic itself the way it does for exact integers. Every degree of freedom IEEE 754 leaves
unspecified — reduction order, FMA contraction, transcendental routing, denormal handling — has to
be pinned by fiat and enforced mechanically.

> **Definition (bit-identical fp32 decode, CIS-2 §13.2).** Fix a model checkpoint (identified by
> the three artifact SHA-256 hashes of §2.1), a prompt, and a decode length. Two conforming CIS-2
> implementations are *bit-identical* on this input iff, for every decode step, each computes the
> same **full fp32 logit vector** — every one of the 49,152 vocabulary entries' raw bit patterns,
> not just the argmax token id — and selects the same argmax token. The witness chain
> (`CIS2_REF`, spec §12.1) is a deterministic SHA-256 fold of exactly that state: the two
> transcendental-table digests, the three artifact hashes, the prompt token ids, and then, per
> step, the full logit vector's raw bytes plus the chosen token id — so equal `CIS2_REF` digests is
> equivalent to bit-identical decode. Covered: the full logit vector at every step, not an
> argmax-only summary — spec §12.1 item 7a is explicit that this is "a much harder bar than
> argmax-only" (`~/projects/claudius-maximus/state/reports/2026-08-28-E15c-verify.md` item 1). Not
> covered: KV-cache byte layout (spec §3.5 states caching is a conformance-neutral memoization
> choice, not part of the pinned math); sampling (greedy/argmax only, spec §3.4); any `rope_theta`
> or sequence length outside the validated set (spec §14.1, §14.4).

## The gate list

Six clauses of spec §1/§5/§6 are load-bearing; each is stated below with its spec section and its
enforcement mechanism in this repo.

| # | Gate | Spec § | Enforcement (file:line / CI) |
|---|---|---|---|
| 1 | **FTZ/DAZ pinned on before any decode-path arithmetic** — x86-64 MXCSR bits 15 (FTZ) and 6 (DAZ) set via direct register read-modify-write (not `_mm_setcsr` wrappers); aarch64 FPCR bit 24 (FZ) via `mrs`/`msr fpcr`. Readback-asserted, not merely "we called the setter." | CIS2_SPEC_v0.2.md §1.3 | `denormal::pin_ftz_daz()`, called `src/main.rs:305` before any weight/decode arithmetic; adversarial unit test `ftz_daz_pinned_and_denormal_input_flushed` (`src/denormal.rs`), `black_box`-guarded so LLVM cannot fold the subnormal op away; passing on both ISAs in CI (`~/projects/claudius-maximus/state/reports/2026-08-28-E15c-verify.md` item 2). |
| 2 | **Round-to-nearest-even (RNE) everywhere, no other rounding mode set.** | CIS2_SPEC_v0.2.md §1.2 | IEEE-754 default; not independently toggled anywhere in `src/`. |
| 3 | **No FMA contraction anywhere** — every `a*b + c` is two separate, separately-rounded operations; `f32::mul_add` is never called. | CIS2_SPEC_v0.2.md §1.4 | `src/math.rs:40-58` (`dot_seq`/`sum_seq`, `let p = a[i]*b[i]; acc = acc + p;` as two statements). Mechanical grep gate `tests/no_mul_add.rs` + disassembly gate `scripts/no_fma_gate.sh` (`objdump` for `vfmadd\|vfnmadd\|vfmsub\|vfnmsub\|fmadd\|fmsub`). Adversarially rebuilt with `RUSTFLAGS="-C target-cpu=native"` on FMA-capable hardware: 0 FMA instructions, digest unchanged (`2026-08-28-E15c-verify.md` item 3). Re-confirmed at v0.2 across a 20-cell `{opt-level 0,1,2,3,s} × {generic,native} × {x86_64,aarch64}` matrix, 0 FMA in every cell (`docs/E15d_v0.2_DIGESTS.md`, run 33195649908). |
| 4 | **Scalar left-to-right reductions** — every dot product and sum (matvec rows, RMSNorm sum-of-squares, softmax denominator, V-mix) folds strictly in index order `0..n-1`; no pairwise tree, no chunking, no reassociation. | CIS2_SPEC_v0.2.md §5.1, §5.3 | `dot_seq` (`src/math.rs:40`), `sum_seq` (`src/math.rs:52`) — plain `for` loops, scalar accumulator. Regression test `dot_seq_is_order_sensitive_by_design` (`src/math.rs:437`) asserts the pinned order specifically: dotting `[1e8, 1.0, -1e8]` against `[1.0, 1.0, 1.0]` in this exact order gives `0.0_f32` (the `1.0` term is lost to rounding against the `1e8` partial sum); any other order gives a different, nonzero answer. |
| 5 | **Pinned polynomial transcendentals with hex coefficients, and no platform libm call** — `exp`/`sin`/`cos`/`ln` are libm-free Cephes-pattern range-reduction + fixed-degree Horner polynomials over hex-pinned `f32` coefficient bit patterns; `rsqrt` and `sqrt`/`/` use the IEEE-754-mandatory correctly-rounded hardware ops instead (no table needed, since any conformant IEEE-754 implementation already agrees bit-for-bit on these). | CIS2_SPEC_v0.2.md §6.1–§6.5 | `exp_pinned` (`src/math.rs:100`), `ldexp_exact` (`src/math.rs:139`), `sin_pinned`/`cos_pinned` (`src/math.rs:206`/`218`), `ln_pinned` (`src/math.rs:272`) with `frexp_exact` (`src/math.rs:259`) and coefficients `LOG_SQRTHF`/`LOG_Q1`/`LOG_Q2`/`LOG_P[0..9]` (`src/math.rs:240-254`); `rsqrt_cr` (`src/math.rs:66`). Coefficient-table digest `table_digest()` (`src/math.rs:342`) prints `465d358ccd63721256dbd2abbc77ad5de755adf3230635f95b12b1727dfa1ea3` at v0.2 (spec §6.6). Zero calls to platform libm `exp`/`sin`/`cos`/`ln` confirmed (`2026-08-28-E15c-verify.md` item 2: "sidesteps the classic glibc-x86-vs-aarch64 transcendental divergence bug class entirely, by construction"). |
| 6 | **Pinned general `ln(theta)` for RoPE `inv_freq`, not a bare per-model literal** — `inv_freq[i] = exp_pinned(-(2i/head_dim)·ln_pinned(rope_theta))`, `ln_pinned` valid for any `rope_theta` read from `config.json`, not hardcoded to one value. | CIS2_SPEC_v0.2.md §7.1 (new in v0.2, closes v0.1 §14.1) | `src/main.rs:345` (`let ln_theta = math::ln_pinned(rope_theta as f32);`), `rope_theta` read at `src/main.rs:331`, `inv_freq` loop `src/main.rs:346-354`, digest `inv_freq_table_digest` computed `src/main.rs:358-365`. Validated on SmolLM2-135M (`rope_theta=100000`, digest bit-identical to the v0.1 literal-based construction — `docs/E15h_REFACTOR_v0.2_RESULT.md`) and Qwen2.5-0.5B (`rope_theta=1000000`, `docs/E15d_bc_RESULT.md`). |
| 7 | **Raw-byte digest binding** — the witness chain (`CIS2_REF`) folds the two transcendental-table digests and the three artifact hashes as their **raw 32 bytes**, not their 64-character hex-ASCII rendering, and the coefficient-table digest and `inv_freq` table digest are now inputs to `CIS2_REF` itself, not merely printed alongside it. | CIS2_SPEC_v0.2.md §12.1 (new in v0.2, closes v0.1 §12.1/§14.2/§14.3) | `sha256_file` returns `[u8; 32]` (`src/main.rs:245`); witness seeding order `table_digest` then `inv_freq_table_digest` then the three artifact hashes then prompt tokens (`src/main.rs:511-519`, spec Appendix A); display-only hex helper (`src/main.rs:585-586` via local `hex::encode`). |

Everything else — memory layout, tiling, thread/SIMD strategy, instruction selection — is free
(spec §1.4/§15 item 6 is silent on it) as long as the pinned reduction order and transcendental bit
patterns match exactly; no optimized (SIMD) kernel has yet been built against this contract (§8,
limitations).

## Mechanism

CIS-1's mechanism (`03_semantics.md`) is that integer addition is associative, so pinning the
*type system* (bounded accumulators) is sufficient; CIS-2 cannot use that shortcut, because fp32
addition is not associative. CIS-2's mechanism is instead the conjunction of the seven gates above:
gate 4 removes reduction-order freedom, gate 3 removes the FMA-vs-separate-rounding degree of
freedom, gates 5–6 remove transcendental-routing freedom (by avoiding platform libm entirely
rather than hoping two libms agree), gate 1 removes the x86-vs-aarch64 hardware default divergence
in denormal handling, and gate 7 makes the receipt bind the exact transcendental coefficients used,
not just the resulting logits — so a receipt holder can detect a differently-tabled but
coincidentally-similar implementation, not just a differently-computed one. Two of the six IEEE-754
basic operations (`sqrt`, `/`) need no pinning at all, because they are mandatory-correctly-rounded
by the standard itself (spec §1.6) — the same is not true of `exp`/`sin`/`cos`/`ln`, which the
standard leaves at merely faithfully-rounded, and that gap is precisely why gates 5–6 exist.

---

**Source map**
- Definition and full-logit-vector digest scope: `docs/CIS2_SPEC_v0.2.md` §12.1, §13.2.
- FTZ/DAZ, RNE, no-FMA: spec §1.2–§1.5.
- Reduction order: spec §5.1, §5.3.
- Transcendentals and coefficient digest: spec §6.1–§6.6.
- RoPE `ln_pinned` generalization: spec §7.1, §16 (v0.2 changelog).
- Raw-byte witness binding: spec §12.1, §14.2, §14.3 (closed gaps).
