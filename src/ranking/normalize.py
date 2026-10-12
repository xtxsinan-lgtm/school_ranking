"""Name normalization for college matching.

norm(): canonical comparison string (lowercase, no punctuation, abbreviations expanded).
key():  looser key that also drops generic words (university/college/of/the...) so that
        "Purdue-Main Campus" == "Purdue University-Main Campus".
"""
import re
import unicodedata

# whole-phrase rewrites applied on the normalized string (order matters)
PHRASES = [
    (r"\bpenn state\b", "pennsylvania state university"),
    (r"\bcal state\b", "california state university"),
    (r"\bcalifornia state univ\b", "california state university"),
    (r"\bcsu\b", "california state university"),
    (r"\buc\b", "university of california"),
    (r"\bu c\b", "university of california"),
    (r"\bcal poly\b", "california polytechnic state university"),
    (r"\bcal\b", "california"),
    (r"\bsuny\b", "state university of new york"),
    (r"\bumass\b", "university of massachusetts"),
    (r"\bumd\b", "university of maryland"),
    (r"\bunc\b", "university of north carolina"),
    (r"\bmich\b", "michigan"),
]
WORDS = {
    "univ": "university", "u": "university", "coll": "college", "inst": "institute",
    "tech": "technology", "intl": "international", "natl": "national", "poly": "polytechnic",
    "sci": "science", "mt": "mount", "ft": "fort", "amp": "and",
}
STOP = {"university", "college", "of", "at", "the", "and", "in", "campus", "main", "system"}


def _plain(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", " and ").replace("’", "").replace("'", "")
    s = re.sub(r"\(.*?\)", " ", s)  # drop parentheticals
    s = re.sub(r"[^a-z0-9 ]+", " ", s)  # punctuation and dashes -> space
    return re.sub(r"\s+", " ", s).strip()


def norm(s):
    s = _plain(s)
    for pat, rep in PHRASES:
        s = re.sub(pat, rep, s)
    toks = [WORDS.get(t, t) for t in s.split()]
    # "st" -> "state" before university/college or at the end ("Ohio St"); otherwise "saint"
    out = []
    for i, t in enumerate(toks):
        if t == "st":
            nxt = toks[i + 1] if i + 1 < len(toks) else None
            out.append("state" if nxt in (None, "university", "college") and i > 0 else "saint")
        else:
            out.append(t)
    return " ".join(out)


def key(s):
    return " ".join(t for t in norm(s).split() if t not in STOP)


def form(s):
    """'of' for "University of X" style, 'suffix' for "X University/College", else 'bare'."""
    n = norm(s).split()
    if len(n) >= 2 and n[0] in ("university", "college", "institute") and n[1] == "of":
        return "of"
    if "university" in n or "college" in n:
        return "suffix"
    return "bare"


def fix_mojibake(s):
    try:
        t = s.encode("latin-1").decode("utf-8")
        return t
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s
