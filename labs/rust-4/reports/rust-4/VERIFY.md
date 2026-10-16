# rust-4 RESULT.md verification (independent recompute, 2026-10-04)

Verdict: CORRECTIONS NEEDED (minor; no label, band, host rule or sentence is wrong).

## Recomputed and matching (from raw folders, not scratch scripts)
- Bar hash: bars/rust-4.txt (trailing newline stripped) + "\n\n" + PINS.txt (trailing newline stripped) = 5ac441b761af7756e861ee8e77cf97c18526cedea2454975138456ed33d4acbd = ledger amended record (also equals bar_sha256 field; 22197 chars).
- M1: R 3,826,304 B, C 108,144 B (result.json m1_bytes_shipped, all 5 hosts; sha256 = pins appendix B, = bin/ files); s = 35.3816 -> RUST LARGER. 3.649 MiB. Venv 1,111,854,868 B (290.58x R, 10,281.2x C), .so 550,024,256 (143.75x, 5086.0x), 35 pkgs, 4,314,098 .py lines.
- M3 box1 (rows.jsonl phase m3): R 219.634/189.739/190.556 s, C 2.604/2.204/2.204 s; medians 190.556/2.2037; t = 86.470 (86.46 only if C is rounded to 2.204; rj rounded gives 86.62); per-rep range 72.86 to 99.65; all KEPT, rc 0, foreign load inside 0.0315/0.1, thr 0, scaling unchanged, 176-188 clamp samples per R rep, 1-2 per C rep; RSS 727,196/724,980/721,548 kB; load before 0.26-0.29, after R 1.10-1.16, after C 0.35/0.35/0.29.
- P install: box1 73.66/63.46/65.65 (median 65.65); box3 73.68 (3 discards); box4 132.43 (2); box5 161.43 (0); box2 7 discards, none kept (clock 51.4-71.3 percent below ref 2784 MHz, thr 0).
- M4: penguin R 2e3c8934... / c5d09b9c..., box1 R 84264575... / b82b21b7... (+ build 3 fa5008ce...): all different; C 5a6ccc32... in all 6. Toolchain equal (rustc commit 88d9e12ae..., gcc 14.2.0-19, musl-tools 1.2.5-3.1~deb13u1). Label C ONLY correct. Diagnostic re-done on penguin: 21 differing bytes = 20 build-id bytes at 640-659 + 1 byte at 2,618,916 (digit in embedded /home/.../m4build/p1/R path, strings offset 2618863); build ids f2f519e1... vs cdf6c367.... Correct.
- M2 cache table: all 16 fall percentages recomputed and equal; box1/3/4/5 each 3 consecutive failures (C, then P or Rv/Cv); box2 ended INVALID in install (7 discards > budget 6) before M2. Report gives no M2 label, no ratio, withholds the lone R rep honestly. No redo job exists in state/feed (only rust4-box1..5); LOG 12:22 says M2 stays NOT RUN.
- Discards 3/7/6/5/3, voids 0, elapsed 1771/1241/1133/950/530 = 5625 s; feed push to harvest 6535 s; baselines/limits; wrapper, run.py, payload hashes; timers_paused=restored; wheelhouse hash 21360ef9... (34 wheels, 249,362,583 B) all equal.
- M5: 104 packages in Cargo.lock (103 vendor dirs, 3,808 .rs files), program 1,868 lines, C 2,415 lines in 11 files, audit data absent. P packages 35 (<50) -> SURPRISE correct.
- Sentences: M1, M3, M4 are exact bar templates; M2 correctly unfilled; no "Rust wins/loses" anywhere; LANGUAGE/KERNELS stated as not answered.

## Corrections (most serious first)
1. M5 vendored line count (RESULT.md section 2 M5 table; section 7 item 14): written 1,919,375 and 1,921,243; `wc -l` on the 3,808 vendor .rs files gives 1,919,373 and total 1,921,241 (python splitlines counts 2 extra separators; the bar says wc -l). Source: ~/feed-payload/rust4/src/R/vendor.
2. Summary line (section 6): bar's own word for a failed cold-cache check is INVALID, not NOT RUN. Replace with: "SUMMARY LINE: M1 RUST LARGER; M2 INVALID (cold cache not dropped, no label, no redo run); M3 RUST SLOWER BUILD; M4 C ONLY." (Keep "NOT RUN" in the sentence list as the reason text.)
3. Ledger word (section 6): the report leaves two readings open. Replace by: "Ledger verdict word: invalid. M2 hit a named INVALID condition (cold cache not dropped) on every host that reached it; the bar's redo clause cannot change that under the frozen runner (operator decision LOG 2026-10-04 12:22: no redo under rust-4, own registration instead). met needs a label on M2 and is not available; inconclusive triggers (TIE NOT SEPARABLE, musl-gcc missing) did not occur; not_met is unused. The bar text strictly says 'after one redo'; none ran, so this is the nearest word, recorded with that note."
4. Combination rule (section 6): do not give two readings. Replace with: "Combination sentence not issued as a finding: M2 is unlabelled, so the rule cannot be fully applied. For the record only: M1 RUST LARGER, M3 RUST SLOWER BUILD, M4 C ONLY match the bar's 'Rust adds nothing over C here' branch, an IMPLEMENTATION and TOOLCHAIN caveat sentence, tagged 'M2 INVALID'."
5. Section 5 Python-size row: replace the hedge with "SURPRISE on the size words (1,111,854,868 B = 1.11 GB is not 'hundreds of MB'); the ratio clause (more than 100 times either) held."
6. Section 7 item 17 / header: replace "bars/rust-4.txt + blank line + PINS.txt" with "bars/rust-4.txt and PINS.txt, each with trailing newlines stripped, joined by one blank line (22,197 characters)"; the plain concatenation does not hash to 5ac441b7.
7. Header line 3: the registration cost field reads "CPU only, about 2 box-hours" (ledger), not the paraphrase written.
8. Section 3 last bullet / item 16: add "the lone R rep (box1 15.8065 s to exit) is in result.json m2.values_exit_s and timed/m2-R-1.out of the raw folders; it is not a result (no C partner, no ratio) and is not used."
9. Section 3: add that the box1 M2 label cell is also M2 INVALID (labelled host), and box2 has no M2 line at all (install INVALID first).

## Ledger verdict word: invalid (reasons in correction 3).

## Headline
On the lab's main test machine the Rust program file is 3,826,304 bytes against 108,144 for the C one (35 times larger) and takes a median 190.6 s to build offline against 2.2 s (86 times longer); the C program rebuilt byte for byte identically in all six builds while the Rust program gave a different file every time. Cold-start speed was not measured because the test's cache-clearing check failed on every machine, and the Python stack is 1.11 GB installed (291 times the Rust file).
