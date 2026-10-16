#!/usr/bin/env python3
"""Fixed prompt -> ids through the OFFICIAL tokenizer.json (HF `tokenizers`, add_special_tokens=False; Qwen adds no BOS).
usage: uv run --no-project --with tokenizers python -I make_ids.py weights/tokenizer.json ids/qwen3-16.txt"""
import sys
from tokenizers import Tokenizer
PROMPT = "Once upon a time"
ids = Tokenizer.from_file(sys.argv[1]).encode(PROMPT, add_special_tokens=False).ids
open(sys.argv[2], "w").write("".join(f"{i}\n" for i in ids)); print(PROMPT, "->", ids)
