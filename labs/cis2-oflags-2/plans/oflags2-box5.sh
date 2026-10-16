#!/usr/bin/env bash
# cis2-oflags-2 (ledger): does the CIS-2 C driver's digest depend on the compiler VENDOR (clang vs gcc)?
# Rebuild verify3 sv5_driver with clang -O2/-O3 (spec flags), a fresh gcc -O2 anchor, and a clang -ffast-math POSITIVE CONTROL;
# replay chunks c000+c001 (100 items) of the 135M guard replay with each binary, compare witness+argmax to the recorded box5 rows.
# Modelled on oflags-box5.sh; same RESULT.txt line format. Fails soft (RESULT: SKIP ...) if clang is unavailable.
set -u
L=${LEG_OUT:-$PWD}; SRC=$HOME/sv5/arma/verify3; G=$HOME/g2-135; W=$HOME/oflags2; mkdir -p $W
: > $L/RESULT.txt
skip() { echo "RESULT: SKIP clang unavailable ($1)" >> $L/RESULT.txt; cp $L/RESULT.txt $W/RESULT.txt; exit 0; }
if ! command -v clang >/dev/null 2>&1; then
  { sudo -n apt-get install -y --no-install-recommends clang > $W/apt.log 2>&1; } || true
fi
command -v clang >/dev/null 2>&1 || skip "apt-get install clang failed or sudo unavailable; see $W/apt.log"
clang --version >/dev/null 2>&1 || skip "clang present but not runnable"
# clang spellings; -fexcess-precision=standard is gcc-only and is omitted for clang (x86-64 SSE math needs no excess precision).
SPECG="-ffp-contract=off -fno-fast-math -fexcess-precision=standard -std=c11 -Wall -Wextra -mno-fma"
SPECC="-ffp-contract=off -fno-fast-math -std=c11 -Wall -Wextra -mno-fma"
declare -A V=( [clang_O2]="-O2 $SPECC" [clang_O3]="-O3 $SPECC" [gcc_O2_anchor]="-O2 $SPECG" [CTRL_clang_fastmath]="-O2 -ffast-math -std=c11 -Wall -Wextra -mno-fma" )
declare -A CCV=( [clang_O2]=clang [clang_O3]=clang [gcc_O2_anchor]=gcc [CTRL_clang_fastmath]=clang )
ORDER="gcc_O2_anchor clang_O2 clang_O3 CTRL_clang_fastmath"
echo "cis2-oflags-2 host=$(hostname) cpu=$(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2) clang=$(clang --version | head -1) gcc=$(gcc --version | head -1) weights=$(cat $G/WEIGHTS_SHA256) ref_rows=$(cat $G/out/box5/c000.jsonl $G/out/box5/c001.jsonl | wc -l)" >> $L/RESULT.txt
norm() { sed -E 's/.*"idx": ([0-9]+).*"ids_out": \[([0-9, ]*)\].*"witness": "([0-9a-f]+)".*"argmax": "([0-9a-f]+)".*/\1 \2 \3 \4/' "$@" | sort -n; }
norm $G/out/box5/c000.jsonl $G/out/box5/c001.jsonl > $W/ref.txt
nref=$(wc -l < $W/ref.txt)
nfail=0
for v in $ORDER; do
  d=$W/$v; rm -rf $d; mkdir -p $d; cp $SRC/*.c $SRC/*.h $SRC/Makefile $d/
  if ! ( cd $d && make -s sv5 CC=${CCV[$v]} CFLAGS="${V[$v]}" > build.log 2>&1 ); then echo "$v BUILD_FAIL" >> $L/RESULT.txt; nfail=$((nfail+1)); continue; fi
  sha=$(sha256sum $d/sv5_driver | cut -c1-16)
  rm -rf $G/out/box5-$v $G/locks/box5-$v
  t0=$(date +%s); SV5_DRIVER=$d/sv5_driver bash $G/replay_job.sh $G box5-$v 2 2 > /dev/null 2>&1; t1=$(date +%s)
  norm $G/out/box5-$v/c000.jsonl $G/out/box5-$v/c001.jsonl > $d/rows.txt 2>/dev/null
  n=$(wc -l < $d/rows.txt); same=$(comm -12 $W/ref.txt $d/rows.txt | wc -l); tokdiff=$(join <(cut -d' ' -f1,2 $W/ref.txt) <(cut -d' ' -f1,2 $d/rows.txt) | awk '$2!=$3' | wc -l)
  echo "$v flags=[${CCV[$v]} ${V[$v]}] bin_sha16=$sha rows=$n identical_rows=$same/$nref verdict_token_diffs=$tokdiff wall_s=$((t1-t0))" >> $L/RESULT.txt
  case $v in CTRL*) ;; *) [ "$same" = "$nref" ] && [ "$n" = "$nref" ] || nfail=$((nfail+1));; esac
  rm -f $d/*.o $d/sv5_driver   # keep rows.txt/build.log; free disk/RAM-backed space between builds
done
cp $L/RESULT.txt $W/RESULT.txt
if [ $nfail -eq 0 ]; then echo "RESULT: OK gcc anchor and both clang spec builds identical to the box5 reference rows (see control line)" >> $L/RESULT.txt; else echo "RESULT: DIFFER $nfail spec build(s) not identical or failed" >> $L/RESULT.txt; fi
