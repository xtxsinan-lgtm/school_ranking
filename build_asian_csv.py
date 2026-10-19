"""CSV (with live array formulas + parameter block) and an HTML explainer for the Asian-basis Bay Area ranking.
Percent-like columns are in percent units (13.8 = 13.8%) so they read correctly after a plain CSV import.
Run from the repo root: python3 build_asian_csv.py  -> /tmp/claude-0/asian_sheet.csv, /tmp/claude-0/asian_explainer.html"""
import csv, io
import pandas as pd

p = pd.read_csv("data/bay_public_asian_top50.csv")
P = pd.read_csv("data/bay_public_asian_params.csv", header=None, index_col=0)[1]
H = ["排名","学校","县","亚裔占比(%)","亚裔BL申请","亚裔BL录取","亚裔UC录取","亚裔UC入学","先验录取率(%)","录取率收缩后(%)","先验入学率(%)","入学率收缩后(%)",
     "预测logit","预测比例(%)","下限(%)","上限(%)","真实比例(全体名单,%)","全体口径排名","名次变化","备注"]
rows = [H]
f = {
 0: "=ARRAYFORMULA(RANK(N2:N51,N2:N51))",
 9: "=ARRAYFORMULA(100*(F2:F51+$B$62*I2:I51/100)/(E2:E51+$B$62))",
 11: "=ARRAYFORMULA(100*(H2:H51+$B$63*K2:K51/100)/(G2:G51+$B$63))",
 12: "=ARRAYFORMULA($B$54+$B$55*(LN(J2:J51/(100-J2:J51))-$B$57)/$B$58+$B$56*(LN(L2:L51/(100-L2:L51))-$B$59)/$B$60)",
 13: "=ARRAYFORMULA(100/(1+EXP(-M2:M51)))",
 14: "=ARRAYFORMULA(100/(1+EXP(-(M2:M51-1.28*$B$61))))",
 15: "=ARRAYFORMULA(100/(1+EXP(-(M2:M51+1.28*$B$61))))",
 18: "=ARRAYFORMULA(R2:R51-A2:A51)",
}
for i, r in p.iterrows():
    row = [""] * len(H)
    row[1], row[2] = r["name"], r.region
    row[3] = round(100 * float(r.share), 0)
    row[4], row[5], row[6], row[7] = int(r.a_app), int(r.a_adm), int(r.a_uadm), int(r.a_uenr)
    row[8], row[10] = round(100 * float(r.prior_rate), 2), round(100 * float(r.prior_yield), 2)
    row[16] = "" if pd.isna(r.actual) else round(100 * float(r.actual), 1)
    row[17] = int(r.rank_all)
    row[19] = r.note if isinstance(r.note, str) else ""
    if i == 0:
        for k, v in f.items(): row[k] = v
    rows.append(row)
rows += [[], ["模型参数(第一页公式引用这些单元格)"]]
for k, v in [("截距 b0", P.b0), ("系数 b1(亚裔录取率)", P.b1), ("系数 b2(亚裔UC入学率)", P.b2), ("录取率 logit 均值", P.m1), ("录取率 logit 标准差", P.s1),
             ("入学率 logit 均值", P.m2), ("入学率 logit 标准差", P.s2), ("留一法预测误差 RMSE(logit)", P.rmse), ("收缩强度 K(录取率)", P.kr), ("收缩强度 K(入学率)", P.ky),
             ("留一法 Spearman(预测 vs 真实)", P.rho)]:
    rows.append([k, round(float(v), 4)])
rows.append(["说明见 Google 文档「算法说明:湾区公立高中 Top50 亚裔升学难度排名」。列 A、J、L–P、S 是数组公式,只在第 2 行有公式。"])
buf = io.StringIO(); csv.writer(buf, lineterminator="\n").writerows(rows)
open("/tmp/claude-0/asian_sheet.csv", "w").write(buf.getvalue())

