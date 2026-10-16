# `gpu/` — E18b: CUDA-portable C++ implementation of CIS-2 v0.3b

**Status: host build verified. `nvcc` (E18c) compiles this source to real
device object code — never linked, never run on a device.** This box has
no NVIDIA GPU, but as of E18c it does have `nvcc` 12.9
(`/usr/local/cuda/bin/nvcc`), compile-only. `make cuda`/`cuda-tree`/
`nofma-cuda` genuinely invoke it and inspect the resulting SASS (§12); no
target here has ever been *linked* into an executable or *executed* on a
device, and no claim is made about runtime behaviour, correctness, or
timing on real hardware. See §12 for exactly what changed and what did
not.

No timing figures appear anywhere in this directory, by lab policy.

---

## 1. What this is

A single-source C++17 implementation of the CIS-2 v0.3b normative forward
pass whose **host build reproduces the Rust reference's `CIS2_REF` digest
bit-for-bit**. The Rust reference on this branch (`src/main.rs`,
`src/math.rs`, `src/denormal.rs`) *is* the normative arithmetic; this port
mirrors it statement by statement. Where the C++ and the Rust could
plausibly differ (float→int cast semantics, `round()` tie rule, operator
associativity, f32 vs f64 intermediates) the difference is called out in
§4 below and reproduced deliberately.

Portability contract, enforced mechanically:

* Every arithmetic function carries `CIS2_FN`, which expands to
  `__host__ __device__` under `nvcc` and to nothing on the host.
* Every kernel is a plain loop over an index space, expressed once via
  `cis2_for_each(n, lambda)` — a `for` loop on the host, a grid launch
  under CUDA. The kernel bodies are the same source text in both builds.
* No libm in the arithmetic path (`floor`, `round`, `frexp`, `ldexp`,
  `copysign` are all open-coded from bit manipulation). `nm -u` on the host
  binary must show no `expf/sinf/cosf/powf/logf/exp/log` symbols.
* `sqrt` is the hardware IEEE-754 correctly-rounded instruction and nothing
  else — see §3, "rsqrt", for why that is the one operation the spec does
  not pin.
* No FMA anywhere: every multiply-then-add is two separately-rounded
  statements. `objdump -d` on the host binary must show zero
  `vfmadd*/vfnmadd*/vfmsub*` instructions.
* FTZ|DAZ pinned in MXCSR at process start and asserted by readback, plus
  the same adversarial denormal self-test the Rust reference runs.

## 2. Files

| file | role |
|---|---|
| `cis2_consts.inc` | **generated** by `cargo run --release --bin math_dump`. Every pinned constant of `src/math.rs` as an exact hex-float literal (no decimal-parse ambiguity between the Rust and C++ front ends). Do not edit. |
| `cis2_fpenv.h` | MXCSR FTZ/DAZ pin + readback assert + §1.3 adversarial self-test; `nvcc -ftz=true` compile-time assert for the device build. |
| `cis2_math.h` | The pinned transcendentals and reduction primitives, ported line-for-line from `src/math.rs`. |
| `cis2_sha256.h` | Self-contained SHA-256 (FIPS 180-4) for the witness/receipt/trace digests. Integer arithmetic, not part of the fp32 path. |
| `cis2_model.h` | safetensors + config.json readers, the model struct, and the forward pass as index-space kernels. |
| `cis2_host.cpp` | Host driver: loads weights, reads token ids from a file, greedy-decodes N tokens, folds the `CIS2_REF` witness, optional `--trace`. |
| `test_math.cpp` | Replays a 242 428-input golden sweep recorded from the Rust functions and requires every one of the 1 454 568 results to be bit-identical. |
| `math_golden.bin` | **generated** by `math_dump` (gitignored; `make test-math` regenerates it). |
| `cis2_sass_probe.cu` | **E18c.** A minimal, self-contained device translation unit (depends only on `cis2_math.h`) exercising the six reduction kernels (sequential + tree dot/sum/softmax) for `nofma-cuda`'s SASS inspection. Never linked, never run. |
| `Makefile` | `host`, `host-gcc`, `host-tree`, `cuda`, `cuda-tree`, `test-math`, `gate`, `gate-128`, `gate-tree`, `gate-tree-128`, `nofma`, `nofma-cuda`, `nolibm`, `clean`. Every heavy command takes the box lock and is niced; the lock is taken by the individual recipes, never by `make` itself (flock is not reentrant, so wrapping the whole `make` in it deadlocks). |

Rust-side support added for this port (all non-normative, none of it in the
decode path):

* `src/bin/math_dump.rs` — emits `cis2_consts.inc` and `math_golden.bin` by
  calling the *same* `src/math.rs` the decode path calls (`#[path]`
  include, so there is exactly one copy of the normative arithmetic).
* `src/math.rs::exported_f32_consts` / `exported_f64_consts` — a read-only
  view of the pinned constants, in `table_digest()`'s fold order.
* `src/main.rs --dump-ids FILE` — writes the tokenizer's prompt ids so the
  C++ never re-implements tokenization.
* `src/main.rs --trace FILE` — the per-(layer, op) trace described in §5.

## 3. Normative op map

Rust line numbers are as of this branch (`cm/e18b-cuda-portable`, based on
`cm/e15m-spec-v0.3-rope` @ `07b585b`). "Reduction order" is the thing that
has to match; everything else is elementwise and order-free *for bits*.

