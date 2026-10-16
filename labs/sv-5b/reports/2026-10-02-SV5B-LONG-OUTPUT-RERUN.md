# sv-5b — 256-token outputs: a stock PyTorch rerun on another CPU class still gives the same tokens: not met

Date: 2026-10-02. Ledger id `sv-5b` (bar sha256 50a98704…, registered 08:06Z before the scripts were run).
Scripts: cis2-spec archive branch `cm/sv5-harness`@42a61d6 (`experiments/sv5/long_rerun.py`, `jobs/sv5b_*.sh`);
analysis `sv5b_analyse.py` (@a241d53). Raw: `state/reports/sv5b/` (`sv5b_analysis.json`, RESULT files).

## Setup

Clean SmolLM2-135M checkpoint of sv-5, the 200 TEST prompts, 256 greedy tokens, no stop, one prompt at a time, one
thread, fp32, pinned stack. Provider box1 (AVX2). This is the follow-up to the main limit of sv-5 (32 tokens).

## Result

| check | result |
|---|---|
| (i) stock rerun on box2 (Celeron, no AVX) against box1 | 0 of 200 prompts differ |
| (i) stock rerun on box3 (Celeron, no AVX) against box1 | 0 of 200 prompts differ |
| stock rerun on penguin (AVX2, no bar) against box1 | 0 of 200 differ; all 51,200 margins bit-identical |
| (ii) exact replay (CIS-2 C driver): penguin against box5 (Pentium T2310, SSSE3) | rows equal 200 of 200 (tokens, witness digest, argmax digest) |
| (ii) exact replay on box4 (Sempron, SSE3) | not yet run (queued behind another job) |
| exact-replay tokens against the PyTorch tokens of box1 (no bar) | equal 200 of 200 |

**Verdict: not met.** The bar needed both parts; part (i) needed at least one differing prompt and shows none, so
the verdict follows from (i) alone. A stock rerun with a token comparison is still enough at 256 tokens on these
hosts. Part (ii) is incomplete: its box4 run is outstanding (it cannot change the verdict) and will be added to
the raw files when done; until then the exact-replay equality at 256 tokens is shown for penguin and box5 only.
The box5 rows carry no host field; the host is taken from the job's result file.

108 of the 200 reference outputs end in a repeating loop (last 64 tokens periodic with a period of at most 32
tokens; the count depends on that definition), which makes late divergence
less likely than in varied text.

Seconds per prompt (median, descriptive): stock rerun box1 23.7, box2 68.6, box3 67.9, penguin 16.5; exact replay
penguin 51.5, box5 96.2.

## What can and cannot be said

- Can be said: for this model with greedy decoding on CPUs, lengthening the output from 32 to 256 tokens did not
  produce a single token difference between a stock rerun on an AVX2 CPU and on Celerons without AVX.
- The logits themselves do differ across CPU classes on most steps (see sv-5c: shifts up to about 9e-5); tokens
  stayed equal because near-ties are rare (2 of 51,200 steps with a margin under 1e-4). The per-token rate is
  measured in sv-5d.
- Cannot be said: that exact replay is needed to verify tokens here. It was not. Its measured extras remain those
  of sv-5: equality of digests across CPU classes, and detection of weight changes that do not change the tokens.
- Limits: one small model, greedy, CPUs, 200 prompts, single run per host.
