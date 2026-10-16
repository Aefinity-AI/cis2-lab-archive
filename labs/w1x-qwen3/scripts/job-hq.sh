#!/usr/bin/env bash
# w1x-qwen3: CIS-2 model breadth, Qwen/Qwen3-0.6B (Apache-2.0), C++ port, spec flags, bf16 on disk / fp32 compute.
# TEMPLATE: NAME and SM below are stamped per host by queue.sh into job-<host>.sh (feed runs one script per host).
# Rows: host-gcc 16 and 128 gen_toks, each run TWICE (repeat); CUDA rows only when SM != none and nvcc is present (hq).
# Digest pins: none (CANDIDATE); the result is cross-host agreement (cm-compare / analyse by PREREG sec 5). No timing numbers are reported as results.
set -u
NAME=cis2-qwen3-hq; SM=sm_61
LEG_OUT="${LEG_OUT:-$HOME/legs/$NAME}"; mkdir -p "$LEG_OUT"; R="$LEG_OUT/RESULT.txt"
ts() { date -u +%FT%TZ; }; say() { printf "%s\n" "$*" >> "$R"; }
say "=== $NAME start $(ts) host=$(hostname) cpu=$(lscpu | grep -m1 'Model name' | sed 's/.*: *//') flags=$(grep -o -w 'avx2\|avx512f\|sse4_2\|fma' /proc/cpuinfo | sort -u | tr '\n' ',')"
D="$HOME/cis2-qwen3"; cd "$D" || { say "RESULT: FAIL $NAME no payload"; exit 1; }
bad=0; IDS=$(sha256sum ids/qwen3-16.txt | cut -c1-64)
chk() { a=$(sha256sum "$1" | cut -c1-64); say "sha256 $2 = $a"; [ "$a" = "$3" ] || { bad=$((bad+1)); say "  ^ FAILED: $2 differs from pin"; }; }
chk weights/model.safetensors model.safetensors f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b
chk weights/config.json config.json 660db3b73d788119c04535e48cf9be5f55bc3100841a718637ae695b442f27dd
chk weights/tokenizer.json tokenizer.json aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4
chk ids/qwen3-16.txt ids16 53ea8e67a213a84677328896d6dea41ef3841b65028cfb85b3ba844e275f5cd7
say "source: Qwen/Qwen3-0.6B revision c1899de289a04d12100db370d81485cdf75e47ca licence apache-2.0 (card + LICENSE read at download)"
say "sources sha256: $(cat gpu/cis2_host.cpp gpu/cis2_math.h gpu/cis2_model.h gpu/cis2_fpenv.h gpu/cis2_sha256.h gpu/cis2_consts.inc | sha256sum | cut -c1-16) (cat of host.cpp math.h model.h fpenv.h sha256.h consts.inc)"
say "g++ $(g++ --version | head -1); nvcc $(command -v nvcc >/dev/null && nvcc --version | tail -1 || echo none); nvidia-smi: $(command -v nvidia-smi >/dev/null && nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>&1 | head -1 || echo none)"
say "mem: $(grep -E 'MemTotal|MemAvailable' /proc/meminfo | tr -s ' ' | tr '\n' ' ')"
GF="-std=c++17 -O2 -ffp-contract=off -fexcess-precision=standard -fno-fast-math -I gpu"
build() { say "build $1: $2"; eval "$2" > "$LEG_OUT/build-$1.log" 2>&1 || { say "  ^ build $1 FAILED rc=$? (see build-$1.log)"; return 1; }; }
TIME=""; [ -x /usr/bin/time ] && TIME="/usr/bin/time -v"
MAXRSS=0
run() { # bin label toks tag: runs in the PARENT shell (no $()), writes <label>-<toks>-<tag>.digest, records row + peak RSS
  out="$LEG_OUT/$2-$3-$4.out"; s=$(date +%s)
  $TIME "$1" --weights-dir weights --ids ids/qwen3-16.txt --gen-toks "$3" > "$out" 2> "$LEG_OUT/$2-$3-$4.err"; rc=$?; e=$(date +%s)
  dg=$(grep '^CIS2_REF' "$out" | sed 's/.*digest=\([0-9a-f]*\).*/\1/'); echo "${dg:-none}" > "$LEG_OUT/$2-$3-$4.digest"
  rss=$(grep 'Maximum resident' "$LEG_OUT/$2-$3-$4.err" | awk '{print $NF}'); rss=${rss:-0}; [ "$rss" -gt "$MAXRSS" ] && MAXRSS=$rss
  say "row $2 gen_toks=$3 run=$4 digest=${dg:-none} CANDIDATE rc=$rc wall_s=$((e-s)) maxrss_kb=$rss"
  [ $rc -eq 0 ] || bad=$((bad+1))
}
declare -A DG
pair() { # bin label: 16 and 128, two runs each
  for t in 16 128; do
    run "$1" "$2" $t 1; run "$1" "$2" $t 2
    a=$(cat "$LEG_OUT/$2-$t-1.digest"); b=$(cat "$LEG_OUT/$2-$t-2.digest"); DG[$2-$t]=$a
    if [ "$a" = "$b" ] && [ "$a" != none ]; then say "repeat $2 gen_toks=$t SAME"; else bad=$((bad+1)); say "repeat $2 gen_toks=$t DIFFERENT ($a vs $b)"; fi
  done
}
if build host-gcc "g++ $GF -o cis2_host_gcc gpu/cis2_host.cpp"; then pair ./cis2_host_gcc host-gcc; else bad=$((bad+1)); fi
if [ "$SM" != none ] && command -v nvcc >/dev/null; then
  NV="nvcc -x cu -std=c++17 -O2 -fmad=false -ftz=true -prec-div=true -prec-sqrt=true --extended-lambda -DCIS2_CUDA_FTZ=1 -arch=$SM -I gpu"
  if build cuda "$NV -o cis2_cuda gpu/cis2_host.cpp"; then
    pair ./cis2_cuda cuda-$SM
    for t in 16 128; do
      if [ "${DG[cuda-$SM-$t]}" = "${DG[host-gcc-$t]}" ]; then say "cuda==host gen_toks=$t SAME"; else bad=$((bad+1)); say "cuda==host gen_toks=$t DIFFERENT"; fi
    done
  else bad=$((bad+1)); fi
fi
rm -f cis2_host_gcc cis2_cuda
if [ $bad -eq 0 ]; then say "RESULT: OK $NAME d16=${DG[host-gcc-16]} d128=${DG[host-gcc-128]} repeat=SAME maxrss_kb=$MAXRSS weights=f47f7117 ids=${IDS:0:8}"; else say "RESULT: FAIL $NAME d16=${DG[host-gcc-16]:-none} d128=${DG[host-gcc-128]:-none} (bad=$bad; see FAILED/DIFFERENT lines) maxrss_kb=$MAXRSS"; fi
say "=== $NAME done $(ts)"; [ $bad -eq 0 ]
