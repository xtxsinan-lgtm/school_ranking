"""Bradley-Terry ranking from Parchment cross-admit matchups.

usage: python3 bradley_terry.py data/sheet_matchups.db data/sheet_schools_resolved.csv [--out data/bt_ranking.csv]

Each pair (A,B) has A's enrolled share p (rounded to a whole percent) and a 95% Wilson interval.
Parchment doesn't publish sample size n, so we recover (k, n) -- k = number who chose A -- by
searching for the integer pair whose Wilson interval matches the published one. Then
    P(A chosen over B) = s_A / (s_A + s_B),  s = exp(theta)
is fit by maximum likelihood on binomial counts (so big pairs count more than tiny ones),
with a small L2 ridge on theta so schools with few matchups don't blow up.
"""
import argparse
import csv
import math
import sqlite3

import numpy as np

Z = 1.959964


def wilson(k, n):
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return 100 * (c - h), 100 * (c + h)


def recover_counts(pct, lo, hi, nmax=3000):
    """Best integer (k, n) consistent with rounded pct and published Wilson [lo, hi]."""
    best = None
    for n in range(2, nmax):
        for k in range(max(0, int(n * (pct - 0.5) / 100)), min(n, int(n * (pct + 0.5) / 100) + 1) + 1):
            if abs(100 * k / n - pct) > 0.5:
                continue
            l, h = wilson(k, n)
            err = abs(l - lo) + abs(h - hi)
            if best is None or err < best[0]:
                best = (err, k, n)
    return best  # (err, k, n)


def fit_bt(idx, pairs, ridge=0.5, iters=200):
    """pairs: list of (i, j, k_i_wins, n). Newton on theta with L2 ridge. Returns theta, se."""
    m = len(idx)
    th = np.zeros(m)
    for _ in range(iters):
        g = -ridge * th
        H = -ridge * np.eye(m)
        for i, j, k, n in pairs:
            p = 1 / (1 + math.exp(th[j] - th[i]))
            r = k - n * p
            g[i] += r
            g[j] -= r
            w = n * p * (1 - p)
            H[i, i] -= w; H[j, j] -= w; H[i, j] += w; H[j, i] += w
        step = np.linalg.solve(H, -g)
        th += step
        if np.abs(step).max() < 1e-9:
            break
    cov = np.linalg.inv(-H)
    return th, np.sqrt(np.diag(cov))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db"); ap.add_argument("schools")
    ap.add_argument("--out", default="data/bt_ranking.csv")
    ap.add_argument("--ridge", type=float, default=0.5)
    ap.add_argument("--exclude", nargs="*", default=["Trinity(DC)"], help="abbrs with too few matchups")
    a = ap.parse_args()

    sch = [r for r in csv.DictReader(open(a.schools, encoding="utf8")) if r["abbr"] not in a.exclude]
    ab = {r["parchment_name"]: r["abbr"] for r in sch}
    idx = {r["abbr"]: i for i, r in enumerate(sch)}

    pairs, errs = [], []
    for na, nb, pa, ci_lo, ci_hi in sqlite3.connect(a.db).execute(
            "SELECT a,b,pct_a,ci_a_lo,ci_a_hi FROM matchups WHERE has_data=1"):
        if na not in ab or nb not in ab:
            continue
        err, k, n = recover_counts(pa, ci_lo, ci_hi)
        errs.append(err)
        pairs.append((idx[ab[na]], idx[ab[nb]], k, n))
    print(f"{len(pairs)} pairs; median recovered n={int(np.median([p[3] for p in pairs]))}; "
          f"median CI-fit error={np.median(errs):.2f}pp, 95th pct={np.percentile(errs, 95):.2f}pp")

    th, se = fit_bt(idx, pairs, a.ridge)
    deg = np.zeros(len(sch)); tot = np.zeros(len(sch))
    for i, j, k, n in pairs:
        deg[i] += 1; deg[j] += 1; tot[i] += n; tot[j] += n
    order = np.argsort(-th)
    # rank interval: simulate theta ~ N(th, se^2) (ignores covariances; rough)
    rng = np.random.default_rng(0)
    sims = th + se * rng.standard_normal((2000, len(th)))
    ranks = (-sims).argsort(1).argsort(1) + 1
    lo, hi = np.percentile(ranks, 2.5, axis=0), np.percentile(ranks, 97.5, axis=0)
    usn = {}
    try:
        for r in csv.DictReader(open("data/schools_seed.csv", encoding="utf8")):
            usn[r["name"]] = r["usnews_rank_2027"]
    except FileNotFoundError:
        pass
    with open(a.out, "w", newline="", encoding="utf8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "abbr", "parchment_name", "theta", "se", "rank_lo", "rank_hi", "n_opponents", "total_students"])
        for rk, i in enumerate(order, 1):
            w.writerow([rk, sch[i]["abbr"], sch[i]["parchment_name"], f"{th[i]:.3f}", f"{se[i]:.3f}",
                        int(lo[i]), int(hi[i]), int(deg[i]), int(tot[i])])
    for rk, i in enumerate(order, 1):
        print(f"{rk:3d} {sch[i]['abbr']:<14} theta={th[i]:+.2f} ±{se[i]:.2f}  rank95%=[{int(lo[i])},{int(hi[i])}]  opps={int(deg[i])}")


if __name__ == "__main__":
    main()
