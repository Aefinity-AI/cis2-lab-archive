# DIAGNOSTIC, no pass mark, one host (box1, Core i5-5200U). Written 2026-10-04 about 12:45Z. Published 2026-10-16 as part of the CIS-2 archive.

Scale: 13,088 parameters, 200 SGD steps, byte MLP. This changes no recorded result: the recorded rust-2a numbers (Rust 0.4136 s, C 0.2669 s, ratio 1.55 on box1) stay as recorded, and the label PORT EQUAL is untouched. Nothing here transfers to larger models, GPUs or PyTorch. Answers LANGUAGE/IMPLEMENTATION detail for this one port alone; FRAMEWORK, KERNELS and TOOLCHAIN are not answered here.

## What was compared
Static, on penguin (no times): build settings. Rust shipped: rustc 1.98.0, release profile opt-level 3, fat LTO, codegen-units 1, panic=abort, RUSTFLAGS unset (baseline x86-64, no target-cpu). C: gcc 14.2 -O2, no LTO, -ffp-contract=off -mno-fma, baseline x86-64, mathpin.c a separate file (calls cross a translation unit). Libm policy: neither side calls platform exp/ln/pow (pinned code in both); floor is inlined in both (no floorf call). Rust main (all inlined by LTO) has 57 panic_bounds_check call sites, 345 calls in total; the 4 backward-pass loops and dot_seq index with `a[i]` on Vecs/slices. Packed ops: Rust main 186 mulps / 146 addps (SSE2 baseline, no ymm); C main has 11 mulps / 7 addps, with exp/ln/matvec/dot_seq as scalar out-of-line functions. No allocation inside the step loops in either arm (buffers made before the loop). I/O: both write 4 checkpoint files of 52 KB in one write (C fwrite, Rust one write_all), 4 small manifest lines; whole-process wall minus in-process wall was 0.003 s in the recorded run, so I/O and start-up are not the gap.
Dynamic, box1, jobs rust2a-diag-box1 (perf) and rust2a-diag2-box1 (variants), host idle (load 0.09). perf is installed but blocked for user cm (perf_event_paranoid, no kernel profiling): perf stat/record produced no data (files empty, kept in diag-box1/). So the cause is located by variants, not by profile. Variants built on penguin (same profile as shipped, gnu target, one change at a time), 7 runs each in rotated interleaved order, in-process wall (TRAIN_WALL_S), median. Every run of every variant wrote the 4 reference digests (checked each run, 63/63 rows equal).

## Variants (box1, in-process wall, median of 7)
| arm | change | median s | ratio to C -O2 | digests equal | gap to C -O2 removed |
|---|---|---|---|---|---|
| C -O2 (reference arm) | as recorded build | 0.2667 | 1.00 | yes 7/7 | |
| C -O3 | -O3 | 0.2412 | 0.90 | yes 7/7 | |
| C -O2 -flto | LTO | 0.2370 | 0.89 | yes 7/7 | |
| Rust shipped | recorded binary | 0.4110 | 1.54 | yes 7/7 | 0 |
| Rust A_base | rebuilt from diag source, same flags (macros inactive) | 0.4106 | 1.54 | yes 7/7 | 0 (rebuild matches shipped) |
| Rust B_unchecked | no bounds checks in 4 backward loops + dot_seq (unsafe get_unchecked) | 0.2896 | 1.09 | yes 7/7 | 0.121 s of 0.144 s = 84 pct |
| Rust C_expcast | to_int_unchecked for `k as i32` in exp | 0.4194 | 1.57 | yes 7/7 | none (+0.009 s, within noise) |
| Rust D_haswell | -C target-cpu=haswell (AVX2 packed, no fma use) | 0.3549 | 1.33 | yes 7/7 | 0.056 s = 39 pct (not like for like: C stayed baseline x86-64) |
| Rust E unchecked + haswell | both | 0.2951 | 1.11 | yes 7/7 | 0.116 s; no extra gain over B alone |
Ratio of shipped to C -O2 in this job 1.54 (recorded 1.55), so the job reproduces the gap.

## Located cause
Bounds checking in the backward-pass hot loops (dW2 update 256x32, the 32 column reductions over 256 rows, dW1 update, dV reduction) plus the dot_seq inside matvec. Removing the checks at 18 call sites (57 to 39 in main) takes the Rust arm from 0.411 s to 0.290 s: 84 pct of the 0.144 s gap to C -O2, ratio 1.54 to 1.09. The checks in these loops also stop the compiler vectorising the elementwise updates, so size cannot be split between "check instructions" and "lost vectorisation" with these data. Digests stay identical (the indices are in range by construction; not a proof for other inputs).
Not a cause here: LTO/codegen-units (already fat/1; C with LTO is faster, not slower), the exp cast, checkpoint writes, allocation, start-up, libm.
Residual: B_unchecked is 0.023 s (9 pct) above C -O2 and 0.049 s above C -O3; not located. Candidates (untested): the 39 remaining check sites in forward loops, per-element exp/tanh inlining differences.
What closes the bulk of the gap: a code change (unchecked indexing in hot loops, or slice-length hoisting), not a Cargo or compiler flag. A flag (target-cpu=haswell) closes 39 pct but changes the machine the binary needs, which matters for old CPUs. The recorded rust-2a numbers stay as recorded.

## Not examined
Which of the 5 loops carries how much (one variant per loop needs more jobs; the two-job limit was used); a safe rewrite (iterators, chunks_exact, slice hoisting) instead of unsafe; the residual 9 pct; the other hosts (no ssh to box2 to box5); musl builds; opt-level 2 or -C llvm-args variants; perf profile (blocked); phone/aarch64; any larger model. One host, 7 reps, no discard/throttle screening beyond the idle gate and load 0.09; C arms rebuilt on box1 by the job.

## Plain paragraph
The Rust version of our small trainer was about one and a half times slower than the C version on the old laptop. The cause is that Rust checks, on every array access, that the position is inside the array, and in the busiest loops those checks also keep the compiler from doing several numbers at once. When those checks were removed in the busiest loops (a change in the code, not a setting), the Rust version came to within about nine percent of C and still wrote the same four output files, byte for byte. This was one machine and a tiny model, the earlier recorded numbers stay as they were, and it says nothing yet about bigger models, other computers or the other questions in the Rust study.

## Files
diag-box1/ (medians2.txt, rows2.txt, run.log, run2.log, stat_*, empty perf outputs); code <home>/projects/alice-model-cm-rust-lab/rust-lab/rust-2a-diag/ (branch cm/rust-lab); payload ~/feed-payload/rust2a-diag (copy of rust2a plus var/; used instead of ~/feed-payload/rust2a with dest <home>/rust2a-diag-payload so the recorded payload and box1 <home>/rust2a stay untouched).
