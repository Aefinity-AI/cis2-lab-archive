#!/usr/bin/env python3
"""From-text check for Qwen3 (and any Llama/Qwen2/Qwen3-shaped config): numpy float32 forward following CIS-2 v0.3b
(sequential sums 5.1/5.3, rsqrt 6.1, pinned exp 6.2, sin/cos 6.3, SiLU 6.4, ln 6.5, RoPE 7, RMSNorm 8, attention 9,
MLP 10, argmax 11.2) plus the Qwen3 per-head q_norm/k_norm = the section 8 RMSNorm applied over each head's head_dim
slice after projection and before RoPE. FTZ/DAZ (1.3) is emulated by flushing subnormals on load and after every
arithmetic operation. Constants come from gpu/cis2_consts.inc (hex-float literals). It also rebuilds the section 12.1
witness (file sha256s, table digest, inv_freq digest, prompt ids, per-step full-vocab logits bits, next id) so its
CIS2_REF digest is directly comparable with the C++ port's. No C++ output is used except the optional --expect compare.
usage: fromtext_forward_qwen3.py PAYLOAD_DIR IDS_FILE GEN_TOKS [--expect HEX64]
Run: uv run --no-project --with numpy python -I fromtext_forward_qwen3.py ... (stdlib + numpy only)."""
import sys, json, re, hashlib, struct
import numpy as np
f32 = np.float32

def fz(a):
    a = np.asarray(a, dtype=f32)
    m = (np.abs(a) < f32(2.0 ** -126)) & (a != 0)
    if m.any():
        a = a.copy(); a[m] = np.copysign(f32(0), a[m])
    return a
def bits(a): return np.ascontiguousarray(a, dtype=f32).view(np.uint32)

D, IDSF, GEN = sys.argv[1], sys.argv[2], int(sys.argv[3])
C = {}
for m in re.finditer(r"CIS2_CONST (float|double) (\w+) = (-?0x[0-9a-fA-F.]+p[+-]\d+)", open(D + "/gpu/cis2_consts.inc").read()):
    C[m.group(2)] = float.fromhex(m.group(3)) if m.group(1) == "double" else f32(float.fromhex(m.group(3)))

def matvecT(WT, x):      # WT [in,out] f32; each output lane strictly left-to-right over k (5.1)
    acc = np.zeros(WT.shape[1], dtype=f32)
    for k in range(WT.shape[0]):
        acc = fz(acc + fz(WT[k] * x[k]))
    return acc
def rms_rows(X, w, eps):  # X [rows,n]; per-row sequential sum of squares (5.3), then (x*inv)*w
    n = X.shape[1]; acc = np.zeros(X.shape[0], dtype=f32); sq = fz(X * X)
    for i in range(n): acc = fz(acc + sq[:, i])
    mean = fz(acc / f32(n)); inv = fz(f32(1) / np.sqrt(fz(mean + eps)))
    return fz(fz(X * inv[:, None]) * w[None, :])

def exp_pinned(x):       # 6.2, vectorised, elementwise identical to the scalar form
    x = np.atleast_1d(fz(x)).astype(f32); res = np.zeros_like(x)
    t = fz(x * C["EXP_LOG2E"]); z0 = fz(t + f32(0.5)); k = np.floor(z0).astype(f32)
    r0 = fz(x - fz(k * C["EXP_C1"])); r = fz(r0 - fz(k * C["EXP_C2"])); r2 = fz(r * r)
    poly = np.full_like(x, C["EXP_P0"])
    for n in range(1, 6): poly = fz(fz(poly * r) + C["EXP_P%d" % n])
    result = fz(fz(fz(poly * r2) + r) + f32(1))
    b = bits(result).astype(np.int64); e = (b >> 23) & 0xFF; ne = e + k.astype(np.int64)
    nb = ((b & ~(0xFF << 23)) | (ne << 23)).astype(np.uint32).view(f32)
    out = np.where(ne <= 0, f32(0), np.where(ne >= 0xFF, f32(np.inf), nb))
    out = np.where(result == 0, result, out)
    out = np.where(x > 88, f32(np.inf), np.where(x < -88, f32(0), out))
    out = np.where(np.isnan(x), f32(np.nan), out)
    return fz(out.astype(f32))
def ln_pinned(x):        # 6.5
    x = f32(x); b = int(bits(np.array([x]))[0]); e = ((b >> 23) & 0xFF) - 126
    m = np.array([(b & 0x807FFFFF) | (126 << 23)], dtype=np.uint32).view(f32)[0]
    if m < C["LOG_SQRTHF"]: e -= 1; m = f32(fz(m + m) - f32(1))
    else: m = f32(m - f32(1))
    z = fz(m * m); poly = C["LOG_P0"]
    for n in range(1, 9): poly = fz(fz(poly * m) + C["LOG_P%d" % n])
    y = fz(fz(poly * m) * z); fe = f32(e)
    y = fz(y + fz(fe * C["LOG_Q1"])); y = fz(y - fz(f32(0.5) * z))
    return f32(fz(fz(m + y) + fz(fe * C["LOG_Q2"])))
