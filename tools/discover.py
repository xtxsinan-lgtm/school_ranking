"""Shallow crawl of each school's website to find matriculation / school-profile links.
Writes data/discovery.csv: school, site, fetch status, candidate links."""
import csv, re, sqlite3, sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
import requests
sys.path.insert(0, "src")
from ranking.db import DB_PATH, ROOT

KW = re.compile(r"matric|school[-_ ]?profile|college[-_ ]?(attend|accept|admit|destination|placement|bound)|where[-_ ]grads|post[-_ ]?secondary|college[-_ ]?list", re.I)
NAVKW = re.compile(r"college|counsel|guidance|about|accountab|profile", re.I)
H = {"User-Agent": "Mozilla/5.0 (compatible; school-ranking-research/0.1)"}

def get(u):
    try:
        r = requests.get(u, headers=H, timeout=20, allow_redirects=True)
        return r.status_code, r.text if r.status_code == 200 and "html" in r.headers.get("content-type", "") else ""
    except Exception as e:
        return type(e).__name__, ""

def links(base, html):
    out = []
    for m in re.finditer(r'(?:href|data-file-name)=["\']([^"\']+)["\'][^>]*>?([^<]{0,80})', html):
        out.append((urljoin(base, m.group(1)), m.group(2).strip()))
    return out

def work(row):
    sid, name, site = row
    if not site or site == "No Data":
        return (name, "", "nosite", "")
    u = site if site.startswith("http") else "https://" + site
    st, html = get(u)
    cands, seen = set(), set()
    if html:
        L = links(u, html)
        for l, t in L:
            if KW.search(l) or KW.search(t):
                cands.add(l)
        nav = [l for l, t in L if NAVKW.search(l) and l.split("/")[2:3] == u.split("/")[2:3]][:6]
        for l in nav:
            if l in seen: continue
            seen.add(l)
            st2, h2 = get(l)
            if h2:
                for l2, t2 in links(l, h2):
                    if KW.search(l2) or KW.search(t2):
                        cands.add(l2)
    return (name, u, st, " | ".join(sorted(cands))[:1500])

con = sqlite3.connect(DB_PATH)
rows = con.execute("select school_id,name,website from schools order by school_id").fetchall()
with ThreadPoolExecutor(12) as ex:
    res = list(ex.map(work, rows))
with open(ROOT / "data" / "discovery.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["school", "site", "status", "candidates"]); w.writerows(res)
import collections
print(collections.Counter(str(r[2]) for r in res))
print(sum(1 for r in res if r[3]))
