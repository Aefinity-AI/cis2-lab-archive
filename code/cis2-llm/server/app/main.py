"""CIS-2 LLM v0.1 scaffold server.

OpenAI-compatible-shaped POST /v1/chat/completions and GET /v1/receipts/{id}.
Every /v1/chat/completions response is backed by a real, replayable CIS-2
receipt for the pinned §13.1 reference vector (see app/runner.py for the
v0.1 scope limit). Receipts append to a hash-chained JSONL log
(app/receipts.py). Never claim "first"; never claim receipts prove output
quality — see docs/CLAIMS.md.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import decode as decode_mod
from . import receipts as receipts_mod
from . import runner

# server/ (parent of this app/ package) holds licensing.py (leg LLM-3).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import licensing as licensing_mod  # noqa: E402

app = FastAPI(title="cis2-llm server", version="0.1.0")
logger = logging.getLogger("cis2_llm.licensing")

LOG_PATH = os.environ.get("CIS2_LLM_RECEIPT_LOG", "data/receipts.jsonl")
log = receipts_mod.ReceiptLog(LOG_PATH)

MODEL_NAME = "cis2-smollm2-135m-fp32-ref"


@app.on_event("startup")
def _check_license() -> None:
    """LLM-3: refuse to start if evaluation expired with no valid
    production license. See server/licensing.py and docs/DEPLOY.md."""
    status = licensing_mod.enforce_at_startup()
    app.state.license_status = status
    logger.info("license check: mode=%s %s", status.mode, status.message)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = MODEL_NAME
    messages: list[ChatMessage]


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/v1/chat/completions")
def chat_completions(req: ChatCompletionRequest):
    if not req.messages:
        raise HTTPException(400, "messages must be non-empty")

    try:
        result = runner.run_reference_vector()
    except runner.RunnerError as e:
        raise HTTPException(500, str(e))

    text = decode_mod.decode(result.generated_token_ids)

    receipt_id = receipts_mod.new_receipt_id()
    record = log.append(
        {
            "receipt_id": receipt_id,
            "created": receipts_mod.now_iso(),
            "model": MODEL_NAME,
            "cis2_version": "v0.3b",
            "witness_digest": result.witness_digest,
            "argmax_digest": result.argmax_digest,
            "table_digest": result.table_digest,
            "inv_freq_table_digest": result.inv_freq_table_digest,
            "generated_token_ids": result.generated_token_ids,
            "prompt": runner.CANONICAL_PROMPT,
        }
    )

    return {
        "id": f"chatcmpl-{receipt_id}",
        "object": "chat.completion",
        "model": MODEL_NAME,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "length",
            }
        ],
        "cis2": {
            "receipt_id": receipt_id,
            "witness_digest": result.witness_digest,
            "log_hash": record["log_hash"],
            "note": (
                "v0.1 scaffold: this receipt covers the pinned CIS-2 v0.3b "
                "reference vector, not free-form generation from the "
                "request messages. See docs/CLAIMS.md."
            ),
        },
    }


@app.get("/v1/receipts/{receipt_id}")
def get_receipt(receipt_id: str):
    rec = log.get(receipt_id)
    if rec is None:
        raise HTTPException(404, "receipt not found")
    return rec


@app.get("/v1/receipts")
def chain_status():
    ok, message = log.verify_chain()
    return {"chain_ok": ok, "message": message}


@app.get("/v1/chain_status")
def chain_status_explicit():
    """Same payload as GET /v1/receipts (kept for compatibility with
    existing callers/tests); this is the explicit, discoverable route
    name. See docs/DEPLOY.md."""
    return chain_status()


class VerifyRequest(BaseModel):
    receipt: dict


@app.post("/verify")
def verify_receipt(req: VerifyRequest):
    """Thin HTTP front for `cis2 verify` — see verifier/cis2_verify_cli.py."""
    import sys
    from pathlib import Path

    verifier_dir = Path(__file__).resolve().parent.parent.parent / "verifier"
    sys.path.insert(0, str(verifier_dir))
    import cis2_verify_cli  # noqa: E402

    ok, problems = cis2_verify_cli.verify(req.receipt)
    return {"ok": ok, "problems": problems}
