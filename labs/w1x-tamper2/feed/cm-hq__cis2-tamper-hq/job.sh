#!/usr/bin/env bash
# cis2-tamper v2: real-weight tamper detection on the actual SmolLM2-135M safetensors.
# Each mutant is a fresh copy of the pinned weights with one change; the C++ port (pinned
# flags) greedy-decodes 16 tokens. Three detection levels are recorded per trial:
#   sha     - sha256 of the mutated file moved (trivial: any byte change)
#   witness - the CIS-2 §12.1 witness moved. The witness header folds weights_sha256, so it
#             moves for ANY file change; this is the artifact-binding property, not a compute test.
#   body    - the witness BODY (per-step full fp32 logits + argmax ids, header excluded) moved:
#             the forward pass itself changed bits somewhere in the logits.
#   argmax  - the greedy token sequence moved (the user-visible output changed).
# Classes: bitflip (one random bit in tensor data), ulp1 (one element +1 bf16 ULP),
# int8 (one whole tensor INT8 round-tripped, per-tensor absmax),
# meta (header padding byte only; control: sha + witness MUST move, body + argmax MUST NOT).
# base = unmutated weights: witness must equal the pinned CIS2_REF, body/argmax are the references.
set -u
NAME=cis2-tamper-hq; SEED=20261018; N_BITFLIP=${N_BITFLIP:-24}; N_ULP=${N_ULP:-24}; N_INT8=${N_INT8:-6}
LEG_OUT="${LEG_OUT:-$HOME/legs/$NAME}"; mkdir -p "$LEG_OUT"; R="$LEG_OUT/RESULT.txt"
ts() { date -u +%FT%TZ; }; say() { printf "%s\n" "$*" >> "$R"; }
say "=== $NAME start $(ts) host=$(hostname) cpu=$(lscpu | grep -m1 'Model name' | sed 's/.*: *//') flags=$(grep -o -w 'avx2\|sse4_2\|fma' /proc/cpuinfo | sort -u | tr '\n' ',') seed=$SEED template=v2"
D="$HOME/cis2-digest"; cd "$D" || { say "RESULT: FAIL $NAME no payload"; exit 1; }
EXP16=d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df
W=weights/model.safetensors
a=$(sha256sum $W | cut -c1-64); say "sha256 model.safetensors = $a"
[ "$a" = 80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1 ] || { say "RESULT: FAIL $NAME weights not pinned"; exit 1; }
say "sources sha256 (payload gpu/): $(cat gpu/cis2_host.cpp gpu/cis2_math.h gpu/cis2_model.h gpu/cis2_fpenv.h gpu/cis2_sha256.h gpu/cis2_consts.inc | sha256sum | cut -c1-16); g++ $(g++ --version | head -1)"
# Patched copy of the port: adds one printed line, run1_body_digest (witness minus its header).
# The CIS2_REF line and every other output are untouched; the base trial proves it (MATCH).
GT="$LEG_OUT/gpu_t"; rm -rf "$GT"; cp -r gpu "$GT"
python3 -I - "$GT/cis2_host.cpp" <<'PY' || { say "RESULT: FAIL $NAME patch"; exit 1; }
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)
rep("  Cis2Sha256 witness;\n", "  Cis2Sha256 witness;\n  Cis2Sha256 body;  // tamper leg: witness body only (no header)\n")
rep("    witness.update_u32le(next_id);\n",
    "    witness.update_u32le(next_id);\n"
    "    for (int i = 0; i < model.vocab; ++i) body.update_u32le(cis2_f32_bits(logits_host[(size_t)i]));\n"
    "    body.update_u32le(next_id);\n")
rep('  printf("prompt_idx=%d run1_argmax_digest=%s\\n", prompt_idx, cis2_hex(adig, 32).c_str());\n',
    '  printf("prompt_idx=%d run1_argmax_digest=%s\\n", prompt_idx, cis2_hex(adig, 32).c_str());\n'
    '  { unsigned char bd[32]; body.finalize(bd); printf("prompt_idx=%d run1_body_digest=%s\\n", prompt_idx, cis2_hex(bd, 32).c_str()); }\n')
open(p, "w").write(s)
PY
say "sources sha256 (patched gpu_t/): $(cat $GT/cis2_host.cpp $GT/cis2_math.h $GT/cis2_model.h $GT/cis2_fpenv.h $GT/cis2_sha256.h $GT/cis2_consts.inc | sha256sum | cut -c1-16)"
GF="-std=c++17 -O2 -ffp-contract=off -fexcess-precision=standard -fno-fast-math -I $GT"
g++ $GF -o "$LEG_OUT/cis2_host_t" "$GT/cis2_host.cpp" > "$LEG_OUT/build.log" 2>&1 || { say "RESULT: FAIL $NAME build"; exit 1; }
MUT="$LEG_OUT/mut"; mkdir -p "$MUT/weights"; cp weights/config.json weights/tokenizer.json "$MUT/weights/"
cat > "$LEG_OUT/mutate.py" <<'PY'
import sys, json, struct, random, shutil
src, dst, cls, idx, seed = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
rnd = random.Random(seed * 1000003 + idx * 7919 + sum(cls.encode()))
with open(src, 'rb') as f:
    n = struct.unpack('<Q', f.read(8))[0]; hdr_raw = f.read(n)
