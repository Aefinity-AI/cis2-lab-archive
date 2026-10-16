# CIS-2 lab archive

Status: archived 2026-10-16, development paused. Aefinity AI is focusing on ALICE and CIS-1.

CIS-2 is a specification and reference implementations for float inference that gives the same bits on different CPUs and GPUs: fp32 inference with pinned operation order and pinned math functions, a witness digest over the computation, and receipts built on that digest. The public spec is at https://github.com/Aefinity-AI/cis2-spec . This repository holds the lab record that sits behind it: pre-registered bars, ledger rows, results, analysis reports and the code snapshots. It does not repeat what the public spec already contains.

## How to read this archive

- `labs/<id>/` has one folder per lab. Verdicts are copied from the experiment ledger exactly as recorded (MET, NOT MET, INCONCLUSIVE, INVALID) or marked open when the ledger has no result row. Losses are reported the same way as wins.
- Each folder README states the question, the registration time and bar hash, the files, and anything left out.
- `labs/<id>/ledger.jsonl` has every ledger row for that id. `PREREG-from-ledger.md` is the bar text as registered; its sha256 equals the `bar_sha256` field (checked for every row).
- `labs/pre-ledger-*` folders group reports from before the ledger existed, or from plain legs. They have no ledger verdict, and this archive does not assign one.
- `code/` has working-tree snapshots (no git history). See `code/SOURCES.md` for repos and commits. Code under code/ is published for reference; no licence is granted for it at this time. Documentation and results are under the root LICENSE (Apache-2.0); see `NOTICE`.
- `paper/` has the CIS-2 paper drafts. `REDACTIONS.md` lists what was removed, rewritten or left unchanged. `MANIFEST.sha256` lists every file.
- Host names: w1 to w4 and hq are the current fleet names. Older records use box1 to box7 and penguin. Mapping: box1 = w2, box2 = w3, box3 = w4, box6 = w1, box7 = hq. box4, box5 and penguin were retired machines (SSE3/Pentium class and a Chromebook). Records are not rewritten.

## Index

Ledger labs: 27 (19 MET, 4 NOT MET, 1 INVALID, 2 open, 1 PREREG draft with no ledger rows). Pre-ledger report groups: 5.

### Replay and rerun (sv-5 family)

| id | question | verdict | basis | folder |
|---|---|---|---|---|
| sv-5 | Exact replay (CIS-2) vs TOPLOC vs stock rerun on SmolLM2-135M | NOT MET | ledger | [labs/sv-5](labs/sv-5) |
| sv-5b | sv-5 follow-up: does a stock PyTorch rerun still give the same tokens on another CPU class at 256 tokens? | NOT MET | ledger | [labs/sv-5b](labs/sv-5b) |
| sv-5c | Does batching or thread count break token equality of a stock PyTorch rerun? (256 tokens, SmolLM2-135M) | NOT MET | ledger | [labs/sv-5c](labs/sv-5c) |
| sv-5d | Per-token divergence rate of a stock PyTorch rerun across CPU classes and under batching (1.6M positions, SmolLM2-135M) | MET | ledger | [labs/sv-5d](labs/sv-5d) |
### Compiler and model shape (C driver)

| id | question | verdict | basis | folder |
|---|---|---|---|---|
| cis2-oflags-1 | CIS-2 C driver digests vs compiler optimisation level (box5, gcc 14.2) | MET | ledger | [labs/cis2-oflags-1](labs/cis2-oflags-1) |
| cis2-oflags-2 | CIS-2 C driver digests vs compiler vendor (clang 19 vs gcc 14.2, box5) | MET | ledger | [labs/cis2-oflags-2](labs/cis2-oflags-2) |
| shape-1 | CIS-2 C driver on a new Llama shape (llama-160m, MHA, untied head): digests on four CPU classes and agreement with stock torch | MET | ledger | [labs/shape-1](labs/shape-1) |
| shape-2 | CIS-2 C driver on llama-160m at 128 greedy tokens (300 prompts): agreement with stock torch fp32 on box4/box5, digests across three CPU classes | MET | ledger | [labs/shape-2](labs/shape-2) |
### Rust implementation question (rust-lab)

