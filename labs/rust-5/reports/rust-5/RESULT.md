# rust-5 RESULT (assembled 2026-10-04 ~08:10Z from raw rows; no ledger entry made here)

Raw files: state/reports/rust-lab/rust-5/{box1,box2-attempt1,box2-attempt2,box3,box4,box5}/ (harness_time.out = ROW lines, k2_pass{A,B}.out, run.log, gate.out, RESULT.txt).
Bar text used: ledger copy, bar_sha256 376fa548... (registered text plus the PINS amendment of 2026-10-04 02:34:03Z, before start). The file bars/rust-5.txt is the unamended text. Start 2026-10-04T02:34:03Z, ref cm/rust-lab@98f2258.
All medians below were recomputed from ROW lines (ns_per_call, 20 reps per arm per shape per tier). Script: ~/scratch-score/r5.py and r5b.py.

## 1. Label rule, INVALID conditions, host by host

Quoted from the bar:
- "The [sole] labelled host is box1 (tiers T0 and T1); box2 (T0) and box3 (T0) are reported with no label ("informal per Rule A")." Host line: "box4 (SSE3) and box5 (SSSE3) with Rust and C", no label.
- Per shape: "RUST AHEAD: r > 1.05 and every Rust per-rep value is faster than every C per-rep value. TIE: 0.95 <= r <= 1.05 ... RUST BEHIND: r < 0.95 and every C per-rep value is faster than every Rust per-rep value. INCONCLUSIVE: r outside 0.95 to 1.05 with overlapping rep ranges; redone once with 40 reps; if the ranges still overlap the label is TIE (NOT SEPARABLE)."
- Per host and tier: RUST AHEAD if A>=3 and B=0; RUST BEHIND if B>=3 and A=0; LEVEL if A=0 and B=0; LEANS ... if A or B is 1 or 2 and the other is 0; MIXED if A>=1 and B>=1.
- INVALID: "outputs not bit-equal; an FMA instruction in a kernel; host load 0.3 or more before or after; a kept rep with clock drop above 15 percent (three discards make that host INVALID); a library arm run with more than one thread; kernel call removed by the compiler (checksum missing); different inputs between arms (hash)." Affected host/tier/part "gets no verdict; redo".
- Pin 5 (amendment): the 1-minute load average includes our own pinned core, so it is not a gate during timing; gate = opening idle wait (load below 0.3, no other leg unit) plus a closing check for other leg units; per-rep load and runnable-other counts "are recorded, not gated".
- Pin 7: "the third discard in one job is INVALID (2 tolerated) ... a redo job starts a fresh budget of 2".
- Pin 8: "INVALID (...) > FAIL (pass not OK, host busy, summary failure) > OK-PARTIAL (any NOTRUN arm or other_runnable_flags>0; usable for arms that ran) > OK. An arm that cannot be prepared prints NOTRUN and gets no label."

Meaning of OK-PARTIAL with other-runnable flags: the bar does not drop flagged reps and does not void the host; flags are recorded, not gated (pin 5), and an OK-PARTIAL result is usable for arms that ran (pin 8). Check made: on box1 I recomputed Part A with every flagged rep dropped (98 flagged ROW lines, 5 more flagged in K2 passes (4 in pass A, 1 in pass B)). The ratios r move by 0.002 or less and every label is unchanged (T0 r 0.996 to 1.019, T1 r 1.001 to 1.040).

Literal-versus-pin reading of the load clause (both stated): literal text "host load 0.3 or more before or after" would void every host in this lab, because the pinned job's own core puts the 1-min load near 1 (ROW load_b 0.88 on box1). Pin 5 replaces that reading and was fixed before start. Under the pin: box1 opening load 0.23, pre-timing 0.28, other_leg_units=[] at open, pre-timing and close; passes. If a reader insists on the literal text, no host here has a verdict.

