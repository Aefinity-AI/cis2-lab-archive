# rust-1b

- Question (ledger title): rust-1b: FRAMEWORK and KERNELS (stage 2 of rust-1): Rust glue + OpenBLAS/MKL, PyTorch, llama.cpp, own Rust kernels
- Why this is CIS-2 scope: CIS-2 implementation-language question (Rust vs C vs PyTorch for the CIS-2 runtime/training port)
- Verdict, as the ledger says: **MET** (ledger result row, 2026-10-05T04:48:30Z)
- Registered: 2026-10-04T09:17:01Z, bar_sha256 `2e0f94a5c74a210bc121471e3c6a01f528e0cc90c9521cf3b9890d4fa5f2df46`, git_head `a6b945adafe3739d036714f633c6bfd649d90fee`
- Amended: 2026-10-04T16:00:13Z, bar_sha256 `b1d2fdb1303c362f647885fe0cf9e0f7eed8d026cc4ebc817b31ccc5e07e8671`. Reason: READINGS AND RECORDS FOR THE STAGE 2 RUNNER, made before any run and before start. Form: insertion of 15 lines (1 of them blank), 0 deleted, one hunk after the EXPECTED/FIXED text and before the SENTENCES paragraph; registered bar_sha256 2e0f94a5c74a. The registered text is kept whole. Items R1 to R12 are readings of rules that the registered bar leaves open, and records that the freeze file FREEZE-STAGE2.md carries. R1 (load tested at the start of an arm run and, during the run, a void rule with limits relative to an idle baseline measured in the job), R2 (reference of the clock rule), R9 (ba
- Started: 2026-10-04T16:04:24Z

## Ledger summary (verbatim from the result row)

met. Verdict word: met means the two-sided pass mark produced its labels (four of four decided); it does not say who is ahead, so quote the labels with it (the pass mark has no mapping to the four register words; recorded as rust-1 and rust-5 were). Phase n1, box1, N=1, 5 reps each, all 45 kept. FRAMEWORK (stack against stack, not language): G-OB ahead of PyTorch fp32+MKL r=1.338; G-OB ahead of llama.cpp F32 r=1.195 (llama.cpp is not the same arithmetic: largest logit difference to L-C 0.072 against about 0.0002 for G-OB, G-MKL, X and T); G-MKL ahead of PyTorch r=1.304. KERNELS: engine X ahead of torch r=1.303 (matrix-vector product alone; attention, softmax, rope stay on the strict scalar path G shares). Headline: framework: G-OB against T ahead, G-OB against Q ahead, G-MKL against T ahead; engine: ahead. All four ahead with separated reps, for this torch set-up, one thread, one machine (box1), SmolLM2-135M; not PyTorch in general. Three of four had a written expectation (most likely behind: 55 percent, 60 percent, and llama.cpp above G-OB), all went against it (SURPRISE); G-MKL against T had no written probability and went the same way as G-OB. No label: memory lines, X against Q (1.165), phase n2 at two threads on box1 (llama.cpp F32 and the Rust arms in the same range), Q8_0 extra, box2 and box3. INVALID: stock PyTorch arm at N=2 on box1 (Threads 4 not 2); box2 (three clock discards, 20.3, 23.1 and 18.5 percent below the reference clock; box2 phase n2 not run) and box3 (three discards, rule not readable from the copied files: rows not copied). Trust column and memory lines (no label) are in RESULT.md section 5: T's hidden-state hash differs across hosts; peak PSS G 539 MB, T 1,332 MB, Q 587 MB. Disclosures: G-OB, G-MKL, T, Q not pure Rust (X is); kernels differ unless G-MKL used; CPUQuota non-binding; 03:20:00Z operator row pull on box1 in the gap between arm runs of n2 (about 27 s before gmkl-O2 rep 0 started, outside every timed window; box1 clock not compared with penguin's), that rep kept, no label; memory line says same calendar day as rust-1; three voided reps in n2, each repeated. Independent checks: recompute, validity and claims readers agree with every label and the verdict word; a final read confirmed every number; the operator's final wording edit is item 13 of the corrections. Not a language verdict.

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `reports/`: analysis reports, result files and key logs from the lab host.
- `results/`: result files named in the ledger result row.
- `plans/`: plan / bar files.

## Notes

- Large per-run stdout/stderr files were kept only when under the size cap; see the omitted list.
