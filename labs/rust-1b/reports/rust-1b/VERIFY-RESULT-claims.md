# VERIFY-RESULT, lens: claims and wording (rust-1b final RESULT.md + register text)

Read-only. Commands: cat/grep/python json walk on the amended bar, BUILD.md (items 1-8, disclosures), RESULT.md, rust1b_result.json, box3/RESULT.txt, `bin/cm-exp show rust-1` and `show rust-1b`, LOG.md grep. No repo edits except this file. (ANSWER-SO-FAR.md and PRIOR-ART.md: not read in depth; no claim in RESULT.md leans on them.)

## Verdict
Agree with the word "met" and with all four labels (AHEAD x4, box1, N=1). The pass mark has no mapping to the four register words (checked: it says only "one sentence per outcome", opens "This is a BAR..."). rust-1 was recorded "met" with the label in the summary (cm-exp show rust-1, 14:02:12Z: "LEVEL is recorded as met"). RESULT.md section 1 states this honestly, including that "met" does not say who is ahead. No INVALID condition touches a labelled pair.

## The 8 must-state items
1 memory line: handled. Deviates on purpose from the template ("different day"): rust-1 job 09:26-11:18Z 10-04, rust-1b n1 16:34-18:18Z 10-04, so "same calendar day" is true; the deviation is stated. Load methods correct for G, X, T, Q, L-R, L-C. No label on memory. OK.
2 arm Q: logit diff 0.0720 (box1) / 0.0845 (box2), INFO line, "not bit-comparable", Q8_0 "different arithmetic". OK. (The register text carries 0.072 but not the INFO line; acceptable for a summary.)
3 KERNELS clause: present in section 1 and item 3 word for word. OK.
4 FRAMEWORK sentences: three sentences in registered form, pure/not pure named. OK.
5 phases and budget: both jobs, order, budget left before n2 (15,812 s). OK.
6 arm L rows from rust-1, not in a pair, frozen after rust-1 numbers: OK.
7 T at N=2: INVALID by Threads rule, 4 vs 2, no value. OK, visible in sections 3, 6, 7 and in the register.
8 trust column: all four parts present; hash of T differs across hosts reported "not argued". OK.

## Disclosures
All of BUILD.md "Disclosures" are in section 7. The 03:20:00Z pull is in section 3 and in the register with: rep 0 of gmkl-O2, KEPT, 19.441674 tok/s, median of the arm (verified from json: reps 19.4417, 19.5120, 19.4722, 19.4411, 19.3125; median 19.441674), load 0.0161 against 0.032, no label. OK.

## Numbers in the register text (all checked against rust1b_result.json)
- r 1.338 / 1.195 / 1.304 / 1.303: labels[0..3].ratio = 1.33769 / 1.19539 / 1.30372 / 1.30330 (also jobs/box1_n1/pairs/*/r).
- X against Q 1.165: jobs/box1_n1/x_v_q_ratio_no_label (1.16465); also x_v_q_ratio_no_label_n1.
- 45 rows all KEPT: jobs/box1_n1/status_counts/KEPT 45.
- Q logit difference 0.072: jobs/box1_n1/gates/q@n1/before|after/max_abs_diff_8 0.07203.
- 19.441674: operator_disclosure_0320Z.value_tps and jobs/box1_n2/median_tps/gmkl-O2.
- Threads 4 not 2: jobs/box1_n2/invalid_rows[0] threads_not_2(max=4).
- 03:20:00Z, 0.0161, 0.032: operator_disclosure_0320Z (limit also in RESULT.md section 3).
- "five reps, all separated, SURPRISE": labels[*].reps_separated True, surprise_flag True.
- "three clock discards each": box2 = jobs/box2/discards[0..2] (drops 0.203, 0.231, 0.185); box3 = only jobs/box3/result_txt/discards 3 (see D1).
No number in the register is missing from or different from the json.

## Discrepancies

D1 (must_correct_in_report): register says hosts box2 and box3 each had "three clock discards". For box2 that is shown by rows (drops 20.3, 23.1, 18.5 percent). For box3 only the feeder RESULT.txt exists (reason=three_discards_on_this_host, 0 reps); RESULT.md section 4 itself says "I cannot say from the folder which rule caused the three discards". Register text is wider than the evidence. Correction: "box2 (three clock discards) and box3 (three discards, rule not readable from the copied files) ended INVALID". Under the bar's own wording a discard is the clock rule, so this is a wording-level fix only. No label changes.

D2 (note): register says "all SURPRISE". For G-MKL against T no expected value was written (RESULT.md section 8 says "no probability written"), yet it is flagged SURPRISE and section 8 closes "The expected ordering was wrong in direction for all four labels". For G-MKL that is an inference from G-OB's expectation, not a registered expectation. Correction: say "three of four have a written expectation (all against it); G-MKL has none and goes the same way as G-OB". Changes no label.

D3 (note): register text is thinner than RESULT.md on scope. It says "Not a language verdict" but does not say: one machine (box1, i5-5200U), one thread, this torch setup (manual loop, no compile), SmolLM2-135M only. A reader of the register line alone could over-read "ahead of PyTorch". Suggest adding "for this torch set-up, one thread, one machine; not PyTorch in general". Also register does not say box2 phase n2 did not run, and does not call phase n2 on box1 PARTIAL (it names the T problem; adequate).

D4 (note): section 3 says "at two threads llama.cpp F32 is a little faster than the Rust arms" for an unlabelled phase. It is hedged ("no conclusion beyond the numbers") and the G-OB/Q ratio 0.930 is in the TIE band numerically. Better to say "numbers in the same range; no label". Not a label claim.

D5 (note): section 9 "17 to 20 percent faster than llama.cpp F32": ratios are 1.165 (G-MKL, X) to 1.195 (G-OB), so 16.5 to 19.5 percent. Round to "about 17 to 20" is within rounding; fine, flagged only for exactness. Section 9 "about 10 GB/s ... consistent with a shared limit; not tested" is speculation but is marked untested.

## Checked and clean
- No "Rust is faster than Python" sentence; RESULT.md says so explicitly and section 9 lists what is not shown (language, implementation, toolchain, other CPU, threads, model).
- No blending of the five answers; arm L rows not in a speed pair.
- Q never called bit-comparable; memory lines carry no label; no label on n2, box2, box3, X against Q, Q8_0.
- Bad news (T INVALID at N=2, box2 INVALID, box3 INVALID, n2 PARTIAL, three voids) is as visible as the good news in sections 3, 4, 6, 9 and in the register.
- Pass-mark INVALID sentence "the affected label gets no verdict, and the run is redone": no labelled pair affected, so no redo due; stated correctly.

## For NEEDS/BLOCKERS
Nothing blocking. Apply D1 (and ideally D2, D3) to the register summary text before recording.
