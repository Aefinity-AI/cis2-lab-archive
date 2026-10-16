# PREREG w4: edit-strength sweep, exact replay versus a calibrated tolerance check (rank-one edit scaled by alpha, SmolLM2-135M)

STATUS: FROZEN rev 2 (critic pass applied) 2026-10-16 03:40Z; registered with cm-exp new (bar sha256 in state/exp registry) and ledgered in the next batch; no run has started. Written 2026-10-16 (Claudius Maximus builder, box7). No run of this lab has been started. Freeze = `cm-exp new w4` plus the public ledger line for this file's sha256; later changes are `w4-amend-N.md`. Source: `state/plans/2026-10-16-EXHAUSTIVE-PROGRAMME.md` section 2 (W4) and SPEED-SIZE report line 269 (Z5 hybrid); GO on `edge-exact`, Justin 2026-10-16 ~03:00Z. The EV card note of line 269 ("EV card before any run") is a freeze item: the parent files it.

## 1. Question
For a rank-one weight edit of SmolLM2-135M whose magnitude is scaled by alpha in {1e-6, 1e-4, 1e-2, 1}: (a) does exact replay (a bit-exact digest comparison) flag the edited model, (b) does a tolerance check calibrated on honest cross-host variation flag it, and (c) does the edited fact's probability move? Is there an alpha at which (a) fires, (b) stays silent and (c) shows no behavioural change?

## 2. What prior art already shows (honest)
- Rank-one editing is KNOWN: ROME (arXiv 2202.05262 [V]), MEMIT 2210.07229 [V]; sequential edits degrade a model (ACL Findings 2024 [R]); "One Mask to Rule Them All" (2605.28839 [R]) reports edits suppress rather than erase. Edit-detection work exists (2405.02765 [R]).
- Detection of quantisation or model swaps from activations or scores is KNOWN: TOPLOC (2501.16007 [V]) and DiFR (2511.20621 [V]) catch those swaps. The earlier "rivals are blind" framing (sv-5, dormant-1/2) is CONTRADICTED by them; the programme marks that line stopped and W4 is its graded successor. This lab does not claim rivals miss anything: TOPLOC is not run here, only a simpler tolerance check of our own, and its blind regime (if any) is a property of that check and its threshold.
- Exact replay catching any nonzero edit that the canary reaches is close to a tautology (a changed weight changes a hash). The sweep found no published detection-versus-edit-strength curve comparing exact replay and tolerance checks (SPEED-SIZE Z4 "WHAT REMAINS OPEN"); sweep limits as in the register. The informative content is where, in alpha, the tolerance check starts to fire and whether that is before or after the fact changes.
- Register ids: 2202.05262, 2210.07229, 2405.02765, 2501.16007, 2511.20621 (`state/reports/prior-art/PRIOR-ART.md`).

## 3. Hypothesis and predictions
- P1 [EST 0.9, mine]: a2 (CIS-2 witness digest of a 16-token canary run) differs from the unedited digest for alpha >= 1e-4 in 10/10 edits, and alpha = 1 in 10/10. At alpha = 1e-6 the fp32 weight change may round to zero in most entries (ΔW relative to w is about 1e-7 against a half-ulp of about 6e-8 [EST, to be replaced by the measured ΔW_1 norm at step 2]), so some edits may change no weight bit: a1 (changed-entry count) is reported and an edit with zero changed entries is counted as "no edit", not as a miss.
- P2 [EST 0.7, mine]: the tolerance check does not flag alpha in {1e-6, 1e-4} in at least 9/10 edits, flags alpha = 1 in at least 9/10 edits; alpha = 1e-2 is the transition and has no prediction.
- P3 [EST 0.6, mine]: edited-fact target probability moves by under 0.01 absolute at alpha <= 1e-4 and by at least 0.2 absolute at alpha = 1 in at least 6/10 edits (identity-covariance ROME-lite is weaker than full ROME on a 135M model; efficacy at alpha = 1 may be low).
- P4 [EST 0.5, mine]: a regime (an eligible alpha with a2 firing, tolerance silent, probability unchanged, all in all but at most one eligible edit) exists. The bar is on this.

## 4. Design
- Model: SmolLM2-135M fp32 (30 layers, hidden 576); edit target `model.layers.15.mlp.down_proj` (mid-layer MLP output, per ROME localisation). Layer index pinned.
- Edits: 10 factual edits authored by us as (subject prompt, old object, new object), pinned in the PREREG appendix at freeze (no dataset text used). Edit vector computed once per edit at alpha = 1 by the ROME closed form with identity key covariance (ROME-lite; a stated deviation from ROME, which estimates the covariance from Wikipedia text). ΔW_alpha = alpha x ΔW_1, added in fp32 and saved as safetensors.
- Detectors per (edit, alpha) on 4 canary prompts (pinned, 16 tokens each):
  - a1: count of weight entries whose fp32 bits changed (and weights-file sha256).
  - a2: CIS-2 witness digest of the 16-token run on the pinned engine (`cis2_host`, g++ build, flags as in `~/feed-payload/jobs/cis2-digest-box7.sh`) versus the unedited digest. Exact-replay verdict = any digest differs.
  - b: tolerance check = maximum absolute difference of final-position logits (fp32, PyTorch CPU, torch 2.10.0+cpu to match sv-5d) between edited and unedited model across the 4 canaries, flagged if above T. T = max(10 x the cross-host |logit diff| between box7 and box2 (SSE4.2 class), 1.4e-3), the cross-host difference being the largest absolute logit difference on the same unedited model and canaries (measured in this lab, step 1). The floor exists because same-class hosts can be bit-identical (sv-5d: penguin = box1 on all 1,664,964 positions), which would make T = 0 and flag every edit; 1.4e-3 = 10 x the largest sv-5d margin shift (1.392e-4). A TOPLOC-style simplification, not TOPLOC.
  - c: probability of the new object under the edit prompt, and under 5 pinned paraphrases, plus 20 unrelated control prompts (maximum change in their reference-token probability).
