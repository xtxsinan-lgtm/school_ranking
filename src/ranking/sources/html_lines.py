"""HTML page with one college per line: "College (N)"; a line without "(N)" counts as `unnumbered` (default 1).
opts: start_marker (text of the heading line), end_marker (first line after the list), period_start/period_end."""
import re

from bs4 import BeautifulSoup


def parse(path, start_marker=None, end_marker=None, period_start=None, period_end=None, unnumbered=1, **opts):
    soup = BeautifulSoup(open(path, encoding="utf-8", errors="replace").read(), "html.parser")
    for t in soup(["script", "style"]):
        t.decompose()
    lines = [re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip() for s in soup.get_text("\n").split("\n")]
    lines = [l for l in lines if l]
    if start_marker:
        idx = [k for k, l in enumerate(lines) if start_marker.lower() in l.lower()]
        lines = lines[idx[-1] + 1:] if idx else lines
    if end_marker:
        j = next((k for k, l in enumerate(lines) if end_marker.lower() in l.lower()), len(lines))
        lines = lines[:j]
    ps = int(period_start) if period_start else None
    pe = int(period_end) if period_end else ps
    gy = ps if ps and ps == pe else None
    recs = []
    for l in lines:
        m = re.fullmatch(r"(.+?)\s*\((\d+)\)", l)
        name, n = (m.group(1).strip(), int(m.group(2))) if m else (l, int(unnumbered))
        if len(name) < 3 or len(name) > 90:
            continue
        recs.append(dict(college_raw=name, section=None, grad_year=gy, period_start=ps, period_end=pe, count=n))
    return recs
