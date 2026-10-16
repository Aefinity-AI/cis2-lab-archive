# sv-5 — exact replay (CIS-2) against TOPLOC and a stock rerun: the registered bar is not met

Date: 2026-10-02. Protocol frozen before any data: `state/plans/SV5-PROTOCOL.md` with Amendments 1 and 2;
calibration recorded before any TEST row (`state/reports/sv5/calibration/`, commit ddfe0f8). Ledger id `sv-5`.
Generated tables: `state/reports/sv5/final/final.md`, `final.json` (analysis script `experiments/sv5/analyse.py`,
cis2-spec archive branch `cm/sv5-harness`@1ce9e76). All counts below are from that file.

## Verdict under the frozen rules

| question | rule | answer |
|---|---|---|
| Q1 | among output-changing tampers, runs that exact replay (arm A) rejects and calibrated TOPLOC (B-cal) accepts, in at least 2 of the classes L2, Q1, P1 | **no** (0 such runs in all three classes) |
| Q2 | a stock greedy rerun on another CPU class, judged on tokens, rejects at least 1 of 200 clean runs that A accepts | **no** (0 of 200) |
| Q3 | among tampers that leave the 32 output tokens unchanged, runs that A rejects and B-cal accepts, in at least 2 of W2, W3, L1 | **yes** (W2 150 of 200, W3 132 of 198; L1 14 of 200 is under the 10 % rule) |

**E1 bar (Q1 and Q2): not met.** At this scale (SmolLM2-135M, 32 greedy tokens, 200 test prompts, CPU hosts) a
verifier that only wants to know "were these the tokens of this model on this prompt" gets the same answer from a
stock rerun with a token comparison, and from TOPLOC with thresholds calibrated on the pair, as from exact replay.
Arm A did not reject any clean run (0 of 200 on each of five verifier hosts), so the run was not stopped.

## What was measured

Model SmolLM2-135M (bf16 weights), 200 TEST prompts, 32 greedy tokens, provider box1 (i5-5200U). 14 tamper classes
plus controls, 200 runs each. Verifier pairs: box1→penguin (same CPU class, AVX2), box1→box2 and box1→box3
(other class: Celeron without AVX). Completeness check: every cell has 200 rows.

Output-changing runs per class (same count under PyTorch and under the CIS-2 runtime): N0 0, W1 0, W2 0, W3 2,
L1 0, L2 12, L3 52, Q1 128, Q2 195, Q3 200, P1 195, P2 180, P3 195, S1 199.

### Clean runs wrongly rejected (TEST, 200 each)

| verifier pair | TOPLOC published thresholds | TOPLOC calibrated | rerun, tokens | rerun, hidden-state hash | exact replay (A) |
|---|---|---|---|---|---|
| box1→penguin (same class) | 0 | 2 | 0 | 0 | 0 |
| box1→box2 (other class) | 0 | 2 | 0 | 200 | 0 |
| box1→box3 (other class) | 0 | 2 | 0 | 200 | 0 |

Arm A's clean rows (tokens, witness digest, argmax digest) are equal to box1's on box2, box3, box4, box5 and
penguin, 200 of 200 each; that includes the SSE3-only Sempron and the SSSE3-only Pentium. Tampered provider rows
that were computed twice on different hosts (L3 on box1 and box3, P2 on box1 and box2, Q2 on box1 and box4) are
equal 200 of 200.

### Tampers rejected, pair box1→penguin (rejected / runs; "changing" = the 32 tokens changed)

