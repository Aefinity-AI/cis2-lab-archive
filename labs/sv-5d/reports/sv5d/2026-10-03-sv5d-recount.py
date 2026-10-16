#!/usr/bin/env python3
"""sv-5d independent recount (2026-10-03).

Purpose: back, from a file that the ledger hashes, every number in
state/reports/2026-10-03-SV5D-PER-TOKEN-DIVERGENCE.md that is NOT in
state/reports/sv5d/2026-10-03-sv5d-compare.json: the pooled X row, the one-sided lower bounds,
the two-sided intervals, the penguin all-window bound, the near-tie counts, the exact ties in
non-reference runs, and the strictness of the flips.

It does not import sv5d_compare.py. Each npz array is read ONCE into a global position axis.
It also cross-checks the compare JSON (window and position counts, every flip, the margin-shift
statistics) and the sidecar JSON of every file (windows hash, window range, token counts).

Run (penguin has about 2.5 GB usable RAM, so cap the job; peak is about 250 MB):
  systemd-run --user --wait --collect --pipe -p MemoryMax=1500M -p MemorySwapMax=0 \
      python3 <root>/state/reports/sv5d/2026-10-03-sv5d-recount.py

Inputs (read-only):
  <home>/sv5d/<host>/<cell>/pNofM.npz + .json   (raw scan output copied to penguin)
  <home>/feed-payload/sv5b/windows.jsonl         (the 8,000 windows)
  state/reports/sv5d/2026-10-03-sv5d-compare.json                   (cross-check only)
Terms: "argmax" = index 0 of torch.topk(logits, 2); "margin" = fp32 top-1 minus top-2 logit.
"""
import glob
import hashlib
import json
import os
import re
import sys
from math import exp, factorial, lgamma, log, log1p

import numpy as np

ROOT = "<home>/sv5d"
WJ = "<home>/feed-payload/sv5b/windows.jsonl"
CMP = "<root>/state/reports/sv5d/2026-10-03-sv5d-compare.json"
FAILS = []


def check(name, ok):
    print(f"CHECK {name}: {'PASS' if ok else 'FAIL'}")
    if not ok:
        FAILS.append(name)


# ---------------------------------------------------------------- windows
lens = {}
wsha = hashlib.sha256(open(WJ, "rb").read()).hexdigest()
for l in open(WJ):
    r = json.loads(l)
    lens[r["w"]] = len(r["ids"])
print("windows.jsonl sha256", wsha)
print("n windows", len(lens), "ids contiguous 0..7999:", sorted(lens) == list(range(8000)))
L = np.array([lens[w] for w in range(8000)], dtype=np.int64)
print("min/max/mean len", L.min(), L.max(), round(L.mean(), 2), "sum", int(L.sum()))
START = np.concatenate([[0], np.cumsum(L)[:-1]])
N = int(L.sum())


def load_cell(dirs):
    """Full arrays over the global position axis for the windows a cell holds, plus per-window coverage."""
    ids = np.full(N, -1, np.int32)
    sec = np.full(N, -1, np.int32)
    mar = np.full(N, np.nan, np.float32)
    cov = np.zeros(8000, np.int32)
    for d in dirs:
        files = [p for p in sorted(glob.glob(os.path.join(d, "*.npz"))) if not re.search(r"\.c\d+\.npz$", p)]
        assert files, d
        for p in files:
            side = json.load(open(p[:-4] + ".json"))
            assert side["windows_sha256"] == wsha, (p, "windows sha mismatch")
            with np.load(p) as z:
                a, b, c, ix = z["ids"], z["second"], z["margins"], z["index"]
            lo, hi = side["range"]
            ws = ix[:, 0]
            assert list(ws) == list(range(lo, hi)), (p, "index windows != sidecar range")
            assert ix[0, 1] == 0 and np.all(ix[1:, 1] == np.cumsum(ix[:-1, 2])), (p, "offsets not contiguous")
            assert int(ix[:, 2].sum()) == len(a) == len(b) == len(c), (p, "length mismatch")
            assert np.all(ix[:, 2] == L[ws]), (p, "window lengths != windows.jsonl")
            assert side["tokens_scanned_this_run"] == len(a), (p, "sidecar token count")
            for w, off, ln in ix:
                s = START[w]
                ids[s:s + ln] = a[off:off + ln]
                sec[s:s + ln] = b[off:off + ln]
                mar[s:s + ln] = c[off:off + ln]
                cov[w] += 1
            print("  ok", os.path.relpath(p, ROOT), side["host"], side["cpu"][-24:], "thr", side["threads"],
                  "batch", side["batch"], "rng", side["range"], "n", len(a),
                  "torch", side["torch"], "transformers", side["transformers"])
    return ids, sec, mar, cov


