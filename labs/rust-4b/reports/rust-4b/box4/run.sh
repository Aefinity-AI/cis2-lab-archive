#!/usr/bin/env bash
# rust-4b (cold start, per-file residency check) job on box4. Payload ~/feed-payload/rust4b, dest <home>/rust4b. Bf16 weights from the box own ~/sv5/arma/weights (sha256 checked by run.py). Needs passwordless sudo (cache drop): without it the job ends NOT RUN with the reason.
# Frozen hashes: sha256 of $HOME/rust4b/PAYLOAD_SHA256 and of $HOME/rust4b/run.py. A difference ends the job INVALID before anything runs.
EXP_PAYLOAD_SHA256=939a31be0078dff41e0202306fcbc943602b16b81a1798b624746e040205df61
EXP_RUNPY_SHA256=337a6e17b360991b2da0d2d7cc81538bc92e97d83a1cd6f1c2515a8f15a31373
H=box4
P=$HOME/rust4b
GOT_P=$(sha256sum "$P/PAYLOAD_SHA256" 2>/dev/null | cut -d' ' -f1)
GOT_R=$(sha256sum "$P/run.py" 2>/dev/null | cut -d' ' -f1)
if [ "$GOT_P" != "$EXP_PAYLOAD_SHA256" ] || [ "$GOT_R" != "$EXP_RUNPY_SHA256" ]; then
  L="RESULT: INVALID host=$H reason=payload_or_runner_differs_from_frozen_sha256 payload_sha256=${GOT_P:-MISSING} run_py_sha256=${GOT_R:-MISSING} frozen_payload_sha256=$EXP_PAYLOAD_SHA256 frozen_run_py_sha256=$EXP_RUNPY_SHA256 nothing_timed=yes"
  echo "$L"
  if [ -n "${LEG_OUT:-}" ]; then mkdir -p "$LEG_OUT"; echo "$L" > "$LEG_OUT/RESULT.txt"; fi
  exit 0
fi
export R4B_FROZEN_PAYLOAD_SHA256=$EXP_PAYLOAD_SHA256 R4B_FROZEN_RUNPY_SHA256=$EXP_RUNPY_SHA256

exec python3 $P/run.py $H
