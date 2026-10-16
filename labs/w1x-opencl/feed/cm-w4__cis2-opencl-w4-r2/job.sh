#!/usr/bin/env bash
# cis2-opencl: CIS-2 OpenCL backend vs pinned digests (SmolLM2-135M). Placeholders: cis2-opencl-w4-r2 none 16 128
# (none unused, kept for template compatibility). TOKS rows (e.g. "128") are pinned below.
# Payload: $HOME/cis2-opencl (gpu/, weights, ids). iGPU needs RUSTICL_ENABLE=iris.
set -u
NAME=cis2-opencl-w4-r2; SM=none; TOKS="16 128"
LEG_OUT="${LEG_OUT:-$HOME/legs/$NAME}"; mkdir -p "$LEG_OUT"; R="$LEG_OUT/RESULT.txt"
ts() { date -u +%FT%TZ; }; say() { printf "%s\n" "$*" >> "$R"; }
say "=== $NAME start $(ts) host=$(hostname) cpu=$(lscpu | grep -m1 'Model name' | sed 's/.*: *//')"
D="$HOME/cis2-opencl"; cd "$D" || { say "RESULT: FAIL $NAME no payload"; exit 1; }
bad=0
chk() { a=$(sha256sum "$1" | cut -c1-64); say "sha256 $2 = $a"; [ "$a" = "$3" ] || { bad=$((bad+1)); say "  ^ FAILED: $2 differs from pin"; }; }
chk weights/model.safetensors model.safetensors 80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1
chk ids/smollm2-16.txt ids16 4b6618b64fe0fd9c261dd30789ec69a4f84c05114820df9e45c4d2c8fac40faf
say "g++ $(g++ --version | head -1)"
EXP16=d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df
EXP128=22f69ad87a615d66a77efaca8b1172d22bdfb4bd5092ceffd302e35669a050f6
GF="-std=c++17 -O2 -ffp-contract=off -fexcess-precision=standard -fno-fast-math -I gpu"
build() { say "build $1: $2"; eval "$2" > "$LEG_OUT/build-$1.log" 2>&1 || { say "  ^ build $1 FAILED rc=$? (see build-$1.log)"; return 1; }; }
run() { # label toks expected bin [extra args...]
  lab=$1; t=$2; exp=$3; bin=$4; shift 4
  out="$LEG_OUT/$lab-$t.out"
  nice -n 10 "$bin" --weights-dir weights --ids ids/smollm2-16.txt --gen-toks "$t" "$@" > "$out" 2> "$LEG_OUT/$lab-$t.err"; rc=$?
  dg=$(grep '^CIS2_REF' "$out" | grep sequential | sed 's/.*digest=\([0-9a-f]*\).*/\1/')
  if [ "$dg" = "$exp" ]; then v=MATCH; elif [ -z "$dg" ]; then v=NORUN; else v=DIVERGE; fi
  say "row $lab gen_toks=$t digest=${dg:-none} expected=${exp:0:16} $v rc=$rc"; echo "$v"
}
exp_for() { case "$1" in 16) echo $EXP16;; 128) echo $EXP128;; *) echo none;; esac; }
RES=""
rows() { # key label bin args...  (runs 16 then TOKS)
  key=$1; lab=$2; bin=$3; shift 3
  RES="$RES ${key}16=$(run $lab 16 $EXP16 $bin "$@")"
  for t in $TOKS; do RES="$RES ${key}$t=$(run $lab "$t" "$(exp_for "$t")" $bin "$@")"; done
}
if build host-gcc "g++ $GF -o cis2_host_gcc_o gpu/cis2_host.cpp"; then
  rows host host-gcc ./cis2_host_gcc_o
else bad=$((bad+1)); fi
if build opencl "make -C gpu opencl opencl-soft test_soft"; then
  LIST=$(RUSTICL_ENABLE=iris gpu/cis2_opencl --cl-list 2>&1); say "clinfo: $(echo "$LIST" | tr '\n' '|')"
  tsoft() { # label platform device  (unit test of the software routines on that device; 0 mismatches required)
    o="$LEG_OUT/test_soft-$1.log"; RUSTICL_ENABLE=iris nice -n 10 gpu/test_soft --n 1 --cl-platform "$2" --cl-device "$3" > "$o" 2>&1; rc=$?
    v=$(grep -oE 'test_soft RESULT: [A-Z]+' "$o" | awk '{print $3}' | tail -1); say "test_soft $1 rc=$rc result=${v:-none}"
    [ $rc -eq 0 ] && [ "$v" = PASS ] && echo PASS || echo FAIL
  }
  case "$LIST" in *Portable*)
    rows pocl pocl gpu/cis2_opencl --cl-platform Portable --cl-device cpu
    rows pocl_soft pocl_soft gpu/cis2_opencl_soft --cl-platform Portable --cl-device cpu
    RES="$RES pocl_test=$(tsoft pocl Portable cpu)";; esac
  case "$LIST" in *NVIDIA*)
    rows nvcl nvcl gpu/cis2_opencl --cl-platform NVIDIA --cl-device NVIDIA
    RES="$RES nvcl_test=$(tsoft nvcl NVIDIA NVIDIA)";; esac
  case "$LIST" in *rusticl*)
    export RUSTICL_ENABLE=iris
    rows igpu_soft igpu_soft gpu/cis2_opencl_soft --cl-platform rusticl --cl-device HD
    RES="$RES igpu_test=$(tsoft igpu rusticl HD)"
    # informational negative control (iGPU hardware divide/sqrt is expected to DIVERGE; not counted)
    ctl=$(run igpu_hw 16 $EXP16 gpu/cis2_opencl --cl-platform rusticl --cl-device HD)
    say "control igpu_hw16=$ctl (DIVERGE expected)"
    unset RUSTICL_ENABLE;; esac
  case "$RES" in *pocl16*|*nvcl16*|*igpu_soft16*) ;; *) say "no OpenCL device rows ran"; bad=$((bad+1));; esac
else bad=$((bad+1)); fi
rm -f cis2_host_gcc_o
case "$RES" in *DIVERGE*|*NORUN*|*FAIL*) bad=$((bad+1));; esac
if [ $bad -eq 0 ]; then say "RESULT: OK $NAME$RES weights=80521b40 ids=4b6618b6"; else say "RESULT: FAIL $NAME$RES (bad=$bad)"; fi
say "=== $NAME done $(ts)"; [ $bad -eq 0 ]
