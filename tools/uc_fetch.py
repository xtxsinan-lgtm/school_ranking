"""Download UC Information Center "Admissions by source school" crosstabs (Tableau server CSV export).

Sheets: FREthbyYr (counts by race/ethnicity), FRGndbyYr (by gender), FRGPAbyYr (mean HS GPA).
Cached under data/raw_uc/<sheet>/<type>__<term>__<campus>.csv ; re-runnable (existing files skipped).
usage: uc_fetch.py <sheet> [campuses comma list|ALL] [first_term] [last_term]"""
import csv, io, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw_uc"
BASE = "https://visualizedata.ucop.edu/t/Public/views/AdmissionsDataTable/{}.csv"
H = {"User-Agent": "Mozilla/5.0"}
TYPES = ["California public high school", "California private high school", "Non-CA domestic high school", "Foreign institution"]
CAMPUSES = ["Universitywide", "Berkeley", "Davis", "Irvine", "Los Angeles", "Merced", "Riverside", "San Diego", "Santa Barbara", "Santa Cruz"]


def fetch(job):
    sheet, typ, term, campus = job
    p = OUT / sheet / f"{typ.replace(' ', '_')}__{term}__{campus.replace(' ', '_')}.csv"
    if p.exists():
        return job, "cached", p.stat().st_size
    for attempt in range(4):
        try:
            r = requests.get(BASE.format(sheet), params={"Sch Src Type Desc (group)": typ, "Fall Term": term, "Campus": campus},
                             headers=H, timeout=240)
            if r.status_code == 200 and r.text.startswith(("Calculation1", "﻿Calculation1", "Calc")) or (r.status_code == 200 and len(r.text) < 400):
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(r.text, encoding="utf-8")
                return job, "ok", len(r.text)
            err = f"{r.status_code} {r.text[:80]!r}"
        except Exception as e:
            err = repr(e)[:100]
        time.sleep(3 * (attempt + 1))
    return job, "FAIL " + err, 0


if __name__ == "__main__":
    sheet = sys.argv[1]
    camp = CAMPUSES if len(sys.argv) < 3 or sys.argv[2] == "ALL" else sys.argv[2].split(",")
    t0, t1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (1994, 2025)
    jobs = [(sheet, ty, y, c) for y in range(t1, t0 - 1, -1) for c in camp for ty in TYPES]
    done = fail = 0
    with ThreadPoolExecutor(5) as ex:
        for job, st, n in ex.map(fetch, jobs):
            done += 1
            if st.startswith("FAIL"):
                fail += 1
                print(job, st, flush=True)
            if done % 25 == 0:
                print(f"{done}/{len(jobs)} fail={fail}", flush=True)
    print("DONE", done, "fail", fail)
