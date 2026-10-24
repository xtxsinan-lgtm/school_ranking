(async function () {
  const H = await loadJSON("data/highschool.json");
  const P = H.params_all, PA = H.params_asian;
  const shortName = (s) => s.replace(/^The /, "").replace(/^Henry M\.? /, "")
    .replace(/San Francisco University High School/, "SF University")
    .replace(/Crystal Springs Uplands School/, "Crystal Springs")
    .replace(/Bellarmine College Preparatory/, "Bellarmine")
    .replace(/Urban School of San Francisco/, "Urban School")
    .replace(/International High School.*/, "SF International")
    .replace(/St\. Francis High School.*/, "St. Francis")
    .replace(/ Senior High School$| High School$| Senior High Schl$| High$| School$/, "");

  /* ---------------- KPIs ---------------- */
  $("#s-ca").innerHTML = `${int(H.counts.ca_schools)}<span>校</span>`;
  $("#s-val").innerHTML = `${H.counts.validation}<span>校 / ${int(H.counts.matric_rows)} 条</span>`;
  $("#s-rho").innerHTML = `${fix(P.rho, 2)}<span>/ ${fix(PA.rho, 2)}</span>`;
  $("#s-rmse").innerHTML = `${fix(P.rmse, 2)}<span>/ ${fix(PA.rmse, 2)}</span>`;
  $("#v-rho").textContent = fix(P.rho, 2);
  $("#v-rmse").textContent = fix(P.rmse, 2);

  /* ---------------- Section 01: 27-School Empirical Matriculation Matrix ---------------- */
  let vFilt = "all";
  const VT = makeTable($("#val-table"), [
    { key: "state_rank", label: "全州#", num: true, fmt: rankBadge },
    { key: "name", label: "学校", cls: "name", fmt: (v, r) => `<b>${esc(shortName(v))}</b><small>${esc(r.city)}</small>` },
    { key: "sector", label: "类型", fmt: (v) => (v === "private" ? `<span class="tag pri">私</span>` : `<span class="tag pub">公</span>`) },
    { key: "period", label: "届别·来源", fmt: (v, r) => `<span class="mono" style="font-size:.73rem">${esc(v)} <small>(${r.src === "official" ? "官方" : "汇总"})</small></span>`, hideSm: true },
    { key: "n", label: "样本N", num: true, fmt: int },
    { key: "elite_n", label: "6校合计", num: true, fmt: (v) => `<b>${int(v)}</b>` },
    { key: "actual", label: "实测%", num: true, fmt: (v) => `<span class="truth">${pct(v)}</span>` },
    { key: "pred", label: "预测%", num: true, fmt: (v) => pct(v) },
    { key: "mit", label: "MIT", num: true, sort: (r) => r.c6.MIT, fmt: (_, r) => r.c6.MIT },
    { key: "stf", label: "Stan", num: true, sort: (r) => r.c6.Stanford, fmt: (_, r) => r.c6.Stanford },
    { key: "yal", label: "Yale", num: true, sort: (r) => r.c6.Yale, fmt: (_, r) => r.c6.Yale },
    { key: "har", label: "Harv", num: true, sort: (r) => r.c6.Harvard, fmt: (_, r) => r.c6.Harvard },
    { key: "pri", label: "Prin", num: true, sort: (r) => r.c6.Princeton, fmt: (_, r) => r.c6.Princeton },
    { key: "col", label: "Colu", num: true, sort: (r) => r.c6.Columbia, fmt: (_, r) => r.c6.Columbia },
    { key: "cal", label: "Calt", num: true, sort: (r) => r.c_other.Caltech, fmt: (_, r) => r.c_other.Caltech, hideSm: true },
    { key: "chi", label: "Chic", num: true, sort: (r) => r.c_other.Chicago, fmt: (_, r) => r.c_other.Chicago, hideSm: true },
    { key: "pen", label: "UPenn", num: true, sort: (r) => r.c_other.UPenn, fmt: (_, r) => r.c_other.UPenn, hideSm: true },
    { key: "brn", label: "Brown", num: true, sort: (r) => r.c_other.Brown, fmt: (_, r) => r.c_other.Brown, hideSm: true },
    { key: "cmu", label: "CMU", num: true, sort: (r) => r.c_other.CMU, fmt: (_, r) => r.c_other.CMU, hideSm: true },
    { key: "cor", label: "Corn", num: true, sort: (r) => r.c_other.Cornell, fmt: (_, r) => r.c_other.Cornell, hideSm: true },
    { key: "ucb", label: "UCB", num: true, sort: (r) => r.c_other.UCB, fmt: (_, r) => r.c_other.UCB },
    { key: "ucla", label: "UCLA", num: true, sort: (r) => r.c_other.UCLA, fmt: (_, r) => r.c_other.UCLA },
    { key: "bl_rate", label: "B+L录取率", num: true, fmt: (v) => pct(v), hideSm: true },
    { key: "uc_yield", label: "UC入学率", num: true, fmt: (v) => pct(v), hideSm: true },
  ], H.validation, {
    sortKey: "actual", asc: false, dense: true,
    onRowClick: (r) => { location.href = `highschool.html?ceeb=${r.ceeb}#profile`; },
    filter: (r) => vFilt === "all" || r.sector === vFilt,
    onCount: (n, all) => ($("#v-count").textContent = `${n} / ${all} 校`),
  });
  $$("#v-tabs button").forEach((b) => (b.onclick = () => {
    vFilt = b.dataset.vf;
    $$("#v-tabs button").forEach((x) => x.classList.toggle("on", x === b));
    VT.rerender();
  }));
  $("#vq").addEventListener("input", (e) => VT.search(e.target.value));

  /* ---------------- Section 02: Asian vs All-Student Comparison ---------------- */
  const asianRows = H.asian50.map((r) => ({ ...r, d_rank: r.rank_all - r.rank }));
  const AT = makeTable($("#asian-table"), [
    { key: "rank", label: "亚裔#", num: true, fmt: rankBadge },
    { key: "name", label: "学校", cls: "name", fmt: (v, r) => `<b>${esc(shortName(v))}</b><small>${esc(r.city)}</small>` },
    { key: "rank_all", label: "全体#", num: true },
    { key: "d_rank", label: "Δ名次 (全体−亚裔)", num: true, fmt: (v) => (v > 0 ? `<span class="up">+${v}</span>` : v < 0 ? `<span class="down">${v}</span>` : "0") },
    { key: "pred", label: "亚裔预测%", num: true, fmt: (v) => `<b>${pct(v)}</b>` },
    { key: "pred_all", label: "全体预测%", num: true, fmt: (v) => pct(v) },
    { key: "asian_share", label: "亚裔占比", num: true, fmt: (v) => pct(v, 0) },
    { key: "asian_bl_app", label: "亚裔B+L录/申", num: true, fmt: (v, r) => `${r.asian_bl_adm}/${v}` },
    { key: "asian_bl_rate_raw", label: "原始录取率", num: true, fmt: (v) => pct(v), hideSm: true },
    { key: "prior_rate", label: "先验 r₀", num: true, fmt: (v) => pct(v), hideSm: true },
    { key: "rate", label: "收缩后 r̂", num: true, fmt: (v) => `<b>${pct(v)}</b>` },
    { key: "asian_yield_raw", label: "原始入学率", num: true, fmt: (v) => pct(v), hideSm: true },
    { key: "prior_yield", label: "先验 y₀", num: true, fmt: (v) => pct(v), hideSm: true },
    { key: "yield", label: "收缩后 ŷ", num: true, fmt: (v) => `<b>${pct(v)}</b>` },
    { key: "z1", label: "z_r / z_y", num: true, fmt: (v, r) => `${sfix(r.z1, 2)}/${sfix(r.z2, 2)}`, hideSm: true },
  ], asianRows, {
    sortKey: "rank", asc: true, dense: true,
    onRowClick: (r) => { location.href = `highschool.html?ceeb=${r.ceeb}#profile`; },
    onCount: (n, all) => ($("#a-count").textContent = `${n} / ${all} 校`),
  });
  $("#aq").addEventListener("input", (e) => AT.search(e.target.value));

  /* ---------------- Section 03: Scatter & Calculator ---------------- */
  const V = H.validation;
  const label = new Set(["The Nueva School", "The Harker School", "San Francisco University High School", "Menlo School", "Saratoga High", "Los Altos High",
    "Henry M. Gunn High", "Lynbrook High", "Los Gatos High", "Leigh High", "Northgate High", "Marin Academy", "Dublin High", "Dougherty Valley High", "Palo Alto High"]);
  scatter($("#scatter"), V.map((v) => ({
    x: v.pred, y: v.actual, color: v.sector === "private" ? "#78358a" : "#0f6b58",
    r: 3.5 + Math.sqrt(v.n) / 9, label: shortName(v.name), showLabel: label.has(v.name),
    html: `<b>${esc(v.name)}</b> (${v.sector === "private" ? "私立" : "公立"} · ${esc(v.period)})<br>实测 <b>${pct(v.actual)}</b> (${v.elite_n}/${int(v.n)}) · 预测 <b>${pct(v.pred)}</b><br>MIT:${v.c6.MIT} Stan:${v.c6.Stanford} Yale:${v.c6.Yale} Harv:${v.c6.Harvard} Prin:${v.c6.Princeton} Colu:${v.c6.Columbia}<br>B+L 录取率 ${pct(v.bl_rate)} · UC 入学率 ${pct(v.uc_yield)}`,
  })), {
    log: true, xmin: 0.004, xmax: 0.28, ymin: 0.004, ymax: 0.28, w: 620, h: 375,
    xticks: [0.005, 0.01, 0.02, 0.05, 0.1, 0.2], yticks: [0.005, 0.01, 0.02, 0.05, 0.1, 0.2],
    xlab: "模型预测比例 p̂", ylab: "实测 6 校比例 (毕业去向表)", diag: true, diagLabel: "p̂ = actual", band: Math.exp(1.28 * P.rmse),
    fmtX: (v) => pct(v, v < 0.01 ? 1 : 0), fmtY: (v) => pct(v, v < 0.01 ? 1 : 0),
  });

  let cm = "all";
  const curP = () => (cm === "asian" ? PA : P);
  const zr = (r, prm) => (logit(r) - prm.m1) / prm.s1;
  const zy = (y, prm) => (logit(y) - prm.m2) / prm.s2;
  const predict = (r, y, prm) => prm.b0 + prm.b1 * zr(r, prm) + prm.b2 * zy(y, prm);
  const bayPub = H.bay.filter((b) => b.sector === "public" && b.bl_rate > 0 && b.uc_yield > 0)
    .map((b) => ({ name: b.name, p: sig(predict(b.bl_rate, b.uc_yield, P)) }));
  const SMAX = 0.1;
  const SX = (p) => 8 + (Math.min(p, SMAX) / SMAX) * 504;
  const stripBase = bayPub.map((b, i) => `<circle cx="${SX(b.p)}" cy="${18 + ((i * 37) % 15) - 7}" r="2.5" fill="var(--accent)" fill-opacity=".22"><title>${esc(b.name)} ${pct(b.p)}</title></circle>`).join("");
  const stripAxis = [0, 0.02, 0.04, 0.06, 0.08, 0.1].map((t) => `<text x="${SX(t)}" y="45" text-anchor="middle">${pct(t, 0)}${t === SMAX ? "+" : ""}</text>`).join("");

  function calc() {
    const prm = curP();
    const sgn = (b) => (b < 0 ? "−" : "+");
    $("#formula-all").innerHTML =
      `logit(p̂) = <b>${fix(prm.b0, 3)}</b> + <b>${fix(prm.b1, 3)}</b>·z<sub>rate</sub> ${sgn(prm.b2)} <b>${fix(Math.abs(prm.b2), 3)}</b>·z<sub>yield</sub> &nbsp;<span class="muted">(μ_r=${fix(prm.m1, 2)}, σ_r=${fix(prm.s1, 2)}, μ_y=${fix(prm.m2, 2)}, σ_y=${fix(prm.s2, 2)})</span>`;
    const ir = $("#in-r"), iy = $("#in-y");
    paintRange(ir); paintRange(iy);
    const r = ir.value / 100, y = iy.value / 100;
    $("#v-r").textContent = pct(r); $("#v-y").textContent = pct(y);
    const L = predict(r, y, prm), p = sig(L), e = 1.28 * prm.rmse;
    $("#out-p").textContent = pct(p);
    $("#out-ci").textContent = `80% CI: ${pct(sig(L - e))} – ${pct(sig(L + e))}`;
    const below = bayPub.filter((b) => b.p < p).length;
    $("#out-rank").textContent = `湾区公立分布分位: P${Math.round((100 * below) / bayPub.length)}`;
    $("#strip").innerHTML = `<svg viewBox="0 0 520 48">${stripBase}
      <line x1="${SX(p)}" x2="${SX(p)}" y1="3" y2="33" stroke="var(--accent)" stroke-width="2" stroke-linecap="round"/>
      <circle cx="${SX(p)}" cy="18" r="5" fill="#fff" stroke="var(--accent)" stroke-width="2"/>${stripAxis}</svg>`;
    $("#calc-detail").innerHTML =
      `x<sub>1</sub> = ${fix(logit(r), 3)}, z<sub>rate</sub> = ${sfix(zr(r, prm), 3)} · x<sub>2</sub> = ${fix(logit(y), 3)}, z<sub>yield</sub> = ${sfix(zy(y, prm), 3)} · logit(p̂) = ${fix(L, 3)} → p̂ = ${pct(p, 2)}`;
  }
  $$("#calc-mode button").forEach((b) => (b.onclick = () => {
    cm = b.dataset.cm;
    $$("#calc-mode button").forEach((x) => x.classList.toggle("on", x === b));
    calc();
  }));
  ["#in-r", "#in-y"].forEach((s) => $(s).addEventListener("input", () => { $$(".pchip").forEach((c) => c.classList.remove("on")); calc(); }));
  const presetNames = ["Saratoga", "Gunn", "Palo Alto", "Los Altos", "Lynbrook", "Mission San Jose", "Monta Vista", "Dougherty Valley", "Dublin", "Lowell"];
  const pool = [...H.top50, ...H.bay.filter((b) => b.sector === "public")];
  presetNames.forEach((n, i) => {
    const s = pool.find((x) => x.name.toLowerCase().includes(n.toLowerCase()));
    if (!s) return;
    const b = document.createElement("button");
    b.className = "pchip"; b.textContent = n; b.title = s.name;
    b.onclick = () => {
      $("#in-r").value = (s.bl_rate * 100).toFixed(1); $("#in-y").value = (s.uc_yield * 100).toFixed(1);
      $$(".pchip").forEach((c) => c.classList.toggle("on", c === b)); calc();
    };
    $("#presets").appendChild(b);
    if (i === 1) b.click();
  });
  calc();

  /* ---------------- Section 04: Parameter Table ---------------- */
  const pRows = [
    ["截距 b₀", fix(P.b0, 4), fix(PA.b0, 4), "岭回归常数项 (logit 尺度)"],
    ["录取率权重 b₁", fix(P.b1, 4), fix(PA.b1, 4), "z(logit B+L 录取率) 回归系数"],
    ["入学率权重 b₂", fix(P.b2, 4), fix(PA.b2, 4), "z(logit UC 入学率) 回归系数"],
    ["录取率均值 μ₁", fix(P.m1, 4), fix(PA.m1, 4), "logit(B+L 录取率) 标准化均值"],
    ["录取率标准差 σ₁", fix(P.s1, 4), fix(PA.s1, 4), "logit(B+L 录取率) 标准化标准差"],
    ["入学率均值 μ₂", fix(P.m2, 4), fix(PA.m2, 4), "logit(UC 入学率) 标准化均值"],
    ["入学率标准差 σ₂", fix(P.s2, 4), fix(PA.s2, 4), "logit(UC 入学率) 标准化标准差"],
    ["Beta 收缩伪计数 K", "—", `${int(PA.kr)} / ${int(PA.ky)}`, "亚裔录取率 / 入学率向全校先验收缩样本量"],
    ["先验回归 (a₀, a₁) 录取率", "—", `${fix(PA.pr_a, 3)}, ${fix(PA.pr_b, 3)}`, "logit(r₀) = a₀ + a₁·logit(r_all)"],
    ["先验回归 (a₀, a₁) 入学率", "—", `${fix(PA.py_a, 3)}, ${fix(PA.py_b, 3)}`, "logit(y₀) = a₀ + a₁·logit(y_all)"],
    ["L2 正则惩罚 λ", "3.0", "3.0", "岭回归惩罚项 λ(b₁² + b₂²)"],
    ["留一法误差 RMSE_LOO", fix(P.rmse, 4), fix(PA.rmse, 4), "留一法交叉验证均方根误差 (logit)"],
    ["留一法秩相关 ρ_LOO", fix(P.rho, 4), fix(PA.rho, 4), "留一法预测值与实测值 Spearman 秩相关"],
    ["校准样本 / 候选池规模", `27 / 1,460`, `${int(PA.n)} / ${int(PA.nrank)}`, "校准学校数 / 湾区入围公校数"],
  ];
  $("#param-table").innerHTML = `<thead><tr><th>参数名称</th><th class="num">全体口径</th><th class="num">亚裔口径</th><th>说明</th></tr></thead><tbody>` +
    pRows.map(([k, v1, v2, d]) => `<tr><td><b>${k}</b></td><td class="num">${v1}</td><td class="num">${v2}</td><td class="muted">${d}</td></tr>`).join("") +
    `</tbody>`;
})();
