#!/usr/bin/env bash
# rust-2a-diag job 1 (box1): perf stat + perf record on the shipped Rust gnu-O3 and the C patched -O2. Diagnostic, no label.
P=${P:-<home>/rust2a-diag-payload}; L=${LEG_OUT:-<home>/legs/rust2a-diag-box1}; mkdir -p "$L"; cd "$L"
exec > >(tee -a "$L/run.log") 2>&1
echo "perf_event_paranoid=$(cat /proc/sys/kernel/perf_event_paranoid) $(perf --version) date=$(date -u +%FT%TZ)"
bash $P/c/build_c.sh $P/c $L/cb O2 patched >/dev/null 2>&1 || { echo "RESULT: FAIL c build"; exit 0; }
IS=$(awk '$2=="init_params.bin"{print $1}' $P/inputs/SHA256SUMS); BS=$(awk '$2=="batch_order.bin"{print $1}' $P/inputs/SHA256SUMS)
RUST="$P/bin/rust2a-gnu-O3 $L/o_r --init $P/inputs/init_params.bin --init-sha $IS --batch $P/inputs/batch_order.bin --batch-sha $BS"
CC="$L/cb/cap1c_patched $L/o_c"
EV=cycles,instructions,branches,branch-misses,cache-misses
for r in 1 2 3; do
 for a in C R; do
  [ $a = C ] && cmd=$CC || cmd=$RUST
  perf stat -x, -e $EV -o stat_$a$r.txt $cmd >/dev/null 2>err_$a$r.txt; echo "STAT $a$r $(grep TRAIN_WALL err_$a$r.txt) $(awk -F, '{printf "%s=%s ", $3,$1}' stat_$a$r.txt | tr -d '\n')"
 done
done
for a in C R; do
  [ $a = C ] && cmd=$CC || cmd=$RUST
  perf record -F 20000 -o rec_$a.data $cmd >/dev/null 2>rec_err_$a.txt; echo "REC $a rc=$? $(grep TRAIN_WALL rec_err_$a.txt)"
  perf report -i rec_$a.data --stdio --sort symbol 2>/dev/null | head -40 > rep_$a.txt
  perf script -i rec_$a.data -F ip 2>/dev/null | sort | uniq -c | sort -rn | head -400 > ips_$a.txt
done
cp $P/bin/rust2a-gnu-O3 $L/rust2a-gnu-O3.bin; cp $L/cb/cap1c_patched $L/cap1c_patched.bin; rm -rf $L/o_r $L/o_c
echo "RESULT: OK diag1 perf stat 3x2 + record 2 (diagnostic, no label)" | tee RESULT.txt
