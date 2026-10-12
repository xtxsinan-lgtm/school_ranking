import csv
import json

from .db import ROOT, connect
from .fetch import fetch
from .normalize import repair_ligatures
from .resolver import Resolver
from .sources import PARSERS

SOURCES_CSV = ROOT / "data" / "sources.csv"


def ingest_all(force_fetch=False):
    con = connect()
    res = Resolver(con)
    vocab = {w for (n,) in con.execute("SELECT alias_raw FROM college_aliases") for w in (n or "").lower().replace(",", " ").split()}
    vocab |= {"pittsburgh", "international", "whittier", "pacific", "institute", "massachusetts", "austin", "scottsdale"}
    with open(SOURCES_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        sch = con.execute("SELECT school_id,name FROM schools WHERE cds_code=?", (row["cds_code"],)).fetchone()
        if not sch:
            print("SKIP unknown cds", row["cds_code"])
            continue
        path, sha, ts = fetch(row["url"], row["cds_code"], force=force_fetch)
        con.execute("INSERT OR IGNORE INTO sources(school_id,url,source_type,parser,notes) VALUES (?,?,?,?,?)",
                    (sch["school_id"], row["url"], row["source_type"], row["parser"], row["notes"]))
        sid = con.execute("SELECT source_id FROM sources WHERE school_id=? AND url=?",
                          (sch["school_id"], row["url"])).fetchone()[0]
        con.execute("UPDATE sources SET fetched_at=?, raw_path=?, sha256=? WHERE source_id=?",
                    (ts, str(path.relative_to(ROOT)), sha, sid))
        recs = PARSERS[row["parser"]](path, **json.loads(row["opts"] or "{}"))
        con.execute("DELETE FROM matriculation WHERE source_id=?", (sid,))
        unresolved = 0
        for r in recs:
            r["college_raw"] = repair_ligatures(r["college_raw"], vocab)
            if r["section"]:
                r["section"] = repair_ligatures(r["section"], vocab)
            cid, method, score = res.resolve(r["college_raw"], r["section"])
            unresolved += cid is None
            con.execute(
                "INSERT OR REPLACE INTO matriculation(school_id,source_id,grad_year,period_start,period_end,college_id,"
                "college_raw,section,count,match_method,match_score) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (sch["school_id"], sid, r["grad_year"], r["period_start"], r["period_end"], cid,
                 r["college_raw"], r["section"], r["count"], method, score))
        con.commit()
        print(f"{sch['name']}: {len(recs)} records, {unresolved} unresolved")
    export(con)


def export(con):
    out = ROOT / "data" / "export"
    out.mkdir(parents=True, exist_ok=True)
    q = {
        "matriculation.csv": """SELECT s.cds_code, s.name AS school, m.grad_year, m.period_start, m.period_end,
            c.college_id, c.name AS college, c.unitid, m.college_raw, m.section, m.count, m.match_method, m.match_score
            FROM matriculation m JOIN schools s USING(school_id) LEFT JOIN colleges c USING(college_id)
            ORDER BY s.name, m.period_start, m.college_raw""",
        "unresolved.csv": "SELECT * FROM unresolved",
    }
    for name, sql in q.items():
        cur = con.execute(sql)
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([d[0] for d in cur.description])
            w.writerows(cur.fetchall())
