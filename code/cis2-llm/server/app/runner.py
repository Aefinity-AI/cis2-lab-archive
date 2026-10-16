"""Thin wrapper around the vendored cis2-verify2 binary.

v0.1 scope: cis2-verify2 (vendored verbatim from cis2-spec, see
verifier/vendor/cis2-verify2/VENDOR.md) only ever computes ONE thing: the
spec's pinned §13.1 reference vector — SmolLM2-135M, fp32, prompt "Once
upon a time", 16 greedy tokens. It takes no CLI arguments and reads
./weights/{model.safetensors,config.json,tokenizer.json} relative to its
cwd. So this v0.1 server does not do general chat completions; it serves
the one receipted computation on demand and is honest about that in the
response (`cis2.note`). General prompts are LLM-4/LLM-5 scope (Kaggle
scale validation, gateway integration) — see docs/CLAIMS.md.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parent.parent.parent / "verifier" / "vendor" / "cis2-verify2"
BINARY = VENDOR_DIR / "target" / "release" / "cis2-verify2"

CANONICAL_PROMPT = "Once upon a time"

_LINE_RE = {
    "witness_digest": re.compile(r"^CIS2_VERIFY2 digest=([0-9a-f]+)"),
    "argmax_digest": re.compile(r"^argmax_digest=([0-9a-f]+)"),
    "table_digest": re.compile(r"^table_digest=([0-9a-f]+)"),
    "inv_freq_table_digest": re.compile(r"^inv_freq table_digest=([0-9a-f]+)"),
    "generated_token_ids": re.compile(r"^generated_token_ids=\[([0-9, ]+)\]"),
}


class RunnerError(RuntimeError):
    pass


@dataclass
class Cis2Result:
    witness_digest: str
    argmax_digest: str
    table_digest: str
    inv_freq_table_digest: str
    generated_token_ids: list[int]
    raw_stdout: str


def run_reference_vector(timeout_s: int = 120) -> Cis2Result:
    if not BINARY.exists():
        raise RunnerError(
            f"vendored verifier binary not found at {BINARY}; "
            "build it with: cd verifier/vendor/cis2-verify2 && cargo build --release"
        )
    weights_dir = VENDOR_DIR / "weights"
    if not (weights_dir / "model.safetensors").exists():
        raise RunnerError(
            f"weights missing under {weights_dir}; fetch with "
            "verifier/vendor/fetch_weights.sh (see docs/DEPLOY.md)"
        )
    proc = subprocess.run(
        [str(BINARY)],
        cwd=str(VENDOR_DIR),
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    if proc.returncode != 0:
        raise RunnerError(
            f"cis2-verify2 exited {proc.returncode}: stderr={proc.stderr.strip()!r}"
        )
    fields: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        for key, pat in _LINE_RE.items():
            m = pat.match(line)
            if m:
                fields[key] = m.group(1)
    missing = [k for k in _LINE_RE if k not in fields]
    if missing:
        raise RunnerError(f"could not parse cis2-verify2 output, missing {missing}: {proc.stdout!r}")
    token_ids = [int(t) for t in fields["generated_token_ids"].split(",") if t.strip()]
    return Cis2Result(
        witness_digest=fields["witness_digest"],
        argmax_digest=fields["argmax_digest"],
        table_digest=fields["table_digest"],
        inv_freq_table_digest=fields["inv_freq_table_digest"],
        generated_token_ids=token_ids,
        raw_stdout=proc.stdout,
    )
