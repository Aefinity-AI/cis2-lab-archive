# sv-5 — exact replay (CIS-2) against TOPLOC and a stock rerun: the registered bar is not met

Date: 2026-10-02. Protocol frozen before any data: `state/plans/SV5-PROTOCOL.md` with Amendments 1 and 2;
calibration recorded before any TEST row (`state/reports/sv5/calibration/`, commit ddfe0f8). Ledger id `sv-5`.
This file supersedes `2026-10-02-SV5-EXACT-REPLAY-VS-TOPLOC-VS-RERUN.md` (revision 1, kept unchanged because the ledger holds its hash).
Generated tables: `state/reports/sv5/final/final.md`, `final.json` (analysis script `experiments/sv5/analyse.py`,
cis2-spec archive branch `cm/sv5-harness`@1ce9e76). All counts below are from that file; an independent recount
from the raw rows (not using the analysis script) reproduced them. Revision 2 of this report: the first version
mislabelled the quantisation classes, called mean timings medians and overstated one sentence; the verdict and
all counts are unchanged.

## Verdict under the frozen rules

| question | rule | answer |
|---|---|---|
| Q1 | among output-changing tampers, runs that exact replay (arm A) rejects and calibrated TOPLOC (B-cal) accepts, in at least 2 of the classes L2, Q1, P1 | **no** (0 such runs in all three classes) |
| Q2 | a stock greedy rerun on another CPU class, judged on tokens, rejects at least 1 of 200 clean runs that A accepts | **no** (0 of 200) |
| Q3 | among tampers that leave the 32 output tokens unchanged, runs that A rejects and B-cal accepts, in at least 2 of W2, W3, L1 | **yes** (W2 150 of 200, W3 132 of 198; L1 14 of 200 = 7 %, under the 10 % rule) |

**E1 bar (Q1 and Q2): not met.** At this scale (SmolLM2-135M, 32 greedy tokens, 200 test prompts, CPU hosts) a
verifier that only wants to know "were these the tokens of this model on this prompt" is served as well by a
stock rerun with a token comparison as by exact replay: the token rerun rejected every output-changing run and no
clean run. TOPLOC with thresholds calibrated on the pair caught every run that exact replay caught in the three
primary Q1 classes; across all classes it missed 1 of the 2 output-changing W3 runs. Arm A did not reject any
clean run (0 of 200 on each of five verifier hosts), so the run was not stopped.

## What was measured

Model SmolLM2-135M (bf16 weights), 200 TEST prompts, 32 greedy tokens, provider box1 (i5-5200U). 14 tamper
classes plus controls, 200 runs each. Verifier pairs: box1→penguin (same CPU class, AVX2; deciding pair for Q1 and
Q3), box1→box2 (Celeron without AVX; deciding pair for Q2) and box1→box3 (second cross-class pair, extra rows).
Completeness check: every cell has 200 rows.

Output-changing runs per class (same count under PyTorch and under the CIS-2 runtime): N0 0, W1 0, W2 0, W3 2,
L1 0, L2 12, L3 52, Q1 128, Q2 195, Q3 200, P1 195, P2 180, P3 195, S1 199.

Calibrated TOPLOC thresholds (exponent mismatches / mantissa mean / mantissa median, from 100 calibration prompts):
box1→penguin 0 / 0 / 0, which makes arm B an exact check of the bf16-rounded top-128 values on that pair
(Amendment 1, item 3); box1→box2 and box1→box3 1 / 0 / 0.

