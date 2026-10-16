"""Decode token ids to text using the pinned tokenizer.json (display only;
never part of any digest — the digests are computed by cis2-verify2 over
token ids, not over decoded text)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from tokenizers import Tokenizer

WEIGHTS_DIR = Path(__file__).resolve().parent.parent.parent / "verifier" / "vendor" / "cis2-verify2" / "weights"


@lru_cache(maxsize=1)
def _tokenizer() -> Tokenizer:
    return Tokenizer.from_file(str(WEIGHTS_DIR / "tokenizer.json"))


def decode(token_ids: list[int]) -> str:
    return _tokenizer().decode(token_ids)
