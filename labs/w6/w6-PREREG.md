# PREREG w6: libm hazard bound, glibc expf versus a correctly-rounded expf (CORE-MATH) inside SmolLM2-135M decoding

STATUS: FROZEN rev 2 (critic pass applied) 2026-10-16 03:40Z; registered with cm-exp new (bar sha256 in state/exp registry) and ledgered in the next batch; no run has started. Written 2026-10-16 (Claudius Maximus builder, box7). No run of this lab has been started. Freeze = `cm-exp new w6` plus the public ledger line for this file's sha256; later changes are `w6-amend-N.md`. Source: `state/plans/2026-10-16-EXHAUSTIVE-PROGRAMME.md` section 2 (W6) and SPEED-SIZE report line 77 (P2 hybrid); GO on `edge-exact`, Justin 2026-10-16 ~03:00Z. Purpose in the programme: informs the L2 tolerance proposal due 2026-10-29.

## 1. Question
How many next-token decisions change if the exponential used in SmolLM2-135M inference is glibc `expf` versus a correctly-rounded binary32 `expf` (CORE-MATH), and how far from correct rounding are glibc `expf` and the CIS-2 pinned exponential over the full binary32 domain the engine can call, a superset of the model's inputs? Part A measures the hypothetical delegation; it says nothing about the shipped digest (the engine uses `cis2_exp_pinned`, not glibc). This is a bound on the "libm hazard" for the CIS-2 specification, i.e. a number for whether libm must be specified bit-for-bit or by a ULP bound.

## 2. What prior art already shows (honest)
- Correctly-rounded libm is KNOWN in isolation: CORE-MATH (exhaustively checked binary32 functions, about the speed of glibc; gitlab.inria.fr/core-math/core-math, MIT or LGPL-class per file, licence re-read at pin) and RLIBM-32 (2104.04043 [R]) report ULP and speed. Gensyn Verde (2502.19405 [V]) re-implements exp, sin, cos and tanh to control operation order and reports practical overhead but no libm-only figure.
- [removed 2026-10-17: unverified prior-art characterization] Sweep limits as in the register.
- Our own CIS-2 specification already pins its own exponential (`cis2_exp_pinned` in `gpu/cis2_math.h`, a strict sequential Horner polynomial, no FMA; Rust twin `exp_pinned` in cis2-fp `src/math.rs`; internal ULP-range work E26/E27). So the production CIS-2 digest does not call glibc at all. This lab therefore measures a hypothetical (what if an implementation delegated exp to libm), which is exactly the question a tolerance-based L2 proposal has to answer. It does not change any existing pinned digest.
- Register ids: 2104.04043, 2502.19405 (`state/reports/prior-art/PRIOR-ART.md`); magnitude logic from MarginGate 2605.30218 [V] and our sv-5d (flips live at tiny margins; cross-ISA noise gave 1.8-2.4 flips per million).

