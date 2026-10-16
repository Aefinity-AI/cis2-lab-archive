# LLM-1 chain test log (2026-09-17T20:48:33Z)

```
== cis2-llm chain test ==
-- starting server --
server up on :8798
-- issuing 3 receipts --
receipt 1 id=62a45055005a413595a2508d91448bec
receipt 2 id=d0ac0cf924ad4c5ab3e6bbb69443ba6a
receipt 3 id=e56f2192b6844e289b62423c74f99341
-- GET /v1/chain_status (expect chain_ok=true) --
{"chain_ok":true,"message":"chain OK"}
-- chain (expect PASS, untampered log) --
PASS chain <home>/cis2-llm-fix/server/data/receipts.jsonl: chain OK
-- verify last receipt on untampered log (expect PASS) --
PASS receipt_id=e56f2192b6844e289b62423c74f99341 witness_digest=d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df
-- overwrite line 1 with a stale record, chain (expect FAIL) --
line 1 after tamper:
{"argmax_digest": "0b9c8f3ac90d0b9cd5f1719ac327dca1fc639fd87468305fccebbe3d56f67aff", "cis2_version": "v0.3b", "created": "2026-09-17T20:48:00Z", "generated_token_ids": [28, 665, 436, 253, 1838, 8180, 3365, 14176, 30, 2306, 4161, 281, 253, 2066, 2291, 351], "inv_freq_table_digest": "da9f6dcfde0425588815509e874515cdcd3d6b8818b6d0136590052e7bbf6f12", "log_hash": "9ae5ddc99470ac665f8a751426bba8de0bb7e2a49fbdbc58c0a3d22361ff42a1", "model": "cis2-smollm2-135m-fp32-ref", "prev_hash": "0000000000000000000000000000000000000000000000000000000000000000", "prompt": "Once upon a time", "receipt_id": "62a45055005a413595a2508d91448bec", "table_digest": "23c7bfaf5cef0095fd021af2eb1808abb4928bae4219756d86bdac670a06b35d", "witness_digest": "d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df"}
FAIL chain <home>/cis2-llm-fix/server/data/receipts.jsonl: line 0: log_hash mismatch (tampered record)
-- verify last receipt on tampered log (expect FAIL, chain broken before it) --
FAIL receipt_id=e56f2192b6844e289b62423c74f99341
  chain: line 0: log_hash mismatch (tampered record)

PASS: chain check passes on an untampered log and fails (with line number) after tampering an earlier line; verify of a later receipt correctly fails too.
```