cells = {
    "R box1 B1T1": [ROOT + "/box1/B1T1_0-8000"],
    "B box1 B8T1": [ROOT + "/box1/B8T1_0-8000"],
    "T box1 B1T2": [ROOT + "/box1/B1T2_0-2000"],
    "box2 B1T1": [ROOT + "/box2/B1T1_0-4000"],
    "box3 B1T1": [ROOT + "/box3/B1T1_4000-8000"],
    "box3 B8T1": [ROOT + "/box3/B8T1_4000-8000"],
    "peng 0-2000": [ROOT + "/penguin/B1T1_0-2000"],
    "peng 2000-8000": [ROOT + "/penguin/B1T1_2000-8000"],
}
D = {}
for k, dirs in cells.items():
    print("loading", k)
    D[k] = load_cell(dirs)
    cov = D[k][3]
    assert cov.max() <= 1, (k, "window appears more than once")
    print("   windows covered", int((cov == 1).sum()), "range", int(np.nonzero(cov)[0].min()), int(np.nonzero(cov)[0].max()))

R = D["R box1 B1T1"]
assert (R[3] == 1).all(), "R does not cover all 8000"
rid, rsec, rmar, _ = R
print("R: ids range", rid.min(), rid.max(), "sec range", rsec.min(), rsec.max(), "margin min", float(rmar.min()),
      "nan", int(np.isnan(rmar).sum()))
print("R: ids==sec anywhere:", int((rid == rsec).sum()), " margin<0:", int((rmar < 0).sum()),
      " margin==0:", int((rmar == 0).sum()))
T6 = np.float32(5.7220458984375e-06)  # 6 steps of 2^-20, the largest R margin among the flips
print("R: margin<1e-5:", int((rmar < 1e-5).sum()), " <=5.722e-6:", int((rmar <= T6).sum()),
      " <1e-4:", int((rmar < 1e-4).sum()), " of", N)
near = np.nonzero(rmar <= T6)[0]


def wp(g):
    w = int(np.searchsorted(START, g, side="right") - 1)
    return w, int(g - START[w])


print("R positions with margin <= 5.722e-6 (%d):" % len(near))
for g in near:
    print("   w%d/p%d" % wp(g), "R top1/top2/margin", int(rid[g]), int(rsec[g]), float(rmar[g]))


def cmp(name):
    ids, sec, mar, cov = D[name]
    wmask = cov == 1
    pos = np.repeat(wmask, L)  # per-position mask of the windows this cell holds
    n = int(pos.sum())
    flips = np.nonzero(pos & (ids != rid))[0]
    nonid = int((pos & (mar != rmar)).sum())
    d = np.abs(mar[pos].astype(np.float64) - rmar[pos].astype(np.float64))
    out = dict(name=name, windows=int(wmask.sum()), positions=n, flips=len(flips),
               max_abs=float(d.max()), mean_abs=float(d.mean()), share_nonid=nonid / n)
    print(f"\n== {name}: windows {out['windows']} positions {n} flips {len(flips)} rate/M {len(flips)/n*1e6:.4f}"
          f"  margin-not-identical {nonid/n:.4%}  max|dmargin| {out['max_abs']:.7g}  mean|dmargin| {out['mean_abs']:.4g}")
    ties = np.nonzero(pos & (mar == 0))[0]
    print("   exact fp32 ties (margin==0) in this cell:", len(ties), " in R over the same positions:",
          int((pos & (rmar == 0)).sum()))
    for g in ties:
        same = bool(ids[g] == rid[g])
        print("     tie w%d/p%d" % wp(g), "own top1/top2", int(ids[g]), int(sec[g]), "| R top1/top2/margin",
              int(rid[g]), int(rsec[g]), float(rmar[g]), "| own top1 == R top1:", same,
              "(counted as a flip)" if not same else "(not a flip)")
    for g in flips:
        w, p = wp(g)
        swap = (ids[g] == rsec[g]) and (sec[g] == rid[g])
        strict = (rmar[g] > 0) and (mar[g] > 0)
        print(f"   flip w{w}/p{p}  R top1 {int(rid[g])} top2 {int(rsec[g])} margin {float(rmar[g]):.6g} | other top1 "
              f"{int(ids[g])} top2 {int(sec[g])} margin {float(mar[g]):.6g} | exact swap {swap} | strict both sides "
              f"(R margin>0 and own margin>0) {strict} | gap change {float(rmar[g]) + float(mar[g]):.5g} | "
              f"R-margin in 2^-20 units {float(rmar[g])*2**20:.3f}")
    nt = [g for g in near if pos[g]]
    print("   R near-ties (<=5.722e-6) inside this cell:", len(nt), " flipped:", sum(1 for g in nt if ids[g] != rid[g]))
    print("   max R margin among flips:", float(max([rmar[g] for g in flips], default=0.0)))
    return out, flips


