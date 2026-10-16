# gateway/ -- async receipt-gated gateway (LLM-5)

Ported from `alice-aegis` safe-7 (async gateway: PENDING/POLL worker pool,
ALLOW on a verified receipt, fail-closed DENY on replay/tamper/missing
receipt, capability tokens bound to the issuing tool -- see alice-aegis
commits c4140fd, c4993e4, b97e8df, 0c66d90 and docs/design/RECEIPT-GATEWAY.md
in cis2-spec). Reimplemented here in Python stdlib + FastAPI (already a
server/ dependency) rather than copied from the Rust `agent_trace` binary
-- this repo has a Python server, so the port is behavior parity of the
state machine, not a code copy. Nothing from alice-aegis's private deploy
scripts or secrets is in this file tree.

## Files
- `gateway.py` -- the `Gateway` class: `submit()`/`poll()` async state
  machine (PENDING -> ALLOW | DENY), freshness/replay guard, capability
  tokens bound to `(receipt_id, tool, action)` (c4993e4 parity: a token
  minted for one tool cannot authorize a different tool).
- `verify_check.py` -- the default `verify_fn`: recomputes a receipt
  record's `log_hash` the same way `server/app/receipts.py` does when it
  writes one (canonical-encode + SHA-256 over the record body +
  `prev_hash`). This is a **record-tamper check**, not a re-run of the
  vendored `cis2-verify2` binary against model weights -- that heavier,
  independent-of-the-server digest check lives in
  `verifier/cis2_verify_cli.py` and needs the vendored binary + fetched
  weights built (not available on every box; see `docs/DEPLOY.md`).
  Pass a different `verify_fn=` into `Gateway()` to use that heavier check
  instead where the binary+weights are present -- the state machine
  (PENDING/POLL/replay guard/cap tokens) does not change.
- `app.py` -- FastAPI front (`POST /v1/gateway/submit`,
  `GET /v1/gateway/poll/{ticket}`), behind the `gateway` profile in
  `deploy/docker-compose.yml`.
- `interface.py` -- the small synchronous-looking `decide()` surface the
  rest of the repo was written against in v0.1; built on top of the real
  async `Gateway` via `submit_and_wait()` (polls with a timeout; never
  upgrades a timeout to ALLOW).

## Fail-closed guarantees (escape-test parity with alice-aegis safe-5b)
- Missing/malformed receipt (no `receipt_id`) -> DENY immediately.
- Replay: a second `submit()` of an already-seen `receipt_id` -> DENY
  ("replay"), even if the first submission is still PENDING (freshness key
  reserved before verify runs, not after it resolves).
- Tamper: a receipt whose stored `log_hash` doesn't match a fresh
  recompute of the record body -> DENY.
- Wrong-tool token: a capability token minted for `(receipt_id, tool=A,
  action)` fails `Gateway.verify_capability()` for `tool=B`.
- Unknown ticket polled -> DENY ("unknown ticket"), never PENDING/ALLOW.
- Any exception out of `verify_fn` -> DENY, never ALLOW-by-default.

See `tests/test_gateway.sh` for the exercised round trip (legit ALLOW,
replay DENY, tamper DENY, missing DENY) and `tests/GATEWAY-LOG.md` for the
raw run on box1.
