# E15e clean-room read log (files read, in order)

1. `docs/design/CIS2_FP_RECEIPT_DESIGN.md` — attempted; **does not exist** in
   this repo (any branch). See `verify/SPEC_GAPS.md` item 0.
2. `docs/E15b_REFERENCE_RESULT.md` (this repo, working tree at
   `origin/cm/e15c-cross-isa` = commit f83e8dd) — read in full.
3. `docs/E15c_RESULT.md` — **not present in the working tree** of
   `origin/cm/e15c-cross-isa` (f83e8dd). Retrieved via
   `git show 05187dc:docs/E15c_RESULT.md`, a commit reachable only from a
   local branch ref (`cm/e15c-cross-isa`) that is *ahead of* origin's
   current tip of the same branch name — origin's `cm/e15c-cross-isa` was
   reset backward at some point after 05187dc was pushed, dropping the
   E15c result commit from the remote branch (still present in this
   clone's local objects/refs). See `verify/SPEC_GAPS.md` item 0 for the
   process note. Content used: preregistered target digests
   (`ba88708b...`, inv_freq `da9f6dcf...`), prompt_toks=4/gen_toks=16/
   dtype=fp32, weight sha256, and the two-run/cross-process pass-bar
   description (no further per-op detail beyond what E15b_REFERENCE_
   RESULT.md already gives).
4. `~/projects/claudius-maximus/state/reports/2026-08-28-E14a-cis2-fp-design.md`
   — read in full (this is "the normative memo" the task describes as
   `docs/design/CIS2_FP_RECEIPT_DESIGN.md`; that path does not exist
   anywhere in `cis2-fp`'s git history. The actual memo lives in a
   *different* repo, `claudius-maximus`, under `state/reports/`. Treated
   as the intended file per the task's own description ("the normative
   memo") since no closer match exists; flagged as a task/pathing
   discrepancy, not a src/ peek.). Referred to throughout as "the memo."
5. `Cargo.toml` (root, `cis2-fp` — the `cis2_ref` package manifest) — read
   only to determine (a) there is no Cargo workspace to join (this is a
   single non-workspace package) and (b) the dependency versions needed to
   build a same-shape standalone crate (`safetensors 0.8`, `tokenizers
   0.23` w/ `onig`, `sha2 0.11`, `serde_json 1`) — permitted per the task
   ("nor read its Cargo.toml dependencies for hints beyond what's needed
   to build the workspace"). No src/ or tests/ file was opened.
6. `./target/release/cis2_ref --help` (built from the untouched `cis2_ref`
   package, not from `verify/`) — no `--help` flag is implemented; running
   it bare only shows it panics looking for `weights/model.safetensors`
   (confirms the weights-directory convention, nothing about internals).

No file under `src/` or `tests/` of `cis2-fp` was opened, grepped, or
diffed at any point in this task.
