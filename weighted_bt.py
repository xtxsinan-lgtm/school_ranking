"""Tier-weighted Bradley-Terry: each pair (i, j) is weighted by how close the two schools are in strength.

    w_ij = exp(-(theta_i - theta_j)^2 / (2 h^2))      (h = bandwidth; h=inf -> ordinary BT)

theta is refit with these weights, then weights are recomputed from the new theta, until it converges.
The bandwidth h is chosen by 5-fold cross-validation: held-out *near-tier* pairs (|dtheta| < NEAR under the
plain-BT fit) are predicted from a model fit on the other folds, and we keep the h with the best held-out
binomial log-likelihood on those pairs.

usage: python3 weighted_bt.py data/sheet_matchups.db data/sheet_schools_resolved.csv [--keep-academies]
"""
import argparse
import csv
import math
import os
import sqlite3

import numpy as np

from bradley_terry import recover_counts

ACADEMIES = ["Naval", "Air Force", "West Point"]
NEAR = 0.35        # "same tier" for evaluating CV, in plain-BT theta units
RIDGE = 0.5
CACHE = "data/pair_counts.csv"


def load_pairs(db, sch):
    ab = {r["parchment_name"]: r["abbr"] for r in sch}
    idx = {r["abbr"]: i for i, r in enumerate(sch)}
    cache = {}
    if os.path.exists(CACHE):
        cache = {(r["a"], r["b"]): (int(r["k"]), int(r["n"])) for r in csv.DictReader(open(CACHE))}
    rows, new = [], False
    for na, nb, pa, lo, hi in sqlite3.connect(db).execute(
            "SELECT a,b,pct_a,ci_a_lo,ci_a_hi FROM matchups WHERE has_data=1"):
        if (na, nb) not in cache:
            _, k, n = recover_counts(pa, lo, hi)
            cache[(na, nb)] = (k, n)
            new = True
        if na in ab and nb in ab:
            k, n = cache[(na, nb)]
            rows.append((idx[ab[na]], idx[ab[nb]], k, n))
    if new:
        with open(CACHE, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["a", "b", "k", "n"])
            for (a, b), (k, n) in cache.items():
                w.writerow([a, b, k, n])
    return np.array(rows, dtype=float)


def fit(m, P, h, iters=60, theta0=None):
    """Weighted BT fit; returns theta, cov. P columns: i, j, k, n."""
    I, J = P[:, 0].astype(int), P[:, 1].astype(int)
    K, N = P[:, 2], P[:, 3]
    th = np.zeros(m) if theta0 is None else theta0.copy()
    for outer in range(iters):
        w = np.ones(len(P)) if math.isinf(h) else np.exp(-((th[I] - th[J]) ** 2) / (2 * h * h))
        t = th.copy()
        for _ in range(50):
            p = 1 / (1 + np.exp(t[J] - t[I]))
            r = w * (K - N * p)
            g = -RIDGE * t
            np.add.at(g, I, r); np.add.at(g, J, -r)
            v = w * N * p * (1 - p)
            H = -RIDGE * np.eye(m)
            np.add.at(H, (I, I), -v); np.add.at(H, (J, J), -v)
            np.add.at(H, (I, J), v); np.add.at(H, (J, I), v)
            step = np.linalg.solve(H, -g)
            t += step
            if np.abs(step).max() < 1e-9:
                break
        t -= t.mean()
        delta = np.abs(t - th).max()
        th = t
        if math.isinf(h) or delta < 1e-6:
            break
    cov = np.linalg.inv(-H)
    return th, cov


def loglik(th, P):
    I, J = P[:, 0].astype(int), P[:, 1].astype(int)
    p = np.clip(1 / (1 + np.exp(th[J] - th[I])), 1e-6, 1 - 1e-6)
    return float(np.sum(P[:, 2] * np.log(p) + (P[:, 3] - P[:, 2]) * np.log(1 - p)) / P[:, 3].sum())


