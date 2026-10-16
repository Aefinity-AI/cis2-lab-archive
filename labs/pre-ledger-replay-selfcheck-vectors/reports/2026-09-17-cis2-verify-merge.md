# cis2-verify-merge — LAND THE CLEAN-ROOM VERIFIER

2026-09-17, aefinity-box2, cm-builder.

PR #4 (cm/cis2-verify-standalone) on cis2-spec, open since 2026-09-09, merged to main.

## Rebase
Clean. 37 commits rebased onto origin/main (advanced 5 commits since PR opened, through `cdefd27`). No conflicts.

## Tests (`cargo test --release` in cis2-verify/)
- lib.rs unit tests: 55 passed, 0 failed
- tests/compare.rs: 8 passed, 0 failed
- tests/detokenize.rs: 7 passed, 0 failed
- tests/end_to_end.rs: 6 passed, 0 failed
- **Total: 76 passed, 0 failed** (PR body's "34 tests" was stale — actual suite is larger, all green; includes the argmax-insufficiency regression test `strictly_stronger_tests::the_witness_chain_separates_runs_the_argmax_digest_cannot`)

## Digest verification against EXPECTED_DIGESTS.md §13.1
Ran `cis2-verify run weights` against the pinned SmolLM2-135M artifacts (sha256-verified download via scripts/fetch_weights.sh):

```
digest=d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df
argmax_digest=0b9c8f3ac90d0b9cd5f1719ac327dca1fc639fd87468305fccebbe3d56f67aff
table_digest=23c7bfaf5cef0095fd021af2eb1808abb4928bae4219756d86bdac670a06b35d
inv_freq_table_digest=da9f6dcfde0425588815509e874515cdcd3d6b8818b6d0136590052e7bbf6f12
generated_token_ids=28,665,436,253,1838,8180,3365,14176,30,2306,4161,281,253,2066,2291,351
```
All 5 values match EXPECTED_DIGESTS.md exactly. `cis2-verify verify` → PASS; `cis2-verify check` → all 9 clauses PASS, residual=none.

## CI
PR body's "10-job dual-ISA CI" claim didn't match current repo state — actual workflow ran 31 jobs (cis2-verify ×2 x86_64/aarch64, conformance ×2, intermediates ×22, reference ×2, verify2 ×2, verify3 ×4). All 31 passed (`gh pr checks 4` exit 0, no pending/failing).

## Merge
Squash-merged (matches repo convention). Force-pushed rebased branch first (feature branch only, main untouched pre-merge).
- Merge commit: `a5421ef` — "Add cis2-verify: standalone verifier built from the spec text alone (#4)"
- PR: https://github.com/Aefinity-AI/cis2-spec/pull/4 (MERGED 2026-09-17T12:36:44Z)
- origin/main confirmed at `a5421ef`

## Non-blocking nit
PR description said "34 tests"; actual is 76. No action needed unless echoed elsewhere (e.g. README).

**No BLOCKERS.md entry needed** — clean rebase, all gates green.
