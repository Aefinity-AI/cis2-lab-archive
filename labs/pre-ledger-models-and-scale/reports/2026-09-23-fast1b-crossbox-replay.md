# fast-1b: cross-box replay of KV-cache decode fix (cis2-spec verify3/)

Date: 2026-09-23
Branch: cm/fast1-deterministic-speed, commit babdd71ddbfe10cfe6ac3f86e9e813477e9dd74a

## Result: MATCH — merged

Digests replayed byte-identically on two independent machines, one with
AVX2/FMA and one without.

### box1 (aefinity-box, this box, local)
```
witness digest: d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df
argmax digest:  0b9c8f3ac90d0b9cd5f1719ac327dca1fc639fd87468305fccebbe3d56f67aff
table digest:   23c7bfaf5cef0095fd021af2eb1808abb4928bae4219756d86bdac670a06b35d
invfreq digest: da9f6dcfde0425588815509e874515cdcd3d6b8818b6d0136590052e7bbf6f12
generated_token_ids: 28,665,436,253,1838,8180,3365,14176,30,2306,4161,281,253,2066,2291,351
self_check.sh: PASS
```

### box2 (w3, Intel Celeron N4020, no AVX2/no FMA)
```
witness digest: d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df
argmax digest:  0b9c8f3ac90d0b9cd5f1719ac327dca1fc639fd87468305fccebbe3d56f67aff
table digest:   23c7bfaf5cef0095fd021af2eb1808abb4928bae4219756d86bdac670a06b35d
invfreq digest: da9f6dcfde0425588815509e874515cdcd3d6b8818b6d0136590052e7bbf6f12
generated_token_ids: 28,665,436,253,1838,8180,3365,14176,30,2306,4161,281,253,2066,2291,351
self_check.sh: PASS
FMA gate (objdump): PASS (0 matches)
```

All four digests and generated_token_ids identical, byte-for-byte, on both
machines. This confirms the KV-cache incremental decode change in
verify3/model.c is a pure recompute-elimination — no change in
floating-point operation, accumulation order, or transcendental route.

Note: box2 checkout was set up as a git worktree
(`~/projects/cis2-spec-fast1-box2`) alongside the pre-existing base repo
(`~/projects/cis2-spec` on box2, which had a different branch checked out),
tracking `origin/cm/fast1-deterministic-speed`. Reused box2's existing repo
remote rather than a fresh clone.

## PR / merge

- PR: https://github.com/Aefinity-AI/cis2-spec/pull/35
  "verify3: KV-cache decode fix (removes O(n^2) recompute)"
- Body per policy: no timing/tok-per-second numbers in PR title or body.
- CI (workflow `verify.yml`, 30 check runs: cis2-verify, conformance,
  demo-quickstart, intermediates x20, reference, verify2, verify3 gcc/clang,
  on both x86_64 and aarch64): all 30 checks PASS.
- Merged via squash. Merge commit: c98d4386542ea731af2e357f2c5abce9a53f86b9
  Merged at 2026-09-23T23:47:30Z.

## Timing numbers (not for the public repo, informational only here)

- box1 (aefinity-box): ~0.63 tok/s before, ~3.6 tok/s after (~5.7x), per the
  original commit message on cm/fast1-deterministic-speed.
- No independent timing measurement was taken on box2 this run (only
  correctness/digest replay was required and performed); box2 is a
  Celeron N4020, much slower absolute hardware, and was used only to
  confirm bit-exact digests on a non-AVX2/FMA path, not for a timing claim.

## Status

- cis2-spec main now contains the KV-cache decode fix.
- No BLOCKERS or NEEDS follow-up required — gates held, digests matched,
  CI green, merged under standing authorization.
