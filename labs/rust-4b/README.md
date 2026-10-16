# rust-4b

- Question (ledger title): rust-4b: cold start (M2 of rust-4) with a per-file residency check: cis2_ref (Rust) against verify3 (C), the Python start, llama.cpp (MEASUREMENT)
- Why this is CIS-2 scope: CIS-2 implementation-language question (Rust vs C vs PyTorch for the CIS-2 runtime/training port)
- Verdict, as the ledger says: **MET** (ledger result row, 2026-10-06T01:21:49Z)
- Registered: 2026-10-05T09:34:31Z, bar_sha256 `f37da0bcd1966ca3d6962b0ef149f7383ca7fb55a91b3d6452cc6b9773b1cba7`, git_head `ab9a44cae372d616bc03001dda78d9dab3096f3d`
- Started: 2026-10-05T09:40:13Z

## Ledger summary (verbatim from the result row)

rust-4b MET. IMPLEMENTATION (cold start, SmolLM2-135M, box1): cis2_ref (Rust) is behind verify3 (C), r=0.820; different implementations, toolchains and dependencies included, not a language verdict. Storage box1: ST4000LM024 spinning disk, ext4; one model, one prompt. Medians to the opening line: R 12.69 s, C 10.41 s; every C rep (9.68-10.74 s) faster than every R rep (11.92-15.58 s). The 2.28 s gap is mostly prefill arithmetic (1.70 s; load 0.43 s). FRAMEWORK (no-Python effect): static binaries start 3.03x (R) and 3.69x (C) faster than the Python stack on box1 (median of 5; 2 of 5 P reps under 3x R; P 34.7-87.2 s); no label. Expectations: TIE (carried 60 pct, operator 50) SURPRISE; P above 3 on box1 held; P above 3 on box2 SURPRISE (1.52 over R, 1.96 over C, no label). Box2-5 numbers only (Rule A); P and Q did not start on box4/box5 (rc -4). Cold = no page of the listed files in memory before start; base system files not listed; not a language verdict; nothing about warm decode. Verifier and scorer agree.

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `reports/`: analysis reports, result files and key logs from the lab host.
- `results/`: result files named in the ledger result row.
- `plans/`: plan / bar files.

## Omitted from this folder (size or type); sha256 recorded so the originals can be matched

- file over 1500000 bytes: 1 files, 1.6 MB total. Examples:
  - `state/reports/rust-lab/rust-4b/trace/P.opens` (1602185 bytes, sha256 `972abbec4972594ec1f6672e67940d6001220365bca2794a7ea10a7393fbad85`)
- Full omitted list for this folder is in `OMITTED.tsv`.

## Notes

- Large per-run stdout/stderr files were kept only when under the size cap; see the omitted list.
