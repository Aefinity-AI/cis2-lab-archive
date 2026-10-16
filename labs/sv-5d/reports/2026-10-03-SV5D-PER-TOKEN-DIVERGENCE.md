# sv-5d: per-token argmax divergence of a stock PyTorch rerun, across CPU classes and under batching

Date: 2026-10-03. Ledger id `sv-5d` (registered 2026-10-02T11:50:07Z, bar sha256 `402041299173e4fe70c791802c293f43c999e12bda52bed7064d3892e87b4fb7`; started 2026-10-02T11:56:06Z).
Status of this file: final scoring text with the verifier fixes applied (updated 2026-10-03 about 07:45Z), ready for `cm-exp result`. Nothing has been recorded in the ledger, committed, pushed or sent.
Evidence files for the record: this report, `state/reports/sv5d/2026-10-03-sv5d-compare.json`, and the recount script and its output `state/reports/sv5d/2026-10-03-sv5d-recount.py` / `.out`.

## Verdict: MET (both registered parts)

- **(x) cross-class: MET.** X (box2 on windows 0-3,999 plus box3 on windows 4,000-7,999, one thread, one window at a time) differs
  from the box1 reference R at **3** of 1,664,964 compared positions = **1.8018 per million**: **2 flips on box2 and 1 on box3**. The rule needs
  at least 3 positions and at least 1 per million. It is **met at the minimum count of 3**. All 3 flips are strict on both sides (R margin and the
  run's own margin both above 0), so none of the 3 depends on how `torch.topk` breaks exact ties (a different tie-break could only add to X). Host by host, neither box2 (2) nor box3 (1)
  reaches 3; the bar defines X as the composite of the two, and (x) is scored on that.
- **(b) batching: MET.** B (box1, batches of 8 consecutive windows, left padding with attention mask, one thread) differs from R at **4** of
  1,664,964 positions = **2.4025 per million**. One of the 4 starts from an exact fp32 tie in R (w1302/p143); **without that flip, (b) is 3 flips =
  1.8018 per million**, still met on both thresholds.
- **Reference run.** R is a single run. At w3334/p101 (one of the 4 B flips and one of the 3 X flips) R is the odd one out: see "Exact ties and the
  reference run".
- All registered cells exist and are complete, so the bar can be scored now. Nothing in the bar waits on a missing cell
  (see "Cells registered and cells missing").
- What "MET" means here, and what it does not: the registered rule is a count rule. It was satisfied. It is not a significance
  test that the true rate is at least 1 per million. The one-sided exact 95 % lower bounds are 0.4911 per million (X) and
  0.8206 per million (B), both under 1, so these samples do not exclude a true rate under 1 per million.

## The bar, quoted exactly from the ledger

> Why: sv-5b/sv-5c found 0 token differences in 200 runs of 256 tokens, but the logits do move (up to 9e-5) and only 2 of 51,200 steps had a top-1 minus top-2 margin that small, so those runs could not measure a rate of a few per million. Setup: clean SmolLM2-135M checkpoint of sv-5, fp32, pinned sv-5 stack. 8,000 text windows from UltraChat conversations taken from the end of the sv-5 shuffled order (no overlap with the sv-5 prompts), each cut to a length drawn with a fixed seed from 160..256 tokens (about 1.66 million positions). One full forward pass per window; at every position record the argmax next token and the top-1 minus top-2 logit margin. Reference R = box1 (AVX2), one window at a time, one thread, all windows. X = other CPU class, one window at a time, one thread: box2 for windows 0-3,999, box3 for windows 4,000-7,999. B = box1, batches of 8 consecutive windows, left padding with attention mask, one thread, all windows. (x) cross-class MET only if X differs from R in the argmax token at 3 or more positions AND at a rate of at least 1 per 1,000,000 compared positions. (b) batching, own verdict, same rule for B against R. If a part is not met, the report states the count, the positions compared and the 95 percent upper bound on the rate. Reported without a bar: T = box1 two threads (windows 0-1,999), S = penguin same CPU class (windows 0-1,999), size of the margin shifts, the reference margin at each differing position, and the implied share of 256-token responses whose greedy output would differ. Prediction written before the run, from the sv-5c margins: 2 to 4 differing positions per million. Limits stated in advance: positions are teacher-forced on natural text, not greedy trajectories; a difference means a greedy decoder would emit a different next token at that context. Exact replay under the CIS-2 runtime is identical across these hosts by construction and by sv-5 measurement; it is not re-measured here.

Parts of the bar (paraphrase of the quoted text, numbered for reference):

1. **R** (reference) = box1 (AVX2), one window at a time, one thread, all 8,000 windows.
2. **(x)** cross-class: X = other CPU class, one window at a time, one thread; box2 for windows 0-3,999, box3 for windows 4,000-7,999. MET only if X differs from R in the
   argmax token at 3 or more positions AND at a rate of at least 1 per 1,000,000 compared positions.
3. **(b)** batching, own verdict, same rule for B against R (B = box1, batches of 8 consecutive windows, left padding with attention mask, one thread, all windows).
4. If a part is not met: report count, positions compared and the 95 percent upper bound on the rate (not needed here, both are met; the upper bounds are in the table anyway).
5. Reported without a bar: T = box1 two threads (windows 0-1,999); S = penguin, same CPU class (windows 0-1,999); size of the margin shifts; the reference margin at each
   differing position; the implied share of 256-token responses whose greedy output would differ.
6. Registered prediction (from the sv-5c margins): 2 to 4 differing positions per million.
7. Stated limits: teacher-forced natural text, not greedy trajectories; exact replay under CIS-2 is not re-measured here.

## Data and method

- Windows: `windows.jsonl` sha256 `20c94006e05d6b86...` (every host's sidecar JSON carries the same value), 8,000 windows of 160 to 256 tokens (mean 208.12), 1,664,964
  positions in all. UltraChat 200k `train_sft`, taken from the end of the sv-5 shuffled order.
- Stack on every host (sidecar JSON): torch 2.10.0+cpu, transformers 5.0.0, `torch.use_deterministic_algorithms(True)`, fp32, SmolLM2-135M. Per position the script records the
  index of `torch.topk(logits, 2)[0]` (called "argmax" below), the second index and the fp32 margin top-1 minus top-2.
- Comparison: `state/reports/sv5d/2026-10-03-sv5d-compare.json` from `sv5d_compare.py` (the loader that reads each npz array once). Chunk files `*.cN.npz` are excluded.
- Independent recount: `state/reports/sv5d/2026-10-03-sv5d-recount.py` with its output `state/reports/sv5d/2026-10-03-sv5d-recount.out` (both are in the record
  command's file list, so the ledger hashes them; the `.out` was produced on 2026-10-03 at 07:43Z and ends `ALL CHECKS PASS`, exit status 0). It does not import
  `sv5d_compare.py`. It reads each npz array once under `systemd-run --user --pipe -p MemoryMax=1500M -p MemorySwapMax=0` (peak 256 MB) and checks the sidecar window
  hash, window range and token count of every file, that window lengths equal those in `windows.jsonl` (total 1,664,964), and that R covers windows 0-7,999 with no gaps.
  It reproduces the compare JSON for all 7 pairs: window counts, position counts, flip counts, every flip's window, position, token ids and margins, and the
  margin-shift statistics. It confirms that penguin's margins are bit-identical to R's on all 1,664,964 positions, and that the sha256 of R's argmax ids over windows 0-1,999 is
  `f8e8cd4b4a22b5c66e02eaa283d098740a483d83c079fc622b8451c46f6ee450`, equal to the value printed by penguin's own job in `sv5d/leg-penguin/RESULT.txt`.
  The pooled X row, the one-sided lower bounds, the two-sided intervals, the penguin all-window bound, the near-tie counts, the exact ties in non-reference runs and the
  strictness of the flips are printed by this script (they are not in the compare JSON). The verifier's own separate script (scipy beta quantiles, not kept) is REPORTED to
  have matched the statistics; that is a second author's check, not part of the evidence files.
- Host identity, read live 2026-10-03 about 07:39Z on penguin, box1, box2 and box3 (sha256): `model.safetensors`
  `80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1`, `config.json` `1d556eab73b69c7f11f64c557a2f9c6f440bd4c6b89bb2584a6b498c92603843`,
  `argmax_scan.py` `9f89c8a68ecfee19e3c8ef54f54eebca970eaf39276ea33551c1da017de19f0e`, `windows.jsonl` `20c94006e05d6b86e52cf92443bc3118cc8c3c2c70cb98c2671823f7b5dafe61`,
  `long_rerun.py` `f96fd0a0...`, `long_rerun_batched.py` `e252843b...` are identical on all four hosts. box3's checkpoint hash was read on box3 itself after it came back and equals box1's.
  Package versions (torch 2.10.0+cpu, transformers 5.0.0) come from each run's sidecar JSON, not from a fresh import.
- Order of events: the bar was registered 2026-10-02T11:50:07Z; `windows.jsonl` has mtime 11:53:55Z on penguin, box1 and box3; the `started` record is 11:56:06Z; the earliest
  surviving result file on any host is penguin w0-1999 (npz mtime 12:42:36Z; box1, box3 and box2 files are dated 16:00Z, 16:21Z and 19:20Z or later).

### CPU class of each host

| host | CPU (sidecar JSON) | class in this programme | source |
|---|---|---|---|
| box1 | Intel Core i5-5200U @ 2.20 GHz | cpu-avx2 (R) | `SV5-PROTOCOL.md` Amendment 1; flags re-read live 2026-10-03 07:39Z: ssse3 fma sse4_2 avx avx2 |
| penguin | Intel Core i5-10210U @ 1.60 GHz | cpu-avx2 (same class as box1) | Amendment 1 and sv-5c; flags re-read live 2026-10-03 07:39Z: ssse3 fma sse4_2 avx avx2 |
| box2 | Intel Celeron N4020 @ 1.10 GHz | cpu-scalar (no AVX2) | Amendment 1; flags re-read live 2026-10-03 07:39Z: ssse3 sse4_2, no avx |
| box3 | Intel Celeron N4020C @ 1.10 GHz | cpu-scalar (no AVX2), same class as box2 | Amendment 1 and sv-5c; flags read live over ssh 2026-10-03 07:39Z (`grep -m1 flags /proc/cpuinfo`): ssse3 sse4_1 sse4_2, no avx, no avx2, no fma |

## Results: cell table

Positions compared are the positions of the windows both runs hold. "Upper 95" is the one-sided exact Clopper-Pearson 95 % upper bound on the per-position rate, per million (as computed by
`sv5d_compare.py`; for the pooled row, the lower bounds and the two-sided intervals by the same bisection in `2026-10-03-sv5d-recount.py`, which the script checks against the compare JSON's upper bounds and P(>=1 flip in 256) on all 7 cells where both exist). P(>=1 in 256) = 1 - (1 - rate)^256 and the same at the upper bound, both treating positions as
independent with one common rate.

| cell | role | windows | positions | flips | rate per million | upper 95 per million | P(>=1 flip in 256 tokens) | same at upper 95 |
|---|---|---|---|---|---|---|---|---|
| **B: box1 B8T1, w0-7999** | registered (b) | 8000 | 1,664,964 | 4 | 2.4025 | 5.4977 | 0.0006148 | 0.001406 |
| **X pooled: box2 B1T1 w0-3999 + box3 B1T1 w4000-7999** | registered (x) | 8000 | 1,664,964 | 3 | 1.8018 | 4.6569 | 0.0004612 | 0.001191 |
| &nbsp;&nbsp;box2 B1T1, w0-3999 (part of X) | part of (x) | 4000 | 833,394 | 2 | 2.3998 | 7.5544 | 0.0006142 | 0.001932 |
| &nbsp;&nbsp;box3 B1T1, w4000-7999 (part of X) | part of (x) | 4000 | 831,570 | 1 | 1.2025 | 5.7047 | 0.0003078 | 0.001459 |
| T: box1 B1T2 (two threads), w0-1999 | reported, no bar | 2000 | 416,030 | 1 | 2.4037 | 11.4026 | 0.0006152 | 0.002915 |
| S: penguin B1T1, w0-1999 | reported, no bar | 2000 | 416,030 | 0 | 0.0000 | 7.2007 | 0 | 0.001842 |
| extra: penguin B1T1, w2000-7999 | extra, no bar | 6000 | 1,248,934 | 0 | 0.0000 | 2.3986 | 0 | 0.0006139 |
| extra: box3 B8T1, w4000-7999 | extra, no bar | 4000 | 831,570 | 2 | 2.4051 | 7.5710 | 0.0006155 | 0.001936 |

Penguin over all 8,000 windows (registered cell plus extra): 0 flips in 1,664,964 positions; the upper 95 % bound is 1.7993 per million (from the recount output, not in the compare JSON).

Implied share of 256-token responses (point estimates, same assumptions): B 0.06148 % (about 1 in 1,626 responses); X pooled 0.04612 % (about 1 in 2,168). At the
upper 95 % bounds: B 0.1406 % (1 in 711), X 0.1191 % (1 in 839).

Two-sided exact 95 % intervals for context (recount output): X 0.3716 to 5.2657 per million; B 0.6546 to 6.1512 per million.

### Size of the margin shifts (reported without a bar)

| cell | largest abs shift of the margin | mean abs shift | positions whose margin is not bit-identical to R |
|---|---|---|---|
| box1 B8T1 (all 8000) | 0.0001106 | 4.389e-06 | 74.23 % |
| box1 B1T2 (w0-1999) | 6.676e-05 | 4.072e-06 | 74.74 % |
| box2 B1T1 (w0-3999) | 9.727e-05 | 7.048e-06 | 91.47 % |
| box3 B1T1 (w4000-7999) | 0.0001373 | 7.063e-06 | 91.52 % |
| box3 B8T1 (w4000-7999, extra) | 0.0001392 | 7.174e-06 | 91.64 % |
| penguin B1T1 (w0-1999) | 0 | 0 | 0.00 % |
| penguin B1T1 (w2000-7999, extra) | 0 | 0 | 0.00 % |

### Every differing position, with margins

Each margin in this table is an fp32 value and an integer multiple of 2^-20 = 9.5367e-07. "Gap change" = ref_margin + other_margin, the movement of the (ref top-1 minus ref top-2) logit gap,
because in every one of these positions the other run's top-1 is the reference's top-2 (all 10 listed flips are swaps of the two leading tokens; the recount counted them). The compare JSON lists
every flip (its cap of 200 was never reached).

| cell | window | position | R top-1 | R top-2 | R margin | other top-1 | other margin | gap change |
|---|---|---|---|---|---|---|---|---|
| B | 274 | 144 | 2166 | 2364 | 1.9073e-06 | 2364 | 7.6294e-06 | 9.5367e-06 |
| B | 1302 | 143 | 281 | 30 | 0 | 30 | 1.9073e-06 | 1.9073e-06 |
| B | 3334 | 101 | 1453 | 325 | 5.722e-06 | 325 | 1.9073e-06 | 7.6294e-06 |
| B | 5595 | 154 | 451 | 260 | 1.9073e-06 | 260 | 3.8147e-06 | 5.722e-06 |
| T | 274 | 144 | 2166 | 2364 | 1.9073e-06 | 2364 | 7.6294e-06 | 9.5367e-06 |
| X/box2 | 3334 | 101 | 1453 | 325 | 5.722e-06 | 325 | 7.6294e-06 | 1.3351e-05 |
| X/box2 | 3687 | 106 | 282 | 739 | 3.8147e-06 | 739 | 9.5367e-06 | 1.3351e-05 |
| X/box3 | 6300 | 248 | 550 | 805 | 1.9073e-06 | 805 | 4.7684e-06 | 6.6757e-06 |
| extra box3 B8T1 | 5595 | 154 | 451 | 260 | 1.9073e-06 | 260 | 2.861e-06 | 4.7684e-06 |
| extra box3 B8T1 | 6300 | 248 | 550 | 805 | 1.9073e-06 | 805 | 4.7684e-06 | 6.6757e-06 |

Distinct (window, position) pairs among the registered cells: B has 4 (w274/p144, w1302/p143, w3334/p101, w5595/p154) and X has 3 (w3334/p101, w3687/p106, w6300/p248), of which
w3334/p101 is shared, so 6 distinct positions in all. Other repeats: w274/p144 flips in both box1 B8T1 and box1 B1T2; w5595/p154 in box1 B8T1 and box3 B8T1; w6300/p248 in box3 B1T1 and box3 B8T1.
So the counts of different variants are not independent draws.

Where the flips sit in R's own margin distribution (recount): R has 1 exact fp32 tie (margin 0.0), 12 positions with margin under 1e-5 and 123 under 1e-4, out of 1,664,964. All
4 B flips and all 3 X flips are among the 10 positions where R's margin is at most 5.722e-06. B flipped 4 of those 10 and X flipped 3 of those 10; no position with R margin above 5.722e-06 flipped in any
registered cell. The rate estimate therefore rests on a small set of near-ties.

### Exact ties and the reference run

Source for this subsection: the recount output (section "Near-tie positions, run by run" and the per-cell tie lines).

- **Exact fp32 ties also occur in non-reference runs.** box2 B1T1 has two (w677/p168 and w3279/p116) and T (box1 two threads) has two (w677/p168 and w1302/p143); penguin has the same
  tie as R at w1302/p143. In each non-reference case the run's recorded top-1 (`torch.topk` index 0) is the same token as R's top-1, so none of them is counted as a flip. R's own margin at
  those positions is 5.722e-06, 3.8147e-06, 5.722e-06 and 0. A different tie-break could only add flips there, never remove one: for X it could add up to 2 (both ties are in box2's registered cell).
- **The 3 X flips are strict on both sides.** R margin above 0 (5.722e-06, 3.8147e-06, 1.9073e-06) and the run's own margin above 0 (7.6294e-06, 9.5367e-06, 4.7684e-06), so X is at least 3 whichever way
  exact ties are broken. The same holds for 3 of the 4 B flips; the exception is w1302/p143, where R's margin is exactly 0.
- **The one tie in R (w1302/p143) cuts both ways, read from the recorded margins.** B prefers token 30 there by 1.9073e-06 and box2 prefers token 281 by 3.8147e-06, while R's recorded token is 281. If R's tie
  had been broken the other way (token 30), the position would leave B (3 flips) and join X (4 flips). Either way both parts are met: as recorded X = 3 and B = 4; with the other tie-break X = 4 and B = 3.
  This is an inference from the margins; the opposite tie-break was not run.
- **R is the odd one out at w3334/p101.** R and penguin (bit-identical to R everywhere) prefer token 1453 by 5.722e-06. The two other configurations that hold this window both prefer token 325: box1 B8T1 by 1.9073e-06
  and box2 B1T1 by 7.6294e-06. This one position supplies 1 of the 4 B flips and 1 of the 3 X flips, and it is a flip only relative to the single reference run. At w274/p144 the pattern differs: R, penguin and box2
  agree (box2 by 1.1444e-05) and the two box1 variants B8T1 and T both prefer token 2364 by 7.6294e-06. R has no repeat, so which run is "right" at these near-ties is not something this experiment can say.

## Cells registered and cells missing

| cell | registered by the bar? | state |
|---|---|---|
| R box1 B1T1 w0-7999 | yes | complete (8,000 windows, 2 parts, 1,664,964 positions) |
| X box2 B1T1 w0-3999 | yes | complete (2 parts) |
| X box3 B1T1 w4000-7999 | yes | complete (2 parts); box3 was unreachable from about 06:00Z to about 07:20Z while thrashing (REPORTED in the scoring and verifier notes; load average 15-23) and is back (read live 07:39Z, load 2.2); this data was already on penguin |
| B box1 B8T1 w0-7999 | yes | complete (1 part, 8,000 windows) |
| T box1 B1T2 w0-1999 | yes (no bar) | complete |
| S penguin B1T1 w0-1999 | yes (no bar) | complete; penguin w2000-7999 also done (extra) |
| box3 B8T1 w4000-7999 | no (extra, no bar) | complete, in the compare file |
| box2 B8T1 w0-3999 | no (extra) | per box2's own directory it finished at 2026-10-03 06:41Z (`p0of1.npz` 5,616,405 bytes, `seconds` 26604.7), but it has not been copied to penguin; the local copy holds only an older log (13 chunks). It is not in the compare file. The dispatch note that it never finished is out of date |
| box2 B1T2 w0-3999 | no (extra) | running on box2 (job started 06:59Z; two 250-window chunks done, the second at 07:30:53Z; read live 07:39Z) |
| box3 B1T2 w4000-7999 | no (extra) | running on box3 (process started 04:58Z; read live 07:39Z): two 250-window chunks done, chunk 0 at 05:11:36Z (67.9 tok/s) and chunk 1 at 07:27:32Z (11.5 tok/s, while box3 was thrashing); the local copy on penguin holds only the first chunk's log, whose 00:11 mtime is CDT = 05:11Z |

The bar names exactly five variant cells (R, X, B, T, S). The ledger `started` record likewise lists B1T2 for box1 only. The box2 and box3 B1T2 legs and the box2 B8T1 copy
are extras that the bar does not mention, so none of them can change the verdict; they can only add unregistered context. Scoring does not wait for them.

## Reasoning for the verdict

1. Cell existence: every cell named in the bar is present and complete (table above), and the compare JSON was reproduced by an independent recount.
2. (x): 2 flips (box2) + 1 flip (box3) = 3 positions out of 833,394 + 831,570 = 1,664,964. 3 is not less than 3, and 1.8018 per million is not less than 1 per million. MET.
3. (b): 4 positions out of 1,664,964 = 2.4025 per million. MET. Robust to dropping the one flip that starts from an exact tie (w1302/p143): the other 3 give 1.8018 per million, still meeting both thresholds.
   Robust the other way too: the 3 X flips are strict on both sides, so a different tie-break cannot remove one (see "Exact ties and the reference run").
4. Reading of X: the bar defines X as the composite (box2 for the lower half of the windows, box3 for the upper half) and asks for one verdict, so pooling is the literal reading. Taken host by host,
   box2 alone has 2 flips and box3 alone has 1; neither would reach 3. The bar does not ask for per-host verdicts, so this is noted and not used.
5. No validity problem found: identical windows hash and checkpoint hash on all four hosts (box3 read live after it came back), identical torch and transformers versions in the sidecars, bar registered before the start record, result files modified after the start record, ledger `verify` OK (94 records).
6. Verdict is `met`, not `inconclusive`: no registered cell is missing and the rule is deterministic given the counts.

## Against the registered prediction and sv-5c

- Prediction was 2 to 4 differing positions per million (3.3 to 6.7 expected positions in 1,664,964). Observed: B 2.4025 per million (4 positions, inside the range); X pooled 1.8018 per million (3 positions;
  the point estimate sits just under the lower end, the count is within what a rate of 2 per million would give). T 2.4037 per million (1 position).
- sv-5c saw 0 differing tokens in 200 runs of 256 tokens (51,200 steps). At 2.4 per million the expected number there is 0.12, so zero has probability 0.884; sv-5c and sv-5d are consistent.

## What this feeds, and what can and cannot be said

Feeds the claim in `2026-10-02-SV5-EXACT-REPLAY-VS-TOPLOC-VS-RERUN-R2.md` (Q2: a stock rerun on another CPU class judged on tokens, 0 of 200) and the question left open in
`2026-10-02-SV5C-BATCHING-THREADS.md` ("cannot tell never from a few per million").

Can be said, on SmolLM2-135M, fp32, this pinned PyTorch/transformers CPU stack, these windows:
- A stock one-pass rerun does not always reproduce the reference's next-token argmax: it differed at 3 of 1,664,964 positions when run on the non-AVX2 Celeron hosts, at 4 of 1,664,964 positions when run
  in batches of 8 with left padding, and at 1 of 416,030 positions with two threads (no bar). The same CPU class (penguin) differed at 0 of 1,664,964, with margins bit-identical.
- Every flip was a swap of the two leading tokens at a position where R's margin was at most 5.722e-06 (6 steps of 2^-20 = 9.5367e-07; the logits themselves were not stored, so their own fp32 spacing was not measured).
- Extrapolated with the independence assumption, that is on the order of 1 in 1,600 to 1 in 2,200 of 256-token responses (point estimates), with an upper 95 % bound of about 1 in 700 to 1 in 850.
- Consistent with sv-5 and sv-5c: such a flip is rare enough that 200 runs saw none.

Cannot be said:
- That the true rate is at least 1 per million with 95 % confidence (lower bounds are under 1); the estimate rests on 3 and 4 events concentrated on a few near-tied positions.
- That a real greedy decoder or a serving workload would show this rate: positions are teacher-forced UltraChat text, not greedy trajectories; the 256-token share assumes a constant, independent per-position rate;
  windows average 208 tokens.
- That batching in general causes the B result: this script left-pads with id 0 and passes no position ids, so the absolute positions of padded windows follow the padded index (as noted in sv-5c, padding mask versus position shift was not
  separated). B measures "batch 8, left padding, as implemented here".
- Anything about GPUs, larger models, sampling, mixed precision, other stacks or other CPU pairs (one reference box, one cross-class family).
- That exact replay is needed for tamper detection: sv-5 Q1 and Q2 still stand as recorded. What sv-5d adds is a measured, small, nonzero token-level disagreement of a stock rerun across CPU class and under batching.
  Exact replay under CIS-2 is identical across these hosts by construction and by the sv-5 measurement; it was not re-measured in sv-5d.

## Caveats

1. (x) is met at the minimum count (3): 2 flips on box2 and 1 on box3. One flip fewer in X would have made it not met. It relies on the bar's composite definition of X; neither host alone reaches 3.
2. The exact-tie flip (w1302/p143): the recorded "argmax" is `torch.topk` index 0, whose order on an exact fp32 tie is the implementation's choice, so R's token there is itself arbitrary. It counts under the bar's rule (the
   argmax token differs) and (b) stays met without it (3 flips, 1.8018 per million). Non-reference runs also have exact ties (box2 at w677/p168 and w3279/p116; T at w677/p168 and w1302/p143), none counted as a flip; the 3 X flips are
   strict on both sides, so (x) does not depend on tie-breaking. See "Exact ties and the reference run".
3. Single reference run R with no repeat of R itself in this experiment. Support for R being stable: penguin (same class) matches it bit for bit on all positions, and the sv-5c control was exact. R is the odd one out at w3334/p101
   (box1 B8T1 and box2 both prefer the other token), so one of the 4 B flips and one of the 3 X flips is a difference from R only.
4. The pooled X row, the lower bounds, the two-sided intervals, the penguin all-window bound and the near-tie counts are printed by `state/reports/sv5d/2026-10-03-sv5d-recount.py` (output in the `.out` next to it), which the record command hashes
   together with this report and the compare JSON.
5. box3 was unreachable from about 06:00Z to about 07:20Z (REPORTED in the scoring and verifier notes) and is back. Its CPU flags (ssse3 sse4_1 sse4_2, no avx, avx2 or fma) and its checkpoint, config, scan-script and windows hashes were read live at 07:39Z
   and match box1's, box2's and penguin's. box3's B1T1 data had been copied to penguin before it went down; the recount reads that copy. The earlier "00:11Z" label for box3's first B1T2 chunk was the local CDT mtime; it is 05:11Z.
6. Flips recur at the same few near-tied positions across variants, so the counts of different variants are not independent draws (6 distinct positions across the registered cells).
7. `cm-exp result` can be called only once per id and hashes the files given at that moment; edit nothing after recording.

## Command that would record it (not run)

Run from the repo root after this file is final; `cm-exp result` is single-use and hashes the four files at that moment. The summary is 556 characters.

```
( cd <root> && bin/cm-exp result sv-5d --verdict met --summary "sv-5d MET on both parts (registered count rule). (x) X (box2 w0-3999 + box3 w4000-7999) vs box1 R: 3 flips (2 box2, 1 box3; strict on both sides) of 1,664,964 = 1.8018/M (95% upper 4.6569); met at the minimum count of 3. (b) box1 B8T1: 4 flips = 2.4025/M (upper 5.4977); without the exact-tie flip w1302/p143: 3 flips, 1.8018/M. T 1/416,030; penguin 0/1,664,964. All flips swap the top two tokens at R margin <= 5.722e-06; R is the odd one out at w3334/p101. One-sided 95% lower bounds 0.49 and 0.82/M are under 1/M. Teacher-forced, SmolLM2-135M fp32, CPU." --file state/reports/2026-10-03-SV5D-PER-TOKEN-DIVERGENCE.md --file state/reports/sv5d/2026-10-03-sv5d-compare.json --file state/reports/sv5d/2026-10-03-sv5d-recount.py --file state/reports/sv5d/2026-10-03-sv5d-recount.out )
```
