# rust-1b FREEZE RECORD, STAGE 2 (G-OB, G-MKL, X, T, Q; Q8_0 extra): FRAMEWORK and KERNELS answers

Written 2026-10-04 by the stage 2 builder, final fix round. Status: final as written. The sha256 of THIS FILE is what the operator writes into the ledger, in the --ref text of `cm-exp start rust-1b` as freeze-stage2=<sha256>; this file must NOT be edited after that sha256 is taken (an edit is a different freeze); BUILD.md and the other files in this folder may change. Nothing was timed, nothing was queued, nothing was registered, amended or started with cm-exp by the builder. Answers served: FRAMEWORK (stack against stack, not language) and KERNELS (our Rust matrix-vector kernels against MKL inside torch). Nothing here is about the IMPLEMENTATION answer (arm L belongs to rust-1) and nothing here is a statement about the Rust language.
The registered bar of rust-1b has bar_sha256 2e0f94a5c74a210bc121471e3c6a01f528e0cc90c9521cf3b9890d4fa5f2df46 (ledger registration 2026-10-04 09:17Z). With the staged amendment applied (state/plans/rust-lab/bars/rust-1b-amended-bar.txt; 15 lines inserted, 0 deleted; readings and records R1 to R12) the bar_sha256 is b1d2fdb1303c362f647885fe0cf9e0f7eed8d026cc4ebc817b31ccc5e07e8671, computed as `printf %s "$(cat state/plans/rust-lab/bars/rust-1b-amended-bar.txt)" | sha256sum` (the file has no trailing newline, so the sha256 of the file is the same value). The amendment is NOT applied by this record; the operator applies it before start (BUILD.md, "Exact operator commands").
Every value below is a value the bar says to record and freeze before the initial timing run. Code and scripts: private repo alice-model, remote origin https://github.com/Aefinity-AI/alice-model.git, branch cm/rust-lab, dir rust-lab/rust1b/, commit 1cdedca978192e0a14dbac2fd9da697d272664ec (pushed; `git rev-parse HEAD` equals the remote branch head at the time of writing). Working copies on penguin: ~/scratch-rust1b/ (builds), ~/feed-payload/rust1b (payload), ~/feed-payload/jobs/rust1b*.sh (wrappers).

## 1. Payload and runner (the frozen drift check)
| item | sha256 |
|---|---|
| PAYLOAD_SHA256 (the list below, 75 lines, `sha256sum -c` all OK at the time of writing; payload 2,032,759,038 bytes) | a2a1b3ee332f171cfb80adbceb4414af9427440b73964334c86e1044fb691cf8 |
| run.py (rust-lab/rust1b/payload/run.py, 1017 lines, byte-equal to the shipped file, cmp) | bcd0fa38eca6eebd338eb7a32c73978168b6ea3ae269e51154240440426e431f |
| run.sh | 65396e67f4d443888f5797123787234290b4b885120f9f5bbdbd9b92c243838c |
| t_arm.py (arm T, 129 lines) | aeaf229cf7d442ff3bcb62eacb3b87bfe47fe594446ab92a2d4a1617ebd6ce54 |
| mkfp32.py (verifies the fp32 conversion on each host) | 853ed0a430c59d2b5b741587a3dc94b79012cf51dc20d9bff1966eff3e0f274a |
Every wrapper below holds the frozen sha256 of PAYLOAD_SHA256 and of run.py, compares them with $HOME/rust1b/ on the box before anything runs, exports them to run.py (which compares again), and prints the actual and the frozen values in every RESULT line (payload_match=); a difference ends the job INVALID with nothing timed. Payload dest on the boxes: <home>/rust1b (feeder --payload ~/feed-payload/rust1b).
The runner changed in no byte in this fix round (run.py sha as in the earlier gate-only run on penguin; the N=1 and N=2 split is done in the wrappers). Its docstring still reads "R1B_PHASES (n1 or n1,n2)"; the runner accepts n1, n2 and n1,n2, and n2 alone was checked by an untimed gate run on penguin.

