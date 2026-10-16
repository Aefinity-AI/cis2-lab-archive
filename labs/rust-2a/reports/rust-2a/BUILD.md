# rust-2a BUILD (2026-10-04, builder subagent; NOT started)

Scale: 13,088 parameters, 200 SGD steps, byte MLP. Nothing here transfers to 135M to 360M models trained on a GPU, to PyTorch, or to training speed at any real size. A Rust-trained model of real size does not exist and is untested.

## Where things are
- Code (private repo alice-model, branch cm/rust-lab, worktree ~/projects/alice-model-cm-rust-lab, dir rust-lab/rust-2a/):
  commit 4a41cbb91fbb5fcb188599b549d234458179f173 = the INITIAL COMPLETE ATTEMPT tree (rust/ is frozen from here; any later change to rust/ is a fix cycle).
- Payload for the feeder: ~/feed-payload/rust2a (14 MB, PAYLOAD_SHA256 file inside; sha256 of that file 0b5e0947ec28e963c828ecae8d6fc4b688037993dbb690c44f8ddf412fc0d92c (re-pinned after the runner fixes below; the old value 25831808... is void)). Dest on boxes <home>/rust2a.
- Job wrappers: ~/feed-payload/jobs/rust2a-{penguin,box1..box5}.sh (digest), rust2a-timing-box{1..5}.sh (wall time). Copies in the repo under rust-lab/rust-2a/jobs/.
- Nothing was queued in cm-feed and cm-exp start was not run (queued jobs would run before start).

## What was built
1. C original, verbatim from ~/projects/alice-model-cm-cap1c (branch cm/cap1c-c-trainer, commit cbacbe9605eca51caffba8f20ee280d9774d8e72): cap1c_train.c 274 lines, mathpin.c 358, mathpin.h, sha256.c/h, Makefile, copied into rust-lab/rust-2a/c/ with sha256 in c/ORIG_SHA256.txt:
   85af26a2... cap1c_train.c, 3ae50c47... mathpin.c, 7dde9a92... mathpin.h, 4f912c42... sha256.c, c47fc385... sha256.h, 1537326e... Makefile (full values in the file).
2. One patch to the C trainer (c/cap1c_train.export.patch, sha256 3d3288a2280c7f7e26a6b89e79e2698994ea02fa8118f1771faae4ebd97dd3d8), arithmetic lines untouched:
   - `#define _POSIX_C_SOURCE 200809L` and `#include <time.h>` (for clock_gettime under -std=c11);
   - optional `argv[2]=--export-inputs argv[3]=DIR` writes init_params.bin (V,W1,b1,W2,b2 raw fp32, 52,352 bytes) and batch_order.bin (200 x 64 pairs byte_in,byte_target, 25,600 bytes) once after init_params();
   - a monotonic-clock line `TRAIN_WALL_S=` on stderr after the 200 steps (in-process wall, measurement (a)).
   The reference digests come from the VERBATIM files ("orig" builds); the patched binary ("patched") is built too and must give the same digests (checked below, it does).
3. Exported inputs (rust-lab/rust-2a/inputs/, produced by the patched C trainer, penguin, -O2):
   - init_params.bin  sha256 3a1b88b2cb90bb0f81cfca4221986f5a6ba28ef267fa01a662881653a16aeb7b
   - batch_order.bin  sha256 f5e254381cc9c6db7f5f71f04ef93b772441e7fad926a65b70db76cc1c96b21e
   The corpus is not exported: the batch file carries the (input byte, target byte) pairs, which is all the trainer reads from it. The Rust binary takes both hashes on the command line and exits 4 before any training if either differs.
