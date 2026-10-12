"""Download candidate URLs from discovery*.csv and flag ones that look like per-college COUNT lists.
usage: probe_candidates.py <outdir> -> data/candidates_scored.csv"""
import csv, hashlib, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
import requests
H = {"User-Agent": "Mozilla/5.0 (compatible; school-ranking-research/0.1)"}
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
cands = set()
for fn in ("data/discovery.csv", "data/discovery_deep.csv", "data/discovery_extra.csv", "data/manual_candidates.csv"):
    if os.path.exists(fn):
        for r in csv.DictReader(open(fn)):
            for u in (r.get("candidates") or r.get("url") or "").split(" | "):
                u = u.split("#")[0].strip()
                if u.startswith("http") and not re.search(r"ncaa|naia|collegedata|nbcbayarea|\.mp4$", u):
                    cands.add((r["school"], u))
NAMES = "Stanford|Berkeley|UCLA|Cornell|Carnegie|Northeastern|Purdue|Michigan|Georgia Tech|Georgia Institute|Boston|Columbia|Duke|Yale|Harvard|Princeton|Santa Clara|Pomona|Wisconsin|Oregon|Arizona|Syracuse|Tufts|Vanderbilt|Rice|Cal Poly|Davis|Irvine|San Diego|Santa Barbara|Santa Cruz|Merced|Riverside".split("|")
CNT = re.compile(r"(?:University|College|Institute|Tech|State|UC|Berkeley|Davis|Irvine|UCLA|Stanford|Cornell|Harvard|Yale|Duke|Rice)[A-Za-z .,&'’–-]{0,40}?[\s:|]+\(?(\d{1,3})\)?(?=\s|$)")
def text(p, isp, raw):
    if isp: return subprocess.run(["pdftotext", "-layout", p, "-"], capture_output=True, text=True).stdout
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw))
def work(c):
    school, u = c
    try: r = requests.get(u, headers=H, timeout=30)
    except Exception as e: return (school, u, type(e).__name__, 0, 0, "")
    if r.status_code != 200: return (school, u, r.status_code, 0, 0, "")
    isp = r.content[:4] == b"%PDF"
    p = f"{OUT}/{hashlib.md5(u.encode()).hexdigest()[:10]}.{'pdf' if isp else 'html'}"
    open(p, "wb").write(r.content)
    t = text(p, isp, r.text if not isp else "")
    return (school, u, "pdf" if isp else "html", sum(n in t for n in NAMES), len(CNT.findall(t)), p)
with ThreadPoolExecutor(10) as ex: res = list(ex.map(work, sorted(cands)))
with open("data/candidates_scored.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["school", "url", "kind", "known_names", "count_lines", "local"]); w.writerows(res)
for r in res:
    if isinstance(r[3], int) and r[3] >= 6: print(r[3], r[4], r[0], r[1][:110])
print(len(res))
