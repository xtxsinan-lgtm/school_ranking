(async function () {
  const H = await loadJSON("data/highschool.json");
  const P = H.params_all, PA = H.params_asian;

  $("#s-ca").textContent = int(H.counts.ca_schools);
  $("#s-val").textContent = H.counts.validation;
  $("#s-rho").textContent = fix(P.rho, 2);
  $("#v-rho").textContent = fix(P.rho, 2);
  $("#src-val").textContent = `${H.counts.validation} 所湾区高中（公立+私立）`;
  $("#src-rows").textContent = `约 ${int(Math.round(H.counts.matric_rows / 100) * 100)} 条“学校–大学–人数”`;
  $("#formula-all").textContent =
    `预测 logit = ${fix(P.b0, 2)} + ${fix(P.b1, 2)} × 录取率标准分 ${P.b2 < 0 ? "−" : "+"} ${fix(Math.abs(P.b2), 2)} × 入学率标准分`;

  /* ---------------- calculator ---------------- */
  const zr = (r) => (logit(r) - P.m1) / P.s1, zy = (y) => (logit(y) - P.m2) / P.s2;
  const predict = (r, y) => P.b0 + P.b1 * zr(r) + P.b2 * zy(y);
  const e = 1.28 * P.rmse;
  function calc() {
    const r = $("#in-r").value / 100, y = $("#in-y").value / 100;
    $("#v-r").textContent = pct(r); $("#v-y").textContent = pct(y);
    const L = predict(r, y);
    $("#out-p").textContent = pct(sig(L));
    $("#out-ci").textContent = `80% 区间：${pct(sig(L - e))} – ${pct(sig(L + e))}`;
    $("#calc-detail").innerHTML =
      `录取率标准分 = ${fix(zr(r), 2)}，入学率标准分 = ${fix(zy(y), 2)}<br>` +
      `预测 logit = ${fix(P.b0, 2)} + ${fix(P.b1, 2)}×${fix(zr(r), 2)} + (${fix(P.b2, 2)})×${fix(zy(y), 2)} = <b>${fix(L, 2)}</b>，换回比例 = ${pct(sig(L))}`;
  }
  $("#in-r").addEventListener("input", calc);
  $("#in-y").addEventListener("input", calc);
  const presetNames = ["Saratoga", "Gunn", "Palo Alto", "Los Altos", "Lynbrook", "Mission San Jose", "Dublin", "Mission Senior"];
  const pool = [...H.top50, ...H.bay.filter((b) => b.sector === "public")];
  presetNames.forEach((n) => {
    const s = pool.find((x) => x.name.toLowerCase().includes(n.toLowerCase()));
    if (!s) return;
    const b = document.createElement("button");
    b.textContent = n;
    b.title = s.name;
    b.onclick = () => { $("#in-r").value = (s.bl_rate * 100).toFixed(1); $("#in-y").value = (s.uc_yield * 100).toFixed(1); calc(); };
    $("#presets").appendChild(b);
  });
  calc();

  /* ---------------- validation scatter ---------------- */
  const V = H.validation;
  const mx = Math.ceil(Math.max(...V.map((v) => Math.max(v.pred, v.actual))) * 50) / 50 + 0.01;
  const label = new Set(["The Harker School", "San Francisco University High School", "Saratoga High", "Los Altos High",
    "Los Gatos High", "Leigh High", "Marin Academy", "Menlo School"]);
  scatter($("#scatter"), V.map((v) => ({
    x: v.pred, y: v.actual, color: v.sector === "private" ? "#8a3fb0" : "#0f8a78",
    r: 4 + Math.sqrt(v.n) / 9, label: v.name.replace(/^The /, "").replace(" School", "").replace(" High", ""), showLabel: label.has(v.name),
    html: `<b>${esc(v.name)}</b>（${v.sector === "private" ? "私立" : "公立"}）<br>预测 ${pct(v.pred)} · 真实 ${pct(v.actual)}<br>名单人数 ${int(v.n)}<br>伯克利+UCLA 录取率 ${pct(v.bl_rate)} · UC 入学率 ${pct(v.uc_yield)}`,
  })), { xmax: mx, ymax: mx, xlab: "模型预测比例", ylab: "真实比例（升学名单）", diag: true, fmtX: (v) => pct(v, 0), fmtY: (v) => pct(v, 0) });

  /* ---------------- tables ---------------- */
  const maxAll = Math.max(...H.top50.map((r) => Math.max(r.hi, r.actual || 0)));
  const maxAs = Math.max(...H.asian50.map((r) => Math.max(r.hi, r.actual || 0)));
  const nameCell = (v, r) => `${esc(v)}<br><small>${esc(r.city)} · ${esc(r.county)}</small>`;
  const tables = {
    all: {
      note: "两个信号用该校全部 UC 申请者计算。“全州名次”是该校在全加州 1,460 所学校按 UC 指标综合分的名次（含私立）。",
      data: H.top50, sortKey: "rank",
      cols: [
        { key: "rank", label: "名次", num: true },
        { key: "name", label: "学校", cls: "name", fmt: nameCell },
        { key: "pred", label: "预测比例", num: true, fmt: (v) => `<b>${pct(v)}</b>`, title: "预测去 6 所顶尖校的比例" },
        { key: "lo", label: "80% 区间 · 真实值", fmt: (v, r) => rangeBar(r.lo, r.hi, r.pred, maxAll, r.actual) + `<small>${pct(r.lo)} – ${pct(r.hi)}</small>`, sort: (r) => r.pred },
        { key: "actual", label: "真实比例", num: true, fmt: (v, r) => (v == null ? "—" : `<b style="color:#e0592a">${pct(v)}</b><br><small>${int(r.actual_n)} 人名单</small>`) },
        { key: "bl_rate", label: "伯克利+UCLA 录取率", num: true, fmt: (v, r) => `${pct(v)}<br><small>${int(r.bl_adm)}/${int(r.bl_app)}</small>` },
        { key: "uc_yield", label: "UC 入学率", num: true, fmt: (v, r) => `${pct(v)}<br><small>${int(r.uc_enr)}/${int(r.uc_adm)}</small>` },
        { key: "state_rank", label: "全州名次", num: true },
        { key: "note", label: "备注", cls: "note", fmt: (v) => esc(v || "") },
      ],
    },
    asian: {
      note: `两个信号只用亚裔申请者计算，并按样本量向全体数据“部分合并”。候选池为湾区有足够亚裔数据的 ${PA.nrank} 所公立高中；“全体口径名次”是同一池子里按全体口径的名次，便于对比。留一法 Spearman = ${fix(PA.rho, 2)}。`,
      data: H.asian50, sortKey: "rank",
      cols: [
        { key: "rank", label: "名次", num: true },
        { key: "name", label: "学校", cls: "name", fmt: nameCell },
        { key: "pred", label: "预测比例", num: true, fmt: (v) => `<b>${pct(v)}</b>` },
        { key: "lo", label: "80% 区间 · 真实值", fmt: (v, r) => rangeBar(r.lo, r.hi, r.pred, maxAs, r.actual) + `<small>${pct(r.lo)} – ${pct(r.hi)}</small>`, sort: (r) => r.pred },
        { key: "actual", label: "真实比例（全体）", num: true, fmt: (v, r) => (v == null ? "—" : `<b style="color:#e0592a">${pct(v)}</b><br><small>${int(r.actual_n)} 人名单</small>`) },
        { key: "asian_share", label: "亚裔占 UC 申请者", num: true, fmt: (v) => pct(v, 0) },
        { key: "rate", label: "亚裔 B+L 录取率（合并后）", num: true, fmt: (v, r) => `${pct(v)}<br><small>原始 ${pct(r.asian_bl_rate_raw)}，${int(r.asian_bl_app)} 人申请</small>` },
        { key: "yield", label: "亚裔 UC 入学率（合并后）", num: true, fmt: (v) => pct(v) },
        { key: "rank_all", label: "全体口径名次", num: true, fmt: (v, r) => { const d = v - r.rank; return `${v} ${d > 0 ? `<span class="up">↑${d}</span>` : d < 0 ? `<span class="down">↓${-d}</span>` : ""}`; } },
        { key: "note", label: "备注", cls: "note", fmt: (v) => esc(v || "") },
      ],
    },
    bay: {
      note: "这是校准之前的“原始”UC 综合分（全加州统一计算），包括私立学校，供参考。综合分 = 录取率标准分，再对强校按 UC 入学率给予加分（入学率越低加分越多）。名次区间来自 2,000 次随机模拟（90% 区间）。仅列伯克利+UCLA 五年合计申请≥60 人的学校。",
      data: H.bay, sortKey: "state_rank",
      cols: [
        { key: "state_rank", label: "全州名次", num: true },
        { key: "name", label: "学校", cls: "name", fmt: nameCell },
        { key: "sector", label: "类型", fmt: (v) => (v === "private" ? `<span class="tag pri">私立</span>` : `<span class="tag pub">公立</span>`) },
        { key: "score", label: "UC 综合分", num: true, fmt: (v) => fix(v, 2) },
        { key: "rank_lo", label: "名次区间", num: true, fmt: (v, r) => `${r.rank_lo} – ${r.rank_hi}` },
        { key: "bl_rate", label: "伯克利+UCLA 录取率", num: true, fmt: (v, r) => `${pct(v)}<br><small>${int(r.bl_app)} 人申请</small>` },
        { key: "uc_yield", label: "UC 入学率", num: true, fmt: (v) => pct(v) },
      ],
    },
  };
  let T;
  function show(t) {
    const c = tables[t];
    $("#tabnote").textContent = c.note;
    T = makeTable($("#table"), c.cols, c.data, { sortKey: c.sortKey, asc: true });
    T.search($("#q").value);
    document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("on", b.dataset.t === t));
  }
  document.querySelectorAll("#tabs button").forEach((b) => (b.onclick = () => show(b.dataset.t)));
  $("#q").addEventListener("input", (ev) => T.search(ev.target.value));
  show("all");
})();
