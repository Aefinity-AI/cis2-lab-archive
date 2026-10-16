# sv-5

- Question (ledger title): Exact replay (CIS-2) vs TOPLOC vs stock rerun on SmolLM2-135M
- Why this is CIS-2 scope: CIS-2 exact replay vs statistical check vs stock rerun
- Verdict, as the ledger says: **NOT MET** (ledger result row, 2026-10-02T07:20:35Z)
- Registered: 2026-10-01T16:52:04Z, bar_sha256 `66efcd0ac9e904a1b4bd1a4fcac41b6efd968640bf534b078b00494bcc74f54c`, git_head `d4ceba5fc8cc7da649085dead63c5348bf7a4917`
- Amended: 2026-10-01T18:27:23Z, bar_sha256 `7fa269ad979fb33e756b423c61c7d9c02986542c74ff15a4ddbfe603e9ad8398`. Reason: Amendment 1, 2026-10-01 18:30Z, before any calibration or TEST data: step 0 smoke test showed box3 has no AVX2, so the same-class verifier is penguin; prompts sha256 4b4e7924...bf9bc; stack torch 2.10.0+cpu transformers 5.0.0 tokenizers 0.22.2 numpy 2.2.6 safetensors 0.7.0 toploc 0.1.6; protocol file sha256 fc61fe4fe723d4d2bead4ed71c69650b20d4e19e89e773d57cbfc6f062ede0e6
- Started: 2026-10-01T20:05:44Z

## Ledger summary (verbatim from the result row)

Q1 no (0 A-only rejects among output-changing runs in L2, Q1, P1 on box1->penguin), Q2 no (stock rerun token check 0/200 clean rejects on box1->box2), Q3 yes (W2 150/200, W3 132/198 A-only among runs that leave tokens unchanged); A clean rejects 0/200 on five verifier hosts; calibrated TOPLOC 2/200 clean false alarms on every pair

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `reports/`: analysis reports, result files and key logs from the lab host.
- `results/`: result files named in the ledger result row.
- `plans/`: plan / bar files.
