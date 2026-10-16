#!/usr/bin/env python3
"""w3 analysis harness: margin-gated verification coverage from the sv-5d CPU fp32 logs.

Spec: state/prereg/w3-PREREG.md (FROZEN rev 2; hash-pinned, never edited here). stdlib + numpy only.
It imports neither sv5d_compare.py nor the sv-5d recount script. Nothing is re-run on a model.

  run_w3.py --out DIR            full analysis (do not start before the START GATE is lifted)
  run_w3.py --out DIR --smoke    smallest pair only (cell T = box1 B1T2 windows 0-1999 against the
                                 reference file box1 B1T1 p0of2); RESULT line is prefixed "SMOKE:"

Sections cited as "PREREG sN" / "step 7.N". See README.md for the function-to-step map.
"""

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DEFAULT_PREREG = os.path.join(REPO, "state", "prereg", "w3-PREREG.md")
DEFAULT_ROOT = os.path.expanduser("~/sv5d")

# --- registered constants (PREREG s3, s7.3b, s9) ---
TAU = 1e-2
TAUS = [1e-6, 1e-5, 1e-4, 2e-4, 1e-3, 1e-2, 1e-1]  # step 7.3(b)
N_EXPECTED = 1664964  # s1, s9
NWIN = 8000
WINDOWS_SHA = "20c94006e05d6b86e52cf92443bc3118cc8c3c2c70cb98c2671823f7b5dafe61"  # sidecar windows_sha256 (sv-5d report / recount)
UNIT = 2.0**-20  # R margins at the flips are exact multiples of this

# Cells: name -> (files relative to ROOT, in_bar, registered)
# Bar cells (sv-5d bar, PREREG s4): X = box2 + box3 composite, B = box1 batch of 8. R is the reference.
CELLS = {
    "R": (["box1/B1T1_0-8000/p0of2.npz", "box1/B1T1_0-8000/p1of2.npz"], False, True),
    "B": (["box1/B8T1_0-8000/p0of1.npz"], True, True),
    "X2": (["box2/B1T1_0-4000/p0of2.npz", "box2/B1T1_0-4000/p1of2.npz"], True, True),
    "X3": (
        ["box3/B1T1_4000-8000/p0of2.npz", "box3/B1T1_4000-8000/p1of2.npz"],
        True,
        True,
    ),
    "T": (["box1/B1T2_0-2000/p0of1.npz"], False, False),
    "box3B8T1": (["box3/B8T1_4000-8000/p0of1.npz"], False, False),
    "pengA": (["penguin/B1T1_0-2000/p0of1.npz"], False, False),
    "pengB": (["penguin/B1T1_2000-8000/p0of1.npz"], False, False),
    "box2B1T2": (["box2/B1T2_0-4000/p0of1.npz"], False, False),
    "box2B8T1": (["box2/B8T1_0-4000/p0of1.npz"], False, False),
    "box3B1T2": (["box3/B1T2_4000-8000/p0of1.npz"], False, False),
}
# Sanity-gate expectations, from the sv-5d report (state/reports/2026-10-03-SV5D-PER-TOKEN-DIVERGENCE.md flip table
# and state/reports/sv5d/2026-10-03-sv5d-recount.out per-cell lines). flip = (window, pos, R top1, R top2, R margin / 2^-20)
EXPECT = {
    "B": dict(
        positions=N_EXPECTED,
        flips=[
            (274, 144, 2166, 2364, 2),
            (1302, 143, 281, 30, 0),
            (3334, 101, 1453, 325, 6),
            (5595, 154, 451, 260, 2),
        ],
        max_shift=0.0001106262,
    ),
    "X2": dict(
        positions=833394,
        flips=[(3334, 101, 1453, 325, 6), (3687, 106, 282, 739, 4)],
        max_shift=9.727478e-05,
    ),
    "X3": dict(
        positions=831570, flips=[(6300, 248, 550, 805, 2)], max_shift=0.0001373291
    ),
    "T": dict(
        positions=416030, flips=[(274, 144, 2166, 2364, 2)], max_shift=6.67572e-05
    ),
    "box3B8T1": dict(
        positions=831570,
        flips=[(5595, 154, 451, 260, 2), (6300, 248, 550, 805, 2)],
        max_shift=0.0001392365,
    ),
    "pengA": dict(positions=416030, flips=[], max_shift=0.0),
    "pengB": dict(positions=1248934, flips=[], max_shift=0.0),
}
R_COUNTS = dict(
    eq0=1, lt1e5=12, lt1e4=123
)  # recount.out line "R: margin<1e-5: 12 <=5.722e-6: 10 <1e-4: 123"; ==0: 1
R_NEAR_T6 = 10


