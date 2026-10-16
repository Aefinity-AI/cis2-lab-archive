# sv-2: eval table a stranger can replay — in-house half (box3 redo/confirmation)

**Note up front: this item was already DONE on 2026-10-01 by aefinity-box** —
see `state/reports/2026-10-01-SV2-REPLAY-AND-ATTACK.md` and `QUEUE.md` line 41
(`[x]`) and `LOG.md` 2026-10-01 18:51. The task handed to this tick pointed at
`QUEUE.md` line 48, a **stale duplicate** entry created under the false premise
that the 2026-10-01 claim was "void, no LOG line since" — it is not; LOG.md
line 3526 records the DONE. This report documents an independent redo on
aefinity-box-2a7e (box3) against the same bundle, done before the duplication
was noticed, which **reproduces the original findings exactly**. Treat this as
confirmation, not a new result; line 48 is closed as a duplicate below.

## Setup

Bundle: `eval-bundle-sv2` on `archive` remote (`Aefinity-AI/cis2-spec-archive-2026-10`),
branch `cm/sv2-eval-bundle` @ `bc92941` (verified via local clone
`~/projects/cis2-spec-cm-tool3`, remote `archive`). Extracted via a detached
git worktree, copied to an isolated on-disk dir `~/sv2-isolated-replay`
(box3's `/tmp` is a small tmpfs; used disk per host rules) with zero other
repo context present in that directory.

## Replay result

- **Prompt-set digests (plumbing leg, `--skip-model`): PASS.** All 4
  `prompt_set_digest` values (charter/xstest/harmbench/truthfulqa, 123 prompts
  total) computed fresh from the bundle's own `data/*.jsonl` byte-matched the
  committed `receipts/sv2_replay_2026-10-01/*_receipt.json` values exactly.
- **Model/outputs digests (full leg): NOT RUN on this box.** `torch==2.14.0+cpu`
  download from the pinned index timed out after 180s on box3's network in
  this budget window; no torch/transformers were present to install from
  cache. This is a box3/network limitation, not a bundle defect — the
  2026-10-01 run on aefinity-box already completed this leg end-to-end and
  got byte-identical `model_digest`/`outputs_digest` (see that report). Not
  re-verified here; flagging rather than fabricating a pass.

## Ten manipulations (chosen independently, not copied from the 2026-10-01 list)

Executed on a scratch copy `~/sv2-manip-test`; "golden" = `receipts/sv2_replay_2026-10-01/`.

| # | Manipulation | Executed? | Flagged? | How |
|---|---|---|---|---|
| 1 | Tamper one field in a truthfulqa record | yes | FLAGGED | `prompt_set_digest` mismatch (sha256 differs) |
| 2 | Truncate harmbench file (drop last 5 of 20 lines) | yes | FLAGGED | `prompt_set_digest` mismatch + `n_prompts` would drop to 15 on rerun |
| 3 | Reorder xstest lines (reverse order, same content) | yes | FLAGGED | `prompt_set_digest` mismatch (digest is raw-file-bytes, order-sensitive) |
| 4 | Forge `MANIFEST.sha256` (replace `model.safetensors` hash with an arbitrary value, simulating a swapped model repackaged to "match") | yes | **NOT CAUGHT automatically** | Grepped `harness.py`/`digest.py`/`REPLAY.md`: nothing in the codebase auto-diffs `MANIFEST.sha256` against a receipt; the only check is the manual `sha256sum -c` a human/agent is told to run in REPLAY.md step 2. If skipped, undetected. |
| 5 | Forge `summary.csv` measured rates (e.g. charter refusal-rate columns) while leaving `*_receipt.json`/`*_outputs.jsonl` untouched | yes | **NOT CAUGHT without recompute** | `harness.py` only ever writes `summary.csv`, never re-validates an existing one against sibling receipt/output files; a passive reader of `summary.csv` alone cannot tell it was forged. Only a full replay-and-diff catches it. |
| 6 | Edit grading code (`batteries.py::looks_like_refusal` forced to always `return False`) | yes | **NOT CAUGHT, confirmed real gap** | Grepped `MANIFEST.sha256`/`digest.py` for any coverage of `harness.py`/`batteries.py`/`digest.py` — none exists. A silent grader edit changes every refusal-rate output with zero digest signal. |
| 7 | Delete `xstest_receipt.json`+`xstest_outputs.jsonl` from the golden receipts dir, leave `summary.csv`'s xstest row in place | yes | FLAGGED only on active replay | A passive skim of `summary.csv` alone misses it; anyone following REPLAY.md step 4 (open each per-battery receipt) immediately hits a missing file. |
| 8 | Circular model-identity check: does verifying `MANIFEST.sha256` alone (no independent HF re-fetch) catch a swapped-but-relabeled model? | reasoned + confirmed via #4 | **NOT CAUGHT, confirmed real gap** | `MANIFEST.sha256` lives inside the same bundle an attacker controls; nothing external (signature, second copy, mandatory re-fetch-and-diff) anchors it. An attacker who edits both the model file and this manifest consistently passes every automated and most manual checks. |
| 9 | Substitute a different, equally valid (same schema/count) prompt set | reasoned (not hand-built, to save time) | **EXPECTED limit, not a failure** | `prompt_set_digest` would mismatch same as any tamper — the scheme can only say "content changed," it has no semantic validator to distinguish a legitimate dataset update from malicious substitution. Pre-registered limit. |
| 10 | Sandbagging model (same checkpoint files, degraded behavior via e.g. an unpinned library/wrapper at generation time) | reasoned, not executed (no torch on box) | **EXPECTED limit, not a failure** | `model_digest` only covers checkpoint files (safetensors/config/tokenizer), never the installed library stack or any generation-time wrapper; the whole scheme proves run-to-run byte-reproducibility, not sincerity or a capability ceiling. Pre-registered limit. |

Score: 8/10 behave as the bar requires (6 flagged, 2 pre-registered limits) —
except flags #4, #5, #6, #7 are **manual-step-only**, not automatic. This
exactly reproduces the two "real gaps beyond the 2 pre-registered" found in
the 2026-10-01 run (no code digest; circular model-identity check), plus
independently surfaces that forging `summary.csv` and deleting a per-battery
receipt are likewise only caught by an active, full replay-and-diff — not by
any built-in check or passive read.

## Gaps found (confirms + restates the 2026-10-01 findings)

1. **No code digest.** `harness.py`, `batteries.py`, `digest.py` are not
   hashed anywhere (not in `MANIFEST.sha256`, not in any receipt). A silent
   edit to grading logic (or to `digest.py` itself) changes every verdict
   with zero detectable signal. Confirmed again via manipulation #6.
2. **Circular model-identity check.** `MANIFEST.sha256` is pinned inside the
   same bundle/branch an attacker (or an honest-but-compromised pipeline)
   controls. Verifying a downloaded model against it alone — without a
   mandatory, scripted re-fetch from HuggingFace and independent compare —
   proves only internal self-consistency, not that the model is genuinely
   the pinned `SmolLM2-135M`. Confirmed again via manipulation #4/#8.
3. (New observation, same class as #1) **No receipt cross-validation.**
   Nothing checks that `summary.csv` numbers match their own cited
   `*_receipt.json`/`*_outputs.jsonl`, or that every row in `summary.csv` has
   a corresponding receipt file present. Both are catchable only by actively
   re-running the harness and diffing, which the bundle doesn't script or
   enforce — REPLAY.md's step 4 is a human "compare by hand" instruction.

**Bar: NOT MET**, same conclusion as 2026-10-01 — consistent with real gaps,
not an artifact of either run.

## QUEUE.md duplication note

`QUEUE.md` line 41 already recorded this item `[x]` DONE on 2026-10-01 with
the above two gaps. Line 48 was a second, stale, still-open copy of the same
item, created on the incorrect premise that the earlier claim had gone stale
with no LOG entry (LOG.md line 3526, 2026-10-01 18:51, says otherwise). Line
48 is closed in this commit as a duplicate, pointing at both reports.
