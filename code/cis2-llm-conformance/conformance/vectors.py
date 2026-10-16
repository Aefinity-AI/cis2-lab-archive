"""Vector implementations.

Each vector is a function ``run(ctx) -> VectorResult``. `ctx` carries the
server/gateway URLs and whatever local-repo access is available (the repo
checkout the runner is executing from — used only for vectors that
genuinely need it: independent chain re-verification via the vendored
CLI, local decode() re-checks, and the license-refusal subprocess test).
Vectors never fabricate a PASS: if the thing they need isn't reachable,
they return BLOCKED or NOT_RUN with the concrete reason, never a fake
PASS/FAIL.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_NOT_RUN = "NOT_RUN"
STATUS_BLOCKED = "BLOCKED"


@dataclass
class VectorResult:
    id: str
    status: str
    detail: str
    receipt_ids: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class Context:
    server: str
    gateway: str | None
    timeout: float = 10.0
    local_repo: bool = True  # True iff running from a cis2-llm checkout (this repo)

    def http_json(self, method: str, url: str, body: dict | None = None) -> tuple[int, Any]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                return resp.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, raw.decode("utf-8", "replace")
        except urllib.error.URLError as e:
            raise ConnectionError(f"cannot reach {url}: {e}") from e

    PINNED_MODEL_ID = "cis2-ref-smollm2-135m"

    def post_chat(self, model: str = PINNED_MODEL_ID, content: str = "hello") -> tuple[int, Any]:
        return self.http_json(
            "POST",
            f"{self.server}/v1/chat/completions",
            {"model": model, "messages": [{"role": "user", "content": content}]},
        )

    def post_verify(self, receipt: dict, request: dict | None = None) -> tuple[int, Any]:
        body: dict = {"receipt": receipt}
        if request is not None:
            body["request"] = request
        return self.http_json("POST", f"{self.server}/verify", body)

    def get_receipt(self, receipt_id: str) -> tuple[int, Any]:
        return self.http_json("GET", f"{self.server}/v1/receipts/{receipt_id}")

    def chain_status(self) -> tuple[int, Any]:
        return self.http_json("GET", f"{self.server}/v1/chain_status")


# ---------------------------------------------------------------------------
# 1. receipt schema validity
# ---------------------------------------------------------------------------

REQUIRED_RECEIPT_FIELDS = [
    "receipt_id",
    "created",
    "model",
    "cis2_version",
    "witness_digest",
    "argmax_digest",
    "table_digest",
    "inv_freq_table_digest",
    "generated_token_ids",
    "prompt",
    "prev_hash",
    "log_hash",
]


def v_receipt_schema(ctx: Context) -> VectorResult:
    vid = "receipt_schema"
    try:
        status, body = ctx.post_chat(content="conformance: receipt_schema")
    except ConnectionError as e:
        return VectorResult(vid, STATUS_BLOCKED, str(e))
    if status != 200:
        return VectorResult(vid, STATUS_FAIL, f"POST /v1/chat/completions -> HTTP {status}: {body}")
    rid = body.get("cis2", {}).get("receipt_id")
    if not rid:
        return VectorResult(vid, STATUS_FAIL, "response missing cis2.receipt_id", evidence={"response": body})
    rstatus, receipt = ctx.get_receipt(rid)
    if rstatus != 200:
        return VectorResult(vid, STATUS_FAIL, f"GET /v1/receipts/{rid} -> HTTP {rstatus}", receipt_ids=[rid])
    missing = [f for f in REQUIRED_RECEIPT_FIELDS if f not in receipt]
    if missing:
        return VectorResult(
            vid, STATUS_FAIL, f"receipt missing required field(s): {missing}",
            receipt_ids=[rid], evidence={"receipt": receipt},
        )
    if not isinstance(receipt["generated_token_ids"], list) or not receipt["generated_token_ids"]:
        return VectorResult(
            vid, STATUS_FAIL, "generated_token_ids present but not a non-empty list",
            receipt_ids=[rid], evidence={"receipt": receipt},
        )
    return VectorResult(
        vid, STATUS_PASS,
        f"all {len(REQUIRED_RECEIPT_FIELDS)} required fields present on receipt {rid}",
        receipt_ids=[rid], evidence={"fields_checked": REQUIRED_RECEIPT_FIELDS},
    )


# ---------------------------------------------------------------------------
# 2. chain integrity
# ---------------------------------------------------------------------------

def v_chain_integrity(ctx: Context) -> VectorResult:
    vid = "chain_integrity"
    rids = []
    try:
        for i in range(3):
            status, body = ctx.post_chat(content=f"conformance: chain {i}")
            if status != 200:
                return VectorResult(vid, STATUS_FAIL, f"issuing receipt {i} -> HTTP {status}: {body}")
            rids.append(body["cis2"]["receipt_id"])
        cstatus, cbody = ctx.chain_status()
    except ConnectionError as e:
        return VectorResult(vid, STATUS_BLOCKED, str(e))
    if cstatus != 200:
        return VectorResult(vid, STATUS_FAIL, f"GET /v1/chain_status -> HTTP {cstatus}", receipt_ids=rids)
    if not cbody.get("chain_ok"):
        return VectorResult(
            vid, STATUS_FAIL, f"server reports chain_ok=false: {cbody.get('message')}",
            receipt_ids=rids, evidence={"chain_status": cbody},
        )
    evidence = {"chain_status_endpoint": cbody, "note": "server-self-reported chain_ok only"}
    # Independent re-check via the vendored verifier CLI against the raw
    # log file, IF this runner has local filesystem access to it (only
    # true when --server points at a server this checkout also owns).
    log_path = REPO_ROOT / "server" / "data" / "receipts.jsonl"
    if ctx.local_repo and log_path.exists():
        cli = REPO_ROOT / "verifier" / "cis2_verify_cli.py"
        try:
            out = subprocess.run(
                ["python3", str(cli), "chain", str(log_path)],
                cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60,
            )
        except Exception as e:
            evidence["independent_cli_check"] = f"error running verifier CLI: {e}"
        else:
            evidence["independent_cli_check"] = {
                "returncode": out.returncode, "stdout": out.stdout[-2000:], "stderr": out.stderr[-2000:],
            }
            if out.returncode != 0:
                return VectorResult(
                    vid, STATUS_FAIL,
                    "server reported chain_ok=true but independent verifier CLI chain check FAILED "
                    "(server self-report and independent re-verification disagree)",
                    receipt_ids=rids, evidence=evidence,
                )
    else:
        evidence["independent_cli_check"] = (
            "SKIPPED: no local filesystem access to the server's receipts.jsonl "
            "(runner not colocated with this server instance) — chain_ok here is "
            "the server's own self-report, not independently re-verified"
        )
    return VectorResult(vid, STATUS_PASS, "chain intact over 3 receipts", receipt_ids=rids, evidence=evidence)


# ---------------------------------------------------------------------------
# 3. replay-tamper detection (via gateway)
# ---------------------------------------------------------------------------

def _mk_receipt(receipt_id: str, witness_digest: str = "deadbeef" * 4) -> dict:
    import hashlib
    GENESIS = "0" * 64
    record = {
        "receipt_id": receipt_id,
        "created": "2026-09-19T00:00:00Z",
        "model": "cis2-smollm2-135m-fp32-ref",
        "cis2_version": "v0.3b",
        "witness_digest": witness_digest,
        "prev_hash": GENESIS,
    }
    canon = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    record["log_hash"] = hashlib.sha256(canon).hexdigest()
    return record


def v_replay_tamper(ctx: Context) -> VectorResult:
    vid = "replay_tamper"
    if not ctx.gateway:
        return VectorResult(vid, STATUS_NOT_RUN, "no --gateway URL given to the runner")

    def submit_and_poll(receipt, tool="conf-tool", action="read"):
        status, body = ctx.http_json(
            "POST", f"{ctx.gateway}/v1/gateway/submit",
            {"receipt": receipt, "tool": tool, "action": action},
        )
        if status != 200:
            return None, {"submit_http_status": status, "submit_body": body}
        result = body
        if result.get("status") == "PENDING":
            ticket = result["ticket"]
            for _ in range(50):
                s2, poll = ctx.http_json("GET", f"{ctx.gateway}/v1/gateway/poll/{ticket}")
                if s2 == 200 and poll.get("status") != "PENDING":
                    result = poll
                    break
                time.sleep(0.05)
        return result.get("status"), result

    import uuid

    run_id = uuid.uuid4().hex[:8]  # unique per invocation so re-running this
    # vector against the same long-lived gateway process never collides with
    # a receipt_id "seen" by an earlier run (the gateway's replay guard is
    # process-global and persists across separate `conformance run` calls).
    try:
        legit = _mk_receipt(f"conformance-legit-{run_id}")
        s1, r1 = submit_and_poll(legit)
        if s1 != "ALLOW":
            return VectorResult(
                vid, STATUS_FAIL, f"baseline legit round trip expected ALLOW, got {s1}",
                evidence={"legit_response": r1},
            )
        s2, r2 = submit_and_poll(legit)  # replay same receipt_id

        # Tamper: take a VALID receipt (log_hash correctly covers its
        # fields), then mutate witness_digest AFTER the fact without
        # recomputing log_hash -- log_hash is now stale relative to the
        # (tampered) witness_digest, which is what a real forged/corrupted
        # record looks like. (Building witness_digest into the record
        # before hashing, as _mk_receipt's own log_hash computation does,
        # would produce an internally-consistent record and prove nothing.)
        tampered = _mk_receipt(f"conformance-tamper-{run_id}")
        tampered["witness_digest"] = tampered["witness_digest"][:-1] + (
            "e" if tampered["witness_digest"][-1] != "e" else "f"
        )
        s3, r3 = submit_and_poll(tampered)
    except ConnectionError as e:
        return VectorResult(vid, STATUS_BLOCKED, str(e))

    problems = []
    if s2 != "DENY":
        problems.append(f"replay of same receipt_id expected DENY, got {s2}")
    if s3 != "DENY":
        problems.append(f"tampered witness_digest expected DENY, got {s3}")
    evidence = {"legit": r1, "replay": r2, "tampered": r3}
    if problems:
        return VectorResult(vid, STATUS_FAIL, "; ".join(problems), evidence=evidence)
    return VectorResult(
        vid, STATUS_PASS, "legit->ALLOW, replay->DENY, tampered witness_digest->DENY", evidence=evidence,
    )


# ---------------------------------------------------------------------------
# 4/5. wrong-model / wrong-prompt binding
# ---------------------------------------------------------------------------

def v_wrong_model_binding(ctx: Context) -> VectorResult:
    """cis3-2b: server/app/main.py now (1) rejects any model id other than
    the pinned Context.PINNED_MODEL_ID with HTTP 400 before issuing a
    receipt, and (2) binds every receipt to the request's model id via a
    `model_id` field, checked by POST /verify when a `request` context is
    given. This vector demonstrates both halves rather than asserting
    either."""
    vid = "wrong_model_binding"
    problems = []
    evidence: dict[str, Any] = {}
    try:
        # (1) requesting an unknown model id is rejected at the API boundary.
        status, body = ctx.post_chat(model="definitely-not-the-real-model-xyz", content="conformance: model binding")
        evidence["unknown_model_request"] = {"status": status, "body": body}
        if status != 400:
            problems.append(f"POST /v1/chat/completions with an unknown model id expected HTTP 400, got {status}")

        # (2) a legit receipt for the pinned model, checked via /verify
        # against a request claiming a *different* model id, must DENY.
        s2, legit = ctx.post_chat(content="conformance: model binding legit")
        evidence["legit_response"] = {"status": s2, "body": legit}
        if s2 != 200:
            problems.append(f"baseline legit chat request expected HTTP 200, got {s2}")
        else:
            rid = legit["cis2"]["receipt_id"]
            rstatus, receipt = ctx.get_receipt(rid)
            evidence["receipt"] = receipt
            if rstatus != 200:
                problems.append(f"GET /v1/receipts/{rid} -> HTTP {rstatus}")
            else:
                vstatus, vbody = ctx.post_verify(
                    receipt,
                    request={"model": "some-other-model-id", "messages": [{"role": "user", "content": "conformance: model binding legit"}]},
                )
                evidence["verify_with_mismatched_model"] = {"status": vstatus, "body": vbody}
                if vstatus != 200:
                    problems.append(f"POST /verify -> HTTP {vstatus}")
                elif vbody.get("ok") is not False:
                    problems.append("POST /verify with mismatched model_id expected ok=false, got ok!=false")
    except ConnectionError as e:
        return VectorResult(vid, STATUS_BLOCKED, str(e))

    if problems:
        return VectorResult(vid, STATUS_FAIL, "; ".join(problems), evidence=evidence)
    return VectorResult(
        vid, STATUS_PASS,
        "unknown model id -> HTTP 400 at request time; receipt bound to the wrong model id -> "
        "POST /verify ok=false",
        evidence=evidence,
    )


def v_wrong_prompt_binding(ctx: Context) -> VectorResult:
    """cis3-2b: every receipt now carries a `prompt_digest` = sha256 of the
    request's actual `messages` (server/app/main.py::_canonical_messages_digest),
    not a hash of the fixed reference prompt the runner still always
    computes. This vector shows (1) two different prompts produce two
    different prompt_digests, and (2) POST /verify DENYs a receipt checked
    against a request whose messages don't hash to that bound digest."""
    vid = "wrong_prompt_binding"
    problems = []
    evidence: dict[str, Any] = {}
    try:
        s1, b1 = ctx.post_chat(content="AAAAAAAAAA conformance prompt A")
        s2, b2 = ctx.post_chat(content="ZZZZZZZZZZ this is a completely different prompt B")
        evidence["resp_a"] = b1
        evidence["resp_b"] = b2
        if s1 != 200 or s2 != 200:
            problems.append(f"baseline requests expected HTTP 200, got {s1}/{s2}")
        else:
            rid_a = b1["cis2"]["receipt_id"]
            rid_b = b2["cis2"]["receipt_id"]
            _, receipt_a = ctx.get_receipt(rid_a)
            _, receipt_b = ctx.get_receipt(rid_b)
            evidence["receipt_a_prompt_digest"] = receipt_a.get("prompt_digest")
            evidence["receipt_b_prompt_digest"] = receipt_b.get("prompt_digest")
            if not receipt_a.get("prompt_digest") or not receipt_b.get("prompt_digest"):
                problems.append("one or both receipts missing prompt_digest field")
            elif receipt_a["prompt_digest"] == receipt_b["prompt_digest"]:
                problems.append("two different prompts produced the SAME prompt_digest (no real binding)")

            vstatus, vbody = ctx.post_verify(
                receipt_a,
                request={"model": Context.PINNED_MODEL_ID, "messages": [{"role": "user", "content": "ZZZZZZZZZZ this is a completely different prompt B"}]},
            )
            evidence["verify_receipt_a_against_prompt_b"] = {"status": vstatus, "body": vbody}
            if vstatus != 200:
                problems.append(f"POST /verify -> HTTP {vstatus}")
            elif vbody.get("ok") is not False:
                problems.append("POST /verify of receipt A against prompt B's request expected ok=false, got ok!=false")
    except ConnectionError as e:
        return VectorResult(vid, STATUS_BLOCKED, str(e))

    if problems:
        return VectorResult(vid, STATUS_FAIL, "; ".join(problems), evidence=evidence)
    return VectorResult(
        vid, STATUS_PASS,
        "distinct prompts -> distinct prompt_digest; receipt checked against a mismatched "
        "prompt via POST /verify -> ok=false",
        evidence=evidence,
    )


