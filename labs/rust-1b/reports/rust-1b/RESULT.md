# rust-1b RESULT (final), 2026-10-05

Status: Published 2026-10-16 as part of the CIS-2 archive. Nothing in this file is recorded, queued or published by this file; the operator records.

Lab: "Rust with libraries, PyTorch and llama.cpp: decode speed and memory on SmolLM2-135M". It is part of the Rust lab. It answers FRAMEWORK (one stack against another stack) and KERNELS (our own matrix-vector kernels against the library kernels inside torch) and nothing else. It does not answer LANGUAGE, IMPLEMENTATION or TOOLCHAIN. The five answers are never blended.

Law used: the amended pass mark, file state/plans/rust-lab/bars/rust-1b-amended-bar.txt, sha256 b1d2fdb1303c362f647885fe0cf9e0f7eed8d026cc4ebc817b31ccc5e07e8671 (equal to the register bar_sha256 and to the sha256 of the file; the file has no final newline). Freeze file sha256 43ec5523...94d3 (recomputed, equals the start record). Registered 2026-10-04T09:17:01Z, pass mark amended 16:00:13Z, started 16:04:24Z.

How I scored: my own script (standard library only, scratch ~/scratch-rust1b-final/result/score.py) reads rows.jsonl and checks/ of box1, box1-n2 and box2 and recomputes each per-rep value as 8 x 63 tokens divided by the sum of the 8 prompt walls. Largest difference from the value the runner stored: 4.9e-07 tokens a second. Terms: "tok/s" is tokens a second (higher is faster); "median" is the middle of five repetitions ("reps"); "r" is the left arm's median divided by the right arm's median; "PSS" is the memory a process is charged for, counting shared pages fairly.

## 1. The answer, in plain sentences

Verdict word for the register: met. How the pass mark gives it: the pass mark has no mapping to the four register words. It prescribes one sentence per outcome and says the bar "can come out against Rust, for Rust, or as a tie". Every label of phase n1 on the labelled host box1 is decided (four of four AHEAD, reps separated, none INCONCLUSIVE, none INVALID, none NOT RUN, none COST-CAPPED), and no INVALID condition of the pass mark touches a labelled pair. The sibling lab rust-1 had the same shape (a two-sided bar, outcome LEVEL) and was recorded as met, with the label in the summary; I follow that. "met" here means "the bar produced its labels", not "Rust won". Open point: the word does not say who is ahead; the labels carry the answer, so always quote them with it.

FRAMEWORK (stack against stack, not language). On box1, one thread, SmolLM2-135M, 64 forced tokens for each of 8 prompts:
- The Rust program calling OpenBLAS (G-OB) is ahead of PyTorch fp32 + MKL (T): 18.567 against 13.880 tok/s, r = 1.338.
- G-OB is ahead of llama.cpp F32 (Q): 18.567 against 15.532 tok/s, r = 1.195.
- The Rust program calling MKL (G-MKL) is ahead of PyTorch: 18.096 against 13.880 tok/s, r = 1.304.
- Kernels differ unless G-MKL was used. G-OB and G-MKL are not pure Rust (they call C or Fortran libraries). The ahead-of-torch result is for this torch set-up (manual loop, no compile, Python in the timed window, one thread). It is not a statement about PyTorch in general.
- Two of these three had a written expectation (G-OB against T, G-OB against Q); both went against it. G-MKL against T had no written expectation and went the same way as G-OB.

KERNELS (our Rust kernels against MKL inside torch). The Rust-fast engine X is ahead of torch on box1, r = 1.303 (18.090 against 13.880 tok/s). This is a statement about our kernels. The engine replaces the matrix-vector product alone; attention, softmax and rope stay on the strict scalar path that G shares. X is pure Rust. SURPRISE (expected behind, about 60 percent). X is within 3 percent of G-OB and G-MKL (ratios only; the pass mark has no pair for this), so the four fast arms sit together and torch and llama.cpp sit behind.

Headline sentence of the pass mark: "framework: G-OB against T ahead, G-OB against Q ahead, G-MKL against T ahead; engine: ahead."

No sentence of the form "Rust is faster than Python" is written or implied.

## 2. Labels of phase n1 on box1 (N=1, 5 reps each, labelled host), with the rule beside each

Rule quoted (Band W): "r = left arm median speed / second arm median speed. LEFT ARM AHEAD: r > 1.10 and non-overlapping reps. TIE: 0.90 <= r <= 1.10. LEFT ARM BEHIND: r < 0.90 and non-overlapping reps. Overlap outside the band: INCONCLUSIVE, redone as 10, then TIE (NOT SEPARABLE)." Reference rule (R4): the reference build of a Rust arm is the opt-level (2 or 3) with the higher median over its kept reps.

