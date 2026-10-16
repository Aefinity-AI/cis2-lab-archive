# gpu-2: batch={4,8}/int8 digest sweep — 2026-09-18 tick 2 progress

Repo: `~/projects/cis2-fp-cm-gpu2` (worktree), branch `cm/gpu2-batch-int8`
(pushed). Never touched `main`. No Kaggle kernel run or credentials used
this tick — CPU-only.

## What got done

Implemented design-doc step 2 for real: `cis2_matmul_batched_seq(B, n, k,
x, w, out)` added to `gpu/cis2_math.h` — loops the existing, unmodified
`cis2_dot_seq` once per (row, output-column), same order as B independent
batch=1 calls (the "row-batch / case 1" arm, expected to be digest-safe
because it introduces no new arithmetic).

Added `gpu/test_batch.cpp` + a `test_batch` Makefile target: CPU-only,
deterministic synthetic inputs (no real model weights — this is a
math-level plumbing check, not the batch1_fp32 anchor from
`gpu/EXPECTED_DIGESTS.md`), B=4, irregular n=37/k=129. Compares SHA-256
digest of the batched path vs B sequential batch=1 calls.

## Real result (not fabricated)

**MATCH.** Both digests equal
`d241d2052ee1f4a6236426509d35cb069c17f477405ffa6cb31d1db9ac3493ba`, 0/148
elements bitwise-different. Reproduce: `make -f gpu/Makefile test_batch`
from repo root.

This is the expected, low-risk outcome per the design doc's own framing
(case 1 has no new reduction order) — a genuine confirmation, not the
interesting/MISMATCH-risk case. That's step 3 (grouped/strided reduction,
`-DCIS2_BATCH_GROUPED`, mirroring the existing `-DCIS2_REDUCTION_TREE`
precedent) and the int8 dequant path (step 4) — both still TODO.

## Resume point for next tick

1. Do design-doc step 3 next: a grouped/strided-reduction batched matmul
   variant (host-side first, still CPU-only/no-Kaggle-needed) behind
   `-DCIS2_BATCH_GROUPED`. This is the arm actually expected to risk a
   digest MISMATCH (non-associative fp32 + different reduction tree
   shape) — report honestly either way.
2. Only step 3's CUDA leg needs nvcc (compile-only on this box, no
   physical GPU here); a real Kaggle P100/T4 GPU run is only needed once
   configs are wired into `gpu/kaggle_gpu2/plan.py` for steps 5–6 (int8
   quant scheme + full 6-config sweep + `kaggle kernels push`). Do not
   start that until step 3/4 are done and reviewed — per
   `gpu/kaggle_gpu2/plan.py`'s own push-priority note (must not collide
   with another GPU kernel or the existing e18b-gpu push timer).
3. Full detail and exact next-step list: see
   `gpu/kaggle_gpu2/BATCH_INT8_DESIGN.md` progress note (2026-09-18 tick
   2) and `gpu/kaggle_gpu2/plan.py`'s updated TODO header.
