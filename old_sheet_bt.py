"""Run the tier-weighted Bradley-Terry on the user's OLD hand-collected matrix (Google Sheet exported as CSV).

usage: python3 old_sheet_bt.py data/old_sheet.csv [--n 40] [--keep-academies]

CSV layout: header row = column schools; first column = row schools; cell (row i, col j) = % of students
admitted to both who chose the ROW school i. Blanks = no data. The sheet has no sample sizes, so every pair
counts as the same `--n` students after shrinking the share toward 50% (Beta(2,2) prior), i.e. no school gets
an advantage from having more students. Bandwidth is picked by the same CV as weighted_bt.py.
Also prints agreement with the sheet's own row order (assumed to be the sheet author's ranking).
"""
import argparse
import csv
import math

import numpy as np

from weighted_bt import fit, cv_select

ALIAS = {"Georgia Tech": "Gatech", "Geogia Tech": "Gatech", "Wisconsin": "UWM", "George Washington": "GWU",
         "Virginia Tech": "VT", "William and Mary": "W&M", "Texas A & M": "TAMU", "Umich": "Umich", "UMich": "Umich"}
ACADEMIES = {"Naval", "Air Force", "West Point"}


def canon(s):
    s = s.strip()
    return ALIAS.get(s, s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--n", type=float, default=40)
    ap.add_argument("--keep-academies", action="store_true")
    ap.add_argument("--out", default="data/old_sheet_bt_ranking.csv")
    a = ap.parse_args()

    rows = list(csv.reader(open(a.csv, encoding="utf8")))
    cols = [canon(c) for c in rows[0][1:]]
    share = {}
    row_order = []
    for r in rows[1:]:
        ri = canon(r[0])
        row_order.append(ri)
        for cj, v in zip(cols, r[1:]):
            v = v.strip()
            if v and v.replace(".", "").isdigit() and ri != cj:
                share.setdefault((ri, cj), []).append(float(v))          # row school's %
                share.setdefault((cj, ri), []).append(100 - float(v))    # mirrored (col school's %)
    pair = {}
    for (i, j), vs in share.items():
        if (j, i) not in pair:
            pair[(i, j)] = float(np.mean(vs))
    names = sorted({s for p in pair for s in p})
    if not a.keep_academies:
        names = [s for s in names if s not in ACADEMIES]
    idx = {s: k for k, s in enumerate(names)}
    P = []
    for (i, j), p in pair.items():
        if i in idx and j in idx:
            sh = (p / 100 * a.n + 2) / (a.n + 4)        # shrink toward 50%
            P.append((idx[i], idx[j], sh * a.n, a.n))
    P = np.array(P, dtype=float)
    m = len(names)
    print(f"{m} schools, {len(P)} pairs (each counted as n={a.n:g})")

    hs = [0.25, 0.4, 0.6, 1.0, math.inf]
    cv, _ = cv_select(m, P, hs)
    best = max(hs, key=lambda h: cv[h][0])
    th, cov = fit(m, P, best)
    th0, _ = fit(m, P, math.inf)
    order = np.argsort(-th)
    r0 = (-th0).argsort().argsort() + 1
    with open(a.out, "w", newline="", encoding="utf8") as f:
        w = csv.writer(f); w.writerow(["rank", "school", "theta", "plain_bt_rank", "sheet_row_rank", "bandwidth"])
        sheet_rank = {s: k + 1 for k, s in enumerate(row_order)}
        for rk, i in enumerate(order, 1):
            w.writerow([rk, names[i], f"{th[i]:.3f}", int(r0[i]), sheet_rank.get(names[i], ""), best])
            print(f"{rk:3d} {names[i]:<14} theta={th[i]:+.2f}  plain={int(r0[i])}  sheet_row={sheet_rank.get(names[i], '-')}")
    common = [s for s in row_order if s in idx]
    x = np.array([row_order.index(s) for s in common]); y = np.array([list(np.array(names)[order]).index(s) for s in common])
    print(f"best h={best}; Spearman with sheet row order ({len(common)} schools): "
          f"{np.corrcoef(x.argsort().argsort(), y.argsort().argsort())[0,1]:.2f}")


if __name__ == "__main__":
    main()