| op | Rust fn (file:line) | reduction order | C++ mirror |
|---|---|---|---|
| bf16→f32 widening | `math.rs:33 widen_bf16` | none (exact `(u32)bits << 16`) | `cis2_widen_bf16`, `cis2_math.h` |
| embedding gather | `main.rs:174` (`embed_tokens[tok*hidden .. +hidden]`) | none | `k_embed`, `cis2_model.h` — 1 thread per hidden index |
| RMSNorm | `main.rs:70 rmsnorm` | `sum_seq` over the **whole** `sq[]` array, strict left-to-right, `math.rs:52` | `cis2_rmsnorm`: `k_square` (elementwise) → `k_sum_seq` (**1 thread**, sequential) → `k_scale_by_weight` (elementwise) |
| q/k/v/o/gate/up/down/lm_head projections | `main.rs:59 matvec` → `math.rs:40 dot_seq` | per output row, strict left-to-right over `in_features`; rows independent | `k_matvec`: 1 thread per output feature, each running `cis2_dot_seq` serially |
| QKV bias (absent for SmolLM2) | `main.rs:90 add_bias_opt` | elementwise | `k_add_bias` |
| RoPE inv_freq table | `main.rs:387-407` | per index `i`, `frac = (2i as f32)/(head_dim as f32)`; `a = frac*ln_theta`; `exp_pinned(-a)` | `cis2_build_inv_freq`, `cis2_model.h` |
| RoPE apply | `main.rs:110 apply_rope_head` | per `(head, i)`, independent | `k_rope`: 1 thread per `(head, i<half)`, computes its own `cos`/`sin` |
| attention scores | `main.rs:207-212` | per `(qh, j)`: `dot_seq(q_head, k_j)` strict L→R over `head_dim`, then `* scale` | `k_scores`: 1 thread per `(qh, j)` |
| softmax | `math.rs:358 softmax_seq` | sequential max scan (first max wins, strict `>`), then `exp_pinned(v-max)`, then `sum_seq` denominator strict L→R, then elementwise divide | `k_softmax`: **1 thread per query head**, running the whole sequential softmax over its own `pos+1` scores |
| attention weighted sum | `main.rs:216-224` | per `(qh, d)`: `acc = acc + scores[j]*v[j][d]` over `j` in **position order** | `k_attn_weighted_sum`: 1 thread per `(qh, d)`, serial over `j` |
| residual adds | `main.rs:99 elementwise_add` | elementwise | `k_add` |
| SwiGLU | `main.rs:239-241` | `silu_pinned(gate[i]) * up[i]`, elementwise | `k_silu_mul` |
| final norm | `main.rs:248` (`rmsnorm` again) | as RMSNorm above | same |
| LM head | `main.rs:255` (`matvec`, tied to `embed_tokens`) | as matvec above | `k_matvec` |
| argmax / greedy | `main.rs:614-621` | sequential scan over `0..vocab`, strict `>`, **first** maximum wins | `cis2_argmax`, host-side (the logits are on the host anyway for the witness fold) |
| exp / sin / cos / ln / silu / rsqrt | `math.rs:100/243/257/312/347/66` | see §4 | `cis2_math.h`, same names prefixed `cis2_` |
| table digest | `math.rs:382 table_digest` | fixed declared order over the LE bytes of every pinned coefficient | `cis2_table_digest`, `cis2_model.h` — asserted equal to the value `math_dump` prints |
| inv_freq table digest | `main.rs:401-407` | SHA-256 over `inv_freq[i].to_le_bytes()` in index order (**value bytes, not bit-pattern bytes** — same thing for f32, but the trace hashes use `to_bits().to_le_bytes()`, see §5) | `cis2_model.h` |
| witness / `CIS2_REF` fold | `main.rs:554-577, 623-631` | see §6 | `cis2_host.cpp` |

## 4. Places where the Rust's evaluation order is **not** obvious

These are the traps. Every one is reproduced deliberately in the C++.

1. **`rmsnorm` scales twice, in this order.** `out[i] = (x[i] * inv) * weight[i]`
   (`main.rs:81-82`), *not* `x[i] * (inv * weight[i])`. Two separately
   rounded multiplies with the intermediate `x[i]*inv` rounded first.
2. **`rmsnorm`'s sum is over a materialised array.** The squares are written
   into `sq[]` in a first loop and only then summed (`main.rs:73-76`). The
   sum is `sum_seq`, strict left-to-right from `acc = 0.0f`, so the leading
   `0.0 + sq[0]` add is real and is performed. Fusing the square into the
   accumulation loop would give the same bits here, but the split is kept
   so the kernel decomposition is faithful.
3. **`mean = ss / (n as f32)`** — a correctly-rounded division by
   `576.0f`, not a multiply by a reciprocal.
4. **Attention scale is applied *after* the dot product**, per score:
   `scores[j] = dot_seq(q,k) * scale` (`main.rs:211`). Scaling `q` up front
   would change the bits. `scale = rsqrt_cr(64.0f) = 1.0f/sqrt(64.0f)`,
   which happens to be exactly `0.125f`, but it is computed, not written.
5. **RoPE's negation happens before the multiply**: `t2 = (-x2) * sin_v[i]`
   (`main.rs:125`), not `-(x2 * sin_v[i])`. Identical for finite values,
   different for a signed zero — and RoPE genuinely sees `sin(0.0) = 0.0`
   at `pos = 0`, so this is load-bearing.
6. **RoPE output order**: `out[i] = x1*cos + (-x2)*sin` and
   `out[i+half] = x2*cos + x1*sin` — the second is `cos` term first.