res = {}
for k in ["B box1 B8T1", "T box1 B1T2", "box2 B1T1", "box3 B1T1", "box3 B8T1", "peng 0-2000", "peng 2000-8000"]:
    res[k] = cmp(k)

# ---------------------------------------------------------------- pooled X (registered cell)
X2, X3 = D["box2 B1T1"][3], D["box3 B1T1"][3]
posX2, posX3 = np.repeat(X2 == 1, L), np.repeat(X3 == 1, L)
assert not (posX2 & posX3).any(), "X cells overlap"
assert ((X2 + X3) == 1).all(), "X cells do not tile 0..7999"
bx2, bx3 = res["box2 B1T1"][1], res["box3 B1T1"][1]
nX = int(posX2.sum() + posX3.sum())
xf = np.concatenate([bx2, bx3])
print("\n== X pooled (box2 B1T1 w0-3999 + box3 B1T1 w4000-7999): positions", nX, "flips", len(xf),
      "(box2 %d, box3 %d)" % (len(bx2), len(bx3)), f"rate/M {len(xf)/nX*1e6:.4f}")
print("   X cells tile windows 0..7999 exactly, no overlap")
xmar = np.where(posX2, D["box2 B1T1"][2], D["box3 B1T1"][2])
print("   X pooled margin-not-identical %.4f%%" % (100 * float((xmar != rmar).mean())))
print("   X pooled flips: strict on both sides (R margin>0 and own margin>0):",
      all((rmar[g] > 0) and (xmar[g] > 0) for g in xf), "->", len(xf), "of", len(xf))
print("   R near-ties (<=5.722e-6) in X:", len(near), " flipped:", len(xf))
xts = np.nonzero(xmar == 0)[0]
print("   X pooled exact ties (own margin==0):", len(xts), [("w%d/p%d" % wp(g), "own top1 == R top1: %s" % bool(
    np.where(posX2, D['box2 B1T1'][0], D['box3 B1T1'][0])[g] == rid[g])) for g in xts])

B = set(res["B box1 B8T1"][1].tolist())
X = set(xf.tolist())
print("distinct flip positions: B", len(B), "X", len(X), "union", len(B | X), "shared", len(B & X))
print("  B:", sorted(wp(g) for g in B))
print("  X:", sorted(wp(g) for g in X))
print("  union:", sorted(wp(g) for g in (B | X)))
b_wo_tie = [g for g in B if rmar[g] > 0]
print("B without the exact-tie flip(s) (R margin == 0):", len(b_wo_tie), "flips, rate/M %.4f" % (len(b_wo_tie) / N * 1e6))
print("B flips strict on both sides:", sum(1 for g in B if rmar[g] > 0 and D['B box1 B8T1'][2][g] > 0), "of", len(B))

# ---------------------------------------------------------------- penguin
pen_flips = len(res["peng 0-2000"][1]) + len(res["peng 2000-8000"][1])
print("\npenguin all-window flips", pen_flips, "of", N)
for k in ["peng 0-2000", "peng 2000-8000"]:
    ids, sec, mar, cov = D[k]
    pos = np.repeat(cov == 1, L)
    print(k, "ids identical", bool((ids[pos] == rid[pos]).all()), "second identical", bool((sec[pos] == rsec[pos]).all()),
          "margins bit-identical", bool((mar[pos].view(np.uint32) == rmar[pos].view(np.uint32)).all()))
