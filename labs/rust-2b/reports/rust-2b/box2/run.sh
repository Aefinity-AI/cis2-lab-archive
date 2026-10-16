#!/usr/bin/env bash
# rust-2b RUN job on box2 (pre-timing check, then the registered reps). Payload ~/rust2b, binary ~/rust2b-build/rust2b_arm_b (from the build job on this host).
EXP_PAYLOAD_SHA256=87b40101954077f08d3f5829e04732f5a8cab16ad24f3f016dabab9ac4452236
EXP_BIN_SHA256=7ce1acca5ddf092f3e8861da0d578d8e50d7aa3aed757675a6d4e5e5b9d4f932
H=box2
P=$HOME/rust2b
GOT_P=$(sha256sum "$P/PAYLOAD_SHA256" 2>/dev/null | cut -d' ' -f1)
GOT_B=$(sha256sum "$HOME/rust2b-build/rust2b_arm_b" 2>/dev/null | cut -d' ' -f1)
BADLIST=0; (cd "$P" && sha256sum -c --quiet SHA256SUMS >/dev/null 2>&1) || BADLIST=1
if [ "$GOT_P" != "$EXP_PAYLOAD_SHA256" ] || [ $BADLIST -ne 0 ] || { [ "$EXP_BIN_SHA256" != none ] && [ "$GOT_B" != "$EXP_BIN_SHA256" ]; }; then
  L="RESULT: INVALID host=$H reason=payload_or_binary_differs_from_frozen_sha256 payload_sha256=${GOT_P:-MISSING} binary_sha256=${GOT_B:-MISSING} frozen_payload=$EXP_PAYLOAD_SHA256 frozen_binary=$EXP_BIN_SHA256 nothing_timed=yes"
  echo "$L"; if [ -n "${LEG_OUT:-}" ]; then mkdir -p "$LEG_OUT"; echo "$L" > "$LEG_OUT/RESULT.txt"; fi; exit 0
fi
export R2B_FROZEN_PAYLOAD_SHA256=$EXP_PAYLOAD_SHA256 R2B_FROZEN_BIN_SHA256=$EXP_BIN_SHA256 R2B_BIN=$HOME/rust2b-build/rust2b_arm_b

RPID=""
python3 $P/run_box.py $H --payload $P --out "${LEG_OUT:-$HOME/legs/rust2b-run-$H}" --reps 5 --threads 1,2 --cap-s 7200 --hard-cap-s 14400 &
RPID=$!
wait $RPID
RC=$?
exit $RC
