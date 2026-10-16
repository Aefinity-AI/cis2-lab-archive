#!/usr/bin/env -S python3 -I
"""w6: compare the score outputs of builds P, G, C (lines: w pos top1 bits top2 bits).
usage: analyse.py P.txt G.txt C.txt  -> flip table + exact one-sided 95% bounds.
Margin = f32(top1) - f32(top2) from the CORE-MATH build C (bar item iii)."""
import struct, sys
def load(p):
    r = []
    for l in open(p):
        w, pos, t1, b1, t2, b2 = l.split()
        f = lambda h: struct.unpack("<f", struct.pack("<I", int(h, 16)))[0]
        r.append((int(w), int(pos), int(t1), f(b1), int(t2), f(b2)))
    return r
P, G, C = (load(a) for a in sys.argv[1:4])
assert len(P) == len(G) == len(C), "length mismatch"
def pair(name, A, B, marg):
    d = [(a[0], a[1], a[2], b[2], marg[i][3] - marg[i][5]) for i, (a, b) in enumerate(zip(A, B)) if a[2] != b[2]]
    n = len(A); k = len(d)
    # exact one-sided 95% (Clopper-Pearson) upper bound on the rate
    from math import comb
    def cdf(kk, p): return sum(comb(n, i) * p**i * (1 - p)**(n - i) for i in range(kk + 1))
    lo, hi = 0.0, 1.0
    for _ in range(80):
        m = (lo + hi) / 2
        if cdf(k, m) > 0.05: lo = m
        else: hi = m
    print("PAIR %s n=%d flips=%d upper95=%.3e" % (name, n, k, hi))
    for w, pos, a, b, mg in d:
        print("  FLIP w=%d pos=%d top1_a=%d top1_b=%d margin_in_C=%.6g" % (w, pos, a, b, mg))
    return d
dGC = pair("G_vs_C", G, C, C)
pair("P_vs_C", P, C, C)
pair("P_vs_G", P, G, C)
n = len(C)
ok2 = len(dGC) <= 4 if n >= 100000 else len(dGC) == 0
ok3 = all(abs(x[4]) <= 1e-3 for x in dGC)
print("BAR_ITEMS (ii) flips_allowed=%s (iii) margins_le_1e-3=%s  [item (i) control digests checked by build_w6.sh; N=%d]" % (ok2, ok3, n))
