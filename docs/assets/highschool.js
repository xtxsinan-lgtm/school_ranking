(async function () {
  const H = await loadJSON("data/highschool.json");
  const valByCeeb = Object.fromEntries(H.validation.map((v) => [v.ceeb, v]));
  const topByCeeb = Object.fromEntries(H.top50.map((r) => [r.ceeb, r]));
  const asianByCeeb = Object.fromEntries(H.asian50.map((r) => [r.ceeb, r]));
  const bayByCeeb = Object.fromEntries(H.bay.map((r) => [r.ceeb, r]));
  const eliteSet = new Set(H.elite6 || ["MIT", "Stanford", "Yale", "Harvard", "Princeton", "Columbia"]);
  const shortName = (s) => s.replace(/^The /, "").replace(/^Henry M\.? /, "")
    .replace(/San Francisco University High School/, "SF University")
    .replace(/Crystal Springs Uplands School/, "Crystal Springs")
    .replace(/Bellarmine College Preparatory/, "Bellarmine")
    .replace(/Urban School of San Francisco/, "Urban School")
    .replace(/International High School.*/, "SF International")
    .replace(/St\. Francis High School.*/, "St. Francis")
    .replace(/ Senior High School$| High School$| Senior High Schl$| High$| School$/, "");

  /* ---------------- Section 01: Clean Ranking Tables ---------------- */
  const maxAll = Math.max(...H.top50.map((r) => Math.max(r.hi, r.actual || 0)));
  const maxAs = Math.max(...H.asian50.map((r) => Math.max(r.hi, r.actual || 0)));
  const nameCell = (v, r) => `<b>${esc(shortName(v))}</b><small>${esc(r.city)} · ${esc(r.county)}</small>`;
  const rangeCell = (max) => (v, r) => `<div class="rcell">${rangeBar(r.lo, r.hi, r.pred, max, r.actual)}<small>${pct(r.lo)}–${pct(r.hi)}</small></div>`;
  const truthCell = (v, r) => (v == null ? `<span class="muted">—</span>` : `<span class="truth">${pct(v)}</span> <small>(${int(r.actual_n)})</small>`);
  const gpaCell = (v) => (v == null ? `<span class="muted">—</span>` : fix(v, 2));

  const tables = {
    all: {
      data: H.top50, sortKey: "rank",
      cols: [
        { key: "rank", label: "#", num: true, fmt: rankBadge },
        { key: "name", label: "学校", cls: "name", fmt: nameCell },
        { key: "pred", label: "预测顶尖比例", num: true, fmt: (v) => `<b>${pct(v)}</b>` },
        { key: "lo", label: "80% 预测区间", fmt: rangeCell(maxAll), sort: (r) => r.pred, hideSm: true },
        { key: "actual", label: "实测比例 (人数)", num: true, fmt: truthCell },
        { key: "bl_rate", label: "B+L 合并录取率", num: true, fmt: (v, r) => `${pct(v)} <small>(${r.bl_adm}/${r.bl_app})</small>` },
        { key: "ucb_rate", label: "UCB 录取率", num: true, fmt: (v, r) => `${pct(v)} <small>(${r.ucb_adm}/${r.ucb_app})</small>`, hideSm: true },
        { key: "ucla_rate", label: "UCLA 录取率", num: true, fmt: (v, r) => `${pct(v)} <small>(${r.ucla_adm}/${r.ucla_app})</small>`, hideSm: true },
        { key: "uc_yield", label: "UC 入学率", num: true, fmt: (v, r) => `${pct(v)} <small>(${r.uc_enr}/${r.uc_adm})</small>` },
        { key: "gpa_adm", label: "UC 录取 GPA", num: true, fmt: gpaCell, hideSm: true },
        { key: "state_rank", label: "全州#", num: true, hideSm: true },
      ],
    },
    asian: {
      data: H.asian50, sortKey: "rank",
      cols: [
        { key: "rank", label: "#", num: true, fmt: rankBadge },
        { key: "name", label: "学校", cls: "name", fmt: nameCell },
        { key: "pred", label: "亚裔口径预测", num: true, fmt: (v) => `<b>${pct(v)}</b>` },
        { key: "lo", label: "80% 预测区间", fmt: rangeCell(maxAs), sort: (r) => r.pred, hideSm: true },
        { key: "actual", label: "实测比例 (全体)", num: true, fmt: truthCell },
        { key: "asian_share", label: "亚裔占比", num: true, fmt: (v) => pct(v, 0) },
        { key: "rate", label: "亚裔 B+L 录取率", num: true, fmt: (v, r) => `${pct(v)} <small>(${r.asian_bl_adm}/${r.asian_bl_app})</small>` },
        { key: "yield", label: "亚裔 UC 入学率", num: true, fmt: (v, r) => `${pct(v)} <small>(${r.asian_uc_enr}/${r.asian_uc_adm})</small>`, hideSm: true },
        { key: "rank_all", label: "全体# (变化)", num: true, fmt: (v, r) => { const d = v - r.rank; return `${v} ${d > 0 ? `<span class="up">↑${d}</span>` : d < 0 ? `<span class="down">↓${-d}</span>` : ""}`; } },
        { key: "gpa_adm", label: "UC 录取 GPA", num: true, fmt: (v) => fix(v, 2), hideSm: true },
      ],
    },
    bay: {
      data: H.bay, sortKey: "state_rank",
      cols: [
        { key: "state_rank", label: "全州#", num: true, fmt: rankBadge },
        { key: "name", label: "学校", cls: "name", fmt: nameCell },
        { key: "sector", label: "类型", fmt: (v) => (v === "private" ? `<span class="tag pri">私立</span>` : `<span class="tag pub">公立</span>`) },
        { key: "score", label: "UC 原始分", num: true, fmt: (v) => `<b>${fix(v, 2)}</b>` },
        { key: "rank_lo", label: "90% 全州区间", num: true, fmt: (v, r) => `${r.rank_lo}–${r.rank_hi}`, hideSm: true },
        { key: "pred", label: "回归预测%", num: true, fmt: (v) => pct(v) },
        { key: "actual", label: "实测比例 (人数)", num: true, fmt: truthCell },
        { key: "bl_rate", label: "B+L 录取率", num: true, fmt: (v, r) => `${pct(v)} <small>(${r.bl_adm}/${r.bl_app})</small>` },
        { key: "ucb_rate", label: "UCB 录取率", num: true, fmt: (v, r) => `${pct(v)} <small>(${r.ucb_adm}/${r.ucb_app})</small>`, hideSm: true },
        { key: "ucla_rate", label: "UCLA 录取率", num: true, fmt: (v, r) => `${pct(v)} <small>(${r.ucla_adm}/${r.ucla_app})</small>`, hideSm: true },
        { key: "uc_yield", label: "UC 入学率", num: true, fmt: (v, r) => `${pct(v)} <small>(${r.uc_enr}/${r.uc_adm})</small>`, hideSm: true },
        { key: "gpa_adm", label: "UC 录取 GPA", num: true, fmt: gpaCell, hideSm: true },
      ],
    },
  };

  /* ---------------- Section 02: Single-School Profile Lookup ---------------- */
  const campNames = H.campuses || ["UCB", "UCLA", "UCSD", "UCD", "UCI", "UCSB", "UCSC", "UCR", "UCM", "All"];
  const campLabels = { All: "UC 全系统" };
  const allBaySorted = H.bay.slice().sort((a, b) => a.state_rank - b.state_rank);
  $("#hs-sel").innerHTML = allBaySorted.map((r) =>
    `<option value="${r.ceeb}">全州#${r.state_rank} · ${esc(r.name)} (${esc(r.city)}, ${r.sector === "private" ? "私立" : "公立"})</option>`
  ).join("");

  let T, curCeeb = Number(new URLSearchParams(location.search).get("ceeb")) || 52347;
  if (!bayByCeeb[curCeeb]) curCeeb = 52347;

  function inspectSchool(ceeb) {
    curCeeb = Number(ceeb);
    $("#hs-sel").value = String(curCeeb);
    if (T) T.setActive(curCeeb);
    $$("#hs-quick .pchip").forEach((c) => c.classList.toggle("on", Number(c.dataset.ceeb) === curCeeb));

    const r = topByCeeb[curCeeb] || bayByCeeb[curCeeb] || asianByCeeb[curCeeb];
    if (!r) return;
    const tAll = topByCeeb[curCeeb];
    const tAs = asianByCeeb[curCeeb];
    const tBay = bayByCeeb[curCeeb];
    const det = H.uc_detail && H.uc_detail[String(curCeeb)];
    const val = valByCeeb[curCeeb];
    const gpa = (det && det.gpa) || [r.gpa_app, r.gpa_adm, r.gpa_enr];

    let html = `<div style="padding-top:8px;border-top:1px solid var(--line-2)">
      <div class="inspector-head" style="margin-bottom:10px">
        <div>
          <h3 style="font-size:1.05rem;margin:0">${esc(r.name)} <span class="tag ${tBay && tBay.sector === "private" ? "pri" : "pub"}" style="vertical-align:1px">${tBay && tBay.sector === "private" ? "私立高中" : "公立高中"}</span></h3>
          <div class="muted" style="font-size:.78rem;margin-top:2px">${esc(r.city)} · ${esc(r.county)} · CEEB 代码 ${curCeeb}</div>
        </div>
        <div class="mono" style="font-size:.78rem;display:flex;gap:14px;flex-wrap:wrap">
          <span>全体口径: <b>${tAll ? `#${tAll.rank} (${pct(tAll.pred)})` : pct(r.pred)}</b></span>
          ${tAs ? `<span>亚裔口径: <b>#${tAs.rank} (${pct(tAs.pred)})</b></span>` : ""}
          ${tBay ? `<span>全州原始分: <b>#${tBay.state_rank} (${fix(tBay.score, 2)})</b></span>` : ""}
          <span>UC GPA (申/录/入): <b>${fix(gpa[0], 2)} / ${fix(gpa[1], 2)} / ${fix(gpa[2], 2)}</b></span>
        </div>
      </div>`;

    if (det && det.c) {
      const C = det.c;
      html += `<div class="inspector-grid"><div>
        <div style="font-size:.78rem;font-weight:600;margin-bottom:5px">UC 9 校区申请 · 录取 · 入学明细（2021–2025 五届合计）</div>
        <table class="camp">
          <thead><tr><th>指标 \\ 校区</th>${campNames.map((k) => `<th>${campLabels[k] || k}</th>`).join("")}</tr></thead>
          <tbody>
            <tr><td>申请人数 (App)</td>${C.map((x) => `<td>${int(x[0])}</td>`).join("")}</tr>
            <tr><td>录取人数 (Adm)</td>${C.map((x) => `<td>${int(x[1])}</td>`).join("")}</tr>
            <tr><td>入学人数 (Enr)</td>${C.map((x) => `<td>${int(x[2])}</td>`).join("")}</tr>
            <tr><td>录取率 (Adm/App)</td>${C.map((x) => `<td>${x[0] ? pct(x[1] / x[0], 1) : "—"}</td>`).join("")}</tr>
            <tr><td>入学率 (Enr/Adm)</td>${C.map((x) => `<td>${x[1] ? pct(x[2] / x[1], 1) : "—"}</td>`).join("")}</tr>
          </tbody>
        </table>
      </div><div>`;
      if (val) {
        html += `<div style="font-size:.78rem"><b>实测毕业去向 (${esc(val.period)} · ${val.src === "official" ? "官方 School Profile" : "公开汇总表"} · 样本 N = ${int(val.n)})</b> · 6 所顶尖校合计 <b class="truth">${val.elite_n} 人 (${pct(val.actual)})</b></div>`;
        html += `<div class="dest-pills">` +
          H.elite6.map((k) => `<span class="dest-pill el">${k}: ${val.c6[k] || 0}</span>`).join("") +
          `</div>`;
        html += `<div class="muted" style="font-size:.73rem;margin-top:8px">实测录取人数前 12 名大学：</div><div class="dest-pills">` +
          val.top_dest.map(([k, cnt]) => `<span class="dest-pill${eliteSet.has(k) ? " el" : ""}">${esc(k)}: <b>${int(cnt)}</b></span>`).join("") +
          `</div>`;
      } else {
        html += `<div style="font-size:.78rem;font-weight:600">该校升学指标摘要</div>
          <div class="mono muted" style="font-size:.76rem;margin-top:5px;line-height:1.7">
            UCB + UCLA 合并录取：${int(r.bl_adm)} / ${int(r.bl_app)} (${pct(r.bl_rate)})<br>
            UC 全系统入学率：${int(r.uc_enr)} / ${int(r.uc_adm)} (${pct(r.uc_yield)})<br>
            模型预测进入 6 所目标名校比例：<b>${pct(r.pred)}</b>${r.lo != null ? ` (80% 区间: ${pct(r.lo)}–${pct(r.hi)})` : ""}<br>
            （注：该校未在 27 所实测毕业去向校准集中，完整 27 校去向矩阵见 <a href="highschool-analysis.html">高中数据分析</a>）
          </div>`;
      }
      html += `</div></div>`;
    }
    html += `</div>`;
    $("#hs-inspect").innerHTML = html;
  }

  [
    ["Gunn", 52347], ["Palo Alto", 52350], ["Saratoga", 53343], ["Lynbrook", 53463],
    ["Mission San Jose", 50990], ["Monta Vista", 50718], ["Lowell", 52965], ["Nueva (私)", 51213], ["Harker (私)", 53172]
  ].forEach(([label, ceeb]) => {
    if (!bayByCeeb[ceeb]) return;
    const b = document.createElement("button");
    b.className = "pchip"; b.dataset.ceeb = ceeb; b.textContent = label;
    b.onclick = () => inspectSchool(ceeb);
    $("#hs-quick").appendChild(b);
  });
  $("#hs-sel").onchange = (e) => inspectSchool(e.target.value);

  function show(t) {
    const c = tables[t];
    T = makeTable($("#table"), c.cols, c.data, {
      sortKey: c.sortKey, asc: true, dense: true,
      rowId: (r) => r.ceeb, activeId: curCeeb,
      onRowClick: (r) => {
        inspectSchool(r.ceeb);
        $("#profile").scrollIntoView({ behavior: "smooth" });
      },
      onCount: (n, all) => ($("#count").textContent = n === all ? `${all} 校` : `${n} / ${all} 校`),
    });
    T.search($("#q").value);
    $$("#tabs button").forEach((b) => b.classList.toggle("on", b.dataset.t === t));
  }
  $$("#tabs button").forEach((b) => (b.onclick = () => show(b.dataset.t)));
  $("#q").addEventListener("input", (ev) => T.search(ev.target.value));
  show("all");
  inspectSchool(curCeeb);
})();
