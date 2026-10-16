# w6 harness: libm hazard bound (glibc expf vs CORE-MATH cr_expf)

Spec: `state/prereg/w6-PREREG.md` (FROZEN rev 2, not edited). Status of this directory: harness built and
smoke-tested; the lab is NOT started (start gate: ledger batch 32 must merge; the start decision is the operator's).

## PREREG step -> file
| PREREG | File |
|---|---|
| 0. pin CORE-MATH commit, glibc, engine sha, patch sha, window list sha; P-build control | `build_w6.sh` (writes `$W6_OUT/BUILD.txt`), `CORE-MATH-PIN.txt` |
| 1. Part A, all binary32 in [-88,0], (0,88], plus band above 88.0 | `part_a.c`, `pinned_exp.cpp`, `run_partA.sh` |
| 1. verifier, 1,000,000 random inputs vs multiprecision (Python `decimal`, 80 digits, exact rounding) | `verify_cr.py` |
| 4. scoring mode for the engine (private patch; `--gen-toks` unchanged) | `w6-scoring.patch` |
| 4. builds P (patched source, default flags), G (`-DCIS2_W6_EXP_GLIBC`), C (`-DCIS2_W6_EXP_CORE` + CORE-MATH `expf.c`) | `build_w6.sh` |
| 4. positions: sv-5d windows, token ids only | `make_windows.py` (checks sha256 20c94006...), `run_partB.sh` |
| 7.2/7.3 rate pilot, full run, G vs C bar, P vs C, P vs G | `run_partB.sh N`, `analyse.py` |
| 11.3 glibc ifunc variant | `part_a` prints `VARIANT:` and `glibc_variant=`; `run_partA.sh` logs LD_DEBUG=bindings |

## Patch (w6-scoring.patch)
Base = the engine sources of the digest payload (`~/cis2-digest/gpu`, files `cis2_host.cpp`, `cis2_math.h`); paths
are `a/gpu/...`, apply with `patch -p1` from a directory that holds `gpu/`. The public cis2-spec repo carries no
`gpu/` tree, so the patch is against the payload copy (see the note at the end). Nothing was committed to cis2-spec.
- `cis2_math.h`: `cis2_exp_pinned` returns `expf(x)` under `-DCIS2_W6_EXP_GLIBC` and `cr_expf(x)` under
  `-DCIS2_W6_EXP_CORE`; with neither define the function is the unchanged pinned polynomial. Every call site
  (softmax, SiLU, the RoPE inv_freq table) is covered.
- `cis2_host.cpp`: `--score-windows FILE --score-out FILE [--score-max N]`. Teacher-forced; one window per line;
  position restarts at 0 per window; per position writes `w pos top1 top1_f32bits top2 top2_f32bits`; prints
  `W6_SCORE exp=... positions=... out_sha256=...`. The `--gen-toks` path is not touched.

## Smoke (box7, nice -n 10, 4 threads)
```
W6_OUT=$HOME/legs/w6 TOKS="16" ./build_w6.sh        # builds, pins, P-build 16-token digest check
./part_a --range neg --stride 1068                  # ~2^20 values per range: SMOKE: lines
./part_a --range pos --stride 1068
./part_a --range band --limit 20000
python3 -I verify_cr.py $W6_OUT/libcrexpf.so 20000 7
```

## Full-run commands (not run)
```
cd state/labs/w6
W6_OUT=$HOME/legs/w6 TOKS="16 128" nice -n 10 ./build_w6.sh   # control must read MATCH for 16 and 128 tokens
W6_OUT=$HOME/legs/w6 ./run_partA.sh                           # neg, pos, band; default and --ftz; spot check 1e6
W6_OUT=$HOME/legs/w6 ./run_partB.sh 1000                      # rate pilot (N falls to 20000 if too slow, PREREG sec 4)
W6_OUT=$HOME/legs/w6 ./run_partB.sh 100000                    # full run; prints the flip table and bound
```
Each run ends in a `RESULT:` line (or `SMOKE:` for the sub-range runs). Part A prints two lines per range
(`impl=glibc`, `impl=pinned`) plus `DETAIL:` (distance histogram) and up to 16 `WORST:` inputs with exact bit patterns.

## Notes the frozen text does not settle
- MXCSR: the engine runs with FTZ|DAZ set (`cis2_fpenv_init`), so subnormal results are flushed there. Part A is
  run in both regimes (`--ftz` sets FTZ|DAZ in every thread). Without `--ftz` the pinned exponential returns +0
  below about -87.34 where the correctly rounded value is subnormal, which inflates its maximum distance; the
  `--ftz` figure is the one that matches what the engine sees.
- `glibc_variant`: LD_DEBUG=bindings shows the binding of `expf@GLIBC_2.27` to libm, not the ifunc body. The
  variant is read from the CPU flags (glibc 2.41 selects the FMA body when FMA and AVX2 are usable) and
  corroborated by the resolved pointer: its low bits equal the resolver's FMA branch offset in libm (0x7d2a0
  versus the baseline 0x676f0 on this Debian build; resolver listing via `objdump -d`).
- CORE-MATH `expf.c` is compiled `-O3 -mfma -mavx2` (the AVX2+FMA host class of PREREG sec 11.3).
- Part B replaces the exponential in the RoPE inv_freq table too ("every exp call"), so the inv_freq table
  digest of G and C differs from P by construction; the P-build control is unaffected.
- Position list: the leading windows of the sv-5d file (file order) until 100,000 positions; the PREREG's
  "same index set as the 3-build comparison" could not be resolved to a stored list, so this is recorded as a choice.
