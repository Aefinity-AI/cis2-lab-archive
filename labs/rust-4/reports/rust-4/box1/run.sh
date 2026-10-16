#!/usr/bin/env bash
# rust-4 job on box1 (payload dest <home>/rust4). Feed with no real CPUQuota (100% x cores) and MemoryMax per the bar. All phases: install, m2, m3.
# run.py measures an idle baseline of the foreign load before anything is timed (rust-1 rule R1, same formula and constants) and voids a repetition with more other load than baseline + margin.
export R4_FROZEN_PAYLOAD_SHA256=697610dd05e120a3cffceef1cc483aa4cb384676a06294201dfe763b63d67e94
# box1: cm-tick.timer and cm-rc-watch.timer are paused for the job (failsafe restore at cap 7200 s + 30 min) and restored in an EXIT trap.
H=box1
TIMERS="cm-tick.timer cm-rc-watch.timer"
SERVICES="cm-tick.service cm-rc-watch.service"
PAUSED=""
STOPPED=""
CAND=""
FAILSAFE=r4-restore-timers-$$
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
trap 'exit 143' TERM INT HUP
for t in $TIMERS; do
  if systemctl --user is-active --quiet "$t"; then CAND="$CAND $t"; fi
done
CAND=${CAND# }
if [ -n "$CAND" ]; then
  if systemd-run --user --quiet --collect --unit="$FAILSAFE" --on-active=9000s systemctl --user start $CAND >/dev/null 2>&1; then
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
export R4_TIMERS_PAUSED=${STOPPED_TXT:-none}
echo "timers_paused=$R4_TIMERS_PAUSED"
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
python3 $HOME/rust4/run.py box1
exit $?
