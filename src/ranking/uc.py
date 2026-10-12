"""Load cached UC Information Center crosstabs (tools/uc_fetch.py) into the SQLite DB."""
import csv
import re
from pathlib import Path

from .db import ROOT, connect

RAW = ROOT / "data" / "raw_uc"
MEASURE = {"App": "App", "Adm": "Adm", "Enr": "Enr", "Enrl": "Enr"}


def _int(v):
    v = (v or "").strip().replace(",", "")
    return int(float(v)) if re.fullmatch(r"-?\d+(\.0+)?", v) else None


def _ceeb(calc, school):
    code = calc[len(school):] if calc.startswith(school) else re.search(r"(\d+)$", calc).group(1)
    return code.strip().zfill(6)


def _parse_name(fn):
    typ, term, campus = fn.stem.split("__")
    return typ.replace("_", " "), int(term), campus.replace("_", " ")


def load(sheets=("FREthbyYr", "FRGndbyYr", "FRGPAbyYr")):
    con = connect()
    for sheet in sheets:
        files = sorted((RAW / sheet).glob("*.csv"))
        if not files:
            continue
        table = {"FREthbyYr": "uc_ethnicity", "FRGndbyYr": "uc_gender", "FRGPAbyYr": "uc_gpa"}[sheet]
        con.execute(f"DELETE FROM {table}")
        n = 0
        for fn in files:
            typ, term, campus = _parse_name(fn)
            with open(fn, newline="", encoding="utf-8-sig") as f:
                rd = csv.DictReader(f)
                if rd.fieldnames is None:
                    continue
                rows = []
                for r in rd:
                    school = r["School"]
                    ceeb = _ceeb(r["Calculation1"], school)
                    con.execute("INSERT OR IGNORE INTO uc_schools(ceeb,name,city,region,school_type) VALUES (?,?,?,?,?)",
                                (ceeb, school, r.get("City"), r.get("County/State/ Country") or r.get("County/State/Country"), typ))
                    if sheet == "FREthbyYr":
                        rows.append((ceeb, term, campus, MEASURE[r["Count"]], r["uad_uc_ethn_7_cat"], _int(r["Pivot Field Values"])))
                    elif sheet == "FRGndbyYr":
                        rows.append((ceeb, term, campus, MEASURE[r["Count"]], r["gender"], _int(r["Pivot Field Values"])))
                    else:
                        v = r["Measure Values"].strip()
                        rows.append((ceeb, term, campus, MEASURE[r["Measure Names"].split()[0]], float(v) if v else None))
                if sheet == "FREthbyYr":
                    con.executemany("INSERT OR REPLACE INTO uc_ethnicity VALUES (?,?,?,?,?,?)", [r for r in rows if r[5] is not None])
                elif sheet == "FRGndbyYr":
                    con.executemany("INSERT OR REPLACE INTO uc_gender VALUES (?,?,?,?,?,?)", [r for r in rows if r[5] is not None])
                else:
                    con.executemany("INSERT OR REPLACE INTO uc_gpa VALUES (?,?,?,?,?)", [r for r in rows if r[4] is not None])
                n += len(rows)
            con.commit()
        print(sheet, "files", len(files), "rows read", n)
    link_schools(con)


def _norm_school(s):
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower())
    s = re.sub(r"\b(high|school|hs|sr|senior|the|of|academy)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def link_schools(con):
    """Match UC schools to our `schools` rows by normalized name + city (Bay Area publics and the private schools we hold)."""
    ours = {}
    for sid, name, city, sector in con.execute("SELECT school_id,name,city,sector FROM schools"):
        ours.setdefault((_norm_school(name), (city or "").lower().strip()), []).append(sid)
    n = 0
    for ceeb, name, city, typ in con.execute("SELECT ceeb,name,city,school_type FROM uc_schools").fetchall():
        k = (_norm_school(name), (city or "").lower().strip())
        ids = ours.get(k)
        if ids and len(ids) == 1:
            con.execute("UPDATE uc_schools SET school_id=?, match_method='name+city' WHERE ceeb=?", (ids[0], ceeb))
            n += 1
    # second pass: same city + fuzzy name, only when there is one clear best candidate
    from rapidfuzz import fuzz
    linked = {r[0] for r in con.execute("SELECT school_id FROM uc_schools WHERE school_id IS NOT NULL")}
    bycity = {}
    for ceeb, name, city, typ in con.execute("SELECT ceeb,name,city,school_type FROM uc_schools WHERE school_id IS NULL"):
        bycity.setdefault((city or "").lower().strip(), []).append((ceeb, name, typ))
    for sid, name, city, sector in con.execute("SELECT school_id,name,city,sector FROM schools").fetchall():
        if sid in linked:
            continue
        want = "California private high school" if sector == "private" else "California public high school"
        cands = [(fuzz.token_set_ratio(_norm_school(name), _norm_school(nm)), ceeb) for ceeb, nm, typ in
                 bycity.get((city or "").lower().strip(), []) if typ == want]
        cands.sort(reverse=True)
        if cands and cands[0][0] >= 85 and (len(cands) == 1 or cands[0][0] - cands[1][0] >= 8):
            con.execute("UPDATE uc_schools SET school_id=?, match_method='fuzzy name, same city' WHERE ceeb=?", (sid, cands[0][1]))
            linked.add(sid)
            n += 1
    con.commit()
    print("linked UC schools to our schools:", n)


if __name__ == "__main__":
    load()
