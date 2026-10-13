"""Calibrated prediction of 'share of graduates at colleges ranked above Berkeley' for SF Bay Area public high schools.

pred_logit = b0 + b1 * z(logit B+L admit rate) + b2 * z(logit UC-wide yield)
b0..b2 are ridge-fitted on the 27 schools with real matriculation lists (uc_validate.py ground truth).
Writes data/bay_public_top50.csv and bay_public_top50.xlsx (sheet 1 uses live formulas over labeled parameters).
"""
import re, sys
import numpy as np, pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

BAY = ["Alameda", "Contra Costa", "Marin", "Napa", "San Francisco", "San Mateo", "Santa Clara", "Solano", "Sonoma"]
MIN_APP, LAM = 300, 3.0
lg = lambda p: np.log(np.clip(p, .01, .99) / (1 - np.clip(p, .01, .99)))

src = open("uc_validate.py").read().split("d = pd.read_csv")[0]
exec(src)                                    # builds g: school, elite, ceeb ... (ground truth)
n_students = m.groupby("school")["count"].sum()

d = pd.read_csv("data/ca_hs_uc_ranking.csv")
d["x1"], d["x2"] = lg(d.bl_adm_rate), lg(d.uc_yield)
mu, sd = d[["x1", "x2"]].mean(), d[["x1", "x2"]].std()
gg = g[["school", "elite", "ceeb"]].merge(d[["ceeb", "x1", "x2"]], on="ceeb").drop_duplicates("school")
Z = ((gg[["x1", "x2"]] - mu) / sd).values
X, y = np.c_[np.ones(len(gg)), Z], lg(gg.elite.values + .005)
pen = LAM * np.diag([0, 1, 1])
b = np.linalg.solve(X.T @ X + pen, X.T @ y)
pred_loo = np.array([np.r_[1, Z[i]] @ np.linalg.solve(X[np.arange(len(y)) != i].T @ X[np.arange(len(y)) != i] + pen,
                                                    X[np.arange(len(y)) != i].T @ y[np.arange(len(y)) != i]) for i in range(len(y))])
rmse = float(np.sqrt(np.mean((pred_loo - y) ** 2)))
rho = float(pd.Series(pred_loo).rank().corr(pd.Series(y).rank()))
print("coef", b.round(3), "LOO rmse %.2f spearman %.2f n=%d" % (rmse, rho, len(y)))

p = d[(d.sector == "public") & d.region.isin(BAY) & (d.app >= MIN_APP)].copy()
p["pred"] = b[0] + b[1] * (p.x1 - mu.x1) / sd.x1 + b[2] * (p.x2 - mu.x2) / sd.x2
p = p.sort_values("pred", ascending=False).head(50).reset_index(drop=True)
truth = gg.set_index("ceeb")
sch = pd.read_csv("uc_export/schools.csv.gz")[["school_id", "name"]]
p["actual"] = p.ceeb.map(truth.elite)
p["actual_n"] = p.ceeb.map(lambda c: n_students.get(g.set_index("ceeb").school.get(c), np.nan) if c in truth.index else np.nan)
p["note"] = np.where(p.bl_adm_rate > 0.17, "录取率可能含 UC 情境加分,预测偏高", "")
p["name"] = p.name.str.title().str.replace(r"\bHs\b", "HS", regex=True)
p.to_csv("data/bay_public_top50.csv", index=False)
pd.Series({"b0": b[0], "b1": b[1], "b2": b[2], "m1": mu.x1, "s1": sd.x1, "m2": mu.x2, "s2": sd.x2, "rmse": rmse, "rho": rho}).to_csv("data/bay_public_model_params.csv", header=False)

# ---------------- workbook ----------------
F = "Arial"
hdr = PatternFill("solid", fgColor="D9E2F3")
blue, bold = Font(name=F, color="0000FF"), Font(name=F, bold=True)
wb = Workbook(); ws = wb.active; ws.title = "湾区公校 Top50"; al = wb.create_sheet("算法说明")

