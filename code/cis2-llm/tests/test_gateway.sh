#!/usr/bin/env bash
# LLM-5 gateway smoke test: legit round trip ALLOW, replay DENY, tamper
# DENY, missing DENY. No Docker, no vendored verifier binary, no model
# weights -- see gateway/README.md for why the default verify_fn is a
# record-tamper check. Writes tests/GATEWAY-LOG.md with the real output.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_MD="$ROOT/tests/GATEWAY-LOG.md"
PORT="${CIS2_LLM_GATEWAY_SMOKE_PORT:-8899}"
export PATH="$HOME/.local/bin:$PATH"

PASS=0
FAIL=0
OUT="$(mktemp)"

log() { echo "$@" | tee -a "$OUT"; }

log "== cis2-llm gateway smoke test =="
log "commit: $(cd "$ROOT" && git rev-parse HEAD 2>/dev/null || echo unknown)"
log "host: $(hostname)"
log "date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

log ""
log "-- starting gateway --"
(cd "$ROOT" && exec uv run --project server uvicorn gateway.app:app \
  --app-dir "$ROOT" --host 127.0.0.1 --port "$PORT" \
  >/tmp/cis2-llm-gateway-smoke-server.log 2>&1) &
SERVER_PID=$!
stop_server() { pkill -TERM -P "$SERVER_PID" 2>/dev/null || true; kill "$SERVER_PID" 2>/dev/null || true; }
trap 'stop_server' EXIT

if ! curl -sf --retry 30 --retry-delay 1 --retry-connrefused \
    "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then
  log "FAIL: gateway did not come up"
  cat /tmp/cis2-llm-gateway-smoke-server.log | tee -a "$OUT"
  FAIL=$((FAIL+1))
else
  log "gateway up on :$PORT"
fi

# Build a legit receipt record with a real log_hash, using the same
# canonical-encode+SHA-256 rule as server/app/receipts.py.
RECEIPT_JSON="$(python3 - <<'PYEOF'
import hashlib, json
GENESIS = "0" * 64
record = {
    "receipt_id": "gwtest-legit-0001",
    "created": "2026-09-17T00:00:00Z",
    "model": "cis2-smollm2-135m-fp32-ref",
    "cis2_version": "v0.3b",
    "witness_digest": "deadbeef" * 4,
    "prev_hash": GENESIS,
}
canon = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
record["log_hash"] = hashlib.sha256(canon).hexdigest()
print(json.dumps(record))
PYEOF
)"

log ""
log "-- test 1: legit round trip (expect ALLOW) --"
RESP1="$(curl -s -X POST "http://127.0.0.1:$PORT/v1/gateway/submit" \
  -H 'Content-Type: application/json' \
  -d "{\"receipt\": $RECEIPT_JSON, \"tool\": \"toolA\", \"action\": \"read\"}")"
log "submit response: $RESP1"
TICKET1="$(echo "$RESP1" | python3 -c 'import json,sys; print(json.load(sys.stdin)["ticket"])')"
STATUS1=""
for _ in $(seq 1 50); do
  POLL1="$(curl -s "http://127.0.0.1:$PORT/v1/gateway/poll/$TICKET1")"
  STATUS1="$(echo "$POLL1" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
  [ "$STATUS1" != "PENDING" ] && break
  sleep 0.05
done
log "final poll: $POLL1"
if [ "$STATUS1" = "ALLOW" ]; then
  log "PASS: test 1 legit round trip -> ALLOW"
  PASS=$((PASS+1))
else
  log "FAIL: test 1 expected ALLOW, got $STATUS1"
  FAIL=$((FAIL+1))
fi

log ""
log "-- test 2: replay same receipt_id (expect DENY) --"
RESP2="$(curl -s -X POST "http://127.0.0.1:$PORT/v1/gateway/submit" \
  -H 'Content-Type: application/json' \
  -d "{\"receipt\": $RECEIPT_JSON, \"tool\": \"toolA\", \"action\": \"read\"}")"
log "submit response: $RESP2"
STATUS2="$(echo "$RESP2" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
if [ "$STATUS2" = "DENY" ]; then
  log "PASS: test 2 replay -> DENY"
  PASS=$((PASS+1))
else
  log "FAIL: test 2 expected DENY, got $STATUS2"
  FAIL=$((FAIL+1))
fi

log ""
log "-- test 3: tampered receipt (flip one byte in witness_digest, expect DENY) --"
TAMPERED_JSON="$(python3 -c "
import json
r = json.loads('''$RECEIPT_JSON''')
r['receipt_id'] = 'gwtest-tamper-0002'
r['witness_digest'] = 'deadbeee' * 4  # last char flipped, log_hash now stale
print(json.dumps(r))
")"
RESP3="$(curl -s -X POST "http://127.0.0.1:$PORT/v1/gateway/submit" \
  -H 'Content-Type: application/json' \
  -d "{\"receipt\": $TAMPERED_JSON, \"tool\": \"toolA\", \"action\": \"read\"}")"
log "submit response: $RESP3"
TICKET3="$(echo "$RESP3" | python3 -c 'import json,sys; print(json.load(sys.stdin)["ticket"])')"
STATUS3=""
for _ in $(seq 1 50); do
  POLL3="$(curl -s "http://127.0.0.1:$PORT/v1/gateway/poll/$TICKET3")"
  STATUS3="$(echo "$POLL3" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
  [ "$STATUS3" != "PENDING" ] && break
  sleep 0.05
done
log "final poll: $POLL3"
if [ "$STATUS3" = "DENY" ]; then
  log "PASS: test 3 tamper -> DENY"
  PASS=$((PASS+1))
else
  log "FAIL: test 3 expected DENY, got $STATUS3"
  FAIL=$((FAIL+1))
fi

log ""
log "-- test 4: missing receipt (expect DENY) --"
RESP4="$(curl -s -X POST "http://127.0.0.1:$PORT/v1/gateway/submit" \
  -H 'Content-Type: application/json' \
  -d '{"receipt": null, "tool": "toolA", "action": "read"}')"
log "submit response: $RESP4"
STATUS4="$(echo "$RESP4" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
if [ "$STATUS4" = "DENY" ]; then
  log "PASS: test 4 missing receipt -> DENY"
  PASS=$((PASS+1))
else
  log "FAIL: test 4 expected DENY, got $STATUS4"
  FAIL=$((FAIL+1))
fi

log ""
log "-- test 5: unknown ticket poll (expect DENY, bonus fail-closed check) --"
POLL5="$(curl -s "http://127.0.0.1:$PORT/v1/gateway/poll/does-not-exist")"
log "poll response: $POLL5"
STATUS5="$(echo "$POLL5" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
if [ "$STATUS5" = "DENY" ]; then
  log "PASS: test 5 unknown ticket -> DENY"
  PASS=$((PASS+1))
else
  log "FAIL: test 5 expected DENY, got $STATUS5"
  FAIL=$((FAIL+1))
fi

stop_server
wait "$SERVER_PID" 2>/dev/null || true
trap - EXIT

log ""
log "== RESULT: $PASS passed, $FAIL failed (5 checks total) =="

{
  echo "# LLM-5 gateway smoke log ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
  echo
  echo '```'
  cat "$OUT"
  echo '```'
} > "$LOG_MD"
rm -f "$OUT"

[ "$FAIL" -eq 0 ]
