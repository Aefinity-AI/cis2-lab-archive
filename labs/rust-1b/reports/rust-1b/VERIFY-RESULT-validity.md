# rust-1b VERIFY-RESULT, lens: validity and process

Written 2026-10-05 by the validity checker. Read-only on the repo except this file. Scratch: ~/scratch-rust1b-final/validity/.
Verdict on the lens: I AGREE with the verdict word (met) and with all four labels. Nothing I found makes a labelled number untrustworthy. I found two sentences in the report that are wrong or unsupported (neither changes a label) and four notes.

Plain terms. "Rep" = one timed run of one arm. "Void" = a rep thrown away because other work on the box was too busy during it; it is repeated. "Discard" = a rep thrown away because the CPU clock dropped more than 15 percent; three discards make the host INVALID. "Outside load" = CPU time used by anything other than the arm and the runner, measured during the rep.

## What I ran (all read-only)
- `bin/cm-ledger check-bar rust-1b` -> "bar line of rust-1b is public as E-0059 line 178".
- `bin/cm-exp show rust-1b` (saved to scratch), sha256sum of the bar file, FREEZE-STAGE2.md, wrappers (box*/run.sh, box3/job.sh), rust1b_result.json; `sha256sum -c EVIDENCE-SHA256SUMS` (under systemd-run MemoryMax 900M).
- `git log`, `git diff`, file mtimes for RESULT-N1.md and rust1b_result.json.
- Python (standard library) over box1/rows.jsonl, box1-n2/rows.jsonl, box2/rows.jsonl; grep of run.log and RESULT.txt in all four folders; LOG.md lines 3919-3921, 3940, 3944, 4017, 4020.
No ssh, no network, no cm-exp/cm-feed write command.

## Identity and process checks
- Pass mark hash: sha256 of state/plans/rust-lab/bars/rust-1b-amended-bar.txt = b1d2fdb1...e8671 = register bar_sha256 of the amendment (2026-10-04T16:00:13Z). The file has NO trailing newline (last byte 0x2e), so "without its final newline" and the whole file give the same hash. HELD. (Registered original bar: 2e0f94a5...df46, as in LOG.)
- Register start record (started 2026-10-04T16:04:24Z, ref text): `cm/rust-lab@1cdedca9... freeze-stage2=43ec5523...94d3 amended-bar=b1d2fdb1...`. sha256 of FREEZE-STAGE2.md today = 43ec552313e064f0bc750d0b0e0946228bf5a6c477c2469505f8524b528694d3 = STARTED.md = register. FREEZE-STAGE2.md mtime 10:48 CDT (15:48Z), before the start. HELD.
- Bar line public before start: ledger line 178 (amended bar) public 16:03:21Z per LOG 16:05, start 16:04:24Z; check-bar passes. HELD.
- Frozen payload and runner: every RESULT.txt (box1, box1-n2, box2, box3) prints payload_sha256 a2a1b3ee...1cf8 and run_py_sha256 bcd0fa38...e431f, both equal to the frozen values and to FREEZE-STAGE2.md section 1 and STARTED.md; payload_match=yes in all four. Wrapper hashes: box1/run.sh 6b6f4e3e..., box1-n2/run.sh 537c9efe..., box2/run.sh 8944aa49..., box3/job.sh c3b0727..., all equal to the FREEZE-STAGE2.md section 2 table. HELD.
- RESULT-N1.md: one commit only (99b4963b, 2026-10-04 20:32Z), `git diff` against HEAD empty, mtime 2026-10-04 14:03:04 CDT = 19:03Z. LOG 19:03Z says it was "corrected per the verifier" at that time, i.e. after the confirming read began (section 8 is dated 19:02Z). So the file is the corrected, confirmed text and has not changed since 19:03Z. HELD (see note 4 on wording).
- rust1b_result.json: committed version has box2_n2 T hash 621456b156088648 (typo); the working copy has 621456b15608864d, which matches box2/checks/gate_before.json and before.t.n2.stdout (hidden=621456b15608864d...). Working-copy sha d3ccbf76... equals EVIDENCE-SHA256SUMS and RESULT.md; all EVIDENCE-SHA256SUMS lines checked OK. The fix is only uncommitted. See note 3.

## Rule by rule, per job
Legend: J1 = box1 n1 (N=1, the labelled job), J2 = box1-n2 (N=2, no label), J3 = box2, J4 = box3. Fields are in rows.jsonl.

