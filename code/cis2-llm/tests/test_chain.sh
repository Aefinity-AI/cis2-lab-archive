#!/usr/bin/env bash
# LLM-1 chain-integrity test: start server (same helpers as tests/smoke.sh),
# issue 3 receipts, `chain` on the untouched log -> PASS, overwrite line 1
# with a stale/tampered record, `chain` -> FAIL (line number), and
# `verify <last-id>` -> FAIL (chain broken before it). Writes
# tests/TEST-CHAIN-LOG.md with the real output. Heavy (build+model load)
# so callers should run this under `flock /tmp/xxon-heavy.lock`.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVER_DIR="$ROOT/server"
LOG_MD="$ROOT/tests/TEST-CHAIN-LOG.md"
PORT="${CIS2_LLM_CHAIN_PORT:-8798}"
DATA_DIR="$SERVER_DIR/data"

echo "== cis2-llm chain test ==" | tee "$LOG_MD.tmp"

rm -rf "$DATA_DIR"

echo "-- starting server --" | tee -a "$LOG_MD.tmp"
(cd "$SERVER_DIR" && exec uv run uvicorn app.main:app --host 127.0.0.1 --port "$PORT" \
  >/tmp/cis2-llm-chain-server.log 2>&1) &
SERVER_PID=$!
# kill the whole tree (uv -> uvicorn) so an orphaned server never keeps the flock fd
stop_server() { pkill -TERM -P "$SERVER_PID" 2>/dev/null || true; kill "$SERVER_PID" 2>/dev/null || true; }
trap 'stop_server' EXIT

if ! curl -sf --retry 30 --retry-delay 1 --retry-connrefused \
    "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then
  echo "FAIL: server did not come up" | tee -a "$LOG_MD.tmp"
  cat /tmp/cis2-llm-chain-server.log | tee -a "$LOG_MD.tmp"
  mv "$LOG_MD.tmp" "$LOG_MD"
  exit 1
fi
echo "server up on :$PORT" | tee -a "$LOG_MD.tmp"

echo "-- issuing 3 receipts --" | tee -a "$LOG_MD.tmp"
RIDS=()
for i in 1 2 3; do
  RESP="$(curl -s -X POST "http://127.0.0.1:$PORT/v1/chat/completions" \
    -H 'Content-Type: application/json' \
    -d '{"messages":[{"role":"user","content":"hello '"$i"'"}]}')"
  RID="$(echo "$RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin)["cis2"]["receipt_id"])')"
  if [ -z "$RID" ]; then
    echo "FAIL: no receipt_id in response $i" | tee -a "$LOG_MD.tmp"
    echo "$RESP" | tee -a "$LOG_MD.tmp"
    mv "$LOG_MD.tmp" "$LOG_MD"
    exit 1
  fi
  echo "receipt $i id=$RID" | tee -a "$LOG_MD.tmp"
  RIDS+=("$RID")
done
LAST_RID="${RIDS[2]}"

echo "-- GET /v1/chain_status (expect chain_ok=true) --" | tee -a "$LOG_MD.tmp"
curl -s "http://127.0.0.1:$PORT/v1/chain_status" | tee -a "$LOG_MD.tmp"
echo | tee -a "$LOG_MD.tmp"

stop_server
wait $SERVER_PID 2>/dev/null || true
trap - EXIT

LOG_FILE="$DATA_DIR/receipts.jsonl"

echo "-- chain (expect PASS, untampered log) --" | tee -a "$LOG_MD.tmp"
CHAIN_OUT="$(cd "$ROOT" && uv run --project server python3 verifier/cis2_verify_cli.py chain "$LOG_FILE" 2>&1)"
CHAIN_RC=$?
echo "$CHAIN_OUT" | tee -a "$LOG_MD.tmp"
if [ $CHAIN_RC -ne 0 ]; then
  echo "FAIL: expected chain PASS on untampered log, got exit $CHAIN_RC" | tee -a "$LOG_MD.tmp"
  mv "$LOG_MD.tmp" "$LOG_MD"
  exit 1
