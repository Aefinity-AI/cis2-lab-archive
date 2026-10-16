# E15e — spec gaps found while writing a clean-room CIS-2 verifier

This crate (`cis2-verify`) was built reading only the files listed in
`CLEANROOM_LOG.md`. Below are the memo/doc ambiguities this independent
implementation had to resolve by its own choice, in the order they bite.

## 0. Process/pathing gaps (not about the spec's content, but about this task)

- `docs/design/CIS2_FP_RECEIPT_DESIGN.md` does not exist anywhere in
  `cis2-fp`'s git history (checked `--all`). The actual "normative memo"
  lives in a *different* repository:
  `~/projects/claudius-maximus/state/reports/2026-08-28-E14a-cis2-fp-design.md`.
  If a real third party tried to follow this task's instructions literally
  ("read only `docs/design/CIS2_FP_RECEIPT_DESIGN.md`"), they would find
  nothing and be unable to proceed at all. Recommend either (a) copying/
  symlinking the memo into `cis2-fp/docs/design/` so the repo is
  self-contained, or (b) fixing the task instructions to point at the
  actual path.
- `origin/cm/e15c-cross-isa` on GitHub currently points at commit `f83e8dd`
  (no `docs/E15c_RESULT.md`, no `hardware_logs/e15c_crossisa_*.log`), but
  a later commit `05187dc` with those files and the actual E15c result
  exists in at least one local clone's objects (reachable via a stale
  local branch ref of the same name, not present on any remote branch).
  This means **the pushed state of `cm/e15c-cross-isa` on GitHub is
  missing its own headline result** — someone force-pushed/reset that
  branch backward after `05187dc` was pushed. This should go in
  `claudius-maximus/state/BLOCKERS.md` or `NEEDS.md`: the E15c result
  needs to be re-pushed (or re-merged) to `origin/cm/e15c-cross-isa` /
  wherever it's meant to land, or it will silently vanish from the
  project's public-facing history.

## 1. Receipt/digest exact byte encoding (E14a memo, RoPE/witness section; E15b's description)

The memo's §5 (E14b plan) states the witness digest is "SHA-256 ... over
every decode step's full logit vector plus the generated token ids and
artifact hashes" but never gives a byte-exact procedure (this level of
precision does not exist in the memo text at all — it exists only in
E15b_REFERENCE_RESULT.md's prose description of an already-built
implementation, which is not itself a spec). Concretely unresolved:

- Order of the three artifact hashes in the seed (this implementation
  chose model.safetensors, then config.json, then tokenizer.json).
- Whether artifact hashes are fed as raw 32 bytes or as their 64-character
  hex-string bytes.
- Integer width/endianness for prompt token ids and per-step chosen token
  ids (this implementation chose `u32`, little-endian).
