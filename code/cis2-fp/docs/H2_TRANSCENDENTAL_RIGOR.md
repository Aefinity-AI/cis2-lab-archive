# H2 — Transcendental accuracy characterization (closes the "pinned by fiat" gap)

**Status: characterization only. No coefficients in `src/math.rs` were changed.
`table_digest()` is unaffected.**

## Problem

`docs/paper/03_contract.md` flags CIS-2's pinned polynomial transcendentals
(`exp_pinned`, `sin_pinned`, `cos_pinned`, `ln_pinned`, §6.2–§6.5) as
justified "by fiat": the spec pins exact f32 coefficients and states they
are "Cephes-pattern" but never quantifies error vs. a correctly-rounded
reference. A reviewer can reasonably ask "why these coefficients, and how
wrong are they?" This memo answers that with measured numbers. It does
**not** change any coefficient — CIS-2's determinism claim never depended
on these functions being *accurate*, only on their being *pinned* (bit-for-bit
reproducible pure-fp32 arithmetic, verified by `table_digest()`). This memo
adds the missing accuracy characterization on top of that.

## Method

1. Ported every pinned function (`exp_pinned`, `sin_pinned`, `cos_pinned`,
   `ln_pinned`, `rsqrt_cr`, `reduce_2pi`, `ldexp_exact`, `frexp_exact`) from
   `src/math.rs` line-for-line into Python using `numpy.float32` at every
   intermediate step, so every op has the same round-to-nearest-even
   single-rounding semantics as the Rust source (verified by spot-checking
   against `src/math.rs`'s own unit tests: `exp(0)==1`, `exp(1)≈e`,
   `rsqrt(64)==0.125`, `ln(100000)`/`ln(1000000)` agreeing with the Rust
   `#[test]`s' host-libm comparisons within the same 2e-6 tolerance).
2. Built a correctly-rounded fp32 oracle: `mpmath` at 60 decimal digits
   computes the true real value, then a candidate-neighbor search
   (checking the nearest 5 fp32 grid points against the arbitrary-precision
   value) picks the exact IEEE-754 correctly-rounded fp32 result. This is
   the reference every "ULP error" and "relative error" number below is
   measured against.
3. Determined the actual argument domain each function sees during a
   SmolLM2-135M / Qwen2.5-0.5B forward pass by reasoning from the ops
   (not by re-instrumenting the model, since the domains follow
   analytically from the spec's own pinned constants):
   - `exp_pinned`: (a) softmax args, always `<= 0` post max-subtract
     (§9.3); (b) `silu_pinned`'s `-x`, x an MLP gate pre-activation,
     empirically bounded for these model scales; (c) RoPE's
     `inv_freq[i] = exp_pinned(-(2i/head_dim)*ln_pinned(theta))`
     (§7.2), exponent in `[-ln(theta), 0]`, i.e. `[-13.9, 0]` for
     `theta` up to `1e6`. Padded scan domain: `x in [-40, 40]`.
   - `ln_pinned`: called exactly once per model load, on `x = rope_theta`
     only (§6.5.2 — "not a per-decode-step hot path"). The two config
     values actually pinned in this spec's test vectors are `100000.0`
     (SmolLM2-135M) and `1000000.0` (Qwen2.5-0.5B).
   - `sin_pinned`/`cos_pinned`: `reduce_2pi` unconditionally folds any
     input to `r in [-pi, pi]` before the Taylor polynomial runs, so the
     *polynomial's* domain is always `[-pi, pi]` — but `reduce_2pi` itself
     is not error-free (see Finding below), so the *end-to-end* function's
     accuracy depends on the raw input `x`, which is the RoPE angle
     `pos * inv_freq[i]` (§7.3). §13's pinned decode fixes `pos in [0, 19]`
     (20 positions, prompt + 16 generated tokens) and `inv_freq[i] in (0, 1]`
     (i=0 gives exactly 1.0; it only shrinks from there), so the actual
     angle domain exercised by the two pinned test vectors is the exact
     40-point-by-32-frequency grid `{pos * inv_freq[i] : pos in 0..=19,
     i in 0..32}` for each of `theta = 100000.0` and `theta = 1000000.0`.
4. Measured max ULP error (IEEE-754 total-order distance in the fp32
   grid) and max relative error, both over the padded continuous-scan
   domain (robustness check) and over the exact discrete grid the two
   pinned test vectors actually use (the number that matters for §13's
   digests).

Full working script:
`<tmp>/<session>/scratchpad/oracle.py`
and `exact_domain.py` (not checked into this repo — scratch analysis only;
the numbers below are the citable artifact).

## Results

| function | domain measured | max ULP | max rel. error |
|---|---|---|---|
| `rsqrt_cr` | all finite x>0 | **0 (correctly rounded by construction)** | 0 |
| `exp_pinned` | x∈[-40,40] (softmax/SiLU/RoPE-exponent, padded) | 1 | 1.19e-7 |
| `exp_pinned` | exact RoPE inv_freq exponents, SmolLM2 θ=1e5 | 1 | — |
| `exp_pinned` | exact RoPE inv_freq exponents, Qwen θ=1e6 | 1 | — |
| `ln_pinned` | x∈[1e3,2e6] (padded around rope_theta constants) | 1 | 7.85e-8 |
| `ln_pinned` | x=100000.0 (SmolLM2 θ, exact §13 value) | **0** | 0 |
| `ln_pinned` | x=1000000.0 (Qwen θ, exact E15d(bc) value) | **0** | 0 |
| `sin_pinned` | exact RoPE angle grid, SmolLM2 θ=1e5, pos≤19 | **1104** | 1.00e-4 |
| `cos_pinned` | exact RoPE angle grid, SmolLM2 θ=1e5, pos≤19 | **398** | 4.19e-5 |
| `sin_pinned` | exact RoPE angle grid, Qwen θ=1e6, pos≤19 | **71** | 4.97e-6 |
| `cos_pinned` | exact RoPE angle grid, Qwen θ=1e6, pos≤19 | **398** | 4.19e-5 |
| `sin_pinned`/`cos_pinned` | x∈[0,19] continuous (superset of the grid above) | up to 12355 | 8.17e-4 |
| `sin_pinned`/`cos_pinned` | x∈[0,8192] (`max_position_embeddings`, NOT the pinned test vector — informative only) | up to ~1.08e7 | 0.58 |

`rsqrt_cr`, `exp_pinned`, `ln_pinned` are all correctly-rounded-or-1-ULP
over every domain tested: essentially as good as a fp32 transcendental
implementation gets, and the "by fiat" gap is closed for these three —
their pinned coefficients reproduce the correctly-rounded fp32 value (or
its immediate neighbor) everywhere the model actually calls them.

## FINDING: `sin_pinned`/`cos_pinned` have a real, quantified accuracy gap — determinism is unaffected

`sin_pinned`/`cos_pinned` exceed the 4-ULP "alarming" threshold specified
in the task, even restricted to the exact grid the two pinned test
vectors use (max 1104 ULP / 1.00e-4 relative, SmolLM2 sin). Root cause,
confirmed by direct inspection (see "DEBUG worst case" in the oracle
script output): `reduce_2pi`'s `x - k*TWO_PI_HI - k*TWO_PI_LO` two-constant
range reduction is done entirely in f32 arithmetic (per this spec's own
no-FMA, single-precision-only constraint, §3.2). This is classic
catastrophic cancellation: subtracting two O(x) quantities that agree to
several leading digits leaves a result whose absolute error is
`O(k * eps_f32 * TWO_PI_HI)`, i.e. it grows *linearly with the position
index* even for small `x` (observed already at `pos≈19`, `k=3`). This is
a known limitation of doing Payne–Hanek-style range reduction with only
two f32-precision constants rather than a double-double or arbitrary-
precision 2π expansion (which the "no-FMA, fp32-everywhere" determinism
requirement of this spec structurally rules out using f64 for). The
polynomial itself (Taylor to degree 21, evaluated on the already-reduced
`r`) is not the source of the error — it is far more accurate than the
reduction step feeding it.

**This is an accuracy concern, not a determinism concern.** The function
is still exactly bit-reproducible (pure fp32 arithmetic, no hardware
transcendental instruction, no undefined behavior) — running it twice on
any conformant IEEE-754 fp32 ISA gives identical bits. What is *not* true
is that those bits are close to the mathematically correct `sin`/`cos`
value at the ~1e-4 relative-error level for the SmolLM2 test vector, and
the error grows worse (0.58 relative, i.e. useless) if the pinned decode
length were extended toward `max_position_embeddings = 8192`. **§13's
16-token pinned test vector is far short of where this becomes severe**,
but any future extension of decode length in this spec family should
re-run this characterization before assuming the current 21-term Taylor
polynomial is adequate.

## Statement for the spec (added as §6.7)

> Determinism does not depend on correctness of these values, only on
> their being pinned (fixed bit-exact fp32 arithmetic, verified by
> `table_digest()`, §6.6); accuracy vs. IEEE-754 correctly-rounded is
> bounded, per function, over the domain this spec's pinned test vectors
> actually exercise, by: `rsqrt_cr` 0 ULP (correctly rounded by
> construction); `exp_pinned` ≤1 ULP; `ln_pinned` 0 ULP at the two pinned
> `rope_theta` values (≤1 ULP over a padded scan); `sin_pinned`/
> `cos_pinned` up to 1104 ULP / 1.00e-4 relative (SmolLM2, pos≤19),
> caused by f32-only range-reduction cancellation, not polynomial
> inadequacy — see `docs/H2_TRANSCENDENTAL_RIGOR.md` for the full
> derivation and measurement method.
