# CIS-2 — Canonical Floating-Point Semantics for fp32 Transformer Inference, v0.1

**Status: DRAFT, not frozen.** Published 2026-10-16 as part of the CIS-2 archive. This document is normative for the scope stated below: a
conforming, from-spec-text-only clean-room implementation MUST reproduce
`CIS2_REF` (§12) and the `inv_freq table_digest` (§8.3) bit-for-bit on the
pinned test vectors of §13, on both x86-64 and aarch64.

This spec exists because two prior clean-room attempts against prose-only
predecessors of this document (`verify/SPEC_GAPS.md`, E15e) each had to
*invent* choices this document now pins by fiat: digest byte encoding
(hex-ASCII vs. raw bytes, integer width, hash order), the transcendental
algorithm (which route, which coefficients), and the RoPE `inv_freq`
construction (which was, at the time, computed by an unpinned host
`f64::powf` call). Every choice below is taken directly from the reference
implementation at a fixed commit (see Appendix A for exact
`file:line` citations); this document's body is written to be
implementable **without** access to `src/` — Appendix A is provided only
so a reviewer can audit that this spec did not silently diverge from what
the reference actually computes.

**What conformance buys:** bit-identical fp32 decode of
`HuggingFaceTB/SmolLM2-135M` given the pinned prompt (§13), reproducible by
an independent from-spec-text implementation, on any ISA that supports
IEEE-754 binary32 arithmetic with FTZ/DAZ control (x86-64 MXCSR, aarch64
FPCR.FZ). This is deliberately narrower than CIS-1 (§1 of
`~/projects/alice-aegis/docs/CIS-1_SPEC_v1.0.md`): floating-point addition
is not associative, so this spec does not claim "any reduction order is
safe" — it claims exactly one pinned reduction order, one pinned
transcendental route, and one pinned digest encoding are collectively
sufficient for bit-identity, and states each of them exactly.

---

## 0. Scope and non-goals (normative)

This spec covers exactly one (model, prompt, decode-length) tuple:
`HuggingFaceTB/SmolLM2-135M`, prompt `"Once upon a time"`, 16 greedy-decoded
tokens, fp32 compute, bf16-on-disk weights. It does **not** claim:

- General correctness of the pinned transcendental polynomials outside the
  input ranges actually exercised by this decode (§6.5, §14.4).
- A general, theta-independent RoPE construction — §7's `LN_THETA` constant
  is pinned **only** for `rope_theta = 100000.0`; a conforming
  implementation for any other theta needs a general pinned-`ln` procedure,
  which this version does not define (§14.3, this is an acknowledged gap,
  not resolved here).
- Cross-framework agreement (vs. PyTorch/`transformers`) — §14.5 the m1.5
  oracle comparison is evidence of correctness, not a conformance
  requirement; CIS-2 conformance is defined relative to this document's own
  bits, not to any third-party framework's output.
- Seeded/temperature sampling — decode is greedy-only (argmax every step),
  matching CIS-1's own non-goal (CIS-1 §10).
- Anything about `verify/` (a *different*, independently-written clean-room
  implementation built by *not* reading `src/`, used only to find gaps in
  earlier drafts of this document — it is evidence this spec was tested
  against, not itself normative).

## 1. Floating-point environment (normative)

1.1. **Format**: IEEE-754 binary32 (`f32`) for all decode-path compute.
Weights are stored on disk as `bfloat16` and widened to `f32` per §4.2
before any arithmetic.

1.2. **Rounding mode**: round-to-nearest-even (RNE), the IEEE-754 default,
for every basic operation (`+`, `-`, `*`, `/`, `sqrt`). No other rounding
mode is set at any point in the decode path. Nothing in this spec changes
the FPU/SIMD rounding-mode control bits from their IEEE-754 default.

1.3. **FTZ/DAZ MUST be pinned on, on every ISA, before any decode-path fp32
arithmetic runs:**
   - x86-64: MXCSR bit 15 (FTZ) and bit 6 (DAZ) both set to 1, via direct
     read-modify-write of the MXCSR register (not the deprecated
     `_MM_SET_*` wrapper macros). A conforming implementation MUST assert
     (readback, not just "we called the setter") that both bits are 1
     before proceeding.
   - aarch64: FPCR bit 24 (FZ) set to 1, via `mrs`/`msr fpcr`. aarch64 has
     no separate DAZ control; FZ alone flushes both denormal inputs and
     denormal outputs for scalar and Advanced SIMD binary32/binary64
     arithmetic. FPCR bit 19 (FZ16, half-precision flush-to-zero) is left
     at its architectural default (this reference never uses fp16) — do
     not set it. A conforming implementation MUST assert (readback) that
     FZ is 1 before proceeding.
   - Any other ISA: undefined by this version of the spec; a conforming
     implementation MUST refuse to run (hard compile-time or run-time
     error) rather than silently proceed without an equivalent control.
   - **Adversarial self-test (MUST run and pass before decode)**: with
     FTZ/DAZ pinned, `f32::MIN_POSITIVE (2^-126) * 1.0e-10` MUST equal
     exactly `+0.0` (not a subnormal), and the smallest positive subnormal
     bit pattern `0x00000001` added to `+0.0` MUST also equal exactly
     `+0.0`. (This must be checked with the operands passed through an
     optimization barrier — e.g. Rust's `std::hint::black_box` — so the
     compiler cannot fold the arithmetic away and mask a broken pin.)

1.4. **No FMA contraction, anywhere, in the reference.** Every
multiply-then-add in this spec is defined as **two separate, separately
RNE-rounded operations**: compute the product, round to `f32`; then add,
round to `f32` again. A single fused `a*b+c` with one rounding step is
**non-conforming** even though it may be "more accurate" — it produces
different bits. In Rust terms: never call `f32::mul_add`; write `a*b + c`
as two statements/expressions, which LLVM does not auto-fuse absent an
explicit fast-math flag Rust does not provide. A conforming implementation
in any language MUST mechanically verify (e.g., disassemble the release
binary and grep for `vfmadd*`/`vfnmadd*`/`vfmsub*`/`vfnmsub*`/`fmadd`/
`fmsub` on the target ISA) that the emitted machine code contains zero
fused multiply-add instructions on the decode path.

