#!/usr/bin/env bash
# cis2-sample: seeded-sampling clause (DRAFT v0 §14) on SmolLM2-135M, C++ port, pinned flags.
# Checks: greedy 16-tok digest MATCH (byte-identical greedy path) + sampled 16/64-tok digests
# (seed=1 T=0.8 K=40 P=0.95; CANDIDATE, cross-host agreement is the result) + host==CUDA when SM != none.
# Payload: $HOME/cis2-sample/{gpu,weights,ids}. SM=none|sm_61.
set -u
NAME=cis2-sample-w4; SM=none
LEG_OUT="${LEG_OUT:-$HOME/legs/$NAME}"; mkdir -p "$LEG_OUT"; R="$LEG_OUT/RESULT.txt"
ts() { date -u +%FT%TZ; }; say() { printf "%s\n" "$*" >> "$R"; }
say "=== $NAME start $(ts) host=$(hostname) cpu=$(lscpu | grep -m1 'Model name' | sed 's/.*: *//') flags=$(grep -o -w 'avx2\|avx512f\|sse4_2\|fma' /proc/cpuinfo | sort -u | tr '\n' ',')"
D="${PAYLOAD:-$HOME/cis2-sample}"; cd "$D" || { say "RESULT: FAIL $NAME no payload"; exit 1; }
bad=0
chk() { a=$(sha256sum "$1" | cut -c1-64); say "sha256 $2 = $a"; [ "$a" = "$3" ] || { bad=$((bad+1)); say "  ^ FAILED: $2 differs from pin"; }; }
chk weights/model.safetensors model.safetensors 80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1
chk ids/smollm2-16.txt ids16 4b6618b64fe0fd9c261dd30789ec69a4f84c05114820df9e45c4d2c8fac40faf
say "sources sha256: $(cat gpu/cis2_host.cpp gpu/cis2_math.h gpu/cis2_model.h gpu/cis2_fpenv.h gpu/cis2_sha256.h gpu/cis2_consts.inc gpu/cis2_sample.h | sha256sum | cut -c1-16)"
say "g++ $(g++ --version | head -1); nvcc $(command -v nvcc >/dev/null && nvcc --version | tail -1 || echo none)"
EXP16=d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df
SAMPLE="1,0.8,40,0.95"
GF="-std=c++17 -O2 -ffp-contract=off -fexcess-precision=standard -fno-fast-math -I gpu"
build() { say "build $1: $2"; eval "$2" > "$LEG_OUT/build-$1.log" 2>&1 || { say "  ^ build $1 FAILED rc=$? (see build-$1.log)"; return 1; }; }
dg_of() { grep '^CIS2_REF' "$1" | grep sequential | sed 's/.*digest=\([0-9a-f]*\).*/\1/'; }
run() { # bin label toks [sample]
  out="$LEG_OUT/$2-$3${4:+-s}.out"
  if [ -n "${4:-}" ]; then "$1" --weights-dir weights --ids ids/smollm2-16.txt --gen-toks "$3" --sample "$4" > "$out" 2> "$LEG_OUT/$2-$3-s.err"
  else "$1" --weights-dir weights --ids ids/smollm2-16.txt --gen-toks "$3" > "$out" 2> "$LEG_OUT/$2-$3.err"; fi
}
ids_sha() { grep '^step ' "$1" | sed 's/.*next_id=//' | paste -sd, | tr -d '\n' | sha256sum | cut -c1-64; }
declare -A S16 S64 IDS G16
leg() { # label bin
  run "$2" "$1" 16; G16[$1]=$(dg_of "$LEG_OUT/$1-16.out")
  if [ "${G16[$1]}" = "$EXP16" ]; then v=MATCH; else v=MISMATCH; bad=$((bad+1)); fi
  say "row $1 greedy16 digest=${G16[$1]:-none} expected=${EXP16:0:16} $v"
  run "$2" "$1" 16 "$SAMPLE"; S16[$1]=$(dg_of "$LEG_OUT/$1-16-s.out"); IDS[$1]=$(ids_sha "$LEG_OUT/$1-16-s.out")
  run "$2" "$1" 64 "$SAMPLE"; S64[$1]=$(dg_of "$LEG_OUT/$1-64-s.out")
  say "row $1 sample16 digest=${S16[$1]:-none} ids16sha=${IDS[$1]} CANDIDATE"
  say "row $1 sample64 digest=${S64[$1]:-none} CANDIDATE"
  [ -n "${S16[$1]}" ] && [ -n "${S64[$1]}" ] || bad=$((bad+1))
}
G=none
if build host-gcc "g++ $GF -o cis2_host_gcc_h gpu/cis2_host.cpp"; then leg host ./cis2_host_gcc_h; else bad=$((bad+1)); fi
if [ "$SM" != none ] && command -v nvcc >/dev/null; then
  NV="nvcc -x cu -std=c++17 -O2 -fmad=false -ftz=true -prec-div=true -prec-sqrt=true --extended-lambda -DCIS2_CUDA_FTZ=1 -arch=$SM -I gpu"
  if build cuda "$NV -o cis2_cuda_h gpu/cis2_host.cpp"; then
    leg cuda ./cis2_cuda_h
    if [ "${S16[host]:-x}" = "${S16[cuda]:-y}" ] && [ "${S64[host]:-x}" = "${S64[cuda]:-y}" ] && [ "${IDS[host]:-x}" = "${IDS[cuda]:-y}" ]; then G=MATCH; else G=MISMATCH; bad=$((bad+1)); fi
    say "host-vs-cuda sampled: $G"
  else bad=$((bad+1)); fi
fi
rm -f cis2_host_gcc_h cis2_cuda_h
if [ $bad -eq 0 ]; then say "RESULT: OK $NAME greedy16=MATCH s16=${S16[host]} s64=${S64[host]} ids16=${IDS[host]} hostcuda=$G weights=80521b40 ids=4b6618b6"; else say "RESULT: FAIL $NAME greedy16=${G16[host]:-none} s16=${S16[host]:-none} s64=${S64[host]:-none} ids16=${IDS[host]:-none} hostcuda=$G (bad=$bad)"; fi
say "=== $NAME done $(ts)"; [ $bad -eq 0 ]
