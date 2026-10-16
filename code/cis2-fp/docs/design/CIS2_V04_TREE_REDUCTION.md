# CIS-2 v0.4 CANDIDATE — pinned tree reduction order (E18c)

Published 2026-10-16 as part of the CIS-2 archive. Not a spec revision yet — a
**candidate** normative reduction order, proposed on top of the still-fully
-intact v0.3b sequential path. See `gpu/README.md` and
`~/projects/claudius-maximus/state/reports/2026-09-02-E18-cis2-gpu-memo.md`
(the E18 memo, critic point 7) for why this leg exists: v0.3b's strict
left-to-right reduction is exactly correct on CPU/CPU-cross-ISA but maps to
a one-thread-per-output-row, fully-serial-over-the-reduction-dimension GPU
kernel — parallel over rows, not over the reduction itself. A pinned
blocked-tree order is a prerequisite for a GPU kernel that also parallelizes
*within* a row, and it must be specified precisely enough that a CPU
reference and a CUDA kernel compute the identical bits from it.

**Plan-wording bug, corrected here:** an earlier framing of this leg implied
a tree reduction could reproduce the v0.3b sequential digests
(`d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df` at 16
tokens, `22f69ad87a615d66a77efaca8b1172d22bdfb4bd5092ceffd302e35669a050f6` at
128 tokens). It cannot: a different summation order over non-associative
fp32 addition produces different rounding, hence a different bit pattern,
hence a different digest, in general. **The correct claim for this leg has
two independent parts:**

1. The v0.3b sequential digests above are **reproduced unchanged** — the
   sequential code path (`dot_seq`, `sum_seq`, `softmax_seq` in
   `src/math.rs`, and their C++ mirrors) is not touched by this work at
   all, so a run with `--reduction sequential` (the default) is
   byte-for-byte the same program it always was.
2. A **new** PREP-PASS digest pair is established for tree mode: Rust-tree
   and C++-host-tree agree with each other, bit-for-bit, at 16 and 128
   tokens. These are **new, v0.4-CANDIDATE digests**, not equal to the
   v0.3b ones, and are not claimed to be. See §5 for the actual values,
   recorded after the proof run.

## 1. The pinned order

**Block size `B = 32`.** One CUDA warp, exactly. This is the whole reason
for the choice: a 32-lane block reduces via a warp-shuffle butterfly
(`__shfl_down_sync` at offsets 16, 8, 4, 2, 1 — 5 rounds, no shared memory,
no `__syncthreads()`, no bank conflicts) with *zero* control-flow branching
on lane id, because the padding rule below (not the kernel) is what handles
a block that isn't full. The same 5-round halving is a 5-iteration loop on
a CPU. Every dimension this leg's two model families actually reduce over
divides 32 evenly (SmolLM2-135M: hidden=576=18×32, intermediate=1536=48×32,
vocab=49152=1536×32; Qwen2.5-0.5B: hidden=896=28×32, intermediate=4864=
152×32, vocab=151936=4748×32) — so for every `matvec` (q/k/v/o/gate/up/
down/lm_head) and for RMSNorm's sum-of-squares (over `hidden`), block size
32 produces **zero ragged blocks** on both checkpoints in this repo. The
ragged-tail rule below exists anyway, and is exercised for real, because
softmax's reduction length is `pos + 1` (the causal attention window),
which is *not* a multiple of 32 for almost every position in a real
decode — e.g. `pos=0` gives a softmax over exactly 1 score.

**Order, precisely, as one function `tree_reduce(values: &[f32]) -> f32`
that both `tree_sum` and `tree_dot` are built from:**

1. Split `values` (length `n`) into consecutive blocks of `B = 32`:
   block `blk` covers indices `[blk*32, blk*32+32)`, the last block
   possibly shorter (`ragged tail`, see below). `num_blocks =
   ceil(n / 32)`.
2. **Within each block**, gather up to 32 leaves into a fixed-size buffer
   `leaf[0..32)` (real values at their in-block index, see tail rule for
   what fills the rest), then reduce that fixed 32-slot buffer by a fixed
   pairwise tree, five rounds, each round halving the live width:
   ```
   width = 32
   while width > 1:
       half = width / 2
       for i in 0..half:
           leaf[i] = leaf[2*i] + leaf[2*i+1]
       width = half
   block_partial = leaf[0]
   ```
   Round 1 folds 32→16 (16 independent adds: `leaf[0]+leaf[1]`,
   `leaf[2]+leaf[3]`, ...), round 2 folds 16→8, ..., round 5 folds 2→1.
   Every add within a round reads two positions no other add in that round
   reads or has yet written (indices `2i, 2i+1 ≥ i` for all `i` in the
   loop, and no later `i' > i` in the same round ever reads index `i`),
   so processing `i = 0..half` in increasing order and writing in place is
   safe with no aliasing hazard — the same property that makes it a valid
   `__shfl_down_sync` butterfly on a GPU (each lane only ever needs a
   value that hasn't been overwritten by a lower lane yet) and a trivial
   inplace CPU loop.
3. **Combine the per-block partials strictly left-to-right**, exactly
   §3.1's existing sequential rule, now applied one level up (over
   `num_blocks` values instead of over `n`):
   ```
   acc = 0.0
   for blk in 0..num_blocks:
       acc = acc + block_partial[blk]
   return acc
   ```

