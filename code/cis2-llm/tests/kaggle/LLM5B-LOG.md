> **ERRATA 2026-10-16 (ERRATA.md E-1):** every `1501ed47...` digest below is the digest of a mis-merged checkpoint and is retired; EXPECTED 7B witness = `a4a6770e5f049a92335bc6fe92bac87f17627b89adc4f28636cd4ab511acbfb3`. History unedited.

# LLM-5b: Kaggle acceptance test for cis2-fp PR #12 (streaming widen)

Published 2026-10-16 as part of the CIS-2 archive. Kernel and dataset below are both **private** Kaggle assets under
the `aefinityaiinc` account; this document and the raw log
(`LLM5B-kernel.log`, same directory) are the only copies that leave
Kaggle.

## What this tests

cis2-fp PR #12 (branch `cm/llm5b-stream-widen`, commit `26c752c`) changes
`cis2_ref` to widen each safetensors tensor bf16 -> fp32 **per tensor,
streamed**, instead of holding the whole bf16 file resident alongside the
f32 model at once. LLM-4 (`tests/kaggle/LLM4-LOG.md`, engine commit
`3aa5f7a`, pre-fix) OOM-killed on `Qwen/Qwen2-7B` on a 31 GB Kaggle CPU
kernel (cgroup `oom_kill 1`), no digest produced. Expected after the fix:
peak RSS ~= f32 model (~28 GB) + largest single tensor + overhead — may
still not fit 31 GB, which would be a legitimate (if disappointing)
result.

This run reused the LLM-4 recipe verbatim (same kernel script structure,
same Qwen2 checkpoints, same prompt/gen-toks, same disk-safe sharded
merge for the 7B download), changing only:
1. the engine source ref (`cm/llm5b-stream-widen` @ `26c752c` instead of
   `3aa5f7a`), packaged as a new private Kaggle dataset
   `aefinityaiinc/cis2-fp-engine-llm5b` (src/, Cargo.toml, Cargo.lock,
   rust-toolchain.toml only — no weights, no target/, no .git), and
2. added memory instrumentation around each `cis2_ref` invocation:
   `free -g` before/after, and an attempt to wrap the child in
   `/usr/bin/time -v` for a direct peak-RSS reading (with a documented
   fallback to `resource.getrusage(RUSAGE_CHILDREN).ru_maxrss` if
   `/usr/bin/time` is not installed in the Kaggle image).

- Kaggle dataset (private, engine source only):
  `aefinityaiinc/cis2-fp-engine-llm5b`
  https://www.kaggle.com/datasets/aefinityaiinc/cis2-fp-engine-llm5b
- Kaggle kernel (private, CPU, script): `aefinityaiinc/llm5b-scale-kaggle`
  https://www.kaggle.com/code/aefinityaiinc/llm5b-scale-kaggle
  - v1: ran to completion (`KernelWorkerStatus.COMPLETE`), no OOM. See
    outcome below.

Environment (kernel v1, `free -h`/`nproc`/`uname -a`/`df -h`) — identical
Kaggle CPU kernel class to LLM-4:
```
Mem:            31Gi       425Mi        28Gi
4 CPUs
Linux ... 6.12.90+ ... x86_64
/dev/loop1       20G  144K   20G   1% /kaggle/working
```

## Instrumentation caveat (honest limitation)

`/usr/bin/time` was **not present** in this Kaggle CPU docker image
(`time -v=False` in the log for every `cis2_ref` invocation), so the
direct-child peak-RSS reading was unavailable and the script fell back to
`resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss`, which is a
**running maximum over all reaped children in the kernel process so far**,
not scoped to a single invocation. In this run, the 7B `cis2_ref`
invocation was by a wide margin the largest-memory child (build step,
merge step, and both 1.5B runs are all sub-3 GB), so the value reported
after the 7B run — and unchanged after both subsequent 1.5B runs — is a
reasonable proxy for the 7B peak specifically: **30,847,376 KB = 29.42
GB**. This is reported as the peak-RSS estimate for the 7B run, with this
caveat attached; it is not a `time -v`-grade per-process measurement.

`free -g` before/after each invocation was **not useful for peak
capture** (as scripted, both calls bracket the whole blocking
`subprocess.run`, so "after" reflects memory already reclaimed once the
child exits, not the in-flight peak) — recorded here so the next kernel
version fixes it (poll `free -g` on an interval from a separate
background loop, or rely solely on `time -v` / cgroup memory.peak).

## 7B outcome (from kernel log, verbatim key fields)

```
"7b": {
  "returncode": 0,
  "elapsed_s": 436.3503224849701,
  "digest": "1501ed4797a55081c38c7d12073a8acf522cc962d8c6d95aaf874fe0108f319a",
  "killed_by_signal": null
}
```
Additional witness detail printed by `cis2_ref` itself:
```
run1_argmax_digest=67f771c526de272cdf8bf22b6804edfca820cee2df9d6d9b68712e27cb43d284
run1_tokens=[12522, 5193, 264, 882, 1305, 1305, 3811, 3811]
runs_identical=true   (cis2_ref's own internal double-run check)
reduction_mode=sequential
```
cgroup `memory.events` after the run: `oom 0`, `oom_kill 0`,
`oom_group_kill 0`, `max 7161` (the `max` counter here is the number of
times an allocation attempt crossed the cgroup's soft `memory.max`
threshold, not a fatal event — `oom_kill 0` is the authoritative
no-OOM signal, consistent with `returncode=0`).

