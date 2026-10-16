"""Gateway interface -- LLM-5 real implementation (was a stub in v0.1).

Ported from alice-aegis safe-7 (async PENDING/POLL, worker pool, commits
c4140fd/b97e8df) and the c4993e4 capability-token-binding fix. See
gateway/gateway.py for the actual state machine and gateway/README.md for
the escape-test list. This module keeps the small synchronous-looking
surface server/ and verifier/ were written against (`decide()`), built on
top of the real async Gateway via submit_and_wait().
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .gateway import Gateway

_default_gateway = Gateway()


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    PENDING = "PENDING"


@dataclass
class GatewayRequest:
    receipt: dict | None
    tool: str
    action: str


def decide(req: GatewayRequest, gateway: Gateway = _default_gateway, timeout_s: float = 5.0) -> Decision:
    """Fail closed: any exception, missing/unverifiable receipt, or replay
    of an already-seen receipt_id -> DENY, never ALLOW. A verify that has
    not resolved by timeout_s comes back PENDING (never upgraded to ALLOW
    just because time ran out) -- poll again via Gateway.poll()."""
    try:
        result = gateway.submit_and_wait(req.receipt, req.tool, req.action, timeout_s=timeout_s)
    except Exception:
        return Decision.DENY
    return Decision(result["status"])
