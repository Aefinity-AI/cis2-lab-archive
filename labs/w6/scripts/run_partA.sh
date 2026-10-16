#!/usr/bin/env bash
# w6 Part A full run (NOT started by the harness build). Needs build_w6.sh output in $W6_OUT.
# Runs each range in two MXCSR regimes: default, and --ftz (what the engine runs under).
set -u
OUT="${W6_OUT:-$HOME/legs/w6}"; R="$OUT/RESULT-partA.txt"
say() { printf "%s\n" "$*" | tee -a "$R"; }
say "=== w6 partA start $(date -u +%FT%TZ) host=$(hostname) $(ldd --version | head -1)"
say "core-math $(git -C "${COREMATH:-$HOME/src/core-math}" rev-parse HEAD)"
LIBM=$(ldconfig -p | awk '/libm.so.6 .*x86-64/{print $NF; exit}')
say "LD_DEBUG bindings: $(LD_DEBUG=bindings "$OUT/part_a" --range pos --limit 4 2>&1 | grep "symbol .expf'" | sed 's/^ *[0-9]*: *//')"
say "libm resolver lea targets: $(objdump -d "$LIBM" --start-address=0x$(nm -D "$LIBM" | awk '/ expf@@GLIBC_2.27/{print $1}') --stop-address=$((0x$(nm -D "$LIBM" | awk '/ expf@@GLIBC_2.27/{print $1}')+0x40)) | grep -c lea) lea instructions; see README for reading"
say "--- multiprecision spot check of cr_expf (PREREG step 1)"
python3 -I "$(dirname "$0")/verify_cr.py" "$OUT/libcrexpf.so" 1000000 20261016 | tee -a "$R"
for regime in "" "--ftz"; do
  for r in neg pos band; do
    say "--- range $r regime '${regime:-default}'"
    "$OUT/part_a" --range $r $regime | tee -a "$R"
  done
done
say "=== w6 partA done $(date -u +%FT%TZ)"
