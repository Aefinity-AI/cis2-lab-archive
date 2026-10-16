#!/usr/bin/env bash
# w6 Part B, the three builds run CONCURRENTLY (each is single-threaded and deterministic, so the
# score files are identical to run_partB.sh's; DEVIATIONS.md item 8). Usage: run_partB_par.sh N
set -u
N="${1:?N positions}"; OUT="${W6_OUT:-$HOME/legs/w6}"; W="${WEIGHTS:-$HOME/cis2-digest/weights}"
HERE="$(cd "$(dirname "$0")" && pwd)"; R="$OUT/RESULT-partB-$N.txt"
say() { printf "%s\n" "$*" | tee -a "$R"; }
"$HERE/make_windows.py" "${SV5B:-$HOME/sv5b}/windows.jsonl" "$N" "$OUT/windows-$N.txt" | tee -a "$R"
s=$(date +%s)
for b in P G C; do
  ( "$OUT/cis2_$b" --weights-dir "$W" --score-windows "$OUT/windows-$N.txt" --score-out "$OUT/score-$b-$N.txt" > "$OUT/score-$b-$N.log" 2> "$OUT/score-$b-$N.err"; echo $? > "$OUT/score-$b-$N.rc" ) &
done
wait
for b in P G C; do say "build $b rc=$(cat "$OUT/score-$b-$N.rc") (concurrent) $(cat "$OUT/score-$b-$N.log")"; done
say "wall_s_all3=$(( $(date +%s) - s ))"
python3 -I "$HERE/analyse.py" "$OUT/score-P-$N.txt" "$OUT/score-G-$N.txt" "$OUT/score-C-$N.txt" | tee -a "$R"
