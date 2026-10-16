# w1x-horizon

- Question (ledger title): w1x-horizon: long-horizon CIS-2 digests (SmolLM2-135M fp32, C++ port, gen_toks 256/512/1024/2048) across hosts and the hq GPU
- Why this is CIS-2 scope: CIS-2 digest at long horizons
- Verdict, as the ledger says: **MET** (ledger result row, 2026-10-16T10:08:20Z)
- Registered: 2026-10-16T08:53:52Z, bar_sha256 `fa67e2d3638667c9d22278d4010f2fc1a9e473e90b70cb21f1702eb152af779a`, git_head `0438bbf5392444462a420006315769e74efe38b2`
- Started: 2026-10-16T08:59:11Z

## Ledger summary (verbatim from the result row)

Every gen_toks value (256, 512, 1024, 2048) produced one identical sequential-order CIS2_REF digest on 5 builds spanning 2 ISA classes + CUDA: hq g++ AVX2+FMA (host C), hq CUDA sm_61, w2 g++ AVX2+FMA Broadwell (host D), w3 g++ SSE4.2 N4020 (host A), w4 g++ SSE4.2 N4020C (host H); 16-token sanity row = pinned d8274305 on every run. Digests: 256=8824a226, 512=d8cdafd4, 1024=d46c3208, 2048=4924cacf. No divergence. Published as informative (not normative) digests; no timing (Rule A).

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `results/`: result files named in the ledger result row.
- `feed/`: job scripts and RESULT.txt files from the fleet job runner (per host).

## Omitted from this folder (size or type); sha256 recorded so the originals can be matched

- internal publication-scoring record (out of scope): 1 files, 0.0 MB total. Examples:
  - `state/reports/w1x-horizon/PUBLISH-SCORE.md` (3347 bytes, sha256 `60da2174c8967b2dbbb2a69756caa15c8094ad5dcc8636c5c70cf4b5032e8e35`)
- Full omitted list for this folder is in `OMITTED.tsv`.

## Notes

- Internal publication-scoring files (PUBLISH-SCORE.md) were left out.