Where the arm A provider rows were computed (allowed by Amendment 2 for hosts whose 100 calibration rows equal
box1's): box1 L2, L3, Q1, Q2, P1, P2, W2, W3, clean; penguin L1, N0; box5 W1, P3, S1; box4 Q3; second copies of
L3 (box3), P2 (box2), Q2 (box4). For L1 and N0 the "box1→penguin" arm A comparison is therefore a
penguin-against-penguin replay; it rests on the clean-row equality below.

### Clean runs wrongly rejected (TEST, 200 each)

| verifier pair | TOPLOC published thresholds | TOPLOC calibrated | rerun, tokens | rerun, hidden-state hash | exact replay (A) |
|---|---|---|---|---|---|
| box1→penguin (same class) | 0 | 2 | 0 | 0 | 0 |
| box1→box2 (other class) | 0 | 2 | 0 | 200 | 0 |
| box1→box3 (other class) | 0 | 2 | 0 | 200 | 0 |

Arm A's clean rows (tokens, witness digest, argmax digest) are equal to box1's on box2, box3, box4, box5 and
penguin, 200 of 200 each; that includes the SSE3-only Sempron and the SSSE3-only Pentium. The three tamper classes
computed twice on different hosts are equal 200 of 200. With the verifier on all CPU threads instead of one (V1,
arms B to D only), the same-class hidden-state hash rejected 31 of 200 clean runs on penguin.

### Tampers rejected, pair box1→penguin (rejected / runs; "changing" = the 32 tokens changed)

| class (what was changed) | kind | TOPLOC published | TOPLOC calibrated | rerun, tokens | exact replay (A) |
|---|---|---|---|---|---|
| N0 control (identity patch) | not changing | 0/200 | 2/200 | 0/200 | 0/200 |
| W1 one weight, lowest mantissa bit | not changing | 0/200 | 1/200 | 0/200 | 200/200 |
| W2 one weight, top mantissa bit | not changing | 0/200 | 50/200 | 0/200 | 200/200 |
| W3 one weight, lowest exponent bit | not changing | 0/198 | 66/198 | 0/198 | 198/198 |
| W3 | changing | 0/2 | 1/2 | 2/2 | 2/2 |
| L1 low-rank update, eps 1e-4 | not changing | 0/200 | 186/200 | 0/200 | 200/200 |
| L2 low-rank update, eps 1e-3 | changing | 0/12 | 12/12 | 12/12 | 12/12 |
| L2 | not changing | 0/188 | 188/188 | 0/188 | 188/188 |
| L3 low-rank update, eps 1e-2 | changing | 0/52 | 52/52 | 52/52 | 52/52 |
| L3 | not changing | 0/148 | 148/148 | 0/148 | 148/148 |
| Q1 int8 quantisation, per row | changing | 0/128 | 128/128 | 128/128 | 128/128 |
| Q1 | not changing | 0/72 | 72/72 | 0/72 | 72/72 |
| Q2 int8 quantisation, per tensor | changing | 142/195 | 195/195 | 195/195 | 195/195 |
| Q2 | not changing | 4/5 | 5/5 | 0/5 | 5/5 |
| Q3 int4 quantisation, per row | changing | 200/200 | 200/200 | 200/200 | 200/200 |
| P1 last prompt token changed | changing | 40/195 | 195/195 | 195/195 | 195/195 |
| P1 | not changing | 1/5 | 5/5 | 0/5 | 5/5 |
| P2 first prompt token changed | changing | 154/180 | 180/180 | 180/180 | 180/180 |
| P2 | not changing | 10/20 | 20/20 | 0/20 | 20/20 |
| P3 instruction sentence prepended | changing | 195/195 | 195/195 | 195/195 | 195/195 |
| P3 | not changing | 5/5 | 5/5 | 0/5 | 5/5 |
| S1 sibling (Instruct) weights | changing | 199/199 | 199/199 | 199/199 | 199/199 |
| S1 | not changing | 1/1 | 1/1 | 0/1 | 1/1 |

The cross-class pairs give the same picture; calibrated TOPLOC is a little weaker there (W2 42/200, W3 56/198,
L1 180/200) because its calibrated exponent threshold is 1 instead of 0 on those pairs.

## Findings beside the bar (reported, no bar attached)

1. **Changes that do not show in the tokens.** A single flipped weight bit, or the smallest low-rank update,
   left the 32 tokens unchanged in 798 of 800 runs. A token rerun cannot see these (0 rejected), nor the 444
   non-changing runs of the larger tampers. Exact replay rejected all of them. Calibrated TOPLOC rejected 1, 50,
   66 and 186 of about 200 in W1, W2, W3 and L1. This is Q3. Such a reject shows that the weights or the
   arithmetic differed from the claim; it is not evidence of a harmful output.
2. **TOPLOC with its published thresholds missed every per-row int8-quantised run that changed the output**
   (0 of 128), every low-rank update (0 of 12, 0 of 52) and most last-token prompt edits (40 of 195). With
   thresholds calibrated on the pair it caught all of them, at the price of 2 false alarms in 200 clean runs on
   every pair. This model is outside TOPLOC's published range (hidden size 576, 2 proofs per run, bf16 cast,
   CPU): it is a measurement on this model only.