7. **`softmax_seq` ties**: the max scan is `if v > max_v`, so the *first*
   occurrence of a repeated maximum wins. Same rule in the argmax
   (`main.rs:616`, `if v > best_val`). Both are `>`, never `>=`.
8. **Softmax divides, it does not multiply by a reciprocal**
   (`math.rs:333`): `*v = *v / denom`.
9. **`exp_pinned`'s `k as i32` is a Rust saturating cast** — NaN→0, out of
   range→clamp — which is *not* C's conversion (UB on overflow). The clamp
   `-88.0 < x < 88.0` earlier in the function means the saturating path is
   never taken in the decode path, but it is reproduced exactly
   (`cis2_f32_to_i32_sat`) because `test_math` sweeps the full f32 space
   and would otherwise hit UB.
10. **`reduce_pi_2` is the only f64 code in the arithmetic path**
    (`math.rs:186`). It widens f32→f64 exactly, does a correctly-rounded
    f64 divide, an f64 `round()`, an f64 multiply and an f64 subtract, then
    narrows to f32 **once**. Everything else in `math.rs` is f32
    throughout. Getting this wrong (staying in f32, or narrowing early) is
    exactly the v0.2→v0.3 defect this branch fixed.
11. **`f64::round()` is ties-AWAY-from-zero**, unlike C++'s default
    round-to-nearest-even conversions and unlike `nearbyint`. It also
    preserves the sign of a zero (`round(-0.0) == -0.0`), and that sign
    then flows into `k_f64 * PI_2_F64`. `cis2_round_f64` reproduces both.
12. **`k_f64 as i64` is likewise a Rust saturating cast** —
    `cis2_f64_to_i64_sat`.
13. **`quadrant(k) = ((k % 4) + 4) % 4`** relies on Rust `%` on `i64` being
    truncated division. C++'s `%` on signed integers is also truncated
    (since C++11), so this transcribes directly — but it is only correct
    *because* both languages truncate, and that is worth stating.
14. **`ln_pinned`'s `m = m + m - 1.0`** (`math.rs:326`) parses as
    `(m + m) - 1.0`, left-associative: two separately-rounded operations,
    not `2.0*m - 1.0` and not an FMA.
15. **`ldexp_exact`'s underflow branch returns `+0.0` regardless of the
    sign of `x`** (`math.rs:147`). Asymmetric with the overflow branch,
    which does respect the sign. Mirrored literally.
16. **`f32::NAN` in Rust is the specific bit pattern `0x7FC00000`.** The
    NaN-returning paths of `exp_pinned`/`ln_pinned` are compared
    bit-for-bit by `test_math`, with no "both are NaN" escape hatch, so the
    C++ pins the same bits (`cis2_nan_f32`).
17. **Denormals: the pin covers *arithmetic*, not bit manipulation.** With
    MXCSR FTZ|DAZ set, every SSE arithmetic op flushes denormal inputs and
    outputs to zero. But `widen_bf16`, `frexp_exact` and `ldexp_exact` are
    pure bit reinterpretation — they can produce and consume denormal *bit
    patterns* without flushing. A bf16 subnormal widens to an f32
    subnormal, which then flushes on the first arithmetic op that touches
    it. This is the reference's behaviour and the port's.
18. **FTZ/DAZ also govern the f64 ops** in `reduce_pi_2` (MXCSR is not
    per-precision). No denormals arise there — `|x| < 8192` and the
    constants are O(1) — but the environment is the same, not a separate
    one.
19. **`eps` and `rope_theta` cross types.** `rms_norm_eps` is read as f64
    from JSON and narrowed (`config["rms_norm_eps"].as_f64() as f32`,
    `main.rs:373`); `rope_theta` likewise (`main.rs:374`, then
    `ln_pinned(rope_theta as f32)`, `main.rs:389`). The C++ parses the JSON
    number with `strtod` (correctly rounded, like `serde_json`) and applies
    the same single narrowing.
20. **`inv_freq`'s `frac`** is `(2 * i) as f32 / (head_dim as f32)` —
    integer multiply, *then* two exact int→f32 conversions, *then* a
    correctly-rounded f32 divide (`main.rs:390`).
21. **The witness binds *raw 32-byte digests*, never hex ASCII**
    (`main.rs:557-561`) — v0.2 §12.1 closed exactly that gap; feeding hex
    strings would produce a plausible-looking but wrong `CIS2_REF`.
22. **`inv_freq_table_digest` hashes `v.to_le_bytes()`** (the f32 *value*
    bytes, `main.rs:404`) while the debug trace hashes
    `v.to_bits().to_le_bytes()` (`main.rs:145`). For f32 these are the same
    four bytes; the distinction is noted so the port does not "fix" one
    into the other.
23. **The logits bound into the witness at step `s` are the logits
    *already computed*** — for `s = 0` those are the last prefill
    position's logits, not a fresh forward pass. The forward pass for
    `pos = prompt_len + s` happens *after* the fold (`main.rs:634`).
24. **`forward_token` pushes k and v into the cache *after* RoPE**
    (`main.rs:199-200`), so the cache holds rotated keys and unrotated
    values, and a cached key is never re-rotated at a later position.
25. **GQA head mapping is integer division**: `kv_head = qh / group` with
    `group = n_heads / n_kv_heads` (`main.rs:170`, `main.rs:205`). For
    SmolLM2-135M that is 9 query heads over 3 kv heads, group 3.

## 5. Trace mode

Both implementations accept `--trace FILE` and write one line per
`(position, layer, op)`:

