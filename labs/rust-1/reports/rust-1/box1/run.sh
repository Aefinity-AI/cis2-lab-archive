#!/usr/bin/env bash
# rust-1 ARM L (cis2_ref against verify3/sv5_driver, plain teacher-forced decode, SmolLM2-135M) timing job on box1. rust-1 is arm L alone; the library arms are rust-1b.
# Payload ~/feed-payload/rust1, dest <home>/rust1. Weights come from the box own ~/sv5/arma/weights (sha256 checked by run.py; not shipped).
# R5 DISCLOSURE: the 2026-10-04 ruling says no CPUQuota. cm-feed cannot omit the quota (an empty --cpu-quota is refused by its field check, systemd rejects "infinity"), so the add line gives 100% x the number of
# logical CPUs, which does not bind; run.py logs cpu.max at every cgroup level and RESULT says cpu_quota_binding=. MemoryMax per the bar (see BUILD.md); run.py refuses to time if the cgroup memory.max differs.
# The first timing job on a host is also the host check of the 2026-10-04 timing ruling (cite its log).
# run.py pins the arm to one core and the sampler to another, logs cpu.max, echoes every R1_* value, measures an idle baseline of the foreign load before rep 0, voids a rep with more other load than baseline + margin during the run,
# and counts its elapsed seconds against the registered cap.
# Frozen hashes (FREEZE-ARM-L.md): sha256 of $HOME/rust1/PAYLOAD_SHA256 and of $HOME/rust1/run.py. A difference ends the job INVALID before anything runs.
EXP_PAYLOAD_SHA256=dc446d789027f1a61edf399d68f4601644890d896ca9c2919924a2dc7cce8ac9
EXP_RUNPY_SHA256=300a10b736c99342129d06afb3a3f9e465f4d5af1f8b1ff162f016a94cdcd13c
H=box1
P=$HOME/rust1
GOT_P=$(sha256sum "$P/PAYLOAD_SHA256" 2>/dev/null | cut -d' ' -f1)
GOT_R=$(sha256sum "$P/run.py" 2>/dev/null | cut -d' ' -f1)
if [ "$GOT_P" != "$EXP_PAYLOAD_SHA256" ] || [ "$GOT_R" != "$EXP_RUNPY_SHA256" ]; then
  L="RESULT: INVALID host=$H reason=payload_or_runner_differs_from_frozen_sha256 payload_sha256=${GOT_P:-MISSING} run_py_sha256=${GOT_R:-MISSING} frozen_payload_sha256=$EXP_PAYLOAD_SHA256 frozen_run_py_sha256=$EXP_RUNPY_SHA256 nothing_timed=yes"
  echo "$L"
  if [ -n "${LEG_OUT:-}" ]; then mkdir -p "$LEG_OUT"; echo "$L" > "$LEG_OUT/RESULT.txt"; fi
  exit 0
fi
export R1_FROZEN_PAYLOAD_SHA256=$EXP_PAYLOAD_SHA256 R1_FROZEN_RUNPY_SHA256=$EXP_RUNPY_SHA256
# ---- box1: pause the periodic user units that would overlap reps (2026-10-04 ruling: timing on an idle host). Real unit names, read over ssh 2026-10-04: cm-tick.timer (every 2 h), cm-rc-watch.timer (every 10 min).
# cm-legd.timer / cm-legd.service (the feeder) and the job unit are NOT touched. A service that is already running is not stopped; the wrapper waits up to 10 minutes for cm-tick.service and cm-rc-watch.service to end.
TIMERS="cm-tick.timer cm-rc-watch.timer"
SERVICES="cm-tick.service cm-rc-watch.service"
PAUSED=""
CAND=""
FAILSAFE=r1-restore-timers-$$
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
    sed -i "1s|$| timers_restored=${RESTORED:-none}|" "$LEG_OUT/RESULT.txt"
  elif [ -n "${LEG_OUT:-}" ]; then
    mkdir -p "$LEG_OUT"; echo "RESULT: INVALID host=$H reason=runner_gone_without_result timers_paused=${PAUSED_TXT:-none} timers_restored=${RESTORED:-none} nothing_timed=unknown" >> "$LEG_OUT/RESULT.txt"
  fi
}
trap restore_timers EXIT
trap 'exit 143' TERM INT HUP
for t in $TIMERS; do
  if systemctl --user is-active --quiet "$t"; then CAND="$CAND $t"; fi
done
CAND=${CAND# }
if [ -n "$CAND" ]; then
  if systemd-run --user --quiet --collect --unit="$FAILSAFE" --on-active=30600s systemctl --user start $CAND >/dev/null 2>&1; then
    for t in $CAND; do
      if systemctl --user stop "$t" >/dev/null 2>&1; then PAUSED="$PAUSED $t"; fi
    done
    PAUSED=${PAUSED# }
  else
    echo "timers not paused: the failsafe restore timer could not be created"
  fi
fi
PAUSED_TXT=$(echo "$PAUSED" | tr ' ' ',')
export R1_TIMERS_PAUSED=${PAUSED_TXT:-none}
echo "timers_paused=$R1_TIMERS_PAUSED"
if [ -n "$PAUSED" ]; then
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
bash $P/run.sh $H
exit $?
