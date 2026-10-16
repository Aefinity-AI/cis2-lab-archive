#!/usr/bin/env bash
# LLM-3 licensing test: keygen -> issue -> verify OK -> tamper one byte ->
# verify INVALID -> issue with past expiry -> verify EXPIRED.
# Writes tests/TEST-LICENSE-LOG.md with the real output.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_MD="$ROOT/tests/TEST-LICENSE-LOG.md"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

RUN=(uv run --project "$ROOT/server" python3 "$ROOT/licensing/license_tool.py")
FAIL=0

{
echo "== cis2-llm licensing test =="
echo "workdir: $TMPDIR"

echo
echo "-- keygen --"
"${RUN[@]}" keygen "$TMPDIR/priv.pem" "$TMPDIR/pub.pem"

echo
echo "-- issue (valid, far-future expiry) --"
"${RUN[@]}" issue --priv "$TMPDIR/priv.pem" --licensee "Test Co" \
  --tier per-instance --expiry 2099-01-01 --instance-id inst-1 \
  --max-receipts-per-day 1000 --out "$TMPDIR/lic-ok.json"

echo
echo "-- verify (expect OK) --"
OUT_OK="$("${RUN[@]}" verify --pub "$TMPDIR/pub.pem" --license "$TMPDIR/lic-ok.json")"
RC_OK=$?
echo "$OUT_OK"
if [ $RC_OK -ne 0 ] || ! echo "$OUT_OK" | grep -q '^OK:'; then
  echo "FAIL: expected OK, got rc=$RC_OK: $OUT_OK"
  FAIL=1
fi

echo
echo "-- tamper one byte in the license file, verify (expect INVALID) --"
python3 - "$TMPDIR/lic-ok.json" "$TMPDIR/lic-tampered.json" <<'PYEOF'
import json, sys
src, dst = sys.argv[1], sys.argv[2]
d = json.load(open(src))
# tamper the licensed instance_id — a real-world forgery attempt — leaving
# the original signature in place, so the tamper is caught by signature
# mismatch, not by JSON-parse failure.
d["license"]["instance_id"] = d["license"]["instance_id"] + "-FORGED"
json.dump(d, open(dst, "w"))
PYEOF
echo "diff:"
diff "$TMPDIR/lic-ok.json" "$TMPDIR/lic-tampered.json" || true
OUT_TAMPER="$("${RUN[@]}" verify --pub "$TMPDIR/pub.pem" --license "$TMPDIR/lic-tampered.json")"
RC_TAMPER=$?
echo "$OUT_TAMPER"
if [ $RC_TAMPER -eq 0 ] || ! echo "$OUT_TAMPER" | grep -q '^INVALID:'; then
  echo "FAIL: expected INVALID, got rc=$RC_TAMPER: $OUT_TAMPER"
  FAIL=1
fi

echo
echo "-- issue with past expiry, verify (expect EXPIRED) --"
"${RUN[@]}" issue --priv "$TMPDIR/priv.pem" --licensee "Test Co" \
  --tier eval --expiry 2020-01-01 --instance-id inst-2 \
  --max-receipts-per-day 10 --out "$TMPDIR/lic-expired.json"
OUT_EXPIRED="$("${RUN[@]}" verify --pub "$TMPDIR/pub.pem" --license "$TMPDIR/lic-expired.json")"
RC_EXPIRED=$?
echo "$OUT_EXPIRED"
if [ $RC_EXPIRED -eq 0 ] || ! echo "$OUT_EXPIRED" | grep -q '^EXPIRED:'; then
  echo "FAIL: expected EXPIRED, got rc=$RC_EXPIRED: $OUT_EXPIRED"
  FAIL=1
fi

echo
if [ "$FAIL" -eq 0 ]; then
  echo "PASS: keygen/issue/verify-OK/tamper-INVALID/expired-EXPIRED all as expected."
else
  echo "FAIL: one or more checks above did not match expectations."
fi
} 2>&1 | tee "$LOG_MD.tmp"

{
  echo "# LLM-3 licensing test log ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
  echo
  echo '```'
  cat "$LOG_MD.tmp"
  echo '```'
} > "$LOG_MD"
rm -f "$LOG_MD.tmp"

exit "$FAIL"
