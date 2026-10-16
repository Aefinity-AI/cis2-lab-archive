# w1x-batch

- Question (ledger title): w1x-batch: batch-size invariance of the CIS-2 witness (C++/CUDA port --batch N) on CPU and the hq GPU
- Why this is CIS-2 scope: CIS-2 witness batch-size invariance
- Verdict, as the ledger says: **MET** (ledger result row, 2026-10-16T10:12:11Z)
- Registered: 2026-10-16T08:53:53Z, bar_sha256 `7a3426cae92c51ca36668d2e916d7cad405af60599ed6b0c59ff44a4380ceeba`, git_head `0438bbf5392444462a420006315769e74efe38b2`
- Started: 2026-10-16T09:05:56Z

## Ledger summary (verbatim from the result row)

hq (host C): per-row witness digest identical at batch sizes 1, 2, 4 and 8 on the host build and on the CUDA sm_61 build; batch-1 row = pinned d8274305; 4-prompt set: each row equals its solo digest on both builds (pset 4/4 host, 4/4 CUDA). Scope: replica-interleaved batching in the C++ port (the forward runs rows interleaved, not a fused batched GEMM); w2 (host D, host build only) row still queued as supplementary evidence; the fused-GEMM variant is a separate registration (w1x-batch-fused).

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `results/`: result files named in the ledger result row.
- `feed/`: job scripts and RESULT.txt files from the fleet job runner (per host).

## Omitted from this folder (size or type); sha256 recorded so the originals can be matched

- internal publication-scoring record (out of scope): 1 files, 0.0 MB total. Examples:
  - `state/reports/w1x-batch/PUBLISH-SCORE.md` (2397 bytes, sha256 `c381c2cfba355eac6587ff86eea6f469dfaa8553da9fe653165e895fdf8125de`)
- Full omitted list for this folder is in `OMITTED.tsv`.

## Notes

- Internal publication-scoring files (PUBLISH-SCORE.md) were left out.
