# LLM-5 gateway smoke log (2026-09-17T20:26:44Z)

```
== cis2-llm gateway smoke test ==
commit: d0275eb2edff4cd4fb7453f7aa0778a635a257c2
host: aefinity-box
date: 2026-09-17T20:26:41Z

-- starting gateway --
gateway up on :8899

-- test 1: legit round trip (expect ALLOW) --
submit response: {"status":"ALLOW","cap_token":"a5a16f60f00bd041d28d4b482de6eecc9fc21f754378fa0a944c513fbd15e5cb","receipt_id":"gwtest-legit-0001","tool":"toolA","action":"read","ticket":"3c55254737c746ad85e05bf7da71819e"}
final poll: {"status":"ALLOW","cap_token":"a5a16f60f00bd041d28d4b482de6eecc9fc21f754378fa0a944c513fbd15e5cb","receipt_id":"gwtest-legit-0001","tool":"toolA","action":"read","ticket":"3c55254737c746ad85e05bf7da71819e"}
PASS: test 1 legit round trip -> ALLOW

-- test 2: replay same receipt_id (expect DENY) --
submit response: {"status":"DENY","reason":"replay: receipt_id 'gwtest-legit-0001' already submitted (ticket 3c55254737c746ad85e05bf7da71819e)","ticket":"edc2bd7e64624b45924ebd7306468967"}
PASS: test 2 replay -> DENY

-- test 3: tampered receipt (flip one byte in witness_digest, expect DENY) --
submit response: {"status":"PENDING","ticket":"8bb7327eb91d41f5b66030b272f95ba3"}
final poll: {"status":"DENY","reason":"log_hash mismatch: stored=cec321cb3cb806bf41361f77eecf1a8f0b247be21b744ff250c04062e5c14cd4 recomputed=c032b8e3facf21c25b10ee2e1993e8ce17dc88183c05fc750000f24774adb8f4 (tampered record)","ticket":"8bb7327eb91d41f5b66030b272f95ba3"}
PASS: test 3 tamper -> DENY

-- test 4: missing receipt (expect DENY) --
submit response: {"status":"DENY","reason":"missing or malformed receipt (no receipt_id)","ticket":"006742d48d194568b2d77ea63d9f91f6"}
PASS: test 4 missing receipt -> DENY

-- test 5: unknown ticket poll (expect DENY, bonus fail-closed check) --
poll response: {"status":"DENY","reason":"unknown ticket","ticket":"does-not-exist"}
PASS: test 5 unknown ticket -> DENY

== RESULT: 5 passed, 0 failed (5 checks total) ==
```
