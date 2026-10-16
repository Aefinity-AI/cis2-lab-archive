# rust-2a RESULT (assembled 2026-10-04 about 05:15Z from raw files; not recorded in the ledger)

Scale: 13,088 parameters, 200 SGD steps, byte MLP. Nothing here transfers to 135M to 360M models trained on a GPU, to PyTorch, or to training speed at any real size. A Rust-trained model of real size does not exist and is untested.

ANSWERS: LANGUAGE (port fidelity). Bar: state/plans/rust-lab/bars/rust-2a.txt. It does not answer FRAMEWORK or KERNELS.

## 1. Label rule and evidence

Bar, label rule (quoted): "PORT EQUAL (level with C): in the initial complete attempt, on every host that ran, and for every Rust build tried, all 4 checkpoint SHA-256 digests equal the reference digests (the result also states 0 fix cycles)." and "PORT DIFFERENT (behind C): any digest on any host or build differs IN THE INITIAL COMPLETE ATTEMPT." Every outcome other than PORT EQUAL is PORT DIFFERENT.

Reference digests (16-hex prefixes): step 50 fd64cf9e032ee182, step 100 d36bd7fd164ba774, step 150 3887f7b3f512a6a2, step 200 f665ffecfabba7a4.
- Set 1: state/reports/2026-09-24-cap1c-c-trainer-cross-isa.md lines 74-77 (full values equal ~/feed-payload/rust2a/REF_DIGESTS.txt, read here).
- Set 2: C original rebuilt and run in the same session on penguin: orig -O0, orig -O2, patched -O0, patched -O2 all give the same 4 digests (penguin/RESULT.txt, penguin raw run dirs, BUILD.md). The two sets agree. Reference not broken.

Digest table, host x build. Every cell below = the 4 reference prefixes in order (fd64cf9e032ee182 d36bd7fd164ba774 3887f7b3f512a6a2 f665ffecfabba7a4); "ref" means all 4 equal; no cell differs.

| host | rust gnu-O0 | rust gnu-O3 | rust musl-O0 | rust musl-O3 | C orig-O0 | C orig-O2 | C patched-O0 | C patched-O2 | evidence |
|---|---|---|---|---|---|---|---|---|---|
| penguin | ref | ref | ref | ref | ref | ref | ref | ref | raw ckpt files intact in ~/feed-payload/rust2a/out/penguin (8 builds, sha256sum recomputed in the harvest and again by the verifier); the report folder penguin/ holds RESULT.txt and run.log only |
| box1 | ref | ref | ref (RESULT line alone) | ref | ref (RESULT line alone) | ref (RESULT line alone) | ref | ref | see note A |
| box2 | ref | ref | ref | ref | ref | ref | ref | ref | raw files kept: box2/digest (checkpoint sha256 list in box2/digest_ckpt_sha256_full.txt, box2/ckpt_sha256_prefixes.txt; ckpt .bin files themselves not copied) |
| box3 | ref | ref | ref (RESULT line alone) | ref | ref (RESULT line alone) | ref (RESULT line alone) | ref | ref | note A |
| box4 | ref | ref | ref (RESULT line alone) | ref | ref (RESULT line alone) | ref (RESULT line alone) | ref | ref | note A |
| box5 | ref | ref | ref (RESULT line alone) | ref | ref (RESULT line alone) | ref (RESULT line alone) | ref | ref | note A |

Note A (box1, box3, box4, box5): run.sh does `rm -rf $OUT` at start and digest and timing mode share out/<host>, so each host's timing job overwrote its digest-job raw files. What survives on those four hosts: the timing job's 5 arms (C patched O0/O2, Rust gnu O3/O0, musl O3), 4 checkpoint files each, recomputed sha256 in boxN/raw_runs_after_timing.txt = reference; and the digest job's own RESULT line with the full 64-hex digests and PER_BUILD all 8 builds = yes (boxN/RESULT_digest.txt, state/feed/cm-boxN/done/rust2a-digest-boxN/RESULT.txt). For rust-musl-O0 and C orig-O0 / orig-O2 on those four hosts there is no surviving raw checkpoint file; the evidence is the RESULT line alone. Box2 is the exception: its digest raw folder was preserved (<home>/rust2a/out-digest-box2) and copied.

