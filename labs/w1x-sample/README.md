# w1x-sample

- Question (ledger title): w1x-sample: CIS-2 seeded-sampling clause (draft section 14: MurmurHash3_x86_32 stateless Gumbel-max noise, pinned ln/exp, rank-order top-k/top-p, first-index argmax, receipt header CIS2-SAMPLE-1) on SmolLM2-135M, C++ port host + CUDA, cross-host + from-text agreement
- Why this is CIS-2 scope: CIS-2 seeded sampling clause
- Verdict, as the ledger says: **MET** (ledger result row, 2026-10-16T11:33:05Z)
- Registered: 2026-10-16T09:59:16Z, bar_sha256 `2029e2a083164b7d4d7a57a5b3e305674ae3c4b0d8741b87b61365eb2dffef91`, git_head `242340c00237b52ec9530e758929108a7ed4ea85`
- Started: 2026-10-16T10:04:41Z

## Ledger summary (verbatim from the result row)

Bar met on all three items. (a) greedy 16-token CIS2_REF d82743059d1db929 reproduced on hq host, hq CUDA sm_61, w2, w3, w4. (b) --sample 1,0.8,40,0.95: s16=98ed8bf7997816f3, s64=6a760d9e4d712551, ids16=f8e7a6b6a0a6f548 identical on hq host (AVX2+FMA), hq CUDA sm_61, w2 (AVX2 Broadwell), w3 and w4 (SSE4.2 N4020): one digest per length across 3 ISA classes + CUDA. (c) numpy from-text ref/sample_ref.py reproduces the 4 MurmurHash KAT rows, the toy vector (u,g,z bits, kept set, next_id=1) and the 16 sampled ids from the dumped logits (same lab, not clean-room). Builder clause resolutions (0-based step, top-p over top-k survivors, running f32 cumsum, strtof T/P, Murmur len 16) recorded in RESULTS-hq-builder.md and go into the spec draft text.

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `reports/`: analysis reports, result files and key logs from the lab host.
- `results/`: result files named in the ledger result row.
- `feed/`: job scripts and RESULT.txt files from the fleet job runner (per host).
- `plans/`: plan / bar files.

## Omitted from this folder (size or type); sha256 recorded so the originals can be matched

- internal publication-scoring record (out of scope): 1 files, 0.0 MB total. Examples:
  - `state/reports/w1x-sample/PUBLISH-SCORE.md` (3396 bytes, sha256 `edd67b67f2bc2edf46f657e871a1ddc2b8f7167ff3ae66718a499197d9fb8b93`)
- Full omitted list for this folder is in `OMITTED.tsv`.

## Notes

- Internal publication-scoring files (PUBLISH-SCORE.md) were left out.
