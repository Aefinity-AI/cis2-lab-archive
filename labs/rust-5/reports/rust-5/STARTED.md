# rust-5 STARTED
start (ledger): 2026-10-04T02:34:03Z, ref cm/rust-lab@98f2258317940b31df70ff14392c6975165a62e7
pass-mark sha256 after amendment (ledger bar_sha256): 376fa548ea2de9be9fc623ef5f95f17fa219bf2b1c74934d428809e7f3523b6d (registered: 2acf9b08...). Note: state/plans/rust-lab/bars/rust-5.txt is the original text (sha 3eb20293...), not updated.
penguin digest lines: none produced (nothing run on penguin after start).
Jobs (no --after, no real CPU quota; memory-max/cpu-quota): rust5-box1 (4500M/400%), rust5-box2 (2800M/200%), rust5-box3 (2800M/200%), rust5-box4 (2900M/100%, lite payload), rust5-box5 (1500M/200%, lite payload). Queue entries 002-rust5-box1, 004-rust5-box2, 002-rust5-box3, 004-rust5-box4, 004-rust5-box5.
Queue position at 02:35Z: box1 next after running dm-pilot11; box2 after running dm-pilot6 + rust2a digest + rust2a timing (3rd); box3 next after dm-pilot10; box4 after rust2a digest (running) + rust2a timing; box5 same as box4.
RESULT line: last line of each job's run output (RESULT: OK|OK-PARTIAL|INVALID|FAIL host=...), via cm-feed status "last done"; files on box under <home>/rust5 out dir, rsynced back by feeder (harness_time.out, k2_pass*.out, summary.json). FAIL host busy = nothing timed, re-queue. Redo wrappers: ~/feed-payload/jobs/rust5redo-s{0..4}-box{1..5}.sh.