html = f"""<h1>湾区公立高中 Top50:亚裔升学难度排名 算法说明</h1>
<h2>目标</h2><p>为亚裔家长回答:这所学校的亚裔学生整体表现如何。预测每所学校毕业生中,去了排名高于伯克利的非 UC 大学(MIT、Stanford、Yale、Harvard、Princeton、Columbia 等,按 Parchment 互选排名 θ&gt;0.95)的比例。</p>
<h2>为什么用亚裔口径</h2><p>亚裔申请者在 UC 的录取率低于全体申请者,高亚裔比例的学校(Lynbrook、Mission San Jose 等)的全体录取率被人口构成压低,不能直接比较。本表只用 UC 公布的「Asian」子群数据,比较各校亚裔学生之间的差别。</p>
<h2>数据</h2><p>UC Information Center 按高中、按族裔统计的申请、录取、入学人数,加州,2021–2025 年秋季学期合并。少于 3 人的格子在源数据里留空,按 1 人补入。表中 BL 指伯克利和 UCLA 两校合计。</p>
<h2>两个特征</h2>
<ul><li>亚裔 BL 录取率:亚裔申请者在伯克利和 UCLA 的合计录取数除以申请数。</li>
<li>亚裔 UC 全系统入学率:亚裔学生被 UC 录取后实际入学 UC 的比例。入学率低,说明录取生去了别处(Stanford、MIT、常春藤、私校、外州),模型里取负号。</li></ul>
<h2>小样本处理</h2><p>收缩后比例 =(数量 + K × 先验)/(申请数 + K)。先验是该校全体学生的比例经全州 logit 回归推出的亚裔预期值(表中「先验」两列,为输入)。亚裔 BL 申请不足 60 人的学校不入榜。</p>
<h2>模型</h2><p>预测 logit = b0 + b1 × z(logit 收缩后录取率) + b2 × z(logit 收缩后入学率);预测比例 = 1/(1+exp(−logit))。z 用全州有足够亚裔数据的学校的均值和标准差标准化。参数见表格下方的参数块(b0 = {P.b0:.3f},b1 = {P.b1:.3f},b2 = {P.b2:.3f})。</p>
<h2>拟合与检验</h2><p>用 {int(P.n)} 所有真实升学名单的学校(含湾区私校)做岭回归(惩罚系数 3)。留一法交叉验证:预测与真实的 Spearman 约 {P.rho:.2f},RMSE 约 {P.rmse:.2f}(logit 单位)。全体口径同样做法是 0.71 和 0.57。表中下限、上限是预测 logit ±1.28×RMSE,约 80% 区间。</p>
<h2>名单范围与对照列</h2><p>湾区 9 县(Alameda、Contra Costa、Marin、Napa、San Francisco、San Mateo、Santa Clara、Solano、Sonoma)的公立高中,亚裔 BL 申请不少于 60 人的共 {int(P.nrank)} 所,按预测值取前 50。「全体口径排名」是同一批学校内、不分族裔的上一版排名;「名次变化」为全体口径排名减亚裔口径排名,正数表示亚裔口径下更靠前。</p>
<h2>限制</h2>
<ol><li>升学名单没有族裔信息,校准目标是全体学生的去向。模型用亚裔数据预测全体学生的去向,没有直接验证亚裔学生的去向。</li>
<li>UC 的「亚裔」是一个大类,含华裔、印度裔、越南裔、菲律宾裔等,无法再分。</li>
<li>校准学校几乎都是湾区富裕学校。低收入学校入学率低,多半是去了 CSU 或社区大学。备注列对这类情况和 UC 情境加分有提示,这些学校的预测不可靠(如 Mission High)。备注列另标出亚裔样本少于 100 人的学校,这些学校的预测主要来自先验。</li>
<li>预测值差距小于预测误差(约 ±2.7 个百分点)时,不要把名次差当作实质差距。学校的平均表现也不等于孩子个人的录取概率,成绩、活动和申请专业的影响更大。</li></ol>"""
open("/tmp/claude-0/asian_explainer.html", "w").write(html)
print(len(buf.getvalue()), len(html))
