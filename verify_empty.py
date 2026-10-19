"""Re-check pairs stored as has_data=0 by fetching them in reverse order (B vs A).
usage: python3 verify_empty.py data/matchups.db
Fills in any pair that turns out to have data; reports how many empties are confirmed."""
import sqlite3, sys, time
from concurrent.futures import ThreadPoolExecutor
from parchment import fetch_matchup

db = sqlite3.connect(sys.argv[1], check_same_thread=False)
empties = db.execute("SELECT a,b FROM matchups WHERE has_data=0").fetchall()
print(len(empties), "empty pairs to re-check")

def chk(p):
    a, b = p
    time.sleep(0.1)
    try:
        return p, fetch_matchup(b, a), None
    except Exception as e:
        return p, None, e

found = errs = 0
with ThreadPoolExecutor(8) as ex:
    for (a, b), m, e in ex.map(chk, empties):
        if e: errs += 1; print("ERR", a, b, e)
        elif m:
            found += 1
            db.execute("UPDATE matchups SET has_data=1,pct_a=?,pct_b=?,ci_a_lo=?,ci_a_hi=?,ci_b_lo=?,ci_b_hi=? WHERE a=? AND b=?",
                       (m["pct_b"], m["pct_a"], m["ci_b_lo"], m["ci_b_hi"], m["ci_a_lo"], m["ci_a_hi"], a, b))
db.commit()
print(f"newly found with data: {found}, errors: {errs}, confirmed empty: {len(empties)-found-errs}")
