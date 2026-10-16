#!/usr/bin/env bash
# cis2-horizon: long-horizon CIS-2 digests (SmolLM2-135M, C++ port, pinned flags).
# Rows for gen_toks in TOKS have no pinned value (CANDIDATE); cross-host agreement is the result.
# 16-token row is a MATCH sanity check against EXPECTED_DIGESTS.md.
set -u
NAME=cis2-horizon-w2; SM=none; TOKS="256 512 1024 2048"
LEG_OUT="${LEG_OUT:-$HOME/legs/$NAME}"; mkdir -p "$LEG_OUT"; R="$LEG_OUT/RESULT.txt"
ts() { date -u +%FT%TZ; }; say() { printf "%s\n" "$*" >> "$R"; }
say "=== $NAME start $(ts) host=$(hostname) cpu=$(lscpu | grep -m1 'Model name' | sed 's/.*: *//') flags=$(grep -o -w 'avx2\|avx512f\|sse4_2\|fma' /proc/cpuinfo | sort -u | tr '\n' ',')"
D="$HOME/cis2-digest"; cd "$D" || { say "RESULT: FAIL $NAME no payload"; exit 1; }
bad=0
chk() { a=$(sha256sum "$1" | cut -c1-64); say "sha256 $2 = $a"; [ "$a" = "$3" ] || { bad=$((bad+1)); say "  ^ FAILED: $2 differs from pin"; }; }
chk weights/model.safetensors model.safetensors 80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1
chk ids/smollm2-16.txt ids16 4b6618b64fe0fd9c261dd30789ec69a4f84c05114820df9e45c4d2c8fac40faf
say "sources sha256: $(cat gpu/cis2_host.cpp gpu/cis2_math.h gpu/cis2_model.h gpu/cis2_fpenv.h gpu/cis2_sha256.h gpu/cis2_consts.inc | sha256sum | cut -c1-16)"
say "g++ $(g++ --version | head -1); nvcc $(command -v nvcc >/dev/null && nvcc --version | tail -1 || echo none)"
EXP16=d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df
GF="-std=c++17 -O2 -ffp-contract=off -fexcess-precision=standard -fno-fast-math -I gpu"
build() { say "build $1: $2"; eval "$2" > "$LEG_OUT/build-$1.log" 2>&1 || { say "  ^ build $1 FAILED rc=$? (see build-$1.log)"; return 1; }; }
run() { # bin label toks expected
  out="$LEG_OUT/$2-$3.out"; s=$(date +%s)
  "$1" --weights-dir weights --ids ids/smollm2-16.txt --gen-toks "$3" > "$out" 2> "$LEG_OUT/$2-$3.err"; rc=$?; e=$(date +%s)
  dg=$(grep '^CIS2_REF' "$out" | grep sequential | sed 's/.*digest=\([0-9a-f]*\).*/\1/')
  if [ "$4" = none ]; then v=CANDIDATE; [ -z "$dg" ] && v=NORUN; elif [ "$dg" = "$4" ]; then v=MATCH; else v=MISMATCH; fi
  say "row $2 gen_toks=$3 digest=${dg:-none} expected=${4:0:16} $v rc=$rc wall_s=$((e-s))"; echo "$v"
}
RES=""
if build host-gcc "g++ $GF -o cis2_host_gcc_h gpu/cis2_host.cpp"; then
  RES="$RES host16=$(run ./cis2_host_gcc_h host-gcc 16 $EXP16)"
  for t in $TOKS; do RES="$RES host$t=$(run ./cis2_host_gcc_h host-gcc "$t" none)"; done
else bad=$((bad+1)); fi
if [ "$SM" != none ] && command -v nvcc >/dev/null; then
  NV="nvcc -x cu -std=c++17 -O2 -fmad=false -ftz=true -prec-div=true -prec-sqrt=true --extended-lambda -DCIS2_CUDA_FTZ=1 -arch=$SM -I gpu"
  if build cuda "$NV -o cis2_cuda_h gpu/cis2_host.cpp"; then
    RES="$RES cuda16=$(run ./cis2_cuda_h cuda-$SM 16 $EXP16)"
    for t in $TOKS; do RES="$RES cuda$t=$(run ./cis2_cuda_h cuda-$SM "$t" none)"; done
  else bad=$((bad+1)); fi
fi
rm -f cis2_host_gcc_h cis2_cuda_h
case "$RES" in *MISMATCH*|*NORUN*) bad=$((bad+1));; esac
if [ $bad -eq 0 ]; then say "RESULT: OK $NAME$RES weights=80521b40 ids=4b6618b6"; else say "RESULT: FAIL $NAME$RES (bad=$bad)"; fi
say "=== $NAME done $(ts)"; [ $bad -eq 0 ]
