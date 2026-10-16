"""FastAPI front for the gateway/gateway.py async state machine.

Not started by `docker compose up` by default -- it is behind the
"gateway" profile in deploy/docker-compose.yml, same as the LLM-1 stub was
(see docs/DEPLOY.md). Run standalone for dev/tests with:
    uv run --project ../server uvicorn gateway.app:app --port 8081
(from the gateway/ directory, or set PYTHONPATH to the repo root).
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel

from .gateway import Gateway

app = FastAPI(title="cis2-llm gateway", version="0.1.0")

_workers = int(os.environ.get("CIS2_GATEWAY_WORKERS", "2"))
gateway = Gateway(workers=_workers)


class SubmitRequest(BaseModel):
    receipt: dict | None = None
    tool: str
    action: str


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/v1/gateway/submit")
def submit(req: SubmitRequest):
    ticket = gateway.submit(req.receipt, req.tool, req.action)
    return gateway.poll(ticket) | {"ticket": ticket}


@app.get("/v1/gateway/poll/{ticket}")
def poll(ticket: str):
    return gateway.poll(ticket) | {"ticket": ticket}
