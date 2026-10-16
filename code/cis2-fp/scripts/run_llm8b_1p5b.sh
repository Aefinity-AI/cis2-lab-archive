#!/usr/bin/env bash
# LLM-8b Phase 2: download Qwen/Qwen2-1.5B (resumable, size+sha256 pinned) and run
# cis2_ref --stream-weights against it. Meant to run detached under
# systemd-run (see systemd unit leg-llm8b-1p5b). Logs everything to
# docs/hardware_logs/llm8b_1p5b_<host>_<date>.log.
set -uo pipefail
cd <home>/projects/cis2-fp-cm-llm8b-stream
mkdir -p weights_qwen2_1_5b docs/hardware_logs
LOG="docs/hardware_logs/llm8b_1p5b_$(hostname)_$(date -u +%F).log"
W=weights_qwen2_1_5b/model.safetensors
URL=https://huggingface.co/Qwen/Qwen2-1.5B/resolve/main/model.safetensors
# Expected size + sha256 from HF headers (content-length / x-linked-etag), pinned 2026-09-18.
EXP_SIZE=3087467144
EXP_SHA=6f3a62caedc5c5278275bf5eed428806eeac8df927a3d333c3c850402c24cdeb
size() { stat -c %s "$W" 2>/dev/null || echo 0; }
{
  echo "=== leg-llm8b-1p5b start $(date -u -Iseconds) ==="
  echo "host: $(hostname), pinned target digest (LLM-4/LLM-5b Kaggle) = 9a463f443223b46c29f0d0ca3dfbcbc6bfb8e2b6c2dd1514967f460dba9d4bf8"
  tries=0
  while [ "$(size)" -lt "$EXP_SIZE" ] && [ "$tries" -lt 6 ]; do
    tries=$((tries+1))
    echo "=== download/resume attempt $tries (have $(size) / $EXP_SIZE bytes) $(date -u -Iseconds) ==="
    curl -sL -C - --retry 8 --retry-delay 10 --retry-all-errors -o "$W" "$URL" || true
  done
  echo "=== download done $(date -u -Iseconds) size=$(size) expected=$EXP_SIZE ==="
  if [ "$(size)" -ne "$EXP_SIZE" ]; then echo "ABORT: size mismatch (truncated download)"; exit 2; fi
  GOT_SHA=$(sha256sum "$W" | awk '{print $1}')
  if [ "$GOT_SHA" != "$EXP_SHA" ]; then echo "ABORT: sha256 mismatch got=$GOT_SHA expected=$EXP_SHA"; exit 3; fi
  echo "weights sha256 OK ($GOT_SHA == HF x-linked-etag)"
  ls -la weights_qwen2_1_5b/
  sha256sum weights_qwen2_1_5b/config.json weights_qwen2_1_5b/tokenizer.json
  echo "=== cis2_ref run start $(date -u -Iseconds) ==="
  RUST_BACKTRACE=1 timeout 8h ./target/release/cis2_ref --stream-weights --weights-dir weights_qwen2_1_5b --gen-toks 8
  rc=$?
  echo "=== cis2_ref run end $(date -u -Iseconds) rc=$rc ==="
} >> "$LOG" 2>&1