```
pos=<p> layer=<L> op=<name> sha256=<64 hex chars>
```

`L` is the layer index, or `-1` for the whole-model ops (`embedding`,
`final_norm`, `logits`). The hash is SHA-256 over the raw little-endian
**f32 bit patterns** of that op's output, in index order.

Ops, in emission order, per position: `embedding`; then per layer
`norm1, q, k, v, rope_q, rope_k, scores, softmax, attn_out, o_proj,
resid1, norm2, gate, up, silu_mul, down, resid2`; then `final_norm`,
`logits`. `scores` and `softmax` are the concatenation over query heads,
in head order, of that head's `pos+1` values. Traces are emitted for every
forward pass (prefill positions and every decode step) of the first
labelled run only.

`make gate` requires the two trace files to be byte-identical (`cmp`), so
the first divergence — if there ever is one — is a single `diff` away
rather than a bisect.

## 6. Witness / `CIS2_REF` fold

Exactly as `src/main.rs` folds it (`main.rs:554-577` and `623-631`), in
this order, into one SHA-256:

```
sha256(model.safetensors)          32 raw bytes
sha256(tokenizer.json)             32 raw bytes
sha256(config.json)                32 raw bytes
math::table_digest()               32 raw bytes
inv_freq_table_digest              32 raw bytes
for t in prompt_ids:               u32 LE
for step in 0..gen_toks:
    for v in logits:               u32 LE of v.to_bits()
    next_id                        u32 LE
```

The printed line is
`CIS2_REF digest=<hex> prompt_idx=0 prompt_toks=<n> gen_toks=<n> dtype=fp32`.
The gate compares that hex against the Rust binary's, and exits non-zero on
any difference.

## 7. Build and gates

```
make -C gpu test-math      # 242 428-input golden sweep, 6 functions, bit-exact
make -C gpu gate           # 16-token digest equality + trace equality (sequential, v0.3b)
make -C gpu gate-128       # 128-token digest equality (sequential, v0.3b)
make -C gpu nofma          # objdump: zero vfmadd/vfnmadd/vfmsub in host/host-tree/test_math
make -C gpu nolibm         # nm -u: no expf/sinf/cosf/powf/logf/exp/log
make -C gpu host host-gcc host-tree   # clang++ and g++ host builds (sequential + tree)
make -C gpu cuda cuda-tree            # E18c: nvcc, compile-only object (-c), never linked/run
make -C gpu gate-tree      # 16-token digest equality + trace equality (tree, v0.4 CANDIDATE)
make -C gpu gate-tree-128  # 128-token digest equality (tree, v0.4 CANDIDATE)
make -C gpu nofma-cuda     # E18c: cuobjdump SASS, zero FFMA in the 4 pure reduction kernels
```

`/usr/local/cuda/bin` is not on `PATH` by default on this box; pass
`NVCC=/usr/local/cuda/bin/nvcc CUOBJDUMP=/usr/local/cuda/bin/cuobjdump`
(both `?=`-overridable) to any target above that touches nvcc.

`gate`/`gate-128`/`nofma` exercise the **untouched v0.3b sequential path**
and must keep reproducing the pinned digests in §8 forever. `gate-tree`/
`gate-tree-128`/`nofma-cuda` exercise the **new v0.4 CANDIDATE tree path**
(§12) and establish a *different*, new digest pair — see §12, not §8, for
those values.

Host flags (clang): `-std=c++17 -O2 -ffp-contract=off -fno-fast-math
-ffp-model=strict`. Host flags (g++): `-std=c++17 -O2 -ffp-contract=off
-fexcess-precision=standard -fno-fast-math -msse2 -mfpmath=sse`. No
`-march=native` in either: it would let the compiler pick FMA-bearing
instruction selection. `-fexcess-precision=standard -mfpmath=sse` on the
g++ side is what keeps every f32 intermediate at f32 rather than spilling
through an x87 80-bit register.

The one libc call that touches floating point at all is `strtod`, used to
parse the two JSON documents' decimal numbers. It is correctly rounded,
it is what `serde_json` gives the Rust reference, and it runs once at
startup — it is not in the decode path and not a transcendental. Nothing
else: `nm -u` on both host binaries lists no math symbol whatsoever.

## 8. Verified results (host build, x86-64, this box)

| gate | result |
|---|---|
| `make test-math` | 242 428 inputs x 6 functions = **1 454 568 comparisons, 0 mismatches** |
| `make gate` (16 tokens) | rust and c++ both `CIS2_REF digest=d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df`; traces **10 260 lines, byte-identical** |
| `make gate-128` (128 tokens) | rust and c++ both `CIS2_REF digest=22f69ad87a615d66a77efaca8b1172d22bdfb4bd5092ceffd302e35669a050f6` |
| `make host-gcc` | the g++ build produces the same 16-token digest and a byte-identical trace |
| `make nofma` | `vfmadd/vfnmadd/vfmsub/vfnmsub` count = **0** in both binaries |
| `make nolibm` | undefined libm math symbols = **0** in both binaries |
| `cargo test` | 7 + 7 + 1 tests pass (including the `.mul_add(` grep gate) |
| `cargo fmt --check` | clean |

The 16-token digest is the value `docs/E15m_RESULT.md` records for v0.3b,
so the C++ agrees with the Rust reference *and* with the two clean-room
verifiers (`verify2/` Rust, `verify3/` C11) that were checked against it.

Not verified, and not claimed: anything about the CUDA build. It has never
been compiled.