hdr = json.loads(hdr_raw); base = 8 + n
tensors = [(k, v) for k, v in hdr.items() if k != '__metadata__']
assert all(v['dtype'] == 'BF16' for _, v in tensors)
shutil.copyfile(src, dst)
def bf16_bits(buf, off): return struct.unpack('<H', buf[off:off+2])[0]
with open(dst, 'r+b') as f:
    if cls == 'base':
        print('base unmutated copy'); sys.exit(0)
    if cls == 'meta':
        # same-length header edit: turn the last padding space into a tab (still JSON whitespace)
        # or, failing that, flip "format":"pt" -> "px". Byte count unchanged, data offsets unchanged.
        i = hdr_raw.rfind(b' ')
        if i >= 0 and hdr_raw[i:].strip() == b'':
            f.seek(8 + i); f.write(b'\t'); print('meta pad-space->tab at header byte %d' % i)
        elif b'"format":"pt"' in hdr_raw:
            j = hdr_raw.index(b'"format":"pt"') + len(b'"format":"p'); f.seek(8 + j); f.write(b'x'); print('meta format pt->px')
        else:
            print('meta SKIP no-same-length-edit'); sys.exit(3)
        sys.exit(0)
    name, t = tensors[rnd.randrange(len(tensors))]
    s, e = t['data_offsets']; nel = (e - s) // 2
    if cls == 'bitflip':
        el = rnd.randrange(nel); bit = rnd.randrange(16); off = base + s + 2 * el
        f.seek(off); old = bf16_bits(f.read(2), 0); new = old ^ (1 << bit)
        f.seek(off); f.write(struct.pack('<H', new))
        kind = 'sign' if bit == 15 else ('exp' if bit >= 7 else 'mant%d' % bit)
        print('bitflip tensor=%s elem=%d bit=%d kind=%s old=%04x new=%04x' % (name, el, bit, kind, old, new))
    elif cls == 'ulp1':
        el = rnd.randrange(nel); off = base + s + 2 * el
        f.seek(off); old = bf16_bits(f.read(2), 0)
        mant = old & 0x7fff; new = (old & 0x8000) | ((mant + 1) & 0x7fff) if mant < 0x7f7f else (old ^ 1)
        f.seek(off); f.write(struct.pack('<H', new))
        print('ulp1 tensor=%s elem=%d old=%04x new=%04x' % (name, el, old, new))
    elif cls == 'int8':
        big = sorted(tensors, key=lambda kv: -(kv[1]['data_offsets'][1] - kv[1]['data_offsets'][0]))
        cand = [kv for kv in big if 'proj' in kv[0] or 'embed' in kv[0]]
        name, t = cand[idx % len(cand)]; s, e = t['data_offsets']; nel = (e - s) // 2
        f.seek(base + s); raw = f.read(e - s)
        vals = struct.unpack('<%dH' % nel, raw)
        def b2f(b): return struct.unpack('<f', struct.pack('<I', b << 16))[0]
        def f2b(x):   # round-to-nearest-even fp32 -> bf16
            u = struct.unpack('<I', struct.pack('<f', x))[0]
            return ((u + 0x7fff + ((u >> 16) & 1)) >> 16) & 0xffff
        fl = [b2f(b) for b in vals]; amax = max(abs(v) for v in fl) or 1.0; scale = amax / 127.0
        q = [max(-127, min(127, int(round(v / scale)))) for v in fl]
        out = struct.pack('<%dH' % nel, *[f2b(qi * scale) for qi in q])
        changed = sum(1 for a, b in zip(raw[::2], out[::2]) if a != b)
        f.seek(base + s); f.write(out)
        print('int8 tensor=%s nel=%d amax=%.6g scale=%.6g changed_lo_bytes=%d' % (name, nel, amax, scale, changed))