# ----------------------------------------------------------------- step 7.1: manifest
def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def parse_manifest(prereg_path):
    """Appendix A of the PREREG: the fenced block of '<sha256>  <relpath>' lines."""
    txt = open(prereg_path, encoding="utf-8").read()
    app = txt[txt.index("## Appendix A") :]
    rows = re.findall(r"^([0-9a-f]{64})  (\S+\.npz)$", app, flags=re.M)
    return {rel: sha for sha, rel in rows}


def verify_manifest(root, manifest, rels):
    """Hash every file BEFORE it is read. Returns {rel: 'ok'|'missing'|'mismatch'|'not-in-manifest'}."""
    out = {}
    for rel in rels:
        p = os.path.join(root, rel)
        if rel not in manifest:
            out[rel] = "not-in-manifest"
        elif not os.path.isfile(p):
            out[rel] = "missing"
        else:
            out[rel] = "ok" if sha256_file(p) == manifest[rel] else "mismatch"
    return out


# ----------------------------------------------------------------- loading
class Layout:
    """Global position axis from the reference's own window index."""

    def __init__(self):
        self.L = np.zeros(NWIN, np.int64)
        self.start = None

    def finish(self):
        self.start = np.concatenate([[0], np.cumsum(self.L)[:-1]])
        self.N = int(self.L.sum())


def read_npz(root, rel):
    p = os.path.join(root, rel)
    side = json.load(open(p[:-4] + ".json"))
    with np.load(p) as z:
        a, b, c, ix = z["ids"], z["second"], z["margins"], z["index"]
    lo, hi = side["range"]
    ws = ix[:, 0]
    problems = []
    if list(ws) != list(range(lo, hi)):
        problems.append("index windows != sidecar range")
    if not (ix[0, 1] == 0 and np.all(ix[1:, 1] == np.cumsum(ix[:-1, 2]))):
        problems.append("offsets not contiguous")
    if not (
        int(ix[:, 2].sum())
        == len(a)
        == len(b)
        == len(c)
        == side["tokens_scanned_this_run"]
    ):
        problems.append("length mismatch")
    if side["windows_sha256"] != WINDOWS_SHA:
        problems.append("sidecar windows_sha256 differs")
    if np.isnan(c).any():
        problems.append("nan margin")
    return a, b, c, ix, side, problems


def load_cell(root, rels, layout, is_ref):
    """Place a cell's arrays on the global axis. Returns (ids, sec, mar, cov, problems)."""
    parts = [read_npz(root, r) for r in rels]
    problems = [x for pt in parts for x in pt[5]]
    if is_ref:  # reference defines the layout
        for a, b, c, ix, side, pr in parts:
            for w, off, ln in ix:
                layout.L[w] = ln
        layout.finish()
    ids = np.full(layout.N, -1, np.int32)
    sec = np.full(layout.N, -1, np.int32)
    mar = np.full(layout.N, np.nan, np.float32)
    cov = np.zeros(NWIN, np.int32)
    for a, b, c, ix, side, pr in parts:
        for w, off, ln in ix:
            if layout.L[w] != ln:
                problems.append("window %d length differs from reference" % w)
                continue
            s = layout.start[w]
            ids[s : s + ln] = a[off : off + ln]
            sec[s : s + ln] = b[off : off + ln]
            mar[s : s + ln] = c[off : off + ln]
            cov[w] += 1
    if cov.max() > 1:
        problems.append("window appears more than once")
    return ids, sec, mar, cov, problems