Host standing under the bar:
- box1 (labelled): gate 350/350 equal_ref=yes (7 arms x 5 shapes x 5 sets x 2 tiers), FMA_CHECK fma_instructions=0 on all 14 kernels, discards 0, lib_thread_violations 0, CKSUM present, data sha256 3989ed8d... same as pinned, clock 2095 to 2100 MHz, thr 0. Not INVALID. Labels: T0 LEVEL, T1 LEVEL.
- box2 attempt 1: RESULT.txt "FAIL ... INVALID discard budget 2 used up, one more discard (clock/throttle)" (third discard; torch passes also empty). INVALID under the bar, redo permitted ("redo"). Its rows were not retained in reports (RESULT and job files alone exist), so nothing in it is used.
- box2 attempt 2 (redo1, fresh budget by pin 7): harness pass "RESULT: OK ... discards=1 other_runnable_flags=76" (one clock-drop discard: K1 2048x2048 rep 9, pin MHz 2089 against ref 2785). 1 discard is inside the budget. 1000 ROW lines, 200 per shape, complete. Job RESULT.txt "FAIL ... timing pass did not finish OK: k2_passA.out: k2_passB.out:". Unlabelled by the bar anyway.
- box3: harness pass stopped at 3rd discard: "FAIL host=box3 tier=T0 INVALID discard budget 2 used up, one more discard (clock/throttle)" (discards: 576x576 rep7 rust_O2 and rep15 c_clang_O3 throttle counter changed; 1536x576 rep7 rust_O3). INVALID under the bar; 476 ROW lines, shapes 2048x2048 and 256x256 never timed, 1536x576 partial (76 rows). No verdict, any numbers are fragments. Pre-existing thr_total=4749364 at open.
- box4, box5: OK-PARTIAL, flags 27 and 46, discards 0, gate 175/175. Not INVALID, but never labelled by the bar.

Cases the bar does not cover (both readings, kinder one not chosen):
(a) A library arm process that dies with SIGILL (box2 attempt 2, box3). The bar says "an arm that cannot be prepared prints NOTRUN and gets no label" (pin 8) and "FAIL (pass not OK ...)". Reading 1: a crash is a failed pass, so the job is FAIL and the host has no usable result. Reading 2: the arm is NOTRUN (OK-PARTIAL), Rust and C rows usable for Part A. For box2 the two readings give the same outcome for the label (none: Rule A, unlabelled); they differ in whether its Rust and C rows count as usable informal numbers. I report them as informal and say reading 1 would discard them. box3 is INVALID by the discard budget under both readings.
(b) A discard that happens inside a redo job after an INVALID earlier job: the bar gives a redo but no cap on redos or on total discards across jobs; pin 7 gives each redo a fresh budget. Not capped, applied as written.
(c) Part A INCONCLUSIVE shapes need a 40-rep redo; none was run (the harness runs 20 reps). Just box4 2048x2048 hit this (see section 4). The redo did not happen; the label stays INCONCLUSIVE, not TIE (NOT SEPARABLE).

## 2. LANGUAGE (Part A), same-algorithm Rust against C, bit-equal output

Ref per host and tier = faster of the two levels for each language (bar rule). Medians ns/call, 20 reps each. r = C median / Rust median.

box1 T0 (SSE2 baseline, LABELLED host) - Rust ref rust_O3, C ref c_gcc_O2:
| shape | Rust ns | C ns | r | label |
| 576x1536 | 440996 | 442423 | 1.0032 | TIE |
| 576x576 | 161246 | 161212 | 0.9998 | TIE |
| 1536x576 | 458804 | 462362 | 1.0078 | TIE |
| 2048x2048 | 2227061 | 2270229 | 1.0194 | TIE |
| 256x256 | 32173 | 32045 | 0.9960 | TIE |
A=0 B=0: LEVEL. Other builds: c_gcc_O3 is 1.6x to 1.7x slower than c_gcc_O2 (e.g. 732759 against 442423 on 576x1536); rust_O2 is 0.9 to 2.9 percent off rust_O3 at T0; c_clang_O3 is up to 1.7 percent off rust_O3 (1536x576).

