# verifier/

Thin wrapper around the vendored `cis2-spec` verifier, not a rewrite.

- `vendor/cis2-verify2/` — verbatim copy of `cis2-spec`'s `verify2` crate
  (src/, Cargo.toml/.lock, CLEANROOM_LOG.md) plus `VENDOR.md` (provenance,
  "do not hand-edit — patch upstream and re-vendor"). Builds to
  `target/release/cis2-verify2`, a no-args binary hardcoded to run the
  pinned CIS-2 v0.3b reference vector (SmolLM2-135M, fp32, "Once upon a
  time", 16 greedy tokens) against `weights/{model.safetensors,
  config.json,tokenizer.json}` in its own cwd, printing the pinned
  digests. `weights/` is git-ignored (repo root `.gitignore`); fetch via
  `cis2-spec/scripts/fetch_weights.sh <dest>` and sha256-check against
  `cis2-spec/EXPECTED_DIGESTS.md` before trusting.
- `cis2_verify_cli.py` — `cis2 verify <receipt-id-or-json-file>`. Loads a
  receipt (by id, from `CIS2_LLM_RECEIPT_LOG`, or a raw JSON file), checks
  its `log_hash` against a fresh canonical-encode-then-SHA-256 of the
  record body + `prev_hash`, and prints PASS/FAIL with exit code 0/1.
  This is a **replay/tamper check of the receipt record**, not an
  independent clean-room re-implementation of the digest computation —
  that role is already filled by `cis2-spec`'s `verify3` crate and its
  cross-implementation convergence work; we do not duplicate it here.
- `server/app/main.py` exposes the same logic over HTTP as `POST /verify`
  (dynamically imports this module — see server/README or main.py).

## Scope note (see docs/CLAIMS.md)
Verifying a receipt confirms the receipt record is internally consistent
and its digests match a fresh run of the pinned reference vector. It says
nothing about whether that reference vector's output was correct, safe,
or representative of any other prompt/model.
