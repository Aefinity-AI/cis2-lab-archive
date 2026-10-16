#!/usr/bin/env bash
# cis2-oflags-1 (ledger): does the CIS-2 C driver's digest depend on the compiler optimisation level?
# Rebuild verify3 sv5_driver at -O0/-O1/-O2/-O3/-Os/-O3 -march=native with the spec flags, plus a -ffast-math POSITIVE CONTROL,
# replay the first two chunks (100 items) of the 135M guard replay with each binary, compare witness+argmax to the recorded box5 rows.
set -u
L=${LEG_OUT:-$PWD}; SRC=$HOME/sv5/arma/verify3; G=$HOME/g2-135; W=$HOME/oflags; mkdir -p $W
SPEC="-ffp-contract=off -fno-fast-math -fexcess-precision=standard -std=c11 -Wall -Wextra -mno-fma"
declare -A V=( [O0]="-O0 $SPEC" [O1]="-O1 $SPEC" [O2]="-O2 $SPEC" [O3]="-O3 $SPEC" [Os]="-Os $SPEC" [O3native]="-O3 -march=native $SPEC" [CTRL_fastmath]="-O2 -ffast-math -std=c11 -Wall -Wextra -mno-fma" )
ORDER="O2 O0 O1 O3 Os O3native CTRL_fastmath"
: > $L/RESULT.txt
echo "cis2-oflags-1 host=$(hostname) cpu=$(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2) gcc=$(gcc -dumpfullversion) weights=$(cat $G/WEIGHTS_SHA256) ref_rows=$(cat $G/out/box5/c000.jsonl $G/out/box5/c001.jsonl | wc -l)" >> $L/RESULT.txt
norm() { sed -E 's/.*"idx": ([0-9]+).*"ids_out": \[([0-9, ]*)\].*"witness": "([0-9a-f]+)".*"argmax": "([0-9a-f]+)".*/\1 \2 \3 \4/' "$@" | sort -n; }
norm $G/out/box5/c000.jsonl $G/out/box5/c001.jsonl > $W/ref.txt
nfail=0
for v in $ORDER; do
  d=$W/$v; rm -rf $d; mkdir -p $d; cp $SRC/*.c $SRC/*.h $SRC/Makefile $d/
  if ! ( cd $d && make -s sv5 CFLAGS="${V[$v]}" > build.log 2>&1 ); then echo "$v BUILD_FAIL" >> $L/RESULT.txt; nfail=$((nfail+1)); continue; fi
  sha=$(sha256sum $d/sv5_driver | cut -c1-16)
  rm -rf $G/out/box5-$v $G/locks/box5-$v
  t0=$(date +%s); SV5_DRIVER=$d/sv5_driver bash $G/replay_job.sh $G box5-$v 2 2 > /dev/null 2>&1; t1=$(date +%s)
  norm $G/out/box5-$v/c000.jsonl $G/out/box5-$v/c001.jsonl > $d/rows.txt 2>/dev/null
  n=$(wc -l < $d/rows.txt); same=$(comm -12 $W/ref.txt $d/rows.txt | wc -l); tokdiff=$(join <(cut -d' ' -f1,2 $W/ref.txt) <(cut -d' ' -f1,2 $d/rows.txt) | awk '$2!=$3' | wc -l)
  echo "$v flags=[${V[$v]}] bin_sha16=$sha rows=$n identical_rows=$same/$(wc -l < $W/ref.txt) verdict_token_diffs=$tokdiff wall_s=$((t1-t0))" >> $L/RESULT.txt
  case $v in CTRL*) ;; *) [ "$same" = "$(wc -l < $W/ref.txt)" ] && [ "$n" = "$(wc -l < $W/ref.txt)" ] || nfail=$((nfail+1));; esac
done
cp $L/RESULT.txt $W/RESULT.txt
if [ $nfail -eq 0 ]; then echo "RESULT: OK all six spec builds identical to the box5 reference rows (see control line)" >> $L/RESULT.txt; else echo "RESULT: DIFFER $nfail spec build(s) not identical or failed" >> $L/RESULT.txt; fi