| Rule | J1 | J2 | J3 box2 | J4 box3 |
|---|---|---|---|---|
| Idle gate at start (load below 0.3, no other units) `before.load[0]`, `before.other_units` | MET: max 0.29, 0 other units, 45 rows | MET: max 0.29, 0 units | MET as far as rows show (not re-read in detail) | CANNOT TELL: no rows copied |
| Outside load during rep (R1) `foreign`, limits from `baseline` (arm 0.0285 / host 0.1 at n1; 0.032 / 0.1 at n2; baseline measured, 20 s windows) | MET: max arm 0.0172, host 0.0378; 0 voids | MET: all 30 kept rows at or below 0.0284 (limit 0.032); 3 VOID rows at 0.0678, 0.0331, 0.0322 (all above 0.032), each repeated; 6-repeat limit not reached | not read | CANNOT TELL |
| Clock (R2) `mhz_drop`, `mhz_rep_low`, `thr_changed` | MET: worst drop 0.01 percent, 0 throttle changes, reference 2095.15 MHz | MET: worst 0.04 percent | VIOLATED as the bar expects: 3 DISCARD rows (0.2029 G-OB O3; 0.2311 and 0.1852 G-MKL O3) -> host INVALID by the 3-discard rule | RESULT says discards=3 INVALID; reason per discard CANNOT TELL (see D2) |
| Threads (INVALID rule) `threads_max` vs `threads` | MET: 1 of 1 in 45 rows | MET for 6 arms (2 of 2); VIOLATED for T: threads_max 4, status INVALID, one row, no value (named in advance by BUILD.md item 7 and LOG 16:00Z ruling 1) | not read | CANNOT TELL |
| Pinning (R7) `arm_cpus` | MET: arm CPU 1 only (all rows), runner CPU 0, separate cores | MET: arm CPUs [0,1], runner CPU 2 (shares core 0 as R7 says) | not read | CANNOT TELL |
| Balanced orders (R9) `order_pos`, RESULT order_9/order_7 | MET: every rep ran in the design order of its rep mod 5; mean position 4.0 for all 9 arms; design_pos = order_pos in all 45 rows | MET for design; real orders differ in 11 rows because T dropped out after rep 0 (disclosed in RESULT.md); VOIDs repeated at their place | not read | CANNOT TELL |
| Voids/discards limits | MET: 0 and 0 | MET: 3 voids (limit 6 per rep), 0 discards | 3 discards = INVALID host | 3 discards = INVALID host |
| Untimed checks before and after (R3) `run.log` GATE lines | MET: 9 of 9 before OK, 9 of 9 after equal_before=yes; arg-max mismatches 0 (Q8_0 17 each, exempt by R3) | MET: 7 before OK, 6 after equal (T has no after-check, INVALID) | before checks OK; not re-read | RESULT lists all arms gate OK |
| Two jobs and order (R11) | MET: n1 job 16:34:40Z-18:18:54Z, then n2 job 02:58Z-04:29Z; no redo needed (no INCONCLUSIVE) | MET: wrapper budget test passed: cap_s 15,812 vs 7,200 needed | n/a | n/a |
| Cost caps and shared file (R8) | MET: used_before 6,735 s, elapsed 6,253 s, cap 22,065 s; after 12,988 s | MET: used_before 12,988, elapsed 5,382 s, cap 15,812 s; after 18,370 s of 28,800 | elapsed 4,517 s (cap 86,400 s, shared, rust-1 use not read) | elapsed 2,421 s |
| Frozen hashes + wrapper (payload, run.py) | MET | MET | MET | MET |
| Timers paused/restored (R10b) | MET: both timers paused and restored | MET | NA (none touched, as R10 says) | NA |
| CPUQuota (R5) | MET: cpu.max 400000/100000 on the job unit, 4 logical CPUs, arm pinned to 1 CPU: not binding | same, arm on 2 CPUs: not binding | 200000/100000 | 200000/100000 |

box1 values reproduce: the RESULT.txt numbers equal the rows.jsonl values (spot checks: gob-O3 18.762273 rep 0; gmkl-O2 n2 median 19.441674 of 19.3125, 19.4411, 19.4417, 19.4722, 19.5120).

## Statements of the report checked against run.log and rows.jsonl
- box2: "three discards, all in rep 0, 0.203 / 0.231 / 0.185; seven reps kept; G-OB O3 kept at its second try; n2 did not run; elapsed 4,517 s": HELD (DISCARD rows t_end 19:23:29Z, 19:52:24Z, 19:56:31Z; tries 1,1,2 on the arms named; RESULT reps n2 all 0).
- box3: "INVALID, three discards, only RESULT.txt and job files exist, cannot say which rule": HELD in section 4 of RESULT.md; the proposed register text goes further (D2).
- PyTorch at N=2: "one T row, rep 0, place 1, 03:11:11Z, INVALID, threads_not_2(max=4), no value, not run again": HELD (row t_end 2026-10-05T03:11:11Z, order_pos 1, value_tps None, problems threads_not_2(max=4); no T row in reps 1 to 4; checks of T before passed, 0 mismatches).
- Voids: "3 voids at 03:34:37Z (0.0678), 04:02:38Z (0.0331), 04:15:23Z (0.0322), each repeated, 0 discards": HELD (rows and run.log lines 46, 58, 64, limit 0.032). The cause of the three outside loads is not known and the report does not claim one; none lines up with the 03:20 pull.
- Weights/prompts/ids/arms same on every arm: HELD via the equal witness and logit-difference lines in every GATE line.