1.5. **No fast-math, no reassociation.** The compiler MUST NOT be given
any flag that licenses reassociating floating-point expressions, assuming
no NaN/Inf, or substituting approximate reciprocal/rsqrt hardware
instructions (e.g. `-ffast-math`, `-Ofast`, `-freciprocal-math`). This
spec's reduction orders (§5) are only bit-determining if the compiler
computes exactly the sequence of operations stated, in the stated order.

1.6. **Division and sqrt**: ordinary IEEE-754 `/` and `sqrt` (both
mandatory-correctly-rounded operations under IEEE-754), never a
reciprocal-approximation instruction (x86 `rcpps`/`rsqrtps`, ARM
`frecpe`/`frsqrte`) and never a library "fast inverse sqrt" trick. Any
conformant IEEE-754 binary32 `sqrt`/`/` implementation on any ISA produces
identical bits for identical inputs, by the standard itself — this is the
one part of the arithmetic this spec does not need to additionally pin.

## 2. Model artifact (normative)

2.1. **Source**: Hugging Face repo `HuggingFaceTB/SmolLM2-135M`, files
fetched from the public `resolve/main/` URLs (no authentication required,
repo is public). No git revision/commit hash is pinned beyond content —
the artifact is identified **only** by the sha256 hashes below, which is
strictly stronger than a mutable branch ref:

| file | sha256 |
|---|---|
| `model.safetensors` | `80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1` |
| `config.json` | `1d556eab73b69c7f11f64c557a2f9c6f440bd4c6b89bb2584a6b498c92603843` |
| `tokenizer.json` | `9ca9acddb6525a194ec8ac7a87f24fbba7232a9a15ffa1af0c1224fcd888e47c` |

A conforming implementation MUST verify all three sha256 hashes before use
and MUST fail loudly (not silently proceed) on mismatch.

2.2. **Architecture parameters**, taken from `config.json` (a conforming
implementation MUST read these from the file, not hardcode them, but their
pinned values for this artifact are, for the reader's convenience):

| field | value |
|---|---|
| `hidden_size` | 576 |
| `intermediate_size` | 1536 |
| `num_hidden_layers` | 30 |
| `num_attention_heads` | 9 |
| `num_key_value_heads` | 3 |
| `hidden_act` | `silu` |
| `rms_norm_eps` | `1e-05` (f64 in JSON; §2.3 pins its f32 cast) |
| `rope_theta` | `100000` (`100000.0`) |
| `rope_interleaved` | `false` |
| `max_position_embeddings` | 8192 |
| `tie_word_embeddings` | `true` |
| `torch_dtype` | `bfloat16` |
| `vocab_size` | 49152 |

Derived: `head_dim = hidden_size / num_attention_heads = 576/9 = 64`
(exact integer division); `group = num_attention_heads / num_key_value_heads
= 9/3 = 3` (GQA group size); `half = head_dim/2 = 32`.

2.3. **`rms_norm_eps` f32 cast**: the JSON value `1e-05` is parsed as an
IEEE-754 `f64` (`1.0e-5`), then cast to `f32` via a single RNE rounding
(Rust `as f32`, equivalent to any IEEE-754-conformant `f64`→`f32`
narrowing conversion). Pinned bit pattern:

```
EPS_F32 = 0x3727C5AC   (== (1.0e-5f64) as f32)
```

2.4. **`rope_theta` restriction (normative for this version)**: this
version's RoPE construction (§7) is defined **only** for
`rope_theta == 100000.0` exactly (`f64` equality against the JSON-parsed
value). A conforming implementation MUST assert this and refuse to run
(not silently substitute a general formula) if the loaded `config.json`
ever has a different `rope_theta` — see §14.3 for why this is a real,
acknowledged gap rather than an oversight.

2.5. **Tensor names and shapes** (row-major, `[out_features, in_features]`
for every linear layer, matching PyTorch's `nn.Linear.weight` layout — a
matvec is `y[o] = Σ_i w[o,i]·x[i]`, §5.1):

```
model.embed_tokens.weight                              [vocab, hidden]
model.layers.{i}.input_layernorm.weight                [hidden]                for i in 0..30
model.layers.{i}.post_attention_layernorm.weight       [hidden]
model.layers.{i}.self_attn.q_proj.weight               [hidden, hidden]
model.layers.{i}.self_attn.k_proj.weight               [n_kv_heads*head_dim, hidden]
model.layers.{i}.self_attn.v_proj.weight               [n_kv_heads*head_dim, hidden]
model.layers.{i}.self_attn.o_proj.weight               [hidden, hidden]
model.layers.{i}.mlp.gate_proj.weight                  [inter, hidden]
model.layers.{i}.mlp.up_proj.weight                    [inter, hidden]
model.layers.{i}.mlp.down_proj.weight                  [hidden, inter]
model.norm.weight                                      [hidden]
```

There is **no** separate `lm_head.weight` tensor in this checkpoint
(confirmed by safetensors header inspection: 272 tensors total, all
`BF16`, no `lm_head.*` name present) — this matches
`tie_word_embeddings: true`. The LM head matmul (§11) reuses
`model.embed_tokens.weight` directly as the `[vocab, hidden]` output
projection matrix; no separate weight is loaded or derived for it.

Every tensor's on-disk dtype is `BF16` (2 bytes/element, little-endian
16-bit pattern per element, raw `safetensors` payload bytes taken two at a
time as `u16::from_le_bytes`). Every tensor MUST be widened per §4.2
before use; no tensor is used in bf16 form at compute time.

## 3. Tokenizer, prompt, and decode protocol (normative)

3.1. **Tokenizer**: the `tokenizer.json` file shipped with the checkpoint
(sha256 above), loaded as a complete, self-contained HuggingFace
`tokenizers`-format tokenizer (BPE-family; the exact merge/vocab table is
entirely contained in this one file — no external vocab/merges files, no
additional special-token config beyond what `tokenizer.json` itself
specifies).

3.2. **Prompt**: the literal ASCII string `Once upon a time` (no
leading/trailing whitespace beyond what is written here, no chat template
applied, no system prompt, no BOS/EOS token added or implied by any
wrapper). This is raw next-token completion, not chat-formatted.