Per-arm values (tok/s, reps 0 to 4; median):

| arm | reps | median | range |
|---|---|---|---|
| G-OB O2 | 18.27 18.43 18.53 18.38 18.50 | 18.4350 | 18.272..18.531 |
| G-OB O3 (reference) | 18.76 18.48 18.59 18.54 18.57 | 18.5670 | 18.482..18.762 |
| G-MKL O2 | 18.00 17.99 18.11 18.09 17.96 | 18.0045 | 17.961..18.110 |
| G-MKL O3 (reference) | 18.01 18.14 18.06 18.10 18.15 | 18.0955 | 18.010..18.146 |
| X O2 (reference) | 18.02 18.22 18.07 18.25 18.09 | 18.0897 | 18.016..18.254 |
| X O3 | 17.66 17.94 17.93 18.11 18.12 | 17.9417 | 17.659..18.116 |
| T (PyTorch) | 14.14 14.10 13.88 13.63 13.74 | 13.8799 | 13.629..14.140 |
| Q (llama.cpp F32) | 15.43 15.52 15.53 15.61 15.56 | 15.5323 | 15.428..15.610 |
| Q8_0 extra, "different arithmetic" | 27.01 27.27 27.24 27.25 27.23 | 27.2369 | 27.013..27.267 |

| pair | r | label | rule beside it | reps |
|---|---|---|---|---|
| FRAMEWORK G-OB (O3) against T | 1.3377 | LEFT ARM AHEAD | r > 1.10 and non-overlapping | lowest G-OB rep 18.482 above highest T rep 14.140 |
| FRAMEWORK G-OB (O3) against Q | 1.1954 | LEFT ARM AHEAD | r > 1.10 and non-overlapping | 18.482 above 15.610 |
| FRAMEWORK G-MKL (O3) against T | 1.3037 | LEFT ARM AHEAD | r > 1.10 and non-overlapping | 18.010 above 14.140 |
| KERNELS X (O2) against T | 1.3033 | LEFT ARM AHEAD | r > 1.10 and non-overlapping | 18.016 above 14.140 |
| X (O2) against Q | 1.1647 | no label (ratio only, by the pass mark) | "X against Q is reported as a ratio with no label" | separated |

Pair-choice check (not the rule): every opt-level of every Rust arm against T and Q is also AHEAD and separated; lowest r against T 1.2926 (X O3), against Q 1.1551 (X O3). No choice of build moves a label. No label is INCONCLUSIVE, so the single 10-rep redo was not called.

Extras with no label: Q8_0 is 1.754 times the F32 Q arm (different arithmetic, 17 arg-max mismatches of 576 positions in the check, exempt by R3). Non-reference builds: G-OB O2 18.435, G-MKL O2 18.004, X O3 17.942.

Comparison with RESULT-N1.md (interim, not edited): all nine arm medians, all pair ratios and all memory medians are the same as in the interim file (to the digits it prints). No difference in any number. Wording differences only: this file states the memory line in true same-day wording (the interim file did too) and writes the pair-choice check above.

## 3. Phase n2 on box1: NO LABEL (two threads)

The pass mark: "N=2 on box1 and box2 is reported with no label". Job rust1b-box1-n2, 2026-10-05 02:58Z to 04:29Z, RESULT PARTIAL, reason arms_not_ok t@n2. CPUs 0 and 1 for the arm, runner on CPU 2.

The PyTorch arm is INVALID at two threads by the Threads rule ("Threads in /proc not equal to N"). The one T row (rep 0, order place 1, 03:11:11Z) has status INVALID, problem threads_not_2(max=4): /proc showed 4 threads while 2 were asked. It has no timing value (no decode times kept), and T was not run again in reps 1 to 4. BUILD.md item 7 and the operator's ruling of 2026-10-04 16:00 named this in advance (the same 4 threads showed in the untimed run on penguin). T's untimed checks passed (0 mismatches, largest logit difference 0.000206). So there is no T number at N=2 and no pair with T exists in phase n2.

Other six arms, 5 kept reps each (tok/s, median): G-OB O2 19.0518, G-OB O3 19.0638 (reference), G-MKL O2 19.4417, G-MKL O3 19.4767 (reference), Q 20.5076, Q8_0 45.1605 ("different arithmetic"). Ratios, no label: G-OB / Q 0.930 (the number alone would sit in the TIE band, and no label is given); G-MKL / Q 0.950; G-MKL / G-OB 1.022. Two threads against one thread on box1: Q 1.320 times, G-OB 1.027, G-MKL 1.076, Q8_0 1.658. So at two threads llama.cpp F32 and the Rust arms are in the same range, with no label (the order differs from phase n1 in the raw numbers); with one job I draw no conclusion beyond the numbers.

