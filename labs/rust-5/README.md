# rust-5

- Question (ledger title): rust-5: fp32 dense matrix-vector product, 4-row interleaved, Rust vs C same algorithm (LANGUAGE), library kernels as speed only (KERNELS)
- Why this is CIS-2 scope: CIS-2 implementation-language question (Rust vs C vs PyTorch for the CIS-2 runtime/training port)
- Verdict, as the ledger says: **MET** (ledger result row, 2026-10-04T08:20:59Z)
- Registered: 2026-10-04T00:34:55Z, bar_sha256 `2acf9b082b84700ad2541fec90a223b7a82f444c16dcadfd89c7aa71bcc32657`, git_head `234c44cc005aa06b75c583c908277691220527b7`
- Amended: 2026-10-04T02:34:03Z, bar_sha256 `376fa548ea2de9be9fc623ef5f95f17fa219bf2b1c74934d428809e7f3523b6d`. Reason: pins only: payload/source hashes, toolchain versions, wording readings from verifier START report; nothing relaxed
- Started: 2026-10-04T02:34:03Z

## Ledger summary (verbatim from the result row)

MET in the bar's sense LEVEL (a tie, not a Rust lead). LANGUAGE, box1 (labelled host, i5-5200U): Rust and C builds of the same fixed-order fp32 matrix-vector loop are inside the tie band on 5 of 5 shapes at both tiers (C/Rust median ratio 0.996 to 1.019 at T0, 1.002 to 1.040 at T1; rust_O3 against c_gcc_O2, 20 reps each, 0 discards); outputs bit-equal on all five hosts (350/350 on box1). KERNELS (speed only, different arithmetic): our loop is BEHIND OpenBLAS, torch MKL and ggml f32 on all 5 shapes on box1 (library time 0.37 to 0.83 of ours). Hosts without a label, ratios shown only: box4 (AMD Sempron) and box5 (Pentium T2310) Rust O2 took 8 to 40 percent less time than C; box2 attempt 2 inside the tie band; box2 attempt 1 and box3 INVALID (discard budget), nothing from them used. FRAMEWORK finding, no number: the stock torch 2.14.0+cpu process ended with Illegal instruction on the Celeron N4020 in 4 documented processes (cause not isolated; a linear-only probe ran). Disclosures: 103 reps on box1 flagged for another runnable task were kept as pin 8 says (dropping them moves no label); the pin-5 load reading replaces a literal clause that would void every host; the unit carried CPUQuota=400 percent (4 CPUs, one pinned thread, no real clamp, but not literally none); the harness wrongly turns a torch crash into a job FAIL; no 40-rep redo for one box4 shape; box2 attempt 1 rows lost; the bar file lacks the pins (ledger copy is authoritative). One kernel, five shapes, single thread, x86-64. Independent verifier recomputed every ratio: CONFIRMED.

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `reports/`: analysis reports, result files and key logs from the lab host.
- `results/`: result files named in the ledger result row.
- `plans/`: plan / bar files.
