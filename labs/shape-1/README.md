# shape-1

- Question (ledger title): CIS-2 C driver on a new Llama shape (llama-160m, MHA, untied head): digests on four CPU classes and agreement with stock torch
- Why this is CIS-2 scope: CIS-2 C driver on a new Llama shape (llama-160m)
- Verdict, as the ledger says: **MET** (ledger result row, 2026-10-03T17:56:30Z)
- Registered: 2026-10-03T14:15:59Z, bar_sha256 `8ddab49541263f889b8a6efd4db1ce8a061aa869fc8910af4e9c38e75d7832c7`, git_head `c9e4298626385307831e423cc85bb996337d2df7`
- Started: 2026-10-03T17:25:23Z

## Ledger summary (verbatim from the result row)

(a) MET and (b) MET: identical ids_out/witness/argmax on 100/100 prompts across penguin, box3, box4, box5; C driver equals stock torch fp32 greedy on 100/100 (re-derived from raw rows). start record entered LATE (box3/4/5 ran before it; bar unchanged since 14:15:59Z). Scope: one shape, 100 prompts, 32 tokens. Report state/reports/2026-10-03-SHAPE1-RESULT.md

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `reports/`: analysis reports, result files and key logs from the lab host.
- `results/`: result files named in the ledger result row.
- `plans/`: plan / bar files.
