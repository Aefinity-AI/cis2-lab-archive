# VERIFY-RESULT-R1 (rust-4b, independent result verifier)

## Verdict
CONFIRMED. Registered word: **met** (box1 pair label RUST BEHIND, r = 0.8204, valid reps, no redo needed). Agrees with the scorer (SUMM-OUT.txt) on label, r, ledger word and SURPRISE.

## Mismatches
None found. Notes (not mismatches):
- My script labels box2, box4, box5 "BEHIND" and box3 "INCONCLUSIVE" by the band arithmetic; Rule A says these hosts carry NO label word. They are numbers only. The scorer correctly prints "no label (Rule A)".
- box1 P/R = 3.025 is only just above 3. Held, but a narrow margin.
- Pin and hash fields in result.json match the pass mark values; I compared the three named hashes only, not the file contents on the boxes (read-only, not re-hashed).

## Key numbers (from box1/rows.jsonl, wall_to_open_s of KEPT rows; box1/result.json)
- bar_sha256 f37da0bcd1966ca3d6962b0ef149f7383ca7fb55a91b3d6452cc6b9773b1cba7 (recomputed from `bin/cm-exp show rust-4b`, equal).
- box1 R median 12.6928 s; C median 10.4127 s; r = C/R = 0.82037. Fastest R 11.9185 s; slowest C 10.7433 s, so every C rep is faster than every R rep. r < 0.95: RUST BEHIND band holds. Redo not applicable.
- box1 other medians: P 38.3982 s (P/R 3.0252, P/C 3.6876, both above 3: operator P line held); expectation TIE (carried 60 percent, operator 50): SURPRISE; operator class RUST BEHIND 25 percent.
- Counts: 5 kept reps for each of R, C, P, Rv, Cv, Q; 0 discards, 0 voids, 0 not-cold repeats; elapsed 1,122 s of 5,400 s cap.
- Pins (result.json): payload sha256 939a31be... = frozen; run_py 337a6e17... = frozen; helper a08c989b... equal; gate witness ecafd089... equals pinned witness; gate_after R and C both equal the same witness; mismatches 0 in all kept rows; rc 0.
- Controls: warm_open 65,689/65,689 pages (100 percent); cold_open 0 pages; warm_final 65,689/65,689 (100 percent). Every KEPT row has check.resident_pages 0, errors 0, drop_ok true.
- Clock/load: every row has foreign load within limits (limit_arm 0.044, limit_host 0.1), thr_changed false, scaling_max unchanged, other_units empty. HOSTCHECK open/close lines: thr 0, no other units, MHz about 2,095 to 2,100.
- Timers: timers_paused and timers_restored both cm-tick.timer,cm-rc-watch.timer (RESULT.txt).
- Positions (rows): mean positions R 2.4, C 2.4, P 2.4, Rv 2.6, Cv 2.6, Q 2.6 (equals result.json design_mean_positions).
- P: probe rc 0, venv_files 29,942, venv python regular, wheelhouse sha256 21360ef9... equal to pin. Disk ST4000LM024-2AN1, ext4, rotational yes (1).
- Other hosts (numbers only, no label): box2 r 0.7755 (R 8.604, C 6.672 s; P 13.109 s, 1.52x R, so Python expectation SURPRISE, informal); box3 r 0.7489 (reps overlap: R min 15.68 < C max 18.25; P 57.883 s, 3.17x R, 4.24x C); box4 r 0.8346 (P and Q NOT RUN rc -4); box5 r 0.9213 (P and Q NOT RUN rc -4). All hosts: controls pass, 0 not-cold, kept rows resident_pages 0, pins match, elapsed 714/1,593/942/1,105 s. Discards/voids: box2 1/3, box3 5/6, box4 1/1, box5 3/0 (all within 6/8 budgets).
- Ledger mapping: box1 pair got a band label on valid reps and expectation recorded SURPRISE: met ("met" does not say who is ahead).

## What I ran
- `bin/cm-exp show rust-4b` (bar saved to ~/scratch-results/rust-4b/bar.txt, sha256 recomputed).
- ~/scratch-results/rust-4b/v.py: reads box1..box5 result.json and rows.jsonl, checks pins, controls, kept-row residency, counts, positions, recomputes medians, r, band label, P factors.
- An inline check of per-row foreign load, throttle, scaling and other-unit fields for box1; grep of box1 RESULT.txt and run.log for timers and HOSTCHECK.
- Nothing run on any box; no other file written.
