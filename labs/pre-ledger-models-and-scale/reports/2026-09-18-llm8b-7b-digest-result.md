# llm8b-7b merge verify + digest tail — 2026-09-18

Repo: Aefinity-AI/cis2-fp, worktree `~/projects/cis2-fp-cm-llm8b-stream`, branch `cm/llm8b-stream` (commit `19819e6`, pushed).

## 1. Independent recompute of merged weights file

```
$ stat -c %s weights_qwen2_7b/model.safetensors
15231272088
$ sha256sum weights_qwen2_7b/model.safetensors
13200c88e7482d83ed9a2bb23a01b515e46663ab57dba853389587d4173dcfa3  weights_qwen2_7b/model.safetensors
```

Both match the claimed values exactly (size 15231272088, sha256
`13200c88e7482d83ed9a2bb23a01b515e46663ab57dba853389587d4173dcfa3`).

## 2. Root cause of the 39064-byte gap

`EXP_MERGED_SIZE=15231233024` (old, wrong) vs actual merged size
15231272088. Delta = 39064 bytes.

Computed per-shard header sizes (8-byte length prefix + JSON header) directly
from the 4 shard files:

| shard | file size | header bytes |
|---|---|---|
| 00001 | 3945426872 | 9144 |
| 00002 | 3864726352 | 11088 |
| 00003 | 3864726408 | 11144 |
| 00004 | 3556392240 | 7472 |
| **total** | 15231271872 | **38848** |

Sum of per-shard *data* bytes (file size minus header) = 15231233024 —
exactly the old `EXP_MERGED_SIZE`. So whoever computed that constant summed
only tensor payload bytes and forgot the merged file also carries its own
header. The merged file's actual header (`merge_shards.py` builds one
combined JSON header covering all 339 tensors) is 39064 bytes — naturally
different from the sum of four separate per-shard headers (38848 bytes),
since header size depends on JSON key/offset text, not just tensor count.

`merged data bytes (15231272088 - 39064 = 15231233024)` equals the shard
data-byte sum exactly, confirming `merge_shards.py` copied tensor bytes
verbatim with no loss/duplication/corruption.

**Verdict: miscomputed constant, not a merge defect.** Fixed
`EXP_MERGED_SIZE` to `15231272088` in `scripts/run_llm8b_7b.sh` (line 19),
committed and pushed to `cm/llm8b-stream`.

## 3. Digest tail run result

Re-ran `scripts/run_llm8b_7b.sh` (it naturally skipped the download — shard
`.sha256.ok` sentinels present — and skipped the merge — size now matches
the fixed `EXP_MERGED_SIZE` — then proceeded to the `cis2_ref` invocation).

Result: **crash, not a digest.** `cis2_ref` panicked:

```
thread 'main' (581504) panicked at src/main.rs:641:55:
read "<home>/projects/cis2-fp-cm-llm8b-stream/weights_qwen2_7b/model.safetensors": out of memory
   2: cis2_ref::sha256_file::{closure#0}
   3: cis2_ref::sha256_file
   4: cis2_ref::main
```

Cause: `sha256_file()` (src/main.rs:640-645) does `std::fs::read(path)` —
reads the entire file into one `Vec<u8>` in RAM before hashing — on a
14.5 GiB merged weights file, on a box with 5.8 GiB total RAM (`free -m`:
~4.96 GiB available at run start). This is unrelated to `--stream-weights`
tensor loading (which the code comments describe as already fixed to
stream per-tensor); the digest/provenance hashing path was never made
streaming.

**Verdict: neither MATCH nor MISMATCH.** No digest was ever computed against
the target `1501ed4797a55081c38c7d12073a8acf522cc962d8c6d95aaf874fe0108f319a`
— the run crashed before comparison.

Full log: `docs/hardware_logs/llm8b_7b_aefinity-box_2026-09-18.log` (in the
worktree, committed on `cm/llm8b-stream`).

## Next steps (for BLOCKERS.md / QUEUE.md — not written by me)

- `cis2_ref::sha256_file` needs to stream-hash (chunked reads, not
  `std::fs::read`) before this leg can produce a digest at all on this box's
  RAM budget. This is a real code fix to `src/main.rs`, separate from the
  merge/size-constant bug fixed here.
- Once fixed, re-run the same digest tail (shards + merged file are already
  verified and on disk — no need to re-download or re-merge) and compare to
  target digest `1501ed4797a55081c38c7d12073a8acf522cc962d8c6d95aaf874fe0108f319a`.