# ----------------------------------------------------------------- step 7.3: computation
def wp(layout, g):
    w = int(np.searchsorted(layout.start, g, side="right") - 1)
    return w, int(g - layout.start[w])


def compare_cell(name, cell, ref, layout):
    """7.3(a),(c): flips against R, reference margin at each, margin shifts."""
    ids, sec, mar, cov = cell
    rid, rsec, rmar = ref
    pos = np.repeat(cov == 1, layout.L)
    n = int(pos.sum())
    flips = np.nonzero(pos & (ids != rid))[0]
    d = np.abs(mar[pos].astype(np.float64) - rmar[pos].astype(np.float64))
    rows = []
    for g in flips:
        w, p = wp(layout, g)
        rows.append(
            dict(
                cell=name,
                window=w,
                pos=p,
                ref_top1=int(rid[g]),
                ref_top2=int(rsec[g]),
                own_top1=int(ids[g]),
                own_top2=int(sec[g]),
                ref_margin=float(rmar[g]),
                own_margin=float(mar[g]),
                shift_abs=abs(float(mar[g]) - float(rmar[g])),
                gap_change=float(rmar[g]) + float(mar[g]),
                swap=bool(ids[g] == rsec[g] and sec[g] == rid[g]),
                ref_margin_units=float(rmar[g]) / UNIT,
            )
        )
    return dict(
        name=name,
        windows=int((cov == 1).sum()),
        positions=n,
        flips=rows,
        max_shift=float(d.max()) if n else 0.0,
    ), flips


def tau_table(rmar, n):
    """7.3(b): count and fraction of positions with reference margin <= tau (float32 margin upcast to float64)."""
    m64 = rmar.astype(np.float64)
    out = []
    for t in TAUS:
        k = int((m64 <= t).sum())
        out.append(
            dict(tau=t, count=k, fraction=k / n, cp95_upper=clopper_pearson_upper(k, n))
        )
    return out