box1 T1 (AVX2, no FMA, LABELLED host) - Rust ref rust_O3, C ref c_gcc_O2:
| 576x1536 | 342274 | 343163 | 1.0026 | TIE |
| 576x576 | 123989 | 124509 | 1.0042 | TIE |
| 1536x576 | 388912 | 390713 | 1.0046 | TIE |
| 2048x2048 | 1861478 | 1935991 | 1.0400 | TIE |
| 256x256 | 24871 | 24928 | 1.0023 | TIE |
A=0 B=0: LEVEL. 2048x2048 r=1.040 is inside the TIE band; the rep ranges there are rust 1859091..2083697 and C 1933671..2152886 (overlap). rust_O2 T1 compiled to scalar vaddss and ran 1.3x slower than rust_O3 T1; c_gcc_O3 T1 was 2.1x slower than c_gcc_O2 on 256x256.

Bytes-per-second yardstick (bar asks for achieved GB/s against 2.93 GB/s): box1 T0 7.5 to 8.2 GB/s on all five shapes, T1 9.0 to 10.7 GB/s. Every shape, including 2048x2048 (16 MiB), is above 2.93 GB/s, so by the bar's own yardstick none is memory-bound; by that yardstick, not independently shown, all five behave as compute-bound on this kernel. The bar's expectation (three large shapes memory-bound, TIE by construction) is not what the measurement shows; the TIE came from compute-bound code that both compilers generate the same way. In-cache 256x256 rate: 8.2 GB/s T0, 10.5 GB/s T1 (the same as the large shapes).

Expected-versus-observed (bar estimate LEVEL about 55 percent): LEVEL observed on both tiers; not a SURPRISE flag.

Correctness (trust column): all arms equal the single-row reference on 5 sets x 5 shapes x tiers on every host (gate: box1 350 of 350, others 175 of 175, 0 not equal). Output hash y_sha16 (set 0) is the same on box1, box4, box5 (RESULT lines) and the unique (shape,set,y_sha256) list of gate.out hashes to the same md5 on all five hosts and both tiers:
576x1536 bfb7f9175de56bba; 576x576 a38e3abfa37da4c3; 1536x576 5f4995603ccc0316; 2048x2048 883ac3bab3549353; 256x256 bb1ce0580e40fa9e.
Unsafe lines (BUILD.md): Rust unchecked kernel 18 (17 in the kernel block + 1 ud2 helper); safe-iterator variant 1 + 1. Safe variant timing (extra, no label), box1 T1: rustsafe_O3 339645 / 123990 / 389761 / 1877428 / 24808 ns against unchecked rust_O3 342274 / 123989 / 388912 / 1861478 / 24871; panic_bounds_check_refs=0 in all four safe builds. Safety cost in this loop: within about 1 percent.

## 3. KERNELS (Part B), speed ratios, arithmetic differs

Our side = faster of Rust and C kernels at the tier (rust_O3 on box1 except 576x576 and 256x256 at T0 where c_gcc_O2). q = library median ns / our median ns (below 1 means our loop is slower). Library arms vectorise across k and use AVX2 FMA on box1 (OpenBLAS core Haswell, MKL AVX2, ggml avx2=1 fma=1, threads 1 on every library arm, 0 thread violations).

box1 T1 (the labelled comparison): q per shape 576x1536 / 576x576 / 1536x576 / 2048x2048 / 256x256
- K1 OpenBLAS sgemv 0.502 / 0.401 / 0.445 / 0.796 / 0.374, all OURS BEHIND (non-overlapping), host label OURS BEHIND. Library 171923 / 49712 / 172929 / 1481323 / 9300 ns.
- K2 torch MKL linear (includes Python dispatch; 1x1 floor per rep 3.98 to 7.99 us, median 4.14 us per call, not subtracted) 0.531 / 0.465 / 0.566 / 0.825 / 0.692, all OURS BEHIND, host label OURS BEHIND. Library 181794 / 57677 / 220220 / 1536226 / 17207 ns.
- K3 ggml F32 0.659 / 0.530 / 0.606 / 0.832 / 0.564, all OURS BEHIND, label OURS BEHIND. Library 225672 / 65673 / 235671 / 1548074 / 14017 ns.
- K4 ggml Q8_0 (no label, different precision) q 0.268 to 0.427. K5 torch dynamic int8 (no label): 102727 / 72901 / 105524 / 453813 / 56741 ns.
box1 T0 (no label): K1 q 0.290 to 0.665, K2 0.358 to 0.690, K3 0.407 to 0.702, all five shapes behind for K1, K2, K3.
Expected 2 to 8 on cache-resident shapes: observed 1/q = 2.5 to 2.7 (K1), 1.4 to 2.2 (K2, K3) on 256x256 and 576x576 at T1; on the large shapes 1/q = 1.2 to 2.2, 2048x2048 1.2 to 1.3. Memory-bound expectation under 2: observed within it on 2048x2048 (1/q 1.2 to 1.3).

