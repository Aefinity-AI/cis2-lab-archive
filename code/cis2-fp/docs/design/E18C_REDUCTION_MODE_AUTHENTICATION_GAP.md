# E18c follow-up — how much does the unauthenticated `reduction_mode` field actually cost?

Published 2026-10-16 as part of the CIS-2 archive. **Not a spec revision.** This memo
supplies the missing measurement behind the open v0.4 decision recorded in
`claudius-maximus/state/NEEDS.md` ("`reduction_mode` is receipt metadata, not
folded into the witness hash — quantify the hole"). It answers that with numbers
rather than an argument, then lays out the three options and their costs.

Companion to `CIS2_V04_TREE_REDUCTION.md` (which defines the pinned tree order)
and to `cis2-spec/docs/PROPOSED_v0.4_TIER1_OP_GOLDENS.md` (the other open v0.4
item). The two are independent; adopting one does not commit you to the other.

## 0. Provenance

Measured 2026-09-09 on `penguin` (Crostini/crosvm, x86_64), `cis2-fp` at
`2fa06be`, `cargo build --release`, `weights/` = SmolLM2-135M
(`model.safetensors` sha256 `80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1`),
run under `flock /tmp/aefinity-os.lock nice -n 10`.

**No timing number appears in this memo and none may be taken from this run.**
penguin is a VM; Rule A forbids it as a source of published timings. Everything
below is a digest or a token id — bit-exact quantities that are machine- and
schedule-independent by construction, which is precisely why they can be
measured here at all.

## 1. Independent reproduction of the E18c PREP-PASS table

All four digests recorded in `CIS2_V04_TREE_REDUCTION.md` §6 were re-derived
today, on a different day, from a different checkout (`2fa06be`, a merge commit
downstream of the `04e5ad77` the table was taken at):

| mode | gen_toks | digest | matches §6 |
|---|---|---|---|
| sequential | 16 | `d82743059d1db929e710236fe4ec37f89e6f932524801345a006980f7c3cc9df` | YES |
| sequential | 128 | `22f69ad87a615d66a77efaca8b1172d22bdfb4bd5092ceffd302e35669a050f6` | YES |
| tree | 16 | `3f3b1ffceca02e8e0e78d5c653963480ea988ef41a378acc5393006ad378e1b3` | YES |
| tree | 128 | `112661fbfcb11440ae7d27c43e45135f8a6ff9f6bc01189d756c76dac96a0fdf` | YES |

The sequential rows also still equal the published v0.3b §13.1 conformance
vector. The tree order has not disturbed the sequential path.

## 2. The measurement that was missing: the tokens do not change

Nothing in the record said whether the two reduction orders produce the same
*text*. They do:

- **gen_toks=16** — both modes emit
  `[6403, 1980, 253, 655, 28, 665, 436, 253, 1838, 8180, 3365, 14176, 30, 2306, 4161, 281, 253, 2066, 2291, 351]`.
- **gen_toks=128** — both modes emit the identical 132-element sequence.
  Compared with `diff` on the captured `run1_tokens=` lines, not by eye:
  `TOKENS IDENTICAL across reduction modes at 128 tokens`.

So across 128 sequential argmax decisions, each taken over a 49 152-wide logit
vector whose every element was summed in a different order, **not one argmax
flipped**. `runs_identical=true` in both modes, so this is not run-to-run noise.

This is a one-checkpoint, one-prompt result and is not evidence that argmax can
never flip under a reduction-order change — §11.2's strict-`>` first-maximal rule
exists exactly because near-ties are reachable. It is evidence about the specific
shape of the risk, below.

## 3. What that implies, stated precisely

The two modes agree on every observable output and disagree on the digest.
That is the worst possible combination for diagnosability:

> A `CIS2_REF` digest mismatch caused purely by reduction order is
> indistinguishable, **from the digest alone**, from a mismatch caused by wrong
> weights, a wrong table, a broken kernel, or a tampered receipt. The only thing
> that tells the two apart is an unauthenticated plaintext field.

Had the modes produced different tokens, a reader comparing two receipts would at
least see *why* they differ. They do not.

## 4. Attestation does not close this (correcting an earlier reading)

`alice-aegis/demo/edge-receipt/attest.sh` passes the receipt's digest **value**
as the TPM quote's qualifying data — `tpm2_quote ... -q "$nonce"`, where `$nonce`
is read by `receipt_nonce()` from the `cis-digest`/`trace-chain` line. It is not
a `sha256sum` of the receipt file. `verify` re-reads that one line and compares.

Therefore every other line on the receipt — `reduction_mode=`, `dtype=`,
`prompt_toks=`, `gen_toks=` — sits **outside the signed material**. A note of
mine had this as "attest.sh signs the full receipt"; it signs the full-width
digest (64 hex rather than a truncation), which is a different claim. Attestation
raises no obstacle to editing `reduction_mode=tree` into `reduction_mode=sequential`.

## 5. The bound on the damage

The hole is narrower than §3 and §4 make it sound, and the bound is worth stating
because it is what makes option (b) below sufficient:

- **A recomputing verifier always catches a mislabel.** A receipt stamped
  `sequential` but produced in tree mode fails a sequential re-verify; the reverse
  fails a tree re-verify. Mislabeling buys an attacker nothing against anyone who
  recomputes.
- **The cost of not being told the mode is one extra recomputation.** A verifier
  holding both implementations can recover the mode by trying both. The field is
  a convenience, not a capability.
- **The gap is real only for a consumer who compares digests without
  recomputing** — an index, a registry, a dashboard, a compliance log that stores
  digests and asks "do these two match?". That consumer is exactly the one an
  auditing or provenance product is built to serve, so the gap is not academic.

## 6. Options for v0.4, with costs

**(a) Fold `reduction_mode` into the witness hash.** Sound, and wrong. A
different set of input bytes hashes differently, so this changes the *sequential*
digest too, invalidating §13.1, the published GitHub release, the HF conformance
dataset, and every receipt ever issued. **Do not do this.** The whole value of the
rare asset is that `d827430…` has been reproduced by strangers; changing it
discards that.

**(b) Make `reduction_mode` a REQUIRED receipt field with normative failure
semantics.** Keep the fold byte-for-byte as it is. Specify: `sequential` is the
default and the only v0.3b-conformant value; the field MUST be present on every
receipt; a verifier MUST FAIL, not warn, on a receipt whose field is absent or
carries an unrecognized value. Non-breaking — no digest moves. Cost: one
paragraph of spec text and one check in each verifier.

**(c) Give the receipt a header digest and quote that instead.** Define a second
SHA-256 over the receipt's metadata lines, and make *that* the TPM quote's
qualifying data (or fold the witness digest into it). This is the only option
that actually authenticates the field. Cost: it breaks `ATTEST.txt`'s current
format and every existing attestation, though not `CIS2_REF`.

## 7. Recommendation

**Adopt (b) in v0.4. File (c) as a separate attestation-format item, not gated on
the reduction work.** (b) removes the diagnosability problem in §3 at zero cost to
the published digests, which is the constraint that actually matters here. (c) is
the real fix for §4 and should be decided on the attestation format's own
schedule, since it affects CIS-1 decode receipts and agent-trace receipts too —
neither of which has anything to do with reduction order.

Rejecting all three is defensible and should be recorded as a decision rather
than left implicit: it means shipping tree mode with a mismatch that reads as a
reproducibility failure and is disambiguated only by an editable line of text.

**Status: PROPOSAL. Justin's call.** Tree reduction remains v0.4 CANDIDATE
private research; publishing it is a separate PUBLISH? gate.
