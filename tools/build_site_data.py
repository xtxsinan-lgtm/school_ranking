"""Build the JSON files used by the GitHub Pages site (docs/).

Standard library only (no pandas), so it runs anywhere:  python3 tools/build_site_data.py
Inputs are the committed result CSVs in data/ (see README); outputs go to docs/data/*.json.

  docs/data/highschool.json  Bay Area public HS Top-50 (all-student and Asian basis), Bay Area UC metrics, validation set
  docs/data/college.json     tier-weighted Bradley-Terry ranking, head-to-head pairs, old-sheet vs new-scrape comparison
  docs/data/cn_college.json  China university Gaokao score rankings (2007–2012), 23-prov matrices, city bias matrix
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
ELITE6 = ["MIT", "Stanford", "Yale", "Harvard", "Princeton", "Columbia"]
OTHER_TOP = ["UCB", "UCLA", "CMU", "UPenn", "Cornell", "Brown", "Caltech", "Chicago", "Duke", "Dartmouth", "NYU", "USC"]
CAMPUSES = [
    ("UCB", "Berkeley"), ("UCLA", "LosAngeles"), ("UCSD", "SanDiego"),
    ("UCD", "Davis"), ("UCI", "Irvine"), ("UCSB", "SantaBarbara"),
    ("UCSC", "SantaCruz"), ("UCR", "Riverside"), ("UCM", "Merced"),
    ("All", "Universitywide"),
]


def ground_truth():
    norm = lambda x: re.sub(r"[^a-z0-9]+", " ", re.sub(r"\bthe\b", " ", str(x).lower().replace("&", " and "))).strip()
    alias = {norm(r["name"]): norm(r["parchment_name"]) for r in rows(D("name_overrides.csv"))}
    bt_rows = rows(D("bt_ranking.csv"))
    theta = {norm(r["parchment_name"]): float(r["theta"]) for r in bt_rows}
    abbr_of = {norm(r["parchment_name"]): r["abbr"] for r in bt_rows}
    ctheta, cabbr = {}, {}
    for r in rows(D("export", "colleges.csv.gz")):
        k = norm(r["name"])
        pk = alias.get(k, k)
        ctheta[r["college_id"]] = theta.get(pk)
        cabbr[r["college_id"]] = abbr_of.get(pk)
    m = rows(D("export", "matriculation_full.csv.gz"))
    pri = {"official": 0, "user_sheet": 1}
    best = {}
    for r in m:
        p = pri.get(r["source_origin"])
        if p is not None:
            best[r["school"]] = min(best.get(r["school"], 9), p)
    tot, elite, by_col, meta = {}, {}, {}, {}
    for r in m:
        if pri.get(r["source_origin"]) != best.get(r["school"]):
            continue
        s = r["school"]
        c = float(r["count"] or 0)
        th = ctheta.get(r["college_id"])
        ab = cabbr.get(r["college_id"]) or r["college"]
        is_elite = th is not None and th > 0.95 and "University of California" not in r["college"]
        tot[s] = tot.get(s, 0) + c
        if is_elite:
            elite[s] = elite.get(s, 0) + c
        col_map = by_col.setdefault(s, {})
        col_map[ab] = col_map.get(ab, 0) + int(c)
        md = meta.setdefault(s, {"src": r["source_origin"], "y0": "", "y1": ""})
        y0, y1 = r.get("period_start") or r.get("grad_year") or "", r.get("period_end") or r.get("grad_year") or ""
        if y0 and (not md["y0"] or y0 < md["y0"]):
            md["y0"] = y0
        if y1 and (not md["y1"] or y1 > md["y1"]):
            md["y1"] = y1
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
                cm = by_col.get(s, {})
                md = meta.get(s, {})
                period = f"{md.get('y0','')}-{md.get('y1','')}" if md.get("y0") != md.get("y1") else md.get("y0", "")
                top_dest = [[k, v] for k, v in sorted(cm.items(), key=lambda x: -x[1])[:12] if v > 0]
                out[hit[0]] = {
                    "school": s,
                    "elite": elite.get(s, 0) / n,
                    "elite_n": int(elite.get(s, 0)),
                    "n": int(n),
                    "src": md.get("src", ""),
                    "period": period,
                    "c6": {k: cm.get(k, 0) for k in ELITE6},
                    "c_other": {k: cm.get(k, 0) for k in OTHER_TOP},
                    "top_dest": top_dest,
                }
                break
    return out


def load_uc_gpa():
    acc = {}
    for r in rows(D("export", "uc_gpa.csv.gz")):
        ft = int(r["fall_term"]) if r["fall_term"].isdigit() else 0
        if 2021 <= ft <= 2025 and r["campus"] == "Universitywide":
            v = num(r["gpa"])
            if v is not None:
                ceeb = int(float(r["ceeb"]))
                acc.setdefault(ceeb, {}).setdefault(r["measure"], []).append(v)
    out = {}
    for ceeb, ms in acc.items():
        avg = lambda k: round(sum(ms[k]) / len(ms[k]), 2) if k in ms and ms[k] else None
        out[ceeb] = [avg("App"), avg("Adm"), avg("Enr")]
    return out


def campus_breakdown(pr):
    if not pr:
        return None
    out = []
    for _, col in CAMPUSES:
        a = int(float(pr.get(f"App_{col}", 0) or 0))
        d = int(float(pr.get(f"Adm_{col}", 0) or 0))
        e = int(float(pr.get(f"Enr_{col}", 0) or 0))
        out.append([a, d, e])
    return out


def build_highschool():
    pa = params(D("bay_public_model_params.csv"))
    pz = params(D("bay_public_asian_params.csv"))
    ca = rows(D("ca_hs_uc_ranking.csv"))
    pooled = {int(float(r["ceeb"])): r for r in rows(D("uc_school_pooled_2021_2025.csv"))}
    gpas = load_uc_gpa()
    truth = ground_truth()
    e = 1.28 * pa["rmse"]
    detail_ceebs = set()

    def camp_cols(ceeb):
        p = pooled.get(ceeb, {})
        g = gpas.get(ceeb, [None, None, None])
        ucb_a = int(float(p.get("App_Berkeley", 0) or 0))
        ucb_d = int(float(p.get("Adm_Berkeley", 0) or 0))
        ucb_e = int(float(p.get("Enr_Berkeley", 0) or 0))
        ucla_a = int(float(p.get("App_LosAngeles", 0) or 0))
        ucla_d = int(float(p.get("Adm_LosAngeles", 0) or 0))
        ucla_e = int(float(p.get("Enr_LosAngeles", 0) or 0))
        return {
            "ucb_app": ucb_a, "ucb_adm": ucb_d, "ucb_enr": ucb_e,
            "ucb_rate": round(ucb_d / ucb_a, 4) if ucb_a else None,
            "ucla_app": ucla_a, "ucla_adm": ucla_d, "ucla_enr": ucla_e,
            "ucla_rate": round(ucla_d / ucla_a, 4) if ucla_a else None,
            "ucsd_adm": int(float(p.get("Adm_SanDiego", 0) or 0)),
            "ucd_adm": int(float(p.get("Adm_Davis", 0) or 0)),
            "uci_adm": int(float(p.get("Adm_Irvine", 0) or 0)),
            "ucsb_adm": int(float(p.get("Adm_SantaBarbara", 0) or 0)),
            "gpa_app": g[0], "gpa_adm": g[1], "gpa_enr": g[2],
        }

    top = []
    for i, r in enumerate(rows(D("bay_public_top50.csv")), 1):
        pr = float(r["pred"])
        ceeb = int(float(r["ceeb"]))
        detail_ceebs.add(ceeb)
        x1, x2 = float(r["x1"]), float(r["x2"])
        z1, z2 = (x1 - pa["m1"]) / pa["s1"], (x2 - pa["m2"]) / pa["s2"]
        item = {
            "rank": i, "ceeb": ceeb, "name": title(r["name"]), "city": r["city"], "county": r["region"],
            "uc_app": int(float(pooled[ceeb]["App_Universitywide"])) if ceeb in pooled else None,
            "bl_app": int(float(r["app"])), "bl_adm": int(float(r["adm"])),
            "uc_adm": int(float(r["uadm"])), "uc_enr": int(float(r["uenr"])),
            "bl_rate": num(r["bl_adm_rate"], 4), "uc_yield": num(r["uc_yield"], 4),
            "z1": round(z1, 3), "z2": round(z2, 3), "pred_logit": round(pr, 3),
            "pred": round(sig(pr), 4), "lo": round(sig(pr - e), 4), "hi": round(sig(pr + e), 4),
            "actual": num(r["actual"], 4), "actual_n": int(float(r["actual_n"])) if r["actual_n"] else None,
            "state_rank": int(r["rank"]), "score": num(r["score"], 3),
            "rank_lo": int(r["rank_lo"]), "rank_hi": int(r["rank_hi"]),
            "note": r["note"],
        }
        item.update(camp_cols(ceeb))
        top.append(item)

    ez = 1.28 * pz["rmse"]
    asian = []
    for i, r in enumerate(rows(D("bay_public_asian_top50.csv")), 1):
        pr = float(r["pred"])
        ceeb = int(float(r["ceeb"]))
        detail_ceebs.add(ceeb)
        a_app, a_adm = int(float(r["a_app"])), int(float(r["a_adm"]))
        a_uapp, a_uadm, a_uenr = int(float(r["a_uapp"])), int(float(r["a_uadm"])), int(float(r["a_uenr"]))
        item = {
            "rank": i, "ceeb": ceeb, "name": title(r["name"]), "city": r["city"], "county": r["region"],
            "asian_share": num(r["share"], 4),
            "asian_bl_app": a_app, "asian_bl_adm": a_adm,
            "asian_uc_app": a_uapp, "asian_uc_adm": a_uadm, "asian_uc_enr": a_uenr,
            "asian_bl_rate_raw": round(a_adm / a_app, 4) if a_app else None,
            "asian_yield_raw": round(a_uenr / a_uadm, 4) if a_uadm else None,
            "prior_rate": num(r["prior_rate"], 4), "prior_yield": num(r["prior_yield"], 4),
            "rate": num(r["rate"], 4), "yield": num(r["yld"], 4),
            "z1": num(r["z1"], 3), "z2": num(r["z2"], 3), "pred_logit": round(pr, 3),
            "pred": round(sig(pr), 4), "lo": round(sig(pr - ez), 4), "hi": round(sig(pr + ez), 4),
            "pred_all": round(sig(float(r["pred_all"])), 4),
            "rank_all": int(r["rank_all"]), "actual": num(r["actual"], 4),
            "actual_n": int(float(r["actual_n"])) if r["actual_n"] else None, "note": r["note"],
        }
        item.update(camp_cols(ceeb))
        asian.append(item)

    bay = []
    for r in ca:
        if r["region"] in BAY:
            ceeb = int(float(r["ceeb"]))
            detail_ceebs.add(ceeb)
            bl_r, uc_y = float(r["bl_adm_rate"]), float(r["uc_yield"])
            z1 = (lg(bl_r) - pa["m1"]) / pa["s1"]
            z2 = (lg(uc_y) - pa["m2"]) / pa["s2"]
            pr = pa["b0"] + pa["b1"] * z1 + pa["b2"] * z2
            t_info = truth.get(ceeb)
            item = {
                "state_rank": int(r["rank"]), "ceeb": ceeb, "name": title(r["name"]),
                "city": r["city"], "county": r["region"], "sector": r["sector"],
                "uc_app": int(float(pooled[ceeb]["App_Universitywide"])) if ceeb in pooled else None,
                "bl_app": int(float(r["app"])), "bl_adm": int(float(r["adm"])),
                "uc_adm": int(float(r["uadm"])), "uc_enr": int(float(r["uenr"])),
                "bl_rate": num(r["bl_adm_rate"], 4), "uc_yield": num(r["uc_yield"], 4),
                "score": num(r["score"], 3), "rank_lo": int(r["rank_lo"]), "rank_hi": int(r["rank_hi"]),
                "pred": round(sig(pr), 4),
                "actual": round(t_info["elite"], 4) if t_info else None,
                "actual_n": t_info["n"] if t_info else None,
            }
            item.update(camp_cols(ceeb))
            bay.append(item)

    camap = {int(float(r["ceeb"])): r for r in ca}
    val = []
    for ceeb, t in truth.items():
        if ceeb not in camap:
            continue
        detail_ceebs.add(ceeb)
        r = camap[ceeb]
        z1 = (lg(float(r["bl_adm_rate"])) - pa["m1"]) / pa["s1"]
        z2 = (lg(float(r["uc_yield"])) - pa["m2"]) / pa["s2"]
        pr = pa["b0"] + pa["b1"] * z1 + pa["b2"] * z2
        val.append({
            "ceeb": ceeb, "name": t["school"], "city": r["city"], "county": r["region"],
            "sector": r["sector"], "state_rank": int(r["rank"]),
            "src": t["src"], "period": t["period"],
            "actual": round(t["elite"], 4), "elite_n": t["elite_n"], "n": t["n"],
            "pred": round(sig(pr), 4), "pred_logit": round(pr, 3),
            "lo": round(sig(pr - e), 4), "hi": round(sig(pr + e), 4),
            "bl_app": int(float(r["app"])), "bl_adm": int(float(r["adm"])),
            "uc_adm": int(float(r["uadm"])), "uc_enr": int(float(r["uenr"])),
            "bl_rate": num(r["bl_adm_rate"], 4), "uc_yield": num(r["uc_yield"], 4),
            "z1": round(z1, 3), "z2": round(z2, 3), "score": num(r["score"], 3),
            "c6": t["c6"], "c_other": t["c_other"], "top_dest": t["top_dest"],
        })
    val.sort(key=lambda v: -v["actual"])

    uc_detail = {}
    for ceeb in detail_ceebs:
        if ceeb in pooled:
            uc_detail[str(ceeb)] = {
                "c": campus_breakdown(pooled[ceeb]),
                "gpa": gpas.get(ceeb, [None, None, None]),
            }

    return {
        "params_all": pa, "params_asian": pz,
        "campuses": [c[0] for c in CAMPUSES],
        "elite6": ELITE6, "other_top": OTHER_TOP,
        "counts": {"ca_schools": len(ca), "bay_schools": len(bay), "validation": len(val),
                   "matric_rows": sum(1 for _ in rows(D("export", "matriculation_full.csv.gz")))},
        "top50": top, "asian50": asian, "bay": bay, "validation": val,
        "uc_detail": uc_detail,
    }


# ------------------------------------------------------------------ colleges
def build_college():
    sch = rows(D("sheet_schools_resolved.csv"))
    full2abbr = {r["parchment_name"]: r["abbr"] for r in sch}
    cat = {r["parchment_name"]: r["category"] for r in rows(D("schools_resolved.csv"))}
    typ = {r["school"]: r["type"] for r in rows(D("ranking_new_data.csv"))}
    bt_map = {r["abbr"]: r for r in rows(D("bt_ranking.csv"))}
    cap_map = {r["abbr"]: r for r in rows(D("wbt_cap50_ranking.csv"))}
    old_bt_map = {r["school"]: r for r in rows(D("old_sheet_bt_ranking.csv"))}
    risers_map = {r["school"]: r for r in rows(D("old_vs_new_risers.csv"))}

    def kind(abbr, full):
        if abbr in typ:
            return "LAC" if typ[abbr].startswith("L") else "University"
        c = cat.get(full, "")
        return "LAC" if "liberal" in c else "University"

    n_of = {}
    for r in rows(D("pair_counts.csv")):
        a, b = full2abbr.get(r["a"]), full2abbr.get(r["b"])
        if a and b:
            n_of[(a, b)] = (int(r["k"]), int(r["n"]))
    pairs = []
    wl = {}
    for r in rows(D("pairs_long.csv")):
        a, b = r["a"], r["b"]
        pa = num(r["pct_a"])
        k_n = n_of.get((a, b))
        k_val, n_val = (k_n[0], k_n[1]) if k_n else (None, None)
        pairs.append([a, b, pa, num(r["ci_a_lo"]), num(r["ci_a_hi"]), n_val, k_val])
        sa = wl.setdefault(a, [0, 0, 0])
        sb = wl.setdefault(b, [0, 0, 0])
        if pa > 50:
            sa[0] += 1; sb[1] += 1
        elif pa < 50:
            sa[1] += 1; sb[0] += 1
        else:
            sa[2] += 1; sb[2] += 1

    rank = []
    for r in rows(D("wbt_ranking.csv")):
        ab = r["abbr"]
        bt_r = bt_map.get(ab, {})
        cp_r = cap_map.get(ab, {})
        ob_r = old_bt_map.get(ab, {})
        rs_r = risers_map.get(ab, {})
        w_l_t = wl.get(ab, [0, 0, 0])
        rank.append({
            "rank": int(r["rank"]), "abbr": ab, "name": r["parchment_name"],
            "type": kind(ab, r["parchment_name"]),
            "theta": num(r["theta"], 3), "se": num(r["se"], 3),
            "lo": int(r["rank_lo"]), "hi": int(r["rank_hi"]),
            "plain": int(r["plain_bt_rank"]), "eff": int(r["effective_students"]),
            "plain_theta": num(bt_r.get("theta"), 3), "plain_se": num(bt_r.get("se"), 3),
            "plain_lo": int(bt_r["rank_lo"]) if bt_r.get("rank_lo") else None,
            "plain_hi": int(bt_r["rank_hi"]) if bt_r.get("rank_hi") else None,
            "n_opp": int(bt_r["n_opponents"]) if bt_r.get("n_opponents") else sum(w_l_t),
            "tot_n": int(bt_r["total_students"]) if bt_r.get("total_students") else None,
            "cap50": int(cp_r["rank"]) if cp_r.get("rank") else None,
            "cap50_theta": num(cp_r.get("theta"), 3),
            "cap50_lo": int(cp_r["rank_lo"]) if cp_r.get("rank_lo") else None,
            "cap50_hi": int(cp_r["rank_hi"]) if cp_r.get("rank_hi") else None,
            "old_rank": int(rs_r["old_rank"]) if rs_r.get("old_rank") else None,
            "old_z": num(rs_r.get("old_z"), 2), "new_z": num(rs_r.get("new_z"), 2),
            "delta_z": num(rs_r.get("delta_z"), 2),
            "old_bt_rank": int(ob_r["rank"]) if ob_r.get("rank") else None,
            "old_bt_theta": num(ob_r.get("theta"), 3),
            "sheet_rank": int(ob_r["sheet_row_rank"]) if ob_r.get("sheet_row_rank") else None,
            "wins": w_l_t[0], "losses": w_l_t[1], "ties": w_l_t[2],
        })
    bw = float(rows(D("wbt_ranking.csv"))[0]["bandwidth"])

    oldnew = []
    for r in rows(D("ranking_new_data.csv")):
        ab = r["school"]
        rs_r = risers_map.get(ab, {})
        ob_r = old_bt_map.get(ab, {})
        oldnew.append({
            "school": ab, "type": r["type"],
            "new_rank": int(r["rank"]), "new_z": num(r["z_score"]),
            "old_rank": int(r["rank_in_old_data"]), "old_z": num(r["z_score_in_old_data"]),
            "delta_z": num(rs_r.get("delta_z"), 2),
            "old_pct": int(rs_r["old_percentile"]) if rs_r.get("old_percentile") else None,
            "new_pct": int(rs_r["new_percentile"]) if rs_r.get("new_percentile") else None,
            "sheet_rank": int(ob_r["sheet_row_rank"]) if ob_r.get("sheet_row_rank") else None,
            "old_bt_theta": num(ob_r.get("theta"), 3),
        })

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


# ------------------------------------------------------------------ China universities (Gaokao score rankings 2007-2012)
CN_SHORT2FULL = {
    "清华": "清华大学", "北大": "北京大学", "北大医学部": "北京大学医学部", "复旦": "复旦大学",
    "上交": "上海交通大学", "浙大": "浙江大学", "中大": "中山大学", "科大": "中国科学技术大学",
    "中科大": "中国科学技术大学", "人大": "中国人民大学", "北外": "北京外国语大学", "南大": "南京大学",
    "北航": "北京航空航天大学", "同济": "同济大学", "城大": "香港城市大学", "中财": "中央财经大学",
    "上财": "上海财经大学", "南开": "南开大学", "对外经贸": "对外经济贸易大学", "北师": "北京师范大学",
    "华科": "华中科技大学", "北邮": "北京邮电大学", "政法": "中国政法大学", "上外": "上海外国语大学",
    "西交": "西安交通大学", "哈工大": "哈尔滨工业大学", "中山": "中山大学", "武大": "武汉大学",
    "厦大": "厦门大学", "天大": "天津大学", "北理": "北京理工大学", "东大": "东南大学",
    "华东理工": "华东理工大学", "北科": "北京科技大学", "大工": "大连理工大学", "南航": "南京航空航天大学",
    "华工": "华南理工大学", "北交": "北京交通大学", "北语": "北京语言大学", "南理": "南京理工大学",
    "吉大": "吉林大学", "华东师大": "华东师范大学", "国医": "中国医科大学", "山大": "山东大学",
    "川大": "四川大学", "首都经贸": "首都经济贸易大学", "民大": "中央民族大学", "华电": "华北电力大学",
    "中南财法": "中南财经政法大学", "电子科大": "电子科技大学", "华东政法": "华东政法大学",
    "国防科大": "国防科学技术大学", "中南": "中南大学",
    "中国科技大学": "中国科学技术大学", "华北电力大学(北京)": "华北电力大学",
}

EXTRA_CITIES = {
    "外交学院": "北京", "中国青年政治学院": "北京", "上海海关学院": "上海", "国际关系学院": "北京",
    "南京财经大学": "南京", "天津外国语大学": "天津", "上海立信会计学院": "上海", "西安外国语大学": "西安",
    "香港城市大学": "香港", "国防科学技术大学": "长沙",
}


def norm_cn_school(s):
    return CN_SHORT2FULL.get(s, s)


def build_cn_college():
    std_rows = rows(D("cn_2011_std_top100.csv"))
    provs_std = [k for k in std_rows[0].keys() if k not in ("rank", "city", "school", "tier", "weighted_mean", "mean")]

    raw_rows = rows(D("cn_2011_raw_cutoff_23prov.csv"))
    provs_raw = [k for k in raw_rows[0].keys() if k not in ("order", "school")]
    raw_map = {r["school"]: {p: int(r[p]) if r[p] else None for p in provs_raw} for r in raw_rows}

    sci12_rows = rows(D("cn_2012_sci_top50.csv"))
    arts12_rows = rows(D("cn_2012_arts_top50.csv"))
    p07_4_rows = rows(D("cn_2006_2007_4prov.csv"))
    p07_3_rows = rows(D("cn_2006_2007_3prov.csv"))
    freq07_rows = rows(D("cn_2007_top20_freq.csv"))
    sc10_rows = rows(D("cn_2010_sichuan_raw_sample.csv"))
    bias_rows = rows(D("cn_2011_city_bias.csv"))
    top30_rows = rows(D("cn_2011_top30.csv"))

    city_of = dict(EXTRA_CITIES)
    for r in std_rows:
        city_of[r["school"]] = r["city"]
        city_of[norm_cn_school(r["school"])] = r["city"]

    sci12_map = {norm_cn_school(r["school"]): r for r in sci12_rows}
    arts12_map = {norm_cn_school(r["school"]): r for r in arts12_rows}
    p07_4_map = {norm_cn_school(r["school"]): r for r in p07_4_rows}
    p07_3_map = {norm_cn_school(r["school"]): r for r in p07_3_rows}
    std_map = {norm_cn_school(r["school"]): r for r in std_rows}

    std100 = []
    for idx, r in enumerate(std_rows, 1):
        sch = r["school"]
        nsch = norm_cn_school(sch)
        rk_str = r["rank"]
        num_rk = int(rk_str) if rk_str.isdigit() else None
        wm = float(r["weighted_mean"])
        m = int(r["mean"])
        pvals = {p: int(r[p]) if r[p] else None for p in provs_std}
        valid_p = [(p, v) for p, v in pvals.items() if v is not None]
        max_p = max(valid_p, key=lambda x: x[1]) if valid_p else (None, None)
        min_p = min(valid_p, key=lambda x: x[1]) if valid_p else (None, None)
        s12 = sci12_map.get(nsch)
        a12 = arts12_map.get(nsch)
        p4 = p07_4_map.get(nsch)
        std100.append({
            "order": idx,
            "rank": rk_str,
            "num_rank": num_rk,
            "city": r["city"],
            "school": sch,
            "tier": int(r["tier"]),
            "weighted_mean": wm,
            "mean": m,
            "n_provs": len(valid_p),
            "max_prov": max_p[0], "max_score": max_p[1],
            "min_prov": min_p[0], "min_score": min_p[1],
            "sci12_rank": s12["rank"] if s12 else None,
            "sci12_avg": num(s12["avg_score"], 2) if s12 else None,
            "arts12_rank": int(a12["rank"]) if a12 else None,
            "arts12_avg": num(a12["avg_score"], 2) if a12 else None,
            "p07_4_rank": int(p4["rank"]) if p4 else None,
            "p07_4_avg": num(p4["avg_score"], 1) if p4 else None,
            "scores": [pvals[p] for p in provs_std],
            "raw_scores": [raw_map[sch][p] for p in provs_std] if sch in raw_map else None,
        })

    top30 = []
    for r in top30_rows:
        sch = r["school"]
        st = std_map.get(sch, {})
        s12 = sci12_map.get(sch, {})
        a12 = arts12_map.get(sch, {})
        p4 = p07_4_map.get(sch, {})
        top30.append({
            "rank": int(r["rank"]),
            "school": sch,
            "city": city_of.get(sch, ""),
            "tier": int(st["tier"]) if st.get("tier") else 1,
            "weighted_mean": num(st.get("weighted_mean"), 1),
            "mean": int(st["mean"]) if st.get("mean") else None,
            "sci12_rank": s12.get("rank"),
            "sci12_avg": num(s12.get("avg_score"), 1),
            "arts12_rank": int(a12["rank"]) if a12.get("rank") else None,
            "arts12_avg": num(a12.get("avg_score"), 1),
            "p07_4_rank": int(p4["rank"]) if p4.get("rank") else None,
            "p07_4_avg": num(p4.get("avg_score"), 1),
        })

    provs_5 = ["河南", "广东", "山东", "四川", "安徽"]
    sci12 = []
    for idx, r in enumerate(sci12_rows, 1):
        sch = r["school"]
        nsch = norm_cn_school(sch)
        st = std_map.get(nsch, {})
        p4 = p07_4_map.get(nsch, {})
        a12 = arts12_map.get(nsch, {})
        rk_s = r["rank"]
        sci12.append({
            "order": idx,
            "rank": rk_s,
            "num_rank": int(rk_s) if rk_s.isdigit() else None,
            "school": sch,
            "city": city_of.get(nsch, ""),
            "avg_score": num(r["avg_score"], 2),
            "河南": int(r["河南"]), "广东": int(r["广东"]), "山东": int(r["山东"]),
            "四川": int(r["四川"]), "安徽": int(r["安徽"]),
            "std11_rank": st.get("rank"),
            "std11_wm": num(st.get("weighted_mean"), 1),
            "p07_4_rank": int(p4["rank"]) if p4.get("rank") else None,
            "p07_4_avg": num(p4.get("avg_score"), 1),
            "arts12_rank": int(a12["rank"]) if a12.get("rank") else None,
            "arts12_avg": num(a12.get("avg_score"), 2),
        })

    arts12 = []
    for r in arts12_rows:
        sch = r["school"]
        nsch = norm_cn_school(sch)
        st = std_map.get(nsch, {})
        s12 = sci12_map.get(nsch, {})
        pvals = {p: int(r[p]) if r[p] else None for p in provs_5}
        arts12.append({
            "rank": int(r["rank"]),
            "school": sch,
            "city": city_of.get(nsch, ""),
            "avg_score": num(r["avg_score"], 2),
            "n_provs": sum(1 for v in pvals.values() if v is not None),
            "河南": pvals["河南"], "广东": pvals["广东"], "山东": pvals["山东"],
            "四川": pvals["四川"], "安徽": pvals["安徽"],
            "sci12_rank": s12.get("rank"),
            "sci12_avg": num(s12.get("avg_score"), 2),
            "std11_rank": st.get("rank"),
            "std11_wm": num(st.get("weighted_mean"), 1),
        })

    cols_07_4 = ["江苏07", "江苏06", "河北07", "河北06", "湖北07", "湖北06", "广东07", "广东06"]
    p07_4 = []
    for r in p07_4_rows:
        sch = r["school"]
        nsch = norm_cn_school(sch)
        st = std_map.get(nsch, {})
        s12 = sci12_map.get(nsch, {})
        item = {
            "rank": int(r["rank"]),
            "school": sch,
            "norm_school": nsch,
            "city": city_of.get(nsch, ""),
            "avg_score": num(r["avg_score"], 1),
            "avg_rank": num(r["avg_rank"], 2),
            "std11_rank": st.get("rank"),
            "std11_wm": num(st.get("weighted_mean"), 1),
            "sci12_rank": s12.get("rank"),
            "sci12_avg": num(s12.get("avg_score"), 2),
        }
        for c in cols_07_4:
            item[c] = int(r[c]) if r[c] else None
        p07_4.append(item)

    cols_07_3 = ["山东07", "山东06", "江苏07", "江苏06", "广东07", "广东06"]
    p07_3 = []
    for r in p07_3_rows:
        sch = r["school"]
        nsch = norm_cn_school(sch)
        item = {
            "rank": int(r["rank"]),
            "school": sch,
            "full_school": nsch,
            "city": city_of.get(nsch, ""),
            "avg_score": num(r["avg_score"], 1),
            "avg_rank": num(r["avg_rank"], 2),
        }
        for c in cols_07_3:
            item[c] = int(r[c]) if r[c] else None
        p07_3.append(item)

    special_notes = {
        "外交学院": "提前批（未计入百强主榜）",
        "中国青年政治学院": "提前批（未计入百强主榜）",
        "国际关系学院": "提前批（未计入百强主榜）",
        "上海海关学院": "本科二批（未计入百强主榜）",
    }
    raw11 = []
    for r in raw_rows:
        sch = r["school"]
        st = std_map.get(sch, {})
        scores = [int(r[p]) if r[p] else None for p in provs_raw]
        valid = [v for v in scores if v is not None]
        raw11.append({
            "order": int(r["order"]),
            "school": sch,
            "city": city_of.get(sch, ""),
            "std_rank": st.get("rank", "—"),
            "std_wm": num(st.get("weighted_mean"), 1),
            "note": special_notes.get(sch, ""),
            "n_provs": len(valid),
            "raw_mean": round(sum(valid) / len(valid), 1) if valid else None,
            "scores": scores,
        })

    schools_07 = [k for k in freq07_rows[0].keys() if k != "province"]
    freq_matrix = []
    for r in freq07_rows:
        freq_matrix.append({
            "province": r["province"],
            "ranks": [int(r[s]) if r[s] and r[s] != "NA" else None for s in schools_07],
        })
    freq_summary = []
    for si, s in enumerate(schools_07):
        rks = [row["ranks"][si] for row in freq_matrix if row["ranks"][si] is not None]
        nsch = norm_cn_school(s)
        freq_summary.append({
            "order": si + 1,
            "abbr": s,
            "school": nsch,
            "city": city_of.get(nsch, ""),
            "top20_count": len(rks),
            "top10_count": sum(1 for x in rks if x <= 10),
            "top5_count": sum(1 for x in rks if x <= 5),
            "mean_rank": round(sum(rks) / len(rks), 2) if rks else None,
        })

    cities = [k for k in bias_rows[0].keys() if k != "province"]
    bias_matrix = []
    for r in bias_rows:
        bias_matrix.append({
            "province": r["province"],
            "vals": [num(r[c], 1) if r[c] != "" else None for c in cities],
        })
    city_summary = []
    for ci, c in enumerate(cities):
        pvals = [(row["province"], row["vals"][ci]) for row in bias_matrix if row["vals"][ci] is not None]
        vs = [v for _, v in pvals]
        hi = max(pvals, key=lambda x: x[1])
        lo = min(pvals, key=lambda x: x[1])
        city_summary.append({
            "city": c,
            "mean_bias": round(sum(vs) / len(vs), 2),
            "pos_provs": sum(1 for v in vs if v > 0),
            "neg_provs": sum(1 for v in vs if v < 0),
            "max_prov": hi[0], "max_val": hi[1],
            "min_prov": lo[0], "min_val": lo[1],
        })

    sc10 = [{
        "rank": i,
        "school": r["school"],
        "category": r["category"],
        "province": r["province"],
        "min_score": int(r["min_score"]),
        "avg_score": int(r["avg_score"]),
        "year": int(r["year"]),
        "admitted": int(r["admitted"]),
        "stream": r["stream"],
        "batch": r["batch"],
    } for i, r in enumerate(sc10_rows, 1)]

    return {
        "provs_std": provs_std,
        "provs_raw": provs_raw,
        "provs_5": provs_5,
        "cols_07_4": cols_07_4,
        "cols_07_3": cols_07_3,
        "schools_07": schools_07,
        "cities": cities,
        "std100": std100,
        "top30": top30,
        "sci12": sci12,
        "arts12": arts12,
        "p07_4": p07_4,
        "p07_3": p07_3,
        "raw11": raw11,
        "freq07": {"provinces": [r["province"] for r in freq_matrix], "matrix": freq_matrix, "summary": freq_summary},
        "city_bias": {"matrix": bias_matrix, "summary": city_summary},
        "sichuan10": sc10,
        "counts": {
            "std_schools": len(std100),
            "provs_std": len(provs_std),
            "cities_bias": len(cities),
            "tables": 10,
        },
    }


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, fn in [("highschool", build_highschool), ("college", build_college), ("cn_college", build_cn_college)]:
        data = fn()
        with open(os.path.join(OUT, name + ".json"), "w", encoding="utf8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        print(name, {k: (len(v) if isinstance(v, list) else v) for k, v in data.items() if k != "params_all" and k != "params_asian"})
