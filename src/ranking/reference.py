"""Build reference tables: colleges from IPEDS HD file, Bay Area public high schools from CDE directory."""
import csv
import re
import io
import zipfile

import requests

from .db import REF, connect
from .normalize import norm

IPEDS_URL = "https://nces.ed.gov/ipeds/datacenter/data/HD2023.zip"
CDE_URL = "https://www.cde.ca.gov/schooldirectory/report?rid=dl1&tp=txt"
BAY_COUNTIES = {"Alameda", "Contra Costa", "Marin", "Napa", "San Francisco",
                "San Mateo", "Santa Clara", "Solano", "Sonoma"}
HS_TYPES = ("High Schools (Public)", "High Schools In 1 School Dist. (Public)", "K-12 Schools (Public)")


def _get(url, name):
    REF.mkdir(parents=True, exist_ok=True)
    p = REF / name
    if not p.exists():
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
        r.raise_for_status()
        p.write_bytes(r.content)
    return p


def build_colleges(con):
    p = _get(IPEDS_URL, "HD2023.zip")
    with zipfile.ZipFile(p) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        rows = list(csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8-sig", errors="replace")))
    n = 0
    for r in sorted(rows, key=lambda r: int(r["UNITID"])):
        if r["CYACTIVE"] != "1" or r["ICLEVEL"] not in ("1", "2"):  # active, 2yr/4yr only
            continue
        if re.search(r"System (Office|Admin)|Systemwide|System Offices?$|-System Administration|Chancellors? Office|Central Office|District Office", r["INSTNM"]):
            continue
        cur = con.execute(
            "INSERT OR IGNORE INTO colleges(unitid,name,city,state,country,sector,iclevel,website) VALUES (?,?,?,?, 'US',?,?,?)",
            (int(r["UNITID"]), r["INSTNM"], r["CITY"], r["STABBR"], int(r["SECTOR"]), int(r["ICLEVEL"]), r["WEBADDR"]))
        cid = con.execute("SELECT college_id FROM colleges WHERE unitid=?", (int(r["UNITID"]),)).fetchone()[0]
        names = {r["INSTNM"]}
        names.update(a.strip() for a in r["IALIAS"].split("|") if a.strip())
        for a in names:
            con.execute("INSERT OR IGNORE INTO college_aliases VALUES (?,?,?, 'ipeds')", (norm(a), cid, a))
        n += 1
    con.commit()
    return n


def build_schools(con):
    p = _get(CDE_URL, "pubschls.txt")
    rows = csv.DictReader(open(p, encoding="utf-8-sig", errors="replace"), delimiter="\t")
    n = 0
    for r in rows:
        if r["County"] not in BAY_COUNTIES or r["StatusType"] != "Active" or r["SOCType"] not in HS_TYPES:
            continue
        if r["SOCType"].startswith("K-12") and "9" not in r["GSserved"]:
            continue
        con.execute(
            "INSERT OR IGNORE INTO schools(cds_code,ncessch,name,district,city,county,zip,website,charter,soc_type,grades) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (r["CDSCode"], r["NCESDist"] + r["NCESSchool"], r["School"], r["District"], r["City"], r["County"],
             r["Zip"], r["WebSite"], 1 if r["Charter"] == "Y" else 0, r["SOCType"], r["GSserved"]))
        n += 1
    con.commit()
    return n


def build_all():
    con = connect()
    print("colleges:", build_colleges(con))
    print("schools:", build_schools(con))