## 3. Predictions (source)
- P1 [EST, mine]: glibc `expf` (version recorded; Debian 13) has maximum error vs the correctly-rounded value of at most 1 ULP over the exhaustive range, and 0.5-5 % of inputs are not correctly rounded.
- P2 [from E27, read 2026-10-16]: `cis2_exp_pinned` (the spec's `exp_pinned`) has maximum error 1 ULP against the f64 oracle narrowed to f32 over every finite f32 (cis2-spec `docs/E27_EXP_LN_RANGE.md` line 185: `exp ALL finite n=3257925634 max|ulp|=1 @0x33800000`; line 186 for x <= 0: `max|ulp|=1`; line 187 for x >= 0: `max|ulp|=1`). Against CORE-MATH (correctly rounded) the distance is therefore expected to be at most 1 ULP in Part A, except inside the spec's high-guard clip band: E27 lines 44-61 record that `x > 88.0` returns +Infinity although exp is finite up to 88.7228, 94,743 f32 values (`0x42B00001` to `0x42B17217`); that band is outside Part A's range [-88, 88] but is reported separately. E26 (`docs/E26_TRIG_RANGE.md`) covers sin/cos only and gives no exp number. E27's oracle is f64 narrowed, not CORE-MATH, so the 1 ULP figure is a pre-check, not a substitute for Part A.
- P3 [EST, mine]: flips between the glibc build and the CORE-MATH build over 100,000 positions: 0 or 1 (P(0) about 0.7). Derivation: sv-5d logit-gap shifts of up to 1.4e-4 from cross-ISA noise gave about 2 flips per million positions; a 1-ULP exp error perturbs softmax and SiLU at a smaller scale than that, so the expected count is about 0.2 in 100,000. If it is larger than 4, the prediction is wrong and that is the result.
- P4 [EST 0.8, mine]: every flip (if any) has margin under 1e-3 in the CORE-MATH run.

## 4. Design
Part A (exhaustive, arithmetic only): enumerate every binary32 input x in [-88, 88] (softmax after max-subtraction gives x <= 0; the SiLU path `cis2_silu_pinned`, `cis2_math.h:432-434`, calls exp(-x) for x of either sign; further code around `cis2_math.h` lines about 574-604) and compare the result bits of (i) glibc `expf`, (ii) `cis2_exp_pinned`, against (iii) CORE-MATH `cr_expf`. About 2.1e9 inputs per implementation over [-88, 88], minutes on box7. Report count of non-equal results and maximum ULP distance, for (i) and (ii), split into [-88, 0] and (0, 88]. The 94,743-value band above 88.0 (E27) is reported separately as a spec-guard fact, not a libm comparison.
Part B (end to end): three builds of the CIS-2 C++ engine (`cis2_host.cpp`, g++ `-std=c++17 -O2 -ffp-contract=off -fexcess-precision=standard -fno-fast-math`, as in the digest job): P = pinned (control; built from the PATCHED source with default flags, so the control digest tests the patched tree; must reproduce the pinned digests d8274305... for 16 tokens and 22f69ad8... for 128 tokens), G = every exp call replaced by glibc `expf`, C = replaced by CORE-MATH `cr_expf`. The rest of the engine is identical. Positions: teacher-forced scoring of fixed text, N = 100,000 positions (target), recording per position the top-1 index and top-1/top-2 margin of each build. This needs a small scoring mode in the engine (private branch, sha256 pinned; unmodified `--gen-toks` behaviour unchanged, checked by the P-build digests). If the engine runs too slowly for N = 100,000 within 1 box-h (rate measured on a 1,000-position pilot), N falls to a pre-declared minimum of 20,000 and the bar's flip allowance scales (section 9).
Texts: 100,000 positions of text from the sv-5d windows file (same index set as the 3-build comparison, pinned list of windows; token ids only used), SmolLM2 tokenization already fixed.

## 5. Hosts and resources
box7 (i7-7700HQ AVX2+FMA, 16 GB): all of Part A and B. Optional, no bar: box1 (AVX2+FMA) repeat of Part A. A no-FMA run (box2 Celeron N4020, SSE4.2; CORE-MATH without-FMA path) is listed in SPEED-SIZE P2 as an open question and is out of scope here (3.7 GB RAM, about 4 GB disk). $0. About 1 box-h of the programme estimate plus compile time, 1 Fable-h. The EV card for the lane (edge-exact, ruled GO by Justin 2026-10-16; w4 has its own card `w4`) must read GO before `cm-exp new w6` is run.

## 6. Models, code, licences
SmolLM2-135M, Apache-2.0, https://huggingface.co/HuggingFaceTB/SmolLM2-135M (weights sha256 80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1). CORE-MATH: https://gitlab.inria.fr/core-math/core-math (binary32 `expf` source; licence text copied into the RESULT file at pin; if it forbids our use, stop). glibc: system library of box7, version recorded (`ldd --version`). Texts: sv-5d window indices (UltraChat 200k licence line copied from the dataset card at freeze). No Claude-generated text enters training data.

## 7. Procedure
0. Pin CORE-MATH commit, glibc version, engine source sha256, patch diff sha256, window list sha256; reproduce the pinned digests with the P-build (control).
1. Part A, with a verifier re-implementation for 1,000,000 random inputs using a multiprecision (MPFR or Python `decimal`/`mpmath`) reference to confirm that `cr_expf` is the correctly rounded value on those samples.
2. Part B rate test on 1,000 positions; then the full run.
3. Compare G vs C (the bar), P vs C and P vs G (reported without a bar).

## 8. Analysis
Counts of position-level top-1 differences between builds, their positions, margins (from C), and exact one-sided 95 % upper bounds. Part A table: counts and max ULP.

## 9. THE BAR (draft, written 2026-10-16 before any run; text for `cm-exp new --bar`)
MET if (i) the P-build reproduces the pinned 16-token and 128-token digests (control), AND (ii) in Part B with N >= 100,000 teacher-forced positions the glibc build and the CORE-MATH build disagree on the top-1 token at no more than 4 positions (one-sided 95 % upper bound on the flip rate below 1e-4 per position), AND (iii) every such disagreement has top-1/top-2 margin at most 1e-3 in the CORE-MATH build. NOT MET if (ii) or (iii) fails (final). Reported, no bar (control): in Part A the maximum distance of glibc `expf` from the correctly-rounded value over [-88, 88] (expected at most 1 ULP, P1). With N between 20,000 and 99,999, the allowance is 0 flips (95 % upper bound under 1.5e-4) and the result is labelled REDUCED-N in any use. INVALID if the control digests are not reproduced, if CORE-MATH `cr_expf` fails the multiprecision spot check, if a pinned hash differs, or if N is under 20,000.

## 10. Success and failure, stated for a stranger
A reader needs the three builds, the position list and the flip table. Whether the flip count is at most 4 and the margins at most 1e-3 is read directly from the table; Part A is re-runnable in minutes by anyone with the CORE-MATH source.

## 11. Disclosures that travel with any W6 number
1. The production CIS-2 digest uses the pinned exponential, not glibc; this lab measures a hypothetical libm substitution, one libm version, one CPU class (AVX2+FMA), one model, teacher-forced scoring rather than free decoding.
2. A flip count of zero in 100,000 bounds the rate only to about 3e-5 per position (rule of three); it is a bound, not "zero hazard".
3. glibc `expf` on x86_64 is ifunc-dispatched (`__expf_fma` on FMA hosts). The selected variant is recorded in the RESULT file (LD_DEBUG=bindings or gdb) and "glibc expf" in every W6 number means that variant; a no-FMA host's glibc is a different function.
4. exp is one of several libm calls (sin, cos, rsqrt/sqrt in rope and norms) in a transformer; only exp is varied.
5. Sample size and the single-reference limits of sv-5d apply to the reading of the 1.8-2.4 per million comparison.

## 12. Publication (per `state/policy/PUBLISH-SCORING.md`)
Private until scored. Part A table and the flip bound are spec evidence for the L2 tolerance proposal and not a moat; the engine patch stays private (the engine internals are CIS-2 conformance material: if the card finds `conformance_suite_internals` applies to the scoring-mode patch, publish the numbers only). Soft flags: `number_not_in_numbers_md`, `word_rule_check`. Score card after the result; 70 or more publishes, 40-69 one NEEDS line, under 40 private. Used internally for the 2026-10-29 L2 proposal after the verifier report, regardless.

## 13. Stop-loss
If the scoring mode cannot be added without changing the P-build control digests within 1 Fable-h, run Part A alone and record Part B as INCONCLUSIVE; if CORE-MATH's licence forbids use, stop (INVALID).

## 14. Status
FROZEN rev 2 (critic pass applied) 2026-10-16 03:40Z; registered with cm-exp new (bar sha256 in state/exp registry) and ledgered in the next batch; no run has started. Suggested registration: id `w6`; title "libm hazard bound: glibc expf vs correctly-rounded expf in SmolLM2-135M decoding"; host `box7`; bar = section 9.
