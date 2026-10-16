# lt-2: Lightning AI T4 replay of gpu-3k batched-forward sweep (third GPU host)

Leg: lt-2 (FRONTIER-1). Published 2026-10-16 as part of the CIS-2 archive. Date: 2026-09-25. Source: worktree
`<home>/projects/cis2-fp-cm-gpu3`, branch
`cm/gpu3-batched-full`, commit `1c6f592b761354cbd0615bbc81608ffd8e6199be`
(verified `git rev-parse HEAD` before the run; unchanged from the
expected sha). Recipe followed: `gpu/kaggle_gpu3/GPU3K_RESULT.md` and
`gpu/kaggle_gpu3/plan.py` (Kaggle T4 run, 2026-09-19), adapted to a
Lightning AI Studio instead of a Kaggle kernel.

Full raw Studio output (build log + every run's stdout, env facts at the
top): `state/reports/lightning-logs/2026-09-25-lt2-gpu3-t4.log`.

## Host facts (from the log)

- GPU: `Tesla T4` (`nvidia-smi -L`), driver `580.178.04`.
- CUDA: `nvcc` release 13.0, V13.0.88 (Kaggle's v2 run used CUDA 12.8;
  this is a different CUDA toolkit minor version, noted as a deviation
  from the Kaggle recipe below).
- CPU: `Intel(R) Xeon(R) Platinum 8259CL CPU @ 2.50GHz` (AWS instance
  behind the Studio, `ip-10-192-16-104`).
- OS: `Linux 6.8.0-1063-aws #66-Ubuntu SMP ... x86_64` (Ubuntu, AWS
  kernel) -- Kaggle's host was a Kaggle-image CPU; this is a third,
  independent x86_64 host/toolchain combination.
- Weights: `HuggingFaceTB/SmolLM2-135M` fetched directly from
  `huggingface.co/.../resolve/main/{config.json,tokenizer.json,model.safetensors}`
  (public, no token). sha256: config.json
  `1d556eab73b69c7f11f64c557a2f9c6f440bd4c6b89bb2584a6b498c92603843`,
  tokenizer.json
  `9ca9acddb6525a194ec8ac7a87f24fbba7232a9a15ffa1af0c1224fcd888e47c`,
  model.safetensors
  `80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1`.

## Build

- Host (g++): `g++ -std=c++17 -O2 -ffp-contract=off -fno-fast-math -msse2
  -mfpmath=sse -I. cis2_host.cpp -o cis2_host_gcc` -- OK.
- CUDA (nvcc, linked executable): `nvcc -x cu -std=c++17 -O2 -fmad=false
  -ftz=true -prec-div=true -prec-sqrt=true --extended-lambda
  -DCIS2_CUDA_FTZ=1 -arch=sm_75 -I. cis2_host.cpp -o cis2_host_cuda` --
  OK, no SIGSEGV (the v1-Kaggle bug this branch's `cis2_k_matmul_batched`
  fix addressed was not reproduced -- expected, since this tree already
  carries the fix).
- Also compile-checked locally on penguin first (host/g++ arm only, no
  weights, no run) before spending any Lightning credit: OK.

## Digest table

All six runs (host x {1,4,8}, cuda x {1,4,8}) reached a printed
`==== gpu-3 --batch B: PASS ====` verdict. Row 0 digest is identical
across every run and equals the pinned `EXPECTED_DIGESTS.md`
`sequential.16` witness:

`d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df`

Per-row `batched_witness_digest` values were byte-identical to the
row's own `standalone_batch1_witness_digest` in every run (all
`vs_standalone_batch1: MATCH` lines), and byte-identical across the
host and cuda binaries at every B. They also match the box1 CPU
(gpu-3) and Kaggle T4 (gpu-3k v2) values recorded in
`GPU3K_RESULT.md` exactly, e.g. for B=8:

| row | prompt (last id) | witness digest (this run, host & cuda) |
|---|---|---|
| 0 | 655 | d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df (pinned MATCH) |
| 1 | 656 | b34a64b86d50b4f1400ecf05e1355fd1558c733cf9912369e36fa8a8386da80a |
| 2 | 657 | 42c9dab3646bac3bcfcc82be4ab0fabe77e7bab2d4b2f8920129dd238ca8d707 |
| 3 | 658 | c01515277ca944815041d1e904a5f19096192b6214f3814e4712f5531b18e501 |
| 4 | 659 | 6147e8feccf9349c5797fd315385c83461ea7f659dddebc65bdd48291082daf0 |
| 5 | 660 | cdbceaf8822f9bbefdf7172068608fc84771e42a415cf20aa81634ddbc40867b |
| 6 | 661 | 79bbc2ec3d44066519afe2672fd33651b6332be2e27804b9f585df419064b4ef |
| 7 | 662 | b4ac49e22cca1a691d2a0b51cc409afbdff1dc1ee1132a4f2d622d9092a5de63 |

All values copied verbatim from the log (grep-checked, not retyped by hand).

## MATCH/MISMATCH per arm

| B | host verdict | cuda verdict | host==cuda all rows |
|---|---|---|---|
| 1 | PASS | PASS | MATCH |
| 4 | PASS | PASS | MATCH |
| 8 | PASS | PASS | MATCH |

No mismatch found anywhere. This is a third, independent GPU host
(Lightning AI T4, AWS-backed) reproducing the same digests as box1 (CPU)
and Kaggle (T4). It is one GPU model (T4), one gate prompt family, one
16-token greedy run; it says nothing about other GPUs, larger batches,
other prompts, or timing (no timing was recorded).

## Deviations from the Kaggle recipe

- CUDA toolkit: nvcc 13.0.88 here vs 12.8.93 on Kaggle's v2 run (both
  `-arch=sm_75`).
- Weights sourced directly from Hugging Face on the Studio (curl, public,
  no token) instead of a pre-staged Kaggle dataset; Kaggle's
  `cis2-e18b-gpu` dataset weights were themselves originally sourced from
  the same HF repo, so this is a difference in staging mechanism only.
- No overlay-dataset step was needed (Lightning has internet + this
  worktree's own `gpu/` tree was tarred and uploaded directly, so there
  was no stale base tree to overlay over, unlike Kaggle's two-dataset
  pattern).
- `plan.py` itself was not run on Lightning; its build/run commands and
  its `ROW_DIGEST_RE`/verdict logic were reproduced by hand in a shell
  script (`run.sh`) and the raw binary output was read directly instead
  of through the script's parser -- avoids the known plan.py summary-table
  regex bug documented in GPU3K_RESULT.md's v2 section (fixed after that
  run, not re-verified here since no parser was used).

## Not verified

- No independent check that `huggingface.co`'s served `model.safetensors`
  for `HuggingFaceTB/SmolLM2-135M` is byte-identical to the copy at
  `<home>/projects/cis2-fp/weights/model.safetensors`
  used by earlier legs (both are public HF downloads of the same repo;
  sha256 of the Studio's copy is recorded above but not diffed against
  penguin's local copy in this leg).
- Lightning credit balance was not queried; the T4 session ran ~134s of
  wall time inside the started Studio (well under the 30-minute bound)
  plus Studio start/stop overhead; no credits total was visible in the
  CLI output used here.
