# Deploy (v0.1 scaffold)

Three modes, in order of what's actually been run:

## 1. Single-process (tested, this is what tests/smoke.sh uses)
```
flock /tmp/xxon-heavy.lock deploy/single-process.sh
```
No Docker, no Postgres. Builds the vendored verifier if needed (heavy —
run under flock), checks `verifier/vendor/cis2-verify2/weights/` exists
(fetch separately, see verifier/README.md), then execs
`uv run uvicorn app.main:app` directly. Receipt log defaults to
`deploy/data/receipts.jsonl` (override with `CIS2_LLM_RECEIPT_LOG`).
Confirmed working on this 1.2 GB-RAM box (empirically ~1.3 GiB avail,
1 GiB swap free — enough for the 135M fp32 reference vector).

### Gateway standalone (LLM-5, no Docker)
```
cd gateway && CIS2_GATEWAY_WORKERS=2 uv run --project ../server \
  uvicorn gateway.app:app --host 127.0.0.1 --port 8081
```
(run from the repo root so `gateway` is importable as a package; the `uv
run --project ../server` just reuses server/'s already-declared FastAPI
dependency, gateway/ adds nothing new to pyproject.toml). This is what
`tests/test_gateway.sh` drives — no verifier binary, no weights, no
Postgres required for the gateway's own tests (it talks to receipt
records directly, not through the running server/).

## 2. Docker Compose (config-validated only, NOT built/run on this box)
```
docker compose -f deploy/docker-compose.yml config   # rc=0, confirmed
```
`docker compose up` / `build` deliberately NOT run here — this box does
not have the RAM headroom to run Postgres + server + verifier containers
concurrently alongside a cargo build. The compose file defines:
- `postgres` — receipt-log-adjacent metadata store (v0.1: server still
  writes the authoritative JSONL log to a named volume; Postgres wiring
  for receipt indexing is future work, not required for the smoke path).
- `server` — builds from `Dockerfile.server`, mounts the receipt-log
  volume, depends_on postgres.
- `verifier` — builds from `Dockerfile.verifier`, exposes `POST /verify`
  standalone (same code as server's `/verify`, split out so verification
  can run on a machine that never holds the weights... it still needs
  the weights to recompute digests, so this is mostly useful for scaling
  verify load, not for removing the weights dependency).
- `gateway` — behind `profiles: ["gateway"]`, not started by a bare
  `docker compose up` (opt in with `docker compose --profile gateway up`).
  Real implementation as of LLM-5 (async PENDING/POLL gateway ported from
  alice-aegis safe-7; see gateway/README.md): `POST /v1/gateway/submit`
  `{receipt, tool, action}` -> `{ticket, status}`, `GET
  /v1/gateway/poll/{ticket}` -> `{status: PENDING|ALLOW|DENY, ...}`. Pure
  Python stdlib + FastAPI (server/pyproject.toml already has FastAPI) —
  no cargo build, no model weights needed for the default verify_fn (a
  record-tamper/replay check, not the heavy cis2-verify2 digest
  recompute; see gateway/verify_check.py). Tested standalone on this box
  with `tests/test_gateway.sh` (uv run uvicorn gateway.app:app, no
  Docker); `docker compose --profile gateway build/up` for the gateway
  service itself has NOT been run on this box (same RAM-headroom
  discipline as server/verifier) — treat the Dockerfile.gateway path as
  config-validated only until someone runs it on a box with headroom.
Secrets: `deploy/secrets/pg_password.example` is a placeholder
("changeme-eval-only"); real secrets are never committed
(`deploy/.gitignore` excludes everything in `secrets/` except the
example file).
Dockerfiles (`Dockerfile.server`, `Dockerfile.verifier`, `Dockerfile.gateway`)
are written but **not built** on this box for the same RAM reason;
they should build cleanly on a normal-RAM CI box or on box1/box2, but
that has not been verified here — treat as unverified until someone
runs it on a box with headroom and reports back.

## 3. Kubernetes / Helm (skeleton only, UNTESTED — no helm/cluster on this box)
`deploy/helm/` — Chart.yaml, values.yaml, templates/{deployment,service,pvc}.yaml.
Values-driven (image repo/tag, replica count, service type/port, PVC size
and storageClassName, resource requests/limits). Never `helm lint`'d or
`helm template`'d here because no `helm` binary is installed on this box.
Treat this as a structural starting point for LLM-6/whoever does the
first real cluster deploy, not a validated chart.

## HTTP routes (server/app/main.py)

- `POST /v1/chat/completions` — issues a receipt for the pinned reference
  vector (see docs/CLAIMS.md scope note).
- `GET /v1/receipts/{receipt_id}` — fetch one receipt record.
- `GET /v1/receipts` — chain-status payload (`{"chain_ok": bool,
  "message": str}`); kept for compatibility with existing callers.
- `GET /v1/chain_status` — same payload as `GET /v1/receipts`, explicit
  route name; prefer this one in new callers.
- `POST /verify` — thin HTTP front for `verifier/cis2_verify_cli.py verify`.

## RAM/heavy-command discipline
Any cargo build or model-loading run on this box goes under
`flock /tmp/xxon-heavy.lock` to avoid contention with other concurrent
legs. `docker build`/`docker compose up`/`helm` are not run here at all
until a bigger box is available — see the "not built" notes above.

## Licensing (LLM-3)

Checked once at FastAPI startup (`server/app/main.py` -> `server/licensing.py`).
Two env vars, both optional:

- `CIS2_LICENSE_FILE` — path to a signed license file produced by
  `licensing/license_tool.py issue` (see licensing/README.md).
- `CIS2_LICENSE_PUBKEY` — path to the ed25519 public key PEM that
  matches the private key used to issue it.

If either is unset, missing, or the license fails verification, the
server runs in **EVAL** mode: a 30-day clock starts on first boot and is
recorded in `data/eval-start` (relative to the server's working
directory; gitignored, resets if deleted — see `server/licensing.py`
module docstring for the trust-model caveat). Once EVAL expires with no
valid production license installed, startup raises and the server
refuses to serve; the error message points back to this file and to
`licensing/README.md`.

Internal/test-only override: `CIS2_EVAL_START_FILE` lets you point the
eval clock at an arbitrary path (used by `tests/test_license.sh` /
`server/licensing.py` unit checks so tests don't fight over
`data/eval-start`). Not meant for production use.

See `licensing/EULA.md` (DRAFT, needs attorney review) for the legal
terms this technical check is enforcing.
