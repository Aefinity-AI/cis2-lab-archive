"""Async receipt-gated gateway -- port of alice-aegis safe-7 (PENDING/POLL,
worker pool, capability tokens bound to the issuing tool) into cis2-llm.

Ported from alice-aegis commits c4140fd/b97e8df (async PENDING/POLL, worker
pool) and c4993e4 (capability tokens bound to the issuing tool, not just
replayable against any tool) -- Rust originals, reimplemented here in
Python stdlib (threading, hmac, uuid, secrets) since cis2-llm ships a
Python server, not the Rust agent_trace binary. Behavior parity, not code
copy; see gateway/README.md for the escape-test list this must pass.

State machine, one ticket per submit():
  PENDING -> ALLOW   (verify_fn(receipt) passed; cap token minted, bound
                       to (receipt_id, tool, action))
  PENDING -> DENY    (verify_fn failed, verify_fn raised, receipt missing/
                       malformed, or receipt_id already seen -- replay)

Fail-closed rules (mirrors alice-aegis's c4140fd doc comment):
  - No receipt, or a receipt missing receipt_id -> DENY immediately, ticket
    still issued so /poll has something to return.
  - The freshness key (receipt_id) is reserved the instant the cheap
    synchronous checks pass, BEFORE the real verify runs on the worker
    thread -- two concurrent submissions of the same receipt_id can never
    both end up ALLOW. The second submission of an already-seen
    receipt_id DENYs synchronously as "replay".
  - Any exception out of verify_fn -> DENY, never ALLOW-by-default.
  - An unknown ticket_id polled -> DENY "unknown ticket", never PENDING or
    ALLOW (fail closed on a caller that guesses/leaks a ticket id).
  - A capability token is bound to (receipt_id, tool, action) via HMAC; it
    is only ever handed out on ALLOW and only verifiable against that
    exact triple (verify_capability), so a token minted for one tool
    cannot be replayed to authorize a different tool/action.
"""
from __future__ import annotations

import hmac
import secrets
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable

from . import verify_check

VerifyFn = Callable[[dict], "tuple[bool, list[str]]"]


@dataclass
class Ticket:
    ticket_id: str
    status: str = "PENDING"  # PENDING | ALLOW | DENY
    reason: str | None = None
    cap_token: str | None = None
    receipt_id: str | None = None
    tool: str | None = None
    action: str | None = None
    created: float = field(default_factory=time.time)


class Gateway:
    def __init__(
        self,
        verify_fn: VerifyFn = verify_check.check_record,
        workers: int = 2,
        cap_secret: bytes | None = None,
    ) -> None:
        self._verify_fn = verify_fn
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="cis2-gateway-verify")
        self._lock = threading.Lock()
        self._tickets: dict[str, Ticket] = {}
        # receipt_id -> first ticket_id that claimed it (freshness / replay guard)
        self._seen_receipts: dict[str, str] = {}
        self._cap_secret = cap_secret or secrets.token_bytes(32)

    def _mint_cap_token(self, receipt_id: str, tool: str, action: str) -> str:
        msg = f"{receipt_id}:{tool}:{action}".encode("utf-8")
        return hmac.new(self._cap_secret, msg, "sha256").hexdigest()

    def verify_capability(self, cap_token: str, receipt_id: str, tool: str, action: str) -> bool:
        """True iff cap_token was minted for exactly this (receipt_id, tool,
        action) triple -- a token minted for tool=A cannot authorize tool=B
        even if the receipt_id and action match (c4993e4 parity)."""
        expected = self._mint_cap_token(receipt_id, tool, action)
        return hmac.compare_digest(expected, cap_token)

    def submit(self, receipt: dict | None, tool: str, action: str) -> str:
        ticket_id = uuid.uuid4().hex

        if not receipt or not isinstance(receipt, dict) or not receipt.get("receipt_id"):
            with self._lock:
                self._tickets[ticket_id] = Ticket(
                    ticket_id=ticket_id,
                    status="DENY",
                    reason="missing or malformed receipt (no receipt_id)",
                    tool=tool,
                    action=action,
                )
            return ticket_id

        receipt_id = receipt["receipt_id"]

        with self._lock:
            prior = self._seen_receipts.get(receipt_id)
            if prior is not None:
                self._tickets[ticket_id] = Ticket(
                    ticket_id=ticket_id,
                    status="DENY",
                    reason=f"replay: receipt_id {receipt_id!r} already submitted (ticket {prior})",
                    receipt_id=receipt_id,
                    tool=tool,
                    action=action,
                )
                return ticket_id
            # Reserve the freshness key before verify runs, even though
            # verify hasn't happened yet -- a concurrent duplicate must see
            # this reservation, not race it.
            self._seen_receipts[receipt_id] = ticket_id
            self._tickets[ticket_id] = Ticket(
                ticket_id=ticket_id,
                status="PENDING",
                receipt_id=receipt_id,
                tool=tool,
                action=action,
            )

        self._executor.submit(self._worker, ticket_id, receipt, tool, action)
        return ticket_id

    def _worker(self, ticket_id: str, receipt: dict, tool: str, action: str) -> None:
        receipt_id = receipt.get("receipt_id")
        try:
            ok, problems = self._verify_fn(receipt)
        except Exception as e:  # fail closed: never let an exception leak to ALLOW
            ok, problems = False, [f"verify_fn raised: {e!r}"]

        with self._lock:
            t = self._tickets[ticket_id]
            if ok:
                t.status = "ALLOW"
                t.cap_token = self._mint_cap_token(receipt_id, tool, action)
                t.reason = None
            else:
                t.status = "DENY"
                t.reason = "; ".join(problems) if problems else "verify failed"

    def poll(self, ticket_id: str) -> dict:
        with self._lock:
            t = self._tickets.get(ticket_id)
        if t is None:
            return {"status": "DENY", "reason": "unknown ticket"}
        out = {"status": t.status}
        if t.status == "DENY":
            out["reason"] = t.reason
        if t.status == "ALLOW":
            out["cap_token"] = t.cap_token
            out["receipt_id"] = t.receipt_id
            out["tool"] = t.tool
            out["action"] = t.action
        return out

    def submit_and_wait(self, receipt: dict | None, tool: str, action: str, timeout_s: float = 5.0) -> dict:
        """Convenience for callers that want a synchronous-looking decide();
        polls submit()'s ticket until resolved or timeout_s elapses (still
        returns PENDING on timeout -- never upgrades a timeout to ALLOW)."""
        ticket_id = self.submit(receipt, tool, action)
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            result = self.poll(ticket_id)
            if result["status"] != "PENDING":
                result["ticket"] = ticket_id
                return result
            time.sleep(0.02)
        result = self.poll(ticket_id)
        result["ticket"] = ticket_id
        return result