## 2. Job wrappers (~/feed-payload/jobs, copies in the repo at the commit above under rust-lab/rust1b/jobs/, generator rust-lab/rust1b/make_wrappers.sh <dir> <payload sha> <run.py sha>)
| wrapper | host | phases | notes | sha256 |
|---|---|---|---|---|
| rust1b-box1-n1.sh | box1 (labelled) | n1 (N=1, 5 reps) | pauses cm-tick.timer and cm-rc-watch.timer, failsafe restore timer at cap + 30 min, EXIT and TERM traps restore | 6b6f4e3e6dc4643ba2ab71c2d5ec3230334efaaeaff696a228b65bb8576224ab |
| rust1b-box1-n2.sh | box1 | n2 (N=2, 5 reps) | same timer handling; budget test before anything runs: ends PARTIAL COST-CAPPED nothing timed if (28,800 s minus the box-seconds file) is below 7,200 s | 537c9efe581b8db3f1e009a6201815bdce055fd96a317b4758517290316ce5ed |
| rust1b-box2.sh | box2 (unlabelled) | n1,n2 in one job | no unit touched | 8944aa493dbf401bf0a336aa390b99e5450c1c71317696381bc17107ae8b8687 |
| rust1b-box3.sh | box3 (unlabelled) | n1 | no unit touched | c3b0727436c39c3007be8523c11dcedbb70390b11969bdbcbc735c9fe6a982ad |
| rust1bredo-box1.sh | box1 | n1, 10 reps (the single redo) | R1B_CAP_S = 28,800 s minus the box-seconds file; timer handling as above | c998b7664646214ad78f6ecf70df9149a0ef41df54838ed024769cfa22cd7e9b |
| rust1bredo-box2.sh | box2 | n1, 10 reps | | 8daccfdac75dffb0acc742184681c17acb4b95461ef57769aeed3b7a5ea5259a |
| rust1bredo-box3.sh | box3 | n1, 10 reps | | 424107e1b0527c78aaa99384afe153925d6f1a9715de9fc2b6580e182b9f0ad3 |
box4 and box5 run no arm of this bar: no wrapper exists for them. Registered caps behind the wrappers (lab totals per host, shared with rust-1 through the file $HOME/.rust1_budget_<host>): box1 28,800 s, box2 and box3 86,400 s. MemoryMax per the bar: box1 4500 MiB, box2 and box3 2800 MiB (run.py checks the cgroup value). CPUQuota: the feeder line gives 100 percent x the logical CPUs (no binding quota, R5). The wrapper tests with a stub systemctl and systemd-run (rust-lab/rust1b/tools/wrapper_test.sh, eight cases and a name listing: timers paused and restored, failsafe not armable, TERM during the wait, box2 touches no unit, frozen-hash mismatch ends INVALID, N=2 budget test below and above its estimate, wrapper names) passed on penguin; the box1 N=2 test showed phases=["n2"] reaching the runner.

