#!/usr/bin/env bash
# rust-2b step 8b RUN job (UNREGISTERED documentation-build check). Payload ~/rust2b-docbuild, binary ~/rust2b-docbuild-build/rust2b_arm_b. No label (host name box1-docbuild). Same runner, reps, threads and caps as the registered box1 run.
# EXP_BIN_SHA256 is written in AFTER the build (BUILD.md 8b section "prepared"); while it is FILL_AFTER_BUILD the gate answers INVALID and nothing is timed.
EXP_PAYLOAD_SHA256=d422854a5d0732b119c1c1ed494f1ddd29ea745e825625451e87b7e69a0b2f9b
EXP_BIN_SHA256=890379674d5250b45ea7252111b0f2530a4cb3ec38aa2fc4644622700e946d39
H=box1-docbuild
P=$HOME/rust2b-docbuild
BIN=$HOME/rust2b-docbuild-build/rust2b_arm_b
GOT_P=$(sha256sum "$P/PAYLOAD_SHA256" 2>/dev/null | cut -d' ' -f1)
GOT_B=$(sha256sum "$BIN" 2>/dev/null | cut -d' ' -f1)
FRZ_B=$(sed -n 's/^PIN binary rust2b_arm_b sha256 \([0-9a-f]\{64\}\).*/\1/p' "$HOME/rust2b-docbuild-build/"FREEZE-*.txt 2>/dev/null | head -1)
BADLIST=0; (cd "$P" && sha256sum -c --quiet SHA256SUMS >/dev/null 2>&1) || BADLIST=1
if [ "$GOT_P" != "$EXP_PAYLOAD_SHA256" ] || [ $BADLIST -ne 0 ] || [ -z "$GOT_B" ] || [ "$GOT_B" != "$EXP_BIN_SHA256" ] || [ "$GOT_B" != "$FRZ_B" ]; then
  L="RESULT: INVALID host=$H reason=payload_or_binary_differs_from_frozen_sha256 payload_sha256=${GOT_P:-MISSING} binary_sha256=${GOT_B:-MISSING} freeze_binary=${FRZ_B:-MISSING} frozen_payload=$EXP_PAYLOAD_SHA256 frozen_binary=$EXP_BIN_SHA256 nothing_timed=yes"
  echo "$L"; if [ -n "${LEG_OUT:-}" ]; then mkdir -p "$LEG_OUT"; echo "$L" > "$LEG_OUT/RESULT.txt"; fi; exit 0
fi
export R2B_FROZEN_PAYLOAD_SHA256=$EXP_PAYLOAD_SHA256 R2B_FROZEN_BIN_SHA256=$EXP_BIN_SHA256 R2B_BIN=$BIN

# ---- box1: pause the periodic user units that would overlap reps (timing ruling 2026-10-04: timing on an idle host). cm-tick.timer and cm-rc-watch.timer; cm-legd.* and the job unit are NOT touched.
TIMERS="cm-tick.timer cm-rc-watch.timer"
SERVICES="cm-tick.service cm-rc-watch.service"
PAUSED=""
STOPPED=""
CAND=""
FAILSAFE=r2b-restore-timers-$$
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
export R2B_TIMERS_PAUSED=${STOPPED_TXT:-none}
echo "timers_paused=$R2B_TIMERS_PAUSED"
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
python3 $P/run_box.py $H --payload $P --bin $BIN --out "${LEG_OUT:-$HOME/legs/rust2b-docbuild-run-box1}" --reps 5 --threads 1,2 --cap-s 7200 --hard-cap-s 14400 &
RPID=$!
wait $RPID
RC=$?
exit $RC