- Total runs: 10 edits x 4 alphas x 4 canaries = 160 engine runs plus PyTorch passes.

## 5. Hosts and resources
box7 (i7-7700HQ AVX2+FMA, 16 GB RAM) for everything; box2 (Celeron N4020, SSE4.2, 3.7 GB) for the T calibration run only (135M fp32 fits; if box2 cannot run it, record the reason and use the 1.4e-3 floor as T, labelled FLOOR-T). No GPU. $0. About 3 box-h [EST from the programme] and 1.5 Fable-h. Engine run time per canary is unmeasured here; if 160 runs exceed 3 box-h, the edit count falls to 6 (see the reduction rule in section 9). The EV card for the lane (edge-exact, ruled GO by Justin 2026-10-16; w4 has its own card `w4`) must read GO before `cm-exp new w4` is run.

## 6. Models, code, licences
SmolLM2-135M, Apache-2.0, https://huggingface.co/HuggingFaceTB/SmolLM2-135M; pinned weights sha256 80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1 (from the existing digest job). ROME is implemented from the paper (no ROME repository code or CounterFact data copied). Edited weights stay private and are not redistributed; they are not training data and no Claude-generated text enters training data. Edit prompts are short sentences written by us.

## 7. Procedure
1. Calibrate T: run the 4 canaries on the unedited model on box7 and box2, take the largest absolute logit difference, set T. Pin T before any edit is applied.
2. Compute the 10 alpha = 1 edit directions on box7; check at alpha = 1 whether the target probability moved (reported).
3. For each alpha: write edited weights, record a1, a2, b, c.
4. Re-derive tables with new code that imports neither the main analysis script nor the engine harness.

## 8. Analysis
Per alpha: counts of edits (of 10) with a2 firing, b firing, c-moved (|Δp| >= 0.01); the regime table; the transition alpha for b. Plain counts, no significance test.

## 9. THE BAR (draft, written 2026-10-16 before any run; text for `cm-exp new --bar`)
MET if there is at least one eligible alpha in {1e-6, 1e-4, 1e-2, 1} at which all three conditions hold in all but at most one of the eligible edits: (a2) the 16-token canary witness digest differs from the unedited digest on at least one of the 4 canaries; (b) the tolerance check (T pinned in step 1) does not flag the edited model on any canary; (c) the target-object probability under the edit prompt and 5 paraphrases changes by less than 0.01 absolute and no control-prompt probability changes by 0.01 or more. An edit with a1 = 0 (no changed weight entries) at an alpha is dropped for that alpha; the alpha is eligible only if at least 8 edits remain. Pre-declared reduction: if the edit count falls to 6 (section 5), the same rule applies with eligibility at least 5 remaining edits and "all but at most one" unchanged. NOT MET if no eligible alpha satisfies all three conditions (final, not re-run). INCONCLUSIVE if no alpha is eligible. INVALID if T is not pinned before any edit is applied, the edited weights change at a layer other than the pinned one, or the unedited-model digest does not equal the pinned digest. MET at alpha <= 1e-4 is the expected case and is reported as such; the informative registered quantity is the smallest alpha at which condition (b) fires versus the smallest alpha at which (c) moves (reported, no bar).

## 10. Success and failure, stated for a stranger
A reader checks the per-alpha table: a2 column, b column with T and the logit differences, c column. MET = one eligible row with all three conditions in all but at most one of the eligible edits. The reader can recompute a2 by running the public engine on the edited weights; the edits are released only if the publish card allows.

## 11. Disclosures that travel with any W4 number
1. "Tolerance check" is our simplified logit-difference check, not TOPLOC or DiFR; its result says nothing about them.
2. ROME-lite (identity covariance) on one 135M model and 10 hand-written edits; efficacy at alpha = 1 is reported and may be low.
3. The regime, if it exists, depends on T (max of 10 x honest cross-host variation and the 1.4e-3 floor); a tighter T would flag smaller edits.
4. Exact replay "sees" an edit only when the canary reaches the edited row; this is not a statement about unreached rows.

## 12. Publication (per `state/policy/PUBLISH-SCORING.md`)
Private until the score card exists. The curve and method are not a moat but touch the exact-replay positioning of CIS-2; `new_technique_patent_question` is NOT expected (rank-one editing is published; the sweep found the curve unpublished, which is exactly why it is scored rather than assumed). Edited weights and edit lists stay private. Soft flags: `number_not_in_numbers_md`, `word_rule_check`. Score card after the result; 70 or more publishes, 40-69 one NEEDS line, under 40 private.

## 13. Stop-loss
If the ROME-lite edit at alpha = 1 moves the target probability in fewer than 3 of 10 edits on step 2, stop and record INCONCLUSIVE (the sweep has nothing to scale); do not tune the editor to rescue it. If step 1 consumes more than 1 box-h, stop.

## 14. Status
FROZEN rev 2 (critic pass applied) 2026-10-16 03:40Z; registered with cm-exp new (bar sha256 in state/exp registry) and ledgered in the next batch; no run has started. Suggested registration: id `w4`; title "edit-strength sweep: exact replay versus calibrated tolerance check on SmolLM2-135M"; host `box7`; bar = section 9.
