# rust-2a

- Question (ledger title): rust-2a: Rust port of the C cap-1c trainer, checkpoints byte-identical to C on every host (LANGUAGE, port fidelity, 13k parameters)
- Why this is CIS-2 scope: CIS-2 implementation-language question (Rust vs C vs PyTorch for the CIS-2 runtime/training port)
- Verdict, as the ledger says: **MET** (ledger result row, 2026-10-04T05:28:25Z)
- Registered: 2026-10-04T00:34:55Z, bar_sha256 `7bed148535aa4f8939a60efa1dcae855ce9e701645b49c71a2b12ecd66256c49`, git_head `234c44cc005aa06b75c583c908277691220527b7`
- Amended: 2026-10-04T01:11:26Z, bar_sha256 `dfcaff2da9684175c01884ebb972dfd2bdeb12e5a4d02146d53f1a2ef12329c7`. Reason: Pins only: tree commit, file hashes, tool versions, flags, memory limits and measurement caveats recorded before start; no threshold, label or sentence changed.
- Started: 2026-10-04T01:11:26Z

## Ledger summary (verbatim from the result row)

PORT EQUAL (level with C). LANGUAGE (port fidelity, 13,088-parameter byte MLP, 200 steps): the Rust port reproduces the C trainer's 4 checkpoint digests on penguin, box1, box2, box3, box4 and box5 with Rust gnu and musl builds at opt-level 0 and 3, in its initial complete attempt (commit 4a41cbb, 0 fix cycles). Nothing follows for 135M to 360M models, for training speed, or for PyTorch. Phone: NOT RUN. Reference digests fd64cf9e032ee182, d36bd7fd164ba774, 3887f7b3f512a6a2, f665ffecfabba7a4 (the 2026-09-24 report and the C original rebuilt on penguin agree). No INVALID condition triggered (init and batch hashes equal, flags recorded, no platform exp/log/pow and no FMA in the Rust binaries). MEASUREMENT, no bar: box1 in-process wall, median of 5: C -O2 0.2669 s, Rust gnu O3 0.4136 s, Rust musl O3 0.4168 s, C -O0 2.0576 s, Rust gnu O0 7.6141 s; Rust/C ratio 1.549 and 1.561 (O3 vs O2), 3.700 (O0 vs O0): SURPRISE (outside 0.8 to 1.25), cause not examined, no label drawn from it. Informal hosts: box2 1.18, box3 1.44, box4 1.31, box5 1.42 (musl O3 vs C O2). Verifier confirmed 2026-10-04 (re-ran penguin, re-hashed box2, checked no iterate-until-match). Disclosures: builder knew the target digests; digest-mode raw files on box1, box3, box4, box5 were overwritten by their timing jobs (RESULT lines and the 5 timing arms remain; penguin and box2 raw intact); runner fixed before start by commit f90658c with rust/ unchanged; box1 timing at nominal 400% quota, load under 0.3 at the start gate only (pin P7), turbo state during the run not known; one valid=NO row each on box3 and box4; pairings opt-matched by the report.

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `reports/`: analysis reports, result files and key logs from the lab host.
- `results/`: result files named in the ledger result row.
- `plans/`: plan / bar files.

## Omitted from this folder (size or type); sha256 recorded so the originals can be matched

- binary/non-text: 2 files, 2.3 MB total. Examples:
  - `state/reports/rust-lab/rust-2a/diag-box1/cap1c_patched.bin` (25848 bytes, sha256 `247588a522323e7c7d450c69cd433ea98626b551e303474c6cbed2f677d4d68f`)
  - `state/reports/rust-lab/rust-2a/diag-box1/rust2a-gnu-O3.bin` (2253792 bytes, sha256 `a257e1fac30149c7f9ad0594727dd52731cd061e85845c9d1983bbc527ca1c45`)
- Full omitted list for this folder is in `OMITTED.tsv`.
