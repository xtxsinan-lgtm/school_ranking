"""Check the ranking against real destinations (28 Bay Area schools with per-college matriculation counts).

Truth = share of reported matriculants at non-UC colleges ranked above Berkeley in data/bt_ranking.csv (theta > 0.95).
Needs uc_export/ (copied from branch claude/nifty-bell-15sx30: data/export/*.csv.gz).
"""
import re
import pandas as pd

norm = lambda x: re.sub(r"[^a-z0-9]+", " ", re.sub(r"\bthe\b", " ", str(x).lower().replace("&", " and "))).strip()
m = pd.read_csv("uc_export/matriculation_full.csv.gz")
c = pd.read_csv("uc_export/colleges.csv.gz")
bt = pd.read_csv("data/bt_ranking.csv")
ov = pd.read_csv("data/name_overrides.csv")
alias = {norm(a): norm(b) for a, b in zip(ov.name, ov.parchment_name)}
theta = dict(zip(bt.parchment_name.map(norm), bt.theta))
c["theta"] = c.name.map(norm).map(lambda k: alias.get(k, k)).map(theta)
m = m.merge(c[["college_id", "theta"]], on="college_id", how="left")
m["p"] = m.source_origin.map({"official": 0, "user_sheet": 1})
m = m[m.p == m.groupby("school").p.transform("min")]          # one source per school
m["elite"] = (m.theta > 0.95) & ~m.college.str.contains("University of California", na=False)
g = m.groupby("school").apply(lambda d: d.loc[d.elite, "count"].sum() / d["count"].sum(), include_groups=False).rename("elite").reset_index()
sch = pd.read_csv("uc_export/schools.csv.gz")[["school_id", "name"]]
u = pd.read_csv("uc_export/uc_schools.csv.gz")[["ceeb", "school_id"]].dropna()
g = g.merge(sch, left_on="school", right_on="name").merge(u, on="school_id")
d = pd.read_csv("data/ca_hs_uc_ranking.csv")
g = g.merge(d, on="ceeb").drop_duplicates("school")
rk = lambda s: s.rank()
print("n schools:", len(g))
for col, sign in [("score", 1), ("bl_adm_rate", 1), ("uc_yield", -1)]:
    print(f"Spearman({col}, elite share) = {sign * rk(g[col]).corr(rk(g.elite)):+.2f}")
print(g.sort_values("rank")[["rank", "school", "elite", "bl_adm_rate", "uc_yield"]].round(3).to_string(index=False))