# parameters on the algorithm sheet (labeled cells; formulas on sheet 1 point at them)
params = [("截距 b0", b[0]), ("系数 b1(伯克利+UCLA 录取率)", b[1]), ("系数 b2(UC 全系统入学率)", b[2]),
          ("录取率 logit 均值(全州 1460 校)", mu.x1), ("录取率 logit 标准差", sd.x1),
          ("入学率 logit 均值", mu.x2), ("入学率 logit 标准差", sd.x2), ("留一法预测误差 RMSE(logit)", rmse)]
al["A1"] = "算法说明"; al["A1"].font = Font(name=F, bold=True, size=14)
al["A3"] = "模型参数(蓝色为输入,第一页的公式引用这些单元格)"; al["A3"].font = bold
for i, (k, v) in enumerate(params):
    r = 4 + i; al.cell(r, 1, k).font = Font(name=F); c = al.cell(r, 2, float(v)); c.font = blue; c.number_format = "0.000"
P = {"b0": "'算法说明'!$B$4", "b1": "'算法说明'!$B$5", "b2": "'算法说明'!$B$6", "m1": "'算法说明'!$B$7",
     "s1": "'算法说明'!$B$8", "m2": "'算法说明'!$B$9", "s2": "'算法说明'!$B$10", "e": "'算法说明'!$B$11"}
al["A12"] = "留一法 Spearman(预测 vs 真实,27 校)"; al["B12"] = rho; al["B12"].font = blue; al["B12"].number_format = "0.00"
al["A12"].font = Font(name=F)
text = [
 ("目标", "预测每所高中毕业生中,去了「排名高于伯克利的非 UC 大学」(MIT、Stanford、Yale、Harvard、Princeton、Columbia 等,按 Parchment 互选排名 θ>0.95)的比例。"),
 ("数据来源", "UC Information Center 按高中统计的申请、录取、入学人数(加州,2021–2025 秋季学期合并)。UC 把少于 3 人的格子留空,按 1 人补入。"),
 ("特征 1:伯克利+UCLA 录取率", "两校合计录取数 ÷ 申请数。它衡量学生被最难的两个校区接受的程度。"),
 ("特征 2:UC 全系统入学率", "UC 录取后实际入学 UC 的比例。入学率低说明录取生去了别处(Stanford、MIT、常春藤、私校、外州)。这一项在模型里取负号:入学率越低,预测越高。"),
 ("为什么不直接用录取率", "学生去更好的学校后不会出现在 UC 入学数里。只看录取率或入学人数会低估这类学校。"),
 ("模型", "预测 logit = b0 + b1 × z(logit 录取率) + b2 × z(logit 入学率),预测比例 = 1/(1+exp(-预测 logit))。z 是用全州 1,460 所学校的均值和标准差标准化。"),
 ("拟合方式", "用 27 所有真实升学名单的湾区学校做岭回归(惩罚系数 3),目标是上述比例的 logit。"),
 ("检验", "留一法交叉验证:每次留出一所学校,用其余 26 所拟合再预测它。预测与真实的 Spearman 约 0.74,RMSE 约 0.55(logit 单位)。第一页的上下限用 ±1.28×RMSE 给出约 80% 区间。"),
 ("名单范围", "旧金山湾区 9 县(Alameda、Contra Costa、Marin、Napa、San Francisco、San Mateo、Santa Clara、Solano、Sonoma)的公立高中,合并后 UC 申请人数不少于 300,按预测值取前 50。"),
 ("限制 1", "校准用的 27 所学校几乎都是湾区富裕学校。低收入学校「没去 UC」多半是去了 CSU 或社区大学,模型会把它误读为「去了更好的学校」。"),
 ("限制 2", "UC 综合评审对低收入学校有情境加分,伯克利+UCLA 录取率超过 17% 的学校预测值偏高,已在备注列标出(如 Mission High)。"),
 ("限制 3", "27 所验证学校里有真实名单的公校只有十几所,单校名单从一百多人到两千多人不等,小样本学校(如 Saratoga 136 人、Leland 106 人)的真实比例波动大。"),
 ("限制 4", "预测不区分前几名的细微差别。Gunn(5.1%)、Palo Alto(4.7%)、Los Altos(4.2%)预测值相差不到 1 个百分点,Saratoga(6.2%)高约 1 个百分点,都小于预测误差(约 ±2.7 个百分点),不要把名次差当作实质差距。"),
 ("真实列", "第一页的「真实比例」来自学校公布的升学名单(官方优先,其次用户表格),只有部分学校有。有真实名单的学校,应以真实比例为准。"),
]
al["A14"] = "说明"; al["A14"].font = bold
for i, (k, v) in enumerate(text):
    r = 15 + i; al.cell(r, 1, k).font = bold; c = al.cell(r, 2, v); c.font = Font(name=F); c.alignment = Alignment(wrap_text=True, vertical="top")
    al.cell(r, 1).alignment = Alignment(vertical="top", wrap_text=True)
