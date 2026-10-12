"""Free-text "Name - N" lists in a PDF, grouped under "Attending ... CSU / UC / Private" style headers
(Dublin High exit surveys). Multi-column layouts and wrapped names are untangled by longest-match segmentation
against the college resolver: a run of words with no number is split into the longest known college names, and the
word group directly before a number gets that number. A listed college without a number counts as 1 (the surveys
only print a number when more than one student chose that college).

opts: year (default: from "Class of 20XX"), stop (regex of the first line that ends the list)."""
import re
import subprocess

SECTIONS = [
    (re.compile(r"csu campuses|california state", re.I), "California State University"),
    (re.compile(r"uc campuses|university of california", re.I), "University of California"),
    (re.compile(r"private and out|private/out|4.? ?year colleges", re.I), "Private and Out-of-State"),
    (re.compile(r"community colleges|2.? ?year colleges", re.I), "Community Colleges"),
    (re.compile(r"military academies", re.I), "Military Academies"),
]
STOP = re.compile(r"^others?\b", re.I)
HEADER = re.compile(r"exit survey results|^responses:|graduates:", re.I)
MAXW = 9


def _segment(words, section, resolver):
    """Split words into college names (longest known match first from the left); returns list of strings."""
    n = len(words)
    best = [None] * (n + 1)  # best[i] = (cost, parts) for words[i:]
    best[n] = (0, [])
    for i in range(n - 1, -1, -1):
        cand = None
        for j in range(min(n, i + MAXW), i, -1):
            span = " ".join(words[i:j])
            ok = resolver.resolve(span, section, allow_fuzzy=False)[0] is not None
            rest = best[j]
            cost = rest[0] + (1 if ok else 3 + (j - i))  # unresolved spans are expensive; fewer parts preferred
            if cand is None or cost < cand[0]:
                cand = (cost, [span] + rest[1])
        best[i] = cand
    return best[0][1]


def parse(path, resolver=None, year=None, stop=None, **opts):
    text = subprocess.run(["pdftotext", "-raw", str(path), "-"], capture_output=True, text=True, check=True).stdout
    m = re.search(r"Class of\s*((?:19|20)\d\d)", text)
    year = int(year or (m.group(1) if m else 0))
    stop_re = re.compile(stop) if stop else STOP
    recs, section, buf = [], None, []

    def flush():
        nonlocal buf
        if not buf or section is None:
            buf = []
            return
        joined = re.sub(r"[-–]\s*(\d{1,3})\b", r" \1 ", " ".join(buf))  # "University-2", "Tech -1", "SD – 8"
        toks = joined.split()
        chunk = []
        for t in toks:
            if t in ("-", "–", "*", ";"):
                continue
            if re.fullmatch(r"\d{1,3}", t) and chunk:
                names = _segment(chunk, section, resolver)
                for nm in names[:-1]:
                    recs.append((nm, section, 1))
                recs.append((names[-1], section, int(t)))
                chunk = []
            else:
                chunk.append(t.strip("*;"))
        if chunk:
            for nm in _segment(chunk, section, resolver):
                recs.append((nm, section, 1))
        buf = []

    for line in text.splitlines():
        line = line.strip()
        if not line or HEADER.search(line):
            continue
        if re.match(r"attending|^\d+- ?year colleges|^[24]- ?year", line, re.I) or SECTIONS[2][0].search(line) and ":" in line:
            flush()
            for pat, name in SECTIONS:
                if pat.search(line):
                    section = name
                    break
            else:
                section = None
            rest = line.split(":", 1)[1] if ":" in line else ""
            rest = re.sub(r"^\s*\(?\d+\)?\s*$", "", rest)
            if rest.strip():
                buf.append(rest)
            continue
        if stop_re.match(line):
            flush()
            section = None
            continue
        buf.append(line)
    flush()
    return [dict(college_raw=n, section=s, grad_year=year, period_start=year, period_end=year, count=c)
            for n, s, c in recs if n]
