"""Run the SAME algorithm on the old sheet and on the new Parchment scrape and compare relative ranks.

Algorithm for both: every pair counts as n=40 students after Beta(2,2) shrinkage (no size advantage), tier-weighted
Bradley-Terry with CV-chosen bandwidth, fit on the schools present in both datasets (military academies and the
ambiguous Trinity excluded). usage: python3 compare_old_new.py data/old_sheet.csv data/sheet_matchups.db data/sheet_schools_resolved.csv
"""
import csv
import math
import sqlite3
import sys

import numpy as np

from old_sheet_bt import canon, ACADEMIES
from weighted_bt import fit, cv_select

N = 40
HS = [0.25, 0.4, 0.6, 1.0, math.inf]


def old_pairs(path):
    rows = list(csv.reader(open(path, encoding="utf8")))
    cols = [canon(c) for c in rows[0][1:]]
    acc = {}
    for r in rows[1:]:
        i = canon(r[0])
        for j, v in zip(cols, r[1:]):
            v = v.strip()
            if v.isdigit() and i != j:
                acc.setdefault((i, j), []).append(float(v)); acc.setdefault((j, i), []).append(100 - float(v))
    pair = {}
    for (i, j), vs in acc.items():
        if (j, i) not in pair:
            pair[(i, j)] = float(np.mean(vs))
    return pair


def new_pairs(db, schools):
    ab = {r["parchment_name"]: r["abbr"] for r in csv.DictReader(open(schools, encoding="utf8"))}
    pair = {}
    for a, b, p in sqlite3.connect(db).execute("SELECT a,b,pct_a FROM matchups WHERE has_data=1"):
        pair[(ab[a], ab[b])] = p
    return pair


def run(pair, names):
    idx = {s: k for k, s in enumerate(names)}
    P = np.array([(idx[i], idx[j], ((p / 100 * N + 2) / (N + 4)) * N, N)
                  for (i, j), p in pair.items() if i in idx and j in idx], dtype=float)
    cv, _ = cv_select(len(names), P, HS)
    h = max(HS, key=lambda x: cv[x][0] if not math.isnan(cv[x][0]) else -9)
    th, _ = fit(len(names), P, h)
    return th, h, len(P)


def main(old_csv, db, schools):
    po, pn = old_pairs(old_csv), new_pairs(db, schools)
    so = {s for p in po for s in p}; sn = {s for p in pn for s in p}
    names = sorted((so & sn) - ACADEMIES - {"Trinity", "Trinity(CT)", "Trinity(TX)", "Trinity(DC)"})
    print(f"{len(names)} common schools")
    tho, ho, npo = run(po, names)
    thn, hn, npn = run(pn, names)
    print(f"old: {npo} pairs, h={ho};  new: {npn} pairs, h={hn}")
    ro = (-tho).argsort().argsort() + 1
    rn = (-thn).argsort().argsort() + 1
    zo = (tho - tho.mean()) / tho.std(); zn = (thn - thn.mean()) / thn.std()
    sp = np.corrcoef(ro, rn)[0, 1]
    print(f"Spearman(old rank, new rank) = {sp:.3f}\n")
    order = np.argsort(-np.abs(rn - ro))
    with open("data/old_vs_new_rank_change.csv", "w", newline="", encoding="utf8") as f:
        w = csv.writer(f); w.writerow(["school", "old_rank", "new_rank", "rank_change(old-new)", "old_z", "new_z", "z_change"])
        for i in order:
            w.writerow([names[i], ro[i], rn[i], ro[i] - rn[i], f"{zo[i]:.2f}", f"{zn[i]:.2f}", f"{zn[i]-zo[i]:+.2f}"])
    print("largest relative rank changes (negative = ranks HIGHER in new data):")
    print(f"{'school':<14}{'old':>4}{'new':>5}{'change':>8}{'z_old':>7}{'z_new':>7}")
    for i in order[:25]:
        print(f"{names[i]:<14}{ro[i]:>4}{rn[i]:>5}{ro[i]-rn[i]:>+8}{zo[i]:>+7.2f}{zn[i]:>+7.2f}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
