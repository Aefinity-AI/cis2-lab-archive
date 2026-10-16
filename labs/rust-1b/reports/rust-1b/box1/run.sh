#!/usr/bin/env bash
# rust-1b (FRAMEWORK and KERNELS, stage 2 of rust-1) timing job rust1b-box1-n1 on box1: G-OB, G-MKL, X (Rust), T (PyTorch), Q (llama.cpp F32), Q8_0 extra; SmolLM2-135M, teacher-forced 64 ids x 8 prompts. Phases: n1.
# Payload ~/feed-payload/rust1b, dest <home>/rust1b. The bf16 weights come from the box own ~/sv5/arma/weights (sha256 checked by run.py); the fp32 file and the GGUFs are in the payload (hash-checked).
# R5 DISCLOSURE (carried from rust-1): the 2026-10-04 ruling says no CPUQuota. cm-feed cannot omit the quota, so the add line gives 100% x the number of logical CPUs, which does not bind;
# run.py logs cpu.max at every cgroup level and RESULT says cpu_quota_binding=. MemoryMax per the bar; run.py refuses to time if the cgroup memory.max differs.
# run.py pins the arm, measures an idle baseline of the foreign load before the first check, voids a rep with more other load than baseline + margin, and counts its elapsed seconds against the lab caps (file ~/.rust1_budget_box1, shared with rust-1).
# Frozen hashes (FREEZE-STAGE2.md): sha256 of $HOME/rust1b/PAYLOAD_SHA256 and of $HOME/rust1b/run.py. A difference ends the job INVALID before anything runs.
EXP_PAYLOAD_SHA256=a2a1b3ee332f171cfb80adbceb4414af9427440b73964334c86e1044fb691cf8
EXP_RUNPY_SHA256=bcd0fa38eca6eebd338eb7a32c73978168b6ea3ae269e51154240440426e431f
H=box1
P=$HOME/rust1b
GOT_P=$(sha256sum "$P/PAYLOAD_SHA256" 2>/dev/null | cut -d' ' -f1)
GOT_R=$(sha256sum "$P/run.py" 2>/dev/null | cut -d' ' -f1)
if [ "$GOT_P" != "$EXP_PAYLOAD_SHA256" ] || [ "$GOT_R" != "$EXP_RUNPY_SHA256" ]; then
  L="RESULT: INVALID host=$H reason=payload_or_runner_differs_from_frozen_sha256 payload_sha256=${GOT_P:-MISSING} run_py_sha256=${GOT_R:-MISSING} frozen_payload_sha256=$EXP_PAYLOAD_SHA256 frozen_run_py_sha256=$EXP_RUNPY_SHA256 nothing_timed=yes"
  echo "$L"
  if [ -n "${LEG_OUT:-}" ]; then mkdir -p "$LEG_OUT"; echo "$L" > "$LEG_OUT/RESULT.txt"; fi
  exit 0
fi
export R1B_FROZEN_PAYLOAD_SHA256=$EXP_PAYLOAD_SHA256 R1B_FROZEN_RUNPY_SHA256=$EXP_RUNPY_SHA256
# ---- box1: pause the periodic user units that would overlap reps (2026-10-04 ruling: timing on an idle host). Unit names read over ssh 2026-10-04: cm-tick.timer (every 1 h), cm-rc-watch.timer (every 10 min).
# cm-legd.timer / cm-legd.service (the feeder) and the job unit are NOT touched. A service that is already running is not stopped; the wrapper waits up to 10 minutes for cm-tick.service and cm-rc-watch.service to end.
TIMERS="cm-tick.timer cm-rc-watch.timer"
SERVICES="cm-tick.service cm-rc-watch.service"
PAUSED=""
STOPPED=""
CAND=""
FAILSAFE=r1b-restore-timers-$$
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
  if systemd-run --user --quiet --collect --unit="$FAILSAFE" --on-active=30600s systemctl --user start $CAND >/dev/null 2>&1; then
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
export R1B_TIMERS_PAUSED=${STOPPED_TXT:-none}
echo "timers_paused=$R1B_TIMERS_PAUSED"
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
export R1B_PHASES=n1
bash $P/run.sh $H
exit $?
