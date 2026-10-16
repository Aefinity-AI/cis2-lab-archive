# rust-2b pre-start read, lens CONFORMANCE, round 5 (2026-10-05, 19:2xZ to 19:31Z, reader subagent)
Verdict: START. 0 MUSTs, 2 SHOULDs. Nothing was built or timed. No steps-per-second or wall-time number was produced.
Ruling version 3 facts: all right. Change record: complete in substance, one wording-level gap (SHOULD 1), so "ruling sound" is answered NO in the strict sense of the question (every difference named); no statement of fact is wrong.

## MUST
None.

## SHOULD
1. RULING-A1.md version 3 changes two things the change record does not name: (a) the sentence "The choice itself ..." was reworded: "(A1 is the registered arm)" added, "unchanged" became "the same in all three versions", "the wrong clause" became "either wrong clause"; (b) the sentence "The first version is in the repository history (commit ce3d37bd, sha256 be983c2d...)" was dropped (its content now stands in the Version 1 line of the record). No fact is affected. The record says only "this change record replaces that paragraph", which does not cover the choice paragraph. Do not re-sha the ruling for this. Either accept it, or name it in BUILD.md section 0b line 15 ("the choice sentence was reworded; the repository-history sentence was folded into the Version 1 line").
2. Step 6b runs a probe on box1 with `cm-feed once`. If the build job of step 4 is still queued or running on box1 at that moment, the probe is pushed by the same `once`; say "after the build job is finished and harvested" in 6b (step 4 and 6b order already imply it; text only).

