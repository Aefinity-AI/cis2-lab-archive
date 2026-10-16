#!/usr/bin/env bash
set -u
NAME=cis2-batch-w2; SM=none
LEG_OUT="${LEG_OUT:-$HOME/legs/$NAME}"; mkdir -p "$LEG_OUT"; R="$LEG_OUT/RESULT.txt"
ts() { date -u +%FT%TZ; }; say() { printf "%s\n" "$*" >> "$R"; }
say "=== $NAME start $(ts) host=$(hostname) cpu=$(lscpu | grep -m1 'Model name' | sed 's/.*: *//') flags=$(grep -o -w 'avx2\|avx512f\|sse4_2\|fma' /proc/cpuinfo | sort -u | tr '\n' ',')"
D="$HOME/cis2-batch"; cd "$D" || { say "RESULT: FAIL $NAME no payload"; exit 1; }
bad=0
chk() { a=$(sha256sum "$1" | cut -c1-64); say "sha256 $2 = $a"; [ "$a" = "$3" ] || { bad=$((bad+1)); say "  ^ FAILED: $2 differs from pin"; }; }
chk weights/model.safetensors model.safetensors 80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1
chk ids/smollm2-16.txt ids16 4b6618b64fe0fd9c261dd30789ec69a4f84c05114820df9e45c4d2c8fac40faf
say "ids/pset4.txt sha256 = $(sha256sum ids/pset4.txt | cut -c1-64)"
say "sources sha256: $(cat gpu/cis2_host.cpp gpu/cis2_math.h gpu/cis2_model.h gpu/cis2_fpenv.h gpu/cis2_sha256.h gpu/cis2_consts.inc | sha256sum | cut -c1-16) (cat of host.cpp math.h model.h fpenv.h sha256.h consts.inc)"
say "g++ $(g++ --version | head -1); nvcc $(command -v nvcc >/dev/null && nvcc --version | tail -1 || echo none); nvidia-smi: $(command -v nvidia-smi >/dev/null && nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>&1 | head -1 || echo none)"
EXP16=d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df
BATCHES="1 2 4 8"
GF="-std=c++17 -O2 -ffp-contract=off -fexcess-precision=standard -fno-fast-math -I gpu"
build() { say "build $1: $2"; eval "$2" > "$LEG_OUT/build-$1.log" 2>&1 || { say "  ^ build $1 FAILED rc=$? (see build-$1.log)"; return 1; }; }
dg_of() { grep "^CIS2_REF.*batch_idx=$2 " "$1" | sed 's/.*digest=\([0-9a-f]*\).*/\1/'; }
# batch ladder: same prompt replicated B times; every row digest must equal the
# same build's batch-1 digest. Sets LADDER (tokens) and bumps bad on DIFF/failure.
ladder() { # bin label
  LADDER=""; local base=""
  for B in $BATCHES; do
    out="$LEG_OUT/$2-b$B.out"; s=$(date +%s)
    "$1" --weights-dir weights --ids ids/smollm2-16.txt --gen-toks 16 --batch $B > "$out" 2> "$LEG_OUT/$2-b$B.err"; rc=$?; e=$(date +%s)
    d0=$(dg_of "$out" 0); same=1; alld=""
    for ((r=0;r<B;r++)); do dr=$(dg_of "$out" $r); alld="$alld ${dr:0:12}"; [ -n "$dr" ] && [ "$dr" = "$d0" ] || same=0; done
    if [ $B = 1 ]; then base="$d0"; [ "$d0" = "$EXP16" ] && v=MATCH || v=MISMATCH
    else [ "$d0" = "$base" ] && [ -n "$d0" ] && [ $same = 1 ] && v=SAME || v=DIFF; fi
    [ $rc = 0 ] || v=FAIL
    say "row $2 batch=$B digest0=${d0:-none} rows_equal=$same rows=[${alld# }] $v rc=$rc wall_s=$((e-s))"
    LADDER="$LADDER $3_b$B=$v"
    case $v in MISMATCH|DIFF|FAIL) bad=$((bad+1));; esac
  done
}
# prompt-set check: batch=4 with 4 distinct prompts; each row digest must equal
# that prompt's solo (batch=1, --ids-set restricted to its own line) digest.
pset() { # bin label prefix
  PSET=""; local ok=0 pf="$LEG_OUT/$2-pset.out" s e
  s=$(date +%s)
  "$1" --weights-dir weights --ids-set ids/pset4.txt --gen-toks 16 --batch 4 > "$pf" 2> "$LEG_OUT/$2-pset.err"; local rc=$?
  for r in 0 1 2 3; do
    sed -n "$((r+1))p" ids/pset4.txt > "$LEG_OUT/$2-solo$r.ids"
    "$1" --weights-dir weights --ids "$LEG_OUT/$2-solo$r.ids" --gen-toks 16 --batch 1 > "$LEG_OUT/$2-solo$r.out" 2> "$LEG_OUT/$2-solo$r.err"
    ds=$(dg_of "$LEG_OUT/$2-solo$r.out" 0); db=$(dg_of "$pf" $r)
    [ -n "$ds" ] && [ "$ds" = "$db" ] && ok=$((ok+1))
    say "pset $2 row=$r solo=${ds:-none} batch4=${db:-none}"
  done
  # sanity: rows must be pairwise distinct (otherwise the test proves nothing)
  nd=$(for r in 0 1 2 3; do dg_of "$pf" $r; done | sort -u | wc -l)
  e=$(date +%s); say "pset $2 ok=$ok/4 distinct_rows=$nd rc=$rc wall_s=$((e-s))"
  PSET=" $3_pset=$ok/4"
  [ $ok = 4 ] && [ $nd = 4 ] && [ $rc = 0 ] || bad=$((bad+1))
}
RES=""
if build host-gcc "g++ $GF -o cis2_batch_host gpu/cis2_host.cpp"; then
  ladder ./cis2_batch_host host host; RES="$RES$LADDER"
  pset ./cis2_batch_host host host; RES="$RES$PSET"
else bad=$((bad+1)); fi
rm -f cis2_batch_host cis2_batch_cuda
if [ $bad -eq 0 ]; then say "RESULT: OK $NAME$RES weights=80521b40 ids=4b6618b6"; else say "RESULT: FAIL $NAME$RES (bad=$bad; see FAILED/DIFF/MISMATCH lines)"; fi
say "=== $NAME done $(ts)"; [ $bad -eq 0 ]
