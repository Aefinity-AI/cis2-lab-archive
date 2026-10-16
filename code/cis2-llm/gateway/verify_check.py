"""Cheap, dependency-light record integrity check for the gateway.

This recomputes the same canonical-encode + SHA-256 chain rule that
server/app/receipts.py uses when it appends a record (prev_hash + sorted-
key/no-whitespace JSON of the rest of the fields -> log_hash). It is a
tamper check on the receipt record itself: flip any byte in any field and
this fails. It does NOT re-run the vendored cis2-verify2 binary against
the model weights (that heavier, independent-of-the-server check lives in
verifier/cis2_verify_cli.py and needs the vendored binary + weights built
-- not available on every box, see docs/DEPLOY.md). Gateways that also
want that heavier check can pass a different verify_fn into Gateway(); the
default here is what keeps this port "Python stdlib + what
server/pyproject.toml already has" per the LLM-5 brief.
"""
from __future__ import annotations

import hashlib
import json


def _canonical(record: dict) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


def check_record(receipt: dict) -> tuple[bool, list[str]]:
    """Recompute log_hash from the record body; PASS iff it matches.

    Fails (False, [...]) on: missing receipt_id, missing log_hash, missing
    prev_hash, or a recomputed hash that does not match the stored one
    (tamper). Never raises for a malformed dict -- callers (Gateway) treat
    any exception as DENY anyway, but this function itself degrades to a
    clean False/reason list so problems are legible in DENY reasons.
    """
    problems: list[str] = []
    if not isinstance(receipt, dict):
        return False, ["receipt is not an object"]
    if not receipt.get("receipt_id"):
        problems.append("missing receipt_id")
    stored_hash = receipt.get("log_hash")
    if not stored_hash:
        problems.append("missing log_hash")
    if receipt.get("prev_hash") is None:
        problems.append("missing prev_hash")
    if problems:
        return False, problems

    check = dict(receipt)
    check.pop("log_hash", None)
    recomputed = hashlib.sha256(_canonical(check)).hexdigest()
    if recomputed != stored_hash:
        return False, [f"log_hash mismatch: stored={stored_hash} recomputed={recomputed} (tampered record)"]
    return True, []