## What I checked and how
### 1. Ruling version 3
- sha256 recomputed: current file ca89995d8ef17c94a044f3d15c29a2c78c85bb298ef1216d3e3d8a80a495fd43 (equal; mtime 14:15:00 -05:00 = 19:15Z); `git show acc7a9c3:...RULING-A1.md | sha256sum` = 5fac4a00c513db54655a7125d1be69ca936bc9e77cab57ad569dc49379b210f7 (equal); `git show ce3d37bd:...` = be983c2d6e917fb8e353b2b15c7fe9ca476f2c60a455f1d90e1da6f1083e860b (equal). Commit acc7a9c3 committed 13:48:16 -05:00 = 18:48Z.
- Word-level diffs (git diff --no-index --word-diff, copies in the scratchpad): v2 to v3 and v1 to v3. Every difference is in the record's list (change record; fact 3 last sentence; lock wording "the spin crate's lock may cost time against parking_lot's"; split of the 18:16Z paragraph and new "Added at 18:43Z ... (not part of the 18:16Z decision)"; "most likely came from"; facts heading; Use bullet) EXCEPT the two items in SHOULD 1. v1 to v3 differences (fact 1 readers, fact 2, fact 3 crate wording, fact 4, "Decided now" to "Decided at 18:16Z", Use bullet) are all in the version 2 list (a) to (h). Times right: v1 18:16Z, v2 18:43Z (re-check 18:41Z to 18:44Z), v3 19:15Z.
- Fact 3 last sentence against the source on box1 (read-only sed/grep, no cargo): graph.rs line 18 `use hashbrown::{HashMap, HashSet};` always; lines 20-21 `#[cfg(feature = "std")] use parking_lot::{Mutex, MutexGuard};`; lines 23-24 `#[cfg(not(feature = "std"))] use spin::{Mutex, MutexGuard};`. lib.rs lines 40-46: `mod collections`: without std hashbrown, with std std::collections. Cargo.toml: `std = ["dep:parking_lot"]`; default = std, tracing; hashbrown, parking_lot, spin are dependencies. Other modules use the facade (memory_management.rs, server.rs, traversal.rs, retro_forward.rs use `collections::`). The sentence is right, including the parenthesis about the graph module.
- Facts 1, 2, 4: re-read; README line 49 "Default: `std`, `simd`, `rayon`." (box1 registry). Fact 4 numbers equal R4's checks (177 against 142, 35 more, 356 added, 729 entries, dirs-sys). Nothing stronger than its evidence. Reason 4 and the "expects" sentence say expectation, not measurement.
- The 18:43Z sentence is now in its own paragraph "Added at 18:43Z ... (not part of the 18:16Z decision)": clearly outside the 18:16Z decision. The header line "written 18:16Z" is the first-written time and the record gives versions: fine.
### 2. Citations and pins
- Amendment header (line 41) and BUILD.md lines 5, 15, 16, 94, 126 (amend-bar --reason), 185 (10b item 7) name ca89995d... and both times 18:43Z and 19:15Z. 5fac4a00 and be983c2d appear only in BUILD.md line 15 (and in 0c line 21 as "version 2, hash in section 0b"), as history with commits.
- Amendment sha256 b0aa8743c32a8a56f4ebe9db87c3a852429be55092832951e8c368c0371a6891 (equal to the fixer's); BUILD.md ae0af6aaf4c30413e6eb89beacb8d67d69a194bc689ee94bc0d97e32d733f58b (equal).
- First 9,968 bytes of the amendment equal rust-2b.txt (python byte compare True); first 9,967 characters hash to 745d9933...; `git diff -U0` against the last committed amendment (17dbb475): one line changed, line 41 (header) only. No pin, hash or number of A1 to A5 changed.
- Every pinned file hashes to a hash named in the amendment (python/sha256sum loop, 15 files incl. inputs, arm_b, scorer files). `git -C .../rust2b status --short .` empty (before and after the tests); `git diff ab68f1a -- .` empty.
### 3. R4 SHOULD 1 to 5 in BUILD.md
- 1(i) FREEZE features line: build_box.sh line 21 does echo "features: burn = =0.21.0, default-features=false ... burn-flex = =0.21.0 (direct) ..."; step 8b (d) says ignore it for the docbuild and quote "burn-flex features as built". Correct.
- 1(ii) full add lines at BUILD.md lines 157-158; --memory-max 3000M / 200% and 4500M / none equal step 4 (line 136) and step 7 (line 144). 1(iii) registry exposure (327 crates) in (e) and section 5. Applied.
- 2 step 6b before step 7 (line 141), uses `cm-feed add ... --cpu-quota none` + `once`, reads result_line in FEED.json (field exists). Applied.
- 3 bin/cm lines 194 to 197 (read: comment 194, local 195, test 196, systemd-run 197); bin/cm-feed 327 to 329 (read); commit acc7a9c3 named with 18:48Z (13:48:16 -05:00); bin/cm line 29 cosmetic named. Applied.
- 4 section 5 lists R4 reads, operator reads, feeder probe, this round. 5 time stamps in one place, line 15. Applied.
### 4. Quota facts
- state/feed/cm-box5/done/quotaprobe-feed-none/FEED.json: status ok, pushed 19:15:23Z, harvested 19:15:41Z, result_line "... leg-quotaprobe-feed-none.service cpu.max=[cat: .../cpu.max: No such file or directory]". job.json: cpu_quota "none", memory_max 100M, added 19:15:17Z. Script sha256 prefix e85d421c9d73fbd1 (equal).
- box1 RESULT.txt: none "max 100000"; 300 "300000 100000"; default "300000 100000". BUILD.md says exactly this.
- run_box.py lines 88-91: cpu_max read in try, `except Exception: ... = None`: null when the file is missing. Line 8 comment "cm leg push always sets a CPUQuota; 400 percent ... effectively no quota": stale. BUILD.md names it in 10b item 15 and doubt 14 ("pinned, cannot change"). Both "null" and "max 100000" are called no quota. Right. The "reading" (no CPU controller files when no sibling unit has a quota) is labelled a reading, not a measurement: acceptable.
### 5. Edits broke nothing
Steps 0 to 11 with 3b, 3c, 6b, 8b in order; cross-references (0b MUST 2, step 6b, step 7, 10b item 15, doubt 14) point to the right places. No step contradicts the pass mark (8b is unlabelled and after harvest, own folders). The only time in the text is "about 8 minutes" (build, section 5). No speed or wall time of the registered configuration.
### 6. Tests (penguin, systemd-run scope MemoryMax=500M, TMPDIR on disk, free -m available 2017 MB before)
SELFTEST PASS 70 checks
MUTCHECK PASS 58 of 58 mutants caught
WRAPPER TEST PASS 14 ok 0 failed
Package `git status --short .` after: empty.

## Needs entry
None for Justin. Operator: nothing blocks `cm-exp amend-bar`. Scratch left in place: scratchpad copies of v1, v2, v3 and diffs; $HOME/tmp-kaggle (test temp).
