# rust-2b

- Question (ledger title): rust-2b: Burn (CPU Flex) vs PyTorch training a 1.8M-parameter byte transformer, 200 steps (FRAMEWORK)
- Why this is CIS-2 scope: CIS-2 implementation-language question (Rust vs C vs PyTorch for the CIS-2 runtime/training port)
- Verdict, as the ledger says: **MET** (ledger result row, 2026-10-16T02:34:05Z)
- Registered: 2026-10-04T00:34:55Z, bar_sha256 `745d99333d8a16670ee737c4be8be8cf0cad96ded4c9e03692bb142f6e14033b`, git_head `234c44cc005aa06b75c583c908277691220527b7`
- Amended: 2026-10-05T19:32:50Z, bar_sha256 `f6ec3c8322c95836fa28d8d5bfc7e9b7ef0c131af8af242ae6bd91367a5845f8`. Reason: build pins A1 to A4 (versions and flags incl. burn-flex features std, simd, rayon; payload pins; data, order, init pins; the torch warm-up sentence) and A5 (scorer file pins), builder 2026-10-05, revision 1; registered text unchanged above the AMENDMENT heading; A1 is the registered features sentence read as in the operator ruling of 2026-10-05 18:16Z by Fable, corrected 18:43Z and 19:15Z (one clause of fact 4, one clause of fact 3 and the change record; the choice is unchanged), RULING-A1.md sha256 ca89995d8ef17c94a044f3d15c29a2c78c85bb298ef1216d3e3d8a80a495fd43; five conformance reads and tw
- Started: 2026-10-06T01:09:28Z

## Ledger summary (verbatim from the result row)

FRAMEWORK, not language (CPU, 1.8M-parameter byte transformer, 200 steps, N=1): Burn Flex, pure Rust is behind PyTorch on box1, steps/s ratio r=0.4476463, final loss 2.4778 against 2.4778. FRAMEWORK: BURN BEHIND. Scale: 1 to 5 million parameters on CPU only; GPU training and 135M to 360M models are untested. FRAMEWORK (memory): Burn peak PSS is lower than PyTorch on box1, ratio 0.357; no-Python effect, not a Rust-language effect.

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `reports/`: analysis reports, result files and key logs from the lab host.
- `results/`: result files named in the ledger result row.
- `plans/`: plan / bar files.

## Omitted from this folder (size or type); sha256 recorded so the originals can be matched

- binary/non-text: 12 files, 88.4 MB total. Examples:
  - `state/reports/rust-lab/rust-2b/box2/check/B_grads1.bin` (7365120 bytes, sha256 `a25829e6f6f5524e8836e48efd596fd7145c467edd0afa4e0da671acdf7ed8ac`)
  - `state/reports/rust-lab/rust-2b/box2/check/B_params1.bin` (7365120 bytes, sha256 `e54e637cca1acbfe790a70b68e164db856790eeff60c28ce7b280f2558e6c765`)
  - `state/reports/rust-lab/rust-2b/box2/check/T_grads1.bin` (7365120 bytes, sha256 `20bb04b941bf52059d700631fdb71371bf866d84eadaaf7694411816936903d6`)
  - `state/reports/rust-lab/rust-2b/box2/check/T_params1.bin` (7365120 bytes, sha256 `9e51eddb4627e1bdccb66cbebaabd806bcdc81fb9f83d97c22aae0644a40b3ea`)
  - `state/reports/rust-lab/rust-2b/box1-docbuild/check/B_grads1.bin` (7365120 bytes, sha256 `167fe93f129536fd80b322493424ae5486f8996c8cc6c10906def0a1611d4115`)
  - `state/reports/rust-lab/rust-2b/box1-docbuild/check/B_params1.bin` (7365120 bytes, sha256 `71845c0704a0b41cc46272855639e0cb276d2feef4c612763ee6cf3b6f556b5c`)
- internal publication-scoring record (out of scope): 1 files, 0.0 MB total. Examples:
  - `state/reports/rust-2b/PUBLISH-SCORE.md` (3132 bytes, sha256 `f90075a4eaa4970b116e36d5cf86cc2d4e241ac027bac00e9d86104100e76140`)
- Full omitted list for this folder is in `OMITTED.tsv`.
