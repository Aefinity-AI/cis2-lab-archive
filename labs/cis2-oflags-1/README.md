# cis2-oflags-1

- Question (ledger title): CIS-2 C driver digests vs compiler optimisation level (box5, gcc 14.2)
- Why this is CIS-2 scope: CIS-2 C driver digests vs compiler optimisation level
- Verdict, as the ledger says: **MET** (ledger result row, 2026-10-03T03:24:18Z)
- Registered: 2026-10-02T23:01:31Z, bar_sha256 `c4cd1a395a593cd12771762ba46b3b9c26c4227f498f6d0a451e97499786f554`, git_head `3964c31ed639161d81b2838878e175705c910eac`
- Started: 2026-10-02T23:01:31Z

## Ledger summary (verbatim from the result row)

CIS-2 C driver on box5 (Pentium T2310, gcc 14.2.0): witness+argmax digests identical to the recorded box5 reference rows for 100/100 items at -O0/-O1/-O2/-O3/-Os/-O3 -march=native with the spec flags; positive control -O2 -ffast-math changed the witness digest on 100/100 rows (argmax + verdict tokens unchanged), so the control fired. Seven distinct binaries, plan sha matches. Scope: one host, one compiler; cross-compiler test (clang) queued as cis2-oflags-2. Verified by cm-verifier from the raw rows on box5.

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `reports/`: analysis reports, result files and key logs from the lab host.
- `results/`: result files named in the ledger result row.
- `plans/`: plan / bar files.
