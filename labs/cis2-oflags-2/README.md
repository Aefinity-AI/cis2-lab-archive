# cis2-oflags-2

- Question (ledger title): CIS-2 C driver digests vs compiler vendor (clang 19 vs gcc 14.2, box5)
- Why this is CIS-2 scope: CIS-2 C driver digests vs compiler vendor
- Verdict, as the ledger says: **MET** (ledger result row, 2026-10-03T15:48:57Z)
- Registered: 2026-10-03T03:25:11Z, bar_sha256 `acf6f8d160e473237208e17d9e735dce926f65e6fbb47434ca04272f15adef4f`, git_head `11576b8729620c3061cdb05ee7936d2cae408a0a`
- Started: 2026-10-03T03:25:11Z

## Ledger summary (verbatim from the result row)

Met on box5 (Pentium T2310): gcc -O2 anchor, clang -O2, clang -O3 each match recorded box5 reference rows 100/100 on witness and argmax; clang -ffast-math control 0/100 witness (fired). One 135M model, 100 items, clang 19.1.7/gcc 14.2.0 only, x86 SSE -mno-fma; no claims beyond. Bar registered 10-03 03:25Z, run evidence post-dates it.

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `reports/`: analysis reports, result files and key logs from the lab host.
- `results/`: result files named in the ledger result row.
- `plans/`: plan / bar files.
