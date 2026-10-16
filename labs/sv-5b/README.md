# sv-5b

- Question (ledger title): sv-5 follow-up: does a stock PyTorch rerun still give the same tokens on another CPU class at 256 tokens?
- Why this is CIS-2 scope: follow-up to sv-5: stock rerun on another CPU class
- Verdict, as the ledger says: **NOT MET** (ledger result row, 2026-10-02T15:15:25Z)
- Registered: 2026-10-02T08:06:24Z, bar_sha256 `50a987047950706ff06c7a32f2753f6d8052155cd9515c31089469613bf8116e`, git_head `281920532d556a190b92659afee0fae59c647d68`
- Started: 2026-10-02T08:08:48Z

## Ledger summary (verbatim from the result row)

NOT MET: at 256 greedy tokens the stock PyTorch rerun on box2 and box3 (Celeron, no AVX) gives box1's tokens on 200/200 prompts each (penguin too; penguin margins bit-identical to box1). Part (ii) incomplete but cannot change the verdict: exact-replay rows equal penguin vs box5 200/200, box4 run outstanding. Verified by cm-verifier with its own comparison code.

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `reports/`: analysis reports, result files and key logs from the lab host.
- `results/`: result files named in the ledger result row.