# ---------------------------------------------------------------------------
# 6. tool-gate deny
# ---------------------------------------------------------------------------

def v_tool_gate_deny(ctx: Context) -> VectorResult:
    """cis3-2b: gateway/tools.yaml + gateway/tool_policy.py add a config-
    driven tool allow/deny list; Gateway.submit() checks it before anything
    receipt-related and DENYs (receipt-logging the refusal to
    gateway/data/tool_denials.jsonl) when the tool isn't allowed. This
    vector submits a VALID receipt against a disallowed tool name (expect
    DENY) and, as a control, the same shape of valid receipt against an
    allowed tool name (expect ALLOW) -- proving the gate is selective, not
    just always-DENY."""
    vid = "tool_gate_deny"
    if not ctx.gateway:
        return VectorResult(vid, STATUS_NOT_RUN, "no --gateway URL given to the runner")

    def submit_and_poll(receipt, tool, action="delete"):
        status, body = ctx.http_json(
            "POST", f"{ctx.gateway}/v1/gateway/submit",
            {"receipt": receipt, "tool": tool, "action": action},
        )
        if status != 200:
            return None, {"submit_http_status": status, "submit_body": body}
        result = body
        if result.get("status") == "PENDING":
            ticket = result["ticket"]
            for _ in range(50):
                s2, poll = ctx.http_json("GET", f"{ctx.gateway}/v1/gateway/poll/{ticket}")
                if s2 == 200 and poll.get("status") != "PENDING":
                    result = poll
                    break
                time.sleep(0.05)
        return result.get("status"), result

    import uuid

    run_id = uuid.uuid4().hex[:8]
    problems = []
    try:
        disallowed_receipt = _mk_receipt(f"conformance-toolgate-deny-{run_id}")
        s1, r1 = submit_and_poll(disallowed_receipt, "disallowed-tool-should-never-be-permitted")
        if s1 != "DENY":
            problems.append(f"valid receipt against a disallowed tool name expected DENY, got {s1}")
        elif "tool gate" not in (r1.get("reason") or ""):
            problems.append(f"DENY reason does not reference the tool gate: {r1.get('reason')!r}")

        allowed_receipt = _mk_receipt(f"conformance-toolgate-allow-{run_id}")
        s2, r2 = submit_and_poll(allowed_receipt, "conf-tool", action="read")
        if s2 != "ALLOW":
            problems.append(f"control: valid receipt against an ALLOWED tool name expected ALLOW, got {s2}")
    except ConnectionError as e:
        return VectorResult(vid, STATUS_BLOCKED, str(e))

    evidence = {"disallowed_tool_result": r1, "allowed_tool_control_result": r2}
    if problems:
        return VectorResult(vid, STATUS_FAIL, "; ".join(problems), evidence=evidence)
    return VectorResult(
        vid, STATUS_PASS,
        "disallowed tool -> DENY (tool gate, receipt-logged); allowed tool -> ALLOW (control)",
        evidence=evidence,
    )


