# rust-2b independent verification, 2026-10-16

Verifier did not build the lab. Own code (python3 -I, script /tmp/claude-1002/-home-justinbrianthompson/b2a72bbd-26dc-4f1d-a4dc-f061e0f3e23a/scratchpad/v.py), run from this directory over box1|box2/result.json and rows.jsonl (rows.jsonl == result.json rows, identical for both hosts). Scorer not run; scorer file sha256 prefix 2efc82ed4311c3e0 (matches A5 pin and the task note). SUMM-box1-box2.txt read, not regenerated.

## Checklist (BUILD.md line 172, mine vs SUMM-box1-box2.txt)

1. r at N=1, box1: PASS. T reps 3.3585 3.2588 3.2442 3.3791 3.3774 (median 3.358457); B reps 1.4962 1.4570 1.5111 1.5034 1.5054 (median 1.503401); r = 0.447646291. Scorer: same reps, r=0.447646291.
2. Loss at step 200 (mean of last 10, recomputed from the 200 stored losses for every rep): PASS. B 2.4778 (2.477787), T 2.4778 (2.477787); scorer 2.4778 / 2.4778. |diff| < 0.05.
3. PSS medians and ratio, box1 N=1: PASS. T 424351 kB, B 151603 kB, ratio 0.3573; scorer 0.357 (B 151603, T 424351).
4. Rep ranges: every T rep above every B rep (min T 3.2442 > max B 1.5111): PASS (the BEHIND clause needs this).
5. N=2 box1 (unlabelled): PASS. medians B 1.848946, T 5.289866, r 0.349526; scorer 0.350, 1.8489, 5.2899.
6. box2 values: N=1 INVALID confirmed: B rep 1 clock_drop 0.177 (scorer 17.7 percent); N=2 only T=1, B=2 OK reps (7 rows COST-CAPPED), scorer "NO LABEL valid reps T=1 B=2": PASS. cpu/wall box2 N=1 T 1.00 B 1.00, N=2 T 1.95 B 1.68; scorer same.
7. Frozen payload and binary hashes: PASS with a caveat. result.json "frozen" = payload 87b40101...2236, bin 7ce1acca...f932, equal to FREEZE-box1.txt PIN lines, to facts.bin_sha256 on both hosts, and to the bar's A2. The RESULT.txt OK lines do NOT carry the hashes (only the INVALID form of the line does, by run.sh design); the hashes are in result.json. WRAPPERS-FINAL.sha256: box1/run.sh sha256 = 3cf37ccd...a339a9bf equals the rust2b-run-box1.sh line and LEG.json script_sha256. box2/run.sh sha256 0770ba11... equals the rust2b-run-box2.sh line of WRAPPERS-box2.sha256, but WRAPPERS-FINAL.sha256 lists a different box2 run wrapper (b08e840f...); box2 is the unlabelled host, so not decisive, but note it. facts.freeze_file_sha256 box1 74c3c4b8...5dd38a (= sha256sum FREEZE-box1.txt = the freeze= in the cm-exp start ref); box2 521bbbd5... = sha256sum FREEZE-box2.txt.
8. Per-rep init/order/data hashes, n_params, warmup, steps equal the check's; threads_set == threads_seen == N on all 40 reps: PASS (box1 20/20, box2 13/13 OK reps).
9. Busy: no box1 rep with busy_before or busy_after >= 0.3 (max 0.062): PASS. box2 max 0.105 (T N=2 rep 1 before), also under 0.3.
10. Clock drop on box1: max 0.0009: PASS (<= 0.15). box2: only B N=1 rep 1 (0.177) exceeds: INVALID confirmed.
11. Check log: box1/check/check_equal.log ends CHECK PASS (loss diffs 3e-8, 4.6e-7; params 1.94e-05; grads 1.21e-06); box2 result.json check lines also CHECK PASS: PASS.
12. box1 timers restored: PASS. RESULT.txt line 1: "timers_restored=cm-tick.timer,cm-rc-watch.timer". Not checked: the live state of those timers now (would be a remote read; not done).
13. COST-CAPPED rows named: box1 capped=0; box2 capped=7: T N=2 reps 2,3,4,5 and B N=2 reps 3,4,5. PASS.
14. facts.memory_max: box1 4718592000, box2 2936012800: PASS.
15. mkl_warm=1 in every T rep: PASS (box1 10/10 T reps, box2 all OK T reps).
16. Thermal zones and throttle counters before and after every OK rep: PASS (present, box1 20/20, box2 13/13; all throttle counters 0). Quote, box1 T N=1 rep 1 before: zones 25.0/27.8/29.8/52.0 C, all cpu0..3 core_throttle_count and package_throttle_count 0; after: thermal_zone3 54.0, throttle all 0.
17. cpu.max: FAIL as recorded / cannot confirm. facts.cpu_max is null on both hosts (the runner records null when /sys/fs/cgroup cpu.max is missing). BUILD.md 4a item 9 says null/missing file means no quota applies, and box1 CPU/wall = 1.00 at N=1 argues no cap in effect, but the job itself did not record "max 100000". Not a bar condition.
18. cpu/wall: PASS. N=1 T 1.00 B 1.00 (my medians 0.998 and 1.002); N=2 Burn box1 1.322 (>1; scorer 1.32), T 1.994 (scorer 1.99).
19. FREEZE-box1.txt features line: PASS. "features = std, simd, rayon" for burn-flex; "burn-flex features as built: rayon simd std". Purity lines: no -sys crates, no C compiler drivers (unique packages 142; Cargo.lock 373; scorer "PURE RUST for B: yes").

