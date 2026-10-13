"""Asian-applicant-basis prediction for SF Bay Area public high schools.

Same target as uc_bay_top50.py (share of graduates at non-UC colleges ranked above Berkeley), but the two features
are computed on Asian applicants only (UC's 'Asian' category), so a school is compared on how its Asian students fare,
not on how its whole applicant pool fares.

 1. Asian counts: App/Adm/Enr at Berkeley, UCLA and UC-wide, fall 2021-2025, suppressed cells (<3) imputed as 1.
 2. Partial pooling: Asian B+L admit rate and UC-wide yield are Beta-shrunk toward a prior predicted from the school's
    all-student value (logit-logit regression across schools) with pseudo-count K, so thin Asian pools lean on the school.
 3. Schools with fewer than MIN_ASIAN_APP Asian Berkeley+UCLA applicants are not ranked.
 4. Ridge fit (lam=3) on the schools with real matriculation lists; leave-one-out error reported.
"""
import numpy as np, pandas as pd

BAY = ["Alameda", "Contra Costa", "Marin", "Napa", "San Francisco", "San Mateo", "Santa Clara", "Solano", "Sonoma"]
MIN_ASIAN_APP, KR, KY, LAM, TOP = 60, 50, 50, 3.0, 50
lg = lambda p: np.log(np.clip(p, .01, .99) / (1 - np.clip(p, .01, .99)))
exec(open("uc_validate.py").read().split("d = pd.read_csv")[0])     # g: school, elite, ceeb  (ground truth)
nlist = m.groupby("school")["count"].sum()

e = pd.read_csv("uc_export/uc_ethnicity.csv.gz")
e = e[e.fall_term.between(2021, 2025) & e.campus.isin(["Berkeley", "Los Angeles", "Universitywide"])]
def pooled(eth):
    x = e[e.ethnicity == eth].pivot_table(index=["ceeb", "fall_term", "campus"], columns="measure", values="count", aggfunc="sum")[["App", "Adm", "Enr"]]
    x["Adm"] = x.Adm.where(x.Adm.notna(), x.App.notna() * 1.0).where(x.App.notna() | x.Adm.notna())
    x["Enr"] = x.Enr.where(x.Enr.notna(), x.Adm.notna() * 1.0).where(x.Adm.notna() | x.Enr.notna())
    x = x.reset_index().groupby(["ceeb", "campus"])[["App", "Adm", "Enr"]].sum().reset_index()
    x = x.pivot(index="ceeb", columns="campus", values=["App", "Adm", "Enr"]).fillna(0)
    x.columns = [f"{a}_{c}".replace(" ", "") for a, c in x.columns]
    o = pd.DataFrame(index=x.index)
    o["app"], o["adm"] = x.App_Berkeley + x.App_LosAngeles, x.Adm_Berkeley + x.Adm_LosAngeles
    o["uapp"], o["uadm"], o["uenr"] = x.App_Universitywide, x.Adm_Universitywide, x.Enr_Universitywide
    return o
A, L = pooled("Asian"), pooled("All")
sc = pd.read_csv("uc_export/uc_schools.csv.gz").set_index("ceeb")
D = A.add_prefix("a_").join(L.add_prefix("l_"), how="inner").join(sc[["name", "city", "region", "school_type"]])
D["share"] = D.a_uapp / D.l_uapp
D = D[(D.a_app >= MIN_ASIAN_APP) & (D.a_uadm > 0) & (D.l_adm > 0) & (D.l_uadm > 0)].copy()

# --- prior from all-student value, then Beta shrinkage --------------------------------------------------
x1, y1 = lg(D.l_adm / D.l_app), lg(D.a_adm / D.a_app)
x2, y2 = lg(D.l_uenr / D.l_uadm), lg(D.a_uenr / D.a_uadm)
(b1r, a1r), (b1y, a1y) = np.polyfit(x1, y1, 1), np.polyfit(x2, y2, 1)
sig = lambda z: 1 / (1 + np.exp(-z))
D["prior_rate"], D["prior_yield"] = sig(a1r + b1r * x1).round(4), sig(a1y + b1y * x2).round(4)   # rounded: these are typed into the sheet
D["rate"] = (D.a_adm + KR * D.prior_rate) / (D.a_app + KR)
D["yld"] = (D.a_uenr + KY * D.prior_yield) / (D.a_uadm + KY)
f1, f2 = lg(D.rate), lg(D.yld)
mu1, sd1, mu2, sd2 = f1.mean(), f1.std(), f2.mean(), f2.std()
D["z1"], D["z2"] = (f1 - mu1) / sd1, (f2 - mu2) / sd2

# --- calibration on real lists ---------------------------------------------------------------------------
T = g[["school", "elite", "ceeb"]].drop_duplicates("school").merge(D[["z1", "z2"]], left_on="ceeb", right_index=True)
X, y = np.c_[np.ones(len(T)), T[["z1", "z2"]].values], lg(T.elite.values + .005)
pen = LAM * np.diag([0, 1, 1])
b = np.linalg.solve(X.T @ X + pen, X.T @ y)
loo = np.array([X[i] @ np.linalg.solve(X[np.arange(len(y)) != i].T @ X[np.arange(len(y)) != i] + pen, X[np.arange(len(y)) != i].T @ y[np.arange(len(y)) != i]) for i in range(len(y))])
rmse, rho = float(np.sqrt(np.mean((loo - y) ** 2))), float(pd.Series(loo).rank().corr(pd.Series(y).rank()))
print("n=%d coef %s LOO rmse %.2f spearman %.2f" % (len(y), b.round(3), rmse, rho))
D["pred"] = b[0] + b[1] * D.z1 + b[2] * D.z2

# --- all-student basis for comparison (model from uc_bay_top50.py) ---------------------------------------
P = pd.read_csv("data/bay_public_model_params.csv", header=None, index_col=0)[1]
D["pred_all"] = P.b0 + P.b1 * (x1 - P.m1) / P.s1 + P.b2 * (x2 - P.m2) / P.s2
B = D[D.region.isin(BAY) & (D.school_type == "California public high school")].copy()
B["rank_all"] = B.pred_all.rank(ascending=False, method="first").astype(int)
NPOOL = len(B)
B = B.sort_values("pred", ascending=False).reset_index().head(TOP)
nm = g.drop_duplicates("ceeb").set_index("ceeb").school
B["actual"] = B.ceeb.map(T.set_index("ceeb").elite)
B["actual_n"] = B.ceeb.map(lambda c: nlist.get(nm.get(c), np.nan))
B["note"] = np.where(B.rate > 0.17, "亚裔录取率偏高,可能含 UC 情境加分", np.where(B.a_app < 100, "亚裔样本少(BL申请<100),预测依赖先验", ""))
B["name"] = B.name.str.title().str.replace(r"\bHs\b", "HS", regex=True)
B.round(5).to_csv("data/bay_public_asian_top50.csv", index=False)
pd.Series({"b0": b[0], "b1": b[1], "b2": b[2], "m1": mu1, "s1": sd1, "m2": mu2, "s2": sd2, "rmse": rmse, "kr": KR, "ky": KY, "rho": rho,
           "pr_a": a1r, "pr_b": b1r, "py_a": a1y, "py_b": b1y, "n": len(y), "nrank": NPOOL}).to_csv("data/bay_public_asian_params.csv", header=False)
print(B[["name", "share", "rate", "yld", "pred", "rank_all", "actual"]].head(25).round(3).to_string())
print("ranked pool (Bay publics with enough Asian data):", NPOOL)