def sincos(x):           # 6.3
    xd = np.asarray(x, dtype=f32).astype(np.float64)
    q = xd / C["PI_2_F64"]; a = np.abs(q); t = np.floor(a); t = np.where(a - t >= 0.5, t + 1.0, t)
    k_f = np.where(q < 0, -t, t)
    r = fz((xd - k_f * C["PI_2_F64"]).astype(f32)); k = k_f.astype(np.int64); r2 = fz(r * r)
    inner = C["SIN_C2"]; inner = fz(fz(inner * r2) + C["SIN_C1"]); inner = fz(fz(inner * r2) + C["SIN_C0"])
    sr = fz(r + fz(inner * fz(r2 * r)))
    inner = C["COS_C2"]; inner = fz(fz(inner * r2) + C["COS_C1"]); inner = fz(fz(inner * r2) + C["COS_C0"])
    r4 = fz(r2 * r2); cr = fz(fz(f32(1) - fz(f32(0.5) * r2)) + fz(inner * r4))
    q4 = ((k % 4) + 4) % 4
    s = np.where(q4 == 0, sr, np.where(q4 == 1, cr, np.where(q4 == 2, -sr, -cr)))
    c = np.where(q4 == 0, cr, np.where(q4 == 1, -sr, np.where(q4 == 2, -cr, sr)))
    return s.astype(f32), c.astype(f32)
def silu(x): return fz(x / fz(f32(1) + exp_pinned(-x)))

