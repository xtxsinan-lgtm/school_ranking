"""Rank California high schools from UC source-school data (fall 2021-2025).

strength = z(logit admit rate at Berkeley+UCLA)        (Beta-shrunk toward the state rate)
leakage  = z(logit universitywide yield)               (UC admits who enroll at no UC: Stanford/MIT/Ivy/private...)
score    = strength - clip(strength, 0, 1) * leakage
  A low yield is credit, not penalty: those admits chose something better.  It is scaled by strength so that
  CSU/community-college/no-enroll melt at typical or low-admit schools is not read as "went somewhere better".
Rank intervals (5th-95th pct) come from Beta posterior draws of both rates.

Tried and rejected: Rasch/IRT ability over all 9 campuses.  Spearman vs real elite destinations was 0.10
(vs 0.69 for the Berkeley+UCLA rate): lower-campus admit rates are driven by the ELC top-9% guarantee, not strength.
"""
import numpy as np, pandas as pd

MIN_APP = 60                 # pooled Berkeley+UCLA applicants
K_RATE, K_YIELD = 50, 50     # Beta pseudo-counts
rng = np.random.default_rng(0)

w = pd.read_csv("data/uc_school_pooled_2021_2025.csv")
w = w.merge(pd.read_csv("uc_export/uc_schools.csv.gz")[["ceeb", "region"]], on="ceeb", how="left")
w["app"] = w.App_Berkeley + w.App_LosAngeles
w["adm"] = w.Adm_Berkeley + w.Adm_LosAngeles
w["uadm"], w["uenr"] = w.Adm_Universitywide, w.Enr_Universitywide
w = w[(w.app >= MIN_APP) & (w.adm > 0) & (w.uadm > 0)].reset_index(drop=True)

p_r, p_y = w.adm.sum() / w.app.sum(), w.uenr.sum() / w.uadm.sum()
a_r, b_r = K_RATE * p_r + w.adm, K_RATE * (1 - p_r) + (w.app - w.adm)
a_y, b_y = K_YIELD * p_y + w.uenr, K_YIELD * (1 - p_y) + (w.uadm - w.uenr)
logit = lambda p: np.log(p / (1 - p))
r_hat, y_hat = a_r / (a_r + b_r), a_y / (a_y + b_y)
mu_r, sd_r, mu_y, sd_y = logit(r_hat).mean(), logit(r_hat).std(), logit(y_hat).mean(), logit(y_hat).std()

def score(r, y):
    zr, zy = (logit(r) - mu_r) / sd_r, (logit(y) - mu_y) / sd_y
    return zr - np.clip(zr, 0, 1) * zy

w["score"] = score(r_hat, y_hat)
D = 2000
draws = score(rng.beta(a_r.values, b_r.values, (D, len(w))), rng.beta(a_y.values, b_y.values, (D, len(w))))
rk = (-draws).argsort(1).argsort(1) + 1
w["rank_lo"], w["rank_hi"] = np.percentile(rk, 5, 0).astype(int), np.percentile(rk, 95, 0).astype(int)
w["bl_adm_rate"], w["uc_yield"] = w.adm / w.app, w.uenr / w.uadm
w["sector"] = np.where(w.school_type.str.contains("private"), "private", "public")
w = w.sort_values("score", ascending=False).reset_index(drop=True)
w.insert(0, "rank", w.index + 1)
cols = ["rank", "name", "city", "region", "sector", "app", "adm", "uadm", "uenr", "bl_adm_rate", "uc_yield",
        "score", "rank_lo", "rank_hi", "ceeb"]
w[cols].round(3).to_csv("data/ca_hs_uc_ranking.csv", index=False)
print(len(w), "schools; state B+L rate %.3f, UC-wide yield %.3f" % (p_r, p_y))
