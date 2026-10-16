# sv-5d addendum: box2/box3 B1T2 and box2 B8T1 now in hand (complete extra cells)

Date: 2026-10-03 (about 12:35Z). Draft; nothing recorded, committed, pushed or sent.
This file supplements `state/reports/2026-10-03-SV5D-PER-TOKEN-DIVERGENCE.md` (final scoring text; its sha256 is already in the ledger `sv-5d` result record, so that file was NOT overwritten).

## Registered bar (verbatim from the ledger `registered` record, bar_sha256 402041299173e4fe...)

> Why: sv-5b/sv-5c found 0 token differences in 200 runs of 256 tokens, but the logits do move (up to 9e-5) and only 2 of 51,200 steps had a top-1 minus top-2 margin that small, so those runs could not measure a rate of a few per million. Setup: clean SmolLM2-135M checkpoint of sv-5, fp32, pinned sv-5 stack. 8,000 text windows from UltraChat conversations taken from the end of the sv-5 shuffled order (no overlap with the sv-5 prompts), each cut to a length drawn with a fixed seed from 160..256 tokens (about 1.66 million positions). One full forward pass per window; at every position record the argmax next token and the top-1 minus top-2 logit margin. Reference R = box1 (AVX2), one window at a time, one thread, all windows. X = other CPU class, one window at a time, one thread: box2 for windows 0-3,999, box3 for windows 4,000-7,999. B = box1, batches of 8 consecutive windows, left padding with attention mask, one thread, all windows. (x) cross-class MET only if X differs from R in the argmax token at 3 or more positions AND at a rate of at least 1 per 1,000,000 compared positions. (b) batching, own verdict, same rule for B against R. If a part is not met, the report states the count, the positions compared and the 95 percent upper bound on the rate. Reported without a bar: T = box1 two threads (windows 0-1,999), S = penguin same CPU class (windows 0-1,999), size of the margin shifts, the reference margin at each differing position, and the implied share of 256-token responses whose greedy output would differ. Prediction written before the run, from the sv-5c margins: 2 to 4 differing positions per million. Limits stated in advance: positions are teacher-forced on natural text, not greedy trajectories; a difference means a greedy decoder would emit a different next token at that context. Exact replay under the CIS-2 runtime is identical across these hosts by construction and by sv-5 measurement; it is not re-measured here.

## What was added
The three cells that the main report lists as "not yet copied / running" are complete and now on penguin:
box2 B8T1 w0-3999 (`~/sv5d/box2/B8T1_0-4000/p0of1.npz`, sha256 d3735d72...fcd), box2 B1T2 w0-3999 (`~/sv5d/box2/B1T2_0-4000/p0of1.npz`, sha256 94727862...494, finished 11:27Z box time), box3 B1T2 w4000-7999 (`~/sv5d/box3/B1T2_4000-8000/p0of1.npz`, sha256 a4f76e7d...83e). rsync from the boxes, sizes and sha256 matched on both ends.
Compare run: `systemd-run --user --scope -p MemoryMax=2500M -p CPUQuota=60% python3 ~/feed-payload/sv5b/sv5d_compare.py` with reference box1/B1T1_0-8000 and all other dirs; output `state/reports/sv5d/2026-10-03-sv5d-compare-full.json` (sha256 2b563fd9b5639ef49baf8c93cb1905eb2007943a94b06c22eabc3803fa4535c5). Windows compared in every cell equal the intended ranges; 0 windows only in one side.

## Per-variant counts (argmax differs from R, teacher-forced, positions compared per cell)
| cell | role | windows | positions | flips | per million | 95% upper (CP) |
|---|---|---|---|---|---|---|
| box1 B8T1 w0-7999 | (b) B, bar | 8000 | 1,664,964 | 4 | 2.4025 | 5.498 |
| box1 B1T2 w0-1999 | T, no bar | 2000 | 416,030 | 1 | 2.4037 | 11.403 |
| box2 B1T1 w0-3999 | part of X | 4000 | 833,394 | 2 | 2.3998 | 7.554 |
| box3 B1T1 w4000-7999 | part of X | 4000 | 831,570 | 1 | 1.2025 | 5.705 |
| box2 B8T1 w0-3999 | extra | 4000 | 833,394 | 4 | 4.7997 | 10.983 |
| box3 B8T1 w4000-7999 | extra | 4000 | 831,570 | 2 | 2.4051 | 7.571 |
| box2 B1T2 w0-3999 | extra | 4000 | 833,394 | 2 | 2.3998 | 7.554 |
| box3 B1T2 w4000-7999 | extra | 4000 | 831,570 | 1 | 1.2025 | 5.705 |
| penguin B1T1 w0-1999 | S, no bar | 2000 | 416,030 | 0 | 0 | 7.201 |
| penguin B1T1 w2000-7999 | extra | 6000 | 1,248,934 | 0 | 0 | 2.399 |

