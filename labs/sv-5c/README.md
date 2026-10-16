# sv-5c

- Question (ledger title): Does batching or thread count break token equality of a stock PyTorch rerun? (256 tokens, SmolLM2-135M)
- Why this is CIS-2 scope: stock rerun under batching/threads
- Verdict, as the ledger says: **NOT MET** (ledger result row, 2026-10-02T15:15:25Z)
- Registered: 2026-10-02T11:02:40Z, bar_sha256 `726cb42b02bb00fa4d6be7be8ad5f571d5afa4604f4c5f169291c70cb6991fa1`, git_head `30cf0821fa870efe96b6c48ee754b42bd0d09c8f`
- Started: 2026-10-02T11:05:54Z

## Ledger summary (verbatim from the result row)

NOT MET (answer no on both parts): box1 B8T1, B8T2 (batches of 8, left padding) and B1T2 (2 threads) each differ from the one-at-a-time reference on 0 of 200 prompts at 256 tokens; control holds; box2 B8T1 also 0 of 200. Logit margins do shift on most steps (max 9.2e-5) but only 2 of 51,200 reference margins are below 1e-4, so the run only bounds the rate (< ~59 per million per variant); sv-5d measures it. Verified by cm-verifier with its own comparison code.

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `reports/`: analysis reports, result files and key logs from the lab host.
- `results/`: result files named in the ledger result row.
