# rust-4

- Question (ledger title): rust-4: install footprint, cold start, offline build, byte-identical rebuild for Rust, C and the Python stack (MEASUREMENT)
- Why this is CIS-2 scope: CIS-2 implementation-language question (Rust vs C vs PyTorch for the CIS-2 runtime/training port)
- Verdict, as the ledger says: **INVALID** (ledger result row, 2026-10-04T21:32:39Z)
- Registered: 2026-10-04T00:34:55Z, bar_sha256 `e353091f3cd68da10187f24330af44a1a594e1e201b4510aab294caca08b29a3`, git_head `234c44cc005aa06b75c583c908277691220527b7`
- Amended: 2026-10-04T10:23:13Z, bar_sha256 `5ac441b761af7756e861ee8e77cf97c18526cedea2454975138456ed33d4acbd`. Reason: wording pins for the build (commit 9200d32894cad2e06580a44466c907fccb816939): programs, flags, M2 and M3 definitions, host reading, hygiene rules adopted from rust-1 (baseline-relative void limits, box1 timer pause); no band, line, host label or expectation changed
- Started: 2026-10-04T10:28:37Z

## Ledger summary (verbatim from the result row)

INVALID as a whole lab (nearest word under the bar's mapping: M2 hit the named INVALID condition 'cold cache not dropped' on every host that reached it and no redo ran; operator decision 2026-10-04 12:22Z: M2 gets its own registration, rust-4b). SUMMARY LINE: M1 RUST LARGER; M2 INVALID (cold cache not dropped, no label, no redo run); M3 RUST SLOWER BUILD; M4 C ONLY. Lines that stand on their own data: M1 IMPLEMENTATION (install size, same libc): the Rust static binary (cis2_ref, 3,826,304 bytes) is larger than the C static binary (verify3, 108,144 bytes), s=35.38; different implementations of CIS-2, not a language verdict. M3 TOOLCHAIN (offline build, box1, labelled host): cargo and rustc with 104 crates build slower than gcc with none, medians 190.556 s against 2.2037 s, t=86.47; not a language verdict. M4 TOOLCHAIN (rebuild identity): C ONLY rebuild byte-identically (6 of 6 C hashes equal, 6 different Rust hashes; the Rust files differ in 21 bytes, 20 of them the build id). Stack rows, FRAMEWORK (no-Python effect): installed Python stack 1,111,854,868 bytes, 290.6 times the Rust binary and 10,281 times the C binary; SURPRISE on the size words of the expectation. Python start: NOT RUN P start on box4 and box5 (Illegal instruction). Cold start: no statement for any program. box2 INVALID in the install phase (7 clock discards, budget 6), unlabelled host. Combination sentence not issued (M2 unlabelled). Nothing about LANGUAGE or KERNELS. Independent verifier recomputed every number (VERIFY.md): 9 minor corrections applied before recording, no label changed.

## Files

- `ledger.jsonl`: every ledger row for this id. Only machine-specific path strings were edited; the `bar` text is untouched and `sha256(bar) == bar_sha256` was re-checked for every row.
- `PREREG-from-ledger.md`: the registered (and amended) bar text, verbatim from the ledger.
- `reports/`: analysis reports, result files and key logs from the lab host.
- `results/`: result files named in the ledger result row.
- `plans/`: plan / bar files.

## Notes

- Large per-run stdout/stderr files were kept only when under the size cap; see the omitted list.
