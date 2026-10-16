# gpu-2 (cis2-fp) steps 5-6: Kaggle GPU sweep v2 — SUCCESS, all arms match expected pattern

Worktree: `<home>/projects/cis2-fp-cm-gpu2`, branch `cm/gpu2-batch-int8`, pushed commit `fdd3ddb`.

## What changed from v1 (two diagnosed root causes fixed)
1. **Stale overlay** — `aefinityaiinc/gpu2-sweep-overlay` only shipped `cis2_sweep.cpp` + `cis2_math.h`, so the nvcc build pulled a stale `cis2_fpenv.h` from the base `cis2-e18b-gpu` dataset (pre-8b81095 guard, always `#error`'d). Fixed: overlay dataset v2 now ships the full `gpu/` source snapshot (`cis2_fpenv.h`, `cis2_math.h`, `cis2_model.h`, `cis2_sha256.h`, `cis2_sweep.cpp`, `cis2_host.cpp`) and `plan.py`'s `overlay_sweep_sources()` copies every `.h`/`.cpp` in the overlay dir as before.
2. **Wrong ids source** — `gate/ids_16tok.txt` (Rust `--dump-ids` output) holds only the 4 prompt token ids, never the 16 generated ones. Fixed: `plan.py` now builds + runs the real `cis2_host` driver (`g++ -DCIS2_BATCH_GROUPED cis2_host.cpp`) against `ids_16tok.txt` with `--gen-toks 16`, parses the 16 `[run1] step N: token_id=U` lines from stderr, and writes `gate/ids_sweep20.txt` = 4 prompt + 16 generated ids. It also compares the host run's `run1_witness_digest` to `gate/expected_digests.json`'s `["sequential"]["16"]["digest"]` and prints a `HOST_GATE` sanity line.

## Kaggle run (kernel v2)
- GPU: `nvidia-smi --query-gpu=name` → **Tesla T4**; `Selected NVCC_ARCH: sm_75`.
- Overlay sha256 lines (all 6 files, from the fetched log):
```
overlay cis2_fpenv.h sha256=9c1a809d90b1b11d5b39fc4c67b498fbc818125a72e9bbd6c4ad3760bf3c82de
overlay cis2_host.cpp sha256=9232e25e0cb4a424dec5a6d39d17f4dd7cef3192cea4968dbb18a43ec21cffe8
overlay cis2_math.h sha256=0d48fd1e4d37956795a1545f889138f7cc9ed7689087db80dc0fc8ab7b8cb53a
overlay cis2_model.h sha256=3455427e3c2be51c3c3492c8bea3e76f99c5cc867a8ef58d736b9c9287fcb003
overlay cis2_sha256.h sha256=ef9eaadec8a5ba4fb1ba3ef2f44604be460c4e0122f82b193e7dc73346939fa7
overlay cis2_sweep.cpp sha256=a05e27bc6adeadf3289ad9fc9684278f4917b8898e5f5c58db09192b6e48e79f
```
- `HOST_GATE`:
```
HOST_GATE digest=d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df expected=d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df MATCH
```
- `gate/ids_sweep20.txt` (20 ids: 4 real prompt + 16 real greedy-generated, sha256=`131c7a1beada67f377aa7db434405fa5349f450871be5b0f584fe2b5a4d5eeac`):
```
6403 1980 253 655 28 665 436 253 1838 8180 3365 14176 30 2306 4161 281 253 2066 2291 351
```
- Both builds succeeded: `---- host build: OK`, `---- cuda build (sm_75): OK` — the ROOT CAUSE 1 `#error` is gone.
- Both host (g++, CPU) and cuda (nvcc, T4) runs completed (`returncode=0`, 10 SWEEP lines each) and printed **identical** digests to each other for every config.

## SWEEP table (host run; cuda run is byte-identical, see log)
| config | digest (first 16 hex) | vs_cpu_batch1 | diffs |
|---|---|---|---|
| host_control_batch1_fp32 | 9a8e923498185888… | MATCH | 0/576 |
| batch1_fp32_seq | 9a8e923498185888… | MATCH | 0/576 |
| batch1_fp32_grouped | f1ba46ce729afea3… | MISMATCH | 455/576 |
| batch1_int8 | 413114502d874b10… | MISMATCH | 576/576 |
| batch4_fp32_seq | 34a369808e935938… | MATCH | 0/576 |
| batch4_fp32_grouped | 6bf560c9f29a3d8d… | MISMATCH | 455/576 |
| batch4_int8 | 31d0109235031d12… | MISMATCH | 576/576 |
| batch8_fp32_seq | ada5b5de31aa3306… | MATCH | 0/576 |
| batch8_fp32_grouped | 23fae4007ee7f42c… | MISMATCH | 455/576 |
| batch8_int8 | c9e186c9c39cf36d… | MISMATCH | 576/576 |

`SWEEP_DONE weights=/kaggle/working/gpu2/weights/model.safetensors ids=/kaggle/working/gpu2/gate/ids_sweep20.txt layer=0 hidden_size=576 n_ids=20`
`SWEEP_SUMMARY matched=8/20` (host's 8 MATCH + cuda's 8 MATCH, out of 20 rows total across both binaries — this is a build/binary count, not a claim that grouped/int8 "should" match; see expectation check below).

## Expectation check (BATCH_INT8_DESIGN.md: fp32-seq MATCH at all batch sizes, grouped MISMATCH, int8 MISMATCH)
- **Matches expectation exactly, both binaries, all batch sizes.** fp32-seq MATCH at batch 1/4/8 (host and cuda); fp32-grouped MISMATCH at batch 1/4/8; int8 MISMATCH at batch 1/4/8. No batch-4/8 seq mismatch, no grouped MATCH — nothing surprising to flag.
- Host and cuda produced bit-identical digests for every one of the 10 configs (same NVCCFLAGS_BASE reproducing host fp32 bit-for-bit on this Kaggle CUDA path, as established by E18).

## Build/run failures
None in this run — both builds OK, both runs returncode=0, no FATAL lines.

## Commit / push
- Branch: `cm/gpu2-batch-int8`
- Commit: `fdd3ddb` (pushed to `origin`, Aefinity-AI/cis2-fp.git)
- Files: `gpu/cis2_sweep.cpp` (docstring fix), `gpu/kaggle_gpu2/plan.py` (overlay + HOST_GATE + ids_sweep20 build), `gpu/kaggle_gpu2/overlay_staging/*` (full source snapshot added), `gpu/kaggle_gpu2/runs/2026-09-19-gpu2-sweep-v2.log`.
- `gpu/kaggle_gpu2/overlay_staging/dataset-metadata.json` pushed as `gpu2-sweep-overlay` dataset version 2 (confirmed `status: ready` before the kernel push).
- Kernel `aefinityaiinc/gpu2-batch-int8` version 2, `KernelWorkerStatus.COMPLETE`.
- Untracked binaries `gpu/test_batch`, `gpu/test_batch_grouped`, `gpu/test_batch_int8` left uncommitted per instruction.
- NOT merged to main, main untouched. Not published (private Kaggle dataset/kernel, private repo).

## Not verified / out of scope this pass
- Only layer 0's `q_proj` matmul is exercised (stated scope in `cis2_sweep.cpp`'s docstring) — not a full forward pass.
- No further retry needed (v2 succeeded on first re-push).

---

## v1 failure (superseded, kept for history)
v1 (commit `7942597`) failed for the two root causes fixed above: cuda build hit `cis2_fpenv.h`'s `#error` (stale overlay missing that file), and the host run hit `FATAL: need >=8 token ids in .../ids_16tok.txt, got 4` (file only ever had the 4 prompt ids). `SWEEP_SUMMARY matched=0/0`, no SWEEP lines produced. Log: `gpu/kaggle_gpu2/runs/2026-09-19-gpu2-sweep.log`.
