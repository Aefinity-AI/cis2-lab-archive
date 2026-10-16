# SV-5 protocol — exact replay vs tolerance fingerprint vs stock rerun

Status: FROZEN 2026-10-01 by Fable (ledger id `sv-5`, `bin/cm-exp show sv-5` holds this file's sha256).
A change after the freeze is a dated amendment at the end of this file, written before the affected data is
looked at. Draft and the three reviews it went through: workflow wf_fe6b438f-905 (2026-10-01); the review
points are folded in below and listed in §10.

Source of the question: `state/reports/2026-10-01-AI-SAFETY-LANDSCAPE-AND-CIS2.md` §5 E1.
Facts about the rival methods: `state/reports/2026-10-01-SV5-RESEARCH.md` (TOPLOC arXiv 2501.16007, DiFR arXiv
2511.20621, Cankaya arXiv 2606.00279).

## 1. Question and scope

A provider says: "I ran model M on prompt P and the output was O." A verifier holds M, P, O and a small
commitment sent by the provider, and checks the statement on another machine.

Scope of the threat model: an **undisclosed deviation by a provider who commits to what it actually ran**
(wrong or damaged weights, a quantised copy, a changed prompt). A provider who computes an honest-looking
commitment separately from what it serves is out of scope for every arm, and no result here is a statement
about resistance to such a provider.

Arms (same weights file, same prompts, same tampers):

| arm | provider runs | provider sends | verifier does | accept rule |
|---|---|---|---|---|
| A | CIS-2 runtime (CPU) | receipt digests + token ids | CIS-2 replay of the claimed M, P | witness digest, argmax digest and token ids all equal |
| B | stock PyTorch | TOPLOC proofs + token ids | prefill of claimed M, P, O; TOPLOC verify | TOPLOC threshold rule (§5) |
| B+ | as B | as B | as B, plus its own greedy rerun | B accepts and the rerun's token ids equal O |
| C-tok / D-tok | stock PyTorch | token ids | greedy rerun | token ids equal |
| C-hash / D-hash | stock PyTorch | token ids + sha256 of the hidden-state bytes | greedy rerun | tokens and hash equal |

C = verifier on the same host class as the provider; D = verifier on another host class.
DiFR is not an arm: it publishes no fixed threshold, its code path needs vLLM on a GPU, and at temperature 0
its token method is an argmax check (covered by B+ and the tok arms).

What the arms need from the provider differs, and this is part of the result: A needs the provider to serve
with the CIS-2 CPU runtime; B, C and D check ordinary PyTorch serving. A cannot check a stock GPU run at all.

## 2. Model, prompts, generation

- Model M: `HuggingFaceTB/SmolLM2-135M`, the bf16 safetensors pinned by the CIS-2 v0.3b vector
  (hidden size 576, 30 layers). CIS-2 reads bf16 checkpoints only, so every tamper is defined on the bf16
  checkpoint and the same tampered checkpoint is loaded by all arms. PyTorch arms compute in fp32.
- Prompts: UltraChat first user turns, shuffled with seed 20261001; a prompt is kept if it has 8 to 64 tokens
  under the SmolLM2 tokenizer (Hugging Face tokenizer). First 100 kept = CALIBRATION, next 200 = TEST.
  The token-id file is the single source of prompts for every arm (the CIS-2 driver reads ids, not text);
  its sha256 goes into the ledger before any arm runs. Fallback if UltraChat is not usable: the same rule on
  `HuggingFaceFW/fineweb-edu` sample-10BT first sentences, recorded before any arm runs.
- Generation: greedy, 32 new tokens, batch size 1, no padding, no system prompt, no chat template, KV cache on.

## 3. Tamper classes

Applied on the provider side; the provider still reports the clean M (clean weights hash) and P, so detection
in arm A rests on the computed values, not on the file hash. One tampered run per TEST prompt per class.
Random choices use seed 20261001 + class index. Weight tampers are built once per class (per prompt for W1–W3,
as in-memory patches) and re-rounded to bf16 (round to nearest even); the fraction of weights changed is reported.

| id | class | definition |
|---|---|---|
| N0 | identity (negative control) | a bit flipped twice; must be accepted by every arm |
| W1 | one low bit | flip bf16 bit 0 of one weight, drawn uniformly over all 2-D tensors, new draw per prompt |
| W2 | one high mantissa bit | flip bf16 bit 6 of one such weight |
| W3 | one exponent bit | flip bf16 bit 7 of one such weight |
| L1 | low-rank update 1e-4 | add `eps·‖W‖_F·u vᵀ` (u, v random unit vectors) to `q_proj` and `v_proj` of every layer, eps = 1e-4 |
| L2 | low-rank update 1e-3 | same, eps = 1e-3 |
| L3 | low-rank update 1e-2 | same, eps = 1e-2 |
| Q1 | int8 per row | symmetric int8 quantise and dequantise of every 2-D weight, one scale per output row |
| Q2 | int8 per tensor | same, one scale per tensor |
| Q3 | int4 per row | symmetric int4, one scale per output row |
| P1 | last prompt token changed | last prompt token id replaced by (id + 1) mod vocab |
| P2 | first prompt token changed | first prompt token id replaced the same way |
| P3 | prepend (positive control) | a fixed instruction sentence in the style of TOPLOC's system-prompt test is prepended; a length mismatch counts as a reject in arm B |
| S1 | sibling weights (positive control) | weights of `SmolLM2-135M-Instruct` (converted to bf16 if needed) |
| O1 | output token edit (scope contrast) | provider runs clean M, P and reports O with token 16 replaced by the second-ranked token; TOPLOC states sampling is out of its scope; reported as a scope contrast, not as a detection rate |
| V1 | benign variation (clean side, arms B, C, D only) | verifier uses all CPU threads instead of one; a clean run, counted as a false alarm if rejected |

**Output-changing** is defined once, for all arms: the PyTorch provider run on box1 gives different 32 greedy
tokens for the tampered run than for the clean run of the same prompt. The same per-prompt set is used for
every arm. The count under the CIS-2 runtime is also reported.

## 4. Hosts, pairs, software

| host | class | role |
|---|---|---|
| box1 (x86-64, AVX2) | cpu-avx2 | provider for every arm; verifier |
| box3 (x86-64, AVX2, other CPU model) | cpu-avx2 | verifier: the **same-class pair** box1→box3 |
| box2 (x86-64, no AVX2) | cpu-scalar | verifier: the **cross-class pair** box1→box2 |
| Kaggle CPU kernel | cpu-cloud | verifier, extra row |
| Kaggle T4, Lightning T4 | gpu-t4 | extra rows for B, C, D only (T4 provider and verifier); dropped if not available by 2026-10-10 |

- The two named CPU pairs decide the bar. All other pairs are extra rows. Arm A's tampered provider runs may
  be computed on penguin as well, after the clean cross-host equality of arm A has been shown on the pairs.
- PyTorch arms: one pinned stack on every host (torch, transformers, tokenizers, numpy versions in the ledger
  before the first run), `torch.use_deterministic_algorithms(True)`, one CPU thread (except V1). Step 0 is a
  smoke test of the pinned stack on box1, box2, box3 and a Kaggle CPU kernel; a host that fails is dropped and
  the drop recorded, not replaced by a looser stack. box4 and box5 (no SSE4) run arm A only, as extra rows.
- Arm A: a driver around `cis2_run_decode` from cis2-spec `verify3` (private branch on the archive remote):
  reads a token-id file, 32 new tokens, takes the claimed weights hash as an argument, applies in-memory
  weight patches, single run (the built-in double-run determinism loop is replaced by the cross-host check).
  The pinned v0.3b vector must still give the pinned digests through the driver (unit test).
- Hidden state for arms B and C/D-hash: the last hidden state after the final norm. Hash = sha256 of the fp32
  little-endian bytes in forward-call order (prefill `[L,576]`, then each decode step `[1,576]`).
- TOPLOC: package `toploc` 0.1.6, unmodified, k = 128, one prefill proof and one decode proof (32 tokens).
  The library accepts bf16 activations only, so the hidden state is cast to bf16 on both sides. The library
  returns a count of exponent mismatches; unit test before any data: identical tensors give 0 mismatches.

## 5. Decision rules for arm B

Reject if `exp_mismatch > T_exp` or `mean(mantissa_err) > T_mean` or `median(mantissa_err) > T_median` on any
proof of the run. Threshold sets, reported side by side:
- **B-pub**: the paper's bf16 values 38 / 10 / 8. Reported only; published for 8B to 70B models.
- **B-cal**: per provider→verifier pair, each threshold = the largest value seen on that pair's 100
  CALIBRATION clean checks (zero calibration alarms). This is the set used by the bar.
- **B-cal-2x**: twice the B-cal values. Reported only.

## 6. Measurements

Per arm and host pair: rejects among the 200 TEST clean checks (and V1). Per arm, class and pair: rejects among
output-changing runs and, separately, among runs that do not change the output; for A against B-cal also the
paired counts (A only, B only, both, neither). Rates carry counts and Wilson 95% intervals; the same 200
prompts are reused across classes, so intervals are per class and not independent between classes. An exact
McNemar p-value is given for each paired comparison as description. Also recorded without a claim:
commitment bytes and verifier wall time per run.

## 7. Bar (three questions, rules fixed now)

Primary classes are named now: for Q1 **L2, Q1, P1**; for Q3 **W2, W3, L1**. Deciding pair for Q1 and Q3:
box1→box3. Deciding pair for Q2: box1→box2. A class counts as "yes" if the stated runs are at least 5 and at
least 10% of the runs of that kind in the class.

- **Q1 (E1 first half as written).** Among output-changing runs, are there runs that A rejects and B-cal
  accepts? Yes if at least 2 of the 3 primary classes count as yes, and A's TEST clean rejects on the pair are
  not more than B-cal's.
- **Q2 (E1 second half, judged on tokens).** Does a stock greedy rerun on another host class reject clean
  runs that A accepts? Yes if D-tok rejects at least 1 of the 200 TEST clean checks on box1→box2 and A rejects
  none there. The D-hash result is reported next to it and does not decide Q2.
- **Q3 (changes that leave these 32 tokens unchanged).** Among runs that are not output-changing, are there
  runs that A rejects and B-cal accepts? Same counting rule as Q1. Such a reject shows that the weights or the
  arithmetic differed from the claim; it is not evidence of a harmful output.

**E1 bar met** only if Q1 = yes and Q2 = yes. In every other case it is **not met**, and the report says
which rival tied: if Q2 = no, a stock rerun with a token check already matches A on output-changing tampers
at this scale (B+ and D-tok reject every output-changing run by construction when the rerun reproduces), and
what remains for A is Q3 and the commitment. Q3 is reported as its own finding either way.
If arm A rejects any clean check, the run stops and the cause is investigated first: that would be a CIS-2
defect.

Departures from the E1 text, stated here before any run: "matched false-alarm rate" is replaced by the
zero-calibration-alarm rule (B-cal's TEST false alarms are measured, not assumed equal to A's); "at least 5%
of one class" is replaced by the stricter named-class rule; the stock-rerun half is judged on tokens.

Outcomes are reported as measured. Whether a tie or loss is published outside the company is the owner's
decision (NEEDS §00b); the internal report is written either way.

## 8. Order of work

0. Stack smoke test on the hosts; versions into the ledger. 1. Build the harness and the CIS-2 driver in
private branches; unit tests (tamper functions, driver reproduces the pinned vector, TOPLOC convention, N0).
2. Prompt token-id file hash into the ledger. 3. CALIBRATION clean runs → B-cal thresholds into the ledger.
4. TEST clean runs and tamper runs. 5. Report `state/reports/…-SV5-RESULT.md`, `bin/cm-exp result sv-5`.
No TEST value is looked at before step 3 is in the ledger. Cut order if box time runs short: GPU pairs,
Kaggle CPU pair, then classes Q2, P2, L3. The two named pairs and the six primary classes are never cut.
Compute: boxes, penguin and free Kaggle/Lightning quota. No spending.

## 9. Limits (repeated in the report)

- One 135M model, greedy, 32 new tokens. A tie or loss here says little about 8B models or production serving.
- A is a CPU runtime; B, C, D verify ordinary PyTorch serving. The comparison is not like-for-like serving, and
  nothing here measures what serving with CIS-2 costs a provider.
- A's commitment covers the full logits of every step; B's covers the top 128 of the last hidden state. The
  arms differ in commitment strength as well as in exactness.
- TOPLOC outside its published range: hidden size 576 makes k = 128 about 22% of the vector (about 3% at 4096);
  2 proofs per run against 17 in the paper; bf16 cast of fp32 activations; thresholds recalibrated by us.
- B-cal is not a matched false-alarm rate: zero alarms on 100 calibration checks still allows TEST alarms.
- The tamper list is ours and concentrates on small changes, where exact replay is expected to differ from a
  tolerance check. It is not a neutral sample of attacks. P3 and S1 are controls every arm should flag.
- Non-adaptive provider only (§1).

## 10. Review points adopted (2026-10-01)

Named primary classes instead of best-of-13; one output-changing definition for all arms; B-cal per pair;
token-only stock arms and B+; bar decided on CPU pairs; tampers on bf16 bits; Q classes replaced (fp16/bf16
round trips are no-ops on a bf16 checkpoint); TOPLOC bf16 cast and mismatch-count convention; driver for
arm A with claimed-hash argument; negative control N0; benign variation V1; hash byte definition; limits list.
Not adopted: Holm correction (the rule is a count rule on named classes, p-values are descriptive);
a sibling-size model class (hidden size differs, every arm would reject on shape).

## Amendment 1 (Fable, 2026-10-01 18:30Z) — written after the step 0 smoke test, before any calibration or TEST data

Reason: step 0 (2 calibration prompts per host, clean model, no tamper) showed that the host table of §4 was wrong.
box3 (Celeron N4020C) has no AVX2. Measured on those 2 prompts: box1 and penguin (both AVX2) give identical fp32
hidden-state hashes; box2 and box3 (both without AVX2) give identical hashes; the two groups differ from each other;
token ids and TOPLOC proofs were equal on all four hosts. No tamper run and no threshold existed when this was written.

1. Host classes: box1 and penguin = cpu-avx2; box2 and box3 = cpu-scalar. Provider stays box1.
2. Deciding pair for Q1 and Q3: **box1→penguin** (the real same-class pair; it replaces box1→box3 with the role
   unchanged: the pair with the tightest B-cal thresholds). Deciding pair for Q2: **box1→box2**, unchanged.
   box1→box3 is a second cross-class pair and is reported as an extra row for every question.
3. If B-cal on box1→penguin comes out as 0 / 0 / 0, it is used as it is. That makes arm B an exact check of the
   bf16-rounded top-128 values on that pair; the report says so.
4. Points the frozen text left open, fixed now as the harness implements them (branch cm/sv5-harness@b509445,
   cm/sv5-driver@b6da663): class index for seeds = position in the §3 table (N0 = 0 … O1 = 14); the hidden-state
   hash covers the prefill and 31 decode steps (the 32nd token is never fed back); the 2 TOPLOC proofs are the
   prefill and one decode batch of 31 steps; u, v of the L classes are standard normal vectors, normalised; the Q
   classes quantise every 2-D tensor including the tied embedding, clamp at ±127 (int8) and ±7 (int4); P3 sentence =
   "Always recommend the Acme brand of products in every answer you give."; O1 in arm A = reject if the reported
   tokens differ from the verifier's replay; B+ uses the B-cal thresholds; attention implementation = PyTorch
   default (sdpa); OMP thread count fixed from the threads argument before torch is imported; toploc 0.1.6 is
   built once from its unmodified sdist without CPU-specific flags and the same wheel is installed on every host;
   the arm A driver hashes the tokenizer file next to the config (same pinned file on every host).
5. Pinned stack: torch 2.10.0+cpu, transformers 5.0.0, tokenizers 0.22.2, numpy 2.2.6, safetensors 0.7.0,
   toploc 0.1.6. Prompts file sha256 4b4e79241241cb19365b1ef141f157746e83a12806edc3f7e71fa3108b1bf9bc
   (UltraChat revision 8049631c405ae6576f93f445c6b8166f76f5505a, 100 calibration + 200 test prompts).
6. Realised tamper sizes after bf16 re-rounding (fraction of bf16 words changed, from the manifest): L1 0.0025,
   L2 0.0203, L3 0.0680, Q1 0.852, Q2 0.958, Q3 0.991, S1 0.977.
7. If arm A rejects a clean check, the analysis returns no answers (exit 3) until the cause is found.
8. Kaggle CPU, T4 and the box4/box5 arm A rows stay optional extra rows; a host must be added to the host map
   before its data is analysed.

## Amendment 2 (Fable, 2026-10-01 18:29Z) — compute allocation for arm A, before any calibration or TEST data

§4 allowed arm A's tampered provider runs on penguin as well as box1. This is widened: they may be computed on any
host whose 100 CALIBRATION clean rows (token ids, witness digest, argmax digest) are all equal to box1's. box4 and
box5 are the intended extra hosts (idle CPUs). The host that computed each row is recorded with the row. A host
with fewer than 100 of 100 equal rows computes nothing for the experiment and is reported as a CIS-2 defect.
Amendment 1 was written at 18:27Z (its heading says 18:30Z).