# ---- load (bf16 -> f32 exact widening, DAZ on load); keep weights transposed [in,out] for lane-sequential matvec
cfg = json.load(open(D + "/weights/config.json"))
Hd, NH, NKV, NL, V = cfg["hidden_size"], cfg["num_attention_heads"], cfg["num_key_value_heads"], cfg["num_hidden_layers"], cfg["vocab_size"]
hd = cfg.get("head_dim", Hd // NH); group = NH // NKV; eps = f32(cfg["rms_norm_eps"]); theta = cfg["rope_theta"]
tied = cfg.get("tie_word_embeddings", True)
fp = open(D + "/weights/model.safetensors", "rb")
hl = struct.unpack("<Q", fp.read(8))[0]; hdr = json.loads(fp.read(hl)); base = 8 + hl
mm = np.memmap(D + "/weights/model.safetensors", dtype=np.uint8, mode="r")
def T(name, transpose=False):
    h = hdr[name]; a, b = h["data_offsets"]; assert h["dtype"] == "BF16"
    u = np.frombuffer(mm[base + a:base + b].tobytes(), dtype="<u2").astype(np.uint32) << 16
    arr = fz(u.view(f32).reshape(h["shape"]))
    return np.ascontiguousarray(arr.T) if transpose else arr
def opt(name, transpose=False): return T(name, transpose) if name in hdr else None
Lw = []
for l in range(NL):
    p = f"model.layers.{l}."
    d = {n: T(p + n + ".weight") for n in ["input_layernorm", "post_attention_layernorm"]}
    for n in ["self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj", "self_attn.o_proj", "mlp.gate_proj", "mlp.up_proj", "mlp.down_proj"]:
        d[n] = T(p + n + ".weight", True)
    for n in ["self_attn.q_norm", "self_attn.k_norm"]: d[n] = opt(p + n + ".weight")
    for n in ["q", "k", "v"]: d[n + "_bias"] = opt(p + f"self_attn.{n}_proj.bias")
    Lw.append(d)
emb = T("model.embed_tokens.weight"); fnorm = T("model.norm.weight")
headT = np.ascontiguousarray(emb.T) if tied else T("lm_head.weight", True)

# ---- inv_freq (7.2), scale
ln_theta = ln_pinned(f32(theta))
inv_freq = np.array([exp_pinned(-fz(f32(2 * i) / f32(hd) * ln_theta))[0] for i in range(hd // 2)], dtype=f32)
inv_freq_digest = hashlib.sha256(inv_freq.astype("<f4").tobytes()).hexdigest()
scale = fz(f32(1) / np.sqrt(f32(hd)))

def rope(x, nheads, pos):
    x = x.reshape(nheads, hd).copy(); half = hd // 2
    s, c = sincos(fz(f32(pos) * inv_freq))
    x1, x2 = x[:, :half], x[:, half:]
    return np.concatenate([fz(fz(x1 * c) + fz(fz(-x2) * s)), fz(fz(x2 * c) + fz(x1 * s))], axis=1)

kc = [[] for _ in range(NL)]; vc = [[] for _ in range(NL)]
kvmap = np.arange(NH) // group
def forward(tok, pos):
    h = emb[tok].copy()
    for l in range(NL):
        W = Lw[l]
        ln = rms_rows(h[None], W["input_layernorm"], eps)[0]
        q = matvecT(W["self_attn.q_proj"], ln); k = matvecT(W["self_attn.k_proj"], ln); v = matvecT(W["self_attn.v_proj"], ln)
        if W["q_bias"] is not None: q = fz(q + W["q_bias"]); k = fz(k + W["k_bias"]); v = fz(v + W["v_bias"])
        if W["self_attn.q_norm"] is not None:
            q = rms_rows(q.reshape(NH, hd), W["self_attn.q_norm"], eps).reshape(-1)
            k = rms_rows(k.reshape(NKV, hd), W["self_attn.k_norm"], eps).reshape(-1)
        q = rope(q, NH, pos); k = rope(k, NKV, pos)
        kc[l].append(k); vc[l].append(v.reshape(NKV, hd))
        K = np.stack(kc[l]); Vv = np.stack(vc[l]); n = pos + 1          # [n,NKV,hd]
        Kh = K[:, kvmap, :]; Vh = Vv[:, kvmap, :]                      # [n,NH,hd]
        acc = np.zeros((NH, n), dtype=f32)
        for d in range(hd): acc = fz(acc + fz(q[:, d][:, None] * Kh[:, :, d].T))
        sc = fz(acc * scale)
        mx = sc[:, 0].copy()
        for j in range(1, n): mx = np.where(sc[:, j] > mx, sc[:, j], mx)
        e = exp_pinned(fz(sc - mx[:, None])).reshape(NH, n)
        den = np.zeros(NH, dtype=f32)
        for j in range(n): den = fz(den + e[:, j])
        pr = fz(e / den[:, None])
        out = np.zeros((NH, hd), dtype=f32)
        for j in range(n): out = fz(out + fz(pr[:, j][:, None] * Vh[j]))
        h = fz(h + matvecT(W["self_attn.o_proj"], out.reshape(-1)))
        ln = rms_rows(h[None], W["post_attention_layernorm"], eps)[0]
        g = matvecT(W["mlp.gate_proj"], ln); u = matvecT(W["mlp.up_proj"], ln)
        h = fz(h + matvecT(W["mlp.down_proj"], fz(silu(g) * u)))
    return matvecT(headT, rms_rows(h[None], fnorm, eps)[0])

def argmax(lg):
    bi = 0; bv = lg[0]
    nz = np.nonzero(lg > bv)[0]
    while nz.size:
        bi = int(nz[0]); bv = lg[bi]; nz = np.nonzero(lg > bv)[0]
    return bi

def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.digest()
def f32b(x): return struct.pack("<I", int(bits(np.array([x], dtype=f32))[0]))
tab = hashlib.sha256()
for n in ["EXP_LOG2E", "EXP_C1", "EXP_C2"] + ["EXP_P%d" % i for i in range(6)]: tab.update(f32b(C[n]))
tab.update(struct.pack("<d", C["PI_2_F64"]))
for n in ["SIN_C0", "SIN_C1", "SIN_C2", "COS_C0", "COS_C1", "COS_C2", "LOG_SQRTHF", "LOG_Q1", "LOG_Q2"] + ["LOG_P%d" % i for i in range(9)]: tab.update(f32b(C[n]))
wit = hashlib.sha256()
for p in ["model.safetensors", "tokenizer.json", "config.json"]: wit.update(sha_file(D + "/weights/" + p))
wit.update(tab.digest()); wit.update(bytes.fromhex(inv_freq_digest))
ids = [int(l) for l in open(IDSF).read().split()]
for t in ids: wit.update(struct.pack("<I", t))
print("table_digest=" + tab.hexdigest()); print("inv_freq_table_digest=" + inv_freq_digest, flush=True)

for pos, t in enumerate(ids): lg = forward(t, pos)
allids = list(ids)
for s in range(GEN):
    nid = argmax(lg)
    wit.update(bits(lg).astype("<u4").tobytes()); wit.update(struct.pack("<I", nid)); allids.append(nid)
    lg = forward(nid, len(ids) + s); print("step", s, "token", nid, flush=True)
print("ids=" + str(allids))
dg = wit.hexdigest(); print("FROMTEXT digest=" + dg)
if "--expect" in sys.argv:
    ex = sys.argv[sys.argv.index("--expect") + 1]; print("FROMTEXT", "MATCH" if ex == dg else "MISMATCH", "expected=" + ex)
