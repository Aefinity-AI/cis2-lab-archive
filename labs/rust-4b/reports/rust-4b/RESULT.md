# rust-4b RESULT (cold start, M2 of rust-4)

Written 2026-10-05 from the collected folders and the two reports below. Status line: the independent verifier (VERIFY-RESULT-R1.md) and the scorer (SUMM-OUT.txt) AGREE (word met, box1 label RUST BEHIND, r=0.8204, expectation SURPRISE; verifier reports mismatches: []). Not held for the operator.

## 1. Registered word and the answer

Ledger word: **met**. "met" says only that the box1 pair got a band label on valid reps and that the expectation is recorded as held or SURPRISE; it does not say who is ahead.

Answer sentence, in the pass mark's own required form (M2):

> IMPLEMENTATION (cold start, SmolLM2-135M, box1): cis2_ref (Rust) is behind verify3 (C), r=0.820; different implementations, toolchains and dependencies included, not a language verdict.

> Storage (box1): ST4000LM024-2AN1, rotational flag yes (1), file system ext4; one model, one prompt.

Stack row (box1, the pass mark's form for P slower by a factor above 3 against both R and C):

> FRAMEWORK (stack, no-Python effect): the static binaries start 3.03 (R) and 3.69 (C) times faster than the Python stack on box1; no label; this is not credited to Rust alone.

The pair is the labelled one: box1 only (Rule A). No redo as 10 was needed: the reps separate. Every other host is numbers only with no label (Rule A).

## 2. Numbers per clause

Source for every figure of this section: box1/rows.jsonl (wall_to_open_s of KEPT rows, as stored in box1/result.json m2.values_open_s) and box1/result.json. Medians are of 5 kept reps. The wall is the time from the spawn of the process to the opening ROW line (CHECK for Rv and Cv), after a successful per-file cold check.

- R (Rust, cis2_ref) reps (s): [12.6928, 12.4663, 11.9185, 15.5787, 13.5203]; median 12.6928.
- C (C, verify3) reps (s): [10.7433, 9.9102, 10.4127, 10.4383, 9.6827]; median 10.4127.
- r = R median speed over C median speed = C median seconds / R median seconds = 10.4127 / 12.6928 = 0.8204.
- Band clause RUST BEHIND: r < 0.95 holds (0.8204); every C rep faster than every R rep holds (slowest C 10.7433 s < fastest R 11.9185 s: True). The TIE band (0.95 to 1.05) and the RUST AHEAD band do not hold. The INCONCLUSIVE route (overlapping reps) did not arise, so no redo as 10 and no TIE (NOT SEPARABLE).
- P (Python start, box1): reps (s) [43.8232, 34.6759, 38.3982, 87.1983, 35.7722]; median 38.3982. Seconds of P over R = 3.0252; over C = 3.6876. Both above 3, by a narrow margin over R. No band is given to P. One P rep (87.20 s) is far above the other four (34.68 to 43.82 s); it was kept (no rule voided it).
- Rv median 14.552 s, Cv median 12.299 s, Q median 8.532 s. No label for these.
- Q is llama.cpp F32, memory-mapped load, NOT the same arithmetic as R and C (largest logit difference 0.072 from the rust-1b freeze, not measured again here). Its speed line carries that figure and no label.

The table of every arm on every host follows in section 3, with load_ns and prefill_ns (the figures the programs print), sectors read and major page faults. Rv and Cv run in check mode, which does not print load_ns or prefill_ns, so those two cells read "not printed". Sectors are 512 bytes (/proc/diskstats delta, device holding the weights file, from just before the spawn to the opening line).

Wall composition (pass mark item 7): the wall holds the cold read, the bf16 to fp32 widening and about 7.6 s of arithmetic on box1 (more on box4 and box5); it is not the read time alone. On box1 the printed prefill_ns medians are R 7.640 s, C 5.939 s, Q 0.275 s (Q does one llama_decode over the whole prompt; R and C go token by token). A difference of the wall between R and C on box1 is therefore not read time alone, and a TIE of the wall on any host would not show equal cold-read behaviour. This result does not credit the difference, or any equality, to storage.

## 3. Validity checks and what held, per host

Source: result.json and rows.jsonl of each box folder; VERIFY-RESULT-R1.md (independent recomputation for box1, and the pins, controls, kept-row residency, counts and positions for all five hosts); the figures below were recomputed again for this file from the same two archives per host.

What held on all five hosts: payload list, runner and helper sha256 equal the frozen values (939a31be..., 337a6e17..., a08c989b...); the correctness gate witness equals the pinned witness before and after (ecafd089...); the warm control read at least 90 percent (100 percent) at the opening and at the end; the cold control read 0 pages at the first try; every KEPT row has check resident_pages 0 and errors 0; 0 not-cold repeats (so none to place); the Cached rule of rust-4 was not applied (the Cached kB before and after are recorded and decide nothing); the weights, config, tokenizer and wheelhouse hashes matched (P wheelhouse sha256 21360ef9... on every host); every host job ended inside the 5,400 s cap with no arm COST-CAPPED; box1 timers were paused and restored (cm-tick.timer, cm-rc-watch.timer). Nothing from penguin was timed. No box was touched for this file.

What did not run: P and Q on box4 and box5 (rc -4, Illegal instruction); see the host tables. The pair label exists on box1 alone by rule.

Positions: the designs fix mean positions 2.4 for R, C, P and 2.6 for Rv, Cv, Q with 6 arms (R and C exactly equal), and 1.4 for R, C and 1.6 for Rv, Cv with 4 arms (box4, box5). These are the 0-based positions the runner stores; the tables show the realised ones. The even-n designs are not mean-balanced for every arm (R and C are).

### box1 (Intel(R) Core(TM) i5-5200U CPU @ 2.20GHz; kernel 6.12.111+deb13-amd64; RAM 5841 MB; llama.cpp build llama-drv-avx2)
Source: box1/result.json, box1/rows.jsonl. Job 20261005T124032Z-988755. RESULT word OK. Elapsed 1122 s of the 5,400 s cap.
- Disk: ST4000LM024-2AN1, rotational flag yes (1), file system ext4, 4000.8 GB, /dev/sda4.
- Controls: warm_open 65689/65689 pages (100 percent); cold_open 0/65689 pages (1 try); warm_final 65689/65689 pages (100 percent).
- Not-cold repeats: 0. Clock and throttle discards: 0 (budget 6). Voids: 0 (budget 8). Kept rows: 30; kept rows with resident_pages not 0 or errors not 0: 0; kept rows with a throttle-counter change: 0.
- Highest foreign load in a kept row: 0.0417 (arm CPU set), 0.0878 CPU (host); limits 0.044 and 0.1. MHz seen at before and after snapshots of kept rows: 2093 to 2100.
- Pins: payload_sha256 = frozen = 939a31be0078...; run_py_sha256 = frozen = 337a6e17b360...; helper_sha256 = a08c989bf485...; gate witness ecafd089d17b... (R and C after the reps: equal); mismatches in every kept R, C, Q row: 0.
- P probe rc 0; Q probe rc 0. Not-run notes: none.

| arm | status | median to opening line (s) | min-max (s) | median load_ns (s) | median prefill_ns (s) | median sectors read to opening line | median major faults | positions per rep (0-based) | mean position (0-based) |
|---|---|---|---|---|---|---|---|---|---|
| R | OK | 12.693 | 11.918-15.579 | 4.885 | 7.640 | 550616 | 14 | [3, 5, 2, 0, 2] | 2.4 |
| C | OK | 10.413 | 9.683-10.743 | 4.455 | 5.939 | 530328 | 1 | [0, 1, 3, 5, 3] | 2.4 |
| P | OK | 38.398 | 34.676-87.198 | not printed | not printed | 995144 | 985 | [2, 4, 0, 1, 5] | 2.4 |
| Rv | OK | 14.552 | 13.883-15.933 | not printed | not printed | 538072 | 14 | [4, 0, 5, 3, 1] | 2.6 |
| Cv | OK | 12.299 | 10.515-13.854 | not printed | not printed | 564840 | 1 | [1, 2, 4, 2, 4] | 2.6 |
| Q | OK | 8.532 | 8.112-10.241 | 7.707 | 0.275 | 1070112 | 50 | [5, 3, 1, 4, 0] | 2.6 |

- timers_paused=cm-tick.timer,cm-rc-watch.timer; timers_restored=cm-tick.timer,cm-rc-watch.timer (box1/RESULT.txt).
- Realised order of arms per rep (box1/result.json m2.order_performed): [['C', 'Cv', 'P', 'R', 'Rv', 'Q'], ['Rv', 'C', 'Cv', 'Q', 'P', 'R'], ['P', 'Q', 'R', 'C', 'Cv', 'Rv'], ['R', 'P', 'Cv', 'Rv', 'Q', 'C'], ['Q', 'Rv', 'R', 'C', 'Cv', 'P']].

### box2 (Intel(R) Celeron(R) N4020 CPU @ 1.10GHz; kernel 6.12.111+deb13-amd64; RAM 3737 MB; llama.cpp build llama-drv-sse42)
Source: box2/result.json, box2/rows.jsonl. Job 20261005T094551Z-702732. RESULT word OK-PARTIAL. Elapsed 714 s of the 5,400 s cap.
Banner: no label (Rule A): this host carries no label word; r and the medians are numbers only.
- Disk: TA2964, rotational flag no (0), file system ext4, 62.6 GB, /dev/mmcblk0p4.
- Controls: warm_open 65689/65689 pages (100 percent); cold_open 0/65689 pages (1 try); warm_final 65689/65689 pages (100 percent).
- Not-cold repeats: 0. Clock and throttle discards: 1 (budget 6). Voids: 3 (budget 8). Kept rows: 30; kept rows with resident_pages not 0 or errors not 0: 0; kept rows with a throttle-counter change: 0.
- Highest foreign load in a kept row: 0.0082 (arm CPU set), 0.0574 CPU (host); limits 0.0355 and 0.1. MHz seen at before and after snapshots of kept rows: 795 to 2785.
- Pins: payload_sha256 = frozen = 939a31be0078...; run_py_sha256 = frozen = 337a6e17b360...; helper_sha256 = a08c989bf485...; gate witness ecafd089d17b... (R and C after the reps: equal); mismatches in every kept R, C, Q row: 0.
- P probe rc 0; Q probe rc 0. Not-run notes: none.

| arm | status | median to opening line (s) | min-max (s) | median load_ns (s) | median prefill_ns (s) | median sectors read to opening line | median major faults | positions per rep (0-based) | mean position (0-based) |
|---|---|---|---|---|---|---|---|---|---|
| R | OK | 8.604 | 8.595-8.722 | 1.344 | 7.219 | 555208 | 14 | [3, 5, 2, 0, 2] | 2.4 |
| C | OK | 6.672 | 6.655-6.715 | 1.157 | 5.502 | 525760 | 1 | [0, 1, 3, 5, 3] | 2.4 |
| P | OK | 13.109 | 13.036-13.522 | not printed | not printed | 964072 | 933 | [2, 4, 0, 1, 5] | 2.4 |
| Rv | OK | 9.204 | 9.181-9.237 | not printed | not printed | 553248 | 14 | [4, 0, 5, 3, 1] | 2.6 |
| Cv | OK | 6.686 | 6.673-6.731 | not printed | not printed | 529864 | 1 | [1, 2, 4, 2, 4] | 2.6 |
| Q | OK | 3.599 | 3.587-3.602 | 1.883 | 1.674 | 1066432 | 47 | [5, 3, 1, 4, 0] | 2.6 |

- Realised order of arms per rep (box2/result.json m2.order_performed): [['C', 'Cv', 'P', 'R', 'Rv', 'Q'], ['Rv', 'C', 'Cv', 'Q', 'P', 'R'], ['P', 'Q', 'R', 'C', 'Cv', 'Rv'], ['R', 'P', 'Cv', 'Rv', 'Q', 'C'], ['Q', 'Rv', 'R', 'C', 'Cv', 'P']].

### box3 (Intel(R) Celeron(R) N4020C CPU @ 1.10GHz; kernel 6.12.94+deb13-amd64; RAM 3303 MB; llama.cpp build llama-drv-sse42)
Source: box3/result.json, box3/rows.jsonl. Job 20261005T102219Z-588469. RESULT word OK-PARTIAL. Elapsed 1593 s of the 5,400 s cap.
Banner: no label (Rule A): this host carries no label word; r and the medians are numbers only.
- Disk: Storage Device, rotational flag yes (1), file system ext4, 500.1 GB, /dev/sda4.
- Controls: warm_open 65689/65689 pages (100 percent); cold_open 0/65689 pages (1 try); warm_final 65689/65689 pages (100 percent).
- Not-cold repeats: 0. Clock and throttle discards: 5 (budget 6). Voids: 6 (budget 8). Kept rows: 30; kept rows with resident_pages not 0 or errors not 0: 0; kept rows with a throttle-counter change: 0.
- Highest foreign load in a kept row: 0.0284 (arm CPU set), 0.0956 CPU (host); limits 0.031 and 0.1. MHz seen at before and after snapshots of kept rows: 795 to 2785.
- Pins: payload_sha256 = frozen = 939a31be0078...; run_py_sha256 = frozen = 337a6e17b360...; helper_sha256 = a08c989bf485...; gate witness ecafd089d17b... (R and C after the reps: equal); mismatches in every kept R, C, Q row: 0.
- P probe rc 0; Q probe rc 0. Not-run notes: none.

| arm | status | median to opening line (s) | min-max (s) | median load_ns (s) | median prefill_ns (s) | median sectors read to opening line | median major faults | positions per rep (0-based) | mean position (0-based) |
|---|---|---|---|---|---|---|---|---|---|
| R | OK | 18.246 | 15.681-19.650 | 10.455 | 7.389 | 560744 | 14 | [3, 5, 2, 0, 2] | 2.4 |
| C | OK | 13.663 | 13.482-18.247 | 8.027 | 5.611 | 534160 | 1 | [0, 1, 3, 5, 3] | 2.4 |
| P | OK | 57.883 | 55.035-69.325 | not printed | not printed | 996536 | 941 | [2, 4, 0, 1, 5] | 2.4 |
| Rv | OK | 16.469 | 16.378-16.580 | not printed | not printed | 559744 | 14 | [4, 0, 5, 3, 1] | 2.6 |
| Cv | OK | 13.734 | 13.637-15.863 | not printed | not printed | 545992 | 1 | [1, 2, 4, 2, 4] | 2.6 |
| Q | OK | 23.020 | 18.586-23.804 | 20.825 | 1.796 | 1099752 | 44 | [5, 3, 1, 4, 0] | 2.6 |

- Realised order of arms per rep (box3/result.json m2.order_performed): [['C', 'Cv', 'P', 'R', 'Rv', 'Q'], ['Rv', 'C', 'Cv', 'Q', 'P', 'R'], ['P', 'Q', 'R', 'C', 'Cv', 'Rv'], ['R', 'P', 'Cv', 'Rv', 'Q', 'C'], ['Q', 'Rv', 'R', 'C', 'Cv', 'P']].

### box4 (AMD Sempron(tm) SI-42; kernel 6.12.94+deb13-amd64; RAM 3669 MB; llama.cpp build llama-drv-sse42)
Source: box4/result.json, box4/rows.jsonl. Job 20261005T232450Z-111624. RESULT word OK-PARTIAL. Elapsed 942 s of the 5,400 s cap.
Banner: no label (Rule A): this host carries no label word; r and the medians are numbers only.
- Disk: HGST HTS541075A9, rotational flag yes (1), file system ext4, 750.2 GB, /dev/sda4.
- Controls: warm_open 65689/65689 pages (100 percent); cold_open 0/65689 pages (1 try); warm_final 65689/65689 pages (100 percent).
- Not-cold repeats: 0. Clock and throttle discards: 1 (budget 6). Voids: 1 (budget 8). Kept rows: 20; kept rows with resident_pages not 0 or errors not 0: 0; kept rows with a throttle-counter change: 0.
- Highest foreign load in a kept row: 0.0152 (arm CPU set), 0.0152 CPU (host); limits 0.0205 and 0.1. MHz seen at before and after snapshots of kept rows: 1050 to 2100.
- Pins: payload_sha256 = frozen = 939a31be0078...; run_py_sha256 = frozen = 337a6e17b360...; helper_sha256 = a08c989bf485...; gate witness ecafd089d17b... (R and C after the reps: equal); mismatches in every kept R, C, Q row: 0.
- P probe rc -4; Q probe rc -4. Not-run notes: ['P start: stack did not start: rc=-4 (Illegal instruction) ()', 'Q start: llama.cpp driver did not start or did not print its check line: rc=-4 (Illegal instruction) ()'].

| arm | status | median to opening line (s) | min-max (s) | median load_ns (s) | median prefill_ns (s) | median sectors read to opening line | median major faults | positions per rep (0-based) | mean position (0-based) |
|---|---|---|---|---|---|---|---|---|---|
| R | OK | 17.057 | 17.035-17.161 | 3.789 | 13.090 | 531056 | 15 | [0, 3, 1, 2, 1] | 1.4 |
| C | OK | 14.237 | 14.206-14.267 | 3.574 | 10.606 | 525832 | 2 | [2, 1, 0, 1, 3] | 1.4 |
| P | NOT RUN | - | - | - | - | - | - | - | - |
| Rv | OK | 20.169 | 20.081-20.373 | not printed | not printed | 535976 | 15 | [3, 0, 2, 3, 0] | 1.6 |
| Cv | OK | 14.291 | 14.284-14.338 | not printed | not printed | 530208 | 2 | [1, 2, 3, 0, 2] | 1.6 |
| Q | NOT RUN | - | - | - | - | - | - | - | - |

- Realised order of arms per rep (box4/result.json m2.order_performed): [['R', 'Cv', 'C', 'Rv'], ['Rv', 'C', 'Cv', 'R'], ['C', 'R', 'Rv', 'Cv'], ['Cv', 'C', 'R', 'Rv'], ['Rv', 'R', 'Cv', 'C']].

### box5 (Intel(R) Pentium(R) Dual  CPU  T2310  @ 1.46GHz; kernel 6.12.94+deb13-amd64; RAM 1964 MB; llama.cpp build llama-drv-sse42)
Source: box5/result.json, box5/rows.jsonl. Job 20261005T183355Z-115218. RESULT word OK-PARTIAL. Elapsed 1105 s of the 5,400 s cap.
Banner: no label (Rule A): this host carries no label word; r and the medians are numbers only.
- Disk: WDC WD1600BEVS-2, rotational flag yes (1), file system ext4, 160.0 GB, /dev/sda4.
- Controls: warm_open 65689/65689 pages (100 percent); cold_open 0/65689 pages (1 try); warm_final 65689/65689 pages (100 percent).
- Not-cold repeats: 0. Clock and throttle discards: 3 (budget 6). Voids: 0 (budget 8). Kept rows: 20; kept rows with resident_pages not 0 or errors not 0: 0; kept rows with a throttle-counter change: 0.
- Highest foreign load in a kept row: 0.0038 (arm CPU set), 0.0681 CPU (host); limits 0.0295 and 0.1. MHz seen at before and after snapshots of kept rows: 797 to 1463.
- Pins: payload_sha256 = frozen = 939a31be0078...; run_py_sha256 = frozen = 337a6e17b360...; helper_sha256 = a08c989bf485...; gate witness ecafd089d17b... (R and C after the reps: equal); mismatches in every kept R, C, Q row: 0.
- P probe rc -4; Q probe rc -4. Not-run notes: ['P start: stack did not start: rc=-4 (Illegal instruction) ()', 'Q start: llama.cpp driver did not start or did not print its check line: rc=-4 (Illegal instruction) ()'].

| arm | status | median to opening line (s) | min-max (s) | median load_ns (s) | median prefill_ns (s) | median sectors read to opening line | median major faults | positions per rep (0-based) | mean position (0-based) |
|---|---|---|---|---|---|---|---|---|---|
| R | OK | 20.212 | 20.193-20.322 | 7.343 | 12.689 | 530904 | 14 | [0, 3, 1, 2, 1] | 1.4 |
| C | OK | 18.621 | 18.588-19.060 | 7.214 | 11.386 | 525776 | 1 | [2, 1, 0, 1, 3] | 1.4 |
| P | NOT RUN | - | - | - | - | - | - | - | - |
| Rv | OK | 24.261 | 24.229-24.364 | not printed | not printed | 535088 | 14 | [3, 0, 2, 3, 0] | 1.6 |
| Cv | OK | 18.721 | 18.703-19.123 | not printed | not printed | 529888 | 1 | [1, 2, 3, 0, 2] | 1.6 |
| Q | NOT RUN | - | - | - | - | - | - | - | - |

- Realised order of arms per rep (box5/result.json m2.order_performed): [['R', 'Cv', 'C', 'Rv'], ['Rv', 'C', 'Cv', 'R'], ['C', 'R', 'Rv', 'Cv'], ['Cv', 'C', 'R', 'Rv'], ['Rv', 'R', 'Cv', 'C']].

Rows with no label: box2, box3, box4, box5 (all arms), and P, Rv, Cv, Q on box1.

Other-host numbers, no label (Rule A): r (R speed over C speed) and the P factors, informal:

| host | r | R median (s) | C median (s) | P median (s) | P over R | P over C |
|---|---|---|---|---|---|---|
| box2 | 0.7755 | 8.604 | 6.672 | 13.109 | 1.52 | 1.96 |
| box3 | 0.7489 | 18.246 | 13.663 | 57.883 | 3.17 | 4.24 |
| box4 | 0.8346 | 17.057 | 14.237 | NOT RUN (rc -4) | - | - |
| box5 | 0.9213 | 20.212 | 18.621 | NOT RUN (rc -4) | - | - |

On box3 the R and C reps overlap (fastest R 15.68 s, slowest C 18.25 s); on the other hosts shown here the reps are separate or not read for overlap; no host other than box1 gets a label word, so none is given.

FRAMEWORK sentences for the other hosts (informal, Rule A):
- box2: FRAMEWORK (stack, no-Python effect): on box2 the Python stack started in 13.11 s against 8.60 s (R) and 6.67 s (C); not slower by the factor of the expectation; no label (Rule A).
- box3: FRAMEWORK (stack, no-Python effect): the static binaries start 3.17 (R) and 4.24 (C) times faster than the Python stack on box3; no label (Rule A); this is not credited to Rust alone.
- box4, box5: FRAMEWORK (stack, no-Python effect): P NOT RUN on box4, return code -4 (Illegal instruction); P NOT RUN on box5, return code -4 (Illegal instruction); no label (Rule A). Q is also NOT RUN there, rc -4.

## 4. Expectations

Carried (pass mark, 2026-10-03): "Expected: TIE (about 60 percent; both are bounded by reading the 0.27 GB weights file and widening), Python slower by a factor above 3 on box2 (about 80 percent)." Operator estimate (2026-10-05, before any run, in the pass mark and the notes): box1 TIE 50, RUST BEHIND 25, RUST AHEAD 15, INVALID or INCONCLUSIVE 10; P slower than R by a factor above 3 on box1 85 percent.

| expectation | outcome | word | source |
|---|---|---|---|
| TIE on box1 (carried, about 60 percent) | RUST BEHIND, r=0.8204 | **SURPRISE** | SUMM-OUT.txt line 11; VERIFY-RESULT-R1.md |
| operator class on box1: most likely TIE (50 percent) | outcome class RUST BEHIND, stated 25 percent | **SURPRISE** | SUMM-OUT.txt line 12 |
| P above 3 times R and C on box1 (operator 85 percent) | 3.025 over R, 3.688 over C | held | SUMM-OUT.txt line 13 |
| Python above 3 on box2 (carried, about 80 percent), informal (Rule A) | 1.52 over R, 1.96 over C | **SURPRISE** | SUMM-OUT.txt line 25 |
| same Python line on box3, informal (Rule A) | 3.17 over R, 4.24 over C | held (informal; my reading of the pass mark's rule "evaluated on every host where P ran"; SUMM-OUT.txt does not print this line) | box3/result.json |
| same Python line on box4 and box5 | P NOT RUN, rc -4 | NOT TESTED there | box4/result.json, box5/result.json |

Note on calibration (pass mark): the operator's estimates for TIE and for INCONCLUSIVE were flagged as possibly high and low; the outcome is a miss on the TIE side either way. The box1 P/R factor of 3.025 holds the line narrowly: it is a median of 5 reps with one rep at 87.2 s.

## 5. What this result does NOT show

- It is not a language verdict. cis2_ref (Rust) and verify3 (C) are two different implementations of CIS-2, with different toolchains and dependencies (cis2_ref is NOT PURE RUST: tokenizers is built with the onig feature, C Oniguruma). It answers IMPLEMENTATION; FRAMEWORK for P and Q. It does not answer KERNELS and does not answer LANGUAGE (rust-5 does).
- It says nothing about warm decode speed (rust-1 and rust-1b cover that).
- One model (SmolLM2-135M) and one prompt (39 ids). One labelled host: box1. box2, box3, box4, box5 carry no label (Rule A) and their held or SURPRISE words are informal.
- "Cold" means "no page of the listed files was in memory before the program started". The check lists the files, so the directory entries and inodes of those files (for P the whole venv, 29,942 files on every host that listed it) are read by the check itself; the program does not meet cold metadata for them. The base system files (dynamic loader cache, libc, libm, libgcc_s and libstdc++ for Q; the same and /usr/lib/python3.13 for P) are not listed and not checked. The check sees the kernel page cache of the listed files only, not the disk or controller firmware cache or the drive's own readahead.
- For P: its standard library and unlisted shared libraries were read cold from disk, unchecked, and R and C have no such files (static binaries). The bias direction of the stack factors y and z is not known and not measured: the warm venv metadata (and for Q mapped pages) shortens P and Q; the unchecked cold standard library lengthens P. Neither is called conservative.
- The wall is not the read time alone: it holds the cold read, the widening and about 7.6 s of arithmetic on box1 (more on box4 and box5). A TIE of the wall would not show equal cold-read behaviour, and no sentence here credits the difference to storage. Sectors and major faults are reported with no label and decide nothing.
- Q is not the same arithmetic as R and C (largest logit difference 0.072, rust-1b freeze) and its load is memory-mapped; no label.
- No sentence of the form "Rust starts faster" or "Rust starts slower" is made outside the M2 form above.

## 6. Exposures and deviations disclosed in the notes

(a) rust-4 recorded INVALID: its M2 check (Cached falls by 80 percent) could not pass after the first drop. One cold R run on box1 (15.8 s to exit) and the like on box3, box4, box5 stand in the rust-4 raw files; they are NOT results (no C partner, no ratio, no label), were used for sizing the cost cap alone, and the builder of this lab saw the box1 value and the spans of the others.
(b) Hosts: box1 is the labelled timing host; box2 is an unlabelled host; box3, box4, box5 are extra hosts with no label.
(c) Python arm: started and timed on box1, box2, box3; NOT RUN P start on box4 and box5 (rc -4, Illegal instruction); the arm was not pre-judged.
(d) The venv of P is made with --copies (the only change of the P install; the install is not timed).
(e) Q is not the same arithmetic (0.072) and memory-maps its GGUF; the sse42 llama build died with rc -4 on box4 and box5, the avx2 build ran on box1.
(f) The file lists come from a trace of opens on penguin with a small purpose-built ptrace tracer (strace is not installed there); the hosts' own libraries are not listed; unlisted base-system files are not checked and for P are mostly cold after the drop.
(g) The even-n order designs are not mean-balanced for every arm (R and C are). Q was kept on box1 although dropping it would have given exact balance.
(h) The cache drop needs passwordless sudo; it worked on all five hosts.
(i) The check reads inodes and directory entries of listed files (for P the whole venv), so P and Q start with warm metadata for them while R and C are fully cold; the direction of the bias of the ratios is not known.
(j) The budget file is written only at job end; no job was killed here (every host wrote a RESULT line), so nothing needed to be added by hand.
(k) The clock rule (6 discards = INVALID) did not end box2 or box3 (discards 1 and 5; voids 3 and 6).
(l) mincore and the helper ran for the first time in this lab and worked on all five hosts: both controls passed at the first try and 0 not-cold repeats occurred. The redo was not used.
(m) The P cold run sizes were guesses; the box1 job took 1,122 s of 5,400 s (under the 2,000 s redo threshold, not needed).
(n) The operator notes (BUILD.md section 7 (i)) say "ratios conservative"; the pass mark (disclosure i) says the direction is not known. The pass mark governs; this file does not call the ratios conservative.
(o) Other deviations from the plan: none found by the verifier; its limit: it compared the three named hashes in result.json only and did not re-hash files on the boxes (read-only).

## 7. Evidence

sha256 values are in EVIDENCE-SHA256SUMS next to this file (bar text, SUMM-OUT.txt, VERIFY-RESULT-R1.md, BUILD.md, FREEZE.md, and per box result.json, rows.jsonl, RESULT.txt, run.log). The bar text sha256 is f37da0bcd1966ca3d6962b0ef149f7383ca7fb55a91b3d6452cc6b9773b1cba7 (bar_sha256 of `bin/cm-exp show rust-4b`; recomputed equal).
Pass mark file sha256 (from the start record ref) a40df1d3445ed7f44186308c2660632905fe93a1913a8f0ba1caad097d5b4ac3; freeze sha256 086f10afaeece1f36d885778e84cbcc6ea6b75a4f8c68baed7f7aeaa6e398787 (start record).
Not hashed: the timed/ per-run logs of each host (they hold program output lines only and no figure cited above that is not also in rows.jsonl).
