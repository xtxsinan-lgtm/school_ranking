"""Import the user's own spreadsheet (sheet 原始升学): one column per school(+period), one row per selected college.

The sheet is a *curated subset* (about 95 well-known colleges; some columns only list colleges with >=4 students, or only
US News top-50). Every school gets its own `sources` row with origin='user_sheet' so it is never mixed up with official
full lists. Zero / blank cells are not stored."""
import re

import openpyxl

from .db import ROOT, connect
from .resolver import Resolver

XLSX = ROOT / "data" / "user_data" / "bay_area_hs_sheet.xlsx"
SHEET_URL = "https://docs.google.com/spreadsheets/d/10avtC8wWR-NcMlUaH9VdNtevsrEmKfp8CuU00DeSkFQ"

# header text in the sheet -> (sector, official name, cds_code or None)
SCHOOLS = {
    "Nueva": ("private", "The Nueva School", None, "Hillsborough"),
    "Harker": ("private", "The Harker School", None, "San Jose"),
    "CPS": ("private", "Crystal Springs Uplands School", None, "Hillsborough"),
    "Branson": ("private", "The Branson School", None, "Ross"),
    "SF University": ("private", "San Francisco University High School", None, "San Francisco"),
    "LWHS": ("private", "Lick-Wilmerding High School", None, "San Francisco"),
    "Menlo": ("private", "Menlo School", None, "Atherton"),
    "Head Royce": ("private", "Head-Royce School", None, "Oakland"),
    "Quarry Lane": ("private", "Quarry Lane School", None, "Dublin"),
    "SF International": ("private", "International High School (SF International)", None, "San Francisco"),
    "SF Urban": ("private", "The Urban School of San Francisco", None, "San Francisco"),
    "Bellarmine": ("private", "Bellarmine College Preparatory", None, "San Jose"),
    "St Francis": ("private", "St. Francis High School (Mountain View)", None, "Mountain View"),
    "Gunn": ("public", None, "43696414332904", None),
    "Lynbrook": ("public", None, "43694684334421", None),
    "Palo Alto": ("public", None, "43696414335782", None),
    "MSJ": ("public", None, "01611760135244", None),
    "Saratoga": ("public", None, "43695344337762", None),
    "Dougherty Valley": ("public", None, "07618040113118", None),
    "Los Altos": ("public", None, "43696094334116", None),
    "Menlo Atherton": ("public", None, "41690624133716", None),
    "Leland": ("public", None, "43696664333522", None),
    "MTV": ("public", None, "43696094334728", None),  # Mountain View High (same MVLA district/years as Los Altos)
    "Los Gatos": ("public", None, "43695344334371", None),
    "Irvington": ("public", None, "01611760134270", None),
    "Dublin": ("public", None, "01750930132704", None),
    "Northgate": ("public", None, "07617540730044", None),
    "Leigh": ("public", None, "43694014330239", None),
    "Milpitas": ("public", None, "43733874334470", None),
}


# sheet-specific readings of ambiguous labels (not applied to other sources)
LABEL_TARGET = {"UWM": "ipeds:University of Wisconsin-Madison"}   # sheet's UWM = UW-Madison
LABEL_UNRESOLVED = {"Trinity", "UG"}                              # meaning unclear -> kept unresolved


def _period(v):
    s = str(v).strip()
    m = re.fullmatch(r"(\d{4})\s*-\s*(\d{4})", s)
    if m:
        return int(m.group(1)), int(m.group(2)), None
    m = re.fullmatch(r"(\d{4})(\.0)?", s)
    y = int(m.group(1))
    return y, y, y


def run():
    con = connect()
    res = Resolver(con)
    ws = openpyxl.load_workbook(XLSX, data_only=True)["原始升学"]
    rows = [[c.value for c in r] for r in ws.iter_rows()]
    names, years, grads, notes = rows[0], rows[1], rows[2], rows[3]
    # carry merged header names rightwards; stop at blank separator columns (index of the 2nd label column)
    cols, cur = [], None
    for j in range(1, len(names)):
        if years[j] is None or str(years[j]).strip() in ("", "升学数据年份"):
            cur = None
            continue
        if names[j]:
            cur = str(names[j]).strip()
        if cur:
            cols.append((j, cur))
    done = set()
    total = 0
    for j, key in cols:
        sector, off_name, cds, city = SCHOOLS[key]
        if cds:
            r = con.execute("SELECT school_id FROM schools WHERE cds_code=?", (cds,)).fetchone()
            sid = r[0]
        else:
            r = con.execute("SELECT school_id FROM schools WHERE name=? AND sector='private'", (off_name,)).fetchone()
            sid = r[0] if r else con.execute(
                "INSERT INTO schools(name,city,sector) VALUES (?,?, 'private')", (off_name, city)).lastrowid
        url = f"{SHEET_URL}#school={key.replace(' ', '_')}"
        note = "User's spreadsheet 湾区高中 / 原始升学: curated subset of ~95 colleges, zero/blank not stored."
        extra = notes[j] if notes[j] else None
        if extra:
            note += f" Sheet note: {extra}"
        con.execute("INSERT OR IGNORE INTO sources(school_id,url,source_type,parser,notes,origin) VALUES (?,?,?,?,?, 'user_sheet')",
                    (sid, url, "sheet", "user_matrix", note))
        src = con.execute("SELECT source_id FROM sources WHERE school_id=? AND url=?", (sid, url)).fetchone()[0]
        if (src) not in done:
            con.execute("DELETE FROM matriculation WHERE source_id=?", (src,))
            con.execute("DELETE FROM cohort_sizes WHERE source_id=?", (src,))
            done.add(src)
        ps, pe, gy = _period(years[j])
        con.execute("INSERT OR REPLACE INTO cohort_sizes VALUES (?,?,?,?)", (src, ps, pe, float(grads[j]) if grads[j] else None))
        for r in rows[4:]:
            label, v = r[0], r[j] if j < len(r) else None
            if not label or v in (None, "", " "):
                continue
            n = int(float(v))
            if n <= 0:
                continue
            lab = str(label).strip()
            if lab in LABEL_UNRESOLVED:
                cid, method, score = None, "ambiguous", 0.0
            elif lab in LABEL_TARGET:
                from .resolver import _target_id
                cid, method, score = _target_id(con, LABEL_TARGET[lab]), "manual", 100.0
            else:
                cid, method, score = res.resolve(lab, None)
            con.execute(
                "INSERT OR REPLACE INTO matriculation(school_id,source_id,grad_year,period_start,period_end,college_id,college_raw,"
                "section,count,match_method,match_score) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (sid, src, gy, ps, pe, cid, str(label).strip(), None, n, method, score))
            total += 1
    con.commit()
    print("user sheet rows imported:", total)
    for r in con.execute("SELECT college_raw, COUNT(*) FROM matriculation m JOIN sources s USING(source_id) WHERE s.origin='user_sheet' AND college_id IS NULL GROUP BY 1"):
        print("unresolved label:", tuple(r))


if __name__ == "__main__":
    run()
