# rust-1

- Question (ledger title): rust-1: decode speed and memory on SmolLM2-135M: our Rust vs our C CIS-2 (IMPLEMENTATION), Rust+OpenBLAS vs PyTorch vs llama.cpp (FRAMEWORK), optional Rust engine (KERNELS)
- Why this is CIS-2 scope: CIS-2 implementation-language question (Rust vs C vs PyTorch for the CIS-2 runtime/training port)
- Verdict, as the ledger says: **MET** (ledger result row, 2026-10-04T14:02:12Z)
- Registered: 2026-10-04T00:34:55Z, bar_sha256 `c20822c4f8350a39749d481ce59ddb716c0c6f676a4a7162c5ff113fe74d6507`, git_head `234c44cc005aa06b75c583c908277691220527b7`
- Amended: 2026-10-04T09:17:01Z, bar_sha256 `a4f1a43eadcd8a9ab2e62c0e0e924d6fba865944418ae337a8bc68513dec6467`. Reason: NARROWING OF SCOPE: rust-1 becomes arm L alone (the IMPLEMENTATION answer, speed and memory), and the stage 2 arms G-OB, G-MKL, T, Q and X (the FRAMEWORK and KERNELS answers, Band W, their labels, expected values and sentences) leave rust-1 and move, with every threshold and INVALID condition unchanged, to a separately registered experiment rust-1b that has its own pass mark, is registered and public in the fingerprint ledger before any of its runs, and carries its own freeze sha256 in its own start --ref. This is a narrowing of scope and not just a change of "versions and hashes not yet known
- Started: 2026-10-04T09:25:49Z

## Ledger summary (verbatim from the result row)

IMPLEMENTATION: LEVEL (label from box1 alone, amended bar a4f1a43e). Speed: rs-gnu-O3 5.097 tok/s against c-gnu-O3 5.189 tok/s, r = 0.98235, inside the TIE band 0.95 to 1.05. The reps are separated (C above Rust in every rep, per-rep ratios 0.9817 to 0.9829) but the band decides. Memory: peak PSS 758,891 against 731,113 kB, m = 1.038, TIE; anonymous m = 1.036. 20 kept reps, 1 void repeated at the same position (cause not recorded), 0 discards; digests equal the reference before and after. LEVEL is recorded as met, as in rust-5: the bar is two-sided and has no met or not_met word. This is not a language verdict (tokenizer, KV layout, loader and allocator differ). Disclosures: the expected absolute levels were wrong (5.04 to 5.19 tok/s measured against 1 to 3.6 expected; 0.73 to 0.77 GB peak against about 0.55 GB expected, the transient 269 MB load buffer is in both peaks); CPUQuota 400 percent was non-binding (R5); read-only ssh sessions of another lab touched box1 from about 09:26 to 09:47Z, and the two reps in that window are not outliers; box2 INVALID (three discards); box3 NOT RUN (host given to another lab); box4 and box5 musl ratios carry no label (box4 rs-O2/c-O2 0.9457; box5 0.8917, O3/O3 1.0513); cargo closing lines were removed from four build logs by a later commit (43e2573), pinned commit 84ecf130 and the payload are unchanged; nine repository files including the freeze file were overwritten with merge-conflict markers by box1's state sync after the job ended, were restored byte for byte from 9b64dcfa, and the freeze file hashes again to 5d4af11c as in the start record (D1 of RESULT.md). Independent verifier: CONFIRMED.

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `reports/`: analysis reports, result files and key logs from the lab host.
- `results/`: result files named in the ledger result row.
- `plans/`: plan / bar files.

## Notes

- Large per-run stdout/stderr files were kept only when under the size cap; see the omitted list.