3.3. **BOS/special-token handling**: tokenization MUST be performed with
`add_special_tokens = false` (i.e. the tokenizer's raw BPE encode of the
prompt string only — no BOS, no EOS, no any other special token
prepended/appended). Pinned result:

```
prompt_token_ids = [6403, 1980, 253, 655]     (4 tokens, u32)
```

3.4. **Decode protocol**: greedy only (argmax every step, §11.2), no
sampling, no temperature, no top-k/top-p. Exactly **16** tokens are
generated after the 4-token prompt, unconditionally — **EOS is not
checked and does not stop generation early** (matching CIS-1's own Tier-3
"EOS ignored" precedent, CIS-1 spec §8). Position indices are
`0, 1, 2, 3` for the 4 prompt tokens (prefill) and `4, 5, ..., 19` for the
16 generated tokens, assigned strictly in generation order (prompt
positions first, generated positions immediately following, no gaps, no
re-indexing).

3.5. **KV-cache equivalence (informative, not itself a conformance
requirement)**: the reference recomputes attention incrementally with a
KV cache that stores exactly the post-RoPE K/V vectors a from-scratch
full-recompute-per-step forward pass would produce (pure memoization, not
a reduction-order change). §14.5 independently confirms the cached and
oracle (full-recompute, no cache) paths agree. A conforming
implementation MAY use a KV cache or MAY recompute from scratch each
step; both are conformant iff they produce bit-identical logits — this
spec pins the *math*, not the caching strategy.

## 4. bf16 → fp32 widening (normative)

4.1. **Formula**: exact, lossless bit-shift, not a rounding conversion.
For a bf16 value with raw 16-bit pattern `b` (as loaded via
`u16::from_le_bytes` on the 2 little-endian bytes of that element in the
safetensors payload):

```
f32_bits = (b as u32) << 16
widened  = f32::from_bits(f32_bits)
```

This is exact because bf16's sign(1)/exponent(8)/mantissa(7) layout is
identical to fp32's top 16 bits with the low 16 mantissa bits defined as
zero — bf16's exponent field has the same width and bias as fp32's, so
there is no exponent range issue and no rounding decision to make. This
MUST be implemented as the literal bit operation above, not as a call
through any "convert" library routine that might round or normalize
differently.

4.2. Every tensor listed in §2.5 is widened element-wise via §4.1 at load
time before any arithmetic touches it. No tensor is used in bf16 form.

## 5. Numeric reduction primitives (normative)

5.1. **Sequential dot product.** For vectors `a`, `b` of equal length `n`:

```
acc = 0.0_f32
for i in 0..n:
    p   = a[i] * b[i]     # separate multiply, RNE-rounded to f32
    acc = acc + p          # separate add, RNE-rounded to f32
return acc
```

Strictly left-to-right, index order `0, 1, ..., n-1`. No pairwise tree, no
chunking, no reordering by magnitude. This is the **only** conforming
reduction order for every dot product and every "sum of products" loop in
this spec (matvec rows §5.2, attention score dot §9.2, V-mix §9.4).
`dot_seq` is order-sensitive by design: dotting `[1e8, 1.0, -1e8]` against
`[1.0, 1.0, 1.0]` in this order gives exactly `0.0_f32` (the `1.0` term is
lost to rounding against the `1e8` partial sum) — any other order gives a
different, nonzero answer; a conforming implementation MUST reproduce
`0.0_f32` on this specific input as a regression check.

5.2. **Matvec.** `y[o] = dot_seq(w[o, :], x)` for `o = 0..out_features`,
where `w[o, :]` is row `o` of the row-major `[out_features, in_features]`
weight tensor (§2.5). Each output element is one independent §5.1 dot
product; rows may be computed in any order or in parallel relative to
each other (row order does not affect any single row's bits), but each
row's own reduction MUST use §5.1's exact order.

5.3. **Sequential sum.** For a vector `a` of length `n` (used for
sum-of-squares in RMSNorm §8 and the softmax denominator §10):

```
acc = 0.0_f32
for i in 0..n:
    acc = acc + a[i]      # separate add, RNE-rounded to f32
return acc
```

Same left-to-right, no-reassociation rule as §5.1.

5.4. **Elementwise add** (residual connections, §9.5/§10.3): plain
`out[i] = a[i] + b[i]` for every `i`, one IEEE-754 add each, no reduction
involved.

## 6. Transcendental functions (normative)

There are two routes used, per the design memo's §3.3 distinction; this
spec pins both exactly.

### 6.1 rsqrt — route (a), correctly-rounded, no table

```
rsqrt(x) = 1.0_f32 / x.sqrt()
```

Composed from two IEEE-754-mandatory correctly-rounded operations
(`sqrt`, then `/`). Because both are mandatory-correctly-rounded under the
standard, **any** conformant IEEE-754 binary32 implementation on any ISA
produces identical bits for identical `x` — no coefficient table, no
digest, no pinning needed beyond "use the standard's `sqrt` and `/`, not
an approximate hardware reciprocal-sqrt instruction" (already stated in
§1.6). `rsqrt(64.0) == 0.125` exactly (`0x3E000000`) is a conformance
check.

### 6.2 exp — route (b), pinned Cephes-pattern polynomial

For `x` a finite `f32`:

1. If `x` is NaN, return NaN.
2. If `x > 88.0`, return `+Infinity`.
3. If `x < -88.0`, return `0.0`.
4. Range reduction: find integer `k` and remainder `r` such that
   `x ≈ k·ln(2) + r`, `|r|` small, via:
   ```
   t   = x * EXP_LOG2E          # x / ln(2), separate mul
   z0  = t + 0.5
   k   = floor(z0)               # k as f32, truncated toward -inf at z0
   kc1 = k * EXP_C1
   r0  = x - kc1
   kc2 = k * EXP_C2
   r   = r0 - kc2                 # two-part ln(2) split, Cephes pattern
   ```