h = hashlib.sha256(rid[: int(START[2000])].astype("<i4").tobytes()).hexdigest()
print("R argmax sha256 w0-1999", h)
print("penguin own sha256 w0-1999", hashlib.sha256(D["peng 0-2000"][0][: int(START[2000])].astype("<i4").tobytes()).hexdigest())

# ---------------------------------------------------------------- the near-tie positions, run by run
# signed gap = (logit of R's top-1 token minus logit of R's top-2 token) as seen by that run, when that run's
# top-2 are the same two tokens (a swap shows as negative); "other" if it is not one of R's two leading tokens.
print("\nNear-tie positions, run by run: signed gap in favour of R's top-1 token (negative = the run prefers R's top-2 token)")
ties_any = set()
for k, (ids, sec, mar, cov) in D.items():
    pos = np.repeat(cov == 1, L)
    ties_any |= set(np.nonzero(pos & (mar == 0))[0].tolist())
interest = sorted(set(near.tolist()) | ties_any)
order = ["R box1 B1T1", "B box1 B8T1", "T box1 B1T2", "box2 B1T1", "box3 B1T1", "box3 B8T1", "peng 0-2000", "peng 2000-8000"]
for g in interest:
    w, p = wp(g)
    parts = []
    for k in order:
        ids, sec, mar, cov = D[k]
        if cov[w] != 1:
            continue
        if ids[g] == rid[g]:
            s = "%+.5g" % float(mar[g])
        elif ids[g] == rsec[g]:
            s = "%+.5g" % (-float(mar[g]))
        else:
            s = "other(top1=%d)" % int(ids[g])
        parts.append(f"{k}: {s}")
    print(f"  w{w}/p{p} R top1/top2 {int(rid[g])}/{int(rsec[g])} | " + " | ".join(parts))

# ---------------------------------------------------------------- cross-check against the compare JSON
print("\nCross-check against", os.path.relpath(CMP, "<root>"))
cj = json.load(open(CMP))
pair = {"box1/B8T1_0-8000": "B box1 B8T1", "box1/B1T2_0-2000": "T box1 B1T2", "box2/B1T1_0-4000": "box2 B1T1",
        "box3/B1T1_4000-8000": "box3 B1T1", "box3/B8T1_4000-8000": "box3 B8T1", "penguin/B1T1_0-2000": "peng 0-2000",
        "penguin/B1T1_2000-8000": "peng 2000-8000"}
check("compare JSON has exactly these 7 pairs", set(cj["pairs"]) == set(pair))
for jk, name in pair.items():
    j = cj["pairs"][jk]
    o, fl = res[name]
    ok = (j["positions_compared"] == o["positions"] and j["positions_argmax_differ"] == o["flips"]
          and j["windows_compared"] == o["windows"])
    jl = sorted((x["window"], x["position"], x["ref_margin"], x["other_margin"], x["ref_top1"], x["ref_top2"], x["other_top1"])
                for x in j["differing"])
    ml = sorted((wp(g)[0], wp(g)[1], float(rmar[g]), float(D[name][2][g]), int(rid[g]), int(rsec[g]), int(D[name][0][g]))
                for g in fl)
    ok = ok and jl == ml
    ok = ok and abs(j["max_abs_margin_diff"] - o["max_abs"]) <= 1e-12 + 1e-9 * abs(o["max_abs"])
    ok = ok and abs(j["mean_abs_margin_diff"] - o["mean_abs"]) <= 1e-12 + 1e-6 * abs(o["mean_abs"])
    ok = ok and abs(j["share_margin_not_identical"] - o["share_nonid"]) <= 1e-12
    check(f"compare JSON == recount for {jk} (counts, every flip, margin-shift stats)", ok)

# ---------------------------------------------------------------- statistics
def _binom_cdf(k, n, p):
    """P(Bin(n,p) <= k), summed in log space."""
    s = 0.0
    for i in range(k + 1):
        s += exp(lgamma(n + 1) - lgamma(i + 1) - lgamma(n - i + 1) + i * log(p) + (n - i) * log1p(-p))
    return s


def cp_upper(x, n, conf=0.95):
    """Exact Clopper-Pearson upper bound at one-sided confidence conf: solves P(Bin(n,p)<=x)=1-conf."""
    a = 1 - conf
    lo, hi = 1e-12, 1.0 - 1e-12
    for _ in range(300):
        m = (lo + hi) / 2
        if _binom_cdf(x, n, m) > a:
            lo = m
        else:
            hi = m
    return hi