| id | question | verdict | basis | folder |
|---|---|---|---|---|
| rust-1 | rust-1: decode speed and memory on SmolLM2-135M: our Rust vs our C CIS-2 (IMPLEMENTATION), Rust+OpenBLAS vs PyTorch vs llama.cpp (FRAMEWORK), optional Rust engine (KERNELS) | MET | ledger | [labs/rust-1](labs/rust-1) |
| rust-1b | rust-1b: FRAMEWORK and KERNELS (stage 2 of rust-1): Rust glue + OpenBLAS/MKL, PyTorch, llama.cpp, own Rust kernels | MET | ledger | [labs/rust-1b](labs/rust-1b) |
| rust-2a | rust-2a: Rust port of the C cap-1c trainer, checkpoints byte-identical to C on every host (LANGUAGE, port fidelity, 13k parameters) | MET | ledger | [labs/rust-2a](labs/rust-2a) |
| rust-2b | rust-2b: Burn (CPU Flex) vs PyTorch training a 1.8M-parameter byte transformer, 200 steps (FRAMEWORK) | MET | ledger | [labs/rust-2b](labs/rust-2b) |
| rust-3 | rust-3: loader robustness under malformed files, our Rust loader vs our C loader, same mutation operators and time per arm | MET | ledger | [labs/rust-3](labs/rust-3) |
| rust-4 | rust-4: install footprint, cold start, offline build, byte-identical rebuild for Rust, C and the Python stack (MEASUREMENT) | INVALID | ledger | [labs/rust-4](labs/rust-4) |
| rust-4b | rust-4b: cold start (M2 of rust-4) with a per-file residency check: cis2_ref (Rust) against verify3 (C), the Python start, llama.cpp (MEASUREMENT) | MET | ledger | [labs/rust-4b](labs/rust-4b) |
| rust-5 | rust-5: fp32 dense matrix-vector product, 4-row interleaved, Rust vs C same algorithm (LANGUAGE), library kernels as speed only (KERNELS) | MET | ledger | [labs/rust-5](labs/rust-5) |
### Edge-exact lane (w3, w4, w6)

| id | question | verdict | basis | folder |
|---|---|---|---|---|
| w3 | w3: margin-gated verification from the sv-5d logs (flips versus top-1/top-2 margin on CPU fp32) | MET | ledger | [labs/w3](labs/w3) |
| w4 | w4: edit-strength sweep, exact replay versus a calibrated tolerance check (rank-one edit scaled by alpha, SmolLM2-135M) | OPEN (registered, never run) | ledger | [labs/w4](labs/w4) |
| w6 | w6: libm hazard bound, glibc expf versus a correctly-rounded expf (CORE-MATH) inside SmolLM2-135M decoding | OPEN (started, no result row in the ledger) | ledger | [labs/w6](labs/w6) |
### w1x series (2026-10-16)