PY
MW="$MUT/weights/model.safetensors"
BASE_BODY=""; BASE_ARGMAX=""; BASE_OK=no
trial() { # cls idx
  desc=$(python3 -I "$LEG_OUT/mutate.py" "$W" "$MW" "$1" "$2" "$SEED"); rc=$?
  [ $rc -eq 3 ] && { say "trial $1 #$2 $desc"; return; }
  sh=$(sha256sum "$MW" | cut -c1-16); smoved=$([ "$sh" = 80521b40281d6ce7 ] && echo no || echo yes)
  out="$LEG_OUT/$1-$2.out"
  "$LEG_OUT/cis2_host_t" --weights-dir "$MUT/weights" --ids ids/smollm2-16.txt --gen-toks 16 > "$out" 2> "$LEG_OUT/$1-$2.err"; rrc=$?
  dg=$(grep '^CIS2_REF' "$out" | grep sequential | sed 's/.*digest=\([0-9a-f]*\).*/\1/')
  bd=$(grep -m1 'run1_body_digest=' "$out" | sed 's/.*=//'); ad=$(grep -m1 'run1_argmax_digest=' "$out" | sed 's/.*=//')
  if [ "$1" = base ]; then
    BASE_BODY=$bd; BASE_ARGMAX=$ad; [ "$dg" = "$EXP16" ] && BASE_OK=yes
    say "trial base witness=${dg:-none} pinned=$([ "$BASE_OK" = yes ] && echo MATCH || echo MISMATCH) body=${bd:-none} argmax=${ad:-none} rc=$rrc"
    echo "base 0 no no no no $desc" >> "$LEG_OUT/trials.tsv"; return
  fi
  wmoved=$([ "$dg" = "$EXP16" ] && echo no || echo yes); [ -z "$dg" ] && wmoved=norun
  bmoved=$([ "$bd" = "$BASE_BODY" ] && echo no || echo yes); [ -z "$bd" ] && bmoved=norun
  amoved=$([ "$ad" = "$BASE_ARGMAX" ] && echo no || echo yes); [ -z "$ad" ] && amoved=norun
  say "trial $1 #$2 sha_moved=$smoved witness_moved=$wmoved body_moved=$bmoved argmax_moved=$amoved rc=$rrc $desc"
  echo "$1 $2 $smoved $wmoved $bmoved $amoved $desc" >> "$LEG_OUT/trials.tsv"
}
: > "$LEG_OUT/trials.tsv"
trial base 0
trial meta 0
for i in $(seq 1 $N_ULP); do trial ulp1 $i; done
for i in $(seq 1 $N_INT8); do trial int8 $((i-1)); done
for i in $(seq 1 $N_BITFLIP); do trial bitflip $i; done
rm -rf "$MUT" "$LEG_OUT/cis2_host_t" "$GT"
T="$LEG_OUT/trials.tsv"
cnt() { awk -v c="$1" -v col="$2" '$1==c{n++; if($col=="yes")d++} END{printf "%d/%d", d, n}' "$T"; }   # col: 3 sha 4 witness 5 body 6 argmax
tot=$(awk '$1!="base"' "$T" | wc -l); det_s=$(awk '$1!="base"&&$3=="yes"' "$T" | wc -l); det_w=$(awk '$1!="base"&&$4=="yes"' "$T" | wc -l)
det_b=$(awk '$1!="base"&&$1!="meta"&&$5=="yes"' "$T" | wc -l); det_a=$(awk '$1!="base"&&$1!="meta"&&$6=="yes"' "$T" | wc -l); nmut=$(awk '$1!="base"&&$1!="meta"' "$T" | wc -l)
bf_hi=$(grep '^bitflip ' "$T" | grep 'kind=\(sign\|exp\)' | awk '{n++; if($5=="yes")b++; if($6=="yes")a++} END{printf "body=%d/%d argmax=%d/%d", b, n, a, n}')
meta=$(awk '$1=="meta"{print "sha="$3" witness="$4" body="$5" argmax="$6}' "$T")
mp=$(awk '$1=="meta"{if($3=="yes"&&$4=="yes"&&$5=="no"&&$6=="no")print "PASS"; else print "FAIL"}' "$T"); [ -z "$mp" ] && mp=SKIP
ok=OK; [ "$BASE_OK" = yes ] || ok=FAIL; [ "$mp" = FAIL ] && ok=FAIL; grep -q norun "$T" && ok=FAIL
say "RESULT: $ok $NAME base=$([ "$BASE_OK" = yes ] && echo MATCH || echo MISMATCH) mutants=$nmut sha_detect=$det_s/$tot witness_detect=$det_w/$tot body_detect=$det_b/$nmut argmax_detect=$det_a/$nmut ulp1:body=$(cnt ulp1 5),argmax=$(cnt ulp1 6) int8:body=$(cnt int8 5),argmax=$(cnt int8 6) bitflip:body=$(cnt bitflip 5),argmax=$(cnt bitflip 6) bitflip_sign_exp:$bf_hi meta:$meta meta_control=$mp seed=$SEED template=v2"
say "=== $NAME done $(ts)"
[ "$ok" = OK ]
