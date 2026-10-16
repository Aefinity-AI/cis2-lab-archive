# rust-4b FREEZE (2026-10-05, revision 4 after pre-registration read R3 (selftest only), revision 3 after read R2 (revision 2 after read R1); builder; nothing registered, queued, started or run on any box; penguin smoke only, every timing value masked)

This file is the freeze record of lab rust-4b (cold start, per-file residency check). Its own sha256 goes into the --ref of the start record (bin/cm-exp start rust-4b --ref cm/rust-lab@b237f4d19989f6dbfa7cc90570ca4ed58fe8b89c freeze=<sha256 of this file>) and the file is not edited after that sha256 is taken. Every hash below was computed on penguin on 2026-10-05 from the file on disk named.

## 1. Sources and code
- Repo: private alice-model, branch cm/rust-lab, worktree ~/projects/alice-model-cm-rust-lab, folder rust-lab/rust4b/, commit b237f4d19989f6dbfa7cc90570ca4ed58fe8b89c (not pushed; revision 4 changed selftest.py only; its parent is revision 3 commit c340f1a0d927ee2cbeba4f63b4c207f7a74e0949). Parent commits: 1cdedca (rust-1b stage 2), 90b817233b1c628241dcb32b947687758210d292 (revision 1) and 79099130fce2cef959534dba82fe6bc9cd5e843e (revision 2); both superseded by this commit, their run.py, payload list and wrappers had other hashes.
- REVISION 2 (2026-10-05, after the pre-registration reads R1 of the design and the code lens; before any run): changed files run.py (the sudo probe is `sudo -n sh -c true`, the same shape as the drop command; the reasons of NOT RUN INVALID name "or the file cannot be cold (tmpfs, mapped by another process)"; nothing else), selftest.py (tests added), summ.py (ledger words, held/SURPRISE/NOT TESTED, not-slower stack sentence, banner for unlabelled hosts), smoke.sh (header comment corrected), smoke_batch.sh (expected-RESULT table), the six wrappers (regenerated with the new frozen runner and payload-list hashes) and PAYLOAD_SHA256 in the payload. UNCHANGED: filelists.json, resident.c, the helper binary, every program, input and order design, make_payload.sh, make_wrappers.sh. Tests of revision 2 on penguin: selftest 82 passed, 0 failed; smoke batch of 9 scenarios (full, order, notcold3, warmfail, coldctl3, warmfinal, cap, nostack, nosudo) every RESULT word equal to its expected word, "SMOKE ASSERT PASS"; wrapper_test.sh 7 cases as designed; the 22 mutants of the verifier (mk.py) all give SELFTEST FAIL for c1-c4, d, d2, d3, d4, d5, e1, e2, e3, g, h, a, a2, b, b2 (e4, f, i, j are not caught by the selftest; in the smoke runs of the verifier each changed a RESULT word, which the smoke table now asserts; not re-run as mutants).
- REVISION 3 (2026-10-05, after the pre-registration reads R2 of the design and the code lens; before any run): changed files run.py (helper_check reads the empty count; a listed non-regular file, and on a frozen list an empty file, is NOT COLD; a real host accepts R4B_REPS 5 or 10 only, else FAIL with nothing timed; the row check record carries nonregular and empty), selftest.py (95 checks), smoke_batch.sh (asserts the arm_status of the order scenario), make_wrappers.sh (box1 and redo10 wrappers run the runner as a child and pass TERM on), wrapper_test.sh (case 3b), the six wrappers (regenerated with the new frozen hashes), the repo copies of the wrappers and PAYLOAD_SHA256 in the payload (only the run.py line changed). UNCHANGED: filelists.json, resident.c, the helper binary, every program, input and order design, make_payload.sh, smoke.sh, summ.py, estimate.py. The pass mark text was revised (see its REVISION 3 sentence). Tests of revision 3 on penguin: selftest 95 passed, 0 failed; smoke batch of 9 scenarios every RESULT word as expected plus the order arm_status, "SMOKE ASSERT PASS"; wrapper_test.sh 8 cases; mutant e4 caught.
- Source files (sha256, file on disk in the folder above):
  - 337a6e17b360991b2da0d2d7cc81538bc92e97d83a1cd6f1c2515a8f15a31373  run.py
  - f29225a8d994d1b5edbbd446d55792f8513c092a829521ba0c1ef43f9b465ed2  filelists.json
  - 889ae49094df3d5994362dcf5f5f8d4b142ad73372896d3eaff07ab294b02a1b  resident.c
  - 50b09f4f4c7515dc203666b14431ea60491a8273d971fc562d5e0eaccacad318  build_helper.sh
  - f8471f3ed68b5d5546367e24598eea86c3ad76ca2b48d2780758402915a7ebc7  make_payload.sh
  - ecd763db7cb9eae7998fe0d7325c03b8d484d8798a11baac432c17e897efa076  make_wrappers.sh
  - f51f8abe49581b677345d1f976fa1754c8bfa5115617ad26cf4de579ea686778  make_order_odd.py
  - d802ad824c52a3260d10420b15303d7155e782422ee443a9e73c11f4cfc5aff8  make_order4b.py
  - 451714831bf9f7c7acc1dd8532f158aa3f2b0a96f77a59948b6fdaa2a5dc5e76  selftest.py
  - e1a41b87944d06d9c85c83a57bb59045e1e13cd5b381be0d4021aa782165ee52  summ.py
  - 900c196ad8d82a29cee2f8e6d882b0aefa5cc9eef72624691159c029229d802b  smoke.sh
  - 51f42eef42a5a77b09645ce80d233869ada108680c7daeeac0dcc5019280d4a0  smoke_batch.sh
  - e120a3899d89939f80133ab8d270a052d5328d2c34e79fd3b9c2382591ff2202  wrapper_test.sh
  - 29baaeb3e08f8bc76a0251944930e0fb00da60cd6c9b3d20920a0b3ba39b0555  trace_opens.c
  - 6cee63b670556987e3280f254f9f8700214e94a9218a18d085545fa670172b4d  trace_run.sh
  - ae3d3a658fda80137b86bc785c2ded28550b2afc84d35a1549c3b0630fd12ea9  estimate.py
  - b3e4a4ff08eef607ab3f4846e857fac1568e8cc056c54f178336ad74642f9b07  p/pstart.py
  - 6929910c32df2897bf16487dd95d2c19df364147d050fbc49e769511a5fb37fd  p/requirements.lock
  - 160db7d26ed93111f2cc174c2ee38548bf68fd4ae266223c6fda8396008602f4  p/WHEELHOUSE_SHA256
  - 7323b9818e6819f332a9b865a47d946842028ce0b2e257023bfa3b4a44d75f7d  inputs/work_cold.jsonl
  - d27650ed0f22126fd1c7c3ee4d862a7a1abc461884bcf56dd969d538c3d17144  inputs/REF_COLD_WITNESS.txt
