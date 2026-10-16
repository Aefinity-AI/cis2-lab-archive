#!/usr/bin/env bash
# w6 build: applies the scoring-mode patch to a COPY of the engine sources and
# builds P (control), G (glibc expf), C (CORE-MATH cr_expf), plus Part A.
# Does not start any measurement except the control digest check.
#   env: W6_OUT   output dir            (default $HOME/legs/w6)
#        ENGINE   unpatched gpu/ dir    (default $HOME/cis2-digest/gpu)
#        COREMATH core-math checkout    (default $HOME/src/core-math)
#        WEIGHTS  dir with model.safetensors etc (default $HOME/cis2-digest/weights)
#        IDS      dir with smollm2-16.txt / -128.txt (default $HOME/cis2-digest/ids)
#        TOKS     "16" (default) or "16 128" for the control digest check
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${W6_OUT:-$HOME/legs/w6}"; ENGINE="${ENGINE:-$HOME/cis2-digest/gpu}"
CM="${COREMATH:-$HOME/src/core-math}"; WEIGHTS="${WEIGHTS:-$HOME/cis2-digest/weights}"
IDS="${IDS:-$HOME/cis2-digest/ids}"; TOKS="${TOKS:-16}"
mkdir -p "$OUT"; R="$OUT/BUILD.txt"; : > "$R"
say() { printf "%s\n" "$*" | tee -a "$R"; }
EXP16=d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df
EXP128=22f69ad87a615d66a77efaca8b1172d22bdfb4bd5092ceffd302e35669a050f6
GF="-std=c++17 -O2 -ffp-contract=off -fexcess-precision=standard -fno-fast-math"

# --- pins -----------------------------------------------------------------
say "pin core-math commit $(git -C "$CM" rev-parse HEAD)"
say "pin glibc $(ldd --version | head -1)"; say "pin g++ $(g++ --version | head -1); gcc $(gcc --version | head -1)"
say "pin patch sha256 $(sha256sum "$HERE/w6-scoring.patch" | cut -c1-64)"
say "pin engine base sha256 (host.cpp math.h model.h fpenv.h sha256.h consts.inc cat) $(cd "$ENGINE" && cat cis2_host.cpp cis2_math.h cis2_model.h cis2_fpenv.h cis2_sha256.h cis2_consts.inc | sha256sum | cut -c1-64)"
say "pin weights sha256 $(sha256sum "$WEIGHTS/model.safetensors" | cut -c1-64) (want 80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1)"

# --- patched copy ----------------------------------------------------------
SRC="$OUT/src"; rm -rf "$SRC"; mkdir -p "$SRC/gpu"; cp "$ENGINE"/cis2_* "$SRC/gpu/"
( cd "$SRC" && patch -p1 < "$HERE/w6-scoring.patch" ) > "$OUT/patch.log" 2>&1 || { say "RESULT: FAIL w6-build patch did not apply (patch.log)"; exit 1; }
say "pin patched engine sha256 $(cd "$SRC/gpu" && cat cis2_host.cpp cis2_math.h cis2_model.h cis2_fpenv.h cis2_sha256.h cis2_consts.inc | sha256sum | cut -c1-64)"

# --- CORE-MATH object -------------------------------------------------------
CMSRC="$CM/src/binary32/exp/expf.c"
[ -f "$CMSRC" ] || { say "RESULT: FAIL w6-build missing $CMSRC"; exit 1; }
say "pin expf.c sha256 $(sha256sum "$CMSRC" | cut -c1-64)"
# CORE-MATH's own build flags: -O3 -march=native is its default; use the FMA path
# explicitly so the object matches the AVX2+FMA host class named in PREREG sec 11.
gcc -O3 -mfma -mavx2 -c "$CMSRC" -o "$OUT/cr_expf.o" 2> "$OUT/build-cr.log" \
 || { say "RESULT: FAIL w6-build cr_expf object (build-cr.log)"; exit 1; }
gcc -shared -fPIC -O3 -mfma -mavx2 "$CMSRC" -o "$OUT/libcrexpf.so" 2>> "$OUT/build-cr.log"

# --- P, G, C ----------------------------------------------------------------
( cd "$SRC" && g++ $GF -I gpu -o "$OUT/cis2_P" gpu/cis2_host.cpp ) > "$OUT/build-P.log" 2>&1 || { say "RESULT: FAIL w6-build P"; exit 1; }
( cd "$SRC" && g++ $GF -DCIS2_W6_EXP_GLIBC -I gpu -o "$OUT/cis2_G" gpu/cis2_host.cpp -lm ) > "$OUT/build-G.log" 2>&1 || { say "RESULT: FAIL w6-build G"; exit 1; }
( cd "$SRC" && g++ $GF -DCIS2_W6_EXP_CORE -I gpu -o "$OUT/cis2_C" gpu/cis2_host.cpp "$OUT/cr_expf.o" -lm ) > "$OUT/build-C.log" 2>&1 || { say "RESULT: FAIL w6-build C"; exit 1; }
say "built P G C: $(sha256sum "$OUT"/cis2_P "$OUT"/cis2_G "$OUT"/cis2_C | cut -c1-16 | tr '\n' ' ')"

# --- Part A binary ------------------------------------------------------------
g++ $GF -I "$SRC/gpu" -c "$HERE/pinned_exp.cpp" -o "$OUT/pinned_exp.o" > "$OUT/build-A.log" 2>&1 \
 && gcc -O2 -ffp-contract=off -fopenmp -fno-builtin-expf -c "$HERE/part_a.c" -o "$OUT/part_a.o" >> "$OUT/build-A.log" 2>&1 \
 && g++ -fopenmp -o "$OUT/part_a" "$OUT/part_a.o" "$OUT/pinned_exp.o" "$OUT/cr_expf.o" -lm >> "$OUT/build-A.log" 2>&1 \
 || { say "RESULT: FAIL w6-build part_a (build-A.log)"; exit 1; }

# --- control: P-build digests ------------------------------------------------
bad=0
for t in $TOKS; do
  want=$EXP16; [ "$t" = 128 ] && want=$EXP128
  # as the digest job: prompt ids16 for both lengths; explicit paths
  dg=$("$OUT/cis2_P" --weights-dir "$WEIGHTS" --ids "$IDS/smollm2-16.txt" --gen-toks "$t" 2> "$OUT/P-$t.err" | tee "$OUT/P-$t.out" | grep '^CIS2_REF' | sed 's/.*digest=\([0-9a-f]*\).*/\1/')
  if [ "$dg" = "$want" ]; then say "control P gen_toks=$t digest=$dg MATCH"; else say "control P gen_toks=$t digest=${dg:-none} want=$want MISMATCH"; bad=1; fi
done
[ "$bad" = 0 ] && say "RESULT: OK w6-build control digests reproduced (toks: $TOKS)" || say "RESULT: FAIL w6-build control digests (INVALID per PREREG sec 9)"
exit $bad