| class (what was changed) | kind | TOPLOC published | TOPLOC calibrated | rerun, tokens | exact replay (A) |
|---|---|---|---|---|---|
| W1 one weight, lowest mantissa bit | not changing | 0/200 | 1/200 | 0/200 | 200/200 |
| W2 one weight, top mantissa bit | not changing | 0/200 | 50/200 | 0/200 | 200/200 |
| W3 one weight, lowest exponent bit | not changing | 0/198 | 66/198 | 0/198 | 198/198 |
| W3 | changing | 0/2 | 1/2 | 2/2 | 2/2 |
| L1 low-rank edit, smallest | not changing | 0/200 | 186/200 | 0/200 | 200/200 |
| L2 low-rank edit | changing | 0/12 | 12/12 | 12/12 | 12/12 |
| L2 | not changing | 0/188 | 188/188 | 0/188 | 188/188 |
| L3 low-rank edit, largest | changing | 0/52 | 52/52 | 52/52 | 52/52 |
| Q1 weights quantised to int8 | changing | 0/128 | 128/128 | 128/128 | 128/128 |
| Q1 | not changing | 0/72 | 72/72 | 0/72 | 72/72 |
| Q2 weights quantised to int4 | changing | 142/195 | 195/195 | 195/195 | 195/195 |
| P1 prompt edit | changing | 40/195 | 195/195 | 195/195 | 195/195 |
| P2 prompt edit | changing | 154/180 | 180/180 | 180/180 | 180/180 |
| P3 injected sentence | changing | 195/195 | 195/195 | 195/195 | 195/195 |
| S1 other checkpoint | changing | 199/199 | 199/199 | 199/199 | 199/199 |
| N0 control (identity patch) | not changing | 0/200 | 2/200 | 0/200 | 0/200 |

The cross-class pairs give the same picture; calibrated TOPLOC is a little weaker there (W2 42/200, W3 56/198,
L1 180/200) because its calibrated thresholds are slightly looser on those pairs.

## Findings beside the bar (reported, no bar attached)

1. **Changes that do not show in the tokens.** A single flipped weight bit, or the smallest low-rank edit, left
   the 32 tokens unchanged in 798 of 800 runs. A token rerun cannot see these (0 rejected). Exact replay rejected
   all of them. Calibrated TOPLOC rejected 1, 50, 66 and 186 of about 200 per class. This is Q3. Such a reject
   shows that the weights or the arithmetic differed from the claim; it is not evidence of a harmful output.
2. **TOPLOC with its published thresholds missed every int8-quantised run** (0 of 128 output-changing) and every
   low-rank edit (0 of 12, 0 of 52), and most P1 prompt edits (40 of 195). With thresholds calibrated on the
   pair it caught all of them, at the price of 2 false alarms in 200 clean runs on every pair. The published
   thresholds were not derived for a 135M model on CPUs; this is a measurement on this model only.
3. **Hashing a stock PyTorch rerun does not work across CPU classes**: 200 of 200 clean runs give a different
   hidden-state hash on the Celerons than on box1 (same tokens). The CIS-2 digests are equal on all six hosts.
4. **Cost** (median seconds per run on the verifier; descriptive, one machine each, no timing claim):
   penguin: TOPLOC check 0.30, stock rerun 2.66, exact replay 9.29. box2: 1.95 / 9.08 / 16.19. box3: 1.91 / 9.96 /
   13.46. Exact replay is the slowest check, about 1.4 to 3.5 times a stock rerun here. Commitment size per run:
   TOPLOC 516 bytes, exact replay 64 bytes, a bare hash 32 bytes.

## What can and cannot be said

- Can be said: on this model and these hosts, exact replay had zero false alarms on five verifier hosts of four
  CPU generations and rejected every tampered run, including every single-bit weight change. Neither rival did
  both.
- Cannot be said: that exact replay detects output tampering better than TOPLOC or a stock rerun. The registered
  test of that claim came out negative: for tampers that change the output, both rivals caught everything exact
  replay caught (TOPLOC only after calibration on the pair).
- Limits (protocol §9): one small model, 32 tokens, greedy decoding, CPUs only, three verifier pairs, single
  seed per class, tamper classes chosen by us. Sampling, GPUs, long outputs and larger models are not covered;
  cross-class token agreement of a stock rerun is expected to degrade with length, and that was not tested here.
- The "control violated" flags in the generated file are the calibrated-TOPLOC false alarms on the identity
  patch (the same 2 runs as its clean false alarms) and the cross-class hash mismatch of finding 3; neither is a
  harness fault. The calibrated-TOPLOC false alarms arise because its verifier recomputes activations in one
  teacher-forced pass while the provider produced them step by step.

## Consequence for the programme

The value of exact replay that this experiment supports is narrower than "catches more tampering": it is (a) an
exact, cross-hardware equality check with no thresholds to calibrate and no false alarms observed, (b) detection
of weight or arithmetic changes that leave a short output unchanged, and (c) a 64-byte commitment. Public wording
should say that and nothing stronger. Whether this result is published outside the company is the owner's
decision (NEEDS §00b, "pre-commit to publishing sv-5 even if a rival method ties").
