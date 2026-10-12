"""Shared helpers for talking to Parchment's cross-admit tool."""
import json
import re
import time
import urllib.parse
import urllib.request

BASE = "https://www.parchment.com/c"
UA = "Mozilla/5.0 (research script; school_ranking)"
TOOL = BASE + "/college/tools/college-cross-admit-comparison.php"
SEARCH = BASE + "/includes/ajax/interact.php"

_PCT = re.compile(r"class='percentage'[^>]*>\s*([\d.]+)%")
_NAME = re.compile(r"<h2>([^<]*)</h2>")
_CI = re.compile(r"95% confidence interval:\s*([\d.]+)%\s*to\s*([\d.]+)%")


def http_get(url, params, retries=4, timeout=30):
    full = url + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(full, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf8", errors="replace")
        except Exception as e:  # network / 5xx -> back off and retry
            last = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"GET failed after {retries} tries: {last}")


def search_institutions(term):
    """Parchment autocomplete -> list of {instName, state, id}."""
    body = http_get(SEARCH, {
        "value": term,
        "modifiers[tool]": "institutionSearch",
        "modifiers[handler]": "autocompleteWithInstName",
        "action": "autocomplete",
    })
    return [{"name": d["instName"], "state": d["state"], "id": d["id"]}
            for d in json.loads(body)]


def parse_matchup(html, name_a, name_b):
    """Return None when Parchment has no data for the pair.

    NOTE: an unknown school name makes the page silently fall back to its
    default (UCLA vs Berkeley), so the returned names MUST match the request.
    """
    names = _NAME.findall(html)[:2]
    pcts = _PCT.findall(html)
    cis = _CI.findall(html)
    if not (len(pcts) == 2 and len(cis) == 2 and len(names) == 2):
        return None
    if [n.strip() for n in names] != [name_a, name_b]:
        raise ValueError(f"name mismatch: asked {name_a!r}/{name_b!r}, got {names}")
    return {
        "pct_a": float(pcts[0]), "ci_a_lo": float(cis[0][0]), "ci_a_hi": float(cis[0][1]),
        "pct_b": float(pcts[1]), "ci_b_lo": float(cis[1][0]), "ci_b_hi": float(cis[1][1]),
    }


def fetch_matchup(name_a, name_b):
    html = http_get(TOOL, {"compare": name_a, "with": name_b})
    return parse_matchup(html, name_a, name_b)
