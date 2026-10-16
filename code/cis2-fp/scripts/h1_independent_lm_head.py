#!/usr/bin/env python3
"""cis3-0 / H1: independent (non-cis2_ref) computation of the sha256 of
the fp32-widened lm_head.weight tensor from a merged Qwen2-7B
safetensors file, for cross-checking src/bin/h1_lm_head_check.rs
(stream_widen::load_tensor_streaming) without sharing any code with it.

- Parses the safetensors header manually (same 8-byte little-endian
  length prefix + JSON header cis2_ref's stream_widen.rs parses).
- Uses numpy.memmap to read ONLY the requested tensor's byte range
  (never loads the whole ~14.5 GiB file into RAM).
- Widens bf16 -> fp32 via the textbook method (zero-extend the 16-bit
  bf16 pattern into the high 16 bits of a 32-bit float, i.e. left-shift
  by 16 and reinterpret as float32 bits) -- exact-bit-pattern-preserving,
  same as CIS-2 Sec 3.5's widen_bf16, but implemented independently in
  numpy rather than calling cis2_ref's Rust code.
- Hashes the resulting float32 array's little-endian bytes with
  hashlib.sha256, exactly as h1_lm_head_check.rs hashes
  f.to_le_bytes() per element in ascending index order.

Usage: python3 h1_independent_lm_head.py <path-to-model.safetensors> [tensor-name]
"""
import sys
import json
import struct
import hashlib
import numpy as np


def main():
    path = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 else "lm_head.weight"

    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        header = json.loads(f.read(n))
        data_start = 8 + n

    entry = header[name]
    assert entry["dtype"] == "BF16", entry["dtype"]
    shape = entry["shape"]
    s, e = entry["data_offsets"]
    n_elems = 1
    for d in shape:
        n_elems *= d
    assert (e - s) == n_elems * 2, f"byte range {e-s} != {n_elems*2} for shape {shape}"

    # memmap only the file; slicing below only pages in the needed range.
    mm = np.memmap(path, dtype=np.uint8, mode="r")
    raw = mm[data_start + s : data_start + e]
    bf16_words = raw.view("<u2")  # little-endian uint16, same byte pairing as Rust code
    assert bf16_words.shape[0] == n_elems

    # bf16 -> fp32: zero-extend into the top 16 bits of a uint32, then
    # reinterpret those bits as float32 (exact, matches CIS-2 Sec 3.5).
    bits32 = bf16_words.astype(np.uint32) << np.uint32(16)
    f32 = bits32.view("<f4")

    h = hashlib.sha256()
    # Hash in the same fixed chunk size regardless of array length so
    # this is reproducible; content is what matters (little-endian f32
    # bytes in ascending index order), not the chunk boundaries.
    chunk = 1 << 24
    fb = f32.tobytes()  # little-endian on this platform (x86_64)
    for i in range(0, len(fb), chunk):
        h.update(fb[i : i + chunk])

    print(f"{name} shape={shape} n_elems={n_elems} sha256={h.hexdigest()}")


if __name__ == "__main__":
    main()
