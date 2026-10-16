# LLM-1 smoke log (2026-09-17T20:46:50Z)

```
== cis2-llm smoke test ==
-- starting server --
server up on :8799
-- issuing one receipt --
{"id":"chatcmpl-fcdb19c4362a473a92faad2f24468c3c","object":"chat.completion","model":"cis2-smollm2-135m-fp32-ref","choices":[{"index":0,"message":{"role":"assistant","content":", there was a little girl named Lily. She lived in a big house with"},"finish_reason":"length"}],"cis2":{"receipt_id":"fcdb19c4362a473a92faad2f24468c3c","witness_digest":"d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df","log_hash":"e3bd2034e9536afd4ce68ee52e7a4d00faafa5e8fdc4e900e189ce66681634d2","note":"v0.1 scaffold: this receipt covers the pinned CIS-2 v0.3b reference vector, not free-form generation from the request messages. See docs/CLAIMS.md."}}
receipt_id=fcdb19c4362a473a92faad2f24468c3c
-- GET /v1/receipts/{id} --
{"argmax_digest":"0b9c8f3ac90d0b9cd5f1719ac327dca1fc639fd87468305fccebbe3d56f67aff","cis2_version":"v0.3b","created":"2026-09-17T20:46:34Z","generated_token_ids":[28,665,436,253,1838,8180,3365,14176,30,2306,4161,281,253,2066,2291,351],"inv_freq_table_digest":"da9f6dcfde0425588815509e874515cdcd3d6b8818b6d0136590052e7bbf6f12","log_hash":"e3bd2034e9536afd4ce68ee52e7a4d00faafa5e8fdc4e900e189ce66681634d2","model":"cis2-smollm2-135m-fp32-ref","prev_hash":"0000000000000000000000000000000000000000000000000000000000000000","prompt":"Once upon a time","receipt_id":"fcdb19c4362a473a92faad2f24468c3c","table_digest":"23c7bfaf5cef0095fd021af2eb1808abb4928bae4219756d86bdac670a06b35d","witness_digest":"d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df"}
-- verify (expect PASS) --
PASS receipt_id=fcdb19c4362a473a92faad2f24468c3c witness_digest=d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df
-- tamper one byte in the receipt log, verify (expect FAIL) --
byte-diff:
1c1
< {"argmax_digest": "0b9c8f3ac90d0b9cd5f1719ac327dca1fc639fd87468305fccebbe3d56f67aff", "cis2_version": "v0.3b", "created": "2026-09-17T20:46:34Z", "generated_token_ids": [28, 665, 436, 253, 1838, 8180, 3365, 14176, 30, 2306, 4161, 281, 253, 2066, 2291, 351], "inv_freq_table_digest": "da9f6dcfde0425588815509e874515cdcd3d6b8818b6d0136590052e7bbf6f12", "log_hash": "e3bd2034e9536afd4ce68ee52e7a4d00faafa5e8fdc4e900e189ce66681634d2", "model": "cis2-smollm2-135m-fp32-ref", "prev_hash": "0000000000000000000000000000000000000000000000000000000000000000", "prompt": "Once upon a time", "receipt_id": "fcdb19c4362a473a92faad2f24468c3c", "table_digest": "23c7bfaf5cef0095fd021af2eb1808abb4928bae4219756d86bdac670a06b35d", "witness_digest": "d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df"}
---
> {"argmax_digest": "0b9c8f3ac90d0b9cd5f1719ac327dca1fc639fd87468305fccebbe3d56f67aff", "cis2_version": "v0.3b", "created": "2026-09-17T20:46:34Z", "generated_token_ids": [28, 665, 436, 253, 1838, 8180, 3365, 14176, 30, 2306, 4161, 281, 253, 2066, 2291, 351], "inv_freq_table_digest": "da9f6dcfde0425588815509e874515cdcd3d6b8818b6d0136590052e7bbf6f12", "log_hash": "e3bd2034e9536afd4ce68ee52e7a4d00faafa5e8fdc4e900e189ce66681634d2", "model": "cis2-smollm2-135m-fp32-ref", "prev_hash": "0000000000000000000000000000000000000000000000000000000000000000", "prompt": "Once upon a time", "receipt_id": "fcdb19c4362a473a92faad2f24468c3c", "table_digest": "23c7bfaf5cef0095fd021af2eb1808abb4928bae4219756d86bdac670a06b35d", "witness_digest": "d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9de"}
FAIL receipt_id=fcdb19c4362a473a92faad2f24468c3c
  witness_digest: stored='d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9de' recomputed='d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df'

PASS: round-trip receipt verified, tampered receipt correctly rejected.
```
