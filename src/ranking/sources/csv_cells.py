"""CSV (e.g. a published Google Sheet) whose header row names sections and whose cells read "College (N)".
Pooled counts: opts must give period_start / period_end."""
import csv
import re

from ..normalize import fix_mojibake

CELL = re.compile(r"(.+?)\s*\(\s*(\d+)\s*\)\s*$")


def parse(path, period_start=None, period_end=None, **opts):
    rows = list(csv.reader(open(path, encoding="utf-8", errors="replace")))
    heads = [h.strip() for h in rows[0]]
    recs = []
    for row in rows[1:]:
        for j, cell in enumerate(row):
            m = CELL.match(cell.strip())
            if m:
                recs.append(dict(college_raw=fix_mojibake(re.sub(r"\s+", " ", m.group(1)).strip()),
                                 section=heads[j] if j < len(heads) else None, grad_year=None,
                                 period_start=period_start, period_end=period_end, count=int(m.group(2))))
    return recs