5. Polynomial evaluation (Horner, strict left-to-right, descending
   coefficient index, no FMA):
   ```
   r2   = r * r
   poly = EXP_P[0]
   for i in 1..=5:
       poly = poly * r + EXP_P[i]
   m1     = poly * r2
   poly2  = m1 + r
   result = poly2 + 1.0
   ```
   (This computes `exp(r) ≈ 1 + r + r²·P(r)` with `P` the degree-5
   polynomial `EXP_P[0]·r⁵ + EXP_P[1]·r⁴ + ... + EXP_P[5]`.)
6. Reconstruct `exp(x) = 2^k · result` via **exact bit manipulation** of
   the `f32` exponent field (`ldexp_exact`, §6.2.1) — not a library
   `ldexp`/multiply-by-power-of-2-computed-as-a-float call.

Pinned coefficients (`f32` bit patterns, hex, big-endian digit order of
the 32-bit pattern as conventionally written — i.e. `0xSEEEEEEE MMMMMMM`
read as one `u32`):

```
EXP_LOG2E = 0x3FB8AA3B   (1/ln2)
EXP_C1    = 0x3F318000   (ln2 hi)
EXP_C2    = 0xB95E8083   (ln2 lo, negative)
EXP_P[0]  = 0x39506967
EXP_P[1]  = 0x3AB743CE
EXP_P[2]  = 0x3C088908
EXP_P[3]  = 0x3D2AA9C1
EXP_P[4]  = 0x3E2AAAAA
EXP_P[5]  = 0x3F000000   (== 0.5 exactly)
```

#### 6.2.1 `ldexp_exact(x, k)` — exact scale-by-power-of-2

```
if x == 0.0: return x
bits     = x.to_bits()
exp_bits = (bits >> 23) & 0xFF          # 8-bit biased exponent field
new_exp  = exp_bits + k                  # k is a signed integer
if new_exp <= 0:   return 0.0             # underflow — FTZ/DAZ (§1.3) governs anyway
if new_exp >= 0xFF: return (x.is_sign_negative() ? -Infinity : +Infinity)
new_bits = (bits & !(0xFF << 23)) | (new_exp << 23)   # replace exponent field only
return f32::from_bits(new_bits)
```
Sign and mantissa bits are untouched; only the 8-bit exponent field is
replaced. This is exact (no rounding) whenever the result stays in the
normal-or-flush range, which the `exp()` domain clamp (steps 2–3) and the
saturation branches above guarantee.

### 6.3 sin/cos — route (b), pinned Taylor series after 2π range reduction

Range reduction to `r ∈ [-π, π]` (2-part-π split, Cephes pattern, strict
left-to-right, no FMA):

```
k    = round(x / TWO_PI_HI)     # round-to-nearest integer, ties per IEEE round()
khi  = k * TWO_PI_HI
r0   = x - khi
klo  = k * TWO_PI_LO
r    = r0 - klo
```

```
TWO_PI_HI = 0x40C90FDA   (== 6.283185)
TWO_PI_LO = 0x347FF14D   (== 2.383651e-07; 2π − TWO_PI_HI, exact-in-f64 split)
```

`cos(x)`: Horner in `r² `, descending from the highest-degree coefficient,
strict left-to-right, no FMA:

```
r2   = r * r
poly = COS_COEF[10]
for i in 9 downto 0:
    poly = poly * r2 + COS_COEF[i]
return poly
```

`sin(x)`: identical structure with `SIN_COEF`, then one final multiply by
`r`:

```
r2   = r * r
poly = SIN_COEF[10]
for i in 9 downto 0:
    poly = poly * r2 + SIN_COEF[i]
return poly * r
```

Pinned coefficients (`1/(2n+1)!` for sin, `1/(2n)!` for cos, `n = 0..10`,
each independently rounded once to `f32` from the exact rational — not
copied from any specific published binary, but algorithmically identical
to the standard Taylor coefficients):

```
SIN_COEF[0..10] = 0x3F800000, 0xBE2AAAAB, 0x3C088888, 0xB9500D01,
                  0x3638EF1E, 0xB2D7322C, 0x2F30922E, 0xAB573FA0,
                  0x274A963A, 0xA317A4DA, 0x1EB8DC77

COS_COEF[0..10] = 0x3F800000, 0xBF000000, 0x3D2AAAAC, 0xBAB60B62,
                  0x37D00D02, 0xB493F27E, 0x310F76C9, 0xAD49CBAA,
                  0x29573F9E, 0xA53413C5, 0x20F2A15F
```

### 6.4 SiLU

```
silu(x) = x / (1.0 + exp_pinned(-x))
```
i.e.: `neg = -x`; `e = exp_pinned(neg)`; `denom = 1.0 + e` (separate add);
`return x / denom` (one IEEE-754-mandatory-correctly-rounded division, not
a reciprocal-multiply).

### 6.5 Table digest (informative binding, NOT part of the witness chain — see §14.6)

SHA-256 over the LE bytes of every pinned coefficient above, in this exact
declared order — `[EXP_LOG2E, EXP_C1, EXP_C2]`, then `EXP_P[0..6]`, then
`[TWO_PI_HI, TWO_PI_LO]`, then `SIN_COEF[0..11]`, then `COS_COEF[0..11]`,
each as 4 little-endian bytes of the `f32` bit pattern, concatenated, one
continuous SHA-256 stream:

```
table_digest = 0bf9257bc56c4588cb4003e1a105b60169e152222ec734811d0a58e66e1cdeca
```

This digest is printed by the reference (`table_digest=` line) but is
**not** folded into `CIS2_REF` (§12) — see §14.6 for why this is a real
gap, not a design choice to rely on.

## 7. RoPE (normative, restricted to `rope_theta = 100000.0`)

7.1. **`inv_freq` construction.** For `i = 0..head_dim/2` (32 values,
`head_dim = 64`):

```
frac    = (2*i as f32) / (head_dim as f32)     # e.g. i=0 -> 0.0, i=1 -> 2/64
neg_arg = -(frac * LN_THETA)                    # separate mul, then negate
inv_freq[i] = exp_pinned(neg_arg)                # §6.2, the SAME pinned exp
```

`LN_THETA` is a **pinned literal f32 bit pattern**, not computed by any
general logarithm procedure, and is valid **only** when `rope_theta ==
100000.0` (§2.4 mandates the loader assert this):

