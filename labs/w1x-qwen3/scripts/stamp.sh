#!/usr/bin/env bash
# Stamp per-host job scripts from job.sh: ./stamp.sh PAYLOAD_DIR  (reads pins from the payload, never from memory)
set -eu
P="${1:-$HOME/feed-payload/cis2-qwen3}"; H="$(cd "$(dirname "$0")" && pwd)"
REV=c1899de289a04d12100db370d81485cdf75e47ca
m=$(sha256sum "$P/weights/model.safetensors" | cut -c1-64); c=$(sha256sum "$P/weights/config.json" | cut -c1-64)
t=$(sha256sum "$P/weights/tokenizer.json" | cut -c1-64); i=$(sha256sum "$P/ids/qwen3-16.txt" | cut -c1-64)
for spec in hq:sm_61 w2:none; do
  h=${spec%%:*}; sm=${spec##*:}
  sed -e "s/@NAME@/cis2-qwen3-$h/" -e "s/@SM@/$sm/" -e "s/@W_MODEL8@/${m:0:8}/" -e "s/@W_MODEL@/$m/" -e "s/@W_CONFIG@/$c/" \
      -e "s/@W_TOK@/$t/" -e "s/@W_IDS@/$i/" -e "s/@REV@/$REV/" "$H/job.sh" > "$H/job-$h.sh"; chmod +x "$H/job-$h.sh"
done
ls -l "$H"/job-*.sh
