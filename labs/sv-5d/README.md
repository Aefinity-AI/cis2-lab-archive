# sv-5d

- Question (ledger title): Per-token divergence rate of a stock PyTorch rerun across CPU classes and under batching (1.6M positions, SmolLM2-135M)
- Why this is CIS-2 scope: per-token divergence of stock rerun across CPU classes
- Verdict, as the ledger says: **MET** (ledger result row, 2026-10-03T08:16:53Z)
- Registered: 2026-10-02T11:50:07Z, bar_sha256 `402041299173e4fe70c791802c293f43c999e12bda52bed7064d3892e87b4fb7`, git_head `12dcec701c556587629b199c3e7f5c02c9ba176c`
- Started: 2026-10-02T11:56:06Z

## Ledger summary (verbatim from the result row)

sv-5d MET on both parts (registered count rule). (x) X (box2 w0-3999 + box3 w4000-7999) vs box1 R: 3 flips (2 box2, 1 box3; strict on both sides) of 1,664,964 = 1.8018/M (95% upper 4.6569); met at the minimum count of 3. (b) box1 B8T1: 4 flips = 2.4025/M (upper 5.4977); 3 without the exact-tie flip w1302/p143. T 1/416,030; penguin S 0/416,030 (0/1,664,964 all windows). All flips swap the top two tokens at R margin <= 5.722e-06. One-sided 95% lower bounds 0.49 and 0.82/M are under 1/M. Teacher-forced, SmolLM2-135M fp32, CPU.

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `reports/`: analysis reports, result files and key logs from the lab host.
- `results/`: result files named in the ledger result row.
