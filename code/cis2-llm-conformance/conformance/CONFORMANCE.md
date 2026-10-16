# conformance/ — cis2-llm corporate conformance suite

Published 2026-10-16 as part of the CIS-2 archive. This directory's job is narrow and honest: give a customer's own auditor
a machine-checkable way to independently confirm which specific, concrete
claims cis2-llm's v0.1 scaffold actually backs up, and which it does not.

**Read `compliance/CROSSWALK.md` first.** That file is the source of truth for
what CIS-2 does and does not cover against EU AI Act / SOC 2 / ISO 42001 /
NIST AI RMF, with citations. This suite is a machine-checkable subset of that
document's claims, not a new or looser set of claims — every vector here maps
back to a specific CROSSWALK.md row (or is honestly marked "not in
CROSSWALK.md" when it isn't a compliance claim at all).

## What this is / is not

- This IS: a set of test vectors that a running cis2-llm server (and,
  optionally, gateway) either demonstrably passes or does not, plus profiles
  that say which vectors are relevant evidence for which named regulatory/
  standards framework, plus an honest "not covered" list per profile.
- This is NOT: a certification, an audit, a substitute for a licensed CPA
  firm (SOC 2), an accredited certification body (ISO 42001), or a
  conformity-assessment body (EU AI Act). See CROSSWALK.md's "Meets-or-
  exceeds verdict" section for what a *real* audit still needs beyond
  anything this suite can produce.
- BLOCKED is not a pass. If a vector reports BLOCKED, that means the property
  it's testing for is a known, currently-real gap in the v0.1 scaffold — read
  the detail field, it explains exactly what's missing and why.

## Layout

```
conformance/
  vectors.py          8 vector implementations (see "Vectors" below)
  profiles/*.json      4 profiles (data): eu-ai-act, soc2-pi1, iso42001, nist-ai-rmf
  report.py            JSON + Markdown report builders
  __main__.py           `python -m conformance run ...` CLI
  reports/              generated reports land here (gitignored — regenerate, don't trust a stale copy)
```

## Running it yourself (independent auditor path)

You need: this repo checked out, `uv` installed, network access once (to fetch
the pinned SmolLM2-135M weights and cargo-build the vendored verifier), and
~1 GiB free RAM. No GPU, no Docker required for this path.

```bash
# 1. Build the vendored verifier binary (one-time, ~1-2 min)
cd verifier/vendor/cis2-verify2
cargo build --release

# 2. Fetch + sha256-verify the pinned model weights (one-time, ~1 min on a
#    normal connection; fetch_weights.sh refuses to proceed on a hash
#    mismatch, so this step is itself a supply-chain integrity check)
bash <path-to-cis2-spec-checkout>/scripts/fetch_weights.sh ./weights
cd ../../..

# 3. Start the server (terminal 1)
cd server
rm -rf data
uv run uvicorn app.main:app --host 127.0.0.1 --port 8799

# 4. Start the gateway (terminal 2, repo root — needed for
#    replay_tamper / tool_gate_deny vectors; omit --gateway below to skip them)
uv run --project server uvicorn gateway.app:app --app-dir . --host 127.0.0.1 --port 8899

# 5. Run a profile (terminal 3)
python3 -m conformance run --profile eu-ai-act \
  --server http://127.0.0.1:8799 --gateway http://127.0.0.1:8899

python3 -m conformance list-profiles   # see all profile names
```

Exit code is `0` iff no vector FAILed (BLOCKED/NOT_RUN don't fail the run —
they're honestly-reported gaps, not errors in the harness). Reports land in
`conformance/reports/conformance-<profile>.{json,md}`.

### License-refusal vector needs local process-spawn capability

`license_expired_refusal` spawns its own short-lived server subprocess (with a
forced-stale eval clock and no production license configured) to check it
refuses to start — it does this regardless of the `--server` URL you pass, by
using the checkout the runner itself is executing from. If you're pointing
`--server` at a remote/already-running instance you don't control the
filesystem of, this vector still runs (it spawns its own separate temp
instance locally) but do read its evidence.server_log_tail to confirm what it
actually observed, and treat it as evidence about *this checkout's* license
enforcement code, not necessarily the exact remote instance you pointed
`--server` at.

### Vectors that need `--server` to be a *local* instance for full evidence

`chain_integrity` and `token_log_completeness` do an extra, stronger,
independent check (re-verifying the log file directly via the vendored CLI,
or re-decoding the raw token ids) ONLY if the runner has local filesystem
access to the same `server/data/receipts.jsonl` the `--server` process is
writing to (i.e. `--server http://127.0.0.1:...` on the same host as the
runner). Against a genuinely remote server, these vectors still run and still
PASS/FAIL on the HTTP-visible evidence, but the report's `evidence` field will
say the independent recheck was SKIPPED and why — read that field, don't
assume the strongest form of the check ran.

## Vectors (the (a) requirement)

| id | what it demonstrates | requires |
|---|---|---|
| `receipt_schema` | every response's receipt has all required fields, non-empty token list | `--server` |
| `chain_integrity` | 3 receipts hash-chain correctly; independently re-verified via the vendored CLI when local | `--server` (stronger with local FS) |
| `replay_tamper` | resubmitting a valid receipt -> DENY (replay); a receipt with a mutated `witness_digest` but stale `log_hash` -> DENY (tamper) | `--server`, `--gateway` |
| `wrong_model_binding` | a request for an unknown model id gets HTTP 400 at issuance; a receipt's bound `model_id` checked via `POST /verify` against a mismatched request -> `ok=false` | `--server` |
| `wrong_prompt_binding` | every receipt carries a `prompt_digest` (sha256 of the request's actual `messages`); two different prompts -> two different digests; a receipt checked via `POST /verify` against a mismatched request's messages -> `ok=false` | `--server` |
| `tool_gate_deny` | `gateway/tools.yaml` allow list: a valid receipt submitted against a disallowed tool name -> DENY (receipt-logged to `gateway/data/tool_denials.jsonl`); the same shape of receipt against an allowed tool name -> ALLOW (control) | `--gateway` |
| `license_expired_refusal` | a server started with a forced-expired eval clock and no production license refuses to come up | local checkout + `uv` |
| `token_log_completeness` | the receipt's `generated_token_ids` has no gaps and (when local) re-decodes to exactly the text returned to the caller | `--server` (stronger with local FS) |

### cis3-2b update (2026-09-19): the 3 BLOCKED vectors are now real PASS/FAIL checks

Closed in this leg:
- **Model binding.** `server/app/main.py` now only serves the pinned
  reference model under model id `cis2-ref-smollm2-135m`
  (`PINNED_MODEL_ID`); any other `model` in the request gets HTTP 400
  before a receipt is ever issued. Every receipt also carries a `model_id`
  field (the request's model id) and a `prompt_digest` field (sha256 of the
  request's actual `messages`, canonically encoded) — real per-request
  binding, computed from what the caller actually sent, not from the fixed
  §13.1 reference prompt the vendored `cis2-verify2` binary still always
  computes (that underlying compute limitation is unchanged — see
  `server/app/runner.py`'s scope note. This leg binds the *receipt record*
  to the *request*, it does not add general-purpose generation).
- **`POST /verify` request-binding check.** `/verify` now accepts an
  optional `request: {model, messages}` field alongside `receipt`. When
  given, it DENYs (`ok: false`) if the receipt's bound `model_id`/
  `prompt_digest` don't match that request, even if the underlying
  digest/chain check independently passes. (Note: fixed a pre-existing bug
  in this endpoint in the same commit — `cis2_verify_cli.verify()` required
  a second `log_path` argument main.py never passed, so `/verify` would
  500 before this fix; `log_path` now defaults to `None`.)
- **Gateway tool gate.** New `gateway/tools.yaml` (allow-list mode) +
  `gateway/tool_policy.py` (loader/matcher, fails closed on any load
  error). `Gateway.submit()` checks the tool name against this policy
  *before* anything receipt-related; a disallowed tool -> DENY,
  independent of receipt validity, and the refusal is appended to a new
  hash-chained `gateway/data/tool_denials.jsonl` log (same chain rule as
  `server/app/receipts.py`, reimplemented locally so `gateway/` has no
  import-time dependency on `server/`).

All three vectors were adversarially verified as real checks (not
harness-shaped false positives): each protection was temporarily stubbed
out on a running server/gateway, the corresponding vector was re-run and
observed to FAIL with the expected reason, then the stub was reverted
before the final commit — see the cis3-2b task notes / PR description for
the exact FAIL output observed for each of the three.

Result on this leg's clean final run: **8/8 PASS, rc 0**, across all four
profiles (`eu-ai-act` runs the full 8; `soc2-pi1` 6; `nist-ai-rmf` 4;
`iso42001` 3 — see each profile's vector list above for which subset it
runs). Reports: `conformance/reports/conformance-<profile>.{json,md}`
(gitignored, regenerate don't trust a stale copy).

### Honest gaps this suite surfaces (do not paper over these)

All three vectors that were BLOCKED as of cis3-2 (`wrong_model_binding`,
`wrong_prompt_binding`, `tool_gate_deny`) are now real PASS/FAIL checks as
of cis3-2b — see "cis3-2b update" above for what closed them. Remaining
honest gaps, carried forward:

- **The underlying compute is still the single pinned §13.1 reference
  vector.** `server/app/runner.py`'s vendored `cis2-verify2` binary still
  only ever computes SmolLM2-135M / fp32 / "Once upon a time" / 16 greedy
  tokens, regardless of the request's actual `messages` content — general-
  purpose generation is still LLM-4/LLM-5 scope in `PROGRAMME.md`, not
  touched by this leg. What cis3-2b adds is that the *receipt record* is
  now genuinely bound to the *request* (real `model_id`/`prompt_digest`
  fields, checked by `/verify`), which is a different and narrower claim
  than "the model actually computed something different for a different
  prompt" — don't conflate the two when reading `wrong_prompt_binding`'s
  PASS.
- **Gateway binding is not yet wired into the tool-gate path.** The new
  `/verify` request-binding check exists on the server; `gateway/gateway.py`'s
  `submit()` does not yet accept an optional `request` context to also
  enforce model/prompt binding at the gateway boundary (only the tool
  allow/deny list is enforced there). If a corporate deployer needs the
  gateway itself to refuse a stale/mismatched receipt's binding (not just
  its hash validity), that's still open — track as a follow-on, not silently
  assumed covered by `tool_gate_deny`.

## Profiles (the (b) requirement)

`conformance/profiles/*.json`: `eu-ai-act`, `soc2-pi1`, `iso42001`,
`nist-ai-rmf`. Each profile lists: which vectors it runs, which
`compliance/CROSSWALK.md` row each vector is evidence for (with the same
"PARTIAL"/"COVERED"/"NOT COVERED" honesty CROSSWALK.md uses — a profile
including a vector is not itself a claim of full coverage; read the
crosswalk row), and a `not_covered` list of things that profile's vectors do
NOT and cannot prove. Read a profile's `not_covered` list before reading its
PASS column — the not_covered list is usually longer and more important.

## Runner (the (c) requirement)

`python -m conformance run --profile <name> --server <url> [--gateway <url>]
[--out-dir <dir>]`. Emits `conformance-<profile>.json` (machine-readable:
per-vector status, crosswalk control, receipt ids produced, raw evidence) and
`conformance-<profile>.md` (human-readable summary table + per-vector detail
+ the profile's not_covered list) into `--out-dir` (default
`conformance/reports/`, gitignored).

The runner never fabricates a PASS: any vector whose implementation raises an
exception is recorded as FAIL with the exception text, never silently
skipped or silently passed. A vector that genuinely can't run against the
given `--server`/`--gateway` (missing infra) reports NOT_RUN with the reason;
a vector that ran but found the scaffold genuinely lacks the property being
tested reports BLOCKED with the reason. See the table above.

## Status of this leg (cis3-2b, 2026-09-19)

Built on cis3-2: implemented request binding (server + `/verify`) and the
gateway tool gate (`gateway/tools.yaml` + `gateway/tool_policy.py`), flipped
all three previously-BLOCKED vectors to real checks, ran all four profiles
clean (rc 0 each, 8/8 PASS on the full eu-ai-act set), and adversarially
verified each of the three new checks by temporarily stubbing its
protection and confirming the vector FAILs (stubs reverted before commit).
Not done in this leg: gateway-side model/prompt binding enforcement (see
"Honest gaps" above); CI wiring (still manual, same as cis3-2 left it).

## Status of prior leg (cis3-2, 2026-09-19)

Built and actually exercised end-to-end on this box: vendored verifier built
(`cargo build --release`), SmolLM2-135M weights fetched + sha256-verified,
server + gateway stood up locally, all four profiles run to completion with
exit code 0 (no FAILs). Results as observed on this run:

- PASS: `receipt_schema`, `chain_integrity`, `replay_tamper`,
  `token_log_completeness`, `license_expired_refusal` (eu-ai-act profile
  only — the other profiles don't include it).
- BLOCKED (honest, documented gaps in the v0.1 scaffold, not test bugs):
  `wrong_model_binding`, `wrong_prompt_binding`, `tool_gate_deny`.
- NOT_RUN: none in this run (both `--server` and `--gateway` were provided).
  Running with only `--server` (no `--gateway`) will report `replay_tamper`
  and `tool_gate_deny` as NOT_RUN instead of running them — this is correct,
  not a bug: those two need the gateway process.

What's genuinely still open, for whoever picks this up next:
- No CI wiring — this suite is exercised manually per the recipe above, not
  on every commit. Given the weights-fetch + cargo-build cost, that's a
  deliberate v0.1 choice (same discipline as `tests/smoke.sh` etc.), not an
  oversight, but note it here so it isn't assumed to run automatically.
- `wrong_model_binding`/`wrong_prompt_binding`/`tool_gate_deny` will stay
  BLOCKED until the underlying product gaps they document are actually
  closed (general-generation server, tool allowlist in the gateway) — that
  is real product work, tracked in `PROGRAMME.md`, out of scope for this
  conformance-suite leg.
- The suite currently talks to one server/gateway pair per run; it does not
  yet test multi-tenant / multi-instance license enforcement, HA/failover,
  or the Postgres-backed log path described in `deploy/` (that path is
  itself unbuilt/untested on this box per `docs/DEPLOY.md`).
