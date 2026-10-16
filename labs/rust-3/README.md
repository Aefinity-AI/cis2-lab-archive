# rust-3

- Question (ledger title): rust-3: loader robustness under malformed files, our Rust loader vs our C loader, same mutation operators and time per arm
- Why this is CIS-2 scope: CIS-2 implementation-language question (Rust vs C vs PyTorch for the CIS-2 runtime/training port)
- Verdict, as the ledger says: **MET** (ledger result row, 2026-10-16T04:24:19Z)
- Registered: 2026-10-04T00:34:55Z, bar_sha256 `091dfb37863577a42e6ff6fd25bd5736d16389ee608579624664b7b070687724`, git_head `234c44cc005aa06b75c583c908277691220527b7`
- Amended: 2026-10-12T17:41:34Z, bar_sha256 `4c3f9f51d172bf60d371d5fade2647300c8b7a4909b2b308aaff7384761cddd9`. Reason: Writes the sha256 of the K5 differential oracle (state/plans/rust-lab/oracle/k5_oracle.py, e81d09b65cbee3ca8917d5f0fc9c2db8536580be7dab1729ccddaccbc01f2739) into the bar, as the registered K5 paragraph says amend-bar will do before start. No other word of the bar changes. The oracle file was first written 2026-10-05 08:39 CDT, after registration (2026-10-04T00:34:55Z), contrary to the registered sentence 'committed before registration'; no loader had been run on any mutant.
- Started: 2026-10-12T20:40:33Z

## Ledger summary (verbatim from the result row)

BAR APPLIED (valid run): K1 RUST LOWER (R1 0 vs C1 10 keys, 3 sites: verify3 model.c/json.c); K3 TIE (0/0, counts too small); K4 TIE (counts too small; 0 vs 2, difference rule conflict noted); K5 RUST LOWER (1 vs 4); K2 informational as scored 0/0, corrected R1 3 / C1 0 (scorer misfiled Rust panics as harness crashes). R2 reported row K5 4, K1/K3/K4 lower bounds. R3/P1/L1 not run yet. Report state/reports/rust-3/RESULT.md

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `reports/`: analysis reports, result files and key logs from the lab host.
- `results/`: result files named in the ledger result row.
- `plans/`: plan / bar files.

## Omitted from this folder (size or type); sha256 recorded so the originals can be matched

- internal publication-scoring record (out of scope): 1 files, 0.0 MB total. Examples:
  - `state/reports/rust-3/PUBLISH-SCORE.md` (4138 bytes, sha256 `ba3e8595f6f3cfd30131f1d4c4359169ddaa64dbe2de1ec3b9bcc0a4beb5500c`)
- file over 1500000 bytes: 1 files, 2.6 MB total. Examples:
  - `state/reports/rust-3/raw/result-R2.json` (2599201 bytes, sha256 `e0c4c33222fbad4756587c8f1dab3de3d98792262f823d44156e037d573eb81f`)
- Full omitted list for this folder is in `OMITTED.tsv`.