## 3. Rust arms G-OB, G-MKL, X (and the strict-order tool that made the reference logits)
- Toolchain (all builds, penguin): rustc 1.98.0 (88d9e12ae 2026-08-18), LLVM 22.1.8, cargo 1.98.0 (797e8a9bc 2026-08-05), host and target x86_64-unknown-linux-gnu, RUSTFLAGS unset, per build CARGO_PROFILE_RELEASE_OPT_LEVEL 2 or 3, lto fat, codegen-units 1, panic abort, `cargo build --release --locked --offline -q --bin cis2_ref [--features ob|mkl|x] --target x86_64-unknown-linux-gnu`; global allocator: system (glibc malloc); rayon is linked through tokenizers and never used in --plain (Threads in /proc checked by the runner). Script: rust-lab/rust1b/build_rust.sh (sha256 8dc9ca8644e9f5f67ed3d822f54166acf2272c1ec88f4a279fef3faf0a20ebcc). No musl build (box4 and box5 run no arm).
- Base: cis2-spec main e68b7512638217c48385d7b63a0c08a42d19afab with the rust-1 patch rust-lab/rust1/patches/rust-plain.diff (sha256 bb40e010d2d57d99d3b32dec46a07bf6c071212e066c82d08a9e401e28eaa3bc, applied before the stage 2 glue). Stage 2 glue: rust-lab/rust1b/make_glue_src.py (sha256 e50fdb0b3034aaf4594e383a6a531ab954c047b9d3339f9bc675771ad504697a) with xk/xk.rs (8ba04599d480816f62e29057eaf7394f1964fa1c78e8fd7c8d129c4f60f03fad) and xk/build.rs (a2cea10263d368a9c88b2045f18a34620a933dcf915204665f9a218d7ccaf1f1); its diff against the rust-1 tree: patches/rust-glue.diff (sha256 622ccbf2135b23d560b79f4f1c81f7096b8060b3f12fbf811078c000e55177ed).
- Built sources: src/main.rs 7103dee7d4299d9f1700e1c860aca71d6f438af8b6c47c5053eab1e560e01734, src/math.rs 2b5e897740f7159332df8ff717d483241d70e10eefcf715278ac35321df78067 (equal to rust-1), src/xk.rs 8ba04599d480816f62e29057eaf7394f1964fa1c78e8fd7c8d129c4f60f03fad. Cargo.lock of the glue tree: rust-lab/rust1b/locks/Cargo.lock.glue f3e008709f3cfca36d0196b6e2d4212e4e4c984177591341d6fbb5a970b2ea33 (151 packages); of the strict base: locks/Cargo.lock.strict-base 736352913da3a483b477ee0e30e4955579f554e3da4c68b1f6f4e43a6e3d6f03.
- Weights loader of G and X (stated as the code does it): the arm's own loader (StSrc in the glue source) parses the safetensors header and reads each tensor with read_exact into its own heap buffer; no whole-file buffer, no mmap (this differs from cis2_ref, which reads the whole file with std::fs::read). F32 file in, so no widening in G and X.
- Arm X scope: the matvec of main.rs is the only function replaced (every linear layer and the output projection, `xk::matvec`, AVX2 + FMA chosen at run time with a portable scalar fallback). Attention (score dot products, softmax, weighted sum), rope, rmsnorm, the activation and the residual additions are the strict scalar code of cis2_ref, the same code G uses. The KERNELS sentence carries that scope (amended bar R12).
- Binaries (frozen, timed; every file with its sha256 in section 11):
| arm | opt-level | file | sha256 |
|---|---|---|---|
| G-OB | 2 | bin/gx-ob-O2 | b72e03220c2e033d5ed48020cf5be8a7f8d6fa613cb559d42c30cf799b426688 |
| G-OB | 3 | bin/gx-ob-O3 | 77e613dd56103f008aa10ce3efa22532818e2b022f39466a8df1a682334aa582 |
| G-MKL | 2 | bin/gx-mkl-O2 | 23af7f9afe971aab82593fbe153311dd7b41fcfd3c5066e9255dc7a7604821d3 |
| G-MKL | 3 | bin/gx-mkl-O3 | 2570051d9fa05061216f61ae43bb7ef64b9f10f6d94c100f7231804ae60b8f55 |
| X | 2 | bin/gx-x-O2 | 49f9c330667864b0e5891a70eb37464094d5426d5c1580e7a868f682cd49030f |
| X | 3 | bin/gx-x-O3 | 4f40eb1b37ed75869cb15f16bc12e91294a0f66580f4f23a1c1d96b6abbc2567 |
| strict-order tool (reference logits only, not shipped, not timed) | 3 | scratch bins/gx-strict-O3 | 5a7e1ea34d92716fac0853ba19b03c142e48ceb9690ef2b9bb155fdc993de155 |
- G-OB library: Debian trixie libopenblas0-pthread 0.3.29+ds-3 (deb sha256 e3541ee2c956c64383054ba116fb6ef86bbaf40035d64e1795185029fdcf0807), run-time libs shipped in lib/ob (libopenblas.so.0 10d1c640..., libgfortran.so.5 d1c716d1..., libquadmath.so.0 da70fb5c...; debs libgfortran5 14.2.0-19 11b62b53..., libquadmath0 14.2.0-19 f5b51cf0...); OPENBLAS_NUM_THREADS=N set by the runner; the core type is recorded at the run by an untimed probe (OPENBLAS_VERBOSE=2). Linked through the openblas-src 0.10.16 crate (feature system) and cblas-sys 0.1.4; rpath $ORIGIN/../lib/ob.
- G-MKL library: pip wheel mkl 2026.1.0 (sha256 4d5a26449818a8aebd4b2aaf6b291831e691f9cf74b152df49b99cf48bbd5360; intel_openmp 2026.1.2 4612231a...; tbb 2023.1.0 64ad3524... downloaded and not shipped), subset shipped in lib/mkl (libmkl_rt, core, intel_lp64, sequential, gnu_thread, avx2, mc3, def, vml_avx2, vml_mc3, vml_def, vml_cmpt, plus libgomp.so.1 from Debian libgomp1 14.2.0-19, deb 72b7a1a3...); calls cblas_sgemv through libmkl_rt.so.3; threading layer set by the runner: SEQUENTIAL at N=1, GNU at N=2; MKL_VERBOSE head kept from an untimed probe (dispatch line on penguin: oneMKL 2026 Update 1 build 20260612, AVX2 enabled; the same line with SSE4.2 forced is in ~/scratch-rust1b/keep/mkl_dispatch_emulated_sse42.txt, sha256 07eade10148b7d7f02bcb04db8bec7e2421a7117041bf64058b84799e0903842; penguin AVX2 line sha256 070c6140660332001a924fb3117e7358baa592d74bb2fac84e7b08916842be19; a per-call figure of the library is kept from no run on penguin).

