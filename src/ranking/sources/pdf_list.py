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


def parse(path, page=None, title_re=None, x_min=0, x_max=None, y_max=None, bare_numbers=False, unnumbered=None,
          y_min_offset=5, ignore=None, strip=None, period_start=None, period_end=None, **opts):
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
    m = re.search(r"((?:19|20)\d\d)\s*[-–—]\s*((?:19|20)?\d\d)", ttext.replace("O", "0"))
    ps, pe = (None, None)
    if m:
        ps = int(m.group(1))
        pe = int(m.group(2)) if len(m.group(2)) == 4 else int(m.group(1)[:2] + m.group(2))
    gy = None
    if not m:
        m1 = re.search(r"class of\s*((?:19|20)\d\d)", ttext, re.I)
        if m1:
            ps = pe = gy = int(m1.group(1))

    junk = re.compile(r"(tt|ti|fi|ff|fl|tti|ffi|ft)+", re.I)  # stray ligature glyphs some PDFs emit as separate words
    body = [(x0, y, x1, w) for x0, y, x1, w in words if y > ytitle + y_min_offset and x0 >= float(x_min)
            and (x_max is None or x0 <= float(x_max)) and (y_max is None or y <= float(y_max)) and not junk.fullmatch(w)]
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
    if bare_numbers:  # "Name      12" -> one item "Name (12)"; the number sits in its own segment after a wide gap
        merged = []
        for sg in sorted(segs, key=lambda t: (round(t[1] / 3), t[0])):
            if merged and re.fullmatch(r"\d{1,3}", sg[2]) and abs(merged[-1][1] - sg[1]) < 3 \
                    and not re.search(r"\(\d+\)$", merged[-1][2]):
                merged[-1] = (merged[-1][0], merged[-1][1], f"{merged[-1][2]} ({sg[2]})")
            else:
                merged.append(sg)
        segs = merged
        segs = [(x0, y, re.sub(r"\s+(\d{1,3})$", r" (\1)", t)) for x0, y, t in segs]  # "Stanford University 41"
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
    if period_start:
        ps, pe = int(period_start), int(period_end or period_start)
        if ps == pe:
            gy = ps
    ignore_re = re.compile(ignore, re.I) if ignore else None
    strip_re = re.compile(strip) if strip else None
    recs, section, pending = [], None, ""
    for x0, y, text in segs:
        text = text.replace("*", "").replace("\u200b", "").strip()
        if strip_re:
            text = strip_re.sub("", text).strip()
        if not text or (ignore_re and ignore_re.search(text)):
            continue
        if len(text) > 25 and (text.endswith(".") or ". " in text) and not re.search(r"\(\d+\)", text):
            pending = ""  # prose sentence, not a college name
            continue
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
        elif unnumbered is not None and text[:1].isupper() and not text.endswith((",", "-")) and len(text) > 3:
            recs.append(dict(college_raw=text, section=section, grad_year=gy, period_start=ps, period_end=pe,
                             count=int(unnumbered)))
            pending = ""
        else:
            pending = full
    return recs