# ----------------------------------------------------------------- s8: Clopper-Pearson
def clopper_pearson_upper(k, n, alpha=0.05):
    """One-sided (1-alpha) upper bound p_U with P(Binom(n,p_U) <= k) = alpha. Exact binomial cdf, bisection."""
    if k >= n:
        return 1.0
    i = np.arange(0, k + 1, dtype=np.float64)
    lg = np.concatenate(
        [[0.0], np.cumsum(np.log(np.arange(1, n + 1, dtype=np.float64)))]
    )  # lgamma(i+1)
    lc = lg[n] - lg[: k + 1] - lg[n - np.arange(0, k + 1)]

    def cdf(p):
        lp = lc + i * math.log(p) + (n - i) * math.log1p(-p)
        mx = lp.max()
        return math.exp(mx) * float(np.exp(lp - mx).sum())

    lo, hi = k / n, 1.0 - 1e-12
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if cdf(mid) > alpha:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ----------------------------------------------------------------- step 7.2: sanity gate
def sanity_gate(smoke, layout, ref, results, near):
    """Totals must reproduce the sv-5d report before any new number is read. Returns (ok, [(check, ok, detail)])."""
    chk = []

    def c(name, ok, detail=""):
        chk.append((name, bool(ok), detail))

    rid, rsec, rmar = ref
    if not smoke:
        c("R positions == 1,664,964", layout.N == N_EXPECTED, str(layout.N))
        c("R covers windows 0..7999", int((layout.L > 0).sum()) == NWIN, "")
        c(
            "R margin==0 count == 1",
            int((rmar == 0).sum()) == R_COUNTS["eq0"],
            str(int((rmar == 0).sum())),
        )
        c(
            "R margin<1e-5 count == 12",
            int((rmar < 1e-5).sum()) == R_COUNTS["lt1e5"],
            str(int((rmar < 1e-5).sum())),
        )
        c(
            "R margin<1e-4 count == 123",
            int((rmar < 1e-4).sum()) == R_COUNTS["lt1e4"],
            str(int((rmar < 1e-4).sum())),
        )
        c("R margin<=5.722e-6 count == 10", len(near) == R_NEAR_T6, str(len(near)))
    for name, exp in EXPECT.items():
        if name not in results:
            continue
        if smoke and name != "T":
            continue
        r = results[name]
        c(
            "%s positions == %d" % (name, exp["positions"]),
            r["positions"] == exp["positions"],
            str(r["positions"]),
        )
        got = sorted(
            (
                f["window"],
                f["pos"],
                f["ref_top1"],
                f["ref_top2"],
                int(round(f["ref_margin_units"])),
            )
            for f in r["flips"]
        )
        c(
            "%s flip table == report" % name,
            got == sorted(exp["flips"]),
            "got %s" % (got,),
        )
        c(
            "%s flips are exact swaps of R top-2" % name,
            all(f["swap"] for f in r["flips"]),
            "",
        )
        c(
            "%s ref margin is a multiple of 2^-20" % name,
            all(
                abs(f["ref_margin_units"] - round(f["ref_margin_units"])) < 1e-9
                for f in r["flips"]
            ),
            "",
        )
        c(
            "%s max margin shift == report" % name,
            abs(r["max_shift"] - exp["max_shift"])
            <= 1e-5 * max(exp["max_shift"], 1e-12) + 1e-12,
            "%.7g vs %.7g" % (r["max_shift"], exp["max_shift"]),
        )
    if not smoke:
        c("X composite tiles windows 0..7999", True, "checked in main()")
        c(
            "bar flips: B=4, X=3",
            len(results["B"]["flips"]) == 4
            and len(results["X2"]["flips"]) + len(results["X3"]["flips"]) == 3,
            "",
        )
    return all(x[1] for x in chk), chk


# ----------------------------------------------------------------- s9: the bar
def bar(counted_flips, count_tau, n, tau=TAU):
    """cond_i: every counted flip has reference margin <= tau. cond_ii: fraction at tau strictly under 1 %
    (integer test count*100 < n, equivalent to count <= 16,649 for n=1,664,964)."""
    cond_i = all(f["ref_margin"] <= tau for f in counted_flips)
    cond_ii = count_tau * 100 < n
    return cond_i, cond_ii


