"""HTML article listing graduates' names under ALL-CAPS college headings (e.g. a student newspaper's
"Class of 20XX destinations"). Only the NUMBER of names per college is kept; names are discarded.

opts: grad_year (int), start_marker / end_marker (text delimiting the list), skip (regex of headings to ignore)."""
import re

from bs4 import BeautifulSoup

SECTION = re.compile(r"^(community colleges?|cal(ifornia)? state univ\w*|csu|(university of california|uc|uc system)|"
                     r"private.*|out.of.state.*|international.*|public.*)$", re.I)


def parse(path, grad_year=None, start_marker=None, end_marker=None, skip=None, **opts):
    soup = BeautifulSoup(open(path, encoding="utf-8", errors="replace").read(), "html.parser")
    for t in soup(["script", "style"]):
        t.decompose()
    lines = [re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip() for s in soup.get_text("\n").split("\n")]
    lines = [l for l in lines if l]
    if start_marker:
        i = next((k for k, l in enumerate(lines) if start_marker.lower() in l.lower()), 0)
        lines = lines[i + 1:]
    if end_marker:
        j = next((k for k, l in enumerate(lines) if end_marker.lower() in l.lower()), len(lines))
        lines = lines[:j]
    skip_re = re.compile(skip, re.I) if skip else None
    recs, section, cur, n = [], None, None, 0

    def flush():
        if cur and n:
            recs.append(dict(college_raw=cur.title() if cur.isupper() else cur, section=section, grad_year=grad_year,
                             period_start=grad_year, period_end=grad_year, count=n))

    for l in lines:
        letters = re.sub(r"[^A-Za-z]", "", l)
        is_head = len(letters) >= 3 and l.upper() == l and not re.search(r"\d", l)
        if is_head:
            if skip_re and skip_re.search(l):
                flush(); cur, n = None, 0; continue
            if SECTION.match(l):
                flush(); cur, n = None, 0; section = l.title(); continue
            flush(); cur, n = l, 0
        elif cur:
            n += 1
    flush()
    return recs