`tree_sum(a)` is `tree_reduce` with leaf `i` = `a[i]`. `tree_dot(a, b)` is
`tree_reduce` with leaf `i` = `a[i] * b[i]` — the multiply is a separate,
separately-rounded operation computed once per leaf as it is gathered
(§3.2's no-FMA rule is untouched: nothing in this document introduces a
fused multiply-add anywhere, at any level).

## 2. Ragged-tail rule: **zero-pad**

For the last block, when `n` is not a multiple of 32, the missing leaf
slots (`leaf[len..32)` where `len = n - blk*32 < 32`) are filled with
`+0.0` rather than, e.g., re-running a shorter ad-hoc tree over just the
real elements.

**Why zero-pad, not a separately-shaped sequential tail:**

- **Uniform kernel, no divergence.** Every block — full or ragged — runs
  the *identical* 5-round fixed-tree code with no branch on `len`. A CUDA
  warp reduction never needs an `if (lane < len)` guard inside the
  shuffle loop; out-of-range lanes just carry `0.0` into the butterfly.
  This is the standard idiom for warp-level partial reductions and is the
  concrete reason B=32 (a warp) was chosen over some other block size:
  the padding rule and the hardware primitive are the same shape.
- **It is not an approximation.** `+0.0` is the exact additive identity
  for every finite, non-negative-zero-sensitive value. Tracing the
  algebra: a padded leaf at index `j` (`j ≥ len`) contributes `0.0` to
  every partial sum it participates in at every round (`0.0 + 0.0 =
  0.0` exactly; `x + 0.0 = x` exactly, for any finite `x`, under
  round-to-nearest — the one caveat, `x = -0.0`, is addressed below).
  Unwinding the fixed 32-slot tree with the tail zero-padded therefore
  collapses to a **specific, well-defined, deterministic binary tree over
  exactly the `len` real leaves** — e.g. for `len = 5` (`pos=4`,
  `softmax` over 5 scores): round 1 pairs `(0,1)→p01`, `(2,3)→p23`,
  `(4, pad)→leaf[4]` (unchanged, since it added `0.0`), and everything
  from index 5 up is `pad+pad=0.0`; round 2: `(p01,p23)→p0123`,
  `(leaf[4], 0.0)→leaf[4]`; round 3: `(p0123, leaf[4])→p01234`; rounds 4–5
  combine `p01234` with more zeros and it is unchanged. Net:
  `((a0+a1)+(a2+a3))+a4` — a real, left-leaning binary tree on the 5
  actual values, not a "same as sequential" degenerate case and not an
  approximation of one.
  This is *why* padding is safe to reason about formally: the padded tree
  is always **some** fixed, n-independent-of-thread-count binary tree
  shape over the real leaves (determined purely by which block/lane
  positions they land in), never a value-dependent one, so it is exactly
  as deterministic as a hand-specified ragged-tail tree would be, at a
  fraction of the implementation complexity (one code path, not two).
- **Deterministic irrespective of thread count.** Whether the GPU launches
  32 threads and 27 of them read a garbage/never-fetched value replaced by
  an explicit `0.0f`, or 5 threads and the other 27 "don't exist," or the
  CPU reference runs it as a single-threaded loop, the *data* fed into the
  fixed tree is identical (`len` real values, `32-len` zeros), so the
  output bits are identical. This is the property the E18 memo (critic
  point 4) and this leg's brief both require: the reduction's bit pattern
  must be a function of the data and the pinned order, not of how many
  execution units happened to run it.
- **The one caveat — signed zero.** `x + (+0.0)` is exact for every
  finite `x` *including* `x = -0.0` under IEEE-754 round-to-nearest
  (`-0.0 + 0.0 = +0.0`, which does differ in sign from a bare `-0.0`, but
  a sign-of-zero difference is invisible to every consumer in this
  pipeline: `to_bits()` would see it, but no normative value in the
  decode path is ever a bare `-0.0` that isn't immediately added to
  something else — the only zero-producing paths, `ldexp_exact`'s
  underflow branch and `x=0.0` inputs, are already specified sign-blind
  per `gpu/README.md` §4 point 15). Not treated as a real hazard here;
  called out for completeness because "pick one and justify" demands it.

