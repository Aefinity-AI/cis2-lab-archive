# VERIFY-PREREG code lens, read R3, lab rust-4b (2026-10-05, penguin, read-only; scratch <home>/scratch-rust4b/verify-code-r3)
VERDICT: FIX_FIRST (one MUST, a selftest-only gap that does not touch run.py, any pin or any wrapper). Everything else is a SHOULD.

## What was run (last lines)
- Selftest (copy of the folder, HOME and scratch redirected): "SELFTEST PASS: 95 passed, 0 failed".
- Smoke batch of 9 scenarios on a reflink copy of the payload (full, order, notcold3, warmfail, coldctl3, warmfinal, cap, nostack, nosudo): every RESULT word as expected, order arm_status as expected, last lines "SMOKE ASSERT PASS" / "done". Every wall, sector and fault value in rows.jsonl is null (29 rows each); no timing value printed.
- wrapper_test.sh (stub systemctl, 8 cases): timers paused and restored (case 1), failsafe cannot be armed (2), TERM to wrapper+runner (3) and to the wrapper alone (3b: restored within 8 s, runner_alive=0), box2 untouched (4), payload differs (5) and runner differs (6) give INVALID before anything runs, redo10 carries R4B_REPS=10 (7).
- Nothing queued, registered or pushed: cm-exp list shows only rust-4 (invalid); cm-ledger status has no rust-4b (seq 197 E-0062); worktree commit c340f1a is not on any remote branch.
- DISCLOSURE of my own slip: my first smoke start ran with the real payload dir as run.py's W and created ~/feed-payload/rust4b/out/penguin-smoke/<job>. I killed it, removed that out/ folder (rm -r out), and re-checked: sha256sum -c PAYLOAD_SHA256 = 0 differences, folder listing as before (only the directory mtime moved). The smoke then ran on a copy in scratch. Note for the operator: smoke.sh/run.py write out/ under the payload folder, so running the smoke on the real payload dir leaves an out/ folder there (harmless to the hashes, which cover named files only).