box2 attempt 2 (N4020, SSE4.2, T0, no label): K1 (OpenBLAS Nehalem core) q 0.368 / 0.370 / 0.419 / 0.721 / 0.394; K3 ggml F32 (avx2=0 fma=0) q 0.511 / 0.663 / 0.729 / 0.874 / 0.839; K4 Q8_0 q 1.003 / 1.215 / 1.045 / 0.978 / 1.241 (no label). K2 NOT RUN (see below).
box3 (INVALID, fragments, no verdict): K1 q 0.383 / 0.369 / 0.447 (576x1536, 576x576, 1536x576 partial); K3 q 0.488 / 0.661 / 0.660; 2048x2048 and 256x256 NOT RUN (host went INVALID at the third discard). K2 NOT RUN.
box4, box5: no library arms (Rust and C arms, no libraries, per the bar). Not run.

K2 on N4020 (box2 attempt 1 and 2, box3): run.log line, verbatim: "<home>/rust5/run.sh: line 81: 495006 Illegal instruction     taskset -c "$CORE" "$PY" -W ignore "$W/harness/k2_torch.py" --data "$DATA" --host "$HOST" --core "$CORE" --max-discards "$(dleft)" $K2A > "$OUT/k2_passA.out" 2>&1" (box2 attempt 2; pass B line 84, pid 496275; box3 pids 390722 and 391389). k2_passA.out and k2_passB.out are 0 bytes on both hosts: no Python traceback, no HDR line. FRAMEWORK deployability finding: the k2_torch.py process of the stock torch 2.14.0+cpu wheel died with SIGILL on the Celeron N4020 (flags include ssse3 sse4_2 popcnt; no avx) in the 4 documented processes (box2 attempt 2 passes A and B, box3 passes A and B; box2 attempt 1 left empty k2 outputs and no run.log, so it is not counted). What the logs do not settle: the pre-timing probe (run.sh line 56, K2 linear alone, --no-k5, shape 256x256) DID run on the same hosts and printed "oneMKL 2024.0 ... Intel(R) SSE4.2 enabled processors" with SGEMM NThr:1, so the fp32 linear call itself executed; the timed passes additionally build the K5 dynamic-int8 arm (torch.ao.quantization.quantize_dynamic, wrapped in try/except which cannot catch a signal). The crashing instruction was not isolated (no gdb or core, nothing may be run on the boxes). So: stock wheel full K2+K5 process crashes on this CPU; whether K2 alone is deployable on it is the open question and the probe says it may be. No K2 speed number exists for N4020.

## 4. Unlabelled hosts (informal; Rule A or INVALID)

