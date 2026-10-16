#!/usr/bin/env python3
"""Merge a sharded safetensors checkpoint into one model.safetensors, streaming.

Pure I/O: no tensor is decoded or re-encoded; bytes are copied verbatim so the
merged file is byte-for-byte the same data as the shards (only the header changes).
Peak RSS ~ header sizes + a 64 MiB copy buffer.

usage: merge_shards.py <dir-with-index.json-and-shards> <out.safetensors>
"""
import hashlib, json, os, struct, sys

CHUNK = 64 << 20

def read_header(path):
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        hdr = json.loads(f.read(n).decode("utf-8"))
    return hdr, 8 + n  # header dict, data_start offset

def main(src, out):
    index = json.load(open(os.path.join(src, "model.safetensors.index.json")))
    wm = index["weight_map"]
    shards = sorted(set(wm.values()))
    entries = []  # (name, dtype, shape, shard, begin, end)
    for sh in shards:
        hdr, ds = read_header(os.path.join(src, sh))
        for name, meta in hdr.items():
            if name == "__metadata__":
                continue
            if wm.get(name) != sh:
                raise SystemExit(f"index/shard mismatch for {name}: index says {wm.get(name)}, found in {sh}")
            b, e = meta["data_offsets"]
            entries.append((name, meta["dtype"], meta["shape"], sh, ds + b, ds + e))
    if len(entries) != len(wm):
        raise SystemExit(f"tensor count mismatch: shards have {len(entries)}, index lists {len(wm)}")
    # merged header: tensors in shard order, contiguous data offsets
    merged, off = {"__metadata__": {"format": "pt"}}, 0
    for name, dtype, shape, sh, b, e in entries:
        merged[name] = {"dtype": dtype, "shape": shape, "data_offsets": [off, off + (e - b)]}
        off += e - b
    hb = json.dumps(merged, separators=(",", ":")).encode("utf-8")
    hb += b" " * ((8 - len(hb) % 8) % 8)  # 8-byte align, safetensors convention
    tmp = out + ".part"
    h = hashlib.sha256()
    with open(tmp, "wb") as fo:
        pre = struct.pack("<Q", len(hb)) + hb
        fo.write(pre); h.update(pre)
        cur = None
        for i, (name, dtype, shape, sh, b, e) in enumerate(entries):
            if cur is None or cur[0] != sh:
                if cur: cur[1].close()
                cur = (sh, open(os.path.join(src, sh), "rb"))
                print(f"shard {sh}: streaming", flush=True)
            f = cur[1]; f.seek(b); left = e - b
            while left:
                buf = f.read(min(CHUNK, left))
                if not buf: raise SystemExit(f"short read in {sh} at tensor {name}")
                fo.write(buf); h.update(buf); left -= len(buf)
        if cur: cur[1].close()
    os.replace(tmp, out)
    size = os.path.getsize(out)
    print(f"merged {len(entries)} tensors -> {out} size={size} sha256={h.hexdigest()}", flush=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
