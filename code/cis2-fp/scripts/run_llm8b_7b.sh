#!/usr/bin/env bash
# LLM-8b Phase 3: Qwen/Qwen2-7B on aefinity-box CPU via --stream-weights.
# Downloads the 4 bf16 shards (resumable, size+sha256 pinned from HF headers 2026-09-18),
# merges them with scripts/merge_shards.py (pure byte copy) into weights_qwen2_7b/model.safetensors,
# then runs cis2_ref --stream-weights --gen-toks 4 (same params as the Kaggle 7B runs).
# Run detached under systemd-run (unit leg-llm8b-7b-r1). Log: docs/hardware_logs/llm8b_7b_<host>_<date>.log
set -uo pipefail
cd <home>/projects/cis2-fp-cm-llm8b-stream
D=weights_qwen2_7b; mkdir -p "$D" docs/hardware_logs
LOG="docs/hardware_logs/llm8b_7b_$(hostname)_$(date -u +%F).log"
BASE=https://huggingface.co/Qwen/Qwen2-7B/resolve/main
# name size sha256  (HF content-length / x-linked-etag, pinned 2026-09-18)
SHARDS="model-00001-of-00004.safetensors 3945426872 bef59d573b8d426d38e8d364975368c6441070e8759f7a3b9e1345f6de37182a
model-00002-of-00004.safetensors 3864726352 d0b7498efcf5bf27cca76cdc86bbecf8b1a7483ba5911611bad9a89dc1209fd3
model-00003-of-00004.safetensors 3864726408 d860d93a1ea84fc38ce1a28f7ff20d91a813c1f9a3237cf60ed02707570b4c55
model-00004-of-00004.safetensors 3556392240 215200d554110010c771fd5707bbb2e404bc362242f67b004647c698bf0fabec"
EXP_CFG=d318b49c4a29771e259d93053084eb752f5bfe69c20c4f2e041bd1017884f810
EXP_TOK=f7c9b2dba4a296b1aa76c16a34b8225c0c118978400d4bb66bff0902d702f5b8
EXP_MERGED_SIZE=15231272088
KAGGLE_MERGED_SHA=0e218d281ea2c86c281db9cc6491f4a37ef7b931e57cd63b70cde999bce265ee
size() { stat -c %s "$1" 2>/dev/null || echo 0; }
{
  echo "=== leg-llm8b-7b start $(date -u -Iseconds) ==="
  echo "host: $(hostname), EXPECTED witness (re-pinned 2026-10-16, see ERRATA.md; prompt_toks=4 gen_toks=4 fp32 sequential) = a4a6770e5f049a92335bc6fe92bac87f17627b89adc4f28636cd4ab511acbfb3 (retired mis-merged Kaggle 1501ed47...)"
  for f in config.json tokenizer.json model.safetensors.index.json; do
    [ -s "$D/$f" ] || curl -sL --retry 8 --retry-delay 10 --retry-all-errors -o "$D/$f" "$BASE/$f"
  done
  [ "$(sha256sum "$D/config.json" | cut -c1-64)" = "$EXP_CFG" ] || { echo "ABORT: config.json sha mismatch"; exit 4; }
  [ "$(sha256sum "$D/tokenizer.json" | cut -c1-64)" = "$EXP_TOK" ] || { echo "ABORT: tokenizer.json sha mismatch"; exit 4; }
  echo "config/tokenizer sha256 OK"
  while read -r name esize esha; do
    W="$D/$name"; tries=0
    while [ "$(size "$W")" -lt "$esize" ] && [ "$tries" -lt 12 ]; do
      tries=$((tries+1))
      echo "=== $name download/resume attempt $tries (have $(size "$W") / $esize) $(date -u -Iseconds) ==="
      curl -sL -C - --retry 8 --retry-delay 10 --retry-all-errors -o "$W" "$BASE/$name" || true
    done
    [ "$(size "$W")" -eq "$esize" ] || { echo "ABORT: $name size $(size "$W") != $esize"; exit 2; }
    if [ ! -f "$W.sha256.ok" ]; then
      got=$(sha256sum "$W" | cut -c1-64)
      [ "$got" = "$esha" ] || { echo "ABORT: $name sha256 got=$got expected=$esha"; exit 3; }
      touch "$W.sha256.ok"
    fi
    echo "$name size+sha256 OK $(date -u -Iseconds)"
  done <<< "$SHARDS"
  if [ "$(size "$D/model.safetensors")" -ne "$EXP_MERGED_SIZE" ]; then
    echo "=== merge start $(date -u -Iseconds) ==="
    python3 scripts/merge_shards.py "$D" "$D/model.safetensors" || { echo "ABORT: merge failed"; exit 5; }
    echo "=== merge end $(date -u -Iseconds) (Kaggle merged sha256 for comparison only: $KAGGLE_MERGED_SHA) ==="
  fi
  [ "$(size "$D/model.safetensors")" -eq "$EXP_MERGED_SIZE" ] || { echo "ABORT: merged size $(size "$D/model.safetensors") != $EXP_MERGED_SIZE"; exit 6; }
  ls -la "$D"; free -m
  echo "=== cis2_ref run start $(date -u -Iseconds) ==="
  RUST_BACKTRACE=1 timeout 36h ./target/release/cis2_ref --stream-weights --weights-dir "$D" --gen-toks 4
  rc=$?
  echo "=== cis2_ref run end $(date -u -Iseconds) rc=$rc ==="
} >> "$LOG" 2>&1