Composite X (box2 w0-3999 + box3 w4000-7999) = 3 flips / 1,664,964 = 1.8018 per million (unchanged from the main report).

## Flip positions and margins (window / position: R margin, run margin; R top1 -> run top1)
- box1 B8T1: w274/p144 (1.907e-06, 7.629e-06; 2166->2364), w1302/p143 (0.0, 1.907e-06; 281->30; exact tie in R), w3334/p101 (5.722e-06, 1.907e-06; 1453->325), w5595/p154 (1.907e-06, 3.815e-06; 451->260).
- box1 B1T2: w274/p144 (same as B8T1).
- box2 B1T1 and box2 B1T2 (identical flip sets): w3334/p101 (5.722e-06, 7.629e-06; 1453->325), w3687/p106 (3.815e-06, 9.537e-06; 282->739).
- box3 B1T1 and box3 B1T2 (identical): w6300/p248 (1.907e-06, 4.768e-06; 550->805).
- box2 B8T1: w677/p168 (5.722e-06, 7.629e-06; 357->284), w3154/p88 (3.815e-06, 5.722e-06; 451->354), w3334/p101 (5.722e-06, 1.335e-05; 1453->325), w3687/p106 (3.815e-06, 9.537e-06; 282->739). Two are the same as box2 B1T1; two are new (batching on top of the class difference).
- box3 B8T1: w5595/p154 (1.907e-06, 2.861e-06; 451->260), w6300/p248 (1.907e-06, 4.768e-06; 550->805).
All listed flips swap the top two tokens (run top1 = R top2). Largest R margin at any flip is 5.722e-06; all are in the sub-1e-5 margin band. Max |margin diff| per cell: box2 9.73e-05, box3 1.37e-04 (B1T1/B1T2), 1.39e-04 (box3 B8T1); the other cells are in the main report.

## New observations (descriptive, not bar items)
1. Thread count made no difference to the flip set on box2 (B1T2 = B1T1, 2 flips) or box3 (B1T2 = B1T1, 1 flip): the new T cells agree with the T bar cell in kind, a count at the same rate scale.
2. Batching on box2 adds 2 flips beyond its one-at-a-time set (4 vs 2); on box3 it adds 1 (2 vs 1, w5595 new). Batching and class differences each move a handful of per-million-scale near-ties; they union rather than cancel in these cells.
3. Penguin (same CPU class as box1) is 0 of 1,664,964 across all 8000 windows, as before.

## Verdict against the bar exactly as registered
Unchanged: (x) MET at the minimum count of 3 (X = 3 of 1,664,964 = 1.80/M, which is at least 3 positions and at least 1 per million); (b) MET (box1 B8T1 = 4, 2.40/M; 3 without the exact-tie w1302/p143, still at least 3). The newly added cells are outside the five registered cells (R, X, B, T, S) and do not change either verdict. Caveat: one-sided 95% lower bounds on X (0.49/M) and B (0.82/M) are below 1/M, so the rate floor of 1 per million is met by the point estimate, not established by the interval (as in the main report).

## Limits
Teacher-forced natural text (not greedy trajectories); one model (SmolLM2-135M fp32), one stack; the near-tie positions are few (14 flips listed over the extra and bar cells, fewer distinct positions), so any rate here is a small-count estimate with wide intervals; the identical flips across B1T1/B1T2 and across B8T1 mean the cells are not independent samples. The extra cells have no registered bar. Exact replay under CIS-2 is not re-measured. No claim about which of two near-tied tokens is "correct".

## Ledger
Not recorded by this step. The ledger already holds a `result` for sv-5d (verdict met, ts 1791015413.6, 2026-10-03T08:16:53Z, files list the main report + compare.json + recount); if the extra cells should be attached, that is a new `files` note, not a change of verdict.
