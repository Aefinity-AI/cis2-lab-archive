#!/usr/bin/env bash
# rust-1b (FRAMEWORK and KERNELS, stage 2 of rust-1) timing job rust1b-box2 on box2: G-OB, G-MKL, X (Rust), T (PyTorch), Q (llama.cpp F32), Q8_0 extra; SmolLM2-135M, teacher-forced 64 ids x 8 prompts. Phases: n1,n2.
# Payload ~/feed-payload/rust1b, dest <home>/rust1b. The bf16 weights come from the box own ~/sv5/arma/weights (sha256 checked by run.py); the fp32 file and the GGUFs are in the payload (hash-checked).
# R5 DISCLOSURE (carried from rust-1): the 2026-10-04 ruling says no CPUQuota. cm-feed cannot omit the quota, so the add line gives 100% x the number of logical CPUs, which does not bind;
# run.py logs cpu.max at every cgroup level and RESULT says cpu_quota_binding=. MemoryMax per the bar; run.py refuses to time if the cgroup memory.max differs.
# run.py pins the arm, measures an idle baseline of the foreign load before the first check, voids a rep with more other load than baseline + margin, and counts its elapsed seconds against the lab caps (file ~/.rust1_budget_box2, shared with rust-1).
# Frozen hashes (FREEZE-STAGE2.md): sha256 of $HOME/rust1b/PAYLOAD_SHA256 and of $HOME/rust1b/run.py. A difference ends the job INVALID before anything runs.
EXP_PAYLOAD_SHA256=a2a1b3ee332f171cfb80adbceb4414af9427440b73964334c86e1044fb691cf8
EXP_RUNPY_SHA256=bcd0fa38eca6eebd338eb7a32c73978168b6ea3ae269e51154240440426e431f
H=box2
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
export R1B_PHASES=n1,n2
exec bash $P/run.sh $H
