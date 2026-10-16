#!/usr/bin/env bash
# w6 Part B (NOT started by the harness build). Usage: run_partB.sh N   (pilot: 1000, full: 100000)
set -u
N="${1:?N positions}"; OUT="${W6_OUT:-$HOME/legs/w6}"; W="${WEIGHTS:-$HOME/cis2-digest/weights}"
HERE="$(cd "$(dirname "$0")" && pwd)"; R="$OUT/RESULT-partB-$N.txt"
say() { printf "%s\n" "$*" | tee -a "$R"; }
"$HERE/make_windows.py" "${SV5B:-$HOME/sv5b}/windows.jsonl" "$N" "$OUT/windows-$N.txt" | tee -a "$R"
for b in P G C; do
  s=$(date +%s)
  "$OUT/cis2_$b" --weights-dir "$W" --score-windows "$OUT/windows-$N.txt" --score-out "$OUT/score-$b-$N.txt" 2> "$OUT/score-$b-$N.err" | tee -a "$R"
  say "build $b rc=$? wall_s=$(( $(date +%s) - s ))"
done
python3 -I "$HERE/analyse.py" "$OUT/score-P-$N.txt" "$OUT/score-G-$N.txt" "$OUT/score-C-$N.txt" | tee -a "$R"
