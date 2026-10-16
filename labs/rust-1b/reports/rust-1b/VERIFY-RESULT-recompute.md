# rust-1b final result: independent recomputation (lens: RECOMPUTATION)

Verdict on this lens: CONFIRMED. No label changes. No number that carries a label is wrong. One loose phrase (note below).

## What I ran
- Own script, standard library only: ~/scratch-rust1b-final/recompute/mine.py (did not read or import score.py or the report's scorer first). A second inline check read hygiene fields (foreign load, MHz, order positions, spreads).
- Per-rep value = 8 x 63 / (sum of the 8 decode_ns in seconds), as the pass mark says ("Per-rep value = (8 x 63 tokens) divided by the sum of the 8 prompt walls"). Median over KEPT reps only. Memory = median of the 5 per-rep peaks (peak_pss_kb, peak_anon_kb, vmhwm_kb).
- Reference build rule (R4): Rust arm reference = opt-level with the higher median. r = left median / right median. Rule applied: "LEFT ARM AHEAD: r > 1.10 and non-overlapping reps" (I read non-overlapping as: lowest left rep above highest right rep). TIE 0.90..1.10. BEHIND r < 0.90 and non-overlapping.
- Labels decided by me before reading the report's labels.

## Row counts (mine = report)
- box1 (n1): 45 rows, 45 KEPT, 0 VOID, 0 DISCARD, 0 INVALID.
- box1-n2: 34 rows: 30 KEPT, 3 VOID (gob-O2 rep1 03:34:37Z foreign 0.0678; gob-O3 rep3 04:02:38Z 0.0331; gmkl-O2 rep4 04:15:23Z 0.0322; limit 0.032 each, so VOID is correct by R1), 1 INVALID (t rep 0, threads 4 not 2), 0 DISCARD. Six other arms 5 KEPT each.
- box2: 10 rows: 7 KEPT, 3 DISCARD (clock drops 0.2029, 0.2311, 0.1852 above 0.15), all rep 0, so the host is INVALID by the three-discard rule. No n2 rows.
- No kept row has foreign load above its limit, start load 0.3 or more, a nonzero rc, problems, or a thread-count change.

## Labels (box1, N=1, mine)
| pair | r (mine) | lowest left / highest right (tok/s) | label |
|---|---|---|---|
| G-OB (O3) v T | 1.3377 | 18.482 / 14.140 | AHEAD |
| G-OB (O3) v Q | 1.1954 | 18.482 / 15.610 | AHEAD |
| G-MKL (O3) v T | 1.3037 | 18.010 / 14.140 | AHEAD |
| X (O2) v T | 1.3033 | 18.016 / 14.140 | AHEAD |
| X (O2) v Q (no label) | 1.1647 | | ratio only |
References: G-OB O3, G-MKL O3, X O2. Every other build also gives AHEAD (lowest r vs T 1.2926 for X O3, vs Q 1.1551). None INCONCLUSIVE. Same four labels as the report.

## Medians (tok/s), mine equals JSON and RESULT.md to all printed digits
n1: gob-O2 18.434973, gob-O3 18.567032, gmkl-O2 18.004451, gmkl-O3 18.095501, x-O2 18.089652, x-O3 17.941708, t 13.879871, q 15.532261, q8 27.236945. Q8/Q 1.7536.
n2: gob-O2 19.051787, gob-O3 19.063831, gmkl-O2 19.441674, gmkl-O3 19.476700, q 20.507575, q8 45.160508. No T. G-OB/Q 0.9296, G-MKL/Q 0.9497, G-MKL/G-OB 1.0217. n2 over n1: Q 1.320, G-OB 1.027, G-MKL 1.076, Q8 1.658. All as in RESULT.md section 3.
The gmkl-O2 n2 median is 19.441674 and is the rep-0 row (t_end 03:21:10Z, start 03:20:27Z, foreign 0.0161, limit 0.032, KEPT). The disclosure matches the rows.
Max difference between my per-rep values and the runner's stored value_tps: under 5e-07 (matches report).

## Memory (box1 n1, kB medians): mine = JSON
PSS: gob-O3 539376, gmkl-O3 546387, x-O2 535050, t 1332285, q 587071, q8 201489. Anon: 535820, 534116, 533472, 888712, 56552, 56644. VmHWM: 541020, 548060, 536672, 1397232, 588908, 203324. Ratios T/G-OB 2.470, Q/G-OB 1.088, T/Q 2.269, anon T/G 1.659. n2 PSS 541684 / 547234 / 587233 / 200007 matches the 541.7 / 547.2 / 587.2 / 200.0 MB in the text.

## box2 (unlabelled, INVALID)
One kept rep per arm; values mine = report: G-OB O3 6.535, T 5.065, Q 7.431, X O2 6.338, X O3 9.098, Q8 12.595, G-MKL O2 5.371. G-MKL O3 has no kept rep. X O3 / X O2 = 1.435 (report says 1.44; fine). I did not compute any label for box2 (one rep per arm gives no median; the report gives none).

## Hygiene numbers re-derived (all agree)
box1 n1: max foreign arm 0.0172, host 0.0378 (limits 0.0285 / 0.10); start loads 0.25-0.29; MHz 2094.855-2095.595; worst drop 0.01 percent; mean order position 4.0 for all nine arms; positions listed in RESULT.md notes equal mine. box1 n2: foreign max 0.0284 (limit 0.032); baseline arm 0.012, host 0.0215; mean positions 2.6-2.8. T rep 3 after-run reading 1,408 MHz is in the row. T median without rep 3: 13.991 (report 13.99). T spread 3.68 percent (report 3.7), widest of nine.

## Discrepancies
1. NOTE (wording only, changes no label): RESULT.md section 9 says the three Rust arms are "each separated by 2.4 to 4.3 tok/s in every repetition". For the four labelled pairs the gap between the lowest left rep and the highest right rep is 2.87 (G-OB v Q), 3.87 (G-MKL v T), 3.88 (X v T), 4.34 (G-OB v T). The 2.4 comes from the unlabelled X v Q pair (18.016 - 15.610 = 2.41). Correction: say "2.9 to 4.3 for the four labelled pairs" (or say that 2.4 is X against Q).
2. NOTE: RESULT.md section 3 lists the other reps of gmkl-O2 in a different order from reps 1 to 4 (rows: 19.512041, 19.472164, 19.441132, 19.312462). Same four numbers, no effect.

Not recomputed (outside this lens): checks/ files (logit differences, 17 Q8 mismatches, T hash), arm L rows from rust-1, dependency and line counts, box3 (no rows exist), budget seconds. The register verdict word "met" is a convention choice, not a recomputation; my numbers do not argue against it and support every label in the proposed summary text (r 1.338, 1.195, 1.304, 1.303, X v Q 1.165).
