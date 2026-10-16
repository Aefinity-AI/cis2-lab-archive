# w3 analysis harness (lab registered, NOT started)

Spec: `state/prereg/w3-PREREG.md` (FROZEN rev 2, hash-pinned by cm-exp; never edited here). The harness is `run_w3.py`
(stdlib + numpy; numpy lives in `~/.venvs/w3`). It reads only the sv-5d `.npz` arrays under `~/sv5d/` (+ sidecar JSON),
imports neither `sv5d_compare.py` nor the recount script, and re-runs no model. Outputs go to `--out` and the harness
refuses a `--out` inside the repo.

Create the venv (once): `uv venv ~/.venvs/w3 && uv pip install -p ~/.venvs/w3/bin/python numpy`

    ~/.venvs/w3/bin/python state/labs/w3/run_w3.py --out DIR            # full analysis
    ~/.venvs/w3/bin/python state/labs/w3/run_w3.py --out DIR --smoke    # smallest pair only

Full run is memory-capped like the recount (PREREG s5):
`systemd-run --user --wait --collect --pipe -p MemoryMax=1500M -p MemorySwapMax=0 nice -n 10 ~/.venvs/w3/bin/python state/labs/w3/run_w3.py --out DIR`

## Function to PREREG step

| function | PREREG | what it does |
|---|---|---|
| `parse_manifest`, `verify_manifest` | Appendix A, step 7.1, s5 | parses the 14 sha256 lines out of the PREREG itself and hashes each file BEFORE it is read; mismatch/missing = cell excluded and listed |
| `main` (load loop) | s5 | excluded registered cell (R, B, X2, X3) = INCONCLUSIVE, no re-scan |
| `read_npz`, `load_cell`, `Layout` | s4 | arrays `ids` (top-1), `second` (top-2), `margins` (fp32 top-1 minus top-2), `index`; checks sidecar range, token count and windows sha; places every cell on one global position axis defined by the reference R (box1 B1T1 w0-7999; `.cN.npz` chunk files are never read) |
| `sanity_gate` | step 7.2, s4, s9 | R positions 1,664,964; R margin ==0 / <1e-5 / <1e-4 / <=5.722e-6 counts (1/12/123/10); per cell positions, flip table (window, position, R top-1, R top-2, R margin in 2^-20 units), exact-swap, largest margin shift; X tiles windows 0-7999; B=4 and X=3 flips. Any failure = INVALID |
| `compare_cell` | step 7.3(a),(c) | flip = own top-1 != R top-1; reference margin at each flip; per cell largest |own - R| margin shift, and per flip its shift and gap change |
| `tau_table` | step 7.3(b) | tau in {1e-6,1e-5,1e-4,2e-4,1e-3,1e-2,1e-1}: count and fraction of positions with R margin <= tau (a margin of exactly 0 counts) |
| `clopper_pearson_upper` | s8 | exact one-sided 95 % Clopper-Pearson upper bound on each fraction (bisection on the binomial cdf) |
| `bar` | s9 | cond_i: every counted flip has R margin <= 1e-2. cond_ii: count*100 < 1,664,964 (same as count <= 16,649) |
| output block in `main` | step 7.4 | `SHA256SUMS` of every output file plus the script |

Counted cells (the sv-5d bar): B = box1 B8T1; X = box2 B1T1 (w0-3999) + box3 B1T1 (w4000-7999). Reported but not in the bar:
T (box1 B1T2), box3 B8T1, penguin (both), box2 B1T2, box2 B8T1, box3 B1T2. `flips_total` counts flips over the counted cells
with multiplicity (a position flipping in both B and X counts twice: 7); distinct positions are in `result.json`.

## Output files (in `--out`)
`RESULT.txt`, `run.log`, `result.json`, `manifest_check.csv`, `flips.csv`, `tau_table.csv`, `cells.csv`, `SHA256SUMS`.

## RESULT line

    RESULT: OK w3 sanity=PASS|FAIL flips_total=N positions=N frac_recheck=F tau=T cond_i=MET|NOT cond_ii=MET|NOT verdict=MET|NOT MET|INCONCLUSIVE|INVALID manifest_sha_ok=yes|no

`frac_recheck` is the fraction of R positions with margin <= tau (tau = 0.01). `manifest_sha_ok=yes` only if all 14 files
verified (full run) or all files the smoke run reads verified. Verdict order: registered cell missing/excluded =
INCONCLUSIVE; else sanity FAIL = INVALID; else MET only if cond_i and cond_ii; else NOT MET.

## --smoke
Loads only the reference file `box1/B1T1_0-8000/p0of2.npz` (windows 0-3999) and cell T `box1/B1T2_0-2000/p0of1.npz`
(windows 0-1999), runs the T-scoped sanity checks, and prints the line prefixed `SMOKE: `. Its `positions` and
`frac_recheck` are over the reference file's 4,000 windows, and its verdict is always INCONCLUSIVE (registered cells
absent). It is a code-path check, not a result.

## PREREG ambiguities and how they were read
- s9 "every flip in every counted registered cell": counted = B, X (bar cells); T/S/extras reported only (PREREG s4 says so).
- s9 INCONCLUSIVE vs INVALID when both could apply: missing cells are tested first (no data to run the gate on).
- s9 "reference margin <= 1e-2": the fp32 margin is widened to float64 and compared with the float64 literal 0.01.
- s7.3(c) "the shift they needed": reported as |own margin - R margin| and as the gap change (R margin + own margin for a swap).
- s5 "sidecar sha256 differs from the report": the sidecars hold a windows hash, not file hashes; the harness checks each
  sidecar's windows_sha256 against the report's value, and file hashes against Appendix A.
