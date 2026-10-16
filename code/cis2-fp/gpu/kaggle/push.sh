#!/bin/bash
# gpu/kaggle/push.sh — push the E18/E18c GPU kernel (e18b_gpu.py +
# kernel-metadata.json) to Kaggle.
#
# As of E18c this kernel tests BOTH reduction orders in one run: the
# spec-NORMATIVE v0.3b sequential path (governs the kernel's exit status)
# and the v0.4 CANDIDATE pinned tree path (reported as CANDIDATE PASS/
# FAIL, never gates exit status) — see e18b_gpu.py's module docstring and
# gpu/README.md SS12/SS11.
#
# DO NOT RUN THIS MANUALLY until GPU quota is available — see the GUARDED, AUTOMATED path
# below, which is how this actually gets pushed.
#
# Guarded one-shot push: ~/bin/kaggle-e18-gpu-push.sh, fired by the
# systemd --user timer kaggle-e18-gpu-push.timer (OnCalendar
# 2026-09-05 01:30 UTC, i.e. the Kaggle weekly GPU quota reset,
# Persistent=true). That script pushes exactly once, logs to
# ~/kaggle-e18-gpu-push.log, notifies via `cm push`, and disables its own
# timer. If refused, it re-arms a one-hour transient retry
# (systemd-run --on-active=3600, capped at 12 attempts, counter in
# ~/.kaggle-e18-gpu-push-retries). Check its state:
#   systemctl --user list-timers kaggle-e18-gpu-push.timer
#   tail ~/kaggle-e18-gpu-push.log
#
# This script (push.sh) itself is what that guard invokes — it is not, on
# its own, gated on anything. Run it BY HAND only if Justin says to go
# and you have independently confirmed both guard conditions above, or if
# deliberately bypassing the guarded path.
#
# Prerequisite: the dataset must exist first — run make_dataset.sh (or
# confirm it already ran) before this.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KAGGLE_BIN="${KAGGLE_BIN:-$HOME/.local/bin/kaggle}"

echo "About to push the E18b GPU kernel. This requires free GPU quota."
echo "If you have not confirmed quota is available, Ctrl-C now."
echo
"$KAGGLE_BIN" kernels push -p "$HERE"
echo "Pushed. Poll status with:"
echo "  $KAGGLE_BIN kernels status aefinityaiinc/e18b-gpu"
echo "Pull the output log with:"
echo "  $KAGGLE_BIN kernels output aefinityaiinc/e18b-gpu -p ./e18b-gpu-output"