box4 (AMD Sempron SI-42, SSE3, T0, Rust O2 scalar-4-accumulator against GCC O2; this compares LLVM autovectorisation with GCC autovectorisation of the same loop): OK-PARTIAL, flags 27, discards 0. rust ref rust_O2, C ref c_gcc_O2:
576x1536 1251072 vs 1531296 r=1.224 AHEAD; 576x576 501518 vs 619219 r=1.235 AHEAD; 1536x576 1311064 vs 1632079 r=1.245 AHEAD; 2048x2048 5555369 vs 7024214 r=1.264 INCONCLUSIVE (a Rust rep at 7618949 overlaps the C range 7021552..7036668; no 40-rep redo run); 256x256 73801 vs 103142 r=1.398 AHEAD. A=4 B=0 (A=5 if the overlap were resolved for Rust); either way the rule gives RUST AHEAD. Informal. Achieved 2.65 to 3.55 GB/s: at the 2.93 GB/s figure, so memory-bound and compute-bound are not separable on this box.
box5 (SSSE3, T0): OK-PARTIAL, flags 46, discards 0. rust_O2 against c_gcc_O2: 1138309 vs 1229016 r=1.080; 475124 vs 528311 r=1.112; 1360461 vs 1504525 r=1.106; 5181009 vs 5652528 r=1.091; 69384 vs 81250 r=1.171. All five RUST AHEAD (ranges disjoint), A=5: no label, ratios shown. Achieved 2.6 to 3.8 GB/s.
box2 attempt 2 (N4020 Celeron, T0): rust_O3 against c_gcc_O2: 551144 vs 545216 r=0.989; 179608 vs 177364 r=0.988; 549096 vs 541986 r=0.987; 2992530 vs 2868531 r=0.959; 36726 vs 36063 r=0.982. All TIE (2048x2048 r=0.959 is inside the band), A=0 B=0: no label, ratios shown, with one clock-drop discard and flags 76. Achieved 5.9 to 7.5 GB/s.
box3 (N4020C, T0, INVALID): 576x1536 r=0.991, 576x576 r=0.987, 1536x576 r=0.989 (partial reps); no verdict, shown to say the fragments agree with box2.
Pattern, stated plainly: on the two oldest CPUs (box4, AMD Sempron SI-42; box5, Intel Pentium T2310; neither has AVX2) the Rust O2 build took 8 to 40 percent less time than every C build; on box1 and box2 the two are inside the tie band, and the partial box3 rows (INVALID host) agree with box2. None of box2 to box5 carries a label. The rows do not say why; the FMA_CHECK instruction mixes differ (Rust O2 T0 4 addss/4 mulss, gcc O2 T0 1 addps/1 mulps), which is a compiler-codegen difference of the same loop, not a language property by itself.

## 5. Sentences (the bar's, filled; no other conclusion sentence)

LANGUAGE (Rust against C, fp32 dense dot, 4-row interleaved, bit-equal output, T0 on box1): the Rust kernel is level with the C kernel on 5 of 5 shapes (compute-bound shapes named: 576x1536, 576x576, 1536x576, 2048x2048, 256x256, by the achieved-GB/s yardstick); host label LEVEL. On hosts without AVX2 this compares LLVM and GCC autovectorisation of the same loop. It says nothing about library kernels.
LANGUAGE (Rust against C, fp32 dense dot, 4-row interleaved, bit-equal output, T1 on box1): the Rust kernel is level with the C kernel on 5 of 5 shapes (compute-bound shapes named: 576x1536, 576x576, 1536x576, 2048x2048, 256x256); host label LEVEL. On hosts without AVX2 this compares LLVM and GCC autovectorisation of the same loop. It says nothing about library kernels.
KERNELS (speed only, arithmetic differs): our strict-order kernel is behind OpenBLAS on box1 (T1), q=0.374 to 0.796 (0.502, 0.401, 0.445, 0.796, 0.374 by shape). The library vectorises across k and may fuse; our order is fixed for bit-identity. It says nothing about the Rust language.
KERNELS (speed only, arithmetic differs): our strict-order kernel is behind MKL via torch (includes Python dispatch) on box1 (T1), q=0.465 to 0.825 (0.531, 0.465, 0.566, 0.825, 0.692 by shape). The library vectorises across k and may fuse; our order is fixed for bit-identity. It says nothing about the Rust language.
KERNELS (speed only, arithmetic differs): our strict-order kernel is behind ggml F32 on box1 (T1), q=0.530 to 0.832 (0.659, 0.530, 0.606, 0.832, 0.564 by shape). The library vectorises across k and may fuse; our order is fixed for bit-identity. It says nothing about the Rust language.

