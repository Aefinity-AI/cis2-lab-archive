# w1x-opencl

- Question (ledger title): w1x-opencl: CIS-2 OpenCL backend reproduces the pinned 16- and 128-token digests on pocl (CPU), NVIDIA OpenCL and an Intel HD 630 iGPU (non-NVIDIA GPU) with software div/sqrt
- Why this is CIS-2 scope: CIS-2 OpenCL backend
- Verdict, as the ledger says: **MET** (ledger result row, 2026-10-16T10:54:39Z)
- Registered: 2026-10-16T10:18:58Z, bar_sha256 `953b004fcbdbe3172b9a3650526ce9bc5c436245dd22d69345635ea5ea933d57`, git_head `c086b49e290fda2a8704f44d340738e9a81f967d`
- Started: 2026-10-16T10:27:17Z

## Ledger summary (verbatim from the result row)

MET on the r2 legs (2026-10-16 10:43-10:49Z). hq (C, i7-7700HQ): host g++, pocl, pocl soft, NVIDIA OpenCL (GTX 1050) and Intel HD 630 via rusticl with soft div/sqrt all reproduce the pinned 16-token (twice, repeat-exact) and 128-token digests; gpu/test_soft PASS on pocl, NVIDIA and HD 630; weights 80521b40 / ids 4b6618b6 confirmed. Negative control: HD 630 hardware div/sqrt DIVERGE at 16 tokens as expected (not in the bar). Beyond the bar: w3 (A) and w4 (H) Intel UHD 600 via rusticl soft div/sqrt MATCH 16+128, test_soft PASS, hw control DIVERGE; w1 (B) run 1 host/pocl/pocl_soft/RTX 2070 OpenCL MATCH 16+128 (its UHD 630 row queued as cis2-opencl-w1-r2). Disclosure: run 1 (10:32-10:35Z) on every host produced no iGPU row because the cm user manager lacked the render group (rusticl listed no device; the template skipped the row); logged as an infrastructure failure, access fixed (render/video groups + ACL on the DRM render node), re-run as -r2 with the bar unchanged. All three Intel iGPUs' hardware div/sqrt runs produced the same divergent digest 8322617c… (informative).

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `results/`: result files named in the ledger result row.
- `feed/`: job scripts and RESULT.txt files from the fleet job runner (per host).
- `plans/`: plan / bar files.

## Omitted from this folder (size or type); sha256 recorded so the originals can be matched

- internal publication-scoring record (out of scope): 1 files, 0.0 MB total. Examples:
  - `state/reports/w1x-opencl/PUBLISH-SCORE.md` (2737 bytes, sha256 `ea290bb101bbbaa36edf8241d7ca862a4511e0ec3432d6cc24cf2dbfb2e3db16`)
- Full omitted list for this folder is in `OMITTED.tsv`.

## Notes

- Internal publication-scoring files (PUBLISH-SCORE.md) were left out.