def cv_select(m, P, hs, folds=5, seed=0):
    th_plain, _ = fit(m, P, math.inf)
    I, J = P[:, 0].astype(int), P[:, 1].astype(int)
    near = np.abs(th_plain[I] - th_plain[J]) < NEAR
    fold = np.random.default_rng(seed).integers(0, folds, len(P))
    out = {}
    for h in hs:
        ll_near, ll_all = [], []
        for f in range(folds):
            th, _ = fit(m, P[fold != f], h)
            te = fold == f
            ll_near.append((loglik(th, P[te & near]), P[te & near][:, 3].sum()))
            ll_all.append((loglik(th, P[te]), P[te][:, 3].sum()))
        wavg = lambda xs: sum(a * b for a, b in xs) / sum(b for _, b in xs)
        out[h] = (wavg(ll_near), wavg(ll_all))
        print(f"  h={h:<5} held-out loglik/student: near-tier {out[h][0]:.4f}   all pairs {out[h][1]:.4f}")
    return out, int(near.sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db"); ap.add_argument("schools")
    ap.add_argument("--keep-academies", action="store_true")
    ap.add_argument("--out", default="data/wbt_ranking.csv")
    a = ap.parse_args()

    drop = ["Trinity(DC)"] + ([] if a.keep_academies else ACADEMIES)
    sch = [r for r in csv.DictReader(open(a.schools, encoding="utf8")) if r["abbr"] not in drop]
    m = len(sch)
    P = load_pairs(a.db, sch)
    print(f"{m} schools, {len(P)} pairs, {int(P[:, 3].sum())} students (estimated)")

    hs = [0.15, 0.25, 0.4, 0.6, 1.0, math.inf]
    print("cross-validation:")
    cvres, nnear = cv_select(m, P, hs)
    print(f"  ({nnear} near-tier pairs in evaluation set)")
    best = max(hs, key=lambda h: cvres[h][0])
    print("best bandwidth:", best)

    th0, cov0 = fit(m, P, math.inf)
    th, cov = fit(m, P, best)
    se = np.sqrt(np.diag(cov))
    rng = np.random.default_rng(0)
    sims = th + rng.multivariate_normal(np.zeros(m), cov, 2000)
    ranks = (-sims).argsort(1).argsort(1) + 1
    lo, hi = np.percentile(ranks, 2.5, axis=0), np.percentile(ranks, 97.5, axis=0)
    r0 = (-th0).argsort().argsort() + 1
    order = np.argsort(-th)
    I, J = P[:, 0].astype(int), P[:, 1].astype(int)
    w = np.exp(-((th[I] - th[J]) ** 2) / (2 * best * best))
    eff = np.zeros(m)
    np.add.at(eff, I, w * P[:, 3]); np.add.at(eff, J, w * P[:, 3])
    with open(a.out, "w", newline="", encoding="utf8") as f:
        wr = csv.writer(f)
        wr.writerow(["rank", "abbr", "parchment_name", "theta", "se", "rank_lo", "rank_hi", "plain_bt_rank", "effective_students", "bandwidth"])
        for rk, i in enumerate(order, 1):
            wr.writerow([rk, sch[i]["abbr"], sch[i]["parchment_name"], f"{th[i]:.3f}", f"{se[i]:.3f}",
                         int(lo[i]), int(hi[i]), int(r0[i]), int(eff[i]), best])
    print(f"\nweighted BT (h={best}) vs plain BT rank:")
    for rk, i in enumerate(order, 1):
        print(f"{rk:3d} {sch[i]['abbr']:<14} theta={th[i]:+.2f} ±{se[i]:.2f} rank95%=[{int(lo[i])},{int(hi[i])}]  plain={int(r0[i])}")
    ab = {s["abbr"]: i for i, s in enumerate(sch)}
    for x, y in [("Harvard", "Yale")]:
        hx, hy = ab[x], ab[y]
        print(f"\n{x} - {y} theta gap: plain {th0[hx]-th0[hy]:+.3f}, weighted {th[hx]-th[hy]:+.3f}")


if __name__ == "__main__":
    main()