def write_csv(path, rows, fields):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def inside_repo(path):
    p = os.path.realpath(path)
    return p == REPO or p.startswith(REPO + os.sep)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out", required=True, help="output directory (must be outside the repo)"
    )
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--prereg", default=DEFAULT_PREREG)
    a = ap.parse_args()
    if inside_repo(a.out):
        sys.exit("refusing to write inside the repo: " + a.out)
    os.makedirs(a.out, exist_ok=True)
    log = []

    def say(s):
        print(s)
        log.append(s)

    prefix = "SMOKE: " if a.smoke else ""
    say(
        "%sw3 harness; prereg sha256 %s; mode %s"
        % (prefix, sha256_file(a.prereg), "SMOKE" if a.smoke else "FULL")
    )
    manifest = parse_manifest(a.prereg)
    assert len(manifest) == 14, "Appendix A must list 14 files, found %d" % len(
        manifest
    )

    if a.smoke:  # smallest pair: the reference file covering windows 0-1999 and cell T
        want = {"R": ["box1/B1T1_0-8000/p0of2.npz"], "T": CELLS["T"][0]}
    else:
        want = {k: v[0] for k, v in CELLS.items()}
    allrels = [r for v in want.values() for r in v]
    # (1) hash everything before reading anything
    status = verify_manifest(a.root, manifest, allrels)
    if not a.smoke:  # the manifest is the whole 14; every one is checked in a full run
        status.update(
            verify_manifest(a.root, manifest, [r for r in manifest if r not in status])
        )
    manifest_ok = all(v == "ok" for v in status.values())
    for r, v in sorted(status.items()):
        say("  manifest %-8s %s" % (v, r))
    write_csv(
        os.path.join(a.out, "manifest_check.csv"),
        [
            dict(path=r, status=v, sha256=manifest.get(r, ""))
            for r, v in sorted(status.items())
        ],
        ["path", "status", "sha256"],
    )

    layout = Layout()
    data, excluded = {}, {}
    for i, (name, rels) in enumerate(want.items()):
        if any(status[r] != "ok" for r in rels):
            excluded[name] = "manifest " + ",".join(
                sorted({status[r] for r in rels if status[r] != "ok"})
            )
            continue
        if name != "R" and "R" not in data:
            excluded[name] = "no reference"
            continue
        ids, sec, mar, cov, pr = load_cell(a.root, rels, layout, is_ref=(name == "R"))
        if pr:
            excluded[name] = "; ".join(sorted(set(pr)))
            if name == "R":
                data.pop("R", None)
            continue
        data[name] = (ids, sec, mar, cov)
        say(
            "  loaded %s: %d windows, %d positions"
            % (name, int((cov == 1).sum()), int(np.repeat(cov == 1, layout.L).sum()))
        )
    for k, v in excluded.items():
        say("  EXCLUDED %s: %s" % (k, v))

    registered_missing = (
        [k for k, v in CELLS.items() if v[2] and (k not in data)]
        if not a.smoke
        else [k for k in want if k not in data]
    )
    full_registered = not a.smoke and not registered_missing
    result = dict(
        mode="smoke" if a.smoke else "full", manifest_ok=manifest_ok, excluded=excluded
    )

    verdict, sanity_ok, flips_total, positions, frac, cond_i, cond_ii = (
        "INCONCLUSIVE",
        False,
        0,
        0,
        float("nan"),
        None,
        None,
    )
    if "R" in data:
        rid, rsec, rmar, _ = data["R"]
        ref = (rid, rsec, rmar)
        positions = layout.N
        near = np.nonzero(rmar <= np.float32(5.7220458984375e-06))[0]
        results, allflips = {}, []
        for name in data:
            if name == "R":
                continue
            r, _f = compare_cell(name, data[name], ref, layout)
            results[name] = r
            allflips += r["flips"]
            say(
                "  %s: positions %d flips %d max shift %.7g"
                % (name, r["positions"], len(r["flips"]), r["max_shift"])
            )
        if full_registered:
            ok_tile = bool(((data["X2"][3] + data["X3"][3]) == 1).all())
            posX = np.repeat(data["X2"][3] == 1, layout.L) | np.repeat(
                data["X3"][3] == 1, layout.L
            )
            ok_tile = ok_tile and int(posX.sum()) == layout.N
        sanity_ok, chk = sanity_gate(a.smoke, layout, ref, results, near)
        if full_registered:
            chk = [
                (n, ok_tile if n.startswith("X composite") else ok, d)
                for n, ok, d in chk
            ]
            sanity_ok = all(x[1] for x in chk)
        for n, ok, d in chk:
            say(
                "  sanity %-4s %s %s"
                % ("PASS" if ok else "FAIL", n, d if not ok else "")
            )
        result["sanity_checks"] = [dict(check=n, ok=ok, detail=d) for n, ok, d in chk]

        # quantities below are read only after the sanity gate; they are computed regardless so a failing run can be diagnosed
        tt = tau_table(rmar, layout.N)
        write_csv(
            os.path.join(a.out, "tau_table.csv"),
            tt,
            ["tau", "count", "fraction", "cp95_upper"],
        )
        flipfields = [
            "cell",
            "window",
            "pos",
            "ref_top1",
            "ref_top2",
            "own_top1",
            "own_top2",
            "ref_margin",
            "own_margin",
            "shift_abs",
            "gap_change",
            "swap",
            "ref_margin_units",
        ]
        write_csv(os.path.join(a.out, "flips.csv"), allflips, flipfields)
        write_csv(
            os.path.join(a.out, "cells.csv"),
            [
                dict(
                    cell=n,
                    windows=r["windows"],
                    positions=r["positions"],
                    flips=len(r["flips"]),
                    max_shift=r["max_shift"],
                    in_bar=CELLS[n][1],
                )
                for n, r in results.items()
            ],
            ["cell", "windows", "positions", "flips", "max_shift", "in_bar"],
        )
        counted = [
            f for f in allflips if a.smoke or CELLS[f["cell"]][1]
        ]  # smoke: every compared cell counts (only T is loaded)
        flips_total = len(counted)
        distinct = sorted({(f["window"], f["pos"]) for f in counted})
        row_tau = [t for t in tt if t["tau"] == TAU][0]
        frac = row_tau["fraction"]
        cond_i, cond_ii = bar(counted, row_tau["count"], layout.N)
        zero_ties = [f for f in counted if f["ref_margin"] == 0]
        result.update(
            tau_table=tt,
            counted_flips=counted,
            distinct_counted_positions=len(distinct),
            zero_margin_flips=zero_ties,
            max_counted_ref_margin=max(
                [f["ref_margin"] for f in counted], default=None
            ),
            max_shift_by_cell={n: r["max_shift"] for n, r in results.items()},
            count_threshold_for_1pct=int(math.floor((layout.N - 1) / 100))
            if layout.N
            else None,
        )
        for t in tt:
            say(
                "  tau %-6g count %8d frac %.6g  CP95 upper %.6g"
                % (t["tau"], t["count"], t["fraction"], t["cp95_upper"])
            )
        if not full_registered:
            verdict = (
                "INCONCLUSIVE"  # s9: registered cells missing (always so in smoke)
            )
        elif not sanity_ok:
            verdict = "INVALID"
        elif cond_i and cond_ii:
            verdict = "MET"
        else:
            verdict = "NOT MET"
    result.update(
        verdict=verdict,
        sanity=sanity_ok,
        flips_total=flips_total,
        positions=positions,
        frac_recheck=frac,
        cond_i=cond_i,
        cond_ii=cond_ii,
    )
    if "R" not in data:
        say("  reference cell unavailable")
    mi = "MET" if cond_i else "NOT"
    mii = "MET" if cond_ii else "NOT"
    line = (
        "RESULT: OK w3 sanity=%s flips_total=%d positions=%d frac_recheck=%s tau=%g cond_i=%s cond_ii=%s verdict=%s manifest_sha_ok=%s"
        % (
            "PASS" if sanity_ok else "FAIL",
            flips_total,
            positions,
            "%.7g" % frac if frac == frac else "nan",
            TAU,
            mi,
            mii,
            verdict,
            "yes" if manifest_ok else "no",
        )
    )
    line = prefix + line
    say(line)
    json.dump(
        result, open(os.path.join(a.out, "result.json"), "w"), indent=1, default=str
    )
    open(os.path.join(a.out, "RESULT.txt"), "w").write(line + "\n")
    open(os.path.join(a.out, "run.log"), "w").write("\n".join(log) + "\n")
    # 7.4: script output sha256
    with open(os.path.join(a.out, "SHA256SUMS"), "w") as f:
        for fn in sorted(os.listdir(a.out)):
            if fn != "SHA256SUMS":
                f.write("%s  %s\n" % (sha256_file(os.path.join(a.out, fn)), fn))
        f.write("%s  run_w3.py\n" % sha256_file(os.path.abspath(__file__)))


if __name__ == "__main__":
    main()