## 4. Arm Q (llama.cpp F32) and the Q8_0 extra
- llama.cpp tag b11381, commit 836d57176dc699a726c55418e4f96b8ca628e1bf (bar: b11381 or newer). Static libraries, CPU only, `-DGGML_NATIVE=OFF -DGGML_OPENMP=OFF -DBUILD_SHARED_LIBS=OFF -DCMAKE_BUILD_TYPE=Release`, driver `g++ -O2 -std=c++17`, gcc/g++ Debian 14.2.0-19, cmake 3.31.6. Script rust-lab/rust1b/build_llama.sh (137eb4d1eca824fbd38482aae3b3cd63658eed9708bb598e83d936bb43228c66). ISA flags fixed explicitly: avx2 build (SSE4.2, AVX, AVX2, BMI2, FMA, F16C; AVX512 off) for box1, sse42 build (no AVX) for box2 and box3; the runner picks the build by the avx2 flag of the host CPU.
- Driver: q/llama_drv.cpp 0187f399444d19a35bf631c2d86243feb2bb9d3e19c635c34ee455f4943f8148, q/sha256.c 4f912c42..., q/sha256.h c47fc385...; KV cache F32 set explicitly; one token at a time through the llama API; -ngl 0 equivalent (CPU only build); prints to stderr an INFO line with system_info, n_vocab, load_mode, flash_attn_type and threads (on penguin: load_mode=mmap, flash_attn_type=-1, i.e. auto).
- Binaries: bin/llama-drv-avx2 4999a4da5a1116aa282480376fa483ee9675ae7d442b388ba838192d03b315b3, bin/llama-drv-sse42 5441f651b61d713287afa35b2552afc7569a5ef16b56fc1e07a3ffae978aec85.
- GGUF files (made from the fp32 file of section 6 by the convert_hf_to_gguf.py of the pinned commit): gguf/model-f32.gguf 8de5be7131bd2250d2631bf6b84b37a654511ce339a25df0e299082579fbf3bc (539,845,056 bytes), gguf/model-q8_0.gguf c06e85f744dec3dd8f6a88927e9b078b70b079cc931c7be905a6c4caf3b1ebe0 (144,810,432 bytes).
- Q is not bit-comparable arithmetic: largest logit difference to L-C in the untimed gate run on penguin 0.072 (0.07203102112), arg-max equal at all 64 positions of all 9 rows; the other arms 0.0002 or less. The result reports the difference and the INFO line (amended bar R3).

