"""Build the JSON files used by the GitHub Pages site (docs/).

Standard library only (no pandas), so it runs anywhere:  python3 tools/build_site_data.py
Inputs are the committed result CSVs in data/ (see README); outputs go to docs/data/*.json.

  docs/data/highschool.json  Bay Area public HS Top-50 (all-student and Asian basis), Bay Area UC metrics, validation set
  docs/data/college.json     tier-weighted Bradley-Terry ranking, head-to-head pairs, old-sheet vs new-scrape comparison
"""
import csv
import gzip
import json
import math
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, "data", *p)
OUT = os.path.join(ROOT, "docs", "data")
BAY = ["Alameda", "Contra Costa", "Marin", "Napa", "San Francisco", "San Mateo", "Santa Clara", "Solano", "Sonoma"]


def rows(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf8", newline="") as f:
        return [{k.strip(): (v or "").strip() for k, v in r.items() if k} for r in csv.DictReader(f)]


def num(x, nd=None):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(v):
        return None
    return round(v, nd) if nd is not None else v


def title(s):
    s = s.title()
    s = re.sub(r"\bHs\b", "HS", s)
    s = re.sub(r"\bSchl\b", "School", s)
    s = re.sub(r"\bSr\b", "Senior", s)
    return s


def params(path):
    return {r[0]: float(r[1]) for r in csv.reader(open(path, encoding="utf8")) if r}


lg = lambda p: math.log(min(max(p, .01), .99) / (1 - min(max(p, .01), .99)))
sig = lambda z: 1 / (1 + math.exp(-z))


# ------------------------------------------------------------------ high school ground truth (mirrors uc_validate.py)
def ground_truth():
    norm = lambda x: re.sub(r"[^a-z0-9]+", " ", re.sub(r"\bthe\b", " ", str(x).lower().replace("&", " and "))).strip()
    alias = {norm(r["name"]): norm(r["parchment_name"]) for r in rows(D("name_overrides.csv"))}
    theta = {norm(r["parchment_name"]): float(r["theta"]) for r in rows(D("bt_ranking.csv"))}
    ctheta = {}
    for r in rows(D("export", "colleges.csv.gz")):
        k = norm(r["name"])
        ctheta[r["college_id"]] = theta.get(alias.get(k, k))
    m = rows(D("export", "matriculation_full.csv.gz"))
    pri = {"official": 0, "user_sheet": 1}
    best = {}
    for r in m:
        p = pri.get(r["source_origin"])
        if p is not None:
            best[r["school"]] = min(best.get(r["school"], 9), p)
    tot, elite = {}, {}
    for r in m:
        if pri.get(r["source_origin"]) != best.get(r["school"]):
            continue
        c = float(r["count"] or 0)
        th = ctheta.get(r["college_id"])
        is_elite = th is not None and th > 0.95 and "University of California" not in r["college"]
        tot[r["school"]] = tot.get(r["school"], 0) + c
        if is_elite:
            elite[r["school"]] = elite.get(r["school"], 0) + c
    sid = {}
    for r in rows(D("export", "schools.csv.gz")):
        sid.setdefault(r["name"], []).append(r["school_id"])
    ceebs_of = {}
    for r in rows(D("export", "uc_schools.csv.gz")):
        if r["school_id"]:
            ceebs_of.setdefault(r["school_id"], []).append(int(r["ceeb"]))
    ca = {int(float(r["ceeb"])) for r in rows(D("ca_hs_uc_ranking.csv"))}
    out = {}
    for s, n in tot.items():
        for i in sid.get(s, []):
            hit = [c for c in ceebs_of.get(i, []) if c in ca and c not in out]
            if hit:
                out[hit[0]] = {"school": s, "elite": elite.get(s, 0) / n, "n": int(n)}
                break
    return out


def build_highschool():
    pa = params(D("bay_public_model_params.csv"))
    pz = params(D("bay_public_asian_params.csv"))
    ca = rows(D("ca_hs_uc_ranking.csv"))
    pooled = {int(float(r["ceeb"])): r for r in rows(D("uc_school_pooled_2021_2025.csv"))}
    truth = ground_truth()
    e = 1.28 * pa["rmse"]

    top = []
    for i, r in enumerate(rows(D("bay_public_top50.csv")), 1):
        pr = float(r["pred"])
        ceeb = int(float(r["ceeb"]))
        top.append({
            "rank": i, "name": title(r["name"]), "city": r["city"], "county": r["region"],
            "uc_app": int(float(pooled[ceeb]["App_Universitywide"])) if ceeb in pooled else None,
            "bl_app": int(float(r["app"])), "bl_adm": int(float(r["adm"])),
            "uc_adm": int(float(r["uadm"])), "uc_enr": int(float(r["uenr"])),
            "bl_rate": num(r["bl_adm_rate"], 4), "uc_yield": num(r["uc_yield"], 4),
            "pred": round(sig(pr), 4), "lo": round(sig(pr - e), 4), "hi": round(sig(pr + e), 4),
            "actual": num(r["actual"], 4), "actual_n": int(float(r["actual_n"])) if r["actual_n"] else None,
            "state_rank": int(r["rank"]), "note": r["note"],
        })

    ez = 1.28 * pz["rmse"]
    asian = []
    for i, r in enumerate(rows(D("bay_public_asian_top50.csv")), 1):
        pr = float(r["pred"])
        asian.append({
            "rank": i, "name": title(r["name"]), "city": r["city"], "county": r["region"],
            "asian_share": num(r["share"], 4), "asian_bl_app": int(float(r["a_app"])),
            "asian_bl_rate_raw": round(float(r["a_adm"]) / float(r["a_app"]), 4),
            "rate": num(r["rate"], 4), "yield": num(r["yld"], 4),
            "pred": round(sig(pr), 4), "lo": round(sig(pr - ez), 4), "hi": round(sig(pr + ez), 4),
            "rank_all": int(r["rank_all"]), "actual": num(r["actual"], 4),
            "actual_n": int(float(r["actual_n"])) if r["actual_n"] else None, "note": r["note"],
        })

    bay = []
    for r in ca:
        if r["region"] in BAY:
            bay.append({
                "state_rank": int(r["rank"]), "name": title(r["name"]), "city": r["city"], "county": r["region"],
                "sector": r["sector"], "bl_app": int(float(r["app"])), "bl_rate": num(r["bl_adm_rate"], 4),
                "uc_yield": num(r["uc_yield"], 4), "score": num(r["score"], 3),
                "rank_lo": int(r["rank_lo"]), "rank_hi": int(r["rank_hi"]),
            })

    camap = {int(float(r["ceeb"])): r for r in ca}
    val = []
    for ceeb, t in truth.items():
        if ceeb not in camap:
            continue
        r = camap[ceeb]
        z1 = (lg(float(r["bl_adm_rate"])) - pa["m1"]) / pa["s1"]
        z2 = (lg(float(r["uc_yield"])) - pa["m2"]) / pa["s2"]
        val.append({"name": t["school"], "sector": r["sector"], "actual": round(t["elite"], 4), "n": t["n"],
                    "pred": round(sig(pa["b0"] + pa["b1"] * z1 + pa["b2"] * z2), 4),
                    "bl_rate": num(r["bl_adm_rate"], 4), "uc_yield": num(r["uc_yield"], 4)})
    val.sort(key=lambda v: -v["actual"])

    return {
        "params_all": pa, "params_asian": pz,
        "counts": {"ca_schools": len(ca), "bay_schools": len(bay), "validation": len(val),
                   "matric_rows": sum(1 for _ in rows(D("export", "matriculation_full.csv.gz")))},
        "top50": top, "asian50": asian, "bay": bay, "validation": val,
    }


# ------------------------------------------------------------------ colleges
def build_college():
    sch = rows(D("sheet_schools_resolved.csv"))
    full2abbr = {r["parchment_name"]: r["abbr"] for r in sch}
    cat = {r["parchment_name"]: r["category"] for r in rows(D("schools_resolved.csv"))}
    typ = {r["school"]: r["type"] for r in rows(D("ranking_new_data.csv"))}

    def kind(abbr, full):
        if abbr in typ:
            return "LAC" if typ[abbr].startswith("L") else "University"
        c = cat.get(full, "")
        return "LAC" if "liberal" in c else "University"

    rank = []
    for r in rows(D("wbt_ranking.csv")):
        rank.append({"rank": int(r["rank"]), "abbr": r["abbr"], "name": r["parchment_name"],
                     "type": kind(r["abbr"], r["parchment_name"]),
                     "theta": num(r["theta"], 3), "se": num(r["se"], 3), "lo": int(r["rank_lo"]), "hi": int(r["rank_hi"]),
                     "plain": int(r["plain_bt_rank"]), "eff": int(r["effective_students"])})
    bw = float(rows(D("wbt_ranking.csv"))[0]["bandwidth"])
    cap = {r["abbr"]: int(r["rank"]) for r in rows(D("wbt_cap50_ranking.csv"))}
    for r in rank:
        r["cap50"] = cap.get(r["abbr"])

    n_of = {}
    for r in rows(D("pair_counts.csv")):
        a, b = full2abbr.get(r["a"]), full2abbr.get(r["b"])
        if a and b:
            n_of[(a, b)] = (int(r["k"]), int(r["n"]))
    pairs = []
    for r in rows(D("pairs_long.csv")):
        a, b = r["a"], r["b"]
        k_n = n_of.get((a, b))
        pairs.append([a, b, num(r["pct_a"]), num(r["ci_a_lo"]), num(r["ci_a_hi"]), k_n[1] if k_n else None])

    oldnew = []
    for r in rows(D("ranking_new_data.csv")):
        oldnew.append({"school": r["school"], "type": r["type"], "new_rank": int(r["rank"]), "new_z": num(r["z_score"]),
                       "old_rank": int(r["rank_in_old_data"]), "old_z": num(r["z_score_in_old_data"])})

    return {
        "bandwidth": bw, "ranking": rank, "pairs": pairs, "oldnew": oldnew,
        "counts": {"schools": len(rank), "pairs": len(pairs),
                   "students": sum(n for _, n in n_of.values()),
                   "old_pairs": old_pair_count()},
    }


def old_pair_count():
    r = list(csv.reader(open(D("old_sheet.csv"), encoding="utf8")))
    cols = [c.strip() for c in r[0][1:]]
    return len({frozenset((row[0].strip(), c)) for row in r[1:] for c, v in zip(cols, row[1:])
                if v.strip().isdigit() and row[0].strip() != c})


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, fn in [("highschool", build_highschool), ("college", build_college)]:
        data = fn()
        with open(os.path.join(OUT, name + ".json"), "w", encoding="utf8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        print(name, {k: (len(v) if isinstance(v, list) else v) for k, v in data.items() if k != "params_all" and k != "params_asian"})
