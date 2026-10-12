"""HTML table: first column = college, remaining header cells = graduating years."""
import re

from bs4 import BeautifulSoup

from ..normalize import fix_mojibake


def _int(s):
    s = s.replace("\xa0", " ").strip()
    m = re.fullmatch(r"\d+", s)
    return int(m.group()) if m else None


def parse(path, **opts):
    soup = BeautifulSoup(open(path, encoding="utf-8", errors="replace").read(), "html.parser")
    recs = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        head = [c.get_text(" ", strip=True) for c in rows[0].find_all(["td", "th"])]
        years = {i: int(h) for i, h in enumerate(head) if re.fullmatch(r"(19|20)\d\d", h)}
        if not years:
            continue
        for tr in rows[1:]:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if not cells or not cells[0].strip():
                continue
            name = fix_mojibake(re.sub(r"\s+", " ", cells[0].replace("\xa0", " ")).strip())
            for i, y in years.items():
                if i < len(cells):
                    n = _int(cells[i])
                    if n is not None:
                        recs.append(dict(college_raw=name, section=None, grad_year=y,
                                         period_start=y, period_end=y, count=n))
    return recs