## 5. Arm T (PyTorch)
- torch 2.14.0+cpu, transformers 5.0.0 (equal to SV5B), numpy 2.5.3, safetensors 0.8.0 (the last two differ from SV5B's 2.2.6 and 0.7.0: known low item L8), Python 3.13.5 on penguin (host Python versions not verified). 34 pinned packages in the lock: rust-lab/rust1b/requirements.lock = p/requirements.lock a7ea601f8c7e179cb9c1ae637d04b9ee2136f008f21e2bcf9546fa5cde825415; wheelhouse list p/WHEELHOUSE_SHA256 819d9f8c6a0e63e13314f05fd8596f96c5fd150c577b080d7cce191de4384061 (34 wheels, listed with their sha256 in section 11). The venv is installed in the job, offline, `--no-index --no-deps --require-hashes`, and its package list must equal the lock.
- t_arm.py: manual forward loop with KV cache fed the fixed ids (no generate()), torch.inference_mode(), no torch.compile, attention sdpa, torch.set_num_threads(N), torch.set_num_interop_threads(1), OMP_NUM_THREADS=N, MKL_NUM_THREADS=N, OMP_WAIT_POLICY=PASSIVE (T alone: known low item L9); weights loaded with safetensors load_file from w32/.
- Hidden-state hash of TRUST COLUMN item 2 is recorded by the check run; expected NO across hosts, reported and not argued.

## 6. Weights (one file per format)
- bf16 file on each host (sv5/arma/weights/model.safetensors) sha256 80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1, config.json 1d556eab73b69c7f11f64c557a2f9c6f440bd4c6b89bb2584a6b498c92603843; run.py verifies both on every host.
- fp32 conversion (exact bit shift; G, X, T and Q read it): w32/model.safetensors 19db913ad817fcd5d544972dfe168ed96f7c9c8cd40ef431da285f016cadbc1c, w32/config.json 1d556eab... (same bytes as the bf16 config); each host recomputes the conversion hash from its own bf16 file with mkfp32.py --verify and must get 19db913a...

## 7. Fixed inputs (bar: SAME WORK)
- Prompts: leading 8 rows of the sv-5 prompt set (~/sv5/arma/prompts.jsonl sha256 4b4e79241241cb19365b1ef141f157746e83a12806edc3f7e71fa3108b1bf9bc; leading 8 lines sha256 1e6a0046d7c39661bb625a492c0d943d1cd829e786bdbcf4f5c840bc43c3e826); warm-up prompt = row idx 8, discarded. inputs/prompts9.jsonl 7c7aad51edb5be753c7ae0523c389c782e8557062bbb895baa85c60936d165d7.
- Teacher-forced ids (rust-1 freeze, reused, not regenerated): inputs/ids64.jsonl e939542aa2b2112822e36c7564817ddc61ddad8d513c9a49dd3f8a4d46d60955.
- Work files: inputs/work9.jsonl df5e94eb375bd4e86a7140a1ceda0c91925ede361a254fcc0b1f22b7095aa296 (9 rows), inputs/work1.jsonl cc704306fcffe930e3fab7ef92fbb2661481768c998d90809bfad82bfa3bf41f, inputs/work_gate.jsonl f2f479082056c620b4e5d81e139a7f1954f466822e2894bc89b121ae8deb9a06 (the warm-up row alone, used by the gate-only check on penguin).
- L-C reference: inputs/REF_WITNESS.txt 1a0ff035daf2124dba11b958b2ae8187438b430dc07675a3453314f935d7453c (rust-1 freeze); inputs/ref_logits.f32 b450d0a7a0d2ee5c6e769061a6fc9201edbf88ddb856578d9e7987902f5811e6 (9 rows x 64 positions x 49152 fp32 logits), made by the strict-order build gx-strict-O3 of section 3 whose witnesses equal REF_WITNESS.txt (cmp of got.txt and want.txt: equal).
- Timed window: decode steps 2 to 64 (63 steps) of each of the 8 prompts, per-rep value = 8 x 63 tokens over the sum of the 8 prompt walls; read in the code of every arm: the clock starts at 0-based step 1 and stops after step 63 (decode_plain_forced in main.rs for G-OB, G-MKL and X, the step loop of t_arm.py for T, of llama_drv.cpp for Q and Q8_0), prefill and step 0 are outside it; run.py takes the 8 timed rows idx 0 to 7 and TIMED_TOKENS = 504.

## 8. Decode loop, lines per arm; dependency count per arm (TRUST COLUMN items 4 and 3)
Counted by rust-lab/rust1b/tools/count_loop1b.py (sha256 ad3c6ce9c4cade0187ba539c87efc1ec004c93038d86f110e26178682a630a27) over the frozen sources of section 3, t_arm.py and llama_drv.cpp; raw output state/reports/rust-lab/rust-1b/decode_loop_counts.txt (sha256 69cad9a661ab8d57323f4add342bc340b1b7feb84d39fac0a4ae103ca219513f; reproduced byte-equal in this round). Rust rule as in rust-1: the timed plain function plus every function of the arm's own sources reached by name from it; "total" = signature to closing brace, "code" = total without blank and comment-only lines. Counts describe size, not quality.
| arm | decode loop, total / code lines | functions | entry loop | forward pass | dependencies |
|---|---|---|---|---|---|
| G-OB, G-MKL (same source, different matvec) | 374 / 353 | 21 | decode_plain_forced 27 / 27 | forward_token 106 / 92 | crates (cargo tree, normal, gnu target, unique incl. the root): 93 for G-OB (openblas-src, cblas-sys), 92 for G-MKL (cblas-sys); build-time/run-time libraries: G-OB libopenblas 0.3.29 + libgfortran5 + libquadmath0 (+ libgcc_s, libm, libc), G-MKL libmkl_rt 2026.1.0 and its layers (+ libgcc_s, libm, libc, libdl) |
| X | 424 / 403 | 24 | decode_plain_forced 27 / 27 | forward_token 106 / 92 | 91 crates, no C or Fortran library (libc, libm, libgcc_s only) |
| T | 20 / 20 (t_arm.py lines 101-120; torch and transformers code not counted) | | | | 34 pip packages (the lock), libraries inside the wheels (MKL, OpenMP, libtorch) |
| Q | 16 / 16 (llama_drv.cpp lines 106-121; llama.cpp and ggml not counted) | | | | llama.cpp b11381 static, libstdc++, libm, libgcc_s, libc |
Cargo.lock holds 151 packages in all (every optional crate); the per-arm figures count what each build links.

## 9. Gate-only run on penguin (untimed checks of every arm; exit codes, mismatches and logit differences alone; no time and no memory value of any arm printed or kept)
Final payload (a2a1b3ee..., run.py bcd0fa38...), R1B_GATE_ONLY=1 on the host label penguin, 9 rows per arm, phases n1 and n2 (and a second run with phase n2 alone to check the box1 N=2 job form). All 16 arm/phase gates state=OK. mismatches = arg-max different from the forced id over the 9 rows x 64 positions; max diff = largest absolute difference of the logits to ref_logits.f32 over the 8 timed rows.
| arm | mismatches | max diff to L-C | Threads max (N=1 / N=2) |
|---|---|---|---|
| G-OB O2, O3 | 0, 0 | 0.00018692017 | 1 / 2 |
| G-MKL O2, O3 | 0, 0 | 0.00018310547 | 1 / 2 |
| X O2, O3 | 0, 0 | 0.00019288063 | 1 / not run at N=2 |
| T | 0 | 0.0002059936523 | 1 / 4 (see BUILD.md and the staged file: open finding) |
| Q (llama.cpp F32) | 0 | 0.07203102112 | 1 / 2 |
| Q8_0 extra | 17 (exempt from the arg-max condition, count recorded) | not computed | 1 / 2 |
Q INFO line on penguin: system_info CPU SSE3 SSSE3 AVX AVX2 F16C FMA BMI2 LLAMAFILE REPACK, load_mode=mmap, flash_attn_type=-1.

## 10. Not in the freeze, not run
Candle CPU, clang builds and musl builds are not built: they are not in this freeze and are not run in rust-1b (the bar: an optional arm that is not in the freeze record at start is not run later). Arm L (L-R, L-C) is not re-measured here; the L-R and L-C peak PSS rows come from rust-1. 360M is not in this bar.

## 11. PAYLOAD_SHA256 (the file whose sha256 is in section 1; every file of the payload but itself, sorted)
    23af7f9afe971aab82593fbe153311dd7b41fcfd3c5066e9255dc7a7604821d3  ./bin/gx-mkl-O2
    2570051d9fa05061216f61ae43bb7ef64b9f10f6d94c100f7231804ae60b8f55  ./bin/gx-mkl-O3
    b72e03220c2e033d5ed48020cf5be8a7f8d6fa613cb559d42c30cf799b426688  ./bin/gx-ob-O2
    77e613dd56103f008aa10ce3efa22532818e2b022f39466a8df1a682334aa582  ./bin/gx-ob-O3
    49f9c330667864b0e5891a70eb37464094d5426d5c1580e7a868f682cd49030f  ./bin/gx-x-O2
    4f40eb1b37ed75869cb15f16bc12e91294a0f66580f4f23a1c1d96b6abbc2567  ./bin/gx-x-O3
    4999a4da5a1116aa282480376fa483ee9675ae7d442b388ba838192d03b315b3  ./bin/llama-drv-avx2
    5441f651b61d713287afa35b2552afc7569a5ef16b56fc1e07a3ffae978aec85  ./bin/llama-drv-sse42
    8de5be7131bd2250d2631bf6b84b37a654511ce339a25df0e299082579fbf3bc  ./gguf/model-f32.gguf
    c06e85f744dec3dd8f6a88927e9b078b70b079cc931c7be905a6c4caf3b1ebe0  ./gguf/model-q8_0.gguf
    1a0ff035daf2124dba11b958b2ae8187438b430dc07675a3453314f935d7453c  ./inputs/REF_WITNESS.txt
    e939542aa2b2112822e36c7564817ddc61ddad8d513c9a49dd3f8a4d46d60955  ./inputs/ids64.jsonl
    7c7aad51edb5be753c7ae0523c389c782e8557062bbb895baa85c60936d165d7  ./inputs/prompts9.jsonl
    b450d0a7a0d2ee5c6e769061a6fc9201edbf88ddb856578d9e7987902f5811e6  ./inputs/ref_logits.f32
    cc704306fcffe930e3fab7ef92fbb2661481768c998d90809bfad82bfa3bf41f  ./inputs/work1.jsonl
    df5e94eb375bd4e86a7140a1ceda0c91925ede361a254fcc0b1f22b7095aa296  ./inputs/work9.jsonl
    f2f479082056c620b4e5d81e139a7f1954f466822e2894bc89b121ae8deb9a06  ./inputs/work_gate.jsonl
    6456b504ac347bd50c419667440b691f6966ad8aff5309d2f06c977fe2f9debe  ./lib/mkl/libgomp.so.1
    9acbe1a76b73007d7a4b978d30aed3f5d39b7ade386e90f7752c2a3d539ee0d0  ./lib/mkl/libmkl_avx2.so.3
    b4f086651ee5a8471140d53fedfdbbaba606287784763b0739f282872c31aa9b  ./lib/mkl/libmkl_core.so.3
    4bc51353a8473a08f18fabefdf5ab79efd98dbf337e2913a23d215748a780782  ./lib/mkl/libmkl_def.so.3
    444288ca845ec374f0435c887f0b4f745bf6bb68bc84059a11ddb0926de196b6  ./lib/mkl/libmkl_gnu_thread.so.3
    9dbdb7d4193679f028787da6b9b2b545e0e16b87a95a64ee7318f544da8b08ac  ./lib/mkl/libmkl_intel_lp64.so.3
    88e3ad1d94ba6d21ceeab6e817c0538457cf22e4113f3bb854bc52b3caf6b555  ./lib/mkl/libmkl_mc3.so.3
    b2ff0e31d7cd18c91813d8f6500f37665597d89de22649d90687aa6bf7bd2c0f  ./lib/mkl/libmkl_rt.so.3
    4e7ff529bec90a1b0ce70299258a64a2ebae7a5a6f3ec031306a6ddb39b5a650  ./lib/mkl/libmkl_sequential.so.3
    707ab79a97ab3d07d0e337bbc78383c2bde925f18d54acf930b2fd110550ed27  ./lib/mkl/libmkl_vml_avx2.so.3
    6b3daa4c0719328bb9a13c004b2f9b34c6b63bc704c840e11b1f41d64983c120  ./lib/mkl/libmkl_vml_cmpt.so.3
    5a68d0cce4a69bdbdfdfbfdf00388e3a0ed1a0d9899b202f4e9cd8f07cc727a3  ./lib/mkl/libmkl_vml_def.so.3
    6d19dfa399ccf86b1aa406b71592c6531ecff4b0bf084e2c3240ee39902e8113  ./lib/mkl/libmkl_vml_mc3.so.3
    d1c716d10039872bb5481b921d2142577c7873cad4d8d9f09028231aa7e42127  ./lib/ob/libgfortran.so.5
    10d1c640ecccd21063a7d80f90e949b1d48202830b6ec0b52b2796c5d0fbce63  ./lib/ob/libopenblas.so.0
    da70fb5c2cbdc1a3fbe984f44dd06a3b19454c75ca40bd92684328cc7a4d275a  ./lib/ob/libquadmath.so.0
    853ed0a430c59d2b5b741587a3dc94b79012cf51dc20d9bff1966eff3e0f274a  ./mkfp32.py
    819d9f8c6a0e63e13314f05fd8596f96c5fd150c577b080d7cce191de4384061  ./p/WHEELHOUSE_SHA256
    a7ea601f8c7e179cb9c1ae637d04b9ee2136f008f21e2bcf9546fa5cde825415  ./p/requirements.lock
    117bac03a25ede5df5440e855b32d556049ca169ead221505badf432fed4b101  ./p/wheelhouse/annotated_doc-0.0.5-py3-none-any.whl
    6152fdbbf9a77fdec97731721bebf7c4c44f7c29b424b0065826173efc7ed101  ./p/wheelhouse/anyio-4.15.1-py3-none-any.whl
    62f22742b58a1a33014a2b6b706588a8d7e2a88ae7bd1a6ebe8c992928483775  ./p/wheelhouse/certifi-2026.7.22-py3-none-any.whl
    255bc9599cf7748b4b1a446ccc735421bd08a2ae529a8b88597d3de5664ee360  ./p/wheelhouse/click-8.5.0-py3-none-any.whl
    698048d158dc3c9e18cc5e88b3efdd4bd0e77d76686b22adb4511cc4b2c2f0db  ./p/wheelhouse/filelock-4.0.10-py3-none-any.whl
    8dd6e646e99ea382bd85f97a45e6b526a442d79423a7dc673f1e2756d05fcb5f  ./p/wheelhouse/fsspec-2026.9.0-py3-none-any.whl
    63cf8bbe7522de3bf65932fda1d9c2772064ffb3dae62d55932da54b31cb6c86  ./p/wheelhouse/h11-0.16.0-py3-none-any.whl
    d62671bb130879cef0ee4c9ebe47a14af6c66ec53e6d84dc15936e5ffdfac82f  ./p/wheelhouse/hf_xet-1.6.0-cp38-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
    2d400746a40668fc9dec9810239072b40b4484b640a8c38fd654a024c7a1bf55  ./p/wheelhouse/httpcore-1.0.9-py3-none-any.whl
    d909fcccc110f8c7faf814ca82a9a4d816bc5a6dbfea25d6591d6985b8ba59ad  ./p/wheelhouse/httpx-0.28.1-py3-none-any.whl
    04e434b06e100eddbce9a6e817d72693a7884b10a79bd67ab48080d5c07eb899  ./p/wheelhouse/huggingface_hub-1.33.0-py3-none-any.whl
    ab7ae7122974553370f0bdb919e1a960b2cd1bc1ef0276416d896db81c14582c  ./p/wheelhouse/idna-3.20-py3-none-any.whl
    85ece4451f492d0c13c5dd7c13a64681a86afae63a5f347908daf103ce6d2f67  ./p/wheelhouse/jinja2-3.1.6-py3-none-any.whl
    9f7ebbcd14fe59494226453aed97c1070d83f8d24b6fc3a3bcf9a38092641c4a  ./p/wheelhouse/markdown_it_py-4.2.0-py3-none-any.whl
    434139499bb20b502ed3baa1f169e618f924a97e7a777fea1a49446d80106cf6  ./p/wheelhouse/markupsafe-3.0.4-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
    84008a41e51615a49fc9966191ff91509e3c40b939176e643fd50a5c2196b8f8  ./p/wheelhouse/mdurl-0.1.2-py3-none-any.whl
    a0b2b9fe80bbcd81a6647ff13108738cfb482d481d826cc0e02f5b35e5c88d2c  ./p/wheelhouse/mpmath-1.3.0-py3-none-any.whl
    e3fd2c13a7814cee3746340d8d7f8598a67f16a58bf47fb7f8793fab6efca1b0  ./p/wheelhouse/networkx-3.7-py3-none-any.whl
    a5fa86b80fd24bcd1aff83ad23be44ea323de3f787be8f8b15d4a65621e25321  ./p/wheelhouse/numpy-2.5.3-cp313-cp313-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl
    d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c  ./p/wheelhouse/packaging-26.3-py3-none-any.whl
    2363c69b61c4a97c838da3b130dcd6468f4848992b21a82f2a63ec34377137d9  ./p/wheelhouse/pygments-2.21.0-py3-none-any.whl
    0f29edc409a6392443abf94b9cf89ce99889a1dd5376d94316ae5145dfedd5d6  ./p/wheelhouse/pyyaml-6.0.3-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
    d49c18f1ea294cf4adde2e5ac256e98c82ea9d708462ce4bf799dffa7cfe8a2c  ./p/wheelhouse/regex-2026.9.29-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
    33bd4ef74232fb73fe9279a257718407f169c09b78a87ad3d296f548e27de0bb  ./p/wheelhouse/rich-15.0.0-py3-none-any.whl
    fd6f3f93c9a0a7cc2788ee63fb763353d4bd2e89b0751bc78fcf7dda00bea774  ./p/wheelhouse/safetensors-0.8.0-cp310-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
    51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670  ./p/wheelhouse/setuptools-84.0.0-py3-none-any.whl
    7ecfff8f2fd72616f7481040475a65b2bf8af90a56c89140852d1120324e8686  ./p/wheelhouse/shellingham-1.5.4-py2.py3-none-any.whl
    e091cc3e99d2141a0ba2847328f5479b05d94a6635cb96148ccb3f34671bd8f5  ./p/wheelhouse/sympy-1.14.0-py3-none-any.whl
    369cc9fc8cc10cb24143873a0d95438bb8ee257bb80c71989e3ee290e8d72c67  ./p/wheelhouse/tokenizers-0.22.2-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
    160e1bc46aeded3111d2801f8ae10dc9a1b946843a7e126b4dbf5e19c5706e95  ./p/wheelhouse/torch-2.14.0+cpu-cp313-cp313-manylinux_2_28_x86_64.whl
    c293e525e6fef9c20e8728fd4612df02a0aa31bb5fe91ecd93e123b1b7bffa73  ./p/wheelhouse/tqdm-4.70.1-py3-none-any.whl
    587086f249ce64c817213cf36afdb318d087f790723e9b3d4500b97832afd52d  ./p/wheelhouse/transformers-5.0.0-py3-none-any.whl
    b3a5fc4342d5fc8fda8fc3010b1cf117e9249aab7fae800c2eff62fd3842d97d  ./p/wheelhouse/typer-0.27.2-py3-none-any.whl
    481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8  ./p/wheelhouse/typing_extensions-4.16.0-py3-none-any.whl
    bcd0fa38eca6eebd338eb7a32c73978168b6ea3ae269e51154240440426e431f  ./run.py
    65396e67f4d443888f5797123787234290b4b885120f9f5bbdbd9b92c243838c  ./run.sh
    aeaf229cf7d442ff3bcb62eacb3b87bfe47fe594446ab92a2d4a1617ebd6ce54  ./t_arm.py
    1d556eab73b69c7f11f64c557a2f9c6f440bd4c6b89bb2584a6b498c92603843  ./w32/config.json
    19db913ad817fcd5d544972dfe168ed96f7c9c8cd40ef431da285f016cadbc1c  ./w32/model.safetensors
