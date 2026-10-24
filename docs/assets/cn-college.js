(async function () {
  const CN = await loadJSON("data/cn_college.json");
  const PROVS = CN.provs_std;
  const stdBySchool = Object.fromEntries(CN.std100.map((r) => [r.school, r]));

  /* City bias lookup: prov + "|" + city -> bias */
  const biasMap = new Map();
  const provBiasRow = new Map();
  CN.city_bias.matrix.forEach((row) => {
    provBiasRow.set(row.province, row.vals);
    CN.cities.forEach((c, idx) => {
      if (row.vals[idx] != null) biasMap.set(row.province + "|" + c, row.vals[idx]);
    });
  });

  /* Within-province rank lookup across the 102 schools */
  const provRanks = {};
  PROVS.forEach((p, pi) => {
    const scored = CN.std100
      .filter((r) => r.scores[pi] != null)
      .slice()
      .sort((a, b) => b.scores[pi] - a.scores[pi]);
    const rmap = {};
    scored.forEach((r, idx) => {
      if (idx > 0 && scored[idx - 1].scores[pi] === r.scores[pi]) {
        rmap[r.school] = rmap[scored[idx - 1].school];
      } else {
        rmap[r.school] = idx + 1;
      }
    });
    provRanks[p] = rmap;
  });

  const tierNames = {
    1: "一档 ≥665",
    2: "二档 645–665",
    3: "三档 625–645",
    4: "四档 605–625",
    5: "五档 585–605",
    6: "六档 <585",
  };
  const tierBadge = (t) => `<span class="tag tier${t}">${tierNames[t] || t}</span>`;

  const modeNotes = {
    std100: "2011年23省平行志愿理科一批最低分等方差标准化 + 各省录取人数加权均值（北大医学部、上交医学院单列不占名次）",
    top30: "回答开篇展示的全国高校排名前30名简表（对应2011年23省标准化主榜前30所独立高校）",
    sci12: "2012年河南、广东、山东、四川、安徽5个招生大省理科录取平均分均值 Top 50",
    arts12: "2012年河南、广东、山东、四川、安徽5个招生大省文科录取平均分均值 Top 50（部分理工高校在个别省份无文科计划）",
    p07_4: "2006–2007年江苏、河北、湖北、广东4省两年理科录取平均分 Top 50（广东06标准分按 √x × 22.5 换算）",
    p07_3: "2006–2007年山东、江苏、广东3省两年理科录取平均分 Top 50（广东06采用900分制原始标准分，并列记为 n+0.5 名）",
  };

  /* ---------------- Section 01: Multi-Period Main Ranking Table ---------------- */
  const qs = new URLSearchParams(location.search);
  let curMode = qs.get("mode") || "std100";
  let curTier = 0;
  let curSchool = qs.get("school") || "清华大学";
  if (!stdBySchool[curSchool]) curSchool = "清华大学";
  let T;

  function selectSchool(name, scroll = false) {
    const match = stdBySchool[name] || CN.std100.find((r) => r.school.includes(name) || name.includes(r.school));
    if (!match) return;
    curSchool = match.school;
    $("#sel-school").value = curSchool;
    renderProfile(match);
    if (T && curMode === "std100") T.setActive(curSchool);
    if (scroll) $("#profile").scrollIntoView({ behavior: "smooth" });
  }

  function renderMainTable(mode) {
    curMode = mode;
    $$("#rtabs button").forEach((b) => b.classList.toggle("on", b.dataset.m === mode));
    $("#tier-bar").style.display = mode === "std100" ? "flex" : "none";
    $("#mode-note").textContent = modeNotes[mode] || "";

    let cols, data, rowId;
    if (mode === "std100") {
      data = CN.std100;
      rowId = (r) => r.school;
      cols = [
        { key: "order", label: "#", num: true, fmt: (v, r) => (r.num_rank ? rankBadge(r.num_rank) : `<span class="mono muted" data-tip="医学院/医学部单列，不占独立学校名次">—</span>`) },
        { key: "school", label: "学校", cls: "name", fmt: (v, r) => `<b>${esc(v)}</b><small>${esc(r.city)}</small>` },
        { key: "tier", label: "分档", fmt: tierBadge },
        { key: "weighted_mean", label: "23省加权均值", num: true, fmt: (v) => `<b>${fix(v, 1)}</b>` },
        { key: "mean", label: "简单均值", num: true },
        { key: "n_provs", label: "招生省数", num: true, fmt: (v) => `${v}/23`, hideSm: true },
        { key: "max_score", label: "最高青睐省", num: true, fmt: (v, r) => `${esc(r.max_prov)} <b>${v}</b> <small class="up">(${sfix(v - r.weighted_mean, 1)})</small>`, hideSm: true },
        { key: "min_score", label: "最低低估省", num: true, fmt: (v, r) => `${esc(r.min_prov)} <b>${v}</b> <small class="down">(${sfix(v - r.weighted_mean, 1)})</small>`, hideSm: true },
        { key: "sci12_avg", label: "2012理科均分", num: true, fmt: (v, r) => (v ? `${fix(v, 1)} <small>#${r.sci12_rank}</small>` : `<span class="muted">—</span>`), hideSm: true },
        { key: "arts12_avg", label: "2012文科均分", num: true, fmt: (v, r) => (v ? `${fix(v, 1)} <small>#${r.arts12_rank}</small>` : `<span class="muted">—</span>`), hideSm: true },
        { key: "p07_4_avg", label: "06-07四省均分", num: true, fmt: (v, r) => (v ? `${fix(v, 1)} <small>#${r.p07_4_rank}</small>` : `<span class="muted">—</span>`), hideSm: true },
      ];
    } else if (mode === "top30") {
      data = CN.top30;
      rowId = (r) => r.school;
      cols = [
        { key: "rank", label: "排名", num: true, fmt: rankBadge },
        { key: "school", label: "学校", cls: "name", fmt: (v, r) => `<b>${esc(v)}</b><small>${esc(r.city)}</small>` },
        { key: "tier", label: "2011分档", fmt: tierBadge },
        { key: "weighted_mean", label: "2011加权均值 (23省)", num: true, fmt: (v) => `<b>${fix(v, 1)}</b>` },
        { key: "mean", label: "2011简单均值", num: true },
        { key: "sci12_avg", label: "2012理科均分 (5省)", num: true, fmt: (v, r) => (v ? `${fix(v, 1)} <small>(#${r.sci12_rank})</small>` : `<span class="muted">—</span>`) },
        { key: "arts12_avg", label: "2012文科均分 (5省)", num: true, fmt: (v, r) => (v ? `${fix(v, 1)} <small>(#${r.arts12_rank})</small>` : `<span class="muted">—</span>`), hideSm: true },
        { key: "p07_4_avg", label: "06-07四省均分", num: true, fmt: (v, r) => (v ? `${fix(v, 1)} <small>(#${r.p07_4_rank})</small>` : `<span class="muted">—</span>`), hideSm: true },
      ];
    } else if (mode === "sci12") {
      data = CN.sci12;
      rowId = (r) => r.school;
      cols = [
        { key: "order", label: "排名", num: true, fmt: (v, r) => (r.num_rank ? rankBadge(r.num_rank) : `<span class="mono muted">—</span>`) },
        { key: "school", label: "学校", cls: "name", fmt: (v, r) => `<b>${esc(v)}</b><small>${esc(r.city)}</small>` },
        { key: "avg_score", label: "五省平均分", num: true, fmt: (v) => `<b>${fix(v, 2)}</b>` },
        { key: "河南", label: "河南", num: true },
        { key: "广东", label: "广东", num: true },
        { key: "山东", label: "山东", num: true },
        { key: "四川", label: "四川", num: true },
        { key: "安徽", label: "安徽", num: true },
        { key: "std11_wm", label: "2011标准化分", num: true, fmt: (v, r) => (v ? `${fix(v, 1)} <small>(#${r.std11_rank})</small>` : `<span class="muted">—</span>`), hideSm: true },
        { key: "p07_4_avg", label: "06-07四省均分", num: true, fmt: (v, r) => (v ? `${fix(v, 1)} <small>(#${r.p07_4_rank})</small>` : `<span class="muted">—</span>`), hideSm: true },
      ];
    } else if (mode === "arts12") {
      data = CN.arts12;
      rowId = (r) => r.school;
      cols = [
        { key: "rank", label: "排名", num: true, fmt: rankBadge },
        { key: "school", label: "学校", cls: "name", fmt: (v, r) => `<b>${esc(v)}</b><small>${esc(r.city)}</small>` },
        { key: "avg_score", label: "五省平均分", num: true, fmt: (v) => `<b>${fix(v, 2)}</b>` },
        { key: "河南", label: "河南", num: true, fmt: (v) => v ?? `<span class="muted">—</span>` },
        { key: "广东", label: "广东", num: true, fmt: (v) => v ?? `<span class="muted">—</span>` },
        { key: "山东", label: "山东", num: true, fmt: (v) => v ?? `<span class="muted">—</span>` },
        { key: "四川", label: "四川", num: true, fmt: (v) => v ?? `<span class="muted">—</span>` },
        { key: "安徽", label: "安徽", num: true, fmt: (v) => v ?? `<span class="muted">—</span>` },
        { key: "n_provs", label: "有效省数", num: true, fmt: (v) => `${v}/5`, hideSm: true },
        { key: "sci12_avg", label: "同年理科均分", num: true, fmt: (v, r) => (v ? `${fix(v, 1)} <small>(#${r.sci12_rank})</small>` : `<span class="muted">—</span>`), hideSm: true },
      ];
    } else if (mode === "p07_4") {
      data = CN.p07_4;
      rowId = (r) => r.school;
      cols = [
        { key: "rank", label: "#", num: true, fmt: rankBadge },
        { key: "school", label: "大学", cls: "name", fmt: (v, r) => `<b>${esc(v)}</b><small>${esc(r.city)}</small>` },
        { key: "avg_score", label: "平均分", num: true, fmt: (v) => `<b>${fix(v, 1)}</b>` },
        { key: "avg_rank", label: "总排名(均值)", num: true, fmt: (v) => fix(v, 2) },
        { key: "江苏07", label: "江苏07", num: true },
        { key: "江苏06", label: "江苏06", num: true, hideSm: true },
        { key: "河北07", label: "河北07", num: true },
        { key: "河北06", label: "河北06", num: true, hideSm: true },
        { key: "湖北07", label: "湖北07", num: true },
        { key: "湖北06", label: "湖北06", num: true, hideSm: true },
        { key: "广东07", label: "广东07", num: true },
        { key: "广东06", label: "广东06(换算)", num: true, hideSm: true },
      ];
    } else {
      data = CN.p07_3;
      rowId = (r) => r.school;
      cols = [
        { key: "rank", label: "#", num: true, fmt: rankBadge },
        { key: "school", label: "学校(原表简称)", cls: "name", fmt: (v, r) => `<b>${esc(v)}</b><small>${esc(r.full_school)} · ${esc(r.city)}</small>` },
        { key: "avg_score", label: "平均分", num: true, fmt: (v) => `<b>${fix(v, 1)}</b>` },
        { key: "avg_rank", label: "省内平均排名", num: true, fmt: (v) => fix(v, 2) },
        { key: "山东07", label: "山东07", num: true, fmt: (v) => v ?? `<span class="muted">—</span>` },
        { key: "山东06", label: "山东06", num: true, fmt: (v) => v ?? `<span class="muted">—</span>` },
        { key: "江苏07", label: "江苏07", num: true, fmt: (v) => v ?? `<span class="muted">—</span>` },
        { key: "江苏06", label: "江苏06", num: true, fmt: (v) => v ?? `<span class="muted">—</span>` },
        { key: "广东07", label: "广东07", num: true, fmt: (v) => v ?? `<span class="muted">—</span>` },
        { key: "广东06", label: "广东06(标准分)", num: true, fmt: (v) => v ?? `<span class="muted">—</span>` },
      ];
    }

    T = makeTable($("#table"), cols, data, {
      sortKey: cols[0].key,
      asc: true,
      dense: true,
      rowId,
      activeId: curSchool,
      filter: (r) => mode !== "std100" || curTier === 0 || r.tier === curTier,
      onRowClick: (r) => selectSchool(r.full_school || r.norm_school || r.school, true),
      onCount: (n, all) => ($("#count").textContent = n === all ? `共 ${all} 校` : `${n} / ${all} 校`),
    });
    T.search($("#q").value);
  }

  $$("#rtabs button").forEach((b) => (b.onclick = () => renderMainTable(b.dataset.m)));
  $$("#ttabs button").forEach((b) => (b.onclick = () => {
    curTier = Number(b.dataset.t);
    $$("#ttabs button").forEach((x) => x.classList.toggle("on", x === b));
    if (T) T.rerender();
  }));
  $("#q").addEventListener("input", (e) => T && T.search(e.target.value));

  /* ---------------- Section 02: Single-School 23-Province Profile ---------------- */
  $("#sel-school").innerHTML = CN.std100
    .map((r) => `<option value="${esc(r.school)}">${r.num_rank ? "#" + r.num_rank : "[单列]"} ${esc(r.school)} (${esc(r.city)} · 加权均值 ${fix(r.weighted_mean, 1)})</option>`)
    .join("");

  ["清华大学", "北京大学", "复旦大学", "上海交通大学", "浙江大学", "中国科学技术大学", "南京大学", "上海交通大学医学院", "中山大学", "厦门大学", "哈尔滨工业大学", "山东大学"].forEach((s) => {
    if (!stdBySchool[s]) return;
    const b = document.createElement("button");
    b.className = "pchip";
    b.textContent = s.replace(/大学$/, "").replace(/^中国科学技术$/, "中科大").replace(/^哈尔滨工业$/, "哈工大");
    b.dataset.s = s;
    b.onclick = () => selectSchool(s, false);
    $("#school-presets").appendChild(b);
  });

  let provT;
  function renderProfile(r) {
    $$("#school-presets .pchip").forEach((b) => b.classList.toggle("on", b.dataset.s === r.school));
    $("#school-summary").innerHTML = `
      <div class="kpis" style="margin-top:4px;padding-top:10px">
        <div class="kpi"><div class="n">${r.num_rank ? "#" + r.num_rank : "单列"}<span>${esc(r.city)} · ${tierNames[r.tier]}</span></div><div class="l">2011 标准化加权均值 <b>${fix(r.weighted_mean, 1)}</b> · 简单均值 <b>${r.mean}</b>（覆盖 ${r.n_provs}/23 省）</div></div>
        <div class="kpi"><div class="n">${r.sci12_avg ? fix(r.sci12_avg, 1) : "—"}<span>${r.sci12_rank ? "2012理科 #" + r.sci12_rank : "未入2012理科前50"}</span></div><div class="l">2012 五省（豫粤鲁川皖）理科录取平均分</div></div>
        <div class="kpi"><div class="n">${r.arts12_avg ? fix(r.arts12_avg, 1) : "—"}<span>${r.arts12_rank ? "2012文科 #" + r.arts12_rank : "未入2012文科前50"}</span></div><div class="l">2012 五省（豫粤鲁川皖）文科录取平均分</div></div>
        <div class="kpi"><div class="n">${r.p07_4_avg ? fix(r.p07_4_avg, 1) : "—"}<span>${r.p07_4_rank ? "06-07四省 #" + r.p07_4_rank : "未入06-07前50"}</span></div><div class="l">2006–2007 苏冀鄂粤四省两年理科均分</div></div>
      </div>`;

    const rows = PROVS.map((p, i) => {
      const stdScore = r.scores[i];
      const rawScore = r.raw_scores ? r.raw_scores[i] : null;
      const diff = stdScore != null ? +(stdScore - r.weighted_mean).toFixed(1) : null;
      const prk = stdScore != null ? provRanks[p][r.school] : null;
      const cBias = biasMap.get(p + "|" + r.city);
      return {
        prov: p,
        std: stdScore,
        diff,
        prk,
        raw: rawScore,
        cBias: cBias ?? null,
      };
    });

    $("#prov-title").innerHTML = `${esc(r.school)} (${esc(r.city)}) 在 23 个省区的录取分数与偏好偏差明细`;
    provT = makeTable($("#prov-table"), [
      { key: "prov", label: "生源省份", cls: "name", fmt: (v) => `<b>${esc(v)}</b>` },
      { key: "std", label: "2011 标准化分数", num: true, fmt: (v) => (v != null ? `<b>${v}</b>` : `<span class="muted">未招生/空缺</span>`) },
      { key: "diff", label: "相对全国加权均值 (省分−全国)", num: true, fmt: (v) => (v == null ? `<span class="muted">—</span>` : `<b class="${v > 0 ? "up" : v < 0 ? "down" : ""}">${sfix(v, 1)}</b>`) },
      { key: "prk", label: "在本省百强内名次", num: true, fmt: (v) => (v != null ? `#${v}` : `<span class="muted">—</span>`) },
      { key: "raw", label: "2010 原始录取最低分", num: true, fmt: (v) => (v != null ? v : `<span class="muted">—</span>`), hideSm: true },
      { key: "cBias", label: `该省对「${esc(r.city)}」高校总体偏好`, num: true, fmt: (v) => (v == null ? `<span class="muted">—</span>` : `<span class="${v > 0 ? "up" : v < 0 ? "down" : ""}">${sfix(v, 1)}</span>`), hideSm: true },
    ], rows, {
      sortKey: "diff",
      asc: true,
      dense: true,
      onRowClick: (row) => {
        $("#sel-prov").value = row.prov;
        renderBargain(row.prov);
        $("#bargain").scrollIntoView({ behavior: "smooth" });
      },
      onCount: (n, all) => ($("#prov-count").textContent = `有效招生 ${rows.filter((x) => x.std != null).length} / ${all} 省`),
    });
    provT.search($("#pq").value);
  }

  $("#sel-school").onchange = (e) => selectSchool(e.target.value, false);
  $("#pq").addEventListener("input", (e) => provT && provT.search(e.target.value));

  /* ---------------- Section 03: Province Bargain / Cost-Performance Finder ---------------- */
  $("#sel-prov").innerHTML = PROVS.map((p) => `<option value="${esc(p)}">${esc(p)}</option>`).join("");
  let curProv = qs.get("prov") || "山东";
  if (!PROVS.includes(curProv)) curProv = "山东";
  let bgTier = "all";
  let bgT;

  PROVS.forEach((p) => {
    const b = document.createElement("button");
    b.className = "pchip";
    b.textContent = p;
    b.dataset.p = p;
    b.onclick = () => {
      $("#sel-prov").value = p;
      renderBargain(p);
    };
    $("#prov-presets").appendChild(b);
  });

  function renderBargain(prov) {
    curProv = prov;
    const pi = PROVS.indexOf(prov);
    $$("#prov-presets .pchip").forEach((b) => b.classList.toggle("on", b.dataset.p === prov));

    const cvals = provBiasRow.get(prov) || [];
    const cityPairs = CN.cities
      .map((c, idx) => [c, cvals[idx]])
      .filter((x) => x[1] != null)
      .sort((a, b) => b[1] - a[1]);
    const liked = cityPairs.slice(0, 4).map(([c, v]) => `${c}(<b class="up">${sfix(v, 1)}</b>)`).join("、");
    const disliked = cityPairs.slice(-4).reverse().map(([c, v]) => `${c}(<b class="down">${sfix(v, 1)}</b>)`).join("、");
    $("#prov-city-summary").innerHTML = `<b>${esc(prov)}考生地域偏好特征（来自 23×29 城市吸引力矩阵）：</b>最偏爱城市：${liked} · 相对低估（高性价比）城市：${disliked}`;

    const rows = CN.std100
      .filter((r) => r.scores[pi] != null)
      .map((r) => {
        const s = r.scores[pi];
        const raw = r.raw_scores ? r.raw_scores[pi] : null;
        const diff = +(s - r.weighted_mean).toFixed(1);
        const prk = provRanks[prov][r.school];
        const rkDiff = r.num_rank != null && prk != null ? prk - r.num_rank : null;
        return {
          order: r.order,
          num_rank: r.num_rank,
          school: r.school,
          city: r.city,
          tier: r.tier,
          wm: r.weighted_mean,
          prov_score: s,
          diff,
          prov_rank: prk,
          rk_diff: rkDiff,
          raw,
          city_bias: biasMap.get(prov + "|" + r.city) ?? null,
        };
      });

    $("#bg-title").innerHTML = `${esc(prov)}考生报考各高校「性价比（被低估程度）」排行`;
    bgT = makeTable($("#bg-table"), [
      { key: "order", label: "全国#", num: true, fmt: (v, r) => (r.num_rank ? rankBadge(r.num_rank) : `<span class="mono muted">单列</span>`) },
      { key: "school", label: "学校", cls: "name", fmt: (v, r) => `<b>${esc(v)}</b><small>${esc(r.city)}</small>` },
      { key: "tier", label: "全国分档", fmt: tierBadge, hideSm: true },
      { key: "wm", label: "全国加权均值", num: true, fmt: (v) => fix(v, 1) },
      { key: "prov_score", label: `${esc(prov)}标准化分`, num: true, fmt: (v) => `<b>${v}</b>` },
      { key: "diff", label: `${esc(prov)} − 全国均值`, num: true, fmt: (v) => `<b class="${v < 0 ? "down" : v > 0 ? "up" : ""}">${sfix(v, 1)}</b>` },
      { key: "prov_rank", label: `${esc(prov)}省内#`, num: true, fmt: (v) => `#${v}` },
      { key: "rk_diff", label: "省内# − 全国#", num: true, fmt: (v) => (v == null ? `<span class="muted">—</span>` : v > 0 ? `<span class="down">低估 ${v} 名</span>` : v < 0 ? `<span class="up">高看 ${-v} 名</span>` : "持平"), hideSm: true },
      { key: "raw", label: `${esc(prov)}2010最低分`, num: true, fmt: (v) => v ?? `<span class="muted">—</span>`, hideSm: true },
      { key: "city_bias", label: `${esc(prov)}对所在城市偏好`, num: true, fmt: (v) => (v == null ? `<span class="muted">—</span>` : `<span class="${v > 0 ? "up" : v < 0 ? "down" : ""}">${sfix(v, 1)}</span>`), hideSm: true },
    ], rows, {
      sortKey: "diff",
      asc: true,
      dense: true,
      filter: (r) => (bgTier === "top30" ? r.tier <= 3 : bgTier === "top56" ? r.tier <= 5 : true),
      onRowClick: (r) => selectSchool(r.school, true),
      onCount: (n, all) => ($("#bg-count").textContent = `${n} / ${all} 所招生高校`),
    });
    bgT.search($("#bq").value);
  }

  $("#sel-prov").value = curProv;
  $("#sel-prov").onchange = (e) => renderBargain(e.target.value);
  $$("#bg-tier button").forEach((b) => (b.onclick = () => {
    bgTier = b.dataset.bt;
    $$("#bg-tier button").forEach((x) => x.classList.toggle("on", x === b));
    if (bgT) bgT.rerender();
  }));
  $("#bq").addEventListener("input", (e) => bgT && bgT.search(e.target.value));

  renderMainTable(curMode);
  selectSchool(curSchool, false);
  renderBargain(curProv);
})();
