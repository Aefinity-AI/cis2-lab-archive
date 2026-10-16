# w1x-tamper

- Question (ledger title): w1x-tamper: real-weight tamper detection on the pinned SmolLM2-135M safetensors (1-ULP element edits, INT8 round-trip of one tensor, single random bit flips, header-only control)
- Why this is CIS-2 scope: CIS-2 real-weight tamper detection v1
- Verdict, as the ledger says: **NOT MET** (ledger result row, 2026-10-16T10:07:18Z)
- Registered: 2026-10-16T08:53:53Z, bar_sha256 `8aba0ae152d2c31a543fe0f1bcba1aa507cd3c6ded3a63be951dbd13a717ae4b`, git_head `0438bbf5392444462a420006315769e74efe38b2`
- Started: 2026-10-16T08:59:12Z

## Ledger summary (verbatim from the result row)

Scored against the frozen bar as registered. Data-mutation clauses MET on both hosts (w3 seed 20261016, w4 seed 20261017): sha256 moved 54/54, witness moved 54/54 (1-ULP 24/24, INT8 6/6, random bit flips 24/24; sign/exponent flips 11/11 and 13/13). Control clause NOT MET: the header-only control moved the witness on both hosts because the §12.1 witness header folds weights_sha256 (verified on hq: tokens and argmax digest identical, witness moved). The bar mis-specified the control; corrected design = w1x-tamper2. Explanation: state/reports/2026-10-16-CIS2-TAMPER-META-CONTROL-RESOLVED.md. Mutant files private.

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `results/`: result files named in the ledger result row.
- `feed/`: job scripts and RESULT.txt files from the fleet job runner (per host).

## Notes

- Internal publication-scoring files (PUBLISH-SCORE.md) were left out.
