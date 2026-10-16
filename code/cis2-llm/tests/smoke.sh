#!/usr/bin/env bash
# LLM-1 smoke test: start server, issue one receipt, verify PASS, tamper
# one byte, verify FAIL. Writes tests/SMOKE-LOG.md with the real output.
# Heavy (build+model load) so callers should run this under
# `flock /tmp/xxon-heavy.lock`.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVER_DIR="$ROOT/server"
LOG_MD="$ROOT/tests/SMOKE-LOG.md"
PORT="${CIS2_LLM_SMOKE_PORT:-8799}"
DATA_DIR="$SERVER_DIR/data"

echo "== cis2-llm smoke test ==" | tee "$LOG_MD.tmp"

rm -rf "$DATA_DIR"

echo "-- starting server --" | tee -a "$LOG_MD.tmp"
(cd "$SERVER_DIR" && exec uv run uvicorn app.main:app --host 127.0.0.1 --port "$PORT" \
  >/tmp/cis2-llm-smoke-server.log 2>&1) &
SERVER_PID=$!
# kill the whole tree (uv -> uvicorn) so an orphaned server never keeps the flock fd
stop_server() { pkill -TERM -P "$SERVER_PID" 2>/dev/null || true; kill "$SERVER_PID" 2>/dev/null || true; }
trap 'stop_server' EXIT

if ! curl -sf --retry 30 --retry-delay 1 --retry-connrefused \
    "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then
  echo "FAIL: server did not come up" | tee -a "$LOG_MD.tmp"
  cat /tmp/cis2-llm-smoke-server.log | tee -a "$LOG_MD.tmp"
  mv "$LOG_MD.tmp" "$LOG_MD"
  exit 1
fi
echo "server up on :$PORT" | tee -a "$LOG_MD.tmp"

echo "-- issuing one receipt --" | tee -a "$LOG_MD.tmp"
RESP="$(curl -s -X POST "http://127.0.0.1:$PORT/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"hello"}]}')"
echo "$RESP" | tee -a "$LOG_MD.tmp"

RID="$(echo "$RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin)["cis2"]["receipt_id"])')"
if [ -z "$RID" ]; then
  echo "FAIL: no receipt_id in response" | tee -a "$LOG_MD.tmp"
  mv "$LOG_MD.tmp" "$LOG_MD"
  exit 1
fi
echo "receipt_id=$RID" | tee -a "$LOG_MD.tmp"

echo "-- GET /v1/receipts/{id} --" | tee -a "$LOG_MD.tmp"
curl -s "http://127.0.0.1:$PORT/v1/receipts/$RID" | tee -a "$LOG_MD.tmp"
echo | tee -a "$LOG_MD.tmp"

echo "-- verify (expect PASS) --" | tee -a "$LOG_MD.tmp"
stop_server
wait $SERVER_PID 2>/dev/null || true
trap - EXIT

VERIFY_OUT="$(cd "$ROOT" && uv run --project server python3 verifier/cis2_verify_cli.py verify "$RID" 2>&1)"
VERIFY_RC=$?
echo "$VERIFY_OUT" | tee -a "$LOG_MD.tmp"
if [ $VERIFY_RC -ne 0 ]; then
  echo "FAIL: expected PASS, got exit $VERIFY_RC" | tee -a "$LOG_MD.tmp"
  mv "$LOG_MD.tmp" "$LOG_MD"
  exit 1
fi

echo "-- tamper one byte in the receipt log, verify (expect FAIL) --" | tee -a "$LOG_MD.tmp"
LOG_FILE="$DATA_DIR/receipts.jsonl"
TAMPERED="/tmp/cis2-llm-smoke-tampered.jsonl"
python3 - "$LOG_FILE" "$TAMPERED" <<'PYEOF'
import sys
src, dst = sys.argv[1], sys.argv[2]
data = open(src).read()
# flip the last hex char of the file (guaranteed to be inside a digest or
# the trailing '}' region's json value; digests are last field's value).
idx = data.rstrip().rfind('f')
if idx == -1:
    idx = len(data.rstrip()) - 2
data = data[:idx] + ('e' if data[idx] == 'f' else 'f') + data[idx+1:]
open(dst, 'w').write(data)
PYEOF
echo "byte-diff:" | tee -a "$LOG_MD.tmp"
diff "$LOG_FILE" "$TAMPERED" | tee -a "$LOG_MD.tmp" || true

TAMPER_OUT="$(cd "$ROOT" && uv run --project server python3 verifier/cis2_verify_cli.py verify "$TAMPERED" 2>&1)"
TAMPER_RC=$?
echo "$TAMPER_OUT" | tee -a "$LOG_MD.tmp"
if [ $TAMPER_RC -eq 0 ]; then
  echo "FAIL: expected FAIL after tamper, got PASS" | tee -a "$LOG_MD.tmp"
  mv "$LOG_MD.tmp" "$LOG_MD"
  exit 1
fi

echo | tee -a "$LOG_MD.tmp"
echo "PASS: round-trip receipt verified, tampered receipt correctly rejected." | tee -a "$LOG_MD.tmp"
{
  echo "# LLM-1 smoke log ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
  echo
  echo '```'
  cat "$LOG_MD.tmp"
  echo '```'
} > "$LOG_MD"
rm -f "$LOG_MD.tmp"
exit 0