Peak PSS medians at N=2: G-OB 541.7 MB, G-MKL 547.2 MB, Q 587.2 MB, Q8_0 200.0 MB. Threads in /proc: 2 for every valid arm.

The operator's 03:20:00Z pull (disclosure required): on 2026-10-05 at 03:20:00Z, in the gap between two arm runs of phase n2 on box1 (the previous arm, gmkl-O3, ended 03:18:56Z; rep 0 of gmkl-O2 ran 03:20:27Z to 03:21:10Z, wall 43.0 s, so the pull came about 27 s before that rep started and outside every timed window; the box1 clock was not checked against penguin's, no ssh), the operator pulled two small row files of another lab (tm-6) from box1 with one rsync (reasons in LOG 03:01Z). The runner KEPT rep 0 of gmkl-O2: recorded outside load 0.0161 against the limit 0.032. Its value, 19.441674 tok/s, is the median of that arm's five reps. Phase n2 carries no label, so no label is touched, and gmkl-O2 is not the reference build (gmkl-O3, median 19.4767, is higher). No conclusion rests on it.

## 4. box2 and box3: no label, both INVALID

Pass mark words: "box2 and box3 are REPORTED with no label ('informal per Rule A')"; "box3 is the same CPU as box2 (N4020) and does not supply a second class"; "three discards on one host make that host INVALID". box2 and box3 are Celeron N4020 machines (2 CPUs, no AVX2, schedutil governor, max 2.8 GHz), run with the sse42 llama.cpp build.

box2 (job 2026-10-04 18:41Z to about 20:00Z, elapsed 4,517 s): RESULT INVALID, reason three_discards_on_this_host. All three discards were the clock rule (a drop of more than 15 percent below the reference: 0.203 on G-OB O3, then 0.231 and 0.185 twice on G-MKL O3), all in the opening rep 0. Seven reps were kept (rep 0 of each of 7 arms; G-OB O3 was kept at its second try). One rep per arm gives no median and no label; the single values (tok/s) are G-OB O3 6.535, T 5.065, Q 7.431, X O2 6.338, X O3 9.098 (note: 1.44 times X O2 in the same rep, so the host clock was not steady), Q8_0 12.595, G-MKL O2 5.371. They are shown for the record and are not read. Phase n2 on box2 did not run (0 reps). Untimed checks passed for every arm (largest logit difference to L-C: G-OB 0.000194, G-MKL 0.000179, X 0.000183, T 0.000172, Q 0.0845). The operator's ssh calls to box2 between 18:43 and 18:47Z (a process listing and a sha256sum of three model files) came while the job was in its opening minutes, before any timed rep (first timed rep ended 19:23Z); disclosed as LOG 18:49 asks. The box2 wrapper does not pause cm-tick.timer and cm-rc-watch.timer (timers_paused=NA).

box3 (job 2026-10-05 00:15Z, elapsed 2,421 s): RESULT INVALID, reason three_discards_on_this_host, 0 kept reps. Only the feeder's copies exist (RESULT.txt, job files, no rows or checks), so I cannot say from the folder which rule caused the three discards; the RESULT line gives the discard count and the baseline and gate results (all nine arms passed their checks). Timers not paused (NA). LOG 01:04Z records no re-run: the pass mark has none for an INVALID host. The labels come from box1 alone and are not affected.

## 5. Memory lines and the trust column (BUILD.md "What the result must state", items 1 to 8, in order)

### Item 1: FRAMEWORK memory line (R4 form)
FRAMEWORK memory (no label, different load paths): peak PSS of G 539.4 MB, T 1,332.3 MB and Q 587.1 MB on box1; L-R 758.9 MB and L-C 731.1 MB are rows of rust-1, taken earlier, on the same calendar day (2026-10-04, 09:26Z to 11:18Z; this job ran 16:34Z to 18:19Z; the template says "a different day", which is not true, so the true wording is written) and in a different job. G reads each tensor with read_exact into its own heap buffer (no whole-file buffer, no mmap); T loads with safetensors load_file; Q memory-maps the GGUF (llama.cpp default, load_mode=mmap in its INFO line); L-R reads the whole file with std::fs::read into a heap buffer and L-C read()s it, as rust-1 records. X loads like G (read_exact, own heap buffers).