```
LN_THETA = 0x413834F1   (== 11.512925; the RNE-nearest f32 to ln(100000))
```

This is mathematically `inv_freq[i] = theta^(-2i/head_dim) =
exp(-(2i/head_dim)·ln(theta))`, evaluated with the pinned `exp_pinned`
polynomial (§6.2) rather than any host `pow`/`powf` call — this is a
deliberate, pinned choice (superseding an earlier, non-normative draft
that used host `f64::powf`; see §14.3/Appendix A for the exact history).

7.2. **`inv_freq` table digest.** SHA-256 over the LE bytes of each of the
32 `inv_freq` values, `f32.to_le_bytes()`, in index order `i = 0..32`, one
continuous stream:

```
inv_freq_table_digest = da9f6dcfde0425588815509e874515cdcd3d6b8818b6d0136590052e7bbf6f12
```

This digest is also **not** folded into `CIS2_REF` — printed separately
(§14.6).

7.3. **Per-position cos/sin table.** For a query/key head being rotated
at sequence position `pos` (a `usize`, cast to `f32` exactly — `pos` never
exceeds 19 in this spec's fixed 20-position decode, well within `f32`'s
exact-integer range):

```
for i in 0..half (half = head_dim/2 = 32):
    angle    = (pos as f32) * inv_freq[i]
    cos_v[i] = cos_pinned(angle)     # §6.3
    sin_v[i] = sin_pinned(angle)     # §6.3
```

7.4. **Rotation (rotate-half convention, `rope_interleaved = false`).**
Given a `head_dim`-length slice `head[0..head_dim]` for one attention
head, with `half = head_dim/2`:

```
for i in 0..half:
    x1 = head[i]
    x2 = head[i + half]
    t1 = x1 * cos_v[i]
    t2 = (-x2) * sin_v[i]
    out[i]        = t1 + t2
    t3 = x2 * cos_v[i]
    t4 = x1 * sin_v[i]
    out[i + half] = t3 + t4
head[0..head_dim] = out[0..head_dim]   # in place, after computing all `out`
```

This is applied to **every** query head (9 heads, each `head_dim=64`
slice of the 576-wide `q` vector) and **every** key head (3 heads, each
`head_dim=64` slice of the 192-wide `k` vector) independently, once per
decode step, at that step's `pos`. Values are never rotated more than
once (the KV cache stores post-RoPE `k`; §3.5).

## 8. RMSNorm (normative)

For input vector `x` of length `n = hidden = 576`, gain vector `weight`
of the same length, and `eps` = `EPS_F32` (§2.3):

```
for i in 0..n: sq[i] = x[i] * x[i]
ss   = sum_seq(sq)              # §5.3, strict left-to-right
mean = ss / (n as f32)          # one IEEE-754 division
inv  = rsqrt(mean + eps)        # §6.1: 1.0 / (mean+eps).sqrt()
for i in 0..n:
    scaled = x[i] * inv
    out[i] = scaled * weight[i]     # (x[i]*inv)*weight[i] — THIS association, not x[i]*(inv*weight[i])
```

The multiply order `(x[i] * inv) * weight[i]` (not `x[i] * (inv *
weight[i])`) is pinned explicitly: floating-point multiplication is not
associative under rounding, so these two orders can differ in the low bit
in general, even though no divergence from this specific reordering has
been observed on this model/prompt (§14.7 notes this as a low-severity but
real pinning, not an oversight).

Applied twice per layer (`input_layernorm` before attention, in §2.5's
naming `post_attention_layernorm` before the MLP) and once after the final
layer (`model.norm.weight`), all using the same procedure and the same
`eps`.

## 9. Attention (GQA, causal, per decode step) (normative)

Let `qh` range over `n_heads = 9` query heads, `kv_head = qh /
group` (`group = 3`) map each query head to its shared KV head (integer
division), `head_dim = 64`.

9.1. **Projections.** `q = matvec(q_proj, ln1, 576, 576)`; `k =
matvec(k_proj, ln1, 192, 576)`; `v = matvec(v_proj, ln1, 192, 576)`
(§5.2), where `ln1` is this layer's post-RMSNorm hidden state (§8). RoPE
(§7) is then applied in place to each of the 9 query-head slices of `q`
and each of the 3 key-head slices of `k`, at the current step's `pos`. `v`
is never rotated.

9.2. **Score.** For query head `qh` at position `pos`, against every
cached key position `j = 0..=pos` (causal: only positions ≤ current,
enforced by the KV cache containing exactly those positions, not by an
explicit mask value):

```
scale     = rsqrt(head_dim as f32)     # computed once: rsqrt(64.0) == 0.125 exactly
d         = dot_seq(q_head, k_j)        # §5.1, over the 64-dim head slice
scores[j] = d * scale                    # separate multiply, applied AFTER the dot
```

9.3. **Softmax** (`softmax_seq`, in place over `scores[0..=pos]`):

```
max_v = scores[0]
for v in scores[1..]:
    if v > max_v: max_v = v      # strict >, so the FIRST occurrence of the max wins ties
for v in scores: v = exp_pinned(v - max_v)     # §6.2
denom = sum_seq(scores)           # §5.3
for v in scores: v = v / denom     # elementwise division, NOT multiply-by-reciprocal
```

9.4. **V-mix.** For each output dimension `d = 0..head_dim`:

```
acc = 0.0_f32
for j in 0..=pos:
    p   = scores[j] * v_cache[j][kv_head][d]
    acc = acc + p                                # separate mul, separate add — same
                                                   # left-to-right order as §5.1, written
                                                   # as an explicit loop rather than a
                                                   # dot_seq call, but semantically identical
out_head[d] = acc
```

9.5. **Output projection and residual.** Concatenate all 9 `out_head`
slices into a 576-wide `attn_out`; `o = matvec(o_proj, attn_out, 576,
576)`; `h = elementwise_add(h, o)` (§5.4).

## 10. MLP / SwiGLU (normative)

Given this layer's post-`post_attention_layernorm` hidden state `ln2`
(576-wide):

