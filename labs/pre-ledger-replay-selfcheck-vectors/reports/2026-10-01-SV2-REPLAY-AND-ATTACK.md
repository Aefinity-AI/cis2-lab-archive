# sv-2: eval table a stranger can replay — outside-stranger half (in-house)

Bundle: `eval-bundle-sv2` (cis2-spec branch `cm/sv2-eval-bundle`, archive remote,
commit `bc92941`), copied to an isolated dir `<home>/sv2-isolated/` and handed
to two fresh subagents with zero other project context.

## Replay (fresh subagent, no other context)

Followed `REPLAY.md` verbatim: fetched SmolLM2-135M weights from HuggingFace,
checked sha256 against `MANIFEST.sha256` (match), built a venv, ran `harness.py`
on all 4 batteries (123 prompts). **All digests matched the golden receipt**:
`model_digest` MATCH, `prompt_set_digest` x4 MATCH, `outputs_digest` x4 MATCH,
`summary.csv` byte-identical. ~10 min CPU wall time.

Doc issues found (real stranger would hit these):
- REPLAY.md's single `pip install torch==... transformers==... --index-url
  pytorch-cpu-index` fails as written — only `torch` is on that index; needs
  two separate installs.
- REPLAY.md suggests building the venv under `/tmp`; on tmpfs-backed `/tmp`
  hosts this risks OOM/ENOSPC and isn't warned about.

Both are documentation fixes, not scheme failures.

## Ten blind manipulations (second fresh subagent, public docs only)

| # | Manipulation | Result |
|---|---|---|
| 1 | Edit one prompt's text post-hoc | FLAGGED (prompt_set_digest) |
| 2 | Forge summary.csv rates, leave outputs.jsonl alone | FLAGGED only if someone recomputes by hand — not automatic |
| 3 | Truncate prompt set | FLAGGED (digest + n_prompts) |
| 4 | Quietly edit grading code (batteries.py) | **UNDETECTED** — no digest covers the harness/grader code itself |
| 5 | Reorder prompts, same content | FLAGGED (raw-byte file hash is order-sensitive) |
| 6 | Replay on an undeclared different runtime | FLAGGED only if someone diffs digests by hand; nothing asserts installed versions |
| 7 | Craft text to fool the keyword grader | **UNDETECTED** — digests reflect the real text, but the pass/fail label is a substring heuristic with no digest coverage |
| 8 | Swap model weights, doctor MANIFEST.sha256 to match | UNDETECTED against the bundle's own manifest (circular); FLAGGED only by independently re-fetching from HF |
| 9 | Swap in a different, equally valid prompt set | UNDETECTED — **expected pass**, known limit |
| 10 | Simulate a sandbagging model (test-aware behavior change) | UNDETECTED — **expected pass**, known limit; harness has no channel to compare test vs. deployment behavior |

## Real gaps (not the two expected limits)

1. **No code digest.** `harness.py`/`batteries.py`/`digest.py` are not hashed
   anywhere; a silent edit to grading logic changes verdicts with zero
   detectable signal (#4, #7).
2. **Model-identity check is circular** unless the verifier independently
   re-fetches the weights from HuggingFace and compares — `MANIFEST.sha256`
   living inside the bundle doesn't stop a doctored bundle (#8).

Suggested fix (not yet implemented, needs a bundle-format revision): add a
`code_digest` (sha256 of the three .py files) to every receipt, and make the
HF re-fetch-and-compare step a scripted, mandatory part of replay rather than
an optional manual instruction in prose.

## Verdict vs. the sv-2 bar

Bar was: "all digests match, every other manipulation flagged." 8/10 flagged
or expected; 2/10 unexpectedly undetected (#4 code-digest gap, #7 grader
heuristic gap) — both real findings, not the two pre-registered expected
passes (#9, #10). **Bar not fully met** — report honestly as a harness
limitation, not a false "PASS".

Outside-stranger (human volunteer, not a subagent) half is still open —
tracked in NEEDS.md.