What this does not show: one kernel (one fp32 4-row-interleaved matrix-vector loop), five shapes, one input set timed (set 0), single thread, plain loops with no intrinsics (hand-written AVX2 Rust is out of scope and lost earlier), x86-64 CPUs (box1 i5-5200U carries the label; no ARM, no GPU), 20 reps, a Rust no_std object built as a static library behind a C ABI and timed from a C harness (so it says nothing about Rust inlining or cargo-built binaries), rustc 1.98.0 against gcc 14.2.0 (clang 19.1.7 reported as an extra). Two things the bar's scale line also limits: the bar answers LANGUAGE for this loop and KERNELS as speed, and it makes no statement on FRAMEWORK, TOOLCHAIN or IMPLEMENTATION beyond what is in the tables. The Part B result is not a statement about Rust: the Rust and the C build of our loop are level with each other and both are behind the libraries, which sum in a different order. No arm here tests why the libraries are faster.

Separate answers to the founder question, not blended: LANGUAGE: level on the labelled host, both tiers (hosts without a label, ratios shown: on the two pre-AVX2 boxes, box4 AMD Sempron and box5 Intel Pentium T2310, the Rust O2 build took 8 to 40 percent less time than C; on the Intel Celeron N4020 the two were inside the tie band). IMPLEMENTATION (our loop against library kernels): our fixed-order loop is 1.2x to 2.7x slower than OpenBLAS, MKL and ggml F32 on box1. FRAMEWORK: torch full K2+K5 process crashes with SIGILL on N4020 with the stock wheel; K2-alone probe ran; box1 K2 includes about 4.1 us dispatch. KERNELS: as the K1, K2, K3 sentences. Build facts recorded (not a TOOLCHAIN verdict; lab rust-4 covers the toolchain): no FMA, bounds-check or output-bit difference between rustc and gcc builds (0 FMA, 0 panic_bounds_check, one set of y hashes on five CPUs); the unsafe cost is 18 lines.

## 6. Disclosures

- Box2 history: attempt 1 (feed rust5-box2) ended FAIL/INVALID discard budget (third clock/throttle discard), torch arm outputs empty (no run.log kept, so the SIGILL is not documented for this attempt); no rows retained here. One redo (rust5-box2-redo1, fresh budget by pin 7): harness pass OK with 1 discard; K2 passes SIGILL; job FAIL. No further redo was queued.
- Harness behaviour: run.sh treats a K2 process crash as "timing pass did not finish OK", so the job result is FAIL even though the Rust and C rows (and K1, K3, K4) are complete on box2 attempt 2. This is the harness reading of pin 8, not a bar clause (see case a).
- Box3 ended INVALID by discard budget (throttle counter changes: thr_total in the millions at open); box3 is the same CPU family as box2.
- box1 flagged reps: 98 harness ROW lines and 5 K2 ROW lines carry runnable_other_b/a above 0 (flags=103 in RESULT.txt, 98 + 4 + 1); none dropped; sensitivity check above shows no label change.
- box1 closing load average 1.11 (own job); opening 0.23. The literal load clause in the registered text conflicts with pin 5; pin 5 applied.
- The registered cache-regime expectation (three large shapes memory-bound) was wrong by the bar's own yardstick (8 to 10 GB/s achieved on box1 against 2.93 GB/s).
- No 40-rep redo was run (box4 2048x2048 INCONCLUSIVE stays so). No box1 shape needed one.
- Rust bytes are the same no_std object on every host (pin 3); C is built by each host's gcc 14.2.0. box4 and box5 use the lite payload (no K2). Torch 2.14.0+cpu, ggml commit 11fe02151f79c41d0d4af7da708755d73b9c0da6, OpenBLAS 0.3.29 (Haswell core on box1, Nehalem on box2/box3).
- The 2.93 GB/s figure comes from RESEARCH_LOOP.md E6 (2026-09-04) and is contradicted here; it is not re-measured in this lab.
- Penguin gave no timing numbers; nothing was run on any box by this assembly (read access via scp and ls).
