# E15h — verify2 vs CIS-2 v0.2: MATCH

A headless tick completed E15h on `origin/cm/e15h-ref-fixes` (repo:
private `Aefinity-AI/cis2-fp`): spec v0.2 folds `table_digest` +
`inv_freq_table_digest` into the CIS2_REF witness header, uses raw
32-byte digest hashing (not hex-ASCII), and generalizes RoPE via
config-driven `math::ln_pinned(rope_theta)`. New reference digest:
`CIS2_REF = a0c563ef804f...5d6261da`.

This tick applied the same spec-driven changes to `verify2/` (clean-room
#2 crate) on branch `cm/e15h-verify2-v0.2`, without opening `src/`.
CI (`e15g-cleanroom-v2.yml`, run 33194049057) PASSED on both x86_64 and
aarch64: `CIS2_VERIFY2 digest`, `argmax_digest`, `table_digest`, and
`inv_freq_table_digest` all match the reference's v0.2 values bit-for-bit.

A duplicate/parallel session also started this same task under branch
`cm/e15h-spec-v0.2` (worktree race — same path got repointed to
`cm/e15h-ref-fixes` mid-session by the headless tick); that WIP was
recovered and pushed to `origin/cm/e15h-spec-v0.2` for the record but is
now superseded — no further action needed on it.

Remaining for whoever owns E15h next: `docs/CIS2_SPEC_v0.2.md` (the
formal spec doc bump) doesn't exist yet, only `docs/E15h_REFACTOR_v0.2_RESULT.md`.
E15d(a)/(b)/(c) workflows have not yet been re-run against v0.2.