Initial complete attempt: commit 4a41cbb91fbb5fcb188599b549d234458179f173 (alice-model, branch cm/rust-lab, worktree ~/projects/alice-model-cm-rust-lab; BUILD.md and STARTED.md). Penguin run of that tree, 2026-10-04 01:11Z: RESULT OK equal=yes, 8 builds, GEN_CHECK equal.
Fix cycles before it matched: 0. Sources: BUILD.md ("Fix round 1 ... rust/ untouched, 0 fix cycles"); `git log` of the worktree for rust-lab/rust-2a shows two commits, 4a41cbb (port, runner, payload scripts) and f90658c (runner fixes, no change under rust/: no --check-gen in timing mode, FAIL on unfinished runs, PARTIAL timing status); `git log 4a41cbb..HEAD -- rust-lab/rust-2a/rust` prints nothing, so rust/ is identical at f90658c. The runner fixes came from a verifier round before start, after the penguin run was planned but not a change to the Rust port.
Phone: NOT RUN (no aarch64 musl build made).

Label per the bar: PORT EQUAL (every host that ran: penguin, box1, box2, box3, box4, box5; every Rust build tried: gnu-O0, gnu-O3, musl-O0, musl-O3; 0 fix cycles), subject to section 2.

Trust column: dependency count 0 beyond std (Cargo.lock has 1 package, rust2a itself; C = libc); Rust builds byte-identically twice on penguin = yes (BUILD.md BUILD-TWICE = yes; I did not rebuild); build-and-compare cycles to initial full match = 1 (the initial attempt matched).

## 2. INVALID conditions, one by one