**The `Qwen/Qwen2-7B` run completed without being OOM-killed, on the same
31 GB Kaggle CPU kernel class that killed it under the pre-fix engine
(LLM-4).** Peak RSS estimate: **~29.4 GB** (see caveat above) — very
close to the 31 GB ceiling, so this is a real but narrow pass, not
headroom to spare.

LLM-4 never obtained a 7B digest (OOM-killed before any digest was
produced), so **there is no prior 7B digest to compare against**. The
digest above (`1501ed47...`) is recorded as a **provisional** first
successful 7B receipt from this engine, not verified against any
independent second run or a second implementation. It should not be
cited as a validated/reproduced 7B result until confirmed by a second
run (ideally on a different kernel invocation or independent engine
build).

## 1.5B outcome — mandatory bit-exactness check (both runs, this kernel)

```
"1_5b_run1": {"returncode": 0, "elapsed_s": 88.66,
  "digest": "9a463f443223b46c29f0d0ca3dfbcbc6bfb8e2b6c2dd1514967f460dba9d4bf8"}
"1_5b_run2": {"returncode": 0, "elapsed_s": 87.83,
  "digest": "9a463f443223b46c29f0d0ca3dfbcbc6bfb8e2b6c2dd1514967f460dba9d4bf8"}
"1_5b_match": true
"1_5b_matches_llm4_known_digest": true
```

**1.5B digest, old (LLM-4, engine `3aa5f7a`, pre-fix) vs new (LLM-5b,
engine `26c752c`, streaming widen):**

| | digest |
|---|---|
| LLM-4 (both runs) | `9a463f443223b46c29f0d0ca3dfbcbc6bfb8e2b6c2dd1514967f460dba9d4bf8` |
| LLM-5b (both runs) | `9a463f443223b46c29f0d0ca3dfbcbc6bfb8e2b6c2dd1514967f460dba9d4bf8` |

**Bit-for-bit equal.** The streaming per-tensor widen produces the
identical CIS-2 §12.1 witness digest as the old whole-buffer widen on
`Qwen/Qwen2-1.5B`, on the same Kaggle CPU kernel class, confirming PR #12
is a memory-layout change only, not a numerical behavior change, at this
scale.

## Timings summary

| Step | Elapsed |
|---|---|
| `cargo build --release` (`cis2_ref`) | 104.3s |
| HF metadata + per-shard download/merge (7B, 4 shards, 339 tensors, 15,231,233,024 bytes) | 119.0s (merge peak RSS during merge itself: 1630 MB) |
| `cis2_ref` 7B attempt (**completed, no kill**) | 436.4s |
| HF download (1.5B, single ~2.9 GB file) + `cis2_ref` run 1 | 88.7s |
| `cis2_ref` run 2 | 87.8s |
| Total kernel wall time | ~15 min |

## Verdict

**(a) Did the 7B run complete without OOM:** **Yes.** `returncode=0`,
`killed_by_signal=None`, cgroup `oom_kill 0`. This is a direct reversal of
the LLM-4 result (OOM-killed, `oom_kill 1`) on the identical 31 GB Kaggle
CPU kernel class, engine source ref changed only per PR #12.

**(b) Peak RSS:** **~29.4 GB estimate** (via `RUSAGE_CHILDREN` fallback,
not a per-process `time -v` reading — see caveat above), against a 31 GB
kernel. This is consistent with the PR's target shape (f32 model ~28 GB +
largest tensor + overhead) and is a narrow, not comfortable, fit.

**(c) Does the 7B digest match a prior expectation:** **No prior digest
to compare** — LLM-4 never produced one. This run's 7B digest
(`1501ed4797a55081c38c7d12073a8acf522cc962d8c6d95aaf874fe0108f319a`) is
recorded as **provisional**, not a validated/reproduced claim.

**Mandatory bit-exactness check (1.5B):** **PASS.** Both 1.5B runs on
this kernel match each other and match the known LLM-4 digest bit-for-bit
(`9a463f4432...`). The streaming widen introduces no numerical change at
1.5B scale.

**Overall:** PR #12's streaming widen fixes the 7B OOM seen in LLM-4 on
this specific 31 GB Kaggle CPU kernel, with a narrow (~29.4 GB of 31 GB)
memory margin, and does not change the 1.5B receipt. The 7B result is
reported as **PROVISIONAL PASS** (completed, no OOM, digest produced,
but not yet independently re-run or cross-checked) — do not cite the 7B
digest as validated until a second confirming run exists.

## Raw log

Full stdout/stderr, `llm5b_results.json` summary block, and cgroup
`memory.events` dumps are in `LLM5B-kernel.log` (same directory),
retrieved via the Kaggle API `kernels_logs` call (the CLI's
`kernels output` did not download `/kaggle/working/llm5b_results.json`
within budget due to the ~3 GB of 1.5B weights staged alongside it in the
kernel's working directory; the JSON summary is reproduced verbatim
above from the kernel's own stdout log).
