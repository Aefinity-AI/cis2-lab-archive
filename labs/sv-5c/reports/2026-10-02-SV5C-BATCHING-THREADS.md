# sv-5c — does batching or thread count break a stock PyTorch rerun? Not at this sample size: both parts "no"

Date: 2026-10-02. Ledger id `sv-5c` (bar sha256 726cb42b…, registered before the script was run). Scripts:
cis2-spec archive branch `cm/sv5-harness`@a241d53 (`experiments/sv5/long_rerun_batched.py`, `jobs/sv5c.sh`). Raw
analysis: `state/reports/sv5c/` (`box1_analysis.json`, `box2_analysis.json`, `margin_shifts.json`, RESULT files).

## Setup

Clean SmolLM2-135M checkpoint of sv-5, the 200 TEST prompts, 256 greedy tokens, no stop, fp32, pinned stack.
Reference = the sv-5b rows of box1 (one prompt at a time, one thread). Variants on box1: batches of 8 prompts in
file order with left padding and attention mask (B8T1), two threads (B1T2), both (B8T2). 174 of the 200 prompts
were padded in the batched runs. The script passes no position ids, so in a padded batch the absolute position of
a prompt's tokens follows the padded index (relative positions are unchanged); whether that or the padding mask
causes the small logit shifts was not separated.

## Result

| variant (host) | prompts whose 256 tokens differ from the reference | steps whose top-1 minus top-2 margin differs | largest margin shift |
|---|---|---|---|
| control: batched code, batch 1, one thread (box1, 20 prompts) | 0 of 20 | 0 of 5,120 | 0 |
| B8T1 (box1) | 0 of 200 | 45,487 of 51,200 | 9.2e-5 |
| B1T2 (box1) | 0 of 200 | 11,724 of 51,200 | 4.0e-5 |
| B8T2 (box1) | 0 of 200 | 45,642 of 51,200 | 9.2e-5 |
| B8T1 (box2, other CPU class; no bar) | 0 of 200 | 46,467 of 51,200 | 8.2e-5 |

The control holds on box1 (tokens and margins equal to the reference) and on box2 (tokens equal to the reference;
margins equal to box2's own one-at-a-time rows, not to box1's, as expected for another CPU class).
**Batching: no. Threads: no.** (Registered rule: "yes" needs at least 1 of 200 prompts to
differ.)

## Why this is not the end of the question

Batching, a second thread and another CPU class all move the logits a little (mean shift of the margin about
1e-6 to 7e-6, largest about 9e-5), on most steps. They did not change a token because near-ties are rare: in the
51,200 reference steps only 2 margins are below 1e-4 (1.1e-5 and 3.3e-5) and 12 are below 1e-3. With shifts of
that size, a rough estimate from the density of small margins and the mean shift gives well under one expected
difference in the 200 runs (of the order of 0.1). So this run bounds the rate loosely (0 in 51,200 steps: below about 59 per million with
95 % confidence, per variant); it cannot tell "never" from "a few per million tokens". Experiment sv-5d measures
that rate directly on 1.66 million positions.

Also seen: penguin and box1 (both AVX2) agree bit for bit on every margin of all 51,200 steps; box2 and box3 (same
Celeron class) have the same shift statistics against box1 as each other. Stock PyTorch was bit-reproducible
within a CPU class here and not across classes, as in sv-5 and sv-1.

## What can and cannot be said

- Can be said: on this model and these hosts, a verifier that reruns one request at a time with stock PyTorch got
  the provider's exact 256 tokens in 200 of 200 cases even when the provider batched 8 requests with padding, used
  two threads, or ran on another CPU class.
- Cannot be said: that this holds for every response at scale (see the rate argument above), for GPUs, for larger
  models, for sampling, or for mixed-precision serving.
- Consequence for the exact-replay claim: together with sv-5 and sv-5b, the evidence so far does not show a case
  where a stock rerun fails on tokens and exact replay is needed for that reason. What exact replay adds on these
  hosts is equality of the hidden state and logits themselves (digests), which a stock rerun does not give across
  CPU classes (sv-5). Note the favourable conditions for the rerun here: the verifier had the provider's exact
  weights and software stack. The per-token rate is being measured in sv-5d.