**Rejected alternative — sequential tail:** reduce the first
`floor(len/32)*32` elements via the fixed tree and fold the remaining
`len mod 32` elements with a plain `sum_seq`-style sequential loop,
combined into the running `acc` last. This is *also* fully deterministic
and would have been an equally valid choice. It was not picked because it
reintroduces exactly the branch-on-length problem the tree is trying to
get away from (a GPU kernel now needs a second, differently-shaped code
path for "the last few elements of a row," with its own launch
configuration or a scalar cleanup pass), for no bit-pattern benefit: the
zero-pad tail is provably a real, fixed tree over the true tail elements
(previous bullet), not a worse approximation of "the right answer" than a
sequential cleanup would be — it is simply a *different*, equally-valid
pinned order over those elements, which is all §3.1 ever required of the
v0.3b sequential rule too (that rule is also just one specific valid
choice among many, pinned for reproducibility's sake, not because it is
more "correct" than any other order).

## 3. Ops covered

Per the task brief, this candidate pins two reduction families:

| op | v0.3b sequential | v0.4 candidate | call sites |
|---|---|---|---|
| dot product (sum of products) | `dot_seq` — strict L→R, mul then separately-rounded add | `tree_dot` — §1, leaf `i` = `a[i]*b[i]` | `matvec` (q/k/v/o/gate/up/down/lm_head projections) **and** attention scores (`dot_seq(q_head, k_j)`) — both call sites route through the same `dot_seq`/`tree_dot` pair in the Rust reference and the same `cis2_dot_seq`/`cis2_tree_dot` pair in the C++ port |
| plain sum | `sum_seq` — strict L→R | `tree_sum` — §1, leaf `i` = `a[i]` | RMSNorm's sum-of-squares (`math::sum_seq(&sq)`); softmax's denominator sum (inside `softmax_seq`, now inside a new sibling `softmax_tree`) |

**Explicitly out of scope for this candidate:** the attention
weighted-sum accumulation (`main.rs:216-224`, `acc = acc + scores[j]*v[j][d]`
over `j` in position order) is a third reduction-shaped loop in the
codebase but is not routed through `tree_dot`/`tree_sum` here — the task
brief names only "dot products... and plain sums (RMSNorm sum of squares,
softmax sum)," and the weighted-sum loop is bounded by `pos+1 ≤ 128` in
this leg's proof runs (small relative to the 576/1536/49152-wide matvecs
that dominate FLOPs), so pinning its tree order is left to a future leg
rather than expanding this one's surface. It remains strictly sequential
in both `--reduction sequential` and `--reduction tree` modes; this is
recorded as a known gap, not a silent omission.

## 4. Implementation shape (both languages, one order)

- **Rust** (`src/math.rs`): `TREE_BLOCK: usize = 32`,
  `tree_block_reduce` (in-place 5-round halving over a fixed
  `[f32; 32]`), a generic `tree_reduce_indexed<F: Fn(usize) -> f32>(n,
  leaf_at)` that blocks/pads/reduces/combines per §1–2, and
  `tree_sum`/`tree_dot` as thin instantiations of it. `softmax_tree` is a
  **new, separate** function next to the untouched `softmax_seq` —
  identical max-scan and `exp_pinned` steps, denominator via `tree_sum`
  instead of `sum_seq`. Nothing in `dot_seq`, `sum_seq`, or `softmax_seq`
  is edited by this leg — new code only, selected by a CLI-level
  `Reduction` enum (`--reduction sequential|tree`, default `sequential`)
  threaded through `matvec`/`rmsnorm`/the attention score loop/the
  softmax call site in `src/main.rs` via two 4-line dispatch wrappers
  (`dot(a,b,mode)`, `sum(a,mode)`, `softmax(scores,mode)`). With
  `--reduction sequential` (the default, and every existing invocation
  with no flag at all), those wrappers call exactly the pre-existing
  `dot_seq`/`sum_seq`/`softmax_seq` — the same functions, same call
  arguments, same order — so the sequential digest is provably unchanged
  by construction, not just by testing.
