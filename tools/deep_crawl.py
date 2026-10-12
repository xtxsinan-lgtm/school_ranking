"""Depth-2 crawl (plus sitemap.xml) restricted to college/counseling-ish links; collects pages whose URL/text matches matriculation keywords."""
import csv, re, sqlite3, sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse
import requests
sys.path.insert(0, "src")
from ranking.db import DB_PATH, ROOT
H = {"User-Agent": "Mozilla/5.0 (compatible; school-ranking-research/0.1)"}
KW = re.compile(r"matric|school[-_ ]?profile|college[-_ ]?(attend|accept|admit|destination|placement|bound|data|outcome|enroll)|where[-_ ]?(our[-_ ])?(grads|graduates|seniors)|post[-_ ]?secondary|class[-_ ]of[-_ ]20\d\d[-_ ]college|senior[-_ ]?(profile|outcomes)", re.I)
NAV = re.compile(r"college|counsel|guidance|career|about|accountab|profile|data|report|senior|graduat|academics|student-?(support|services)", re.I)
def get(u):
    try:
        r = requests.get(u, headers=H, timeout=20)
        return r.status_code, r.text if r.status_code == 200 else ""
    except Exception as e:
        return type(e).__name__, ""
def links(base, html):
    return [(urljoin(base, m.group(1)).split("#")[0], m.group(2).strip()) for m in re.finditer(r'(?:href)=["\']([^"\']+)["\'][^>]*>([^<]{0,80})', html)]
def work(row):
    sid, name, site = row
    if not site or site == "No Data": return (name, "", "nosite", "")
    u = site if site.startswith("http") else "https://" + site
    host = urlparse(u).netloc
    st, html = get(u)
    found, seen, frontier = set(), {u}, []
    def scan(base, html):
        for l, t in links(base, html):
            if KW.search(l) or KW.search(t): found.add(l)
            elif urlparse(l).netloc == host and NAV.search(l + " " + t) and l not in seen and not l.lower().endswith((".pdf", ".jpg", ".png", ".doc", ".docx")):
                frontier.append(l)
    if html: scan(u, html)
    sm = get(urljoin(u, "/sitemap.xml"))[1]
    for l in re.findall(r"<loc>([^<]+)</loc>", sm):
        if KW.search(l): found.add(l)
    for depth in range(2):
        cur, frontier = frontier[:25], []
        for l in cur:
            if l in seen: continue
            seen.add(l)
            _, h = get(l)
            if h: scan(l, h)
    return (name, u, st, " | ".join(sorted(found))[:3000])
if len(sys.argv) > 1 and sys.argv[1] == "extra":
    rows = [(0, r["school"], r["site"]) for r in csv.DictReader(open(ROOT / "data" / "extra_sites.csv")) if r["site"]]
    OUTNAME = "discovery_extra.csv"
else:
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("select school_id,name,website from schools order by school_id").fetchall()
    OUTNAME = "discovery_deep.csv"
with ThreadPoolExecutor(12) as ex: res = list(ex.map(work, rows))
with open(ROOT / "data" / OUTNAME, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["school", "site", "status", "candidates"]); w.writerows(res)
print(sum(1 for r in res if r[3]))
