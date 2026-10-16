# VERIFY-RESULT-final-R1 (rust-4b, adversarial final reader)

## Verdict: RECORD (ledger word met)

No MUST items. RESULT.md (sha256 7f0069dd...fd42da, matches) and the proposed register text are correct against the pass mark and the raw files. Three SHOULD edits to the register text are listed below; none changes the word or the label.

## Checks I did myself (own recomputation from box*/rows.jsonl and result.json, status KEPT rows)
- bar_sha256 f37da0bc...1cba7: sha256 of the `bin/cm-exp show rust-4b` bar field, equal. EVIDENCE-SHA256SUMS: every entry OK except the bar-text line (its name is a description, not a file; not a defect).
- box1 R reps [12.6928, 12.4663, 11.9185, 15.5787, 13.5203], median 12.6928; C reps [10.7433, 9.9102, 10.4127, 10.4383, 9.6827], median 10.4127; r = 10.4127/12.6928 = 0.82037. Slowest C 10.743 < fastest R 11.919. Band RUST BEHIND holds; no redo. Register ranges (C 9.68-10.74, R 11.92-15.58) correct.
- P median 38.3982; P/R 3.0252, P/C 3.6876 -> "3.03" and "3.69" correct. P reps 43.82, 34.68, 38.40, 87.20, 35.77 s.
- 30 KEPT rows on box1, 0 discards, 0 voids, 0 not-cold, all resident_pages 0, errors 0, rc 0, mismatches 0, throttle changes 0. Foreign load max 0.0417 (limit 0.044) and 0.0878 (limit 0.1). MHz 2093-2100. Elapsed 1,122 s. Timers paused and restored (RESULT.txt).
- Pins in box1/RESULT.txt: payload 939a31be..., run_py 337a6e17..., helper a08c989b..., witness ecafd089... all equal to frozen/pinned values. Controls 65689/65689, 0, 65689/65689.
- Disk ST4000LM024-2AN1, rotational "yes (1)", ext4: correct.
- All RESULT tables re-derived for box1..box5: medians, min-max, load_ns, prefill_ns, sectors, major faults, positions, discards/voids (box2 1/3, box3 5/6, box4 1/1, box5 3/0), elapsed (1122, 714, 1593, 942, 1105), P venv files 29,942 on all hosts, probe rc -4 on box4 and box5, other-host r (0.7755, 0.7489, 0.8346, 0.9213) and P factors (1.52/1.96, 3.17/4.24). All match. Only difference: box2 Rv median 9.2035 printed as 9.204 (round-half, immaterial).
- SUMM-OUT.txt lines agree with RESULT section 4: carried TIE SURPRISE, operator class SURPRISE, P above 3 on box1 held, box2 Python SURPRISE.
- Pass mark "must state" items (1) to (8) and disclosures (a) to (n) are all present in RESULT.md. Nothing forbidden is said: no label word on box2..box5, no "Rust starts faster/slower" outside the M2 form, no credit to storage, no "conservative", no prompt or generated text. Ledger mapping: label on valid reps + expectation recorded as SURPRISE = met. Correct.
- Register text: every number and sentence matches, and the M2 and Storage sentences equal the required form.

## MUST
None.

## SHOULD (register text only)
1. Python expectation is told only in its held half. The text says "P above 3 on box1: held" and omits that the carried Python line (above 3 on box2, about 80 pct) came out SURPRISE (1.52 over R, 1.96 over C, informal, Rule A). Add after the box1 clause: "Carried Python line on box2: SURPRISE (1.52 over R, 1.96 over C, informal)."
2. "3.03" is a median and a narrow margin. Two of five P reps (34.68, 35.77 s) are under 3 times the R median. Add to the FRAMEWORK clause: "medians of 5; P reps 34.7-87.2 s; margin over 3 is narrow".
3. Say what the wall gap holds, so a reader does not read BEHIND as slow cold reading. On box1 the R minus C gap is 2.28 s in the wall; printed prefill_ns medians are R 7.640 s, C 5.939 s (1.70 s of the gap) and load_ns R 4.885 s, C 4.455 s (0.43 s). Sectors read are about equal (550,616 vs 530,328). Suggested: "most of the 2.28 s gap is in the arithmetic of the prefill the programs print (1.70 s), not in the load (0.43 s); the wall is not read time alone; no storage credit." (Data statement only; no credit to storage and nothing about warm decode.) Optionally add that P's standard library was read cold unchecked while R and C have no such files (required item 8; it is in RESULT.md but not in the register text).

## What I ran
cm-exp show rust-4b (saved bar to ~/scratch-results/bar.txt, sha256 f37da0bc...); sha256sum on RESULT.md and EVIDENCE-SHA256SUMS; python recomputation over box1..box5 rows.jsonl and result.json; reading SUMM-OUT.txt, VERIFY-RESULT-R1.md, the full bar. Nothing run on any box. Only this file written (scratch in ~/scratch-results).