1. init or batch-order sha256 differs between arms: not triggered. init 3a1b88b2cb90bb0f81cfca4221986f5a6ba28ef267fa01a662881653a16aeb7b, batch f5e254381cc9c6db7f5f71f04ef93b772441e7fad926a65b70db76cc1c96b21e. Every run.log (penguin, box1, box2 digest and timing, box3, box4, box5) prints these same two values on the "init_sha256= batch_sha256=" line; the Rust binary takes both on the command line and exits 4 before training if either differs (INPUTS_OK in box2 run-rust-*/stderr for all 4 Rust builds; GEN_CHECK init=equal batch=equal also printed). The C arms (patched) wrote them once; the C trainer reads its own init. Satisfied.
2. reference digests disagree: not triggered (section 1, two sets agree).
3. build-flag difference not recorded: satisfied. C flags recorded in every run.log "C build ..." line, identical on all six hosts: `gcc -O{0,2} -ffp-contract=off -fno-fast-math -fexcess-precision=standard -std=c11 -Wall -Wextra -mno-fma -lm` (gcc 14.2.0-19 on all). Rust: rustc 1.98.0 / LLVM 22.1.8, RUSTFLAGS unset (default x86-64), profiles release (opt 3, lto fat, cgu 1, panic abort) and o0, `--locked --offline`, recorded in payload/bin/BUILD_ENV.txt and BUILD.md; 4 Rust binary sha256 in bin/SHA256SUMS (re-checked here with sha256sum -c: 4 OK). Caveat: the C trainer rebuilds on each host while Rust binaries are one prebuilt set; C binary sha256 recorded in each run.log. The bar says compiler versions and exact flags were "not fixed" before start; the amend (pins) is in STARTED.md.
4. Rust port links code calling platform exp/ln/pow: checked here on penguin against the payload binaries. `nm` over all four binaries: 0 symbols named exp, expf, exp2, log, logf, log2, pow, powf, tanh, tanhf (902 symbols in musl-O3, 669 in gnu-O3); undefined symbols of the gnu build are libc and unwind runtime (malloc, memcpy, clock_gettime, fstat64, ...; no libm); `ldd`: gnu builds link libgcc_s and libc (no libm), musl builds are statically linked. Source check: grep of rust/src for powf / .exp( / .ln( / .tanh / mul_add / extern "C" finds a comment alone ("No std exp, ln or powf; no mul_add"). `objdump -d` of all four: 0 FMA instructions. Also, 9,000 test vectors for exp/ln/tanh bit-exact against C (BUILD.md; not re-run here). Satisfied. Limit: symbol and source checks, not a taint analysis of every instruction path.
5. digest run on a host where the binary did not finish: not triggered. Every RESULT_digest line is RESULT: OK with all 8 PER_BUILD yes; no FAIL, rc!=0 or OOM on any host. Box2: 8 RUN lines rc=0.

Not clearly satisfied (not INVALID items, bar text on measurement): see section 3, host-idle wording.

## 3. MEASUREMENT (wall time, no bar; expected 0.8 to 1.25 for Rust/C in-process)

Source: timing_rows.txt per host (box2: box2/timing/timing_rows.txt). 5 reps, arm order rotated, every row equal_ref=yes. Seconds. "in" = in-process wall of the 200 steps (monotonic clock inside the program), "whole" = whole-process wall including start, file reads, 4 checkpoint hashes. Rep values listed in rep order 0..4.

box1 (Core i5-5200U; the host that counts):
| arm | in median | in reps | whole median | whole reps |
|---|---|---|---|---|
| C patched -O2 | 0.2669 | 0.268603 0.266917 0.265606 0.270852 0.266364 | 0.2711 | 0.2728 0.2711 0.2699 0.2752 0.2708 |
| C patched -O0 | 2.0576 | 2.051638 2.057633 2.062409 2.065568 2.019195 | 2.0620 | 2.0560 2.0620 2.0668 2.0699 2.0236 |
| Rust gnu O3 | 0.4136 | 0.410393 0.417925 0.435911 0.413507 0.413554 | 0.4168 | 0.4136 0.4212 0.4392 0.4168 0.4168 |
| Rust gnu O0 | 7.6141 | 7.614139 7.594093 7.925919 7.617919 7.606569 | 7.6228 | 7.6228 7.6023 7.9413 7.6262 7.6149 |
| Rust musl O3 | 0.4168 | 0.419163 0.417267 0.416753 0.416483 0.416537 | 0.4195 | 0.4218 0.4200 0.4195 0.4193 0.4193 |

Informal hosts (Rule A; medians, in / whole; reps in the timing_rows.txt files named above):
| host | C O2 | C O0 | Rust gnu O3 | Rust gnu O0 | Rust musl O3 |
|---|---|---|---|---|---|
| box2 | 0.4757 / 0.4804 | 2.2562 / 2.2639 | 0.5597 / 0.5634 | 8.8572 / 8.8672 | 0.5605 / 0.5636 |
| box3 | 0.3214 / 0.3259 | 2.1429 / 2.1486 | 0.4559 / 0.4611 | 8.7825 / 8.7923 | 0.4642 / 0.4685 |
| box4 | 0.7193 / 0.7287 | 5.3604 / 5.3701 | 0.9409 / 0.9479 | 20.5776 / 20.5978 | 0.9409 / 0.9471 |
| box5 | 0.6590 / 0.6695 | 4.0177 / 4.0281 | 0.9311 / 0.9391 | 15.0165 / 15.0355 | 0.9374 / 0.9440 |
Rep values on the informal hosts, in-process: box2 C O2 0.320382 0.479075 0.478911 0.475653 0.475123; C O0 2.159018 2.244904 2.259385 2.256184 2.259599; gnu O3 0.455961 0.559564 0.559813 0.560501 0.559728; gnu O0 8.765383 8.860947 8.853698 8.857185 8.872540; musl O3 0.462015 0.559125 0.563079 0.560456 0.564286. box3 gnu O0 8.782496 8.732006 9.110984 9.463002 8.730124. box4 gnu O0 21.094207 13.444745 20.577597 13.612113 20.886132 (bimodal, unexplained); box4 gnu O3 1.083056 0.945551 0.940923 0.937368 0.939709. Full values for all arms in each host's timing_rows.txt. Box2 rep 0 is about 30 percent faster than reps 1 to 4 on every arm (e.g. C O2 0.3204 vs 0.4751 to 0.4791); cause not determined (box2 MHz 2687 to 2774 and throttle counters 0 in all SNAP lines).

Ratio the bar defines: Rust wall over C wall, in-process (a) expected 0.8 to 1.25; outside is written SURPRISE. The bar does not name which Rust build is paired with which C build; I give the opt-matched pairs the bar's build list implies (Rust opt-level 3 vs C -O2, Rust opt-level 0 vs C -O0). Median-over-median, box1:
- in-process (a): Rust gnu O3 / C O2 = 0.4136/0.2669 = 1.549; Rust musl O3 / C O2 = 0.4168/0.2669 = 1.561; Rust gnu O0 / C O0 = 7.6141/2.0576 = 3.700.
- whole-process (b): gnu O3 / C O2 = 1.537; musl O3 / C O2 = 1.547; gnu O0 / C O0 = 3.697.
SURPRISE flag: applies. The bar's rule is "A ratio outside 0.8 to 1.25 in (a) is written as SURPRISE"; 1.549 and 1.561 (O3 vs O2) and 3.700 (O0 vs O0) are all above 1.25. Under every pairing of a Rust arm with a C arm in this table, (a) is outside the range. It changes no label. The bar's (b) expectation was "the two programs look alike"; they do not on box1 (ratios 1.54 to 3.70). Cause not examined in this lab; no explanation is offered.
Informal hosts, (a) Rust musl O3 / C O2 and Rust gnu O0 / C O0: box2 1.178 / 3.926; box3 1.444 / 4.098; box4 1.308 / 3.839; box5 1.422 / 3.738. On box2 both O3 pairings are under 1.25 (musl-O3 / C-O2 1.178, gnu-O3 / C-O2 1.177); box2 O0 / O0 is 3.926. Every pairing on box3, box4 and box5 is above 1.25. Informal per Rule A.

Did the box1 job meet the BOXES.md ruling (2026-10-04 00:40Z: no CPUQuota, idle host, load/MHz/throttle recorded before and after every repetition, clamp or throttle rep discarded and repeated, opening timing job is the check)?
- Quota: job.json (state/feed/cm-box1/done/rust2a-timing-box1/job.json) has cpu_quota "400%", memory_max 4500M; box1 is 2 cores / 4 threads, so 400% is the whole machine, nominally no cap; the job log says "quota_note=run with no CPUQuota on an idle host". It is not literally "no CPUQuota"; I did not verify the effective cgroup value on the box (no further box1 call, split test running). Pushed 2026-10-04T02:08:59Z.
- Throttle: all 53 SNAP lines in run.log, per-core throttle counters 0 0 0 0 0 0 0 0 before and after every rep; MHz 2095 on all 4 cores in every SNAP (cpuinfo_max_mhz 2100); no throttle or MHz discard.
- Load: start-gate load = 0.18 0.44 0.91 (below 0.3 on the 1-minute figure). Per-rep SNAP 1-minute loads range 0.18 to 0.68, and 45 of the 53 SNAP lines are 0.3 or higher; the job's own runs raise the load average. The bar's "load below 0.3 before and after" is met at the start gate and not on each repetition's reading. Pin P7 of the amended bar says the idle gate is a load below 0.3 at job start only, and that per-rep checks are the SNAP lines and the other-runnable test, so this is as registered; the bar's INVALID list has no timing item and the runner's own idle check (other runnable tasks) is what discarded reps.
- Discards: 1 (rep 4 rust-gnu-O0, other_runnable_before=1, repeated; the kept try 2 equals the discarded try within 0.2 percent). 0 valid=NO rows. RESULT: OK rows=25.

Flagged rows (informal hosts): box3 rep 3 rust-musl-O3 valid=NO other_runnable_before=1 tries=4 (in-process 0.462264; 5 DISCARDs on box3 in total); box4 rep 2 c-patched-O2 valid=NO other_runnable_before=2 tries=4 (in-process 0.745727; 27 DISCARDs on box4, a 1-core host). Both rows equal the reference digests. The "other runnable" check is a single sampled read of /proc/loadavg and has a measured false-positive floor (HARVEST-2026-10-04.md section (b)), so a flag is not shown to be a real competing task. Box2: 0 DISCARDs, 0 valid=NO, RESULT OK rows=25. Box5: 1 DISCARD, 0 valid=NO. Box3/box4 FEED.json records status 'fail' for the PARTIAL jobs although all rows finished and equal the reference.

## 4. Sentence the bar prescribes (outcome PORT EQUAL, 0 fix cycles)

"LANGUAGE (port fidelity, 13,088-parameter byte MLP, 200 steps): the Rust port reproduces the C trainer's 4 checkpoint digests on penguin, box1, box2, box3, box4, box5 with Rust opt-level 0 and 3 (gnu and musl targets), in its initial complete attempt (0 fix cycles). Nothing follows for 135M to 360M models, for training speed, or for PyTorch."

Wall line: "Measurement only (box1 counts; other hosts informal per Rule A): in-process wall Rust/C = 1.549 (gnu O3 vs C O2; musl O3 1.561; opt-level 0 vs -O0 3.700) on box1, whole-process wall Rust/C = 1.537 (gnu O3 vs C O2; musl O3 1.547; O0 vs O0 3.697); expected 0.8 to 1.25 (SURPRISE)."

## 5. Disclosures and what this does not show

- Scale: 13,088 parameters, 200 SGD steps, byte MLP. Nothing here transfers to 135M to 360M models trained on a GPU, to PyTorch, or to training speed at any real size. A Rust-trained model of real size does not exist and is untested.
- The builder knew the target digests. Pre-start tests (cargo test) covered sha256, exp/ln/tanh against C, the forward pass for batch position 0; the backward pass and SGD update were not tested before the penguin run. The label rests on the initial attempt matching with 0 fix cycles.
- The training arithmetic is the quantity under test: init weights and batch order are exported from the C trainer and read by the Rust port (hash-gated). The Rust init generator match (GEN_CHECK equal) is an extra with no label.
- Same x86-64 family on all hosts (no AVX2/FMA on box2/box4/box5; all builds avoid FMA). No aarch64 host: phone NOT RUN. Cross-ISA is not shown here.
- Raw digest files on box1, box3, box4, box5 were overwritten by their timing jobs (run.sh defect); three builds per host rest on the RESULT line alone. Box2 raw digest files preserved.
- The box1 job's quota was nominal 400% on a 4-thread host and per-rep load readings are 0.3 or higher (section 3); the ratio is a measurement under those conditions, 5 reps, one machine. The timing arms compare Rust opt-level 3 (lto fat) with C -O2, a pairing choice of this report. The cause of the ratios is not examined.
- The Rust binaries include two sha256 input-hash gates in timing mode (about 78 KB hashed per run; BUILD.md notes this small asymmetry); the in-process wall is not affected by it.
- box4 Rust gnu-O0 wall is bimodal (13 vs 21 s); unexplained. Box2 rep 0 faster than later reps; unexplained.
- Files: box2 raw copies in box2/digest and box2/timing (checkpoint .bin files not copied; sha256 lists kept).

## Verifier pass (2026-10-04)

CONFIRMED met (PORT EQUAL). The verifier re-ran the payload on penguin (all 8 builds, 32 checkpoint files, same 4 digests), re-hashed box2's preserved digest files, checked that no Rust checkpoint or build existed before commit 4a41cbb (no sign of iterate-until-match), ran nm, ldd, objdump and strings on the four Rust binaries (no exp, log, pow or tanh symbols, no libm, no FMA), and recomputed the box1 medians and ratios. Corrections applied above: the box2 ratio sentence, the location of penguin's raw files, the P7 citation. Further disclosures: the builder knew the target digests and the backward pass had no pre-start test; a read of box1 after the run showed turbo disabled (no_turbo=1, max 2100 MHz, governor performance), and it is not known whether that was so during the run; the Rust in-process timing follows two input hash gates of about 78 KB; pairings are opt-matched, a choice of this report; box4 gnu-O0 is bimodal and box2 rep 0 is faster, both unexplained.
