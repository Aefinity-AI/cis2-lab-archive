# w1x-coverage

- Question (ledger title): Constructed CIS-2 coverage vector: exact argmax tie (M15) and subnormal logit (M01) on a tiny Llama-arch model
- Why this is CIS-2 scope: CIS-2 constructed coverage vector (tie, subnormal)
- Verdict, as the ledger says: **MET** (ledger result row, 2026-10-16T14:18:11Z)
- Registered: 2026-10-16T10:45:40Z, bar_sha256 `777d11ce914ffdfa56d8e20381dfecd3ca593b8b2c6a0b2638fcbdb1a864fa2d`, git_head `991d013cae15111d968f844c39717a79060f54ba`
- Started: 2026-10-16T10:53:57Z

## Ledger summary (verbatim from the result row)

All 4 hosts (hq, w2 AVX2; w3, w4 SSE4.2 Celerons) RESULT: OK with identical ref8 4660d6c3…8734, m01=MOVED and m15=MOVED everywhere, ids0=5 (TIE_A), repeat=SAME, payload weights 677a5a25 config af88fb25 ids aa1bb87d. The two mutants SAME on every real-model vector in E22 (no FTZ/DAZ pin; argmax >=) are now caught by a constructed coverage vector.

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `reports/`: analysis reports, result files and key logs from the lab host.
- `results/`: result files named in the ledger result row.
- `plans/`: plan / bar files.

## Omitted from this folder (size or type); sha256 recorded so the originals can be matched

- internal publication-scoring record (out of scope): 1 files, 0.0 MB total. Examples:
  - `state/reports/w1x-coverage/PUBLISH-SCORE.md` (2427 bytes, sha256 `583595cda650bf760704722256cbae3122010ee0128dac03486d094734be06cb`)
- Full omitted list for this folder is in `OMITTED.tsv`.

## Notes

- Internal publication-scoring files (PUBLISH-SCORE.md) were left out.
