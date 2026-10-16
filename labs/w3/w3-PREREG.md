# PREREG w3: margin-gated verification from the sv-5d logs (flips versus top-1/top-2 margin on CPU fp32)

STATUS: FROZEN rev 2 (critic pass applied) 2026-10-16 03:40Z; registered with cm-exp new (bar sha256 in state/exp registry) and ledgered in the next batch; no run has started. Written 2026-10-16 (Claudius Maximus builder, box7). No analysis of this lab has been started. Freeze = `cm-exp new w3` plus the public ledger line for this file's sha256; later changes are `w3-amend-N.md`. Source: `state/plans/2026-10-16-EXHAUSTIVE-PROGRAMME.md` section 2 (W3); GO on `edge-exact`, Justin 2026-10-16 ~03:00Z.

## 1. Question
Over the 1,664,964 positions of the registered sv-5d scan (SmolLM2-135M, fp32, CPU, torch 2.10.0+cpu), do all observed argmax flips (across CPU class and batch) sit below a small top-1/top-2 margin, so that a verifier re-checking only positions under that margin covers every observed flip while re-checking under 1 % of positions?

## 2. What prior art already shows (honest)
- MarginGate (arXiv 2605.30218 [V]): on GPU BF16, batch-induced flips are 0.3-1.3 % of steps, risk concentrates at low top-1/top-2 margin, and its verifier fires on 15-19 % of steps. 2506.09501 [V] shows BF16 decision flips with batch size. 2609.26621 is cited in the sweep for margin-triggered repair.
- Our own sv-5d (MET 2026-10-03; `state/reports/2026-10-03-SV5D-PER-TOKEN-DIVERGENCE.md`, NUMBERS.md line for sv-5d) already found 3 cross-class and 4 batch flips in 1,664,964 positions (1.8/M and 2.4/M), all swapping the top two tokens at a reference margin of at most 5.722e-06, and a largest margin shift of 1.392e-4. So the direction of this lab is already visible in the sweep's own data: W3 does not discover it. What W3 adds is a registered coverage rule (flips versus margin threshold, and the re-check fraction), computed by new code that imports neither existing script, on all raw arrays, and a CPU fp32 figure to set beside MarginGate's GPU BF16 figures. CPU fp32 coverage was not found by the sweep (SPEED-SIZE report line 54: "CPU fp32 measurement OPEN"); sweep limits as in the register.
- Register ids: 2605.30218, 2506.09501 (`state/reports/prior-art/PRIOR-ART.md`). Duplicate marking: sv-5d is DUPLICATE on GPU, KEEP for CPU scope (programme section 3); W3 uses it as input only.

## 3. Hypothesis and predictions
- Registered threshold tau = 1e-2 logit units (programme plan; SPEED-SIZE line 54 falsifier).
- P1 [data already seen, so this is a reproduction check, not a surprise]: maximum reference margin over all flips in all registered cells = 5.722e-06; no flip above tau.
- P2 [EST, mine]: fraction of the 1,664,964 positions with reference margin <= 1e-2 is between 0.3 % and 1.2 %. Derivation: the report gives 123 positions under 1e-4 (7.4e-5 of positions); a flat margin density extrapolated to 1e-2 gives about 0.74 %; real top-1/top-2 margin densities rise toward 0 only mildly, so the range is wide and the 1 % line is NOT safely cleared. This prediction is a coin flip around the bar and is stated so.
- P3 [measured in the report]: fraction at tau2 = 2e-4 (1.44 x the largest observed margin shift 1.392e-4) is about 0.01 % (123 under 1e-4 plus a few more) [EST for the count between 1e-4 and 2e-4].

