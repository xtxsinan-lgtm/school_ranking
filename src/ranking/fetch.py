"""Download with on-disk cache. Raw files are kept so extraction can be re-run offline."""
import hashlib
import re
import time
from datetime import datetime, timezone

import requests

from .db import RAW

UA = "Mozilla/5.0"


def fetch(url, subdir, force=False):
    """Return (path, sha256, fetched_at). Cached under data/raw/<subdir>/."""
    d = RAW / subdir
    d.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^A-Za-z0-9]+", "_", url.split("//", 1)[-1])[-80:]
    existing = sorted(d.glob(stem + ".*"))
    if existing and not force:
        p = existing[-1]
        return p, hashlib.sha256(p.read_bytes()).hexdigest(), datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat()
    r = requests.get(url, headers={"User-Agent": UA, "Accept": "text/html,application/pdf,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"}, timeout=60, allow_redirects=True)
    r.raise_for_status()
    ct = r.headers.get("content-type", "")
    ext = "pdf" if ("pdf" in ct or r.content[:4] == b"%PDF") else "csv" if "csv" in ct else "html"
    p = d / f"{stem}.{ext}"
    p.write_bytes(r.content)
    time.sleep(1)  # be polite
    return p, hashlib.sha256(r.content).hexdigest(), datetime.now(timezone.utc).isoformat()