al.column_dimensions["A"].width = 38; al.column_dimensions["B"].width = 110

heads = ["排名", "学校", "城市", "县", "UC 申请人数", "伯克利+UCLA 申请", "伯克利+UCLA 录取", "UC 全系统录取", "UC 全系统入学",
         "伯克利+UCLA 录取率", "UC 全系统入学率", "预测 logit", "预测比例", "区间下限", "区间上限", "真实比例(升学名单)", "名单人数", "备注"]
for j, h in enumerate(heads, 1):
    c = ws.cell(1, j, h); c.font = bold; c.fill = hdr; c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
w = pd.read_csv("data/uc_school_pooled_2021_2025.csv").set_index("ceeb")
for i, r in p.iterrows():
    n = i + 2
    vals = [None, r["name"], r.city, r.region, int(w.loc[r.ceeb, "App_Universitywide"]), int(r.app), int(r.adm), int(r.uadm), int(r.uenr)]
    for j, v in enumerate(vals, 1):
        if v is not None: ws.cell(n, j, v).font = blue if j >= 5 else Font(name=F)
    f = Font(name=F)
    ws.cell(n, 1, f"=RANK(M{n},$M$2:$M$51)").font = f
    ws.cell(n, 10, f"=G{n}/F{n}").number_format = "0.0%"
    ws.cell(n, 11, f"=I{n}/H{n}").number_format = "0.0%"
    ws.cell(n, 12, f"={P['b0']}+{P['b1']}*(LN(J{n}/(1-J{n}))-{P['m1']})/{P['s1']}+{P['b2']}*(LN(K{n}/(1-K{n}))-{P['m2']})/{P['s2']}").number_format = "0.00"
    ws.cell(n, 13, f"=1/(1+EXP(-L{n}))").number_format = "0.0%"
    ws.cell(n, 14, f"=1/(1+EXP(-(L{n}-1.28*{P['e']})))").number_format = "0.0%"
    ws.cell(n, 15, f"=1/(1+EXP(-(L{n}+1.28*{P['e']})))").number_format = "0.0%"
    if not pd.isna(r.actual):
        c = ws.cell(n, 16, float(r.actual)); c.number_format = "0.0%"; c.font = blue
        c = ws.cell(n, 17, int(r.actual_n)); c.font = blue
    if r.note: ws.cell(n, 18, r.note)
    for j in range(1, 19):
        if ws.cell(n, j).font.name != F: ws.cell(n, j).font = Font(name=F, color=ws.cell(n, j).font.color)
for j, wd in enumerate([6, 34, 14, 14, 10, 12, 12, 12, 12, 12, 12, 9, 10, 10, 10, 14, 9, 36], 1):
    ws.column_dimensions[get_column_letter(j)].width = wd
ws.row_dimensions[1].height = 44; ws.freeze_panes = "C2"
wb.save("bay_public_top50.xlsx")
print(p[["name", "city", "pred", "actual"]].head(12).round(3).to_string())
