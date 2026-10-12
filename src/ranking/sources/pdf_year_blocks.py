"""PDF table of repeated blocks "College Name | '22 '23 '24 '25" laid out side by side (e.g. Menlo-Atherton
Graduate Destinations). Years come from header rows; zero cells are skipped."""
import re
import subprocess

ROW = re.compile(r"([A-Za-z][A-Za-z0-9.,&’'()/ \-]*?)\s+(\d+(?:\s+\d+){%d})(?=\s{2,}|\s*$)")


def parse(path, n_years=4, first_year=None, **opts):
    text = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, check=True).stdout
    years = None
    recs = []
    for line in text.splitlines():
        h = re.findall(r"[‘'’](\d\d)\b", line)
        if "College Name" in line and len(h) >= n_years:
            years = [2000 + int(y) for y in h[:n_years]]
            continue
        if not years:
            continue
        for m in re.finditer(ROW.pattern % (n_years - 1), line):
            name = re.sub(r"\s+", " ", m.group(1)).strip(" ,")
            if name.lower().startswith(("college name", "year")) or len(name) < 2:
                continue
            vals = [int(v) for v in m.group(2).split()]
            for y, v in zip(years, vals):
                if v > 0:
                    recs.append(dict(college_raw=name, section=None, grad_year=y, period_start=y, period_end=y, count=v))
    return recs
