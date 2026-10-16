# gpu-2: batch+int8 determinism — progress 2 (step 4, int8 quantization)

Worktree: `~/projects/cis2-fp-cm-gpu2`, branch `cm/gpu2-batch-int8` (pushed to
origin at `79c55f8`, NOT merged to main). CPU-only work, no Kaggle/GPU
execution.

## What was done

Design doc's step 1 (decide the int8 quant scheme) and step 4 (implement
it) from `gpu/kaggle_gpu2/BATCH_INT8_DESIGN.md`:

- Scheme: per-output-channel (per weight-row) symmetric int8, `scale =
  max(abs(row)) / 127`, round-half-away-from-zero, clamp to [-127, 127]
  (Q8_0-style). Weight-only quantization; activations stay fp32; dequant
  happens ON-THE-FLY inside the matmul inner loop (per the design doc's
  own preference — this exercises real arithmetic, not just I/O).
- Implemented `cis2_quantize_row_i8` and `cis2_matmul_batched_int8` in
  `gpu/cis2_math.h`, same style/house rules as the existing batch code
  (no FMA, separate mul/add, strict left-to-right accumulation matching
  `cis2_dot_seq` so any mismatch is attributable to quantization alone).
- Extended `gpu/test_batch.cpp` (built with `-DCIS2_BATCH_INT8`, new
  `test_batch_int8` Makefile target) to quantize the same deterministic
  test weight matrix, run the int8 matmul, and compare its digest against
  the fp32 batch=1-equivalent reference.

## Real result (not fabricated)

Built and ran `make -f gpu/Makefile test_batch_int8` locally (CPU-only):

```
BATCH_TEST B=4 n=37 k=129 batched_digest=d241d205... seq_digest=d241d205... bitwise_diffs=0/148
BATCH_TEST RESULT: MATCH
BATCH_INT8_TEST B=4 n=37 k=129 int8_digest=8ef80ce8... seq_digest=d241d205... bitwise_diffs_vs_seq=148/148 max_abs_diff=0.16224861 mean_abs_diff=0.04701660
BATCH_INT8_TEST RESULT vs seq: MISMATCH
```

MISMATCH at all 148/148 output elements vs the fp32 reference —
expected, a priori, per the design doc's framing (int8 quantization
perturbs essentially every dequantized weight, unlike step 3's grouped
reduction which was a pure reduction-order effect). Magnitude:
max_abs_diff ≈ 0.162, mean_abs_diff ≈ 0.047 over inputs drawn from
[-2, 2). Steps 2 and 3 were re-run and confirmed unchanged (no
regression): step 2 still MATCH (`d241d205...`), step 3 still MISMATCH
122/148 vs `d0e4116d...`, both bit-identical to prior ticks.

Progress note appended to `gpu/kaggle_gpu2/BATCH_INT8_DESIGN.md`. Commit
`79c55f8` on `cm/gpu2-batch-int8`, pushed to origin, not merged to main.

## Remaining (RESUME)

Steps 5-6 only: wire `cis2_matmul_batched_seq`/`_grouped`/`_int8` into
`plan.py`'s digest table against real model weights (current tests use
synthetic xorshift32 data, not the model), then an actual Kaggle P100/T4
GPU sweep + kernel push (kaggle CLI creds present). Optionally a
compile-only CUDA leg for `-DCIS2_BATCH_GROUPED` first (cheap, no GPU).