## Could not check
- Live state of box1 timers now, box1 queue/journal (no remote access used).
- cpu.max actual value (not recorded by the job).
- Whether the pinned summ.py code is itself correct (I re-derived the numbers independently instead; not a code audit).
- box3: no result file; box3 unreachable.
- Wall time per rep is the job's own clock; not independently timed.

## Verdict against the registered bar
Loss condition applied first: |2.4778 - 2.4778| <= 0.05 holds. Deciding clause: "BURN BEHIND: r < 0.90 and every T rep value above every B rep value." r = 0.4476 < 0.90 and min T 3.2442 > max B 1.5111, so box1 = BURN BEHIND. "Overall = the box1 label (FRAMEWORK: BURN AHEAD, BURN BEHIND, or LEVEL...)". No INVALID cause applies to box1 (load, clock, counts, hashes, threads all clean); box2 INVALID only affects box2's reported line ("there it only affects their reported lines"). The bar is a BAR that can come out against Rust; a clean BEHIND is a measured result (it matched the 55 percent expectation, no surprise), not an invalid or inconclusive run. Memory: ratio 0.357 < 0.90 with B rep range (148321..152599) entirely below T (420540..425165): BURN LOWER.

Recommended verdict word: **met** (the bar resolved cleanly to a registered label on the labelled host; "not_met" would only apply if the bar were a prediction of Burn matching or beating PyTorch, which it is not). If cm-exp semantics treat "met" as "Rust wins", use the same facts with whichever word the operator's convention maps to "registered bar produced a valid label"; this is the only judgment call, the numbers are unambiguous. Not invalid, not inconclusive.

## Sentences to pass to cm-exp result (copied from SUMM-box1-box2.txt)
FRAMEWORK, not language (CPU, 1.8M-parameter byte transformer, 200 steps, N=1): Burn Flex, pure Rust is behind PyTorch on box1, steps/s ratio r=0.4476463, final loss 2.4778 against 2.4778.
FRAMEWORK: BURN BEHIND. Scale: 1 to 5 million parameters on CPU only; GPU training and 135M to 360M models are untested.
FRAMEWORK (memory): Burn peak PSS is lower than PyTorch on box1, ratio 0.357; no-Python effect, not a Rust-language effect.
(also carry: "LABEL: framework, not language" and the Scale line from the top of SUMM; box2 N=1 INVALID clock drop 17.7 percent, box2 N=2 NO LABEL 7 COST-CAPPED rows, box2/box3 unlabelled per Rule A.)

## For NEEDS/BLOCKERS
Nothing blocking. Minor: WRAPPERS-FINAL.sha256 box2 run wrapper hash differs from the box2 wrapper actually run (WRAPPERS-box2.sha256 matches), and cpu_max null; both worth a line in the final report.
