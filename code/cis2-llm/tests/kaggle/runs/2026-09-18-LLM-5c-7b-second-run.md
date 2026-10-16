> **ERRATA 2026-10-16 (ERRATA.md E-1):** `1501ed47...` is retired (mis-merged checkpoint); "second independent run MATCH" is void. EXPECTED = `a4a6770e...`.

# LLM-5c: second independent 7B CIS-2 run (Kaggle)

- Kernel: `aefinityaiinc/llm5b-scale-kaggle`, version 2 (pushed from `~/tmp/llm5c-pull`, code unchanged from the accepted LLM-5b/PR #12 script `llm5b-scale-kaggle.py`; dataset source `aefinityaiinc/cis2-fp-engine-llm5b`).
- Accelerator: CPU only (`enable_gpu: false`, `enable_tpu: false`) — same 31 GB Kaggle CPU kernel class as LLM-4/LLM-5b. Same platform, not cross-platform.
- Status polled to `KernelWorkerStatus.COMPLETE` (kernel push ~02:39Z, complete ~02:56Z, ~17 min wall time).
- Raw log pulled via `kaggle.api.kaggle_api_extended.KaggleApi().kernels_logs(...)` (the `kernels output` CLI download only returned the dataset source files, not `/kaggle/working` outputs, same limitation noted in LLM5B-LOG.md) → saved to `~/tmp/llm5c-out/llm5c-kernel-v2.log`.

## Raw digest strings (from the raw log, not a summary)

7B (`Qwen/Qwen2-7B`, prompt_toks=4, gen_toks=4, dtype=fp32, reduction_mode=sequential), both internal runs (run1/run2) identical:
```
1501ed4797a55081c38c7d12073a8acf522cc962d8c6d95aaf874fe0108f319a
```

1.5B (`Qwen/Qwen2-1.5B`, prompt_toks=4, gen_toks=8), both internal runs (run1/run2) identical:
```
9a463f443223b46c29f0d0ca3dfbcbc6bfb8e2b6c2dd1514967f460dba9d4bf8
```

## Comparison to expected (character-for-character, via shell string equality, not eyeballing)

| Model | Expected (LLM-4/LLM-5b) | This run (v2) | Result |
|---|---|---|---|
| Qwen2-7B | `1501ed4797a55081c38c7d12073a8acf522cc962d8c6d95aaf874fe0108f319a` | `1501ed4797a55081c38c7d12073a8acf522cc962d8c6d95aaf874fe0108f319a` | **MATCH** |
| Qwen2-1.5B | `9a463f443223b46c29f0d0ca3dfbcbc6bfb8e2b6c2dd1514967f460dba9d4bf8` | `9a463f443223b46c29f0d0ca3dfbcbc6bfb8e2b6c2dd1514967f460dba9d4bf8` | **MATCH** |

Table digest and inv_freq table digest also identical to prior runs
(`23c7bfaf...` / `02908dae...`), and argmax digests identical
(`67f771c5...` for 7B, `bbc7a844...` for 1.5B).

## OOM / memory

`memory.events` `oom_kill 0` at every checkpoint (3 occurrences in the
log, all `oom_kill 0`) — no OOM kill this run either, consistent with
LLM-5b. `time -v` peak RSS was again unavailable in this sandbox (falls
back to `RUSAGE_CHILDREN`, which the script itself flags as a running
max across children, not a clean per-process reading); no new peak-RSS
number is claimed beyond what LLM-5b already reported (~29.4 GB
estimate, same fallback method, same kernel class).

## Verdict

**7B SECOND-RUN MATCH (same platform, Kaggle; not yet cross-platform).**

Both the 7B and 1.5B CIS-2 §12.1 witness digests reproduce bit-for-bit
on a second, independent Kaggle kernel run (version 2, same code, same
31 GB CPU kernel class, no OOM). Per the hard rule, this does **not**
upgrade 7B to "validated" — it is a second same-platform confirmation.
A cross-platform (non-Kaggle) 7B run would be needed for a stronger
claim.
