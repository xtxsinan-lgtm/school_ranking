"""Minimal two-sheet xlsx (live formulas) for upload to Google Drive: Top50 table + algorithm page.
Reads data/bay_public_top50.csv and data/bay_public_model_params.csv written by uc_bay_top50.py."""
import zipfile, base64
import numpy as np, pandas as pd
from xml.sax.saxutils import escape

p = pd.read_csv("data/bay_public_top50.csv")
P = pd.read_csv("data/bay_public_model_params.csv", header=None, index_col=0)[1]
A = "'算法说明'!"

def cell(ref, v, s=0):
    if v is None or (isinstance(v, float) and np.isnan(v)): return ""
    if isinstance(v, str) and v.startswith("="): return f'<c r="{ref}" s="{s}"><f>{escape(v[1:])}</f></c>'
    if isinstance(v, str): return f'<c r="{ref}" s="{s}" t="inlineStr"><is><t>{escape(v)}</t></is></c>'
    return f'<c r="{ref}" s="{s}"><v>{v}</v></c>'
col = lambda i: "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[i]
def sheet(rows, widths):
    cols = "<cols>" + "".join(f'<col min="{i+1}" max="{i+1}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths)) + "</cols>"
    body = "".join(f'<row r="{r}">' + "".join(cell(f"{col(c)}{r}", v, s) for c, (v, s) in enumerate(row)) + "</row>" for r, row in enumerate(rows, 1))
    return ('<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetViews><sheetView workbookViewId="0"><pane xSplit="2" ySplit="1" topLeftCell="C2" state="frozen"/></sheetView></sheetViews>'
            + cols + "<sheetData>" + body + "</sheetData></worksheet>")
# styles: 0 normal, 1 header bold, 2 percent 0.0%, 3 number 0.00, 4 blue input, 5 blue percent, 6 bold title, 7 wrap
styles = ('<?xml version="1.0" encoding="UTF-8"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
 '<numFmts count="1"><numFmt numFmtId="164" formatCode="0.0%"/></numFmts>'
 '<fonts count="4"><font><sz val="10"/><name val="Arial"/></font><font><b/><sz val="10"/><name val="Arial"/></font>'
 '<font><sz val="10"/><color rgb="FF0000FF"/><name val="Arial"/></font><font><b/><sz val="14"/><name val="Arial"/></font></fonts>'
 '<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
 '<fill><patternFill patternType="solid"><fgColor rgb="FFD9E2F3"/></patternFill></fill></fills>'
 '<borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs>'
 '<cellXfs count="8"><xf/><xf fontId="1" fillId="2" applyFont="1" applyFill="1"><alignment wrapText="1" vertical="center" horizontal="center"/></xf>'
 '<xf numFmtId="164" applyNumberFormat="1"/><xf numFmtId="2" applyNumberFormat="1"/><xf fontId="2" applyFont="1"/>'
 '<xf fontId="2" numFmtId="164" applyFont="1" applyNumberFormat="1"/><xf fontId="3" applyFont="1"/><xf fontId="1" applyFont="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs></styleSheet>')

heads = ["排名","学校","城市","县","UC 申请人数","伯克利+UCLA 申请","伯克利+UCLA 录取","UC 全系统录取","UC 全系统入学",
         "伯克利+UCLA 录取率","UC 全系统入学率","预测 logit","预测比例","区间下限","区间上限","真实比例(升学名单)","名单人数","备注"]
w = pd.read_csv("data/uc_school_pooled_2021_2025.csv").set_index("ceeb")
rows = [[(h, 1) for h in heads]]
for i, r in p.iterrows():
    n = i + 2
    rows.append([
        (f"=RANK(M{n},$M$2:$M$51)", 0), (r["name"], 0), (r.city, 0), (r.region, 0), (int(w.loc[r.ceeb, "App_Universitywide"]), 4),
        (int(r.app), 4), (int(r.adm), 4), (int(r.uadm), 4), (int(r.uenr), 4),
        (f"=G{n}/F{n}", 2), (f"=I{n}/H{n}", 2),
        (f"={A}$B$4+{A}$B$5*(LN(J{n}/(1-J{n}))-{A}$B$7)/{A}$B$8+{A}$B$6*(LN(K{n}/(1-K{n}))-{A}$B$9)/{A}$B$10", 3),
        (f"=1/(1+EXP(-L{n}))", 2), (f"=1/(1+EXP(-(L{n}-1.28*{A}$B$11)))", 2), (f"=1/(1+EXP(-(L{n}+1.28*{A}$B$11)))", 2),
        (None if pd.isna(r.actual) else float(r.actual), 5), (None if pd.isna(r.actual) else int(r.actual_n), 4),
        (r.note if isinstance(r.note, str) else None, 0)])
s1 = sheet(rows, [6,34,14,14,10,12,12,12,12,12,12,9,10,10,10,14,9,36])

text = [
 ("目标","预测每所高中毕业生中,去了排名高于伯克利的非 UC 大学(MIT、Stanford、Yale、Harvard、Princeton、Columbia 等,按 Parchment 互选排名 θ>0.95)的比例。"),
 ("数据来源","UC Information Center 按高中统计的申请、录取、入学人数(加州,2021–2025 秋季学期合并)。UC 把少于 3 人的格子留空,按 1 人补入。"),
 ("特征 1:伯克利+UCLA 录取率","两校合计录取数除以申请数,衡量学生被最难的两个校区接受的程度。"),
 ("特征 2:UC 全系统入学率","UC 录取后实际入学 UC 的比例。入学率低,说明录取生去了别处(Stanford、MIT、常春藤、私校、外州)。模型里这一项取负号:入学率越低,预测越高。"),
 ("为什么不直接用录取率","学生去了更好的学校后不会出现在 UC 入学数里。只看录取率或入学人数,会低估这类学校。"),
 ("模型","预测 logit = b0 + b1 × z(logit 录取率) + b2 × z(logit 入学率);预测比例 = 1/(1+exp(-预测 logit))。z 用全州 1,460 所学校的均值和标准差标准化。"),
 ("拟合方式","用 27 所有真实升学名单的湾区学校做岭回归(惩罚系数 3),目标是上述比例的 logit。"),
 ("检验","留一法交叉验证:每次留出一所学校,用其余 26 所拟合再预测它。预测与真实的 Spearman 约 0.74,RMSE 约 0.56(logit 单位)。第一页的区间上下限为预测 logit ±1.28×RMSE,约 80% 区间。"),
 ("名单范围","旧金山湾区 9 县(Alameda、Contra Costa、Marin、Napa、San Francisco、San Mateo、Santa Clara、Solano、Sonoma)的公立高中,UC 申请人数合计不少于 300,按预测值取前 50。"),
 ("限制 1","校准用的 27 所学校几乎都是湾区富裕学校。低收入学校没去 UC 多半是去了 CSU 或社区大学,模型会把它误读为去了更好的学校。"),
 ("限制 2","UC 综合评审对低收入学校有情境加分。伯克利+UCLA 录取率超过 17% 的学校预测值偏高,已在备注列标出(如 Mission High)。"),
 ("限制 3","有真实名单的公校只有十几所,单校名单从一百多人到两千多人不等。小样本学校(如 Saratoga 136 人、Leland 106 人)的真实比例波动大。"),
 ("限制 4","Gunn(5.1%)、Palo Alto(4.7%)、Los Altos(4.2%)预测值相差不到 1 个百分点,Saratoga(6.2%)高约 1 个百分点,都小于预测误差(约 ±2.7 个百分点),不要把名次差当作实质差距。"),
 ("真实列","第一页的真实比例来自学校公布的升学名单(官方优先,其次用户表格),只有部分学校有。有真实名单的学校,应以真实比例为准。"),
]
prm = [("截距 b0",P.b0),("系数 b1(伯克利+UCLA 录取率)",P.b1),("系数 b2(UC 全系统入学率)",P.b2),("录取率 logit 均值(全州 1460 校)",P.m1),
       ("录取率 logit 标准差",P.s1),("入学率 logit 均值",P.m2),("入学率 logit 标准差",P.s2),("留一法预测误差 RMSE(logit)",P.rmse)]
rows2 = [[("算法说明",6)], [], [("模型参数(蓝色为输入,第一页的公式引用这些单元格)",1)]]
rows2 += [[(k,0),(round(float(v),4),4)] for k,v in prm]
rows2 += [[("留一法 Spearman(预测 vs 真实,27 校)",0),(round(float(P.rho),2),4)], [], [("说明",1)]]
rows2 += [[(k,1),(v,7)] for k,v in text]
s2 = sheet(rows2, [38,110]).replace('<pane xSplit="2" ySplit="1" topLeftCell="C2" state="frozen"/>','')

ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
 '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
 '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
 + "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in (1, 2)) + "</Types>")
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
rels = f'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="{R}/officeDocument" Target="xl/workbook.xml"/></Relationships>'
wb = f'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="{R}"><sheets><sheet name="湾区公校 Top50" sheetId="1" r:id="rId1"/><sheet name="算法说明" sheetId="2" r:id="rId2"/></sheets></workbook>'
wr = f'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="{R}/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="{R}/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="rId3" Type="{R}/styles" Target="styles.xml"/></Relationships>'
with zipfile.ZipFile("bay_public_top50_min.xlsx", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for n, x in [("[Content_Types].xml", ct), ("_rels/.rels", rels), ("xl/workbook.xml", wb), ("xl/_rels/workbook.xml.rels", wr), ("xl/styles.xml", styles),
                 ("xl/worksheets/sheet1.xml", s1), ("xl/worksheets/sheet2.xml", s2)]:
        z.writestr(n, x)
b = base64.b64encode(open("bay_public_top50_min.xlsx", "rb").read()).decode()
open("/tmp/claude-0/min.b64", "w").write(b); print(len(b))