- Runner: run.py sha256 337a6e17b360991b2da0d2d7cc81538bc92e97d83a1cd6f1c2515a8f15a31373 (the payload copy is the same file, cmp equal). Pins carried by the runner: weights, config and tokenizer sha256, GGUF sha256, constants of the hygiene (6 windows of 20 s, margins 2 points and 0.05 CPU, floors 2 percent and 0.10 CPU, baseline ceilings 15 percent and 0.30 CPU, budgets 6 discards and 8 voids), cold check constants (3 not-cold in a row, warm control 90 percent, cold control 3 tries), CAP_S 5400.

## 2. Programs (nothing rebuilt)
- R = cis2_ref, sha256 d0f8ec89e4f63c6ed37fb6d5416662e3b56e740b202126d8f8637cb5cb6e6503; C = verify3 sv5_driver, sha256 5a6ccc32ec04ca14d831f6b508bb69822ea51c6f16b7305f601dd87a056e1fd8. Both copied byte for byte from ~/feed-payload/rust4/bin to ~/feed-payload/rust4b/bin by make_payload.sh; the copies are compared with cmp (exit 0) and the sha256 of source and copy is shown equal in the make_payload.sh output (four "sha256 equal" lines). The rust-4 pass mark pins the same two values.
- Q (llama.cpp F32, the frozen rust-1b payload): llama-drv-avx2 sha256 4999a4da5a1116aa282480376fa483ee9675ae7d442b388ba838192d03b315b3, llama-drv-sse42 sha256 5441f651b61d713287afa35b2552afc7569a5ef16b56fc1e07a3ffae978aec85, gguf/model-f32.gguf sha256 8de5be7131bd2250d2631bf6b84b37a654511ce339a25df0e299082579fbf3bc (539,845,056 bytes); equal to rust-1b FREEZE-STAGE2.md section 4. The driver is unchanged (no source change): on penguin `llama-drv-avx2 --plain time --model model-f32.gguf --prompts work_cold.jsonl --n-gen 1 --threads 1 --print-ns 0` printed `LOAD load_ns=NA load=mmap`, `ROW idx=0 n_prompt=39 n_gen=1 prefill_ns=NA decode_ns=NA mismatches=0`, `DONE plain=time rows=1` and the INFO line (system_info CPU SSE3 SSSE3 AVX AVX2 F16C FMA BMI2 LLAMAFILE REPACK, n_vocab 49152, load_mode=mmap, flash_attn_type=-1, threads=1) with exit 0, so Q is built (D5). The check mode (`--plain check`, used for the untimed probe) printed `CHECK idx=0 witness=c7b509af... mismatches=0`. The largest logit difference of Q (0.072, rust-1b) is not measured in this lab.
- Weights (on every box, not shipped): model.safetensors 80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1 (269,060,552 bytes = 65,689 pages of 4,096 bytes), config.json 1d556eab73b69c7f11f64c557a2f9c6f440bd4c6b89bb2584a6b498c92603843, tokenizer.json 9ca9acddb6525a194ec8ac7a87f24fbba7232a9a15ffa1af0c1224fcd888e47c.
- Wheelhouse (P): the 34 wheels of rust-4 copied (cp -r) from ~/feed-payload/rust4/p/wheelhouse; wheelhouse list sha256 21360ef99c777608fc5e0b3e13bf8d898cbfad6970b11701c36f80ee390e738e recomputed by make_payload.sh and by the runner on every host (equal to p/WHEELHOUSE_SHA256 and to rust-4); p/requirements.lock 6929910c32df2897bf16487dd95d2c19df364147d050fbc49e769511a5fb37fd; p/pstart.py b3e4a4ff08eef607ab3f4846e857fac1568e8cc056c54f178336ad74642f9b07 (rust-4's, unchanged). The venv is made with `python3 -m venv --copies` (the only change of the P install): on penguin the venv python is a regular file of its own (6,828,688 bytes), the venv holds 29,942 regular files (venv list sha256 32d560b025dc4660dcb8640be15628460a0dddbaa3a638f2b28cfbc45cb96069, sorted relative paths, penguin, informational).

## 3. The residency helper
- Source resident.c sha256 889ae49094df3d5994362dcf5f5f8d4b142ad73372896d3eaff07ab294b02a1b; build script build_helper.sh sha256 50b09f4f4c7515dc203666b14431ea60491a8273d971fc562d5e0eaccacad318.
- Build (penguin, 2026-10-05): musl-gcc (musl-tools 1.2.5-3.1~deb13u1 on gcc 14.2.0-19) `-O2 -std=gnu11 -Wall -Wextra -Werror -static -s -Wl,--build-id=none -ffile-prefix-map=<dir>=/src`, SOURCE_DATE_EPOCH=1759536000; built twice and the two outputs compared (cmp equal) before the name is taken. Binary bin/rust4b_resident sha256 a08c989bf4855064b911b1bbf3e361900030d4bbc8d71700bf5ee7aca3876812, 51,048 bytes, ELF 64-bit x86-64 statically linked stripped.
- What it does: for each path (arguments or a list on stdin): open read-only, fstat; a regular file of size above 0 is mmap'ed read-only (MAP_SHARED) and mincore() counts its resident pages; prints `F <resident> <total> <bytes> <path>` for files with resident pages, `E <errno> <path>` for a path it cannot open, map or query, `N <path>` for a non-regular file, and one `SUM files= regular= empty= nonregular= resident_pages= total_pages= errors= page_size=` line. It reads and modifies no file. Tested on penguin: a resident file counts all its pages, an empty file, a directory and a missing file are counted as such, and after fsync plus posix_fadvise DONTNEED of the file the helper reports 0 resident pages (selftest, "real helper" checks).

## 4. File lists per arm (frozen: filelists.json sha256 f29225a8d994d1b5edbbd446d55792f8513c092a829521ba0c1ef43f9b465ed2), with the trace evidence
Templates: {BIN} payload bin, {IN} payload inputs, {GG} payload gguf, {WD} weights dir (~/sv5/arma/weights), {W} payload dir, {VENV} the job's venv, {QBIN} llama-drv-avx2 on a host with the avx2 flag else llama-drv-sse42.
- R: {BIN}/R_cis2_ref, {IN}/work_cold.jsonl, {WD}/config.json, {WD}/model.safetensors
- C: {BIN}/C_sv5_driver, {IN}/work_cold.jsonl, {WD}/config.json, {WD}/model.safetensors
- Rv: R's list + {WD}/tokenizer.json;  Cv: C's list + {WD}/tokenizer.json   (the check mode opens the tokenizer; the trace shows it)
- Q: {QBIN}, {GG}/model-f32.gguf, {IN}/work_cold.jsonl
- P: {W}/p/pstart.py, {IN}/work_cold.jsonl, {WD}/config.json, {WD}/model.safetensors, and EVERY regular file under {VENV} (the walk is made at check time: files only, symlinks and directories left out, the python executable among them); pages are summed over all of them. The design names the python executable, the venv files and the weights file; the list here also holds pstart.py, work_cold.jsonl and config.json, which the trace shows P opens: a stricter list, never a weaker one.
- Not listed (named here, as the pass mark says): files of the base system that a program opens, not checked (REVISION 2: the earlier reason "they are mapped all the time and cannot be cold" was wrong; see the note at the end of this section): for Q /etc/ld.so.cache, libstdc++.so.6, libm.so.6, libgcc_s.so.1, libc.so.6 under /lib/x86_64-linux-gnu; for P the same libraries plus libbz2, libcrypto, libdl, libexpat, libffi, liblzma, libpthread, librt, libsqlite3, libssl, libuuid, libz, libzstd, /usr/lib/python3.13 (243 files), /etc/localtime, locale files, openssl.cnf, gconv cache, python's own temporary files under /tmp; for R and C (static musl) nothing. Files under /proc, /sys and /dev are not page-cache files.

- NOTE (revision 2): the sentence of the pass mark (COLD) supersedes the "not_listed" note of filelists.json (a PIN, untouched) and the wording of the bullet above. The drop is system-wide: measured on penguin, only 5 of about 800 files under /usr/lib/python3.13 are mapped by any process (the .py and .pyc files are read, not mapped), and drop_caches=3 also drops unreferenced directory entries and inodes. So after each drop P reads its standard library and its unlisted shared libraries from disk, unchecked, while the static R and C open no such file; this is part of what the P row measures.

Trace tool. strace is not installed on penguin (no network, no sudo), so the trace was made with trace_opens.c (sha256 29baaeb3e08f8bc76a0251944930e0fb00da60cd6c9b3d20920a0b3ba39b0555), a small ptrace tracer that follows the child and every thread and process it creates and prints one line per open, openat, openat2 and execve (x86_64), with the return value; recipe trace_run.sh (sha256 6cee63b670556987e3280f254f9f8700214e94a9218a18d085545fa670172b4d). The programs ran on penguin only to make these traces, with the binaries and weights named; no timing was taken. The raw traces are in state/reports/rust-lab/rust-4b/trace/ (R.opens ... P.opens; each line `<tid> <syscall> <return value, negative = failed> <flags hex> <path>`). The binaries traced are the rust-4 payload copies of R and C (the same bytes as in the rust-4b payload) and the rust-1b llama-drv-avx2; the paths in the traces are those on penguin.

R trace (trace/R.opens sha256 b972758788e9dd265e3cbd2b11ab82d310a4a8d195e1ad2fd1ac3211305089cc); the program printed LOAD, ROW (mismatches=0) and DONE, exit 0:
    1493196 execve 0 0 <home>/feed-payload/rust4/bin/R_cis2_ref
    1493196 open 4 88000 <home>/sv5/arma/weights/config.json
    1493196 open 4 88000 <home>/sv5/arma/weights/model.safetensors
    1493196 open 4 88000 <home>/feed-payload/rust4/inputs/work_cold.jsonl

C trace (trace/C.opens sha256 d87a0c543072677aed8a776bf5f383765bdece883e1b13b51f855ca96843191a):
    1493219 execve 0 0 <home>/feed-payload/rust4/bin/C_sv5_driver
    1493219 open 4 8000 <home>/feed-payload/rust4/inputs/work_cold.jsonl
    1493219 open 4 8000 <home>/sv5/arma/weights/config.json
    1493219 open 4 8000 <home>/sv5/arma/weights/model.safetensors

Rv trace (check mode; trace/Rv.opens sha256 cef9dbdd450d4f7d7fc172825243c779805ddf5f294d5b5696ad593d40852d5d); printed CHECK with the reference witness ecafd089d17b... and mismatches=0, exit 0:
    1493244 execve 0 0 <home>/feed-payload/rust4/bin/R_cis2_ref
    1493244 open 4 88000 <home>/sv5/arma/weights/model.safetensors
    1493244 open 4 88000 <home>/sv5/arma/weights/tokenizer.json
    1493244 open 4 88000 <home>/sv5/arma/weights/config.json
    1493244 open 4 88000 <home>/sv5/arma/weights/config.json
    1493244 open 4 88000 <home>/sv5/arma/weights/model.safetensors
    1493244 open 4 88000 <home>/feed-payload/rust4/inputs/work_cold.jsonl

Cv trace (check mode; trace/Cv.opens sha256 48b843d45a882f39ea12864a1308ca031d7edcdbf7a604ca246d262cba758b79):
    1493250 execve 0 0 <home>/feed-payload/rust4/bin/C_sv5_driver
    1493250 open 4 8000 <home>/sv5/arma/weights/config.json
    1493250 open 4 8000 <home>/sv5/arma/weights/tokenizer.json
    1493250 open 4 8000 <home>/feed-payload/rust4/inputs/work_cold.jsonl
    1493250 open 4 8000 <home>/sv5/arma/weights/config.json
    1493250 open 4 8000 <home>/sv5/arma/weights/model.safetensors

Q trace (llama-drv-avx2; trace/Q.opens sha256 1195e229318e02fb26928d28ec8207b59e020d3fc24e316e2f9e29d9c849d8a7):
    1493301 execve 0 0 <home>/feed-payload/rust1b/bin/llama-drv-avx2
    1493301 openat 4 80000 /etc/ld.so.cache
    1493301 openat 4 80000 /lib/x86_64-linux-gnu/libstdc++.so.6
    1493301 openat 4 80000 /lib/x86_64-linux-gnu/libm.so.6
    1493301 openat 4 80000 /lib/x86_64-linux-gnu/libgcc_s.so.1
    1493301 openat 4 80000 /lib/x86_64-linux-gnu/libc.so.6
    1493301 openat 4 0 /proc/cpuinfo
    1493301 openat 4 0 <home>/feed-payload/rust1b/gguf/model-f32.gguf
    1493301 openat 4 0 <home>/feed-payload/rust1b/gguf/model-f32.gguf
    1493301 openat 4 0 <home>/feed-payload/rust4/inputs/work_cold.jsonl

P trace (trace/P.opens sha256 972abbec4972594ec1f6672e67940d6001220365bca2794a7ea10a7393fbad85; 11,385 open, openat and execve calls, 84 of them failed (ENOENT probes), 5,438 distinct paths opened successfully: 5,150 under the venv, 12 under /proc, /sys and /dev, 276 elsewhere). Of the 276: 243 under /usr/lib/python3.13 (the standard library), and these 33, none of which is listed except the four marked (L):
    /etc/ld.so.cache  /etc/localtime
    {IN}/work_cold.jsonl (L)  {W}/p (a directory)  {W}/p/pstart.py (L)  {WD}/config.json (L)  {WD}/model.safetensors (L)
    libbz2.so.1.0 libc.so.6 libcrypto.so.3 libdl.so.2 libexpat.so.1 libffi.so.8 libgcc_s.so.1 liblzma.so.5 libm.so.6 libpthread.so.0 librt.so.1 libsqlite3.so.0 libssl.so.3 libstdc++.so.6 libuuid.so.1 libz.so.1 libzstd.so.1 (all /lib/x86_64-linux-gnu)
    /tmp/3gqc3abx  /tmp/tmp4kehk4um  /tmp/tmp4kehk4um/probe-source (python's temporary files)
    /usr/lib/locale/C.utf8/LC_CTYPE  /usr/lib/locale/locale-archive  /usr/lib/ssl/openssl.cnf  /usr/lib/x86_64-linux-gnu/gconv/gconv-modules.cache  /usr/share/locale/locale.alias  venv/bin/python (the executable, relative; under the venv)
  The venv walk lists all 29,942 regular files of the venv (the trace opened 5,150 of them): the strict reading, so that an unopened file that is resident is also a failure.

## 5. Order design (run.py DESIGN; make_order_odd.py for n = 5 and make_order4b.py for n = 4 and 6, fixed seeds 20261004 + n and 20261005 + n)
Rep k uses row (k - 1) mod 5, so the orders repeat in a redo of 10. Position -> arm, arms in canonical order R, C, P, Rv, Cv, Q restricted to the arms that run.
n=4 arms (canonical order R, C, Rv, Cv):
    row 1 (reps 1, 6): R Cv C Rv
    row 2 (reps 2, 7): Rv C Cv R
    row 3 (reps 3, 8): C R Rv Cv
    row 4 (reps 4, 9): Cv C R Rv
    row 5 (reps 5, 10): Rv R Cv C
    position sums per arm over the 5 rows: {'R': 7, 'C': 7, 'Rv': 8, 'Cv': 8} ; mean positions {'R': 1.4, 'C': 1.4, 'Rv': 1.6, 'Cv': 1.6}
n=5 arms (canonical order R, C, P, Rv, Cv):
    row 1 (reps 1, 6): C Rv R Cv P
    row 2 (reps 2, 7): Cv P C Rv R
    row 3 (reps 3, 8): Rv C Cv R P
    row 4 (reps 4, 9): R P Rv Cv C
    row 5 (reps 5, 10): P R Cv C Rv
    position sums per arm over the 5 rows: {'R': 10, 'C': 10, 'P': 10, 'Rv': 10, 'Cv': 10} ; mean positions {'R': 2.0, 'C': 2.0, 'P': 2.0, 'Rv': 2.0, 'Cv': 2.0}
n=6 arms (canonical order R, C, P, Rv, Cv, Q):
    row 1 (reps 1, 6): C Cv P R Rv Q
    row 2 (reps 2, 7): Rv C Cv Q P R
    row 3 (reps 3, 8): P Q R C Cv Rv
    row 4 (reps 4, 9): R P Cv Rv Q C
    row 5 (reps 5, 10): Q Rv R C Cv P
    position sums per arm over the 5 rows: {'R': 12, 'C': 12, 'P': 12, 'Rv': 13, 'Cv': 13, 'Q': 13} ; mean positions {'R': 2.4, 'C': 2.4, 'P': 2.4, 'Rv': 2.6, 'Cv': 2.6, 'Q': 2.6}
Notes: n = 5 is exact (every arm mean position 2.0). n = 4 and n = 6 cannot be exact with 5 rows (the sum 5 x (n - 1) / 2 is 7.5 and 12.5): the sums differ by at most 1, R and C hold exactly the same sum, no arm stands at the same position in two consecutive rows (row 5 to row 1 included), and for n = 6 five different arms open the five rows. Box1, box2 and box3 hold 6 arms when P and Q start; box4 and box5 hold 4 arms when P and Q do not start (5 if one does).

## 6. Payload ~/feed-payload/rust4b (dest on the boxes <home>/rust4b; one payload for all five hosts, 769 MB, 47 files)
- PAYLOAD_SHA256 (the list of sha256 of every file but itself) sha256 939a31be0078dff41e0202306fcbc943602b16b81a1798b624746e040205df61; `sha256sum -c PAYLOAD_SHA256` in the payload directory reports every file OK.
- Files other than the 34 wheels (full list; the wheels are in the file PAYLOAD_SHA256 and covered by the wheelhouse list hash 21360ef9...):
    5a6ccc32ec04ca14d831f6b508bb69822ea51c6f16b7305f601dd87a056e1fd8  ./bin/C_sv5_driver
    d0f8ec89e4f63c6ed37fb6d5416662e3b56e740b202126d8f8637cb5cb6e6503  ./bin/R_cis2_ref
    4999a4da5a1116aa282480376fa483ee9675ae7d442b388ba838192d03b315b3  ./bin/llama-drv-avx2
    5441f651b61d713287afa35b2552afc7569a5ef16b56fc1e07a3ffae978aec85  ./bin/llama-drv-sse42
    a08c989bf4855064b911b1bbf3e361900030d4bbc8d71700bf5ee7aca3876812  ./bin/rust4b_resident
    f29225a8d994d1b5edbbd446d55792f8513c092a829521ba0c1ef43f9b465ed2  ./filelists.json
    8de5be7131bd2250d2631bf6b84b37a654511ce339a25df0e299082579fbf3bc  ./gguf/model-f32.gguf
    d27650ed0f22126fd1c7c3ee4d862a7a1abc461884bcf56dd969d538c3d17144  ./inputs/REF_COLD_WITNESS.txt
    7323b9818e6819f332a9b865a47d946842028ce0b2e257023bfa3b4a44d75f7d  ./inputs/work_cold.jsonl
    160db7d26ed93111f2cc174c2ee38548bf68fd4ae266223c6fda8396008602f4  ./p/WHEELHOUSE_SHA256
    b3e4a4ff08eef607ab3f4846e857fac1568e8cc056c54f178336ad74642f9b07  ./p/pstart.py
    6929910c32df2897bf16487dd95d2c19df364147d050fbc49e769511a5fb37fd  ./p/requirements.lock
    337a6e17b360991b2da0d2d7cc81538bc92e97d83a1cd6f1c2515a8f15a31373  ./run.py

## 7. Wrappers ~/feed-payload/jobs (each carries the frozen payload-list hash 939a31be0078dff41e0202306fcbc943602b16b81a1798b624746e040205df61 and the runner hash 337a6e17b360991b2da0d2d7cc81538bc92e97d83a1cd6f1c2515a8f15a31373 and ends INVALID on a difference; box1 and redo10 also pause and restore cm-tick.timer and cm-rc-watch.timer, failsafe 7200 s)
- 5bb6bd4a63d268dff8a83620aed0b104f0502e32941481892afa8f7f5f8ab110  rust4b-box1.sh
- 2e383a8f7cd024d8c84622e35ee44312a02cdc4a07e76d5a432e176d6bca86dd  rust4b-box2.sh
- e13dee969cad0ef1d32d92e7dee36398892b7d4a144b51e75b764fe9cf2f20c6  rust4b-box3.sh
- 0fda13b475719e52eb7ea4afef575a3af2f30e7d0479656c27a5088afd753290  rust4b-box4.sh
- 8a45683cb2bd8432ea8668f26f28ecf2fce55253c9e47d9b224b571cb1944707  rust4b-box5.sh
- a8a6ed2c1d4cb95f6483e517c535898af125d30d604ef82001d9a4de78e259fa  rust4b-redo10-box1.sh
(copies in the repo folder rust-lab/rust4b/jobs, cmp equal.) Wrapper plumbing was tested on penguin with a stub systemctl, systemd-run and run.py (wrapper_test.sh): timers paused and restored, cm-legd.timer untouched, failsafe not armable gives nothing paused, SIGTERM restores the timers and writes a RESULT line, box2 leaves every timer alone, a changed payload list or runner ends INVALID with both actual and frozen values.

## 8. Not in this file
The bar sha256 (BUILD.md, top), the amend or registration record, the ledger batch number and the --ref of the start record. Nothing is queued: the cm-feed lines are in BUILD.md for the operator.
