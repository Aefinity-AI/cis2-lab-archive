#!/usr/bin/env python3
"""cis3-0m: reproduce Kaggle's wrong `LAYER_DIGEST embed` from box1's pinned shards.

Run on aefinity-box in ~/projects/cis2-fp-cm-llm8b-stream/weights_qwen2_7b/ (the four
sha256-verified HF shards + model.safetensors.index.json).  It simulates the merged
file that the cis3-0k / LLM-5B / LLM-5c Kaggle kernels produced:

  header data_offsets : assigned iterating weight_map (index.json) order
  data bytes          : written grouped by sorted shard, each shard in weight_map order

and hashes (fp32-widened, same as cis2_ref hash_f32_slice) the 3584 bf16 values that
the Kaggle header labels as model.embed_tokens.weight row 882 (last prompt token).
Result 2026-09-19: 38e87ad1ec58e68ce6a8586a59f5f37c983b3718edb5fe8783b77d41f70f784c
== Kaggle's logged LAYER_DIGEST embed; the bytes actually come from
model.layers.0.mlp.down_proj.weight; 338 of 339 tensors are mislabelled.
"""
import struct, json, hashlib, bisect
H = 3584
wm = json.load(open("model.safetensors.index.json"))["weight_map"]
shards = sorted(set(wm.values()))
names = [n for n in wm if n != "__metadata__"]
print("index order first 4:", names[:4])

def hdr(p):
    f = open(p, "rb"); n = struct.unpack("<Q", f.read(8))[0]; h = json.loads(f.read(n)); return h, 8 + n
LH = {s: hdr(s) for s in shards}

# Kaggle header: offsets in index order
koff = {}; off = 0; plan = {s: [] for s in shards}
for n in names:
    s = wm[n]; h, ds = LH[s]; b, e = h[n]["data_offsets"]
    koff[n] = off; plan[s].append((n, ds + b, e - b)); off += e - b
# Kaggle data layout: shard order, within shard index order
lay = []; cur = 0
for s in shards:
    for n, fo, sz in plan[s]:
        lay.append((cur, s, fo, sz, n)); cur += sz
starts = [l[0] for l in lay]

def kread(merged_off, size):
    i = bisect.bisect_right(starts, merged_off) - 1
    st, s, fo, sz, n = lay[i]; d = merged_off - st; assert d + size <= sz
    f = open(s, "rb"); f.seek(fo + d); r = f.read(size); f.close(); return r, n

def widened_digest(raw):
    s = hashlib.sha256()
    for i in range(0, len(raw), 2):
        s.update(struct.pack("<I", struct.unpack("<H", raw[i:i + 2])[0] << 16))
    return s.hexdigest()

raw, src = kread(koff["model.embed_tokens.weight"] + 882 * H * 2, H * 2)
print("Kaggle-layout embed row 882 actually comes from tensor:", src)
print("simulated Kaggle LAYER_DIGEST embed:", widened_digest(raw))
print("Kaggle logged value                : 38e87ad1ec58e68c...")
mis = sum(1 for st, s, fo, sz, n in lay if koff[n] != st)
print("tensors whose Kaggle header offset != data offset:", mis, "of", len(lay))
