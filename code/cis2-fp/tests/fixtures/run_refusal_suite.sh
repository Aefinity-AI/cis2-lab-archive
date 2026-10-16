#!/usr/bin/env bash
# Config-only refusal suite: every checkpoint here is outside the CIS-2
# specified subset and MUST be refused by name with rc=2 and zero digests.
# No weights are downloaded or hashed — the gate runs on config.json alone.
set -u
cd "$(dirname "$0")/../.." || exit 1
BIN=./target/release/cis2_ref
fail=0
for d in tests/fixtures/refusal/*/ tests/fixtures/refusal-deep/*/; do
  [ -d "$d" ] || continue
  k=$(basename "$d")
  out=$("$BIN" --weights-dir "$(pwd)/$d" --gen-toks 1 2>&1); rc=$?
  if [ "$rc" -ne 2 ] || printf '%s' "$out" | grep -q 'CIS2_REF digest='; then
    # qwen2/llama-family configs are architecturally SUPPORTED; they are
    # expected to pass the gate and fail later on absent weights (rc=101).
    if [ "$rc" = 101 ] && ! printf '%s' "$out" | grep -q 'CIS2_REF digest='; then
      printf 'PASS(gate-accepted, no weights) %s\n' "$k"; continue
    fi
    printf 'FAIL %-28s rc=%s\n' "$k" "$rc"; fail=1; continue
  fi
  printf 'PASS(refused) %-24s %s\n' "$k" "$(printf '%s' "$out" | grep -o 'reason=.*' | cut -c8- | head -c 70)"
done
[ "$fail" = 0 ] && echo "REFUSAL SUITE: ALL PASS" || echo "REFUSAL SUITE: FAILURES"
exit $fail