## The 03:20:00Z pull (the row that was running)
The row nearest 03:20:00Z is n2 rep 0, arm gmkl-O2, order place 6 (the last of rep 0): `before.t` 2026-10-05T03:20:27Z, `t_end` 03:21:10Z, `wall_process_s` 43.0, recorded outside load `foreign_arm` = `foreign_host` = 0.0161 (limit 0.032), value 19.441674 tok/s, status KEPT, `before.load` 0.29 (the idle gate).
The row before it, gmkl-O3 rep 0, ran 03:18:13Z to 03:18:56Z. So 03:20:00Z lies in the GAP between the two arm runs (about 91 s with the runner waiting for the load average to fall from 1.3 to below 0.3), 27 s BEFORE the gmkl-O2 process started. No timed window (all 45+34 rows) contains 03:20:00Z. This assumes penguin and box1 clocks agree to within a few seconds; I could not test that (no ssh).
So: the value 19.441674 and the 0.0161 are as the report says, and the median claim is right (it is the middle of the five). But the report's sentence "during rep 0 of arm gmkl-O2 ... a rep taken during a pull is not a clean rep" is not supported: by the rows the pull was before the timed run, not in it. At worst it could have nudged the one-minute load average the gate read (0.29, which is within the usual 0.26-0.29 of every other row). No conclusion rests on that rep: gmkl-O2 is not even the reference build of G-MKL at N=2 (gmkl-O3 median 19.4767 is higher than gmkl-O2 19.4417), phase n2 carries no label, and no label of phase n1 is touched. Also the operator's own LOG argument ("the pull cannot pass unseen into a timing") rested on the foreign-load check, which only covers the timed window; here that point does not arise because the pull was outside it.

## Does anything make a labelled number untrustworthy?
No. All four labelled pairs are phase n1 on box1: 45 of 45 KEPT, 0 voids, 0 discards, load at start at most 0.29, outside load at most 0.0172 against 0.0285, clock drop at most 0.01 percent, Threads 1 in every row, frozen hashes equal, checks equal before and after, order balanced, nothing ran on box1 during that job by the log (LOG 16:00Z ruling 4; ssh to box2 at 18:43-18:47Z did not touch box1). No void rule, clock rule, thread rule or hash rule fires.

## Discrepancies
D1 (must_correct_in_report). RESULT.md section 3 (line 70) and the proposed register text say the 03:20:00Z pull was "during rep 0 of arm gmkl-O2". Rows: that rep's process ran 03:20:27Z to 03:21:10Z (before.t, t_end, wall 43.0 s); gmkl-O3 ended 03:18:56Z. Correction: say the pull happened in the gap between the arms gmkl-O3 and gmkl-O2 of rep 0, about 27 s before gmkl-O2 started (box1 clock not checked against penguin), so it is outside every timed window; the rep was KEPT with outside load 0.0161 against 0.032; the "doubt" paragraph can be dropped or reworded; keep the disclosure itself.
D2 (must_correct_in_report). The proposed register text says "hosts box2 and box3 (three clock discards each)". For box2 this holds (rows). For box3 only `discards=3` and `three_discards_on_this_host` exist; no rows, so the rule behind each discard cannot be shown (RESULT.md section 4 says so itself). Correction: "box2: three clock discards; box3: three discards (RESULT.txt reason three_discards_on_this_host; rows not copied)".
D3 (note). Committed rust1b_result.json (HEAD) has box2_n2 T hash 621456b156088648; correct value 621456b15608864d (box2/checks). The working copy is already right and its sha matches the evidence list; commit the working copy, not HEAD.

## Notes
N1. Start-of-run load was 0.25 to 0.29 in every row, at most 0.01 under the literal 0.3 limit. Already disclosed in RESULT.md (R1 reads the limit as a start-of-run gate). Not a trigger.
N2. The register has no mapping from this bar to met/not_met/inconclusive/invalid; "met = the bar produced its labels" follows rust-1 and rust-5. I cannot check the sibling precedent beyond the report text; it is a convention choice, not a validity finding. The pass mark's own INVALID text removes only "the affected label"; no labelled pair is affected.
N3. T at N=2 INVALID and the 3 voids mean phase n2 order balance (R9) is not exactly the design for reps 1 to 4 (11 rows one place earlier); disclosed; n2 has no label.
N4. RESULT-N1.md: the confirming read (section 8, 19:02Z) and the verifier corrections (LOG 19:03Z) are both in the single committed file; no later change. Anyone who reads "unchanged since its confirming read" should mean "since 19:03Z".
N5. Causes of the three n2 voids (03:34Z, 04:02Z, 04:15Z, 0.0322 to 0.0678 CPUs) are unexplained; the runner handled them by rule. No effect on labels.