| id | question | verdict | basis | folder |
|---|---|---|---|---|
| w1x-horizon | w1x-horizon: long-horizon CIS-2 digests (SmolLM2-135M fp32, C++ port, gen_toks 256/512/1024/2048) across hosts and the hq GPU | MET | ledger | [labs/w1x-horizon](labs/w1x-horizon) |
| w1x-tamper | w1x-tamper: real-weight tamper detection on the pinned SmolLM2-135M safetensors (1-ULP element edits, INT8 round-trip of one tensor, single random bit flips, header-only control) | NOT MET | ledger | [labs/w1x-tamper](labs/w1x-tamper) |
| w1x-tamper2 | w1x-tamper2: real-weight tamper detection v2 on the pinned SmolLM2-135M safetensors, three detection levels (witness incl. §12.1 header; witness BODY = per-step full fp32 logits + argmax ids, header e | MET | ledger | [labs/w1x-tamper2](labs/w1x-tamper2) |
| w1x-batch | w1x-batch: batch-size invariance of the CIS-2 witness (C++/CUDA port --batch N) on CPU and the hq GPU | MET | ledger | [labs/w1x-batch](labs/w1x-batch) |
| w1x-sample | w1x-sample: CIS-2 seeded-sampling clause (draft section 14: MurmurHash3_x86_32 stateless Gumbel-max noise, pinned ln/exp, rank-order top-k/top-p, first-index argmax, receipt header CIS2-SAMPLE-1) on S | MET | ledger | [labs/w1x-sample](labs/w1x-sample) |
| w1x-opencl | w1x-opencl: CIS-2 OpenCL backend reproduces the pinned 16- and 128-token digests on pocl (CPU), NVIDIA OpenCL and an Intel HD 630 iGPU (non-NVIDIA GPU) with software div/sqrt | MET | ledger | [labs/w1x-opencl](labs/w1x-opencl) |
| w1x-coverage | Constructed CIS-2 coverage vector: exact argmax tie (M15) and subnormal logit (M01) on a tiny Llama-arch model | MET | ledger | [labs/w1x-coverage](labs/w1x-coverage) |
| w1x-qwen3 | PREREG w1x-qwen3: CIS-2 model breadth, Qwen3-0.6B (QK-norm, head_dim 128) reproduces one digest across hosts | NO LEDGER ROWS (PREREG draft only; one untimed smoke run, not counted) | PREREG file only | [labs/w1x-qwen3](labs/w1x-qwen3) |
### Pre-ledger report groups (no ledger verdict)

| id | question | verdict | basis | folder |
|---|---|---|---|---|
| pre-ledger-e14-e15-reference | E14/E15 series: CIS-2 fp32 reference, cross-ISA, compiler invariance, clean-room verify; H1-H4 follow-ups; first results and critic pass | no ledger rows; see folder README | reports only | [labs/pre-ledger-e14-e15-reference](labs/pre-ledger-e14-e15-reference) |
| pre-ledger-gpu | CIS-2 on GPUs: E18/E18B, gpu2 batch sweeps, Kaggle and Lightning T4 replays, bf16 design memo | no ledger rows; see folder README | reports only | [labs/pre-ledger-gpu](labs/pre-ledger-gpu) |
| pre-ledger-models-and-scale | CIS-2 digests on other models and scales: SmolLM2-360M, Qwen2.5-0.5B, 7B, 8B feasibility; cross-box replays | no ledger rows; see folder README | reports only | [labs/pre-ledger-models-and-scale](labs/pre-ledger-models-and-scale) |
| pre-ledger-replay-selfcheck-vectors | replayable evaluation bundle, self-checks on old CPUs, vectors, verify merge | no ledger rows; see folder README | reports only | [labs/pre-ledger-replay-selfcheck-vectors](labs/pre-ledger-replay-selfcheck-vectors) |
| pre-ledger-prior-art | prior-art reports for CIS-2 | no ledger rows; see folder README | reports only | [labs/pre-ledger-prior-art](labs/pre-ledger-prior-art) |

## Borderline: kept out, listed so the call can be checked

These ledger labs touch the CIS-2 runtime but are mainly about guard models, swarms or training, so they are not in this archive. Verdicts are the ledger's.

| id | what it does | ledger verdict |
|---|---|---|
| mx-g2a | guard verdict replay identity under the CIS-2 runtime | MET |
| mx-g2b | guard verdict fidelity of the CIS-2 export | NOT MET |
| mx-g2c | 135M guard verdicts under the CIS-2 C runtime, cross-host | NOT MET |
| mx-k4c | export path on SSE3-only hosts | MET |
| sw-t1c | fixed-order C head trainer, bit-identical across CPUs | MET |
| sw-t1d | same, whole Banking77 grid | MET |
| sw-t1e | same, second dataset | MET |
| sw-t3 | replayable swarm traces under CIS-2 | open (no result row) |
| sw-t5c | micro intent router in C, same bits on every CPU | MET |
| sw-t6c | guard head with the fixed-order C trainer | NOT MET |
| tm-6b | guard abstains using the CIS-2 C runtime printed logits | MET |
| dormant-1 | exact replay vs rerun on dormant backdoor substitution | INCONCLUSIVE |
| dormant-2 | same, one complete attempt | NOT MET |

Also left out as borderline or out of scope: the cap-1 fixed-order C trainer reports, the small-1 / small-2 / spec-1 technique branches (int8, ternary, speculative decoding), the safe / trust / tools / xb receipt-gateway design and test reports, the fm-4c and fm-7 values experiments, the pub-1 to pub-4 paper-drafting process reports, and internal strategy and business documents.

## Status of the results (plain summary)

- In w1x-horizon (up to 2048 tokens), w1x-batch (batch sizes 1 to 8), w1x-opencl, w1x-coverage, cis2-oflags-1, cis2-oflags-2, shape-1 and shape-2 the ledger verdict is MET: the witness digests matched the recorded references across the hosts and builds each bar named. Read each bar for its exact scope.
- Stock PyTorch reruns did not give the same tokens across CPU classes or under batching (sv-5, sv-5b, sv-5c: NOT MET for the bars that asked whether they would; sv-5d measured the per-token divergence rate).
- The v1 real-weight tamper study (w1x-tamper) is NOT MET as registered; the second (w1x-tamper2) is MET. Both are in the archive.
- w4 was registered and never started. w6 was started and has partial data but no ledger result.

## Notes

Some records carry 'private' markers written before the 2026-10-16 decision to publish the CIS-2 archive; they are left unchanged so their ledger hashes still match.

Code under code/ is published for reference; no licence is granted for it at this time. Documentation and results are under the root LICENSE (Apache-2.0).
