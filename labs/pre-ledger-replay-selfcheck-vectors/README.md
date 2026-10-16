# pre-ledger-replay-selfcheck-vectors

- Scope: replayable evaluation bundle, self-checks on old CPUs, vectors, verify merge
- Verdict: **no ledger rows exist for these (they predate the experiment ledger, or were run as plain legs).** What each report says about itself is quoted below; this archive does not restate it as MET / NOT MET.

## Reports

- `reports/2026-09-17-cis2-vectors-2.md`: cis2-vectors-2: softmax_v1 and embed_lookup_v1 conformance vectors
- `reports/2026-09-17-cis2-verify-merge.md`: cis2-verify-merge — LAND THE CLEAN-ROOM VERIFIER
  - report states: All 5 values match EXPECTED_DIGESTS.md exactly. `cis2-verify verify` → PASS; `cis2-verify check` → all 9 clauses PASS, residual=none.
- `reports/2026-10-01-BOX4-SSE3-SELFCHECK.md`: box4 — CIS-2 v0.3b self-check on an SSE3-only x86-64 CPU: PASS
  - report states: Raw log: `state/reports/box4-selfcheck/RESULT.txt` (sha256 7d409d22069c8a4c…, 24 lines). Leg: `box4-selfcheck`
- `reports/2026-10-01-CONTINUOUS-VALIDATION-RECHECK.md`: Re-check: cis2-spec docs/results/2026-09-27-CONTINUOUS-VALIDATION.md (2026-10-01)
  - report states: Runs: `bash scripts/cis2_monitor.sh` (8m00s wall, incl. weights fetch + cargo build) -> RESULT: PASS. Corruption phase run exactly as the report's commands.
  - report states: Spec status line says "DRAFT, not frozen" (spec line 3). `S/docs/V04_OPEN_ITEMS.md` lists open work (op-level golden tier, issue #1).
- `reports/2026-10-01-SV2-REPLAY-AND-ATTACK.md`: sv-2: eval table a stranger can replay — outside-stranger half (in-house)
  - report states: checked sha256 against `MANIFEST.sha256` (match), built a venv, ran `harness.py`
- `reports/2026-10-01-cis2-spec-selfcheck-penguin.log`
- `reports/2026-10-04-SV2-REPLAY-AND-ATTACK.md`: sv-2: eval table a stranger can replay — in-house half (box3 redo/confirmation)
  - report states: confirmation, not a new result; line 48 is closed as a duplicate below.
- `reports/2026-10-16-W8-DENORMAL-FTZ-RUST2B.md`: W8: denormal/FTZ count on rust-2b checkpoints (box1)
  - report states: RESULT: OK, rows=20, failed=0). Format: raw flat little-endian float32,
- `reports/box4-selfcheck/RESULT.txt`
- `reports/box5-selfcheck/RESULT.txt`
