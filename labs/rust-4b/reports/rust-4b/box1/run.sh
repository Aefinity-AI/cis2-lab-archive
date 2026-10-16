#!/usr/bin/env bash
# rust-4b (cold start, per-file residency check) job on box1. Payload ~/feed-payload/rust4b, dest <home>/rust4b. Bf16 weights from the box own ~/sv5/arma/weights (sha256 checked by run.py). Needs passwordless sudo (cache drop): without it the job ends NOT RUN with the reason.
# Frozen hashes: sha256 of $HOME/rust4b/PAYLOAD_SHA256 and of $HOME/rust4b/run.py. A difference ends the job INVALID before anything runs.
EXP_PAYLOAD_SHA256=939a31be0078dff41e0202306fcbc943602b16b81a1798b624746e040205df61
EXP_RUNPY_SHA256=337a6e17b360991b2da0d2d7cc81538bc92e97d83a1cd6f1c2515a8f15a31373
H=box1
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

# ---- box1: pause the periodic user units that would overlap reps (timing ruling 2026-10-04: timing on an idle host). cm-tick.timer and cm-rc-watch.timer; cm-legd.* and the job unit are NOT touched.
TIMERS="cm-tick.timer cm-rc-watch.timer"
SERVICES="cm-tick.service cm-rc-watch.service"
PAUSED=""
STOPPED=""
CAND=""
FAILSAFE=r4b-restore-timers-$$
restore_timers() {
  trap - EXIT
  RESTORED=""
  if [ -n "$PAUSED" ]; then
    systemctl --user stop "$FAILSAFE.timer" >/dev/null 2>&1 || true
    for t in $PAUSED; do
      systemctl --user start "$t" >/dev/null 2>&1 || true
      if systemctl --user is-active --quiet "$t"; then RESTORED="$RESTORED,$t"; fi
    done
  fi
  RESTORED=${RESTORED#,}
  echo "timers_restored=${RESTORED:-none}"
  if [ -n "${LEG_OUT:-}" ] && [ -s "$LEG_OUT/RESULT.txt" ]; then
    sed -i "1s|\$| timers_restored=${RESTORED:-none}|" "$LEG_OUT/RESULT.txt"
  elif [ -n "${LEG_OUT:-}" ]; then
    mkdir -p "$LEG_OUT"; echo "RESULT: INVALID host=$H reason=runner_gone_without_result timers_paused=$(echo "${PAUSED:-none}" | tr " " ",") timers_restored=${RESTORED:-none} nothing_timed=unknown" >> "$LEG_OUT/RESULT.txt"
  fi
}
trap restore_timers EXIT
RPID=""
term_runner() { if [ -n "$RPID" ]; then kill -TERM "$RPID" 2>/dev/null; wait "$RPID" 2>/dev/null; fi; exit 143; }
trap term_runner TERM INT HUP
for t in $TIMERS; do
  if systemctl --user is-active --quiet "$t"; then CAND="$CAND $t"; fi
done
CAND=${CAND# }
if [ -n "$CAND" ]; then
  if systemd-run --user --quiet --collect --unit="$FAILSAFE" --on-active=7200s systemctl --user start $CAND >/dev/null 2>&1; then
    for t in $CAND; do
      PAUSED="$PAUSED $t"   # the record comes BEFORE the stop: a kill between the two still restores the unit
      systemctl --user stop "$t" >/dev/null 2>&1 || true
      if ! systemctl --user is-active --quiet "$t"; then STOPPED="$STOPPED $t"; fi
    done
    PAUSED=${PAUSED# }; STOPPED=${STOPPED# }
  else
    echo "timers not paused: the failsafe restore timer could not be created"
  fi
fi
STOPPED_TXT=$(echo "$STOPPED" | tr ' ' ',')
export R4B_TIMERS_PAUSED=${STOPPED_TXT:-none}
echo "timers_paused=$R4B_TIMERS_PAUSED"
if [ -n "$STOPPED" ]; then
  W=0
  while [ $W -lt 600 ]; do
    BUSY=0
    for s in $SERVICES; do
      case $(systemctl --user show -p ActiveState --value "$s" 2>/dev/null) in active|activating) BUSY=1;; esac
    done
    [ $BUSY -eq 0 ] && break
    sleep 10 & wait $!; W=$((W+10))
  done
  echo "waited_for_tick_services_s=$W"
fi
python3 $P/run.py $H &
RPID=$!
wait $RPID
RC=$?
exit $RC
