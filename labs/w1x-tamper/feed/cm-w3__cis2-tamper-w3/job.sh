#!/usr/bin/env bash
# cis2-tamper: real-weight tamper detection (closes the moat-1 gap: mutate the actual
# SmolLM2-135M safetensors, not the receipt text). Each mutant is a fresh copy of the pinned
# weights with one change; the C++ port (pinned flags) decodes 16 tokens; we record whether the
# witness digest moved away from the pinned CIS2_REF and whether sha256 moved.
# Classes: bitflip (one random bit in tensor data), ulp1 (one element +1 bf16 ULP),
# int8 (one whole tensor INT8 round-tripped, per-tensor absmax), meta (header __metadata__ only;
# control: sha moves, witness must NOT move).
set -u
NAME=cis2-tamper-w3; SEED=20261016; N_BITFLIP=24; N_ULP=24; N_INT8=6
LEG_OUT="${LEG_OUT:-$HOME/legs/$NAME}"; mkdir -p "$LEG_OUT"; R="$LEG_OUT/RESULT.txt"
ts() { date -u +%FT%TZ; }; say() { printf "%s\n" "$*" >> "$R"; }
say "=== $NAME start $(ts) host=$(hostname) cpu=$(lscpu | grep -m1 'Model name' | sed 's/.*: *//') flags=$(grep -o -w 'avx2\|sse4_2\|fma' /proc/cpuinfo | sort -u | tr '\n' ',') seed=$SEED"
D="$HOME/cis2-digest"; cd "$D" || { say "RESULT: FAIL $NAME no payload"; exit 1; }
EXP16=d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df
W=weights/model.safetensors
a=$(sha256sum $W | cut -c1-64); say "sha256 model.safetensors = $a"
[ "$a" = 80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1 ] || { say "RESULT: FAIL $NAME weights not pinned"; exit 1; }
GF="-std=c++17 -O2 -ffp-contract=off -fexcess-precision=standard -fno-fast-math -I gpu"
say "sources sha256: $(cat gpu/cis2_host.cpp gpu/cis2_math.h gpu/cis2_model.h gpu/cis2_fpenv.h gpu/cis2_sha256.h gpu/cis2_consts.inc | sha256sum | cut -c1-16); g++ $(g++ --version | head -1)"
g++ $GF -o "$LEG_OUT/cis2_host_t" gpu/cis2_host.cpp > "$LEG_OUT/build.log" 2>&1 || { say "RESULT: FAIL $NAME build"; exit 1; }
MUT="$LEG_OUT/mut"; mkdir -p "$MUT/weights"; cp weights/config.json weights/tokenizer.json "$MUT/weights/"
# mutate.py: writes $MUT/weights/model.safetensors from $W with one mutation; prints a description line
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
        # pick among the largest tensors deterministically so the 6 picks are distinct projection matrices
        big = sorted(tensors, key=lambda kv: -(kv[1]['data_offsets'][1] - kv[1]['data_offsets'][0]))
        cand = [kv for kv in big if 'proj' in kv[0] or 'embed' in kv[0]]
        name, t = cand[idx % len(cand)]; s, e = t['data_offsets']; nel = (e - s) // 2
        f.seek(base + s); raw = f.read(e - s)
        vals = struct.unpack('<%dH' % nel, raw)
        import math
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
total=0; det_w=0; det_s=0
trial() { # cls idx
  desc=$(python3 -I "$LEG_OUT/mutate.py" "$W" "$MW" "$1" "$2" "$SEED"); rc=$?
  [ $rc -eq 3 ] && { say "trial $1 #$2 $desc"; return; }
  sh=$(sha256sum "$MW" | cut -c1-16); smoved=$([ "$sh" = 80521b40281d6ce7 ] && echo no || echo yes)
  out="$LEG_OUT/$1-$2.out"
  "$LEG_OUT/cis2_host_t" --weights-dir "$MUT/weights" --ids ids/smollm2-16.txt --gen-toks 16 > "$out" 2> "$LEG_OUT/$1-$2.err"; rrc=$?
  dg=$(grep '^CIS2_REF' "$out" | grep sequential | sed 's/.*digest=\([0-9a-f]*\).*/\1/')
  wmoved=$([ "$dg" = "$EXP16" ] && echo no || echo yes); [ -z "$dg" ] && wmoved=norun
  ids=$(grep -m1 -i 'generated\|token_ids' "$out" | cut -c1-120)
  say "trial $1 #$2 sha_moved=$smoved witness_moved=$wmoved rc=$rrc $desc"
  total=$((total+1)); [ "$smoved" = yes ] && det_s=$((det_s+1)); [ "$wmoved" = yes ] && det_w=$((det_w+1))
  echo "$1 $2 $smoved $wmoved $desc" >> "$LEG_OUT/trials.tsv"
}
: > "$LEG_OUT/trials.tsv"
trial meta 0
for i in $(seq 1 $N_ULP); do trial ulp1 $i; done
for i in $(seq 1 $N_INT8); do trial int8 $((i-1)); done
for i in $(seq 1 $N_BITFLIP); do trial bitflip $i; done
rm -rf "$MUT" "$LEG_OUT/cis2_host_t"
ulp_n=$(grep -c '^ulp1 ' "$LEG_OUT/trials.tsv"); ulp_d=$(awk '$1=="ulp1"&&$4=="yes"' "$LEG_OUT/trials.tsv" | wc -l)
int_n=$(grep -c '^int8 ' "$LEG_OUT/trials.tsv"); int_d=$(awk '$1=="int8"&&$4=="yes"' "$LEG_OUT/trials.tsv" | wc -l)
bf_n=$(grep -c '^bitflip ' "$LEG_OUT/trials.tsv"); bf_d=$(awk '$1=="bitflip"&&$4=="yes"' "$LEG_OUT/trials.tsv" | wc -l)
bf_hi_n=$(grep '^bitflip ' "$LEG_OUT/trials.tsv" | grep -c 'kind=\(sign\|exp\)'); bf_hi_d=$(grep '^bitflip ' "$LEG_OUT/trials.tsv" | grep 'kind=\(sign\|exp\)' | awk '$4=="yes"' | wc -l)
meta=$(awk '$1=="meta"{print "sha_moved="$3" witness_moved="$4}' "$LEG_OUT/trials.tsv")
say "RESULT: OK $NAME trials=$total sha_detect=$det_s/$total witness_detect=$det_w/$total ulp1=$ulp_d/$ulp_n int8=$int_d/$int_n bitflip=$bf_d/$bf_n bitflip_sign_exp=$bf_hi_d/$bf_hi_n meta:$meta seed=$SEED"
say "=== $NAME done $(ts)"
