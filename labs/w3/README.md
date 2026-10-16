# w3

- Question (ledger title): w3: margin-gated verification from the sv-5d logs (flips versus top-1/top-2 margin on CPU fp32)
- Why this is CIS-2 scope: CIS-2 margin-gated verification from sv-5d logs
- Verdict, as the ledger says: **MET** (ledger result row, 2026-10-16T03:32:34Z)
- Registered: 2026-10-16T03:24:17Z, bar_sha256 `af8c226351e7cf827adb5192116db4e7183a019c4304acde4d4fb76ddeb7c082`, git_head `b6196de34eefcbd917eaf3ee2b8ec15d10fae79d`
- Started: 2026-10-16T03:31:00Z

## Ledger summary (verbatim from the result row)

W3 MET 2026-10-16T03:32Z: sanity gate PASS (all report rows reproduce, manifest sha256 ok 14/14); 7 counted flips (B=4, X=3) all at reference margin <= 1e-2; positions 1664964, recheck fraction at tau=1e-2 = 0.006857 (11416; bar < 1 % = 16649) CP95 upper 0.006963; harness state/labs/w3/run_w3.py sha256 9805fbb05e043fe7...; run ~2 s CPU on box7 under 1500M cap

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `reports/`: analysis reports, result files and key logs from the lab host.
- `results/`: result files named in the ledger result row.
- `scripts/`: lab scripts as committed in the lab repo.
- `w3-PREREG.md`: PREREG file as registered.

## Omitted from this folder (size or type); sha256 recorded so the originals can be matched

- internal publication-scoring record (out of scope): 1 files, 0.0 MB total. Examples:
  - `state/reports/w3/PUBLISH-SCORE.md` (3194 bytes, sha256 `c1a2ceb6546efe492d0a93260fc234fbcf39ce162864adce7c194bc31d91b23a`)
- Full omitted list for this folder is in `OMITTED.tsv`.
