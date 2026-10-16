# rust-3 RESULT (scored 2026-10-16 04:25Z)

Lab: rust-3 "loader robustness under malformed files, our Rust loader vs our C loader, same mutation operators and time per arm".
Registry: `bin/cm-exp show rust-3` (registered 2026-10-04T00:34:55Z, bar sha256 091dfb37…; amended 2026-10-12T17:41:34Z to pin the K5 oracle, bar sha256 4c3f9f51d172bf60d371d5fade2647300c8b7a4909b2b308aaff7384761cddd9; started 2026-10-12T20:40:33Z ref cm/rust-lab@ce3e7107 payload 6cd45a34… freeze 33a97267…).
Bar text: state/plans/rust-lab/bars/rust-3-amended-bar.txt (unedited). Verdict: BAR APPLIED, valid run. Labels are per class; there is no overall label and no sum.

## The five class lines (bar sentences, verbatim form)

LANGUAGE (our Rust loader against our C loader, same fuzzer, same sanitiser, 1 hour each, K1 memory-safety): Rust shows 0 distinct findings, C shows 10: RUST LOWER. Counts are small and the C loader parses one format. Classes are not added together.

LANGUAGE (K2, controlled failures, informational): our Rust loader shows 0 and our C loader shows 0; the C loader's error-code returns are not counted, so this is not a defect ranking. (As scored by the tool. Corrected reading in deviation note 1: Rust 3, C 0, "more controlled failures" on the Rust side.)

LANGUAGE (our Rust loader against our C loader, same fuzzer, same sanitiser, 1 hour each, K3 hang): Rust shows 0 distinct findings, C shows 0: TIE (counts too small to separate). Counts are small and the C loader parses one format. Classes are not added together.

