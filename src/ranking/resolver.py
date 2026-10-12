"""Map a raw college string from a school's list to a unified college_id.

Order: manual alias (section-specific first) -> exact normalized match -> loose key match
(same name form, unique) -> fuzzy (flagged for review). Inside a "Cal State"/"UC" section only
manual section aliases and exact matches are allowed, so e.g. "San Diego" can never become the
University of San Diego. Anything else stays unresolved (college_id NULL) and shows up in the
`unresolved` view; fix by adding a row to data/aliases/college_aliases.csv.
"""
import csv
from collections import defaultdict

from rapidfuzz import fuzz, process

from .db import ROOT
from .normalize import form, key, norm

ALIAS_CSV = ROOT / "data" / "aliases" / "college_aliases.csv"


def section_class(section):
    if not section:
        return None
    s = norm(section)
    if s.startswith("california state") or s.startswith("csu"):
        return "csu"
    if s.startswith("university of california"):
        return "uc"
    return None


def _target_id(con, target):
    if target.startswith("intl:"):
        name, _, country = target[5:].partition("|")
        r = con.execute("SELECT college_id FROM colleges WHERE unitid IS NULL AND name=?", (name,)).fetchone()
        if r:
            return r[0]
        cid = con.execute("INSERT INTO colleges(name,country) VALUES (?,?)", (name, country or None)).lastrowid
        con.execute("INSERT OR IGNORE INTO college_aliases VALUES (?,?,?, 'manual')", (norm(name), cid, name))
        return cid
    if target.startswith("ipeds:"):
        rows = con.execute("SELECT college_id FROM colleges WHERE unitid IS NOT NULL AND name=?", (target[6:],)).fetchall()
        if len(rows) != 1:
            print("WARN ipeds name not unique/found:", target)
            return None
        return rows[0][0]
    r = con.execute("SELECT college_id FROM colleges WHERE unitid=?", (int(target),)).fetchone()
    if not r:
        print("WARN unknown unitid", target)
    return r[0] if r else None


def load_manual_aliases(con):
    """CSV columns: alias,target[,section]. target = UNITID | ipeds:<exact IPEDS name> | intl:<Name>|<Country>.
    section = optional class (csu / uc) restricting where the alias applies."""
    out = {}
    if not ALIAS_CSV.exists():
        return out
    with open(ALIAS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            alias, target = row["alias"].strip(), row["target"].strip()
            if not alias or not target:
                continue
            cid = _target_id(con, target)
            if cid is None:
                continue
            sec = (row.get("section") or "").strip() or None
            out[(sec, norm(alias))] = cid
            if sec is None:
                con.execute("INSERT OR REPLACE INTO college_aliases VALUES (?,?,?, 'manual')", (norm(alias), cid, alias))
    con.commit()
    return out


class Resolver:
    def __init__(self, con):
        self.con = con
        self.manual = load_manual_aliases(con)
        self.exact = defaultdict(set)
        for a, cid in con.execute("SELECT alias_norm,college_id FROM college_aliases"):
            self.exact[a].add(cid)
        self.keyidx = defaultdict(lambda: defaultdict(set))  # key -> form -> ids
        for a, ids in self.exact.items():
            self.keyidx[key(a)][form(a)].update(ids)
        self.keys = [k for k in self.keyidx if k]

    def resolve(self, raw, section=None, allow_fuzzy=True):
        """Return (college_id|None, method, score)."""
        n = norm(raw)
        cls = section_class(section)
        if cls and (cls, n) in self.manual:
            return self.manual[(cls, n)], "manual", 100.0
        if (None, n) in self.manual:
            return self.manual[(None, n)], "manual", 100.0
        ids = self.exact.get(n, set())
        if len(ids) == 1:
            return next(iter(ids)), "exact", 100.0
        if cls and len(raw.split()) < 2:  # bare names inside a CSU/UC section ("San Diego") are never guessed
            return None, "none", 0.0
        k, f = key(raw), form(raw)
        by_form = self.keyidx.get(k, {})
        if by_form:
            cand = set(by_form.get(f, set())) if f != "bare" else set().union(*by_form.values())
            if len(cand) == 1:
                return next(iter(cand)), "key", 100.0
            if len(cand) > 1:
                return None, "ambiguous", 0.0
            return None, "none", 0.0
        if allow_fuzzy and len(k) >= 6:
            best = process.extract(k, self.keys, scorer=fuzz.token_sort_ratio, limit=2)
            if best and best[0][1] >= 93 and (len(best) == 1 or best[0][1] - best[1][1] >= 4):
                by_form = self.keyidx[best[0][0]]
                cand = set(by_form.get(f, set())) if f != "bare" else set().union(*by_form.values())
                if len(cand) == 1:
                    return next(iter(cand)), "fuzzy", float(best[0][1])
        return None, "none", 0.0

    def create_international(self, raw, section):
        """Unresolved names under an "International" section become their own (non-IPEDS) college rows, shared by name."""
        import re
        if not section or not re.search(r"interna", section, re.I):
            return None
        name = re.sub(r"\s+", " ", raw).strip().rstrip(",")
        country = None
        if "," in name:
            name, _, tail = name.rpartition(",")
            name, country = name.strip(), tail.strip() or None
        n = norm(name)
        ids = self.exact.get(n)
        if ids and len(ids) == 1:
            return next(iter(ids))
        cid = self.con.execute("INSERT INTO colleges(name,country) VALUES (?,?)", (name, country)).lastrowid
        self.con.execute("INSERT OR IGNORE INTO college_aliases VALUES (?,?,?, 'auto')", (n, cid, name))
        self.exact[n].add(cid)
        return cid