Intended device flags, **never exercised**: `-fmad=false -ftz=true
-prec-div=true -prec-sqrt=true`, no `-use_fast_math`, and no
`__expf`/`__sinf`/`__cosf`/`__fdividef` intrinsics anywhere in the source.
`cis2_fpenv.h` `#error`s at compile time if `-ftz=true` was not passed.

## 9. aarch64

**Status: cross-ISA port added on `cm/e18b-arm`, proven via GitHub's
`ubuntu-24.04-arm` runner (this box has no aarch64 hardware).**

Changes, all in this section's scope only:

* `gpu/cis2_fpenv.h` — an aarch64 branch that pins flush-to-zero via
  `FPCR.FZ` (bit 24), read/modified/written with inline `mrs`/`msr fpcr`,
  with a readback assert — the exact mirror of `src/denormal.rs`'s
  aarch64 arm (same bit, same sequence, `FZ16` left untouched). The x86-64
  MXCSR path is byte-for-byte unchanged. `cis2_black_box`'s optimization
  barrier now uses the `"w"` (AArch64 FP/SIMD register) constraint on that
  arch instead of x86's `"x"` (SSE) constraint — the previous code
  hardcoded `"x"` for both, which does not exist on aarch64 and failed to
  even parse there.
* `gpu/cis2_math.h` — `cis2_sqrt_f32` gained an aarch64 branch: a single
  inline `fsqrt` instruction (AArch64's hardware IEEE-754
  correctly-rounded scalar sqrt), the direct equivalent of the x86-64
  `sqrtss` path. No libm, no new arithmetic.
* `gpu/Makefile` — `-ffp-contract=off` was already unconditional (it is
  the mandatory flag on aarch64: clang and gcc both contract separate
  multiply+add into `fmadd`/`fmla` by default on this ISA, unlike x86-64).
  Added: an arch switch (`uname -m`) so g++'s `-msse2 -mfpmath=sse` (x86-64
  only, rejected by g++ on aarch64) is not passed there, and the `nofma`
  gate's `objdump` grep pattern switches from
  `vfmadd|vfnmadd|vfmsub|vfnmsub` (x86-64) to
  `fmadd|fmsub|fnmadd|fnmsub|fmla|fmls` (aarch64 scalar + NEON FMA
  mnemonics).
* `.github/workflows/e18b-cpp-cross-isa.yml` — new workflow, matrix
  `ubuntu-24.04` (x86_64) / `ubuntu-24.04-arm` (aarch64). Each job fetches
  the pinned weights, builds the Rust reference and both C++ host builds
  (clang++, g++), runs `test-math`, `nofma`, `nolibm`, and `gate` (16
  tokens, digest + trace equality), and asserts its own `CIS2_REF` digest
  equals the pinned target below. A final `compare` job downloads both
  runners' artifacts and asserts the x86_64 and aarch64 digests equal each
  other and both equal the pinned target, and that both runners' trace
  files are byte-identical across ISA.

Local proof, since this box cannot execute aarch64 code: `clang++
--target=aarch64-linux-gnu` and `aarch64-linux-gnu-g++` (Debian's
`g++-aarch64-linux-gnu` cross package) both compile `cis2_host.cpp` and
`test_math.cpp` to aarch64 object code cleanly with the same
`-ffp-contract=off -fno-fast-math` flags used on the host, and
`aarch64-linux-gnu-objdump -d` on the resulting object shows **zero**
`fmadd/fmsub/fnmadd/fnmsub/fmla/fmls` instructions and the expected
`fsqrt`/`mrs`/`msr` instructions present. This is a codegen check, not a
runtime one — the runtime proof is the GitHub Actions run below.

### CI run

| | |
|---|---|
| workflow run | https://github.com/Aefinity-AI/cis2-fp/actions/runs/33655093168 |
| x86_64 `CIS2_REF` digest (16 tok) | `d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df` |
| aarch64 `CIS2_REF` digest (16 tok) | `d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df` |
| equal to each other and to pinned `d827…cc9df` | **YES** — `compare` job PASS, both runners' 16-token traces byte-identical across ISA |

Green on the first push, `cm/e18b-arm` @ `b370b33`, 2026-09-02. Both the
`x86_64` and `aarch64` `run` jobs independently passed `test-math`
(1 454 568 comparisons, 0 mismatches), `nofma`, `nolibm`, and `gate`
(digest + 10 260-line trace equality between the C++ port and the Rust
reference on that runner); the `compare` job then confirmed the two
runners' digests and traces agree with each other and with the pinned
v0.3b target. The C++ port now carries the same cross-ISA evidence the
Rust reference has (`e15c-cross-isa.yml`).

## 10. Second model — Qwen2.5-0.5B