## 4. Design
Inputs: the raw per-position arrays (`~/sv5d/<host>/<cell>/pNofM.npz` plus sidecar JSON on box7; reference R = box1 B1T1 windows 0-7999; chunk files `.cN.npz` excluded as in `state/reports/sv5d/2026-10-03-sv5d-recount.py`). Each array records top-1 index, top-2 index and fp32 margin per position. Nothing is re-run on a model. The analysis script is new, does not import `sv5d_compare.py` or the recount script, and its sha256 is pinned at freeze. Its totals must reproduce the report's 1,664,964 positions and the flip table before any new number is read (sanity gate; failure = INVALID).
Cells counted: all registered cells in the sv-5d bar (X = box2 + box3 cross-class composite, B = box1 batch of 8); extra cells (T, box3 B8T1, penguin) are reported but not in the bar.

## 5. Hosts and resources
box7 only (i7-7700HQ, 16 GB RAM); the npz set is 68 MB. A few CPU-minutes, $0, about 1 Fable-h. The EV card for the lane (edge-exact, ruled GO by Justin 2026-10-16; w4 has its own card `w4`) must read GO before `cm-exp new w3` is run. No GPU. Memory-capped like the recount (`systemd-run --user -p MemoryMax=1500M`). If any npz is missing or its sidecar sha256 differs from the report, that cell is excluded and listed; fewer than all registered cells present = INCONCLUSIVE, not a re-run (box3 is down, so a re-scan of its half is not available).