- **C++** (`gpu/cis2_math.h`, `gpu/cis2_model.h`): `CIS2_TREE_BLOCK 32`,
  `cis2_tree_block_reduce`, a templated `cis2_tree_reduce_indexed<F>(n,
  leaf_at)` using the same `[=] CIS2_FN(...)` extended-lambda idiom this
  file already uses for `cis2_for_each` (so the identical lambda compiles
  under both the host build and `nvcc`'s `--extended-lambda`), and
  `cis2_tree_sum`/`cis2_tree_dot`. `cis2_softmax_tree` sits next to the
  untouched `cis2_softmax_seq`. Selection is a **compile-time** macro,
  `CIS2_REDUCTION_TREE`: `gpu/cis2_math.h` defines `CIS2_DOT(a,b,n)` /
  `CIS2_SUM(a,n)` / `CIS2_SOFTMAX(scores,n)` to expand to the tree or
  sequential functions depending on whether that macro is defined;
  `gpu/cis2_model.h`'s `cis2_k_matvec`, `cis2_rmsnorm`, the attention
  score kernel, and `cis2_k_softmax` call the macro, not the underlying
  function, at their one call site each. Building without
  `-DCIS2_REDUCTION_TREE` preprocesses to **exactly the prior source
  text** at those call sites — not merely "the same result," the literal
  same tokens reach the compiler — which is the strongest available form
  of "zero change to sequential-mode output" on the C++ side.
- Both languages mirror a runtime/compile-time distinction deliberately:
  the Rust reference is one binary that a human runs with a flag: a
  compile-time `#[cfg]` split would need two binaries and complicate the
  gate scripts for no benefit at CPU scale. The C++ port already builds
  two separate binaries per mode by convention in this repo (`host`,
  `host-gcc`, and now their `-tree` siblings), and CUDA in particular
  benefits from the mode being resolved at compile time (no runtime
  branch inside a device kernel body, no divergent warp on the branch
  itself) — so the two ports use the idiom that is cheapest and safest in
  each language, while implementing the identical §1–2 order.

## 5. Receipt: how the mode is recorded

`--reduction {sequential,tree}` is printed as `reduction_mode=<mode>` on
the `CIS2_REF` summary line and on a separate `prompt_idx=N
reduction_mode=<mode>` line, in both the Rust reference and the C++ port.
**It is not folded into the witness/`CIS2_REF` SHA-256 fold** — the fold
in `main.rs:554-577` (mirrored in `gpu/cis2_host.cpp`) is untouched byte
for byte, so `reduction_mode` is receipt metadata printed alongside the
digest (the same role `dtype=fp32` already plays on that line), not an
input to it. This is deliberate: folding the mode string into the witness
would change the *sequential* digest too (a different set of input bytes
hashes to a different output), which would contradict "the v0.3b
sequential digests stay byte-for-byte unchanged." A receipt holder who
cares which mode produced a given digest reads the printed
`reduction_mode=` field next to it; the digest itself continues to prove
only what it always proved (weights + tokenizer + config + tables +
prompt + generated logits/tokens), now for either reduction order.

## 6. PREP-PASS digests (v0.4 CANDIDATE) — FILLED IN

Proof run on penguin (`flock /tmp/aefinity-os.lock nice -n 10
systemd-run --user --scope -p CPUQuota=60% -p MemoryMax=2000M`,
SmolLM2-135M, `weights/`, `model.safetensors` sha256
`80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1`),
Rust reference at commit `04e5ad77fabec22745fd5180532c55672855f499`
(`cm/e18c-pinned-tree-reduction`), C++ host build (clang++) same tree,
next commit:

| mode | model | tokens | Rust digest | C++ host digest | equal |
|---|---|---|---|---|---|
| sequential | SmolLM2-135M | 16 | `d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df` | `d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df` | YES — equals the pinned v0.3b value |
| sequential | SmolLM2-135M | 128 | `22f69ad87a615d66a77efaca8b1172d22bdfb4bd5092ceffd302e35669a050f6` | `22f69ad87a615d66a77efaca8b1172d22bdfb4bd5092ceffd302e35669a050f6` | YES — equals the pinned v0.3b value |
| **tree (v0.4 CANDIDATE)** | SmolLM2-135M | 16 | `3f3b1ffceca02e8e0e78d5c653963480ea988ef41a378acc5393006ad378e1b3` | `3f3b1ffceca02e8e0e78d5c653963480ea988ef41a378acc5393006ad378e1b3` | YES — Rust-tree == C++-host-tree |
| **tree (v0.4 CANDIDATE)** | SmolLM2-135M | 128 | `112661fbfcb11440ae7d27c43e45135f8a6ff9f6bc01189d756c76dac96a0fdf` | `112661fbfcb11440ae7d27c43e45135f8a6ff9f6bc01189d756c76dac96a0fdf` | YES — Rust-tree == C++-host-tree |

At 16 tokens both modes also carry byte-identical per-(position, layer,
op) `--trace` files between the Rust reference and the C++ host build
(10 260 lines each, `cmp` clean) — `gpu/README.md` §5/§12. As predicted
in §"Plan-wording bug" above, the tree digests are **different from** the
sequential ones (`3f3b1ff...` ≠ `d827430...`, `112661f...` ≠
`22f69ad...`) — this is expected, not a defect: a different reduction
order over non-associative fp32 addition produces different rounding.
Full gate outputs, the `nofma-cuda` SASS results, and the real (never
before compiled on this box) `nvcc` object-file builds of the full C++
port are in `gpu/README.md` §12.
