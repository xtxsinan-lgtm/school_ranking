"""usage: crawl_one.py <root_url> [maxpages] -> print links whose url/text look like college outcome data"""
import re, sys
from urllib.parse import urljoin, urlparse
import requests
H = {"User-Agent": "Mozilla/5.0 (compatible; school-ranking-research/0.1)"}
KW = re.compile(r"accept|result|destination|where[-_ ]|class[-_ ]of|matric|profile|college[-_ ]?going|attend|senior|outcome|naviance|post[-_ ]?secondary|\.pdf|\.xlsx|spreadsheet|drive\.google|docs\.google", re.I)
NAV = re.compile(r"college|counsel|guidance|career|about|accountab|profile|data|report|senior|graduat|student|academ|class", re.I)
root = sys.argv[1]; maxp = int(sys.argv[2]) if len(sys.argv) > 2 else 60
host = urlparse(root).netloc
seen, front, hits = set(), [root], {}
while front and len(seen) < maxp:
    u = front.pop(0)
    if u in seen: continue
    seen.add(u)
    try: r = requests.get(u, headers=H, timeout=20)
    except Exception: continue
    if r.status_code != 200 or "html" not in r.headers.get("content-type", ""): continue
    for m in re.finditer(r'href=["\']([^"\']+)["\'][^>]*>([^<]{0,90})', r.text):
        l = urljoin(u, m.group(1)).split("#")[0]; t = re.sub(r"\s+", " ", m.group(2)).strip()
        if re.search(r"matric|accept|destination|college.?(go|attend|outcome|list)|where.*(go|attend)|class[-_ ]of[-_ ]20|school[-_ ]?profile", l + " " + t, re.I):
            hits.setdefault(l, t)
        if urlparse(l).netloc == host and NAV.search(l + t) and l not in seen and not re.search(r"\.(jpg|png|pdf|docx?|xlsx?|mp4)$", l, re.I):
            front.append(l)
for l, t in hits.items(): print(t[:70], "|", l)
print("pages crawled:", len(seen))
