# VERIFY-PRESTART code R2 for rust-2b (lens: same experiment, timing and scoring) 2026-10-05

VERDICT: START. No MUST found. Nothing registered was run for time (check mode prints no time; only --smoke runs were timed).
Pinned files re-hashed: run_box.py, check_equal.py, Cargo.toml, Cargo.lock, build_box.sh, summ.py, selftest.py, mutcheck.py, arm_t.py, main.rs, init.bin, order.bin all equal the A1 to A5 pins in rust-2b-amend-proposed.txt. The amend text starts with the registered text unchanged (9,967 chars).

## 1. Model and optimiser, line by line (arm_t.py against arm_b/src/main.rs)
Same: pre-LN order (ln1, q/k/v/o attention, residual, ln2, ff1, exact erf GELU, ff2, residual), final LN, tied head with no bias (one Param in Burn, one tensor in torch, so one Adam state and one gradient that sums both paths), learned positions, no dropout, scale 1/sqrt(32), causal mask before softmax, mean cross-entropy over 16x64, LN eps 1e-5, fp32, AdamW lr 3e-4 constant, betas 0.9/0.999, eps 1e-8, wd 0.01 on every tensor, no clipping, fresh gradients every step.
Read in Burn 0.21.0 source on box1: AdamW decay = p*(1 - lr*wd) then minus lr*m_hat/(sqrt(v_hat)+eps), bias correction on, amsgrad and cautious off (same as torch). burn-flex gelu = 0.5 x (1+erf(x/sqrt2)) (exact).
Differences that are framework differences, not mismatches: torch sdpa (fused, causal) against Burn matmul + mask_fill + softmax over the full 64x64; torch AdamW against Burn's separate elementwise ops. Registered as written ("sdpa attention").

## 2. Equality check, run by me on box1 (no time printed), registered configuration, N=1
n_params 1841280 both; init and order sha256 equal.
loss_fwd T=5.54213667 B=5.5421367 diff 3.1e-8 (tol 1e-5)
loss_after_step1 T=4.86082554 B=4.860826 diff 4.6e-7 (tol 1e-5)
loss_step2 diff 2.4e-8, loss_step3 diff 1.6e-8 (tol 1e-4)
params1 max abs diff 1.94e-5 in l3.ff2.w (tol 1e-4); grads1 max relative diff 1.2e-6; CHECK PASS.
Extra test of mine (numpy, double): reference AdamW step from the init file and T's gradients. Both arms agree with wd 0.01 and eps 1e-8 (mean abs error 4e-10 T, 6e-10 B); "no weight decay" would give 3.8e-8 and "eps 1e-5 or Burn defaults" 2.1e-5. So both optimisers really are the registered one. The B max 1.94e-5 comes from a few tensor elements with near-zero gradient (first Adam step is about +-lr there), not from a setting.

## 3. Timing region
Both arms time: batch build, forward, loss, backward, optimiser step, loss read-out (T item() after step, B to_vec before backward; same cost). Both exclude: file read, init load, sha256, the 5 warm-up steps (batches 0..4; timed use 5..204, order.bin holds 205), weights dump and hash (after the clock stops), JSON write. Clocks: time.perf_counter and std::time::Instant (monotonic). Per-rep value = steps/wall with steps=200 (scorer makes any other steps count INVALID). Runner uses time.monotonic.

## 4. Threads
T at N=1: 1 OS thread (counted during check run). B at N=1: 2 OS threads (main + one rayon worker; main blocks while the worker computes), rayon pool = N, seen = 1. Smoke runs: process CPU seconds per wall second 0.91 to 1.08 at N=1 for both arms. B at N=2 barely used the second thread in the tiny smoke (cpu/wall 1.08); N=2 is unlabelled.

## 5. Other checks
Arm rotation: odd reps T then B, even reps B then T, N=1 first. PSS sampled 0.25 s from smaps_rollup (lower bound, noted in facts). Final-weights hash: smoke gave one hash per arm per N across reps (run-to-run equal). Memory limit is set by the wrapper's job unit (facts record memory.max).

## 6. Scorer
selftest.py: SELFTEST PASS 70 checks. mutcheck.py: MUTCHECK PASS 58 of 58 mutants caught.
My synthetic inputs (summ.py, 5 reps, rep ranges separated unless stated): r=1.10 exactly -> TIE; r=1.1000001 -> BURN AHEAD; r=0.90 exactly -> TIE; r=0.8999999 -> BURN BEHIND; r=1.2 with B min = T max -> INCONCLUSIVE and "no overall label"; loss diff 0.05 exactly -> passes (speed label written); 0.0501 -> LOSS DIVERGENT with no speed sentence. All match the bar text. Sentences match the registered wording.

## 7. Warm-up
arm_t.py line 3 after import torch: torch.full((8,),0.5) then erf, exp, cos; before argparse, before any model or data tensor; prints mkl_warm=1; outside the timed region; also runs in check mode.

## SHOULD (none blocks the start)
S1. Pre-timing check cannot see a wrong weight decay (wd shift 3e-6*|p| is under the 1e-4 tolerance). I verified by hand that both are right; the fix would be an AdamW step reference check (my opt.py in <home>/scratch-rust2b/verify-code-r2/).
S2. Work-done gate is a lower bound only (>= 0.8 core at N=1). Add an upper bound (for example <= 1.3) for both arms.
S3. B at N=1 runs a rayon worker with a blocked main thread, so each parallel op pays a thread hand-off a single-thread build would not. It is the registered setting (pool = N); say it next to the number.
S4. Peak PSS from a 0.25 s sampler misses short peaks; also record VmHWM from /proc/<pid>/status.
S5. If every B rep hits the 3600 s per-run timeout the scorer prints "B: DID NOT RUN, cause statuses [TIMEOUT]"; the sentence should say timed out, not did not run.
S6. A single noisy rep (load or clock drop) makes the whole N label INVALID (bar says "a kept rep"); the redo10 wrapper handles INCONCLUSIVE only, an INVALID needs a fresh full run. The redo-as-10 file replaces the opening file, so that host's N=2 lines are not printed.
S7. Scorer rounds r to 9 decimals, so a ratio within 5e-10 of 1.10 or 0.90 is read as TIE. Harmless.
S8. Burn is built for the x86-64 baseline and relies on runtime CPU detection inside its crates; PyTorch uses its AVX2 kernels. Registered (RUSTFLAGS recorded); keep it in the result text.

Scratch: <home>/scratch-rust2b/verify-code-r2/ (box1, own build, ck/, smoke_out/), <home>/scratch-rust2b/verify-code-r2/edge.py (penguin).
