#!/usr/bin/env python3
"""Compare two raw little-endian fp32 logit dumps (Rust CIS2_DUMP_STEP0_LOGITS
vs. a torch/transformers oracle dump) and print max abs/relative diff. Exit
1 if relative diff exceeds the E15b m1.5 preregistered bar (< 1e-2 * max|logit|).
"""
import struct
import sys

def load(path):
    data = open(path, "rb").read()
    n = len(data) // 4
    return struct.unpack(f"<{n}f", data)

def main():
    rust_path, oracle_path = sys.argv[1], sys.argv[2]
    rust = load(rust_path)
    oracle = load(oracle_path)
    assert len(rust) == len(oracle), f"length mismatch: {len(rust)} vs {len(oracle)}"
    n = len(rust)
    max_abs = 0.0
    max_idx = -1
    max_logit = max(abs(v) for v in rust)
    for i in range(n):
        d = abs(rust[i] - oracle[i])
        if d > max_abs:
            max_abs = d
            max_idx = i
    rel = max_abs / max_logit if max_logit != 0 else 0.0
    print(f"n={n}")
    print(f"max_abs_diff={max_abs} at idx={max_idx} rust={rust[max_idx]} oracle={oracle[max_idx]}")
    print(f"max_abs_logit_rust={max_logit}")
    print(f"relative_max_diff={rel}")
    bar = 1e-2
    if rel >= bar:
        print(f"FAIL: relative diff {rel} >= preregistered bar {bar}")
        sys.exit(1)
    print(f"PASS: relative diff {rel} < preregistered bar {bar}")

if __name__ == "__main__":
    main()