# ---------------------------------------------------------------------------
# 7. license-expired refusal
# ---------------------------------------------------------------------------

def v_license_expired_refusal(ctx: Context) -> VectorResult:
    vid = "license_expired_refusal"
    if not ctx.local_repo:
        return VectorResult(
            vid, STATUS_NOT_RUN,
            "requires spawning a fresh server process with a stale eval-clock file and no "
            "valid production license, then observing it refuse to start — not exercisable "
            "against an already-running --server URL; only runnable from a colocated checkout",
        )
    server_dir = REPO_ROOT / "server"
    if not server_dir.exists() or shutil.which("uv") is None:
        return VectorResult(vid, STATUS_NOT_RUN, "local server/ checkout or `uv` binary not available on this host")

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        eval_start_file = tdp / "eval-start"
        stale = "2020-01-01T00:00:00Z"
        eval_start_file.write_text(stale + "\n")
        port = "8977"
        env = dict(os.environ)
        env["CIS2_LLM_RECEIPT_LOG"] = str(tdp / "receipts.jsonl")
        env["CIS2_EVAL_START_FILE"] = str(eval_start_file)
        env.pop("CIS2_LICENSE_FILE", None)
        env.pop("CIS2_LICENSE_PUBKEY", None)
        log_file = tdp / "server.log"
        with open(log_file, "w") as lf:
            proc = subprocess.Popen(
                ["uv", "run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", port],
                cwd=str(server_dir), env=env, stdout=lf, stderr=subprocess.STDOUT,
            )
        up = False
        deadline = time.time() + 25
        try:
            while time.time() < deadline:
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=1)
                    up = True
                    break
                except Exception:
                    if proc.poll() is not None:
                        break
                    time.sleep(0.5)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
        server_log = log_file.read_text(errors="replace")[-3000:]
        evidence = {"server_returncode": proc.returncode, "server_log_tail": server_log, "eval_start_forced_to": stale}
        if up:
            return VectorResult(
                vid, STATUS_FAIL,
                "server came up healthy despite a stale (expired) eval clock and no valid "
                "production license — expected startup refusal",
                evidence=evidence,
            )
        refused = "Refusing to start" in server_log or "BLOCKED" in server_log or (proc.returncode not in (0, None) and proc.returncode != -15)
        if refused:
            return VectorResult(vid, STATUS_PASS, "server refused to start with expired eval clock / no production license", evidence=evidence)
        return VectorResult(
            vid, STATUS_FAIL,
            "server did not come up but log does not show the expected license-refusal message "
            "(could be an unrelated startup failure — see evidence)",
            evidence=evidence,
        )


