"""Scrape every pairwise cross-admit matchup into a resumable SQLite DB.

usage: python3 scrape_pairs.py data/schools_resolved.csv data/matchups.db [--workers 4] [--delay 0.15]

Only rows with match in (exact, fuzzy) are used -- review fuzzy rows first, and
change them to 'exact' (or fix parchment_name) once verified. Each unordered pair
is fetched once (alphabetical order of parchment_name). Safe to Ctrl-C and re-run:
finished pairs (including "no data" ones) are skipped.

Table matchups: a, b, has_data, pct_a, pct_b, ci_a_lo, ci_a_hi, ci_b_lo, ci_b_hi
(percent = share of students admitted to both who enrolled at that school).
"""
import argparse
import csv
import itertools
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from parchment import fetch_matchup

SCHEMA = """CREATE TABLE IF NOT EXISTS matchups(
  a TEXT, b TEXT, has_data INTEGER,
  pct_a REAL, pct_b REAL, ci_a_lo REAL, ci_a_hi REAL, ci_b_lo REAL, ci_b_hi REAL,
  PRIMARY KEY(a, b))"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("schools")
    ap.add_argument("db")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--delay", type=float, default=0.15, help="sleep per request per worker (s)")
    ap.add_argument("--limit", type=int, default=0, help="stop after N new pairs (testing)")
    args = ap.parse_args()

    names = sorted({r["parchment_name"] for r in csv.DictReader(open(args.schools, encoding="utf8"))
                    if r["match"] in ("exact", "fuzzy") and r["parchment_name"]})
    db = sqlite3.connect(args.db, check_same_thread=False)
    db.execute(SCHEMA)
    done = set(db.execute("SELECT a, b FROM matchups"))
    todo = [p for p in itertools.combinations(names, 2) if p not in done]
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(names)} schools, {len(todo)} pairs to fetch ({len(done)} already done)")

    lock, counter, t0 = threading.Lock(), [0], time.time()

    def work(pair):
        a, b = pair
        time.sleep(args.delay)
        try:
            m = fetch_matchup(a, b)
        except Exception as e:
            print("FAIL", pair, e)
            return
        with lock:
            if m is None:
                db.execute("INSERT OR REPLACE INTO matchups(a,b,has_data) VALUES(?,?,0)", (a, b))
            else:
                db.execute("INSERT OR REPLACE INTO matchups VALUES(?,?,1,?,?,?,?,?,?)",
                           (a, b, m["pct_a"], m["pct_b"], m["ci_a_lo"], m["ci_a_hi"], m["ci_b_lo"], m["ci_b_hi"]))
            counter[0] += 1
            if counter[0] % 200 == 0:
                db.commit()
                rate = counter[0] / (time.time() - t0)
                print(f"{counter[0]}/{len(todo)}  {rate:.1f} req/s  eta {(len(todo)-counter[0])/rate/60:.0f} min", flush=True)

    with ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(work, todo))
    db.commit()
    n, d = db.execute("SELECT COUNT(*), SUM(has_data) FROM matchups").fetchone()
    print(f"done: {n} pairs stored, {d} with data")


if __name__ == "__main__":
    main()
