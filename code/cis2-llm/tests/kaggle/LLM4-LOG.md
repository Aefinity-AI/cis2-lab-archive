# LLM-4: Kaggle scale validation (Qwen2 1.5B / 7B attempt)

Published 2026-10-16 as part of the CIS-2 archive. Kernel and dataset below are both **private** Kaggle assets under
the `aefinityaiinc` account; this document and the raw log
(`LLM4-kernel.log`, same directory) are the only copies that leave Kaggle.

## What ran

- Engine: `cis2_ref` (generic, config-driven fp32 reference forward pass),
  from `~/projects/cis2-fp` at commit `3aa5f7a` (main, "E18c: quantify the
  reduction_mode authentication gap with a measurement").
- Kaggle dataset (private, engine source only — no `target/`, no weights,
  no `.git`): `aefinityaiinc/cis2-fp-engine-llm4`
  https://www.kaggle.com/datasets/aefinityaiinc/cis2-fp-engine-llm4
- Kaggle kernel (private, CPU, script): `aefinityaiinc/llm4-scale-kaggle`
  https://www.kaggle.com/code/aefinityaiinc/llm4-scale-kaggle
  - v1: failed with `OSError: [Errno 28] No space left on device` while
    merging `Qwen/Qwen2-7B`'s 4 safetensors shards into a single file —
    `snapshot_download` pulled all 4 shards (~14.2 GiB) into
    `/kaggle/working` (20 GB disk) before the merge step tried to write a
    second ~14.2 GiB merged file. This was a disk-space bug in the kernel
    script, not a finding about the engine.
  - Fix (kernel v2): download-and-merge one 7B shard at a time, deleting
    each shard immediately after its tensor bytes are copied into the
    merged file, then deleting the merged 7B file before Phase 2. Peak
    `/kaggle/working` usage dropped well under 20 GB; the merge itself
    completed in 115.6s (339 tensors, 15,231,233,024 bytes).
  - v2: ran to completion (`KernelWorkerStatus.COMPLETE`); see outcome
    below.

Environment (kernel v2, `free -h`/`nproc`/`uname -a`/`df -h`):
```
Mem:            31Gi       420Mi        28Gi
4 CPUs
Linux ... 6.12.90+ ... x86_64
/dev/loop1       20G  136K   20G   1% /kaggle/working
```

## Commands (as run inside the kernel script)

```
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain none --profile minimal
cargo build --release   # cis2_ref, rust-toolchain.toml pins channel 1.98.0
# Phase 1: Qwen/Qwen2-7B — per-shard hf_hub_download + streaming byte-level
# merge (see download_and_merge_sharded() in llm4_kaggle.py) into a single
# model.safetensors, then:
./target/release/cis2_ref --weights-dir /kaggle/working/weights_qwen2_7b --gen-toks 4
# Phase 2: Qwen/Qwen2-1.5B (single-file checkpoint, no merge needed), run twice:
./target/release/cis2_ref --weights-dir /kaggle/working/weights_qwen2_1_5b --gen-toks 8
./target/release/cis2_ref --weights-dir /kaggle/working/weights_qwen2_1_5b --gen-toks 8
```
Default prompt in both cases: `"Once upon a time"` (cis2_ref's built-in
default; no `--prompt-set` was passed).

## 7B outcome (verbatim, from `llm4_results.json` + kernel log)

```
"7b": {
  "returncode": -9,
  "elapsed_s": 284.5444676876068,
  "digest": null,
  "killed_by_signal": 9,
  "stdout_tail": "",
  "stderr_tail": "loading + widening weights (bf16 -> fp32, exact bit-shift, §3.5)..."
}
```

Kernel log around the kill (timestamps are seconds since kernel start):
```
225.20 [stdout] ==============================================================================
225.20 [stdout] 7B: running cis2_ref
225.20 [stdout] ==============================================================================
509.74 [stderr] loading + widening weights (bf16 -> fp32, exact bit-shift, §3.5)...
509.74 [stdout] ---- 7B: exit=-9 elapsed=284.5s
509.74 [stdout] ---- 7B: PROCESS KILLED BY SIGNAL 9 (likely OOM if 9==9)
509.87 [stdout] ---- 7B: cat /sys/fs/cgroup/memory.events (rc=0):
low 0
high 0
max 3104
oom 14
oom_kill 1
oom_group_kill 0
```
`dmesg` was not readable inside the container (rc=1, no output) but the
cgroup `memory.events` counter (`oom_kill 1`) directly confirms the Linux
OOM killer terminated the process during cis2_ref's own bf16→f32 weight
widening step, consistent with the pre-run estimate that `Qwen/Qwen2-7B`
in this engine (~45 GB peak: full safetensors load + f32 copies) would
not fit in the kernel's 31 GB Kaggle CPU RAM. No digest was produced. This
is honest negative evidence at 7B scale on this hardware/engine
combination, not a bug to paper over.

## 1.5B outcome (both runs)

```
"1_5b_run1": {"returncode": 0, "elapsed_s": 95.39890909194946,
  "digest": "9a463f443223b46c29f0d0ca3dfbcbc6bfb8e2b6c2dd1514967f460dba9d4bf8"}
"1_5b_run2": {"returncode": 0, "elapsed_s": 93.42900037765503,
  "digest": "9a463f443223b46c29f0d0ca3dfbcbc6bfb8e2b6c2dd1514967f460dba9d4bf8"}
"1_5b_match": true
```

Both `Qwen/Qwen2-1.5B` runs exited 0 and produced the **identical**
CIS-2 §12.1 witness digest
(`9a463f443223b46c29f0d0ca3dfbcbc6bfb8e2b6c2dd1514967f460dba9d4bf8`),
back-to-back on the same Kaggle CPU kernel, ~94s each.

## Timings summary

| Step | Elapsed |
|---|---|
| rustup install + `cargo build --release` | ~98s (to start of Phase 1 header, log line `98.48 [stdout] PHASE 1: Qwen/Qwen2-7B attempt`) |
| HF metadata + per-shard download/merge (7B, 4 shards, 15.2 GiB) | ~127s (98.48s to 225.20s "7B: running cis2_ref"; merge step itself measured 115.6s internally) |
| cis2_ref 7B attempt (killed) | 284.5s |
| HF download (1.5B, single ~3 GB file) + cis2_ref run 1 | 95.4s |
| cis2_ref run 2 | 93.4s |
| Total kernel wall time | ~716s (~12 min) |

## Verdict

This run validates fp32-exact, bit-reproducible CIS-2 receipts for
`Qwen/Qwen2-1.5B` on Kaggle CPU (2 independent runs, identical §12.1
witness digest), which is the largest architecture/scale this generic
`cis2_ref` engine has been shown to reproduce end-to-end off this fleet.
It does **not** demonstrate a working 7B-class receipt: the `Qwen/Qwen2-7B`
attempt was killed by the OOM killer during weight widening on a 31 GB
Kaggle CPU kernel, so no digest exists at 7B and none should be claimed.
"LLM-scale" (7B–8B) fp32-exact reproduction remains unvalidated pending
either a larger-RAM Kaggle kernel (GPU kernels currently offer more RAM
than this CPU one) or an engine change that avoids holding the full model
in f32 twice during load.