## Hashes (all equal on disk)
- 21 source lines of FREEZE section 1 (run.py, filelists.json, resident.c, build_helper.sh, make_*.sh/py, selftest.py, summ.py, smoke*.sh, wrapper_test.sh, trace_*, estimate.py, p/*, inputs/*): 0 DIFF. Payload run.py == repo run.py (cmp).
- sha256sum -c PAYLOAD_SHA256 (every payload file incl. 34 wheels, R, C, llama drivers, GGUF, helper): 0 failures. PAYLOAD_SHA256 itself 939a31be... equals the pass mark PIN and both wrappers' EXP value; run.py 337a6e17... equals PIN and EXP_RUNPY.
- Six wrappers on disk equal the six PIN lines (5bb6bd4a, 2e383a8f, e13dee96, 0fda13b4, 8a45683c, a8a6ed2c) and the repo copies (cmp).
- R d0f8ec89... and C 5a6ccc32... in the rust-4b payload equal ~/feed-payload/rust4/bin (sha256 of both). Weights 80521b40, config 1d556eab, tokenizer 9ca9acdd, prompts.jsonl 4b4e7924 match the pins. GGUF 8de5be71 and the two llama drivers equal rust-1b FREEZE-STAGE2.
- Runner on a real host compares PAYLOAD_SHA256 and run.py with the wrapper's frozen values, then every payload file against the list, then weights/config/tokenizer/GGUF pins (read in run.py main); wrappers verify before python runs.

## Runner diff against rust-4 run.py
1140 diff lines: a rewrite around D1 to D6 (new cold check, controls, order, cap, rows). I read the whole new timed path (helper_check, drop_caches, warm_control, cold_control, attempt, timed_phase, main). Nothing found that the design does not ask for, apart from the guards already declared in the pass mark (empty file / non-regular file not cold, REPS 5 or 10 only) and the 7200 s per-run timeout noted in SHOULD 1.

## Helper (resident.c)
Page count from file size (ceil(len/page)), whole file mapped, MAP_SHARED PROT_READ, mincore vector freed. Tested on btrfs scratch (not tmpfs), file of 100 pages + 123 bytes (101 pages):
- after DONTNEED: SUM resident_pages=0 total_pages=101; after a full read: F 101 101 ...; after DONTNEED again: 0.
- empty file: counted empty=1 (0 pages); missing file: "E 2"; permission denied: "E 13"; directory: "N"; symlink: followed, reports the target's pages (right); /proc file: empty=1 (runner refuses an empty file on a frozen list).
- tmpfs (/dev/shm, 10 pages): F 10 10 -> fully resident, so the cold control fails there (matches the pass mark).
- Unreadable list "-l /nonexistent": rc 2, no SUM. No arguments: rc 0 and a SUM with files=0 (see SHOULD 3). Errors and missing files cannot read as cold because the runner requires errors==0.

## D3 controls and mutants (scratch copy of run.py, selftest run on each)
CAUGHT (selftest FAIL): a warm threshold removed; WARM_MIN=0; cold check skipped in attempt; cold check skipped in cold control; one resident page tolerated (attempt, control, 1 percent); helper failure read as zero pages; helper exception read as zero pages; errors ignored; non-regular ignored; drop_ok ignored; drop skipped in every attempt; drop skipped after rep 1; drop skipped in the cold control; drop return code ignored; MAX_NOTCOLD 99; COLD_CTL_TRIES 9; cap test bypassed (return True); not-cold rep not repeated at the same place; helper check before the drop; P venv walk dropped; helper fed only the first path; weights removed from the file lists. Not run as a selftest mutant but covered by the smoke table: warm control after the last rep (warmfinal scenario expects INVALID).
SURVIVED: "d4" = remove `and (chk["total"] or 0) > 0` from the cold decision in attempt(): selftest 95/95 PASS. It is unreachable on real lists (a frozen list with total 0 is all-empty and the empty guard catches it; P's list holds non-empty files), but no test bites it, and the rule is that a surviving mutant is a MUST. Fix below.

## Other checks
- Own drop and check per arm run: drop_caches(paths) and helper_check(paths) are inside attempt(); order drop, then check, then spawn is asserted by selftest; mutants e2/e3/j die.
- Discarded rep repeated at the same place: NOTCOLD/DISCARD/VOID do `continue` in the same position loop; consecutive-not-cold counter resets on a cold pass; 3 in a row ends the arm only.
- Order: DESIGN rows are permutations. n=5: all arms mean position 2.0. n=4: sums 7,7,8,8 (R and C 1.4). n=6 (box1 with P and Q): sums 12,12,12,13,13,13 (means 2.4 / 2.6; R and C 2.4 equal). No arm at the same place in consecutive orders, wrap included. "Every arm the same mean" is arithmetically impossible for 6 arms in 5 rows; the pass mark states this (disclosure g). If P or Q drops out mid-job R and C positions can differ (order_for skips the absent arm).
- Cap: cap_ok is tested before every attempt (each not-cold retry too); elapsed counted from job start incl. install and probes; budget file subtracted. A started run is not stopped at the cap (SHOULD 1).
- sudo: only the drop command and the probe `sudo -n sh -c true` (grep of run.py and all wrappers); wrappers use systemctl --user only.
- box1 wrapper: EXIT trap restore_timers (stops failsafe, starts the paused timers, writes timers_restored, writes RESULT if the runner left none); TERM/INT/HUP trap kills the runner child and exits 143, which fires the EXIT trap; PAUSED is set before systemctl stop; failsafe timer 7200 s covers SIGKILL. Tested by wrapper_test cases 1 to 3b.
- summ.py band(): 0.95 <= r <= 1.05 TIE, AHEAD needs max(R) < min(C), BEHIND needs max(C) < min(R), else INCONCLUSIVE; matches the pass mark. Cost estimate: estimate.py reproduces 1,624 / 2,815 / 2,788 / 1,568 (pass mark 1,569) / 1,768 s and 10,536 s (pass mark 10,537, rounding).

## MUST
1. Selftest does not bite the "total pages = 0 with no error counts as cold" mutant (d4). Fix (selftest.py only; run.py, payload, wrappers and every PIN unchanged; only the selftest.py sha256 line of FREEZE section 1 and the freeze revision text change):
   in install_fakes()'s helper(), insert before the line `nr = getattr(sc, "nonreg", {}); em = getattr(sc, "empty", {})`:
```
        zleft = getattr(sc, "zero", {}).get(arm, 0)
        if zleft > 0:                               # a helper that saw no page at all (total 0, no error): the attempt must be NOT COLD
            sc.zero[arm] = zleft - 1
            return {"resident": 0, "total": 0, "files": 1, "errors": 0, "nonzero": [], "err_paths": [], "rc": 0, "nonregular": 0, "empty": 0}
```
   and before the line `sc = fresh(); sc.errs = {"C": 1}` add:
```
sc = fresh(); sc.zero = {"C": 1}
install_fakes(sc)
m2 = R.timed_phase(["R", "C"], {}, arms_est(["R", "C"]), "W", 10.0)
check("guard: a helper that reports 0 total pages and no error is NOT COLD (the attempt is repeated)", [c for c in sc.calls if c[1] == "C"] == [("check", "C"), ("check", "C"), ("run", "C", "m2-C-1")] and R.STATE["notcold"] == 1, [c for c in sc.calls if c[1] == "C"])
```
   Verified in scratch: original run.py gives "SELFTEST PASS: 96 passed, 0 failed"; run.py with the d4 mutation gives "SELFTEST FAIL: 95 passed, 1 failed" on that check. Patched selftest.py sha256 (my scratch copy, t4/selftest.py) 451714831bf9f7c7acc1dd8532f158aa3f2b0a96f77a59948b6fdaa2a5dc5e76. Update FREEZE (selftest.py hash, "96 passed") and the pass mark disclosure (n) count if it quotes 95.

## SHOULD
1. RUN_TIMEOUT_S = 7200 applies to every arm run and the install, but the cap is 5,400 s and the box1 failsafe fires at 7,200 s: a hung arm (stuck disk read) can run 1.5 h past the cap, and the failsafe would restore cm-tick while the job still runs. Better: kill an arm run at min(7200, max(600, 5 x its estimate), remaining cap). Changes run.py (new hash, all wrappers, all PINs), so only do it if a re-freeze is happening anyway; otherwise add one sentence to the pass mark: "A started arm run is not stopped at the cap; the per-run timeout is 7,200 s."
2. helper_check never compares the helper's SUM files= with len(paths); add `chk["files"] == len(paths)` to the cold decision (needs a run.py change; same remark as 1). The lists are never empty and a path with a newline fails safe (E lines), so no known failure.
3. Helper with no arguments and no list prints a SUM with files=0 and rc 0 (cannot happen through the runner, which always passes a list).
4. The runner never reads the helper's rc for a decision (pass mark says so, correctly). A helper that exited non-zero after writing a clean SUM would be accepted; impossible with this source (rc 0 whenever SUM is written).
5. order_for: when P or Q drops out mid-job, R and C positions are no longer equal-sum; record the realised positions per arm (already in M2 positions) and say in the result that balance holds only while no arm dropped out (pass mark disclosure g already says so for R and C).
6. smoke.sh / run.py write out/ under the payload folder (W). Say in BUILD.md: run the smoke on a copy of the payload, or delete out/ afterwards.
7. The P cold-run estimate (100 s / 200 s) is a guess; the first P attempt is cap-tested with the warm probe time + 10 s. Harmless inside the 5,400 s cap on all hosts (box1 1,624 s) but state that est["P"] is the warm probe time until the first attempt.

## CONFIRMED (not at fault)
Hashes and pins, helper semantics on disk and tmpfs, 21 of 22 mutants dead, smoke table, wrapper traps, order balance as stated, cap test per attempt, sudo only for drop (+ same-shape probe), timing masked in smoke, nothing queued/registered/pushed.
