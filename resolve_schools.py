"""Map school names (e.g. US News names) to Parchment institution names.

usage: python3 resolve_schools.py data/schools_seed.csv data/schools_resolved.csv

Input columns: name, category, [anything else is carried through].
Output adds parchment_id, parchment_name, match ('exact'|'fuzzy'|'none').
Review every 'fuzzy'/'none' row by hand before scraping.
"""
import csv
import difflib
import re
import sys
from concurrent.futures import ThreadPoolExecutor

from parchment import search_institutions


def norm(s):
    s = s.lower().replace("&", "and")
    return re.sub(r"[^a-z0-9 ]", "", s).strip()


def queries(name):
    """Alternate spellings: Parchment uses 'X, Y', 'X - Y', 'X-Y' and a leading 'The' inconsistently."""
    qs = [name, name.replace("-", " - "), name.replace("-", ", "), "The " + name]
    if "-" in name:
        qs.append(name.split("-")[0])
    if ":" in name:
        qs.append(name.split(":")[0])
    return list(dict.fromkeys(qs))


def resolve(name, override=None):
    """override = known Parchment name; looked up verbatim and must match exactly."""
    cands = []
    for q in queries(override or name):
        for c in search_institutions(q):
            if c not in cands:
                cands.append(c)
    for c in cands:
        if norm(c["name"]) == norm(override or name):
            return c, "exact"
    if cands:
        best = max(cands, key=lambda c: difflib.SequenceMatcher(None, norm(c["name"]), norm(name)).ratio())
        return best, "fuzzy"
    return None, "none"


def load_overrides(path="data/name_overrides.csv"):
    try:
        return {r["name"]: r["parchment_name"] for r in csv.DictReader(open(path, encoding="utf8"))}
    except FileNotFoundError:
        return {}


def main(src, dst):
    rows = list(csv.DictReader(open(src, encoding="utf8")))
    overrides = load_overrides()
    with ThreadPoolExecutor(4) as ex:
        results = list(ex.map(lambda r: resolve(r["name"], overrides.get(r["name"])), rows))
    seen, out = set(), []
    for r, (c, kind) in zip(rows, results):
        r["parchment_id"] = c["id"] if c else ""
        r["parchment_name"] = c["name"] if c else ""
        r["match"] = kind
        if c and c["id"] in seen:
            r["match"] = "duplicate"
        elif c:
            seen.add(c["id"])
        out.append(r)
    with open(dst, "w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    from collections import Counter
    print(Counter(r["match"] for r in out))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
