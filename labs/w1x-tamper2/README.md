# w1x-tamper2

- Question (ledger title): w1x-tamper2: real-weight tamper detection v2 on the pinned SmolLM2-135M safetensors, three detection levels (witness incl. §12.1 header; witness BODY = per-step full fp32 logits + argmax ids, header excluded; greedy-token argmax digest), base trial, header-only control
- Why this is CIS-2 scope: CIS-2 real-weight tamper detection v2
- Verdict, as the ledger says: **MET** (ledger result row, 2026-10-16T10:07:19Z)
- Registered: 2026-10-16T09:29:10Z, bar_sha256 `4c146db39d2f52c7aa23a85a92972bec00d6aeebb1bced23ad5c0d572dd5b560`, git_head `05d578fbe3efb224fb4ffcb2bd4d8f5f5b77e050`
- Started: 2026-10-16T09:37:50Z

## Ledger summary (verbatim from the result row)

All three host runs (w3 seed 20261016, w4 20261017, hq 20261018; template v2) MET every clause: base trial = pinned CIS2_REF on each; sha256 and witness moved 55/55 (54 mutants + control) on each; witness BODY digest moved 54/54 on each (1-ULP 24/24, INT8 6/6, random bit flips 24/24; sign/exponent flips 11/11, 13/13, 12/12 = 100%); header-only control moved sha256 + witness and did NOT move body or argmax on all three (meta_control PASS). Argmax (greedy-token) detection as measured: w3 4/54, w4 5/54, hq 3/54 (1-ULP 0/72; INT8 9/18; bit flips 3/72 incl. sign/exp 2/36).

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `reports/`: analysis reports, result files and key logs from the lab host.
- `results/`: result files named in the ledger result row.
- `feed/`: job scripts and RESULT.txt files from the fleet job runner (per host).

## Omitted from this folder (size or type); sha256 recorded so the originals can be matched

- internal publication-scoring record (out of scope): 1 files, 0.0 MB total. Examples:
  - `state/reports/w1x-tamper2/PUBLISH-SCORE.md` (2984 bytes, sha256 `7efdb452ae384ef719376a9023552ed4b4fda3d23d02bf35bf083d4866f11ea8`)
- Full omitted list for this folder is in `OMITTED.tsv`.

## Notes

- Internal publication-scoring files (PUBLISH-SCORE.md) were left out.