4. Rust port rust-lab/rust-2a/rust/: src/main.rs (training loop 1:1: same loop nesting, same left-to-right accumulation, no mul_add, plain `a*b + c`), src/mathpin.rs (ftz/daz pin by inline asm stmxcsr/ldmxcsr and the C self-test, exp_pinned, ln_pinned, tanh_pinned, dot_seq, matvec; the only float library operation is floor, an exact IEEE operation, as in the C), src/sha256.rs (vendored std-only SHA-256). Cargo.lock lists 1 package (rust2a itself): 0 dependencies beyond std. Extra (unlabelled): `--check-gen` regenerates corpus, batch order and initial weights in Rust and compares with the exported files; it prints `GEN_CHECK init=equal|DIFF batch=equal|DIFF`.
5. Runner rust-lab/rust-2a/run.sh (digest mode, and MODE=timing), make_payload.sh, rust/build.sh, c/build_c.sh, c/vecgen.c.

## Versions, flags, hashes (penguin, 2026-10-04)
- rustc 1.98.0 (88d9e12ae 2026-08-18), LLVM 22.1.8, cargo 1.98.0; host x86_64-unknown-linux-gnu; targets x86_64-unknown-linux-gnu and x86_64-unknown-linux-musl (musl-tools and the rust target installed this session; added to ~/dev-setup/bootstrap.sh, pushed 3b2a73b).
- RUSTFLAGS unset (baseline x86-64, no target-cpu). Profiles (Cargo.toml): release = opt-level 3, lto fat, codegen-units 1, panic abort, overflow-checks off; o0 = same with opt-level 0, lto off. `cargo build --locked --offline -j1 --profile <p> --target <t>`.
- gcc (Debian 14.2.0-19) 14.2.0 on penguin and all five boxes (glibc 2.41, x86_64 on all five: checked `uname -m` over ssh). C flags (from the cap-1c Makefile, only -O varied): `-O{0,2} -ffp-contract=off -fno-fast-math -fexcess-precision=standard -std=c11 -Wall -Wextra -mno-fma`, `-lm`. C is rebuilt on each host by run.sh.
- Rust binaries (identical when built twice into separate target dirs: BUILD-TWICE = yes; also identical when rebuilt from the committed tree):
  - 97f78c799021c788dfc7aa762b69478071523ff293cdb4bdc7f8f826d66f91f7  rust2a-gnu-O0
  - a257e1fac30149c7f9ad0594727dd52731cd061e85845c9d1983bbc527ca1c45  rust2a-gnu-O3
  - caed738e9bde2cf9e349d63151d06e7983600e50727b55d5aa91d2a01854c4fd  rust2a-musl-O0 (static-pie)
  - e1534fe6cefa5c03b8044ca6176e8d0c4e3d568c782201455e82bfc7b94b48c9  rust2a-musl-O3 (static-pie)
  Source hashes: Cargo.lock 3bb85083..., main.rs e8e7945d..., mathpin.rs 52d68a81..., sha256.rs 401cad32... (BUILD_ENV.txt in the payload bin/).
