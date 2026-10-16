#!/usr/bin/env python3
"""`cis2 verify <receipt-id-or-json-file>` / `cis2 chain <log-file>`

Independent-of-the-server verification: re-runs the vendored cis2-verify2
binary and checks its digests against a stored receipt record (fetched
from the server's log file directly, or passed as a JSON file/blob). Exits
0 and prints PASS on match, exits 1 and prints FAIL otherwise — this is
the same binary used to *issue* the receipt, so this is a replay check
(does the record match what verify2 computes today), not a second
clean-room implementation; cis2-spec's own verify3 (C) already fills that
role for the base spec.

`verify <id>` also checks the hash-chain integrity of the log file up to
and including that receipt (see `_verify_chain_upto` below, which mirrors
app/receipts.py::ReceiptLog.verify_chain — same hash rule, reimplemented
here so the CLI has no import-time dependency on the server package
beyond `app.runner`). `chain <log-file>` checks the whole file. Neither
detects truncation of the log's head or tail (deleted lines at the start,
or an entirely deleted/replaced tail) unless the resulting head hash is
anchored somewhere else (e.g. published, or checked against a server that
has its own copy) — see docs/CLAIMS.md.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "server"))

from app import runner  # noqa: E402

DEFAULT_LOG = REPO_ROOT / "server" / "data" / "receipts.jsonl"

GENESIS_HASH = "0" * 64


def _canonical(record: dict[str, Any]) -> bytes:
    """Deterministic byte encoding for hashing: sorted keys, no whitespace.

    Mirrors app/receipts.py::_canonical exactly (same hash rule). Kept as
    a local copy rather than an import so this CLI's chain check has no
    hidden dependency on server internals beyond the record shape itself;
    tests/test_chain.sh asserts this and the server agree on a sample log.
    """
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _read_log_lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def verify_chain_file(path: Path) -> tuple[bool, str]:
    """Recompute the hash chain from scratch over an entire log file.

    Same rule as app/receipts.py::ReceiptLog.verify_chain: each record's
    log_hash covers the record's own fields (minus log_hash) plus the
    previous record's log_hash (genesis = 64 zero hex chars).
    """
    records = _read_log_lines(path)
    if not records:
        return True, "empty log"
    prev_hash = GENESIS_HASH
    for i, rec in enumerate(records):
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


def verify_chain_upto(path: Path, receipt_id: str) -> tuple[bool, str]:
    """Verify the hash chain from genesis up to and including the line
    whose receipt_id matches. FAILs if the receipt_id is not found, or if
    any line up to and including it breaks the chain."""
    records = _read_log_lines(path)
    prev_hash = GENESIS_HASH
    for i, rec in enumerate(records):
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
        if rec.get("receipt_id") == receipt_id:
            return True, f"chain OK through line {i}"
    return False, f"receipt_id {receipt_id} not found in {path}"


def load_receipt(arg: str) -> tuple[dict, Path | None]:
    """Returns (receipt, log_path). log_path is the JSONL file the receipt
    was sourced from (so the caller can run the chain check against it),
    or None if arg was a bare single-JSON-object blob with no log
    context (in which case the chain check is skipped, not passed)."""
    p = Path(arg)
    if p.exists():
        text = p.read_text().strip()
        # Accept either a bare JSON object or a JSONL log (take the matching
        # or last line).
        if text.startswith("{") and "\n" not in text:
            return json.loads(text), None
        last = None
        for line in text.splitlines():
            if line.strip():
                last = json.loads(line)
        if last is None:
            raise SystemExit(f"no receipts in {p}")
        return last, p
    # Treat arg as a receipt_id, look it up in the default log.
    if not DEFAULT_LOG.exists():
        raise SystemExit(f"{arg} is not a file and default log {DEFAULT_LOG} does not exist")
    for line in DEFAULT_LOG.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("receipt_id") == arg:
            return rec, DEFAULT_LOG
    raise SystemExit(f"receipt_id {arg} not found in {DEFAULT_LOG}")


def verify(receipt: dict, log_path: Path | None) -> tuple[bool, list[str]]:
    problems: list[str] = []
    try:
        result = runner.run_reference_vector()
    except runner.RunnerError as e:
        return False, [f"verifier run failed: {e}"]

    checks = [
        ("witness_digest", result.witness_digest),
        ("argmax_digest", result.argmax_digest),
        ("table_digest", result.table_digest),
        ("inv_freq_table_digest", result.inv_freq_table_digest),
        ("generated_token_ids", result.generated_token_ids),
    ]
    for field, recomputed in checks:
        stored = receipt.get(field)
        if stored != recomputed:
            problems.append(f"{field}: stored={stored!r} recomputed={recomputed!r}")

    receipt_id = receipt.get("receipt_id")
    if log_path is not None and receipt_id is not None:
        chain_ok, chain_msg = verify_chain_upto(log_path, receipt_id)
        if not chain_ok:
            problems.append(f"chain: {chain_msg}")

    return (len(problems) == 0), problems


def main(argv: list[str]) -> int:
    usage = (
        "usage: cis2_verify_cli.py verify <receipt-id-or-json-file>\n"
        "       cis2_verify_cli.py chain [log-file]"
    )
    if len(argv) == 2 and argv[0] == "verify":
        receipt, log_path = load_receipt(argv[1])
        ok, problems = verify(receipt, log_path)
        if ok:
            print(f"PASS receipt_id={receipt.get('receipt_id')} witness_digest={receipt.get('witness_digest')}")
            return 0
        print(f"FAIL receipt_id={receipt.get('receipt_id')}")
        for p in problems:
            print(f"  {p}")
        return 1

    if argv and argv[0] == "chain":
        if len(argv) == 1:
            log_path = DEFAULT_LOG
        elif len(argv) == 2:
            log_path = Path(argv[1])
        else:
            print(usage, file=sys.stderr)
            return 2
        ok, message = verify_chain_file(log_path)
        if ok:
            print(f"PASS chain {log_path}: {message}")
            return 0
        print(f"FAIL chain {log_path}: {message}")
        return 1

    print(usage, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