```
gate = matvec(gate_proj, ln2, 1536, 576)     # §5.2
up   = matvec(up_proj,   ln2, 1536, 576)
for i in 0..1536:
    hid[i] = silu_pinned(gate[i]) * up[i]     # §6.4, then one separate multiply
down = matvec(down_proj, hid, 576, 1536)
h    = elementwise_add(h, down)                # §5.4
```

## 11. LM head and argmax (normative)

11.1. After the final layer, `hn = rmsnorm(h, model.norm.weight, eps)`
(§8). `logits = matvec(embed_tokens_weight, hn, vocab=49152, hidden=576)`
(§5.2), reusing the tied embedding matrix directly (§2.5) — no separate
weight, no transpose (the embedding table is already `[vocab, hidden]`,
the exact shape a `matvec` row-dot needs).

11.2. **Argmax**, strict left-to-right scan, first-occurrence-wins on
exact ties:

```
best_idx = 0
best_val = logits[0]
for idx, v in enumerate(logits):
    if v > best_val:          # strict >, never >=
        best_val = v
        best_idx = idx
next_token_id = best_idx as u32
```

## 12. Digest / receipt format (normative)

All digests are SHA-256 (32 raw bytes), rendered as lowercase hex (64
ASCII characters) when printed. There are **three separate, independently
computed** digests; none of them contains any of the others as a
sub-input except where explicitly stated.

12.1. **Witness chain / `CIS2_REF` digest.** One continuous
`Sha256::update()` stream (not a step-wise re-hash of
`running_digest || new_data` — this is a single hash object updated
repeatedly, then finalized once), fed in exactly this order:

1. `weights_sha256` — the **64-character lowercase hex ASCII string**
   (§2.1's `model.safetensors` digest), fed as its UTF-8/ASCII bytes (64
   bytes), **not** the raw 32-byte digest.
2. `tokenizer_sha256` — same encoding, the `tokenizer.json` hex string (64
   ASCII bytes).
3. `config_sha256` — same encoding, the `config.json` hex string (64
   ASCII bytes).
4. Every prompt token id, in order, each as **`u32` little-endian, 4
   bytes** (`t.to_le_bytes()`) — 4 tokens × 4 bytes = 16 bytes total for
   this prompt.
5. For each of the 16 decode steps, in step order (`step = 0..16`):
   a. The **full fp32 logit vector for this step** (49152 entries, in
      vocab-index order), each entry's raw bit pattern as `u32`
      little-endian (`v.to_bits().to_le_bytes()`), concatenated —
      49152 × 4 = 196608 bytes per step. This is the logit vector
      **before** this step's argmax pick (i.e., the vector argmax was
      just computed against), not the vector for the *next* position.
   b. The chosen `next_token_id` for this step, as **`u32` little-endian,
      4 bytes**.

Finalize once after all 16 steps; the resulting 32-byte digest, hex
encoded, is `CIS2_REF`:

```
CIS2_REF = ba88708bf4159a4057d4eef727820ebc5ce1744ae334bfe0cc0776e03509dd0f
```

printed as `CIS2_REF digest=ba88708b... prompt_toks=4 gen_toks=16
dtype=fp32`.

12.2. **Argmax-token digest.** A **separate** `Sha256` instance (not
derived from or continuing the witness chain above), fed the LE `u32`
bytes of every token id in `prompt_token_ids ++ [16 generated token ids]`
(20 tokens total, in that order, prompt first), one continuous stream,
finalized once:

```
argmax_digest = 0b9c8f3ac90d0b9cd5f1719ac327dca1fc639fd87468305fccebbe3d56f67aff
```

12.3. **Table digests** (§6.5, §7.2) are computed and printed
independently of both digests above and are **not** inputs to either.

12.4. **Determinism check (MUST).** The reference computes the entire
decode (§3.4) **twice** in the same process (`run1`, `run2`) and MUST
assert all three of: `witness_digest_run1 == witness_digest_run2`,
`argmax_digest_run1 == argmax_digest_run2`, and
`token_ids_run1 == token_ids_run2`, before printing any result — this is
the same-host determinism bar, a precondition for the stronger cross-ISA
claim (§13.2), not itself the interesting claim.

## 13. Test vectors (normative)

13.1. **Full run, prompt `"Once upon a time"`, 16 greedy tokens:**

```
weights_sha256   = 80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1
config_sha256    = 1d556eab73b69c7f11f64c557a2f9c6f440bd4c6b89bb2584a6b498c92603843
tokenizer_sha256 = 9ca9acddb6525a194ec8ac7a87f24fbba7232a9a15ffa1af0c1224fcd888e47c
prompt_token_ids = [6403, 1980, 253, 655]
generated_token_ids (16, in order) =
    [28, 665, 436, 253, 1838, 8180, 3365, 14176, 30, 2306, 4161, 281, 253, 2066, 2291, 351]
table_digest           = 0bf9257bc56c4588cb4003e1a105b60169e152222ec734811d0a58e66e1cdeca
inv_freq_table_digest  = da9f6dcfde0425588815509e874515cdcd3d6b8818b6d0136590052e7bbf6f12
argmax_digest          = 0b9c8f3ac90d0b9cd5f1719ac327dca1fc639fd87468305fccebbe3d56f67aff
CIS2_REF (witness_digest) = ba88708bf4159a4057d4eef727820ebc5ce1744ae334bfe0cc0776e03509dd0f
```

13.2. **Cross-run/cross-ISA conformance bar.** All of §13.1's values MUST
reproduce bit-for-bit: (a) across two sequential runs in the same process
(§12.4); (b) across two separate OS process invocations on the same host;
(c) across x86-64 and aarch64, same source, unmodified, both with §1.3's
FTZ/DAZ pin actually in effect (verified by the adversarial self-test,
§1.3) and §1.4's zero-FMA gate passing (disassembly check).