- Binary checks: no imported or called exp/log/pow/tanh symbols in any of the 4; 0 FMA instructions in any of the 4.
- Builds tried by the runner (a superset of the bar's list; any difference on any of them is PORT DIFFERENT): Rust {gnu, musl} x {O0, O3} on every host where they start (box4 and box5 get the same musl static files); C orig {O0, O2} plus patched {O0, O2}.
- Reference digests, from R/2026-09-24-cap1c-c-trainer-cross-isa.md (also REF_DIGESTS.txt):
  fd64cf9e032ee182e2623aaada3e71918d4b8d31c25d8dfc876fed74a85e3e12 (50), d36bd7fd164ba77481a9d8f25f2fbd1acd83561f68cb8ceca9b3ba99be57705c (100), 3887f7b3f512a6a2ed4bb72572966f46b90366f6a546aafe758ae7587db76ccd (150), f665ffecfabba7a4a6c0248c73107ecf8953efd9ef20b861a50fbc3ce818fd3e (200).
- C original rebuilt on penguin this session (second reference set, C only): orig -O0, orig -O2, patched -O0, patched -O2 all give the 4 digests above (the two reference sets agree; the "reference broken" INVALID condition is not triggered). In-process wall on penguin (informal, not a timing result): -O2 about 0.19 s, -O0 about 1.2 s.
- Phone aarch64: no aarch64 musl build made; the line reads "phone: NOT RUN".
- Hosts: box1..box5 are all x86_64 with gcc, so no 32-bit target was needed.

## Pre-start tests run (allowed kinds only; none runs the 200-step training of the Rust port)
- cargo test (dev profile and --release): 4 passed. sha256 known answers (empty, abc, 1,000,000 x 'a', split-update boundaries); exp/ln/tanh 9,000 vectors bit-exact against the C functions (3,016 lines per function: 16 special inputs incl. +-0, subnormal, +-inf, plus 3,000 pseudo-random; vectors/vectors.txt sha256 71fb9978ae5f1d076e9666aa2496fe7718a0da0c72a3e4e9d81a7e898c79cf41, made by c/vecgen.c); forward layer chain for batch position 0 (W1, b1, tanh, W2, b2, softmax, loss) bit-exact vs C on the exported init (h_pre, h_act, logits, probs, loss); Rust generators reproduce the exported init_params.bin and batch_order.bin exactly (extra, unlabelled). Backward pass and SGD update are NOT covered by any pre-start test (that is the quantity under test).
- Argument parsing and hash gate: no args, missing file, wrong init sha (exit 4 before training), unknown flag.
- run.sh plumbing smoke on penguin with STUB "Rust" binaries (scripts that print the reference digests and write no checkpoints): real C builds and runs ran, runner reported equal=no because the checkpoint files were absent (as designed), timing mode printed rows. Stub outputs are not results.
- Not run: the Rust trainer to completion on any host, any Rust-vs-C timing comparison.

## Exact commands for the start step (not run)
```
cd <root>
bin/cm-exp start rust-2a --ref cm/rust-lab@4a41cbb91fbb5fcb188599b549d234458179f173
# 1. penguin, the initial complete attempt (digest only, MemoryMax 500M, CPUQuota 60%, systemd-run --user); writes state/reports/rust-lab/rust-2a/penguin/RESULT.txt
bash ~/projects/alice-model-cm-rust-lab/rust-lab/rust-2a/jobs/rust2a-penguin.sh
# 2. boxes, digest jobs (queue order; no --after):
P=~/feed-payload; F=bin/cm-feed; J=$P/jobs
for b in 1 2 3 4 5; do $F add cm-box$b rust2a-digest-box$b $J/rust2a-box$b.sh --payload $P/rust2a --payload-dest <home>/rust2a --memory-max 500M --cpu-quota 60%; done
# 3. wall-time jobs, queued after the digest jobs (box1 counts; others informal; host idle, no real quota; run.sh waits up to 10 min for load < 0.3, then FAIL):
$F add cm-box1 rust2a-timing-box1 $J/rust2a-timing-box1.sh --payload $P/rust2a --payload-dest <home>/rust2a --memory-max 4500M --cpu-quota 400%
$F add cm-box2 rust2a-timing-box2 $J/rust2a-timing-box2.sh --payload $P/rust2a --payload-dest <home>/rust2a --memory-max 2800M --cpu-quota 200%
$F add cm-box3 rust2a-timing-box3 $J/rust2a-timing-box3.sh --payload $P/rust2a --payload-dest <home>/rust2a --memory-max 2800M --cpu-quota 200%
$F add cm-box4 rust2a-timing-box4 $J/rust2a-timing-box4.sh --payload $P/rust2a --payload-dest <home>/rust2a --memory-max 2900M --cpu-quota 100%
$F add cm-box5 rust2a-timing-box5 $J/rust2a-timing-box5.sh --payload $P/rust2a --payload-dest <home>/rust2a --memory-max 1500M --cpu-quota 200%
```
Each digest job ends with `RESULT: OK host=<h> c=<4 digests, C -O2> rust=<4 digests of the first differing Rust build, else musl-O3> equal=<yes|no> rust_builds=.. c_builds=..`; equal=yes only if every C and Rust build, and every written checkpoint file, equals the reference. The per-build lines (RUN ...) and GEN_CHECK lines are in the job log and RESULT.txt tail. Timing job rows: `ROW rep= arm= whole_wall_s= in_process_wall_s= valid=`; each rep is preceded and followed by a SNAP line (load average, per-core MHz, throttle counters); a rep with a throttle-counter change, other runnable tasks, or max-core MHz below 75 percent of cpuinfo_max_freq is discarded and repeated (up to 4 tries; the last try is kept with valid=NO:<reason>). Arm order rotates per rep.

## Notes and limits for the result writer
- The initial-attempt label is fixed by the penguin run of commit 4a41cbb plus the host runs of the same binaries. Any edit under rust-lab/rust-2a/rust/ after the first comparison is a fix cycle.
- Suggested amend-bar (pins only, before start): rustc 1.98.0 / LLVM 22.1.8, gcc 14.2.0, the Rust profile flags above, the four binary sha256 values, the two input sha256 values, commit 4a41cbb. Not applied by the builder.
- Rule A: the timing jobs follow the 2026-10-04 BOXES.md ruling, but the first timing job on box1 is itself the CPUQuota/thermal check for that host; cite its log.
- The box queues are busy until about 02:00 to 04:30 UTC with other labs; the run.sh digest job takes about 1 minute at 60 percent quota on box1 (estimate; the C -O0 and Rust -O0 builds dominate), more on box4.

## Fix round 1 (verifier FIX_FIRST, 2026-10-04; runner only, rust/ untouched, 0 fix cycles)
- Code commit with the runner fixes: f90658cff611da2eb40fb8b96feeb5cc0a8d192d (on top of 4a41cbb; git diff 4a41cbb..HEAD under rust-lab/rust-2a/rust is empty). The initial-attempt tree for the label stays 4a41cbb (rust/ identical); run.sh sha256 now d68d980e85102e33095b25bb4e6e9097b4a0d61284306f0ad95444f57ddc1346. Payload hash: PAYLOAD_SHA256 file sha256 0b5e0947ec28e963c828ecae8d6fc4b688037993dbb690c44f8ddf412fc0d92c (payload bin hashes unchanged).
- Blocker 1 (valid, fixed): --check-gen is now passed only in digest mode. Timing mode passes only --init/--init-sha/--batch/--batch-sha. The two input SHA-256 gates stay in timing mode (about 78 KB hashed per run, well under a millisecond on box1, a few ms on the Celeron/Sempron/Pentium); they stay because the bar makes a differing init or batch hash INVALID. This residual cost to Rust is reported here as a known small asymmetry in measurement (b).
- Blocker 2 (valid, fixed): digest mode now prints "RESULT: FAIL ... invalid=binary_did_not_start_or_finish not_started=[builds] not_finished=[runs with rc!=0 or no 4 digests]" when any Rust build did not start or any run exited nonzero (incl. OOM kill, hash-gate exit 4) or printed no 4 digests; equal=no with RESULT: OK is printed only when every run finished and a digest differed. Timing mode: a row with rc!=0 is valid=NO; final line is RESULT: OK only if rows=5 x reps, no valid=NO and no equal_ref=no; otherwise PARTIAL with valid_NO_rows= and rows_equal_ref_no=. Stub plumbing test (shell stubs, not results, deleted) showed FAIL with rc=9 build named and PARTIAL with valid_NO_rows=1.
- Blocker 3 (valid in part): free -m total on box4 = 3669 MB, 80 percent = 2935, wrapper value 2900M is within the bar. box5 total = 1964 MB, 80 percent = 1571, wrapper value 1500M is within the bar (a little under). box1/2/3 values 4500M/2800M/2800M match. Digest jobs run at 500M on all hosts (stricter than the bar, which names timing limits); wrappers not changed. Needed amend-bar sentence (record, not easier): "Digest jobs (not timing) run under MemoryMax 500M on every host; an out-of-memory kill is INVALID (binary did not finish)." Orchestrator to include it in the pins amend-bar.
- Stub outputs under ~/scratch-rust (stub/, stub2/) deleted; tV deleted. Not run: any Rust training, any Rust-vs-C comparison.
