"""PDF school profile with a multi-column "College Name (N)" list under a heading
such as "Graduate Matriculation from 2024-2026". Pooled counts (no per-year split).

Uses `pdftotext -bbox` word coordinates: words on a line are split into segments at large x gaps
(= column gaps); a segment ending in "(N)" is an item, other segments are section headings.
Reading order: columns left-to-right, each top-to-bottom; headings persist across columns.
"""
import re
import subprocess
from html import unescape

GAP = 9.0
SECTION_RE = re.compile(
    r"(community colleges?|cal(ifornia)? state univ(ersitie)?s?( \(csu\))?|csu|univ(ersity)? of california( \(uc\))?|uc|"
    r"private( ?/ ?| and )?(out.of.state)?( colleges| universities)?|out.of.state( colleges| universities)?|"
    r"(international|interna\s?onal)( colleges| universities)?|california\s*-\s*(private|public)|public( colleges| universities)?|other|"
    r"[24].?year( colleges?| universities)?|work|military|gap year|undecided|unknown|employment|"
    r"private (colleges|universities).*|out of state.*|(california state|cal state) universit(y|ies)|trade.*)", re.I)
HEADING_RE = re.compile(r"matriculation|colleges? .*attend|where .* go", re.I)


def _words(path, page):
    out = subprocess.run(["pdftotext", "-bbox", "-f", str(page), "-l", str(page), str(path), "-"],
                         capture_output=True, text=True, check=True).stdout
    return [(float(a), float(b), float(c), unescape(w)) for a, b, c, w in re.findall(
        r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="[\d.]+">(.*?)</word>', out)]


def parse(path, page=None, title_re=None, x_min=0, **opts):
    pages = [int(page)] if page else range(1, 4)
    heading = re.compile(title_re, re.I) if title_re else HEADING_RE
    for pg in pages:
        words = _words(path, pg)
        # locate the title line
        lines = {}
        for x0, y, x1, w in words:
            lines.setdefault(round(y / 3), []).append((x0, y, x1, w))
        title = None
        for k in sorted(lines):
            text = " ".join(w for _, _, _, w in sorted(lines[k]))
            if heading.search(text):
                title = (min(y for _, y, _, _ in lines[k]), text)
                break
        if title:
            break
    if not title:
        raise ValueError("matriculation heading not found")
    ytitle, ttext = title
    m = re.search(r"((?:19|20)\d\d)\s*[-–]\s*((?:19|20)\d\d)", ttext)
    ps, pe = (int(m.group(1)), int(m.group(2))) if m else (None, None)
    gy = None
    if not m:
        m1 = re.search(r"class of\s*((?:19|20)\d\d)", ttext, re.I)
        if m1:
            ps = pe = gy = int(m1.group(1))

    junk = re.compile(r"(tt|ti|fi|ff|fl|tti|ffi|ft)+", re.I)  # stray ligature glyphs some PDFs emit as separate words
    body = [(x0, y, x1, w) for x0, y, x1, w in words if y > ytitle + 5 and x0 >= float(x_min) and not junk.fullmatch(w)]
    # group into lines
    rows = {}
    for x0, y, x1, w in body:
        for k in (round(y / 3), round(y / 3) - 1, round(y / 3) + 1):
            if k in rows and abs(rows[k][0] - y) < 3:
                rows[k][1].append((x0, x1, w))
                break
        else:
            rows[round(y / 3)] = (y, [(x0, x1, w)])
    segs = []  # (x0, y, text)
    for k, (y, ws) in rows.items():
        ws.sort()
        cur = [ws[0]]
        for a in ws[1:]:
            if a[0] - cur[-1][1] > GAP or re.fullmatch(r"\(\d+\)", cur[-1][2]):
                segs.append((cur[0][0], y, " ".join(w for _, _, w in cur)))
                cur = [a]
            else:
                cur.append(a)
        segs.append((cur[0][0], y, " ".join(w for _, _, w in cur)))
    # cluster segment start x into columns
    xs = sorted({round(s[0]) for s in segs})
    cols = []
    for x in xs:
        if not cols or x - cols[-1][-1] > 12:
            cols.append([x])
        else:
            cols[-1].append(x)
    starts = [c[0] for c in cols]
    def col_of(x):
        return max(i for i, s in enumerate(starts) if s - 6 <= x)
    segs.sort(key=lambda s: (col_of(s[0]), s[1]))
    recs, section, pending = [], None, ""
    for x0, y, text in segs:
        full = (pending + " " + text).strip()
        m = re.fullmatch(r"(.+?)\s*\((\d+)\)", full)
        if m and SECTION_RE.fullmatch(m.group(1).strip()):
            section, pending = m.group(1).strip(), ""  # subtotal line, e.g. "University of California (64)"
        elif m:
            recs.append(dict(college_raw=m.group(1).strip(), section=section, grad_year=gy,
                             period_start=ps, period_end=pe, count=int(m.group(2))))
            pending = ""
        elif re.search(r"\(\d+\)", full):
            continue
        elif SECTION_RE.fullmatch(text.strip()):
            section, pending = text.strip(), ""
        else:
            pending = full
    return recs