LANGUAGE (our Rust loader against our C loader, same fuzzer, same sanitiser, 1 hour each, K4 over-allocation): Rust shows 0 distinct findings, C shows 2: TIE (counts too small to separate). Counts are small and the C loader parses one format. Classes are not added together. (Rule conflict, deviation note 2: the difference rule nC - nR >= 2 reads RUST LOWER; the small-counts rule nR + nC < 3 reads TIE. The bar's own sentence for nR + nC < 3 is applied.)

LANGUAGE (our Rust loader against our C loader, same fuzzer, same sanitiser, 1 hour each, K5 wrongly accepted): Rust shows 1 distinct findings, C shows 4: RUST LOWER. Counts are small and the C loader parses one format. Classes are not added together.

FRAMEWORK/third-party (no label): R2 (alice-rs loader, memmap2) shows K1 0, K2 0 (corrected 8), K3 0, K4 0, K5 4 (K1/K3/K4 are lower bounds, deviation note 5); this says nothing about our Rust or our C.
FRAMEWORK/third-party (no label): L1 (llama.cpp GGUF loader via gguf_init_from_file_ptr, harness pkg/l1/h_l1.cpp, ASan, box1, 2 trials x ~30 min, 43,327,666 + 45,186,194 execs, 144 raw artifacts) shows K1 0, K2 1 (ggml_abort), K3 0, K4 1 (asan alloc-too-big in ggml_aligned_malloc <- ggml_init <- gguf_init_from_reader), K5 not assessed; both sites found in both trials; this says nothing about our Rust or our C. Reproducers: box1 ~/legs/rust3-L1-box1/repro (4 files). Third-party: triage against upstream llama.cpp main before any disclosure (NEEDS).
FRAMEWORK/third-party (no label): P1 (PyTorch pickle loader via atheris, ASan preload, w2 = ex-box1, 2 trials x ~31 min, 25,026,825 + 25,067,991 execs, 0 crash artifacts) shows K1 0, K2 0, K3 0, K4 0, K5 not assessed; harness_crashes 1 = a replay-phase timeout on mutant O1_000.pt (stack is atheris/libFuzzer alarm machinery only) that did not reproduce on minimisation (7.3 s, under the 10 s timeout, minimised to CLEAN), so it is not a loader finding; this says nothing about our Rust or our C. Raw: raw/result-P1.json, raw/RESULT-P1.txt.
FRAMEWORK/third-party (no label): R3 RUNNING on w2 since ~07:05Z (deviation note 7); no row until it lands.

## Surprise against the pre-run estimate
Expected K1: Rust 0 (about 90 percent), C 0 or 1. Observed C 10 distinct keys at 3 sites. The C side is the public verify3 loader (cis2-spec verify3/model.c, verify3/json.c). All ten are reachable from a malformed header before any weights hash is checked; see "C findings" below. Expected K2 Rust 1 to 3: observed 3 (corrected). Expected K4 Rust 0 to 1, C 0 to 1: observed Rust 0, C 2 keys at one site. Expected K5 both 0 to 1: observed Rust 1, C 4, R2 4.

## Counts per arm (dedup key = class | deepest own-or-vendored frame | operator)

| arm | K1 keys (sites) | K2 as scored / corrected | K3 | K4 keys (sites) | K5 keys (sites) | harness crashes as scored | raw crash artifacts | execs trial 1 + 2 | wall s trial 1, 2 |
|---|---|---|---|---|---|---|---|---|---|
| C1 verify3 (C) | 10 (3) | 0 / 0 | 0 | 2 (1) | 4 (3: bounds, overlap, size) | 0 | 201 (K1 raw 1891 reports, K4 raw 309, triaged fully) | 132611 + 129916 | 1800.4, 1800.4 |
| R1 cis2_ref + vendored safetensors 0.8.0 (Rust) | 0 | 0 / 3 (1 site) | 0 | 0 | 1 (1: bounds,size) | 24 | 24 | 761187 + 727894 | 1866.2, 1826.2 |
| R2 alice-rs + memmap2 (Rust, reported row) | 0 (lower bound) | 0 / 8 (3 sites + core) | 0 (lower bound) | 0 (lower bound) | 4 (2: overlap, size) | 257 | 257 triaged + 2190 untriaged | 188961 + 207821 | 1800.7, 1800.1 |

K5 oracle rows: C1 983 assessed, 305 accepted by the loader, 111 wrongly accepted files; R1 1545 assessed, 108 accepted, 13 wrongly accepted files; R2 1251 assessed, 224 accepted, 36 wrongly accepted files. Oracle sha256 e81d09b65cbee3ca8917d5f0fc9c2db8536580be7dab1729ccddaccbc01f2739 in every arm (matches the amended bar).

C1 K1 keys: cis2_model_load ×3 (O1, O6, libfuzzer), json_obj_get ×3 (O1, O2, libfuzzer), st_get_tensor ×4 (O1, O3, O6, libfuzzer). Kinds: heap-buffer-overflow 7, SEGV on unknown address 3. C1 K4 keys: cis2_model_load ×2 (O1, libfuzzer): header_len taken from the file drives malloc(header_len+1) to about 2^63 (ASan allocation-size-too-big / rss limit). C1 K5 keys: O3 (overlap), O4 (size), O6 (bounds), O7 (duplicate key; see note 6).
R1 K5 key: O7 only (13 files, duplicate-key mutants; see note 6). R2 K5 keys: O3 (overlap), O5 (size), O7, libfuzzer.

## Trust column (count_trust.py, raw/trust.json)

| arm | loader lines own | with vendored | unsafe lines own / vendored | dependencies | header fields parsed | K1 per 1,000 lines (with vendored) |
|---|---|---|---|---|---|---|
| C1 | 419 | 419 | n/a (C) | 0 | 2 (dtype, data_offsets) | 23.9 |
| R1 | 21 | 955 | 0 / 3 | 29 | 4 | 0 |
| R2 | 68 | 1536 | 1 / 140 | 13 | 3 | 0 (lower bound) |
| L1 | 1402 | 1402 | n/a (C++) | 0 | 12 | not run |

Caveat written into the bar and repeated here: C1 parses one pinned bf16 format and two header fields, so it may show fewer bugs because it is smaller (a loader-size effect), not because of the language. In this run the smaller loader showed more, so the size caveat does not explain the K1 result; it still applies to every TIE line.

Miri (box3, extra, not counted): files=2 ub=0 (raw/RESULT-miri-box3.txt; aegis-core unsafe blocks not included).

## C findings (our public code; fix before publication)
All in the public repo Aefinity-AI/cis2-spec at commit c98d438 (verify3/, 2026-09-23):
1. verify3/model.c cis2_model_load: header_len is read from the file and never bounded against the file length before malloc(header_len+1) and memcpy (K1 heap-buffer-overflow when header_len exceeds the bytes present; K4 when header_len is huge).
2. verify3/model.c st_get_tensor: data_offsets start/end are used as `g_st.data + start` without checking start <= end <= data_len (K1 heap-buffer-overflow / SEGV).
3. verify3/json.c json_obj_get: strcmp on a key pointer that can be null or point past the buffer when the header JSON is truncated or has a non-string key (SEGV).
4. K5: json_obj_get is first-wins on duplicate keys; shape/dtype/offset fields are not validated against the file length (overlap, size, bounds accepted).
Reproducers: 201 minimised files copied to box7 ~/legs/rust3-c1-repro/ (originals box1 <home>/legs/rust3-C1-box1/repro/). Fix tracked as a cis2-spec PR (see NEEDS); digests are expected to be unaffected because the fixes only reject files the pinned model never produces; the PR CI digest check decides.

## Deviation and interpretation notes (dated 2026-10-16; the bar is unedited)
1. Scorer misfiling of Rust panics (tool defect, not a bar change). run_arm.py keeps the first 12 stack frames (line 150); a Rust panic's first 12 frames are panic machinery, so classify.py saw no loader frame and filed every Rust panic as a harness crash (R1 24, R2 257). The "panicked at" line of each record is in loader source. Corrected by reading that line: R1 K2 = 3 keys at 1 site (loader_extract.rs:11 load_f32_tensor unwrap_or_else "tensor … missing": O2 19 files, libfuzzer 2; loader_extract.rs:12 assert_eq shape mismatch: O4 3); R2 K2 = 8 keys at 3 sites + core (safetensors.rs:39 `open` slice 8..8+n out of range: O1 69, O6 17, libfuzzer 2; safetensors.rs:61 `get_f32` slice by data_offsets: O3 44, O6 78, O7 20; safetensors.rs:52 `get_u8`: O7 5; core accum.rs:206 `product()` overflow inside get_f32: O4 19, O7 3). None is an allocation-failure abort, so no hidden K4. K2 carries no label, so the four labels are unchanged. The bar's INVALID rule "a harness crash counted as a loader finding" is not triggered (the error ran the other way: loader panics counted as harness crashes; after correction no harness crash is counted as a finding). Both readings are reported.
2. K4 rule conflict. nR = 0, nC = 2 satisfies RUST LOWER (nC - nR >= 2) and also nR + nC < 3 ("TIE (counts too small to separate)"). The bar gives no precedence; the small-counts sentence is applied because it is the bar's own sentence for this count range, and the conflict is stated on the line.
3. Fuzz flags. All arms ran with -fork=1 -ignore_crashes=1 -ignore_timeouts=1 -ignore_ooms=1 in addition to the bar's -max_len=1048576 -rss_limit_mb=1024 -timeout=10 -seed=<trial>. Fork mode is not in the bar text; it is identical across R1 and C1 (the INVALID rule needs a difference between them), so the pair stands. Recorded here.
4. R1 trial walls 1866 s and 1826 s, over (not under) the 30-minute trials; the INVALID rule is "under". Executions are reported, not labelled.
5. R2 triage cap. run_arm.py triages at most 1500 artifacts per trial; R2 produced 2190 artifacts beyond the cap that were never triaged. R2 K1/K3/K4 are therefore lower bounds; R2 is a reported row with no label, so no label is affected. Re-triage of the 2,190 untriaged files RUNNING on w3 since 2026-10-16 ~07:45Z (feed leg rust3-R2-retriage-w3; the frozen scorer's own replay/describe, mtime order from w2, no minimisation; job state/labs/rust-3/jobs/rust3-R2-retriage.sh). Dry run on hq, 4 files: all K2 at alice_src/safetensors.rs:39.
6. K5 duplicate-key interpretation. The pinned oracle counts every duplicate definition of a tensor name; serde_json in safetensors 0.8.0 keeps the last definition, and a last-wins check (raw/lastwins-check.py, run 2026-10-16) shows all 13 R1 O7 files consistent under last-wins. The bar says the oracle decides, so the count stands; it is not evidence of a validation bug in the safetensors crate. C1 K5 without O7 is still 3 keys; R2 K5 without O7 is 3. A NEEDS line records this as a third-party finding with the recommendation "no disclosure".
7. R3, P1, L1 not run. Binaries exist on box1 (<home>/scratch-rust3/rust3-bin: l1_fuzz, p1_fuzz, r3_fuzz; prefixes L1/P1/R3.txt); jobs rust3-L1/P1/R3-box1 are queued after the W6 box1 leg. They are reported rows with no label, so the bar pair is complete without them.
8. Mutant counts: 100 per operator per format (gguf 700, pickle 700, safetensors 700; MANIFEST.tsv sha256 d3e33587…); the INVALID rule on unequal counts is not triggered.
9. R1 K5 site is recorded as "bounds,size" by the oracle (one file class failing two checks); counted as one site.

## Pins
Scorer: pkg/classify.py 5f3f0fe443b98a4b8f825bb433ae1a84f6ceefe06e47b3ed9cc44b69c7e0f8ea; pkg/run_arm.py e551fd9b8d968cb8d3315a80c5f42893b0b7aa2004be5477b5d613cacc138911; pkg/summ.py 6c269f4e32c118dc2e415e7dc942b36cf28a6ed5f1ca24cd31aabaf22a9cd456; pkg/count_trust.py 11c10b7f…; payload SHA256SUMS 6cd45a34… (6355 files). Fuzz binaries: c1_fuzz 37751d1b…, c1_accept 8808742c…, r1_fuzz 10a9e840…, r1_accept a1c53661…, r2_fuzz c1540050…, r2_accept c0fe63c7…. ASan on in every arm; hash gate off in every harness (harness enters below the gate, BUILD.md). Raw: state/reports/rust-3/raw/ (result-*.json, RESULT-*.txt, trust.json, RESULT-miri-box3.txt). Trials and corpora: box1 <home>/legs/rust3-<arm>-box1/{repro,trial1,trial2}.
Publication: per PUBLISH-SCORE.md beside this file; hold until the verify3 fix PR is merged.

## L1 reproducer validation on a second host (hq, 2026-10-16 ~06:55Z; dry run of state/labs/rust-3/jobs/rust3-L1-repro.sh)
All four L1 crash files reproduce on hq (i7-7700HQ, AVX2; harness rebuilt locally with the payload's build.sh, Debian clang 19.1.7 + clang19-res; harness sha256 c515d9ac… differs from the w2 build as expected):
2 × K2 (ggml.c:1787 GGML_ASSERT(INT64_MAX / ne[i] > current_nelements)), 2 × K4 (ASan: requested allocation size exceeds maximum, in ggml_aligned_malloc ← ggml_init ← gguf_init_from_reader). Files: state/reports/rust-3/L1-repro-hq/{RESULT.txt,run.log}. Third host (w3, no AVX2) queued as feed leg rust3-L1-repro-w3. Status: reported rows, not counted; upstream triage before any disclosure (NEEDS).

Third host w3 (ex-box2, Celeron N4020, no AVX2), feed leg rust3-L1-repro-w3, 2026-10-16 ~07:10Z: 4/4 reproduce (2 K2 at ggml.c:1787, 2 K4 ASan alloc-too-big), harness sha256 9a4fd2b80ed025f7…. The L1 sites now reproduce on three hosts (w2 original, hq, w3). File: L1-repro-w3/RESULT.txt. Status unchanged: reported rows, upstream triage before any disclosure (NEEDS).
