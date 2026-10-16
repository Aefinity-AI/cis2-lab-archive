"""Hash-chained append-only receipt log for CIS-2 LLM v0.1.

Each receipt record is a JSON line. Every record's `log_hash` covers the
record's own fields plus the previous record's `log_hash` (genesis =
64 zero hex chars), so tampering with any one record breaks the chain from
that point forward. This is a v0.1 scaffold: a single JSONL file behind a
lock, not the postgres-backed log described in deploy/. Swap the storage,
keep the chaining rule.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any

GENESIS_HASH = "0" * 64

_lock = threading.Lock()


def _canonical(record: dict[str, Any]) -> bytes:
    """Deterministic byte encoding for hashing: sorted keys, no whitespace."""
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


class ReceiptLog:
    def __init__(self, path: str | os.PathLike):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def _last_hash(self) -> str:
        last = GENESIS_HASH
        if self.path.stat().st_size == 0:
            return last
        with open(self.path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                last = rec["log_hash"]
        return last

    def append(self, fields: dict[str, Any]) -> dict[str, Any]:
        with _lock:
            prev_hash = self._last_hash()
            record = dict(fields)
            record["prev_hash"] = prev_hash
            digest_input = _canonical(record)
            log_hash = hashlib.sha256(digest_input).hexdigest()
            record["log_hash"] = log_hash
            with open(self.path, "a") as f:
                f.write(json.dumps(record, sort_keys=True) + "\n")
            return record

    def get(self, receipt_id: str) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        with open(self.path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("receipt_id") == receipt_id:
                    return rec
        return None

    def verify_chain(self) -> tuple[bool, str]:
        """Recompute the hash chain from scratch; returns (ok, message)."""
        if not self.path.exists():
            return True, "empty log"
        prev_hash = GENESIS_HASH
        with open(self.path, "r") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                stored_hash = rec.get("log_hash")
                stored_prev = rec.get("prev_hash")
                check = dict(rec)
                check.pop("log_hash", None)
                recomputed = hashlib.sha256(_canonical(check)).hexdigest()
                if stored_prev != prev_hash:
                    return False, f"line {i}: prev_hash mismatch"
                if recomputed != stored_hash:
                    return False, f"line {i}: log_hash mismatch (tampered record)"
                prev_hash = stored_hash
        return True, "chain OK"


def new_receipt_id() -> str:
    return uuid.uuid4().hex


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