| arm (box1, N=1) | peak PSS | peak anonymous | VmHWM | load method |
|---|---|---|---|---|
| G-OB O3 (reference) | 539.4 MB | 535.8 MB | 541.0 MB | read_exact, per-tensor heap buffers |
| G-MKL O3 | 546.4 MB | 534.1 MB | 548.1 MB | same |
| X O2 (reference) | 535.1 MB | 533.5 MB | 536.7 MB | same |
| T | 1,332.3 MB | 888.7 MB | 1,397.2 MB | safetensors load_file |
| Q | 587.1 MB | 56.6 MB | 588.9 MB | memory-mapped GGUF |
| Q8_0 extra | 201.5 MB | 56.6 MB | 203.3 MB | memory-mapped GGUF |
| L-R (rust-1, earlier job, O3 build) | 758.9 MB | 757.4 MB | | std::fs::read of the whole file |
| L-C (rust-1, earlier job, O3 build) | 731.1 MB | 730.8 MB | | read() |

(MB = kB / 1000, medians of 5 per-rep peaks.) Ratios on peak PSS, no label: T / G-OB 2.470; Q / G-OB 1.088; T / Q 2.269; L-R / G-OB 1.407; L-C / G-OB 1.355. Peak anonymous T / G-OB 1.659. Arm L rows are never in a speed pair and no row of rust-1 enters a Band W ratio. I used the O3 builds of arm L (rust-1's memory pair); the O2 builds are L-R 762.4 MB and L-C 772.1 MB. PSS carries an I/O-method effect (Q maps its file, so file pages count in PSS and not in anonymous memory); anonymous bytes are the closer comparison (T 889 MB, G 536 MB, Q 57 MB with its file mapped).

### Item 2: arm Q
Largest logit difference of Q to L-C: 0.0720 on box1 (0.0845 on box2); G-OB, G-MKL and X are 0.0002 or less and T is 0.000206 (about 0.0002). The arg-max equals the forced id at all 64 positions of every row (0 mismatches). Q INFO line on box1 (every check, before and after): "system_info=CPU : SSE3 = 1 | SSSE3 = 1 | AVX = 1 | AVX2 = 1 | F16C = 1 | FMA = 1 | BMI2 = 1 | LLAMAFILE = 1 | REPACK = 1 | n_vocab=49152 load_mode=mmap flash_attn_type=-1 threads=1" (threads=2 at N=2); box2: "CPU : SSE3 = 1 | SSSE3 = 1 | LLAMAFILE = 1 | REPACK = 1 ... flash_attn_type=-1". The 0.072 and 0.0845 figures belong next to every Q speed line above (15.532 tok/s at N=1, 20.508 at N=2). Q is not bit-comparable arithmetic and is not the same arithmetic as G, X or T. The Q8_0 row is "different arithmetic".

### Item 3: KERNELS sentence with the scope clause
KERNELS (our Rust kernels against MKL inside torch): the Rust-fast engine is ahead of torch on box1, r=1.303. This is a statement about our kernels. The engine replaces the matrix-vector product alone; attention, softmax and rope stay on the strict scalar path that G shares. X was built and is in the freeze record, so "engine: NOT TESTED" does not apply.

### Item 4: FRAMEWORK sentences as registered
1. FRAMEWORK (stack against stack, not language): G-OB is ahead of PyTorch fp32 + MKL on box1, r=1.338. Kernels differ unless G-MKL was used. G-OB is not pure Rust.
2. FRAMEWORK (stack against stack, not language): G-OB is ahead of llama.cpp F32 on box1, r=1.195. Kernels differ unless G-MKL was used. G-OB is not pure Rust. (Q's logit difference 0.0720 and INFO line: item 2.)
3. FRAMEWORK (stack against stack, not language): G-MKL is ahead of PyTorch fp32 + MKL on box1, r=1.304. Kernels differ unless G-MKL was used. G-MKL is not pure Rust. (Torch calls its own MKL 2024.0 Update 2 build 20240605 on its gnu_thread layer; G-MKL calls MKL 2026 Update 1 build 20260612, sequential: same kernel family, not the same library build or threading layer, so "glue alone" is not written.)
Pure Rust or not: X pure Rust; G-OB, G-MKL, T and Q not pure Rust.

### Item 5: phases on box1, order, budget
Two box1 jobs, in the order R11 fixes: first rust1b-box1-n1 (phase n1, N=1, 2026-10-04 16:34:40Z to 18:18:54Z, OK, 6,253 s), then rust1b-box1-n2 (phase n2, N=2, 2026-10-05 02:58Z to 04:29Z, PARTIAL, 5,382 s). No redo ran (no label INCONCLUSIVE). Budget of box1 (registered 28,800 s, shared with rust-1): used by rust-1 before this lab 6,735 s, left at the start 22,065 s; after the first job 12,988 s used; budget left before the second job 15,812 s, against the 7,200 s its wrapper requires (test passed). After the second job: 18,370 s used and 10,430 s left (my sums; I did not read the budget file on box1). N=2 on box1 was not COST-CAPPED.

### Item 6: arm L rows and freeze order
L-R and L-C peak PSS rows come from rust-1 (item 1) and are in no speed pair. The arms were frozen after the arm L numbers of rust-1 were known: the rust-1 box1 job ended 2026-10-04 11:18:43Z, its RESULT.md file time is 14:01Z, the freeze file time is 15:48Z, and the start record is 16:04:24Z (file times converted from local UTC-5; the ledger record of rust-1 is 14:02:12Z).

### Item 7: T at N=2
See section 3: T at N=2 is INVALID by the Threads rule (4 threads in /proc, 2 asked), one row, no value; the N=1 pairs are not affected (T shows exactly 1 thread in all 45 timed rows and in the checks).

### Item 8: trust column
- (1) Largest logit difference to L-C (box1): G-OB 0.00018692, G-MKL 0.00018311, X 0.00019288, T 0.00020599, Q 0.07203 (box2: G-OB 0.00019360, Q 0.08449). These equal the untimed run on penguin in the freeze file.
- (2) Hidden-state hash of T (prompt 0, first 16 of 64 hex): box1 N=1 9161d025d94864b0, equal before and after; box1 N=2 d1bafcfbd795f9cf (different from N=1); box2 N=1 4b2f932aade59b09 (box2 N=2: 621456b15608864d). Equal across hosts: NO, as the pass mark expected ("reported and not argued"). box3: no check files were copied, so not read.
- (3) Dependencies: G-OB 93 crates plus libopenblas 0.3.29, libgfortran5, libquadmath0; G-MKL 92 crates plus libmkl_rt 2026.1.0 and its layers; X 91 crates, no C or Fortran library; T 34 pip packages plus the libraries inside the wheels (MKL, OpenMP, libtorch); Q llama.cpp b11381 static plus libstdc++.
- (4) Lines of the decode loop, total / code (counts describe size, not quality; torch, transformers and llama.cpp code are not counted): G-OB and G-MKL 374 / 353, X 424 / 403, T 20 / 20, Q 16 / 16.
- Pure Rust: X yes; G-OB, G-MKL, T, Q no.

## 6. Hygiene of each job

| item | box1 n1 (labelled) | box1 n2 (no label) | box2 (no label) | box3 (no label) |
|---|---|---|---|---|
| RESULT | OK | PARTIAL (t@n2) | INVALID | INVALID |
| rows (statuses) | 45 KEPT | 34: 30 KEPT, 3 VOID, 1 INVALID | 10: 7 KEPT, 3 DISCARD | not copied |
| voids | 0 | 3, each repeated (rep 1 gob-O2, 03:34:37Z, 0.0678 against limit 0.032; rep 3 gob-O3, 04:02:38Z, 0.0331; rep 4 gmkl-O2, 04:15:23Z, 0.0322); limit of 6 not reached | 0 | n/a |
| discards (clock) | 0 | 0 | 3 (INVALID host) | 3 (INVALID host) |
| out-of-memory kills | 0 | 0 | 0 | none reported |
| arm checks before and after | 9 of 9 arms: exit 0, 9 CHECK rows, 0 mismatches, witness equal before and after (Q8_0: 17 mismatches, exempt, recorded) | 7 arms: T checked before only (its arm ended INVALID at its first timed run); the six others passed before and after | before-checks passed, no after-checks (job ended) | gates passed for all 9 arms |
| threads in /proc | 1 in every row | 2 in every valid row; T 4 (INVALID) | 1 | n/a |
| clock rule (R2) | my recomputation: worst drop of a kept rep 0.014 percent, 2094.9 to 2095.6 MHz, 0 over 15 percent; thermal-throttle counters unchanged | worst 0.038 percent | 3 discards at 18.5 to 23.1 percent below the reference | 3 discards |
| outside load (R1), kept reps | arm CPUs max 0.0172 against limit 0.0285; host max 0.0378 CPU against 0.10 | arm max 0.0284 against 0.032; host max 0.0284 against 0.10 | within limit 0.0465 / 0.10 | limit 0.037 / 0.10 |
| load at the start of each arm | 0.25 to 0.29 (limit below 0.3) | 0.25 to 0.29 | 0.26 to 0.29 | n/a |
| idle baseline (6 windows of 20 s) | arm 0.0085, host 0.0125 | arm 0.012, host 0.0215 | arm 0.0265, host 0.048 | arm 0.017, host 0.0325 |
| order (R9) | performed order equals the design in all 45 rows; mean position 4.0 of 0 to 8 for every arm; positions in section 6 note | design 3.0 of 0 to 6; performed 2.6 to 2.8 because T dropped out (see note) | n/a | n/a |
| elapsed against cap | 6,253 s of 22,065 s | 5,382 s of 15,812 s | 4,517 s (registered cap 86,400 s, rust-1 used 2,514 s) | 2,421 s (cap 86,400 s, none used before) |
| hashes | payload a2a1b3ee...1cf8 and run.py bcd0fa38...e431f equal to the frozen values; wrapper sha 6b6f4e3e... equals frozen | same payload and run.py; wrapper 537c9efe... equals frozen | same; wrapper 8944aa49... | same (RESULT line) |
| timers (cm-tick, cm-rc-watch) | paused and restored | paused and restored | not paused (NA) | not paused (NA) |
| CPUs | arm CPU 1, runner CPU 0 (separate cores) | arm CPUs 0 and 1, runner CPU 2 (shares core of CPU 0) | arm 1, runner 0 | arm 1, runner 0 |

Notes. Order positions of phase n1 (reps 0 to 4): G-OB O2 8,7,0,4,1; G-OB O3 0,3,5,7,5; G-MKL O2 6,4,6,0,4; G-MKL O3 7,5,3,2,3; X O2 3,2,4,5,6; X O3 4,8,7,1,0; T 1,0,8,3,8; Q 2,1,2,8,7; Q8_0 5,6,1,6,2. Phase n2: 10 kept rows and 1 voided row (gmkl-O2 rep 4, place 3 against design place 4) in reps 2 to 4 stood one place earlier than the design, because T was INVALID after its first run and was not run again; the other arms moved up. Voided reps were repeated at the same place. Phase n2 positions of the kept rows are in rust1b_result.json.

Clock, literal reading: the pass mark says "CPU MHz from /proc/cpuinfo before and after each rep". One after-run snapshot on box1 phase n1 (T, rep 3, arm CPU idle after the run) read 1,408 MHz against 2,100 before; the amended reading R2 (in-run readings, once a second) is the law the runner applied and shows no drop. Neither reading moves a label (T rep 3 dropped: all three T pairs stay AHEAD, ratios above 1.29).

CPUQuota (R5): the feeder sets 100 percent times the logical CPUs (box1 400 percent, box2 and box3 200 percent); this does not bind with the arm pinned to one or two CPUs; cpu_quota_binding=no; stated as a disclosure.

Cap rule: no arm was COST-CAPPED. Phase n1 on box1 was never cut.

## 7. Disclosures carried from BUILD.md

- CPUQuota does not bind (R5); box2 and box3 are unlabelled hosts (same CPU class; one class supplies no label) and both ended INVALID; box4 and box5 run no arm (stock torch gives "Illegal instruction" on import there).
- The amendment is wider than "versions and hashes not yet known" and rests on the operator's written ruling (LOG 2026-10-04 16:00); R11 narrows what can be claimed on box1 (two jobs; N=2 may have been absent; it ran).
- The stack of T differs from SV5B: numpy 2.5.3 and safetensors 0.8.0 against 2.2.6 and 0.7.0 (transformers 5.0.0 and torch 2.14.0+cpu match). T's numbers are for this stack. The stacks also differ in wait policy and threading layer: T sets OMP_WAIT_POLICY=PASSIVE; G-MKL uses the SEQUENTIAL MKL layer at one thread (GNU layer at two); G-OB sets OPENBLAS_NUM_THREADS; a statement of stack against stack.
- Q is not bit-comparable arithmetic (R3); X changes the matrix-vector product alone (R12); G and X load tensors with read_exact into per-tensor buffers (R4).
- Nothing in rust-1b was timed before the start; the budget arithmetic was an estimate from the pass mark's expected speeds (the estimates 7,920 s and 7,200 s against 6,253 s and 5,382 s measured).
- The operator's pull of 03:20:00Z on box1 (section 3) and the operator's ssh calls on box2 of 18:43 to 18:47Z (section 4).
- The N=2 T arm was accepted before the start as one that ends INVALID (operator ruling 2026-10-04 16:00); the run did so.
- T reps drift down on box1 phase n1 (14.14, 14.10, 13.88, 13.63, 13.74; spread 3.7 percent, the widest of the nine arms); without rep 3 the T median is 13.99; no label changes.
- The L8, L9 and L10 items of BUILD.md stand as written there (L10: the host label comes from the wrapper argument; the cgroup and file checks still applied).
- Phase n1 start-of-run loads (0.25 to 0.29) sit 0.01 under the 0.3 limit at the nearest. Read literally, the load sentence "below 0.3 before and after" would void every rep (end-of-run 0.48 to 0.89 is the arm's own load); R1 reads it as a start-of-run gate. Not a trigger.

## 8. Expected against measured (SURPRISE flag)

| item | expected (written before any run) | measured on box1 | flag |
|---|---|---|---|
| G-OB against T | T above G-OB: BEHIND about 55 percent, TIE about 30, AHEAD about 15 | AHEAD, r = 1.338 | SURPRISE |
| G-OB against Q | Q above G-OB (llama.cpp F32 about 1.5 to 3 times the strict-order arms) | G-OB above Q, r = 1.195 (Q at 0.837 of G-OB) | SURPRISE |
| G-MKL against T | no probability written for this pair; the general sentence of the pass mark applies ("our Rust arms are behind them ... a result that is level or ahead is a SURPRISE") | AHEAD, r = 1.304 (same direction as G-OB) | SURPRISE by the general sentence only |
| X against T (KERNELS) | BEHIND about 60 percent | AHEAD, r = 1.303 | SURPRISE |
| memory | torch above the strict arms; Rust arms near 0.55 GB | T 1.332 GB, G-OB 0.539 GB (T / G-OB 2.47); right | as expected |
| T speed | torch rerun about 10.8 tok/s on box1 (256 tokens including prefill) | 13.88 tok/s (decode steps 2 to 64, no prefill) | different window, consistent in size |

The expected ordering was wrong in direction for the three labels that had a written expectation; the fourth (G-MKL against T) had none and went the same way as G-OB. The text's "1.5 to 3 times faster than the strict-order arms" is about the strict arm L builds of rust-1, which are not part of any pair here.

## 9. What this result does and does not show

Shows: on one machine (box1, Intel i5-5200U, 2.1 GHz fixed by the performance governor), one thread, SmolLM2-135M, 8 prompts of 63 timed steps, teacher-forced, in fp32: three Rust-driven arms (OpenBLAS, MKL, our own kernels) decode about 30 percent faster than this PyTorch setup and about 16 to 20 percent faster than llama.cpp F32 (ratios 1.165 to 1.195; only G-OB against llama.cpp, 1.195, carries a label; 1.165 is X and G-MKL against llama.cpp, ratios only, no label), each of the four labelled pairs separated by 2.9 to 4.3 tok/s in every repetition (2.4 tok/s belongs to X against Q, which has no label). All of this is for this torch set-up, one thread, one machine (box1); not PyTorch in general. The four fast arms sit within 3 percent of each other and share the same strict scalar code for attention, rope and norms. This is stack against stack.

Does not show:
- Nothing about the Rust language. The glue arms call C or Fortran libraries; X replaces the matrix-vector product alone; T is Python plus C++ plus MKL; Q is C++. Nothing about IMPLEMENTATION (arm L, rust-1) or TOOLCHAIN. Never "Rust is faster than Python".
- Kernels differ unless G-MKL was used, and even G-MKL calls a different MKL build and threading layer from torch's. No "glue alone" claim.
- "Ahead of torch" is for this torch set-up: 2.14.0+cpu, manual KV-cache loop, no compile, sdpa attention, passive OMP wait, one thread, Python in the timed window. Nothing about PyTorch compiled, batched or threaded.
- Q is not the same arithmetic (logit difference 0.072 against about 0.0002 for the other arms, largest 0.000206 for T), with llama.cpp defaults for flash attention and no OpenMP.
- Nothing about another CPU, thread count, model size or token count. The only labels are phase n1 on box1. Phase n2 on box1 (two threads, one job, T INVALID) reports llama.cpp F32 above G-OB and G-MKL at two threads (G-OB / Q 0.930, G-MKL / Q 0.950) and G-MKL 2 percent above G-OB (ratio 1.022): one job, no label, no conclusion. box2 and box3 are INVALID and show nothing.
- Peak PSS is not like for like (mapped file against heap against whole-file read).
- The weights of 539 MB are streamed once per token: at G-OB speed about 10 GB/s of weight traffic (arithmetic from the row, no bandwidth test run). No cause is claimed for the four fast arms lying together; no bandwidth test was run.
- One job on one day; the 5-rep spread inside an arm is 0.8 to 3.7 percent.

## 10. Files and hashes

- <root>/state/reports/rust-lab/rust-1b/rust1b_result.json: sha256 d3ccbf760383b079b794e41e1b854938d3566ae75e9575c88c1a1837ea464ed9 (labels, ratios, medians per arm, phase and host, memory, gate differences, statuses, voids, discards, elapsed seconds against caps, hashes checked).
- Amended pass mark: state/plans/rust-lab/bars/rust-1b-amended-bar.txt, sha256 b1d2fdb1303c362f647885fe0cf9e0f7eed8d026cc4ebc817b31ccc5e07e8671.
- EVIDENCE-SHA256SUMS (same folder): sha256 of every file under box1, box1-n2, box2, box3 and of rust1b_result.json; check with `sha256sum -c EVIDENCE-SHA256SUMS` from the folder.
- Other files read: BUILD.md, FREEZE-STAGE2.md (sha256 43ec552313e064f0bc750d0b0e0946228bf5a6c477c2469505f8524b528694d3), STARTED.md, RESULT-N1.md (unchanged since 19:03Z on 2026-10-04, when it was corrected after the confirming read had begun: one commit 99b4963b, git diff empty, mtime 19:03Z; sha256 d1737bba02d30a8459c1079d1b60b9b596ffaa0f11b1a68cb84767dbfe8b5efd), decode_loop_counts.txt (69cad9a6...513f), rust-1 rows (state/reports/rust-lab/rust-1/box1/rows.jsonl), LOG.md.
- Scoring script (scratch, not in the repo): ~/scratch-rust1b-final/result/score.py.
- This file is the final result text; it is not itself in EVIDENCE-SHA256SUMS because it is written from them.

## 11. Corrections
Made after three independent readers checked this file (VERIFY-RESULT-recompute.md, -validity.md, -claims.md). All agreed with the labels and the verdict word; no label or number changed.
1. Section 9 gap "2.4 to 4.3 tok/s": the four labelled pairs are 2.87 (G-OB v Q), 3.87 (G-MKL v T), 3.88 (X v T), 4.34 (G-OB v T); 2.4 is the unlabelled X v Q pair. Rewritten as 2.9 to 4.3 for the labelled pairs, with 2.4 named as X against Q.
2. Section 3 order of the later gmkl-O2 reps differed from rows: same four values, no change needed.
3. 03:20:00Z pull: not during rep 0 of gmkl-O2 (it ran 03:20:27Z to 03:21:10Z); the pull fell in the gap after gmkl-O3 ended 03:18:56Z. Disclosure kept, position fixed, the "rep taken during a pull" doubt removed.
4 and 8. box3: no rows exist, so the rule behind its three discards cannot be shown; box2's three clock discards are shown in rows. The register text now says so. Section 4 already said it.
5. rust1b_result.json: the committed copy had a typo in the box2 N=2 T hash (621456b156088648); the working copy (621456b15608864d, matches box2/checks/gate_before.json) is the one to commit. Its sha256 d3ccbf76... equals EVIDENCE-SHA256SUMS and section 10; unchanged here.
6. RESULT-N1.md: stated as unchanged since 19:03Z, not since the confirming read (section 10).
7. Start-of-run load 0.25 to 0.29 in every n1 and n2 row (at most 0.01 under 0.3) and the unknown causes of the three n2 voids (0.0322 to 0.0678): already disclosed (sections 6 and 7) or handled by rule; no label touched.
9. "All SURPRISE": three of four labels had a written expectation, all went against it; G-MKL against T had none (sections 1 and 8).
10. Register text now carries the scope: for this torch set-up, one thread, one machine (box1); not PyTorch in general; box2 phase n2 did not run.
11. Section 3: llama.cpp F32 against the Rust arms at two threads is now "same range, no label" (G-OB / Q 0.930).
12. Section 9: "17 to 20 percent" is now "about 16 to 20 percent" (ratios 1.165 to 1.195).
13. Operator's final edit (2026-10-05, after the last adversarial read VERIFY-RESULT-final.md, which confirmed the verdict word, all four labels and every number of the register text, and listed 3 presentation points on numbers and 11 on wording; no label, ratio or median changed): (a) section 5 item 2 and section 9: T's largest logit difference is 0.000206, so "0.0002 or less" now names G-OB, G-MKL and X only; (b) section 6 notes: "11 rows" is now "10 kept rows and 1 voided row" (recounted by the operator from box1-n2/rows.jsonl: design place against performed place); (c) section 1: "level with" is now "within 3 percent of" (no pair of the pass mark exists for X against the G arms); (d) section 8, G-MKL against T: the final reader asked for "not flagged SURPRISE"; the operator keeps a flag and words it exactly: EXPECTED VALUES gives no probability for this pair, and the BIGGER SYSTEMS NAMED sentence of the pass mark ("our Rust arms are behind them ... a result that is level or ahead is a SURPRISE and is flagged as such") covers every Rust arm against T, so the cell reads "SURPRISE by the general sentence only"; (e) section 9: the two-thread line now gives the ratios and says "no conclusion"; the sentence that offered a shared limit as a reading of the four fast arms is replaced by "no cause is claimed"; the 16 to 20 percent line now says which ratio carries a label; (f) the register text: box2 discards written as percent (20.3, 23.1, 18.5), llama.cpp's arithmetic difference placed next to its speed line, the meaning of the word "met" stated, the clock caveat of the 03:20:00Z pull added, the headline sentence and a pointer to the trust column and memory lines added.