13.3. **Step-0 full-logit-vector spot check (informative, not part of
`CIS2_REF`)**: an independent oracle comparison
(`docs/E15b_m1p5_CORRECTNESS.md`, this branch) against
`torch`/`transformers` fp32 forward pass of the same checkpoint found, at
generation step 0 (right after prefill, before the first generated
token), across all 49152 logits: `max_abs_diff ≈ 8.965e-05` (vocab index
40082: this reference `5.486028671264648`, oracle
`5.486118316650391`), `max|logit| ≈ 22.531156539916992`, relative diff
`≈ 3.98e-06` — evidence of *correctness* (this is a valid forward pass),
not evidence of bit-identity with `torch` (which this spec never claims;
`torch` uses its own BLAS reduction order and libm, out of scope). This
spec does not define a `--dump-step0` flag as part of its normative
surface; the debug env-var hook (`CIS2_DUMP_STEP0_LOGITS`, Appendix A)
that produced this comparison is informative tooling, not part of
conformance.

## 14. Known gaps and internal inconsistencies (informative — read before treating this as complete)

14.1. **`rope_theta = 100000.0`-only.** §7's `LN_THETA` is a bare pinned
literal, valid for exactly one theta value; there is no general pinned
`ln()` procedure in this version. A conforming implementation for a
different SmolLM2/Llama-family checkpoint with a different `rope_theta`
cannot be built from this document alone. This is the single most
significant scope limitation of v0.1.

14.2. **Digest byte encoding for artifact hashes is hex-ASCII, not raw
bytes — a real, easy-to-miss pinning.** §12.1 step 1–3 feeds the
64-character hex **string's** ASCII bytes into the witness hash, not the
32 raw digest bytes. Nothing about the word "hash" or "digest" in prose
would tell an implementer this; it is only recoverable by reading
`src/main.rs`'s `sha256_file` (returns a `String`) and its call site
(`witness.update(weights_sha256.as_bytes())`) — Appendix A cites the exact
lines. This was the literal ambiguity `verify/SPEC_GAPS.md` item 1
flagged as unresolved; this document resolves it by fiat, matching the
actual reference.

14.3. **Neither table digest (§6.5, §7.2) is bound into `CIS2_REF`.** The
reference computes and prints `table_digest` and
`inv_freq_table_digest` entirely independently of the witness chain —
`CIS2_REF` binds only the three artifact-file hashes, the prompt token
ids, and the per-step logit vectors + chosen tokens. **This means a
receipt holder cannot detect, from `CIS2_REF` alone, whether a verifier
used the exact pinned polynomial/RoPE-table coefficients of §6/§7 or some
other transcendental implementation that happens to produce the same
logits** (or, worse, silently different logits that a checker did not
notice because they never compared `table_digest`/`inv_freq_table_digest`
separately). This is a genuine, unresolved weakness in the receipt design
inherited unchanged from the reference — not a choice this spec can
retroactively fix without changing the reference's actual hashed bytes
(which would change `CIS2_REF` itself). Recommendation for v0.2: fold both
table digests into the witness chain's seed, alongside the artifact
hashes.

14.4. **Trig polynomial accuracy is only validated for `|x| ≲ 14`** (unit
tests sweep `x = i * 0.7` for `i` in `-20..=20`). RoPE angles in this
spec's fixed 20-position decode stay small (`pos < 20`, `inv_freq ≤ 1.0`),
so this is adequate for §13's test vectors, but the two-part-π reduction
(§6.3) has not been stress-tested at larger magnitudes where it could
lose more precision. A clean-room implementer targeting a longer sequence
than this spec's 20 positions should not assume this polynomial's
accuracy holds unchanged.

14.5. **RMSNorm multiply order (§8) is pinned but its bit-level necessity
is unconfirmed.** `(x[i]*inv)*weight[i]` vs. `x[i]*(inv*weight[i])` are
not provably identical for arbitrary fp32 operands under rounding, but no
divergence between the two orders has actually been observed on this
model/prompt — this is pinned for completeness/reproducibility
discipline, not because a measured mismatch was found.

14.6. **The oracle correctness check (§13.3) is a defensible spot-check,
not exhaustive.** It confirms 16/16 greedy token-id agreement and one
step's full-vocab logit agreement to ~4e-6 relative — it does not check
every intermediate layer's activations against the oracle, so a
compensating pair of errors elsewhere in the 30-layer stack that happens
to preserve step-0's output and all 16 argmax decisions cannot be
completely ruled out by this evidence alone.