## 6. Data and licences
Windows are UltraChat 200k `train_sft` text (HuggingFaceH4/ultrachat_200k, https://huggingface.co/datasets/HuggingFaceH4/ultrachat_200k; licence line to be copied from the dataset card at freeze, not assumed; used here only as already-scanned indices, no text read or published) and SmolLM2-135M (Apache-2.0, https://huggingface.co/HuggingFaceTB/SmolLM2-135M). No new third-party data enters.

## 7. Procedure
1. Freeze this file, the script sha256, the npz manifest (path, size, sha256).
2. Run the sanity gate (position counts, flip counts per cell equal the report).
3. Compute: (a) for every flip in every counted cell, the reference margin; (b) for tau in {1e-6, 1e-5, 1e-4, 2e-4, 1e-3, 1e-2, 1e-1}, the count and fraction of positions with reference margin <= tau; (c) per cell, the largest margin shift and the flip positions with the shift they needed.
4. Write results to `state/reports/w3/`, with the script output sha256.

## 8. Analysis
Exact counts and the one-sided 95 % bound (Clopper-Pearson) on the fraction of positions re-checked are reported. A flip with reference margin exactly 0 (the w1302/p143 tie) is listed and counted under tau (0 <= tau).

## 9. THE BAR (draft, written 2026-10-16 before the analysis; text for `cm-exp new --bar`)
MET if, after the sanity gate passes, (i) (reproduction of the sv-5d report line 135; it cannot fail unless the sanity gate is wrong) every argmax flip in every counted registered cell has reference margin <= 1e-2, AND (ii) the fraction of the 1,664,964 positions with reference margin <= 1e-2 is strictly under 1 % (count at most 16,649; 1 % of 1,664,964 is 16,649.64). NOT MET if any counted flip has reference margin above 1e-2, or if (i) holds but the fraction at 1e-2 is 1 % or more (the covering rule exists but is not cheap at that threshold; the smaller tau2 = 2e-4 figures are then reported as the separate observation they are). INCONCLUSIVE if registered cells are missing; INVALID if the sanity gate fails.

## 10. Success and failure, stated for a stranger
Check: the committed script, the npz manifest and the output table. A reader re-derives the 16,649 count threshold and the maximum flip margin from the arrays.

## 11. Disclosures that travel with any W3 number
1. The flips were already known (7 registered, 3 and 4 per cell family) before this PREREG; condition (i) is a reproduction. The new content is the fraction at tau and the registered rule.
2. 7 flips in 1.66 M positions is a very small sample for a coverage claim; the report's own caveat applies ("the rate estimate rests on a small set of near-ties"). A rule that covers 7 flips has not been shown to cover the next one. The margin-shift maximum 1.392e-4 is the more informative bound: a flip needs a reference margin smaller than the shift at that position.
3. One model, one corpus, fp32 CPU, torch 2.10.0+cpu, one reference run (R is itself the odd one out at w3334/p101).
4. The re-check fraction is computed on R's margins; a verifier using its own run's margins would see shifts of up to 1.392e-4, so the registered tau covers that only because tau is far larger than the shift.
5. Not comparable one-to-one with MarginGate: different precision (fp32 versus BF16), different hardware, teacher-forced scan versus decoding.

## 12. Publication (per `state/policy/PUBLISH-SCORING.md`)
Result recorded privately before any publication (`cm-exp result w3`, report under `state/reports/w3/`). The coverage table is spec evidence and the cheap-verification argument for the receipt gateway; no hard stop expected (no suite internals, recipes, kernels, customer artifacts, pricing; the arrays contain token ids, not text). Soft flags: `number_not_in_numbers_md` until `bin/cm-numbers` runs; `word_rule_check`. Score card after the result; 70 or more publishes, 40-69 one NEEDS line, under 40 private.

## 13. Stop-loss
If the sanity gate cannot reproduce the report within 1 Fable-h, stop; INVALID. No re-scan of model outputs is part of this lab.

## 14. Status
FROZEN rev 2 (critic pass applied) 2026-10-16 03:40Z; registered with cm-exp new (bar sha256 in state/exp registry) and ledgered in the next batch; no run has started. Suggested registration: id `w3`; title "margin-gated verification coverage from the sv-5d CPU fp32 logs"; host `box7`; bar = section 9.

## Appendix A. sv-5d .npz manifest (sha256, computed 2026-10-16 on box7 from ~/sv5d; 14 files)
```
5934aa597aee3705b6bfa03a036d84f756c9b7f3f43cb1e663e82c10d88b7f00  box1/B1T1_0-8000/p0of2.npz
5e7e5d3677d7941f6e785998f22470447984b8792cc7d87650f217fd0abaaaf1  box1/B1T1_0-8000/p1of2.npz
6dd986cacbef141f7a4a436fa79d7b339a4659ea76f521cb507515549bdc6ecc  box1/B1T2_0-2000/p0of1.npz
edda6d1d3814827497dd717fea255df79079c3bef37baa4cab5ec6035ec0edd2  box1/B8T1_0-8000/p0of1.npz
048018c1f85cd5b65be34f586e1a356d9a3f4513f6f7977b5f6d18e775f423b6  box2/B1T1_0-4000/p0of2.npz
b1d911bcc47f5859dd7359a69cfa34289acb8a658c876be2b5cc19bd8b56898f  box2/B1T1_0-4000/p1of2.npz
94727862488f11cdf5d15895c4463e9515eb38bcf40a4ae072a8ed302fc95494  box2/B1T2_0-4000/p0of1.npz
d3735d729162f77b86e4978816795aca8c1938ff9e95d6276b86051b22517fcd  box2/B8T1_0-4000/p0of1.npz
02e59764fd421ee88409ed3bb6cf70160c645fb2d73dc5957f1cc51b678889c7  box3/B1T1_4000-8000/p0of2.npz
43f01a8314d4491d8a8903d8ec1e05e606102f807c09e4a4c08c75b8daf7d75d  box3/B1T1_4000-8000/p1of2.npz
a4f76e7dc5e1c68ba2dbf4f9ab437b9f10fdb586f096a84579ceddcbeec8683e  box3/B1T2_4000-8000/p0of1.npz
559b3c200f15ad53f155117b701f3adbc86c3b9702ad53dafbede1ba00f0a095  box3/B8T1_4000-8000/p0of1.npz
4269a998b50ff8a09955c16e7b8407fadf16bd97b71e747e2219fef3ae94b02c  penguin/B1T1_0-2000/p0of1.npz
d729f5f013bc541e42dac3a2ece777ef6738d0160728fbd608c9739d6879ade7  penguin/B1T1_2000-8000/p0of1.npz
```
Cell-composition of the bar (which of these files count) is fixed by the sv-5d bar; extra cells (T, box3 B8T1, penguin) are reported, not in the bar. Compare against the sidecar JSON sha256 values at freeze; any difference excludes that cell (section 5).