**Status: run on GitHub CI (`ubuntu-24.04` x86_64 + `ubuntu-24.04-arm`
aarch64), green.** This proves the C++ port is not tuned to SmolLM2-135M:
Qwen2.5-0.5B is a different config (896 hidden, 24 layers, 14 query heads
over **2** kv heads — GQA group=7, versus SmolLM2's group=3 — 151 936
vocab, `rope_theta=1000000.0` vs SmolLM2's `10000.0`) and a different
checkpoint shape (`self_attn.{q,k,v}_proj.bias` tensors present, which
SmolLM2's checkpoint does not have). Both the GQA group-size generality
and the QKV-bias code path (`k_add_bias`, README §3) had never been
exercised against real weights before this run — they were "coded but
never exercised" per the earlier state of this section.

No C++ arithmetic changed. One infra fix was required:
`gpu/Makefile`'s `gate`/`gate-128` targets passed `--weights-dir` to the
C++ binary but not to the Rust reference (which silently defaulted to
`./weights`, i.e. SmolLM2) — fixed to pass it to both, so `make gate
WEIGHTS=weights_qwen` runs the *same* model on both sides. See
`.github/workflows/e18b-cpp-qwen.yml`, which copies the
`e18b-cpp-cross-isa.yml` matrix/gate pattern (uname assert, Rust +
C++(clang++/g++) builds, `test-math`, `nofma`, `nolibm`, `gate`, then a
`compare` job) against Qwen2.5-0.5B, with the weight fetch sha256-pinned
(see `gpu/EXPECTED_DIGESTS.md`).

| | |
|---|---|
| workflow run | https://github.com/Aefinity-AI/cis2-fp/actions/runs/33658402020 |
| prompt / gen_toks | "Once upon a time" / 16 |
| x86_64 `CIS2_REF` digest | `c9dff099d927a6dda91514c260c7207de7aca4b361291e57fae390a352392e62` |
| aarch64 `CIS2_REF` digest | `c9dff099d927a6dda91514c260c7207de7aca4b361291e57fae390a352392e62` |
| C++ == Rust on each runner | **YES** (`gate` step, digest + 10-token-prompt trace equality) |
| x86_64 == aarch64 | **YES** (`compare` job: digests and traces byte-identical across ISA) |

First attempt (run 33658016355) failed before ever reaching a digest —
the Makefile bug above, not an arithmetic mismatch: the Rust reference
loaded the *default* `weights/` directory (SmolLM2, only `config.json`
present on the runner in that job's checkout, no weights fetched there)
while the C++ side correctly loaded `weights_qwen/`. Fixed and rerun
green on the first arithmetic attempt (run 33658402020), and
`TARGET_DIGEST` in the workflow now pins `c9dff099...` as a real gate on
future runs. This is a fresh **v0.3b digest** — not comparable to the
v0.2 Qwen digest `2c9f6235...` in `docs/E15d_v0.2_DIGESTS.md`, which
predates this branch's RoPE/`reduce_pi_2` fix (README §4.10).

Full digest table across both model families: `gpu/EXPECTED_DIGESTS.md`.

## 11. Kaggle leg

**Status: staged (both kernels), guarded auto-push armed for the next
GPU-quota reset.** This box has no GPU, so `cuda`/`cuda-tree` have still
never been *linked or run* here — everything in this section is prepared
for the first Kaggle GPU run, not a report of one. As of E18c, the staged
kernel tests **both** the spec-normative v0.3b sequential reduction order
and the v0.4 CANDIDATE pinned tree order (SS12) in one script, one push,
one Kaggle run.

Files, under `gpu/kaggle/`:

| file | role |
|---|---|
| `make_dataset.sh` | Packs `gpu/`'s sources (the same `Makefile` this box gates with — no flag transcription, no drift; the tree reduction lives entirely behind `-DCIS2_REDUCTION_TREE` inside the files already copied, verified by `grep -n CIS2_REDUCTION_TREE gpu/*.h gpu/*.cpp`, so no new source file was needed), `weights/`, the 16- and 128-token prompt-id files for **both** modes (`gate`/`gate-128` and `gate-tree`/`gate-tree-128`), the host C++ build's own 16-token traces for **both** modes, and `gate/expected_digests.json` (now keyed `sequential`/`tree`) into a dataset directory, writes `dataset-metadata.json`, and pushes it as the private dataset `aefinityaiinc/cis2-e18b-gpu` (`kaggle datasets create`/`version`, chosen automatically). Needs no GPU. |
| `e18b_gpu.py` | The kernel code file (`kernel_type: script`). Installs nothing. Prints `nvcc --version`, the GPU name, and runs `make -C gpu nofma-cuda` (SASS FMA gate — needs no physical GPU, see SS12b). Links two genuinely runnable executables directly via `nvcc` (the Makefile's `cuda`/`cuda-tree` targets pass `-c`, object-only, deliberately never linked on this GPU-less dev box — see the script's module docstring for why it reproduces `NVCCFLAGS` by hand for the link step instead): `cis2_cuda` (sequential) and `cis2_cuda_tree` (`-DCIS2_REDUCTION_TREE`). Runs 16- and 128-token forward passes for **both** binaries, and separately builds+runs the **host** target (sequential only) on the Kaggle CPU as a control. Prints a final `mode \| tokens \| expected \| got \| verdict` table and writes `/kaggle/working/e18_results.json`. Exit status is governed by the **sequential** checks only — a tree/CANDIDATE FAIL is reported (`CANDIDATE FAIL`) but never flips the kernel's exit code, so an infra failure in the exploratory tree path can never be mistaken for or mask a failure of the load-bearing spec-normative path. |
| `kernel-metadata.json` | `enable_gpu: true`, private, `enable_internet: false`, dataset `aefinityaiinc/cis2-e18b-gpu` attached. |
| `push.sh` | The `kaggle kernels push` command, now guarded by `~/bin/kaggle-e18-gpu-push.sh` and `kaggle-e18-gpu-push.timer` (see below) rather than run by hand. |

### Expected outputs

Eight checks, each independently PASS/FAIL (four sequential, which govern
exit status; four tree/CANDIDATE, reported only):

| check | mode | compares | expects |
|---|---|---|---|
| `host_16tok` (control) | sequential | Kaggle-CPU host-build digest + trace | digest `d827…cc9df`; trace byte-identical to this box's host C++ trace |
| `host_128tok` (control) | sequential | Kaggle-CPU host-build digest | digest `22f6…050f6` |
| `gpu_16tok` | sequential | `cis2_cuda` digest + trace | digest `d827…cc9df`; trace byte-identical to this box's host C++ trace |
| `gpu_128tok` | sequential | `cis2_cuda` digest | digest `22f6…050f6` |
| `gpu_16tok_tree` (CANDIDATE) | tree | `cis2_cuda_tree` digest + trace | digest `3f3b…78e1b3`; trace byte-identical to this box's host C++ tree-mode trace |
| `gpu_128tok_tree` (CANDIDATE) | tree | `cis2_cuda_tree` digest | digest `1126…96a0fdf` |

**PASS/FAIL definition**: a run PASSES only if its `CIS2_REF` digest is
bit-identical to the pinned expected digest for its mode **and**, where a
trace is compared (the 16-token runs, both modes), the trace file is
byte-identical to the expected trace for that mode. Anything else is
FAIL, and the kernel prints the first divergent trace line —
`pos=<p> layer=<L> op=<name> sha256=<hex>` on both sides — rather than
just "mismatch". The host control failing while the sequential GPU run
also fails points at the Kaggle image's toolchain, not at the device
arithmetic; the host control passing while the sequential GPU run fails
localises the problem to CUDA specifically. The tree checks have no CPU
"control" of their own beyond the dataset's pre-recorded host C++
tree-mode trace/digest (SS12a), since tree mode is CANDIDATE, not
normative — a tree FAIL is a genuine open question about this leg's GPU
kernel, not a leg failure.

### What is staged vs. what still needs to run

```
gpu/kaggle/make_dataset.sh       # dataset upload — no GPU needed — RUN, see evidence below
gpu/kaggle/push.sh                # kernel push — NEEDS FREE GPU QUOTA — guarded, not run by hand
```

Weekly Kaggle GPU quota resets 2026-09-05 00:00 UTC. `push.sh` is no longer a purely manual step: it is
now invoked by a guard script fired once by a systemd `--user` timer
(`kaggle-e18-gpu-push.timer`, `OnCalendar=2026-09-05 01:30:00 UTC`, `Persistent=true`, 90 minutes after the
quota reset). The guard pushes exactly once, logs to `~/kaggle-e18-gpu-push.log`, notifies, and
disables its own timer. Do NOT run `push.sh` by hand
unless deliberately bypassing this guard; instead:

```
systemctl --user list-timers kaggle-e18-gpu-push.timer
tail ~/kaggle-e18-gpu-push.log
kaggle kernels status aefinityaiinc/e18b-gpu
kaggle kernels output aefinityaiinc/e18b-gpu -p ./e18b-gpu-output
```

## 12. v0.4 CANDIDATE — pinned tree reduction (E18c)

Full derivation, the ragged-tail rule, and the exact algorithm: see
`docs/design/CIS2_V04_TREE_REDUCTION.md`. Summary:

* **Block size 32** (one CUDA warp). **Ragged tail: zero-padded** — a
  block short of 32 real leaves has its remaining slots filled with
  `+0.0` before the fixed 5-round pairwise tree runs, which makes the
  padded tree collapse to a real, deterministic (if left-leaning) binary
  tree over exactly the real leaves — not an approximation, and not a
  second code path.
* **Two new functions per language**, siblings of the untouched v0.3b
  ones: `tree_sum`/`tree_dot` next to `sum_seq`/`dot_seq` (Rust
  `src/math.rs`; C++ `cis2_tree_sum`/`cis2_tree_dot` in `cis2_math.h`),
  `softmax_tree` next to `softmax_seq`. Nothing in the sequential
  functions is edited.
* **Selection**: Rust — CLI flag `--reduction sequential|tree` (default
  `sequential`), a `Reduction` enum threaded through
  `matvec`/`rmsnorm`/the attention-score loop/the softmax call site via
  three 4-line wrappers (`dot`/`sum`/`softmax`) that call the old
  functions unmodified when the mode is `sequential`. C++ — compile-time
  macro `-DCIS2_REDUCTION_TREE`, expanding `CIS2_DOT`/`CIS2_SUM`/
  `CIS2_SOFTMAX` at `cis2_model.h`'s four kernel call sites; building
  without the macro preprocesses to the exact prior source text there.
* **Receipt**: `reduction_mode=sequential|tree` is printed next to
  `CIS2_REF` (both languages) but is **not** folded into the witness hash
  — the sequential-mode digest is therefore providably unaffected by this
  leg's existence, not just unaffected by testing.
* **Scope**: dot products (`matvec` + attention scores) and plain sums
  (RMSNorm sum-of-squares, softmax denominator) are pinned. The attention
  weighted-sum accumulation (`acc = acc + scores[j]*v[j][d]`) is
  explicitly **not** routed through the tree in this candidate — see the
  design doc §3 for why (bounded by `pos+1 ≤ 128` here, small next to the
  576/1536/49152-wide matvecs; left to a future leg).

### 12a. Digests — v0.3b sequential (must stay pinned) vs v0.4 CANDIDATE tree (new)

Run on penguin, `weights/` (SmolLM2-135M, `model.safetensors` sha256
`80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1` — same
checkpoint E15b/E18b already used), commit `04e5ad77fabec22745fd5180532c55672855f499`
(Rust side; C++/Makefile changes follow in the next commit on this
branch).

| mode | model | tokens | Rust digest | C++ host digest | equal | trace equal |
|---|---|---|---|---|---|---|
| sequential | SmolLM2-135M | 16 | `d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df` | `d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df` | YES (== pinned v0.3b) | YES (10 260 lines identical) |
| sequential | SmolLM2-135M | 128 | `22f69ad87a615d66a77efaca8b1172d22bdfb4bd5092ceffd302e35669a050f6` | `22f69ad87a615d66a77efaca8b1172d22bdfb4bd5092ceffd302e35669a050f6` | YES (== pinned v0.3b) | n/a |
| **tree (v0.4 CANDIDATE)** | SmolLM2-135M | 16 | `3f3b1ffceca02e8e0e78d5c653963480ea988ef41a378acc5393006ad378e1b3` | `3f3b1ffceca02e8e0e78d5c653963480ea988ef41a378acc5393006ad378e1b3` | YES | YES (10 260 lines identical) |
| **tree (v0.4 CANDIDATE)** | SmolLM2-135M | 128 | `112661fbfcb11440ae7d27c43e45135f8a6ff9f6bc01189d756c76dac96a0fdf` | `112661fbfcb11440ae7d27c43e45135f8a6ff9f6bc01189d756c76dac96a0fdf` | YES | n/a |

`make -C gpu gate`/`gate-128` (sequential) and `gate-tree`/`gate-tree-128`
(tree) all report `GATE PASS`. `cargo test --release`: 25/25 pass
(includes the 6 new tree/softmax_tree regression tests). `cargo fmt
--check`: clean.

The sequential rows are expected to equal the §8 pinned values
(`d827...cc9df` / `22f6...050f6`) exactly — that equality, not just
"still PASS," is the proof that this leg touched nothing on that path.
The tree rows are new values with no prior pin to compare against; their
significance is Rust-tree == C++-host-tree, not equality to the
sequential digests (which would in fact indicate a bug — see the design
doc's "plan-wording bug" note).

### 12b. `nofma-cuda` — SASS-level no-FMA, real device object code

`make -C gpu nofma-cuda` compiles `cis2_sass_probe.cu` with nvcc
(`NVCC_ARCH=sm_75`, Kaggle T4, override with `NVCC_ARCH=sm_60` for a
P100) to a relocatable device object — real SASS, never linked, never
run — and greps `cuobjdump --dump-sass` per kernel function:

| kernel | contains division/sqrt? | FFMA gate |
|---|---|---|
| `k_dot_seq` / `k_sum_seq` | no | strict zero |
| `k_dot_tree` / `k_sum_tree` | no | strict zero |
| `k_softmax_seq` / `k_softmax_tree` | yes (`logits[i]/denom`) | reported, not gated — `-prec-div=true` division on an architecture with no hardware DIV instruction (Turing included) is legitimately a `MUFU.RCP` + Newton–Raphson refinement sequence containing FFMA; this is the documented exception, not a violation of §1.4 |

Result (`make -C gpu nofma-cuda NVCC=/usr/local/cuda/bin/nvcc
CUOBJDUMP=/usr/local/cuda/bin/cuobjdump`, real SASS for sm_75):

| kernel | FFMA count |
|---|---|
| `k_dot_seq` | 0 |
| `k_sum_seq` | 0 |
| `k_dot_tree` | 0 |
| `k_sum_tree` | 0 |
| `k_softmax_seq` | 47 (division refinement — expected, not gated) |
| `k_softmax_tree` | 47 (division refinement — expected, not gated) |

`no-FMA-cuda gate: PASS`. The two softmax kernels' FFMA counts are
identical (47 each) — consistent with the hypothesis that every one of
those instructions comes from the shared `logits[i] / denom` division
sequence (`-prec-div=true` on sm_75, which has no hardware DIV
instruction), since `k_softmax_seq`'s denominator (`cis2_sum_seq`) and
`k_softmax_tree`'s (`cis2_tree_sum`) are independently proven zero-FFMA
above — the two softmax kernels differ ONLY in which zero-FFMA sum they
call, so an identical non-zero count in both isolates the source to the
one thing they share (the division), not to either reduction order.

`make -C gpu cuda cuda-tree NVCC=/usr/local/cuda/bin/nvcc` — the FULL
host driver (weights/JSON/safetensors loading, the whole forward pass,
not just the reduction kernels) — also compiles cleanly to a real device
object (`.o`, 110 448 / 112 544 bytes) for sm_75, in both modes, with no
errors. This is new: previously (E18b) this box had no `nvcc` at all and
`cuda` had never been compiled. It is still never linked and never run.

### 12c. What this leg did and did not establish

**Established**: the v0.4 CANDIDATE pinned tree order is specified
precisely enough that two independent implementations (Rust reference,
C++ host build) compute bit-identical results from it, on real weights,
at two token counts, with per-op trace equality — the same bar §8 already
cleared for the sequential order. The C++ single source now compiles
under nvcc with the tree macro defined, and the tree kernels' compiled
SASS contains no FMA. The v0.3b sequential digests are unchanged.

**Not established**: anything about GPU *execution* — no kernel here has
run on a device (§11's Kaggle leg remains the first real-GPU run,
whenever quota allows, and should exercise both `-DCIS2_REDUCTION_TREE`
and its absence). Not established: that the tree order's numerical
values are "more correct" than the sequential order's — per
`docs/E15b_m1p5_CORRECTNESS.md`, correctness (agreement with an
independent torch/transformers oracle at the token-id level) has already
been shown to be insensitive to which particular valid reduction order is
used; this leg is about cross-implementation bit-identity of a
GPU-parallelizable order, not a correctness re-check.
