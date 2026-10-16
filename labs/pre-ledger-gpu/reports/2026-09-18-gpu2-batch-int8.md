# gpu-2: batch={4,8} + INT8 extension of E18 — status report

2026-09-18, cm-builder subagent.

## Bottom line

**Prepared-but-not-run.** No CUDA/int8 kernel code was written, no Kaggle
kernel was pushed, no digests (real or otherwise) were produced. This was
a deliberate scope decision under this session's compute/token budget,
not a credentials blocker — Kaggle CLI + `~/.kaggle/access_token` are
present and usable on this box.

## What exists today (findings)

Grepped `gpu/cis2_host.cpp`, `gpu/cis2_model.h`, `gpu/cis2_math.h`,
`gpu/Makefile` in `cis2-fp` for `batch|int8|INT8|quant`: zero matches.
E18/E18c is batch=1, fp32-only, end to end — there is no batching
dimension threaded through the matmul/attention code and no quantized
weight path at all. Extending it is real new kernel work, not a flag.

## What was delivered this session

Branch `cm/gpu2-batch-int8`, worktree `~/projects/cis2-fp-cm-gpu2`
(cis2-fp main tree untouched), pushed to origin (no PR opened, per
instructions — internal branch only):

- `gpu/kaggle_gpu2/BATCH_INT8_DESIGN.md` — design doc distinguishing two
  ways to "batch": (1) row-batch (B independent forward passes, reuses
  existing sequential reduction, expected to MATCH batch=1 — low
  information value) vs (2) true grouped/strided GEMM batching (a
  different reduction tree, plausibly changes fp32 rounding — this is
  the arm that could produce a genuine MISMATCH finding, mirroring the
  already-known-to-diverge `-DCIS2_REDUCTION_TREE` CANDIDATE path from
  E18c). Also specifies a recommended int8 quant scheme (per-channel
  symmetric, Q8_0-style) and 6 concrete next-implementation-steps.
- `gpu/kaggle_gpu2/plan.py` — driver scaffold (adapted from
  `gpu/kaggle/e18b_gpu.py`'s dataset/build pattern) that documents the 6
  target configs (batch{1,4,8} x {fp32,int8}) and their expected
  MATCH/MISMATCH semantics, but raises `NotImplementedError` on import
  rather than faking a run.

## Why stopped here

Writing a correct batched-reduction CUDA kernel and an int8 dequant path
in the remaining session budget risked exactly the failure mode this
project's rules warn against: a silently-wrong kernel producing a
digest that looks like a result but isn't trustworthy. The design doc's
step-by-step (row-batch first, sanity-check MATCH, then grouped-GEMM,
then int8) is written so a future tick or human can pick it up directly.

## Exact next action

Implement design-doc steps 1-4 in `gpu/cis2_model.h`/`cis2_math.h` on
`cm/gpu2-batch-int8`, then push via
`~/.local/bin/kaggle kernels push -p gpu/kaggle_gpu2` — after adding a
kernel-metadata.json and dataset (copy `gpu/kaggle/make_dataset.sh`
pattern) and, per `gpu/kaggle/push.sh`'s own guard, confirming GPU quota
and ALICE-ternary-kernel priority before pushing.

Suggest adding to QUEUE.md: `- [ ] gpu-2: implement batched/int8 CUDA
kernels per gpu/kaggle_gpu2/BATCH_INT8_DESIGN.md, push+run on Kaggle
(track: kaggle)` — this is not yet a NEEDS/BLOCKERS item (no Justin-only
action required, just more build time).