fi

echo "-- verify last receipt on untampered log (expect PASS) --" | tee -a "$LOG_MD.tmp"
VERIFY_OUT="$(cd "$ROOT" && uv run --project server python3 verifier/cis2_verify_cli.py verify "$LAST_RID" 2>&1)"
VERIFY_RC=$?
echo "$VERIFY_OUT" | tee -a "$LOG_MD.tmp"
if [ $VERIFY_RC -ne 0 ]; then
  echo "FAIL: expected verify PASS on untampered log, got exit $VERIFY_RC" | tee -a "$LOG_MD.tmp"
  mv "$LOG_MD.tmp" "$LOG_MD"
  exit 1
fi

echo "-- overwrite line 1 with a stale record, chain (expect FAIL) --" | tee -a "$LOG_MD.tmp"
python3 - "$LOG_FILE" <<'PYEOF'
import json
import sys

path = sys.argv[1]
lines = open(path).read().splitlines()
first = json.loads(lines[0])
# A "stale record" plausible-looking tamper: replace the payload with an
# earlier-looking but internally-recomputed record so a naive "does line 1
# parse and have the right fields" check would not catch it -- only
# recomputing the hash chain does. We flip one hex char of the stored
# log_hash itself (simulating a substituted/rolled-back earlier receipt
# whose recorded hash no longer matches its own content).
lh = first["log_hash"]
new_last = "0" if lh[-1] != "0" else "1"
first["log_hash"] = lh[:-1] + new_last
lines[0] = json.dumps(first, sort_keys=True)
open(path, "w").write("\n".join(lines) + "\n")
PYEOF
echo "line 1 after tamper:" | tee -a "$LOG_MD.tmp"
head -n1 "$LOG_FILE" | tee -a "$LOG_MD.tmp"

CHAIN_TAMPER_OUT="$(cd "$ROOT" && uv run --project server python3 verifier/cis2_verify_cli.py chain "$LOG_FILE" 2>&1)"
CHAIN_TAMPER_RC=$?
echo "$CHAIN_TAMPER_OUT" | tee -a "$LOG_MD.tmp"
if [ $CHAIN_TAMPER_RC -eq 0 ]; then
  echo "FAIL: expected chain FAIL after tampering line 1, got PASS" | tee -a "$LOG_MD.tmp"
  mv "$LOG_MD.tmp" "$LOG_MD"
  exit 1
fi
if ! echo "$CHAIN_TAMPER_OUT" | grep -q "line 0"; then
  echo "FAIL: expected chain FAIL output to name line 0 (the tampered first line)" | tee -a "$LOG_MD.tmp"
  mv "$LOG_MD.tmp" "$LOG_MD"
  exit 1
fi

echo "-- verify last receipt on tampered log (expect FAIL, chain broken before it) --" | tee -a "$LOG_MD.tmp"
VERIFY_TAMPER_OUT="$(cd "$ROOT" && uv run --project server python3 verifier/cis2_verify_cli.py verify "$LAST_RID" 2>&1)"
VERIFY_TAMPER_RC=$?
echo "$VERIFY_TAMPER_OUT" | tee -a "$LOG_MD.tmp"
if [ $VERIFY_TAMPER_RC -eq 0 ]; then
  echo "FAIL: expected verify FAIL for $LAST_RID after tampering line 1, got PASS" | tee -a "$LOG_MD.tmp"
  mv "$LOG_MD.tmp" "$LOG_MD"
  exit 1
fi

echo | tee -a "$LOG_MD.tmp"
echo "PASS: chain check passes on an untampered log and fails (with line number) after tampering an earlier line; verify of a later receipt correctly fails too." | tee -a "$LOG_MD.tmp"
{
  echo "# LLM-1 chain test log ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
  echo
  echo '```'
  cat "$LOG_MD.tmp"
  echo '```'
} > "$LOG_MD"
rm -f "$LOG_MD.tmp"
exit 0