3. **Hashing a stock PyTorch rerun does not work across CPU classes**: 200 of 200 clean runs give a different
   hidden-state hash on the Celerons than on box1 (same tokens). The CIS-2 digests are equal on all six hosts.
4. **Cost** (mean seconds per run on the verifier, from the generated file; descriptive, one machine each, no
   timing claim). penguin: TOPLOC check 0.30, stock rerun 2.66, exact replay 9.29. box2: 1.95 / 9.08 / 16.19.
   box3: 1.91 / 9.96 / 13.46. Medians (recount): penguin 0.27 / 2.63 / 8.35, box2 1.76 / 8.86 / 14.28, box3
   1.54 / 9.90 / 12.05. Exact replay is the slowest check: 1.2 to 3.5 times a stock rerun and about 7 to 31
   times the TOPLOC check here. Commitment size per run: TOPLOC 516 bytes, exact replay 64 bytes, a bare hash 32.

## What can and cannot be said

- Can be said: on this model and these hosts, exact replay had zero false alarms on five verifier hosts of four
  CPU generations and rejected every tampered run, including every single-bit weight change. Neither rival did
  both. This holds under the conditions in the limits below: the provider must serve with the CIS-2 CPU runtime
  (a stock or GPU run cannot be checked this way), and the provider does not adapt to the check.
- Cannot be said: that exact replay detects output tampering better than a stock rerun or calibrated TOPLOC. The
  registered test of that claim came out negative. For tampers that change the output the token rerun caught
  every run; calibrated TOPLOC caught every run in the three primary classes and all but 1 of 1,358 over all
  classes.
- Limits (protocol §9): one small model, 32 tokens, greedy decoding, CPUs only, three verifier pairs, single
  seed per class. The tamper list is ours and concentrates on small changes, where exact replay is expected to
  differ from a tolerance check; it is not a neutral sample of attacks. Arm A verifies CIS-2 serving while arms
  B, C and D verify ordinary PyTorch serving, so this is not like-for-like serving, and nothing here measures
  what serving with CIS-2 costs a provider. The commitments differ in strength (A covers the full logits of
  every step, TOPLOC the top 128 values of the last hidden state). Calibrated TOPLOC is not a matched
  false-alarm rate. Sampling, GPUs, longer outputs and larger models are not covered and were not tested.
- The "control violated" flags in the generated file are the calibrated-TOPLOC false alarms on the identity
  patch (the same 2 runs as its clean false alarms on each pair) and the cross-class hash mismatch of finding 3.
  The TOPLOC false alarms are consistent with the fact that its verifier recomputes activations in one
  teacher-forced pass while the provider produced them step by step (a step-by-step stock rerun on penguin
  reproduces box1's hashes 200 of 200); that cause was not isolated by an experiment.

## Consequence for the programme

The value of exact replay that this experiment supports is narrower than "catches more tampering": it is (a) an
exact, cross-hardware equality check with no thresholds to calibrate and no false alarms observed, (b) detection
of weight or arithmetic changes that leave a short output unchanged, and (c) a 64-byte commitment — at the
highest verification cost of the three methods and only for providers that serve with the CIS-2 runtime. Public
wording should say that and nothing stronger. Whether this result is published outside the company is the owner's
decision (NEEDS §00b, "pre-commit to publishing sv-5 even if a rival method ties").