14.7. **This spec's own history**: earlier states of the reference (see
`docs/E15b_REFERENCE_RESULT.md`) computed `inv_freq` via unpinned host
`f64::powf`, producing a *different* `CIS2_REF`
(`830d972dbfb0b5598015f33571d08623d2b05d8e239b8d0288562d9ac9786907`) than
the one this spec pins (`ba88708b...`, produced after switching to
`exp_pinned`-based `inv_freq`, §7.1). The argmax-token digest
(`0b9c8f3a...`) is unchanged between both versions — the 16 greedy token
ids never flipped, only the full logit bit pattern did. This is recorded
here because it demonstrates the exact failure mode §14.3 warns about:
two "reasonable" reference states differ in `CIS2_REF` for a reason
(`inv_freq`'s construction) that a `CIS2_REF`-only comparison would not
localize without also comparing `inv_freq_table_digest`.

## 15. Conformance (normative)

An implementation is CIS-2 v0.1 conforming iff, from this document's text
alone (no access to `src/`):

1. It reproduces every value in §13.1 bit-for-bit, on x86-64.
2. It reproduces every value in §13.1 bit-for-bit, on aarch64, unmodified
   source, with the ISA-specific FTZ/DAZ leg of §1.3 actually exercised
   (not a no-op stub).
3. Its release binary contains zero FMA instructions on the decode path
   (§1.4, disassembly-verified).
4. Its self-test (§1.3's adversarial denormal check) passes.
5. It passes §12.4's same-process two-run determinism check.

This is a narrower and more mechanical bar than CIS-1's three-tier scheme
(CIS-1 §8) because CIS-2 v0.1 has exactly one pinned (model, prompt,
length) tuple rather than CIS-1's op-goldens/selftest/token-digest split;
a future version should factor out op-level goldens (individual
`exp_pinned`/`sin_pinned`/`cos_pinned`/`rsqrt`/`dot_seq` unit vectors) as
their own tier, independent of the full 30-layer decode, the way CIS-1's
Tier 1/Tier 2 do — not done in this version.

## 16. Version history

- **v0.1 (2026-08-28)** — first draft. Closes every item in
  `verify/SPEC_GAPS.md` (digest byte encoding, transcendental route and
  exact coefficients, RoPE `inv_freq` construction and digest, RMSNorm
  elementwise order) against the actual reference implementation at the
  commit cited in Appendix A. Known-incomplete: §14's items, especially
  14.1 (theta-general RoPE) and 14.3 (table digests not bound into the
  receipt) are left open for v0.2, not resolved here.

---

## Appendix A — source citations (informative; not required to implement this spec)

Every normative choice above is taken from this repo's `src/` at the
commit checked out on branch `cm/e15f-spec-v0.1` (based on
`origin/cm/e15e-cleanroom-verify`). Reference implementation state:
post-"m1.5 RoPE fix" (`docs/E15b_m1p5_CORRECTNESS.md`), i.e. `inv_freq`
via `exp_pinned`, not the earlier `f64::powf` draft.

- §1.3 FTZ/DAZ: `src/denormal.rs:22-34` (x86_64 MXCSR), `:43-57` (aarch64
  FPCR), `:106-137` (adversarial self-test), `src/main.rs:225-229` (call +
  assert at process start).
- §1.4 no-FMA: `src/math.rs:37-48` (`dot_seq`/`sum_seq`, comment block
  `:1-28`), `tests/no_mul_add.rs` (grep gate), `scripts/no_fma_gate.sh`
  (grep + objdump gate).
- §2.1/§2.2 artifact + config: `docs/E15b_REFERENCE_RESULT.md` provenance
  table; `src/main.rs:240-250` (config field reads), `:258-261` (theta
  assert).
- §2.5 tensor names/shapes: `src/main.rs:285-314`.
- §3.2-3.4 tokenizer/prompt/decode: `src/main.rs:334-339` (tokenize,
  `add_special_tokens=false` via `tok.encode(prompt, false)`), `:357-412`
  (prefill + 16-step greedy loop, no EOS check).
- §4.1-4.2 bf16 widening: `src/math.rs:29-35` (`widen_bf16`),
  `src/main.rs:188-204` (`load_f32_tensor`, byte unpacking).
- §5.1-5.4 reductions: `src/math.rs:37-58` (`dot_seq`, `sum_seq`),
  `src/main.rs:41-50` (`matvec`), `:69-75` (`elementwise_add`).
- §6.1 rsqrt: `src/math.rs:60-68`.
- §6.2 exp: `src/math.rs:85-158` (`exp_pinned`, `ldexp_exact`).
- §6.3 sin/cos: `src/math.rs:160-227` (`reduce_2pi`, `sin_pinned`,
  `cos_pinned`, coefficient tables `:164-165, 177-203`).
- §6.4 SiLU: `src/math.rs:229-236`.
- §6.5 table digest: `src/math.rs:261-285` (`table_digest`), value
  confirmed in `docs/E15b_REFERENCE_RESULT.md`.
- §7 RoPE: `src/main.rs:252-279` (`inv_freq` construction + digest,
  including the `LN_THETA` literal and the `rope_theta==100000.0`
  assert), `src/main.rs:80-102` (`apply_rope_head`).
- §8 RMSNorm: `src/main.rs:52-67`.
- §9 attention: `src/main.rs:109-168` (`forward_token`, projections
  through V-mix and `o_proj`).
- §10 MLP: `src/main.rs:170-178`.
- §11 LM head/argmax: `src/main.rs:181-186` (LM head matvec via tied
  embed_tokens), `:388-396` (argmax scan).
- §12 digests: `src/main.rs:341-426` (`run` closure: witness seeding
  `:349-355`, per-step chain update `:401-406`, argmax digest
  `:415-419`), `:206-222` (`sha256_file` returns hex `String`, confirming
  §14.2's hex-ASCII-not-raw-bytes encoding).
- §13.3 oracle comparison: `docs/E15b_m1p5_CORRECTNESS.md` in full;
  `scripts/oracle_compare.py` (not re-read line-by-line for this spec,
  cited for the comparison methodology only).
- §14.7 prior `CIS2_REF` value: `docs/E15b_REFERENCE_RESULT.md`
  (`830d972d...`, pre-RoPE-fix) vs. `docs/E15b_m1p5_CORRECTNESS.md`
  (`ba88708b...`, post-fix, matches this spec).

## Appendix B — where this spec found the reference itself inconsistent or unpinned

(Every item cross-referenced to its §14 discussion above; listed here
tersely for a reviewer scanning only this appendix.)

1. **RoPE `inv_freq` is theta-specific by construction** (`LN_THETA` a
   bare literal; no general `ln()`), yet the surrounding code and memo
   describe the implementation as "architecture-general Llama-family
   code... driven entirely from `config.json`" — the RoPE leg is the one
   place this claim does not actually hold without the `rope_theta ==
   100000.0` assert silently narrowing scope. §14.1.
2. **Table digests (`table_digest`, `inv_freq_table_digest`) are computed
   but never folded into `CIS2_REF`** — the receipt's own stated purpose
   (bind everything that determines the output) is under-delivered by the
   reference's actual hashed byte sequence. §14.3.
3. **Digest byte encoding (hex-ASCII vs. raw bytes) for the three artifact
   hashes is not discoverable from any prose/memo text this program has
   produced** — only from reading `sha256_file`'s return type and its
   call site. Not a bug, but a real "you cannot get this from the spec
   prose that existed before this document" gap, now closed. §14.2.
4. **`rsqrt`/`sqrt`/`/` are the only operations in this whole spec that
   are unconditionally, provably cross-ISA-identical by the IEEE-754
   standard itself** ("correctly rounded" is mandatory for these, not
   merely recommended) — every other transcendental (`exp`, `sin`, `cos`)
   is pinned "by fiat" (memo's own words) and has no such guarantee
   outside this document's specific coefficients. This is not an
   inconsistency in the reference, but it is the one place a clean-room
   implementer might mistakenly assume a stronger property (e.g. that
   `exp_pinned` is "correctly rounded" the way `sqrt` is) than what is
   actually true.
