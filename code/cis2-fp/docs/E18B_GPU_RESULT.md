# E18b / E18c — CIS-2 fp32 receipt reproduced on a GPU

**Status: PASS (v8, 2026-09-08). Supersedes the v5 write-up below.**

## Result (v8, Kaggle, 2026-09-08 12:07 UTC)

The CIS-2 v0.3b reference, compiled for CUDA and run on a **Tesla P100-PCIE-16GB
(sm_60, Pascal)** under `nvcc` 12.8 with
`-fmad=false -ftz=true -prec-div=true -prec-sqrt=true`, produced the same receipt
digests as the CPU reference on all four vectors, and a **byte-identical per-step
trace** at 16 tokens in both reduction modes.

| build | mode | tokens | digest | verdict |
|---|---|---|---|---|
| host g++ (Kaggle CPU) | sequential | 16 | `d82743059d1db929…` | PASS, trace byte-identical |
| host g++ (Kaggle CPU) | sequential | 128 | `22f69ad87a615d66…` | PASS |
| nvcc, P100 | sequential | 16 | `d82743059d1db929…` | PASS, trace byte-identical |
| nvcc, P100 | sequential | 128 | `22f69ad87a615d66…` | PASS |
| nvcc, P100, `-DCIS2_REDUCTION_TREE` | tree (v0.4 CANDIDATE) | 16 | `3f3b1ffceca02e8e…` | PASS, trace byte-identical |
| nvcc, P100, `-DCIS2_REDUCTION_TREE` | tree (v0.4 CANDIDATE) | 128 | `112661fbfcb11440…` | PASS |

Expected digests and reference traces were produced on penguin/box1 (x86-64, g++ and
clang++) before the dataset was uploaded on 2026-09-03.

**Trace identity is byte-level, not just digest-level.** The GPU 16-token trace, the
Kaggle host trace and the pre-baked CPU reference trace all hash to
`9a559a9e284c5e5b2a78b29c0dbab0e2bb2ce0c2e48069dd6bac20331cad46b6`; the tree-mode GPU
trace and its CPU reference both hash to
`40c931cd080da04f8e926f84e7f6f5605eada74cd8f858baa4be0d6ae955f0bf`. The two modes
differ from each other, which is the control that the diff is real.
See `hardware_logs/e18b-gpu-kaggle/2026-09-08-p100-v8-trace-sha256.txt`.

## What v8 fixed

Versions 6 and 7 were **false positives**. `nvcc_link` was missing `-x cu`, so
`cis2_host.cpp` compiled as host C++ and the "GPU" runs executed on the CPU. v8 adds
`-x cu`, fixes the two device-compile errors that change exposed, SASS-gates the
**real production binaries** (not a standalone probe), and samples `nvidia-smi`
during the 128-token runs.

Do not cite v6 or v7 for anything.

## Device-execution evidence

`cuobjdump --dump-sass` on the actual `cis2_cuda` and `cis2_cuda_tree` binaries
(return code 0) finds **13 `cis2_index_kernel` instantiations each** — the whole
forward pass is on the device, and there is no host fallback path when compiled
with nvcc.

`nvidia-smi` sampled once per second during the 128-token runs:

| run | samples | GPU util mean | max |
|---|---|---|---|
| `gpu_128tok` | 10 | 58.2 % | 87 % |
| `gpu_128tok_tree` | 11 | 61.6 % | 89 % |

This is a device-occupancy observation, not a performance measurement; no timing
number is claimed or published.

## FMA gate (SASS, real binaries)

Per binary, 63 FFMA instructions total across 13 kernels:

| kernel | FFMA | MUFU |
|---|---|---|
| `cis2_k_matvec` | 0 | — |
| `cis2_k_scores` | 0 | — |
| `cis2_k_attn_weighted_sum` | 0 | — |
| `cis2_k_add`, `cis2_k_add_bias`, `cis2_k_embed`, `cis2_k_store_kv` | 0 | — |
| `cis2_rmsnorm` (2 of 3 instantiations) | 0 | — |
| `cis2_k_silu_mul` | 12 | 3 |
| `cis2_k_softmax` | 32 | 7 |
| `cis2_k_rope` | 1 | 3 |
| `cis2_rmsnorm` (1 instantiation) | 18 | 8 |

**Every kernel that carries a pinned reduction — matvec, scores, weighted sum —
contains zero FFMA.** Every kernel that does contain FFMA also contains `MUFU`,
the signature of the `MUFU.RCP` / `MUFU.RSQ` seed followed by Newton–Raphson
refinement steps that `-prec-div=true -prec-sqrt=true` emit for `/` and `sqrt`.
Those refinements are correctly rounded by construction; the bit-identical digest
and byte-identical trace are the empirical evidence that they are.

## What this shows, and what it does not

It shows that a specification written for CPU fp32 — pinned reduction order, no FMA
contraction, no flush-to-zero, correctly rounded division and sqrt, pinned
transcendental polynomials, pinned RoPE tables — is **sufficient** for an independent
CUDA implementation to reproduce the CPU receipt bit-for-bit.

It does not show anything about performance (the run was correctness-only), about
Ampere/Hopper/Blackwell, about tensor-core paths (this port uses none), about batched
or multi-stream execution, or about any model other than SmolLM2-135M. One GPU
generation, one driver and compiler version, one model.

## Run provenance

- Kaggle kernel `aefinityaiinc/e18b-gpu`, private, GPU enabled, internet disabled,
  finished **2026-09-08 12:07:11 UTC**; docker image pinned by digest
  `sha256:37c64f7dd9c54116ecd1bcc88817c5469b88387388fade02bfa8bf3fc647d461`.
- Machine-readable verdicts: `hardware_logs/e18b-gpu-kaggle/2026-09-08-p100-v8-results.json`
  (`nofma_cuda_pass`, `sequential_pass`, `tree_candidate_pass` all true).
- SASS dumps: `…-v8-cis2_cuda.sass.txt`, `…-v8-cis2_cuda_tree.sass.txt`.
- Utilization samples: `…-v8-gpu_128tok_nvidia-smi.csv`, `…-v8-gpu_128tok_tree_nvidia-smi.csv`.
- Sources: dataset `aefinityaiinc/cis2-e18b-gpu` plus overlay `cis2-e18b-gpu-overlay`.

## Wording

No "first" and no "only" claims. Prior art on deterministic and reproducible GPU
inference exists (Gensyn `repops`, Microsoft RepDL, the vLLM and SGLang determinism
flags). The contribution here is narrower and stated as such: identity holds **from a
written specification**, across CPU compilers, two ISAs and a GPU, with a receipt a
third party can re-verify from the spec text alone.

---

## Historical: v5 (P100, 2026-09-06) — superseded

The v5 run reached the same four digests but SASS-gated a standalone probe rather than
the production binaries and captured no utilization sample, so device execution was
established from source structure alone. Its adversarial review (cm-verifier,
2026-09-06) returned CONFIRMED WITH CAVEATS and listed exactly those two gaps plus an
unre-derivable FFMA count; **v8 closes all three**. Log:
`hardware_logs/e18b-gpu-kaggle/2026-09-06-p100-v5.log`.
