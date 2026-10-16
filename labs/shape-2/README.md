# shape-2

- Question (ledger title): CIS-2 C driver on llama-160m at 128 greedy tokens (300 prompts): agreement with stock torch fp32 on box4/box5, digests across three CPU classes
- Why this is CIS-2 scope: CIS-2 C driver on llama-160m at 128 tokens vs stock torch
- Verdict, as the ledger says: **MET** (ledger result row, 2026-10-04T02:40:01Z)
- Registered: 2026-10-03T19:14:53Z, bar_sha256 `37de64508dfdcc241467d52c11b6922ee2ba58854b4ad1561e0999ba3909b041`, git_head `2a31d0321584f0949cf7fcea254cf78e2310daee`
- Started: 2026-10-03T19:19:22Z

## Ledger summary (verbatim from the result row)

MET on the headline (b): the C driver (sv5_driver, gcc -O2 build fb7ec824...) on BF16 llama-160m weights gives the same whole 128-token greedy output as stock PyTorch 2.10.0+cpu fp32 on 300 of 300 prompts on box4 (Sempron, SSE3) and 300 of 300 on box5 (Pentium T2310, SSSE3); pass needs 294 on each. Independent verifier recounted from the raw rows with its own script (whole-list equality of exactly 128 ids), confirmed 300 distinct prompts per box, no early stop (no EOS in any of 600 outputs), prompts/reference/weights hashes equal to the pass mark, reference built by PyTorch without the driver and before the box jobs. Secondary (a): ids, witness and argmax fields identical between box4 and box5 on 300 of 300 rows; the penguin (AVX2) unit was NOT run, so (a) covers the two boxes only. Caveats: one model shape (llama-160m), one number format, benign prompts of at most 64 tokens, greedy, one run per prompt; about 5% of outputs are repetitive (1 of 300 is a single repeated token, 16 have a short periodic tail), which makes those matches easy; this shows equal token strings, not bit-identical logits against PyTorch; no throughput claim; the driver hash is pinned by earlier sv-5 records, not in this pass mark; the reference logs are empty, so the PyTorch version rests on the venv and the pass-mark text.

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `reports/`: analysis reports, result files and key logs from the lab host.
- `results/`: result files named in the ledger result row.
