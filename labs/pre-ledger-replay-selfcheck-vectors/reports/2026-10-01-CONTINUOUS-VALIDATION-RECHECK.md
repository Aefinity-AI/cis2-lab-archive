# Re-check: cis2-spec docs/results/2026-09-27-CONTINUOUS-VALIDATION.md (2026-10-01)

Setup: fresh shallow clone of Aefinity-AI/cis2-spec @ 205b024 in the session scratchpad (not ~/projects). Same CPU as the report (i5-10210U, avx2/fma), same kernel string. Nothing changed in any repo. Corruption done on a copy inside the scratch clone only.
Runs: `bash scripts/cis2_monitor.sh` (8m00s wall, incl. weights fetch + cargo build) -> RESULT: PASS. Corruption phase run exactly as the report's commands.

## Claim table
| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| 1 | Host i5-10210U, ISA avx,avx2,fma,sse4_2, Linux 6.6.147 x86_64 | REPRODUCED (same machine) | log: `cpu_model: Intel(R) Core(TM) i5-10210U`, `isa_flags(relevant): avx,avx2,fma,sse4_2` |
| 2 | selfcheck "10 passed, 0 failed" | REPRODUCED | `== SUMMARY: 10 passed, 0 failed ==` |
| 3 | witness digest d82743059d1d...c9df | REPRODUCED, matches EXPECTED_DIGESTS.md line 25 (v0.3b block) | `CIS2_VERIFY3 digest=d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df` |
| 4 | argmax 0b9c8f3a...7aff | REPRODUCED, matches EXPECTED (line 22) | `CIS2_VERIFY3 argmax_digest=0b9c8f3ac90d...67aff` |
| 5 | table_digest 23c7bfaf...b35d | REPRODUCED, matches EXPECTED (line 20) | `CIS2_VERIFY3 table_digest=23c7bfaf5cef...06b35d` |
| 6 | inv_freq da9f6dcf...6f12 | REPRODUCED, matches EXPECTED (line 21) | `CIS2_VERIFY3 inv_freq_table_digest=da9f6dcf...` |
| 7 | generated_token_ids 28,665,...,351 | REPRODUCED, matches EXPECTED | identical 16-id list in log |
| 8 | model.safetensors sha256 80521b40...5da1 | REPRODUCED, matches pin | fetch `got=80521b40281d...55da1` |
| 9 | Two baseline runs 08:41/08:48 bit-identical | PARTLY: I ran one baseline (identical digests to the report); the 09-27 run times and second run are NOT CHECKABLE. Cross-day agreement is consistent with the claim. |
| 10 | printf \xff at offset 1000000 -> corrupted sha f262f76b...7493 | REPRODUCED | `f262f76b67887396a7c0de5e24d44eb4c72ec9fbcf6dbd3b978a1d40d87a7493  weights/model.safetensors` |
| 11 | Direct verify3 on corrupted file prints FATAL sha256 mismatch got=f262...7493, then `selftest=PASS ftz_daz=pinned` | REPRODUCED (rc=91) | `CIS2_VERIFY3 FATAL: model.safetensors sha256 mismatch, got=f262...7493` / `CIS2_VERIFY3 selftest=PASS ftz_daz=pinned`. Cosmetic: report wraps FATAL over two lines; real output is one line. |
| 12 | "refused to run forward pass" | REPRODUCED by source+output: hash check at verify3/main.c:99-112 precedes determinism/forward (l.138+); no digest line printed. |
| 13 | Fetch path re-downloads on corrupted file and self-check then PASSes | REPRODUCED for the fetch step only (ran fetch_weights.sh on corrupted copy): `Re-fetching model.safetensors (local copy does not match pin)` then sha back to 80521b40... I did not re-run a full selfcheck after that (monitor run was before corruption). The earlier-day ordering ("when run earlier") NOT CHECKABLE. |
| 14 | Restore sha 80521b40 | REPRODUCED (via re-fetch; I did not use the .bak path, trivial) |
| 15 | Monitor summary: PASS, digest_hint=6ebb67358c6bbab8, two runs 08:49:28 / 09:00:07 | REPRODUCED the PASS and the same hint; times NOT CHECKABLE | `20261001T055122Z  PASS  digest_hint=6ebb67358c6bbab8` |
| 16 | phase2_corrupt_verify3.log, monitor_logs on experiment host | NOT CHECKABLE (host-local; monitor_logs/ not in repo) |

## Problems / overstated claims
1. **digest_hint is not a model digest.** Script takes the last 16-64 hex string in the log. In the log that is the cargo test binary name `conformance_rope-6ebb67358c6bbab8` (a build hash). The report presents it in a "Monitor summary log" next to digests and says baseline digests were preserved; the hint says nothing about weights/outputs and would be identical under any weight state that still passes. It is also build-path/toolchain dependent. Should not be read as a digest.
2. **Monitor PASS is a grep on text.** RESULT is PASS iff log contains "PASS: all"; exit status of selfcheck is ignored for PASS. It checks selfcheck's self-reported digest comparison against the repo's own EXPECTED_DIGESTS.md, so "PASS" = repo-consistent, not independent.
3. **"Phase 3 PASS on restored clean stack" under-tests monitor failure behavior.** The monitor was never run on the corrupted file, so detection by the monitor (FAIL, exit 1) is not shown. Conclusion 4 ("treat FAIL as an incident") rests on an untested FAIL path. Also note selfcheck's fetch step self-heals a corrupted file, so the monitor would likely PASS after silently repairing; the incident is not logged as FAIL. This is the real gap: corruption is masked in monitor mode.
4. **"Silent weight changes are caught by the public tooling"** (Summary) is stronger than shown: one byte, one offset, one file (model.safetensors), caught by a sha256 pin. This shows the hash gate works; it is not new evidence about CIS-2 digests (the run never reaches logits). Config/tokenizer corruption, tampered pins/EXPECTED_DIGESTS.md, or tampered verifier binary were not tested.
5. **"Demonstrates operational continuous validation"** and "concrete public example of continuous validation of bit-identical inference integrity": no scheduling (cron/timer) was used; two manually invoked runs ~11 min apart. "Scheduled-style" is manual. No long-horizon or multi-host data. "Without GPUs or proprietary stacks" is true but not tested vs. anything.
6. "Baseline remained bit-identical across repeated self-checks": n=2 same host, same day (plus my cross-day run, consistent).
7. Phase 2 header "PASS (integrity failure detected)" mixes a pass/fail vocabulary; and the verifier prints `selftest=PASS` after FATAL, which a skim reader could misread.
8. Report was added without review; no claim was found false. Wording rules: "demonstrates" ok; no "first"/"proves"/"guarantee" seen.

## Suggested edits (for NEEDS if Justin wants)
- Remove or relabel digest_hint (or have monitor print the witness digest); state that it was a build hash.
- Add a monitor-mode corruption run with the fetch self-heal disabled, or document that monitor masks corruption.
- Soften "demonstrates operational continuous validation" to "exercised by hand".