# ---------------------------------------------------------------------------
# 8. per-token log completeness
# ---------------------------------------------------------------------------

def v_token_log_completeness(ctx: Context) -> VectorResult:
    vid = "token_log_completeness"
    try:
        status, body = ctx.post_chat(content="conformance: token log completeness")
    except ConnectionError as e:
        return VectorResult(vid, STATUS_BLOCKED, str(e))
    if status != 200:
        return VectorResult(vid, STATUS_FAIL, f"POST /v1/chat/completions -> HTTP {status}")
    rid = body["cis2"]["receipt_id"]
    rstatus, receipt = ctx.get_receipt(rid)
    if rstatus != 200:
        return VectorResult(vid, STATUS_FAIL, f"GET /v1/receipts/{rid} -> HTTP {rstatus}", receipt_ids=[rid])
    ids = receipt.get("generated_token_ids")
    if not isinstance(ids, list) or not ids:
        return VectorResult(vid, STATUS_FAIL, "generated_token_ids missing/empty on receipt", receipt_ids=[rid])
    if any(t is None for t in ids):
        return VectorResult(vid, STATUS_FAIL, "generated_token_ids contains a null/gap entry", receipt_ids=[rid], evidence={"ids": ids})

    evidence = {"num_tokens_logged": len(ids)}
    if ctx.local_repo:
        try:
            sys.path.insert(0, str(REPO_ROOT / "server"))
            from app import decode as decode_mod  # noqa: PLC0415

            recomputed_text = decode_mod.decode(ids)
        except Exception as e:
            evidence["local_decode_recheck"] = f"error: {e}"
        else:
            returned_text = body["choices"][0]["message"]["content"]
            evidence["local_decode_recheck"] = {
                "recomputed_text": recomputed_text,
                "returned_text": returned_text,
                "match": recomputed_text == returned_text,
            }
            if recomputed_text != returned_text:
                return VectorResult(
                    vid, STATUS_FAIL,
                    "decoding the receipt's logged generated_token_ids does not reproduce the "
                    "text actually returned to the caller -- a gap between what was logged and "
                    "what was emitted",
                    receipt_ids=[rid], evidence=evidence,
                )
    else:
        evidence["local_decode_recheck"] = "SKIPPED: no local decode.py access (remote --server only)"

    return VectorResult(
        vid, STATUS_PASS,
        f"{len(ids)} token ids logged with no gaps" + (
            "; independently re-decoded and matched the returned text" if isinstance(evidence.get("local_decode_recheck"), dict) else ""
        ),
        receipt_ids=[rid], evidence=evidence,
    )


VECTORS = {
    "receipt_schema": v_receipt_schema,
    "chain_integrity": v_chain_integrity,
    "replay_tamper": v_replay_tamper,
    "wrong_model_binding": v_wrong_model_binding,
    "wrong_prompt_binding": v_wrong_prompt_binding,
    "tool_gate_deny": v_tool_gate_deny,
    "license_expired_refusal": v_license_expired_refusal,
    "token_log_completeness": v_token_log_completeness,
}