- Whether the "chain" is one continuous `Sha256::update()` stream (what
  this implementation does) or a step-wise re-hash of
  `(running_digest || new_data)` (a true hash *chain*, which the word
  "chained" in the memo's Context recap arguably implies more strongly) --
  these produce different final bytes.

**This resolved cleanly for the argmax-token digest only:** this
implementation's independent choice — `SHA-256` over `u32` little-endian
bytes of every prompt token id followed by every generated token id, as
one continuous hash stream, no artifact hashes included — reproduced
`0b9c8f3ac90d0b9cd5f1719ac327dca1fc639fd87468305fccebbe3d56f67aff` **exactly**,
matching E15b/E15c's own reported `argmax_digest` bit-for-bit. That
digest's encoding was therefore *not* ambiguous in practice, or this
implementation got lucky on the first of only two plausible encodings
tried (`u32`/`u64` widths × prompt-first/gen-first order); either way, it
is independent confirmation that the greedy-decode token sequence itself
(not just the encoding scheme) is identical between two independently
written implementations.

The full witness/`CIS2_REF` digest (over full fp32 logit vectors) did
**not** reproduce and is not expected to, independent of encoding choice
— see item 2.

## 2. Transcendental function route is not actually pinned by the memo (the load-bearing gap)

§3.3 states two options and **recommends (a) correctly-rounded** but
explicitly could not source a Rust CORE-MATH/RLIBM binding (E15b's own
finding, repeated independently by this implementation — no such crate
was found/attempted here either, same constraint). The memo's fallback,
**(b) "pinned LUT + polynomial,"** is *by the memo's own words* "one
arbitrary choice among many" whose coefficients "must be pinned by fiat"
— i.e., **the memo intentionally does not, and cannot, specify exact
coefficients**, because pinning them is delegated to whichever
implementation adopts route (b). Two independent implementations that
both "follow the memo" by choosing route (b) have **no shared reference**
to converge on unless they separately agree on identical coefficients out
of band (which defeats the purpose of a spec-driven clean-room check).

This implementation used route (a) as literally as possible given the
same crate-availability constraint E15b hit: host `std`/libm `f32::exp`/
`sin`/`cos` (glibc), which is "faithfully rounded" (<=1 ULP) but not
proven correctly-rounded. E15b/E15c instead used route (b) with
independently-pinned Cephes-pattern coefficients (per E15b's own
description; not read from src). These are, by construction, two
different transcendental implementations, so a full logit-vector digest
match was never plausible — this run is exactly the "argmax survives
tiny transcendental precision differences even though the bit-exact
logit vector does not" case the memo's own risk section (§6) flags in
spirit (though not this specific framing) as "an uninteresting positive
would say the contract works for this model's typical inputs, not that
it's sound" — here it is the opposite polarity: the low-order bits
diverge, but the argmax decisions do not, at least not on this
non-adversarial prompt.

**Recommendation for CIS2 v0.2:** if bit-identical *logits* (not just
argmax) across independent implementations is a goal, §3.3 must either
(a) get a real Rust correctly-rounded binding (e.g. FFI to CORE-MATH's C
reference code) so two honest implementations converge by construction,
or (b) the memo must itself publish the exact pinned coefficients/table
as spec text (the way CIS-1 publishes its exp LUT constant in-spec), not
leave them to be independently invented per implementation.

## 3. RoPE `inv_freq` construction and digest are underspecified in the memo itself

The E14a memo never states the `inv_freq` formula at all (RoPE is
mentioned only via its `sin`/`cos` nondeterminism risk in §2's table, not
its initialization-time table construction). The `theta^(-2i/head_dim)`
formula used here is the standard Llama convention, not memo text.
E15b's own open-question #4 proposes an `exp_pinned(-exponent * ln(theta))`
construction as *future work*, not a specified procedure — no formula for
`exponent`, no pinned `ln` algorithm, and no digest byte encoding is ever
given in either doc this implementation was allowed to read.

This implementation computed `inv_freq[i] = 1.0 / theta.powf(2i/head_dim)`
via host `f64::powf` (i.e., the literal thing E15b's own doc calls "a
host-libm dependency that... has not been pinned or digested" — an
admitted, not-yet-fixed gap in the reference itself, not just in this
clean-room attempt), then digested the resulting 32 `f32` values'
`to_bits().to_le_bytes()`, concatenated LE, SHA-256. Result
(`6d20bb9d2a7ec35a70fcc399fed93e17664fa74f95942d9ec77f17ae7a882668`) does
not match the target (`da9f6dcf...`), consistent with the reference
apparently having moved to a different (`exp_pinned`) construction between
E15b and E15c that is not specified anywhere this implementation was
permitted to read.

## 4. RMSNorm elementwise order (minor)

Memo doesn't state whether `x[i]*scale*weight[i]` should be computed as
`(x[i]*scale)*weight[i]` or `x[i]*(scale*weight[i])` — these are not
bit-identical in fp32 for arbitrary operands (multiplication is not
associative in fp under rounding, in general, though for this particular
op the difference from reordering two scalar multiplies is very unlikely
to be visible — noted for completeness, not fought over since it isn't
where the observed mismatch is coming from). This implementation chose
`(x[i]*scale)*weight[i]`.

## Summary of what this run demonstrates

| Check | Result |
|---|---|
| Weight/config/tokenizer sha256 | **match** E15b/E15c's provenance table exactly |
| Tokenization of `"Once upon a time"` | **match**: `[6403, 1980, 253, 655]` |
| Greedy-decoded 16 token ids | **match**, bit-for-bit identical sequence |
| `argmax_digest` (SHA-256, u32 LE, prompt+gen tokens) | **MATCH**: `0b9c8f3a...` |
| `inv_freq table_digest` | **mismatch**: `6d20bb9d...` vs target `da9f6dcf...` |
| `CIS2_REF`/witness digest (full fp32 logit chain) | **mismatch**: `241a7338...` vs target `ba88708b...` |

Read strictly per this experiment's own preregistered outcomes: this is a
**MISMATCH** on the two digests that are supposed to be the strong,
bit-exact convergence claims (`CIS2_REF`, `inv_freq table_digest`), with
the first identifiable divergent quantity being **the transcendental
function implementation** (§3.3's unpinned route (b) coefficients / route
(a) crate unavailability) — not tokenization, not weight provenance, and
not (surprisingly) the greedy-decode argmax decisions themselves, which
converged independently along with their own dedicated digest. This is a
materially different, more informative outcome than a blanket "everything
mismatched" would be.