def cp_lower(x, n, conf=0.95):
    """Exact Clopper-Pearson lower bound at one-sided confidence conf: solves P(Bin(n,p)<=x-1)=conf."""
    if x == 0:
        return 0.0
    lo, hi = 1e-12, 1.0 - 1e-12
    for _ in range(300):
        m = (lo + hi) / 2
        if _binom_cdf(x - 1, n, m) > conf:
            lo = m
        else:
            hi = m
    return lo


print("\nStats per million. upper95 / lower95 are ONE-SIDED exact 95% bounds; 2s_lo / 2s_hi are the TWO-SIDED exact 95% interval")
print("(each tail 2.5%). P256 = 1-(1-rate)^256 and the same at the upper bound; both assume independent positions, one common rate.")
rows = [("B (box1 B8T1)", 4, N), ("X pooled", 3, N), ("X box2 part", 2, 833394), ("X box3 part", 1, 831570),
        ("T (two threads)", 1, 416030), ("S penguin w0-1999", 0, 416030), ("penguin w2000-7999", 0, 1248934),
        ("penguin all windows", 0, N), ("box3 B8T1 (extra)", 2, 831570),
        ("B without exact-tie flip", 3, N)]
UPPER = {}
for name, x, n in rows:
    u = cp_upper(x, n)
    UPPER[name] = (u, x, n)
    lw = cp_lower(x, n)
    tlo, thi = cp_lower(x, n, 0.975), cp_upper(x, n, 0.975)
    p256 = 1 - (1 - x / n) ** 256
    pu = 1 - (1 - u) ** 256
    print(f"{name:26s} x={x} n={n} rate {x/n*1e6:.4f} upper95 {u*1e6:.4f} lower95 {lw*1e6:.4f} "
          f"2s_lo {tlo*1e6:.4f} 2s_hi {thi*1e6:.4f} P256 {p256:.6f} (1 in {1/p256 if p256 else float('inf'):.0f}) "
          f"P256@upper {pu:.6f} (1 in {1/pu:.0f})")
# the compare JSON's own upper bounds and P(>=1 flip in 256) must agree with this script's bisection
jmap = {"B (box1 B8T1)": "box1/B8T1_0-8000", "X box2 part": "box2/B1T1_0-4000", "X box3 part": "box3/B1T1_4000-8000",
        "T (two threads)": "box1/B1T2_0-2000", "S penguin w0-1999": "penguin/B1T1_0-2000",
        "penguin w2000-7999": "penguin/B1T1_2000-8000", "box3 B8T1 (extra)": "box3/B8T1_4000-8000"}
for name, jk in jmap.items():
    u, x, n = UPPER[name]
    j = cj["pairs"][jk]
    ok = (abs(j["rate_per_million_upper95_clopper_pearson"] - u * 1e6) <= 1e-6 * max(1.0, u * 1e6)
          and abs(j["rate_per_million"] - x / n * 1e6) <= 1e-9
          and abs(j["p_at_least_one_in_256"] - (1 - (1 - x / n) ** 256)) <= 1e-12
          and abs(j["p_at_least_one_in_256_at_upper95"] - (1 - (1 - u) ** 256)) <= 1e-9)
    check(f"compare JSON rate, upper95 and P256 == recount for {jk}", ok)
print("expected positions at 2/M and 4/M (registered prediction):", round(2e-6 * N, 3), round(4e-6 * N, 3))
print("P(0 flips in 51,200 positions) at 2.4025/M (sv-5c comparison): %.3f" % exp(-2.4025e-6 * 51200))
for r in [0.5, 1, 1.8, 2.4]:
    lam = r * 1e-6 * N
    p_lt3 = sum(exp(-lam) * lam ** k / factorial(k) for k in range(3))
    print(f"if the true rate were {r}/M: P(count>=3 in {N} positions) = {1-p_lt3:.3f}")

print("\nSUMMARY: X pooled flips %d (box2 %d, box3 %d) of %d; B flips %d of %d; T %d of %d; penguin %d of %d" % (
    len(xf), len(bx2), len(bx3), nX, len(B), N, len(res['T box1 B1T2'][1]), res['T box1 B1T2'][0]['positions'], pen_flips, N))
print("ALL CHECKS PASS" if not FAILS else "FAILED CHECKS: %s" % FAILS)
sys.exit(1 if FAILS else 0)
