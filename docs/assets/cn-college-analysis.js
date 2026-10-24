(async function () {
  const CN = await loadJSON("data/cn_college.json");
  const PROVS_STD = CN.provs_std;
  const PROVS_RAW = CN.provs_raw;

  const tierBg = {
    1: "background:#fee2e2;color:#991b1b;font-weight:700",
    2: "background:#ffedd5;color:#9a3412;font-weight:600",
    3: "background:#fef9c3;color:#854d0e;font-weight:600",
    4: "background:#dcfce7;color:#166534;font-weight:600",
    5: "background:#d1fae5;color:#065f46;font-weight:600",
    6: "background:#e0f2fe;color:#075985;font-weight:600",
  };

  /* ---------------- Section 01: 4 Original Full Matrices ---------------- */
  let curMat = "std100";
  let matQuery = "";

  const matNotes = {
    std100: "图 7 · 2011 年 23 省平行志愿理科一批录取最低分标准化全表（102 校 × 23 省，以 665/645/625/605/585 分为界划分为 6 档；单元格绿色表示高于该校加权均值，橙色表示低于该校加权均值）",
    raw11: "图 6 · 2010/2011 年新浪教育抓取处理后 23 省各校原始理科录取最低分矩阵（前 50 校，含提前批的外交学院、中国青年政治学院、国际关系学院及二批的上海海关学院）",
    freq07: "图 2 · 2007 年各省高考理科录取最低分排名前 20 榜单上露脸次数最多的 26 所高校名次表（共 30 个省区，红字 NA 表示未进入该省前 20 名或未公布）",
    sc10: "图 5 · 从新浪教育抓取的 2010 年四川省理科录取原始数据节选（20 所高校，展示院校类型、所在省市、最低分、录取人数及批次）",
  };

  function stdDiffBg(diff) {
    if (diff == null) return "";
    const a = Math.min(Math.abs(diff) / 18, 1) * 0.36;
    if (diff > 1.5) return `background:rgba(17,122,67,${a.toFixed(2)})`;
    if (diff < -1.5) return `background:rgba(200,75,21,${a.toFixed(2)})`;
    return "";
  }

  function renderMatrix() {
    $$("#mat-tabs button").forEach((b) => b.classList.toggle("on", b.dataset.m === curMat));
    $("#mat-note").textContent = matNotes[curMat] || "";
    const q = matQuery.trim().toLowerCase();

    if (curMat === "std100") {
      $("#mat-legend").style.display = "flex";
      const rows = CN.std100.filter((r) => !q || r.school.toLowerCase().includes(q) || r.city.toLowerCase().includes(q));
      let h = `<table class="matrix"><thead><tr><th>排名</th><th>城市</th><th>学校</th><th>加权均值</th><th>均值</th>${PROVS_STD.map((p) => `<th>${esc(p)}</th>`).join("")}</tr></thead><tbody>`;
      rows.forEach((r) => {
        h += `<tr onclick="location.href='cn-college.html?school=${encodeURIComponent(r.school)}#profile'" style="cursor:pointer">`;
        h += `<td class="mono">${r.rank}</td>`;
        h += `<td>${esc(r.city)}</td>`;
        h += `<th style="${tierBg[r.tier] || ""}">${esc(r.school)}</th>`;
        h += `<td class="mono"><b>${fix(r.weighted_mean, 1)}</b></td>`;
        h += `<td class="mono">${r.mean}</td>`;
        PROVS_STD.forEach((p, idx) => {
          const v = r.scores[idx];
          const raw = r.raw_scores ? r.raw_scores[idx] : null;
          if (v == null) {
            h += `<td class="muted">—</td>`;
          } else {
            const diff = +(v - r.weighted_mean).toFixed(1);
            const tip = `<b>${esc(r.school)} · ${esc(p)}</b><br>2011 标准化分: <b>${v}</b><br>全国加权均值: ${fix(r.weighted_mean, 1)} (偏差 <b>${sfix(diff, 1)}</b>)${raw != null ? `<br>2010 原始最低分: ${raw}` : ""}`;
            h += `<td class="cell" style="${stdDiffBg(diff)}" data-tip-html="1" data-tip="${esc(tip)}">${v}</td>`;
          }
        });
        h += `</tr>`;
      });
      h += `</tbody></table>`;
      $("#mat-box").innerHTML = h;
    } else if (curMat === "raw11") {
      $("#mat-legend").style.display = "none";
      const rows = CN.raw11.filter((r) => !q || r.school.toLowerCase().includes(q) || r.city.toLowerCase().includes(q) || r.note.toLowerCase().includes(q));
      let h = `<table class="matrix"><thead><tr><th>序号</th><th>学校</th><th>标准化#</th>${PROVS_RAW.map((p) => `<th>${esc(p)}</th>`).join("")}</tr></thead><tbody>`;
      rows.forEach((r) => {
        h += `<tr><td class="mono">${r.order}</td>`;
        h += `<th>${esc(r.school)}${r.note ? ` <span class="tag pri">${esc(r.note.split("（")[0])}</span>` : ""}</th>`;
        h += `<td class="mono">${esc(r.std_rank)}</td>`;
        PROVS_RAW.forEach((p, idx) => {
          const v = r.scores[idx];
          if (v == null) {
            h += `<td class="muted">—</td>`;
          } else {
            const tip = `<b>${esc(r.school)} · ${esc(p)}</b><br>2010 原始录取最低分: <b>${v}</b>${r.note ? `<br><span class="muted">${esc(r.note)}</span>` : ""}`;
            h += `<td data-tip-html="1" data-tip="${esc(tip)}">${v}</td>`;
          }
        });
        h += `</tr>`;
      });
      h += `</tbody></table>`;
      $("#mat-box").innerHTML = h;
    } else if (curMat === "freq07") {
      $("#mat-legend").style.display = "none";
      const schs = CN.schools_07;
      const sumMap = Object.fromEntries(CN.freq07.summary.map((s) => [s.abbr, s]));
      const rows = CN.freq07.matrix.filter((r) => !q || r.province.toLowerCase().includes(q));
      let h = `<table class="matrix"><thead><tr><th>理工省份 \\ 学校</th>${schs.map((s) => `<th data-tip="${esc(sumMap[s].school)}：进入前20共 ${sumMap[s].top20_count}/30 省，平均名次 ${fix(sumMap[s].mean_rank, 1)}">${esc(s)}</th>`).join("")}</tr></thead><tbody>`;
      rows.forEach((r) => {
        h += `<tr><th>${esc(r.province)}</th>`;
        r.ranks.forEach((rk, idx) => {
          if (rk == null) {
            h += `<td style="color:#c81e1e;font-size:.68rem">NA</td>`;
          } else {
            const bg = rk <= 3 ? "background:#fee2e2;font-weight:700" : rk <= 10 ? "background:#fef9c3;font-weight:600" : "";
            h += `<td style="${bg}" data-tip="${esc(r.province)} · ${esc(sumMap[schs[idx]].school)}: 第 ${rk} 名">${rk}</td>`;
          }
        });
        h += `</tr>`;
      });
      h += `<tr style="background:#f4f2ec;font-weight:700"><th>前20名露脸省数 (共30省)</th>${schs.map((s) => `<td>${sumMap[s].top20_count}</td>`).join("")}</tr>`;
      h += `<tr style="background:#f4f2ec;font-weight:600"><th>上榜省份平均名次</th>${schs.map((s) => `<td>${fix(sumMap[s].mean_rank, 1)}</td>`).join("")}</tr>`;
      h += `</tbody></table>`;
      $("#mat-box").innerHTML = h;
    } else {
      $("#mat-legend").style.display = "none";
      const rows = CN.sichuan10.filter((r) => !q || r.school.toLowerCase().includes(q) || r.category.toLowerCase().includes(q));
      let h = `<table class="data dense"><thead><tr><th class="num">#</th><th>院校名称</th><th>院校类型</th><th>所在省市</th><th class="num">最低分</th><th class="num">平均分(原表0)</th><th class="num">年份</th><th class="num">录取人数</th><th>科类</th><th>录取批次</th></tr></thead><tbody>`;
      rows.forEach((r) => {
        h += `<tr><td class="num">${r.rank}</td><td><b>${esc(r.school)}</b></td><td>${esc(r.category)}</td><td>${esc(r.province)}</td><td class="num"><b>${r.min_score}</b></td><td class="num muted">${r.avg_score}</td><td class="num">${r.year}</td><td class="num"><b>${r.admitted}</b></td><td>${esc(r.stream)}</td><td><span class="tag ${r.batch.includes("提前") ? "pri" : "uni"}">${esc(r.batch)}</span></td></tr>`;
      });
      h += `</tbody></table>`;
      $("#mat-box").innerHTML = h;
    }
  }

  $$("#mat-tabs button").forEach((b) => (b.onclick = () => {
    curMat = b.dataset.m;
    renderMatrix();
  }));
  $("#mq").addEventListener("input", (e) => {
    matQuery = e.target.value;
    renderMatrix();
  });
  renderMatrix();

  /* ---------------- Section 02: 23 Provinces x 29 Cities Attractiveness Bias Matrix ---------------- */
  function biasCellStyle(v) {
    if (v == null) return "";
    const a = Math.min(Math.abs(v) / 15, 1) * 0.28;
    if (v > 0) return `color:#b91c1c;background:rgba(220,38,38,${a.toFixed(2)});font-weight:${v >= 5 ? 700 : 500}`;
    if (v < 0) return `color:#1d4ed8;background:rgba(37,99,235,${a.toFixed(2)});font-weight:${v <= -5 ? 700 : 500}`;
    return `color:#b91c1c`;
  }

  let bh = `<table class="matrix"><thead><tr><th>生源省 \\ 高校城市</th>${CN.cities.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>`;
  CN.city_bias.matrix.forEach((row) => {
    bh += `<tr><th style="cursor:pointer" onclick="location.href='cn-college.html?prov=${encodeURIComponent(row.province)}#bargain'" data-tip="点击查看 ${esc(row.province)} 考生高性价比选校排行">${esc(row.province)}</th>`;
    row.vals.forEach((v, ci) => {
      const c = CN.cities[ci];
      if (v == null) {
        bh += `<td class="muted">—</td>`;
      } else {
        const tip = `<b>${esc(row.province)}考生 → ${esc(c)}高校</b><br>吸引力偏差: <b>${sfix(v, 1)} 分</b><br><span class="muted">${v > 0 ? "高于全国平均投票分（更偏爱）" : v < 0 ? "低于全国平均投票分（相对低估/高性价比）" : "与全国平均持平"}</span>`;
        bh += `<td style="${biasCellStyle(v)}" data-tip-html="1" data-tip="${esc(tip)}">${v.toFixed(1)}</td>`;
      }
    });
    bh += `</tr>`;
  });
  bh += `</tbody></table>`;
  $("#bias-box").innerHTML = bh;

  const cityT = makeTable($("#city-table"), [
    { key: "city", label: "高校所在城市", cls: "name", fmt: (v) => `<b>${esc(v)}</b>` },
    { key: "pos_provs", label: "正偏好省份数 (>0)", num: true, fmt: (v) => `<span class="up"><b>${v}</b> 省</span>` },
    { key: "neg_provs", label: "负偏好省份数 (<0)", num: true, fmt: (v) => `<span class="down"><b>${v}</b> 省</span>` },
    { key: "max_val", label: "最青睐该城之省份 (最高正偏差)", num: true, fmt: (v, r) => `${esc(r.max_prov)} <b style="color:#b91c1c">+${fix(v, 1)}</b>` },
    { key: "min_val", label: "最冷落该城之省份 (最大负偏差)", num: true, fmt: (v, r) => `${esc(r.min_prov)} <b style="color:#1d4ed8">${fix(v, 1)}</b>` },
    { key: "mean_bias", label: "23省均值校验", num: true, fmt: (v) => `<span class="muted">${sfix(v, 2)}</span>`, hideSm: true },
  ], CN.city_bias.summary, {
    sortKey: "max_val",
    asc: false,
    dense: true,
    onCount: (n, all) => ($("#city-count").textContent = `${n} / ${all} 座城市`),
  });
  $("#cq").addEventListener("input", (e) => cityT.search(e.target.value));

  /* ---------------- Section 03: Cross-Period (06-07 vs 2012) & Stream (Sci vs Arts) ---------------- */
  let evMode = "period";
  let evT;

  function renderEvolution(mode) {
    evMode = mode;
    $$("#ev-tabs button").forEach((b) => b.classList.toggle("on", b.dataset.ev === mode));

    if (mode === "period") {
      $("#sc-title").textContent = "2006–07 四省理科均分 vs 2012 五省理科均分（共有 44 校）";
      $("#ev-table-title").textContent = "2006–07 四省均分 vs 2012 五省理科均分对比表";
      $("#sc-legend").innerHTML = `<span><i style="background:#117a43"></i>2012 名次上升 (≥3名)</span><span><i style="background:#9e2a2b"></i>名次基本稳定</span><span><i style="background:#b83227"></i>2012 名次下降 (≥3名)</span>`;

      const shared = CN.p07_4
        .filter((r) => r.sci12_avg != null)
        .map((r) => {
          const r12 = r.sci12_rank === "-" ? (r.norm_school.includes("北京") ? 4 : 9) : Number(r.sci12_rank);
          const dRank = r.rank - r12;
          return {
            school: r.norm_school,
            city: r.city,
            r07: r.rank,
            s07: r.avg_score,
            r12_str: r.sci12_rank,
            r12,
            s12: r.sci12_avg,
            d_rank: dRank,
            d_score: +(r.sci12_avg - r.avg_score).toFixed(1),
            std11: r.std11_wm,
          };
        });

      const notable = new Set(["清华大学", "北京大学", "复旦大学", "上海交通大学", "上海交通大学医学院", "北京大学医学部", "浙江大学", "中国科学技术大学", "南京大学", "中山大学", "哈尔滨工业大学", "北京师范大学", "山东大学", "武汉大学", "同济大学", "华南理工大学"]);
      scatter($("#scatter"), shared.map((x) => ({
        x: x.s07,
        y: x.s12,
        r: 5,
        color: x.d_rank >= 3 ? "#117a43" : x.d_rank <= -3 ? "#c84b15" : "#9e2a2b",
        label: x.school.replace(/大学$/, "").replace(/^上海交通大学医学院$/, "上交医").replace(/^北京大学医学部$/, "北医").replace(/^中国科学技术$/, "中科大").replace(/^哈尔滨工业$/, "哈工大"),
        showLabel: notable.has(x.school) || Math.abs(x.d_rank) >= 6,
        html: `<b>${esc(x.school)}</b> (${esc(x.city)})<br>06–07 四省均分: <b>${fix(x.s07, 1)}</b> (#${x.r07})<br>2012 理科均分: <b>${fix(x.s12, 1)}</b> (#${x.r12_str})<br>名次变化: <b>${x.d_rank > 0 ? "+" + x.d_rank : x.d_rank}</b>`,
      })), {
        xmin: 595, xmax: 675, ymin: 600, ymax: 678, w: 540, h: 400,
        xlab: "2006–2007 苏冀鄂粤四省理科平均分", ylab: "2012 豫粤鲁川皖五省理科平均分",
        diag: true, diagLabel: "y = x",
      });

      evT = makeTable($("#ev-table"), [
        { key: "r12", label: "12#", num: true, fmt: (v, r) => (r.r12_str === "-" ? `<span class="mono muted">单列</span>` : rankBadge(v)) },
        { key: "school", label: "学校", cls: "name", fmt: (v, r) => `<b>${esc(v)}</b><small>${esc(r.city)}</small>` },
        { key: "r07", label: "07#", num: true },
        { key: "d_rank", label: "Δ名次 (07−12)", num: true, fmt: (v) => (v > 0 ? `<b class="up">+${v}</b>` : v < 0 ? `<b class="down">${v}</b>` : "0") },
        { key: "s12", label: "2012均分", num: true, fmt: (v) => `<b>${fix(v, 1)}</b>` },
        { key: "s07", label: "06-07均分", num: true, fmt: (v) => fix(v, 1) },
        { key: "std11", label: "11标准化", num: true, fmt: (v) => fix(v, 1), hideSm: true },
      ], shared, {
        sortKey: "r12",
        asc: true,
        dense: true,
        onRowClick: (r) => { location.href = `cn-college.html?school=${encodeURIComponent(r.school)}#profile`; },
        onCount: (n, all) => ($("#ev-count").textContent = `${n} / ${all} 校`),
      });
      evT.search($("#eq").value);
    } else {
      $("#sc-title").textContent = "2012 五省理科平均分 vs 2012 五省文科平均分（共有 39 校）";
      $("#ev-table-title").textContent = "2012 五省理科 vs 文科平均分对比表";
      $("#sc-legend").innerHTML = `<span><i style="background:#9e2a2b"></i>文理兼招 Top 50 高校</span><span>虚线上侧：文科排位相对更高 · 下侧：理科排位相对更高</span>`;

      const shared = CN.arts12
        .filter((r) => r.sci12_avg != null)
        .map((r) => {
          const rSci = Number(r.sci12_rank);
          const dRank = rSci - r.rank;
          return {
            school: r.school,
            city: r.city,
            r_arts: r.rank,
            s_arts: r.avg_score,
            r_sci: rSci,
            s_sci: r.sci12_avg,
            d_rank: dRank,
            d_score: +(r.sci12_avg - r.avg_score).toFixed(1),
          };
        });

      const notable = new Set(["清华大学", "北京大学", "复旦大学", "中国人民大学", "上海交通大学", "浙江大学", "南京大学", "华东师范大学", "北京师范大学", "对外经济贸易大学", "中央财经大学", "上海财经大学", "哈尔滨工业大学", "华中科技大学", "北京邮电大学", "天津大学", "东南大学", "武汉大学", "中山大学"]);
      scatter($("#scatter"), shared.map((x) => ({
        x: x.s_sci,
        y: x.s_arts,
        r: 5,
        color: x.d_rank >= 5 ? "#78358a" : x.d_rank <= -5 ? "#283891" : "#9e2a2b",
        label: x.school.replace(/大学$/, "").replace(/^哈尔滨工业$/, "哈工大").replace(/^对外经济贸易$/, "对外经贸"),
        showLabel: notable.has(x.school),
        html: `<b>${esc(x.school)}</b> (${esc(x.city)})<br>2012 理科均分: <b>${fix(x.s_sci, 1)}</b> (#${x.r_sci})<br>2012 文科均分: <b>${fix(x.s_arts, 1)}</b> (#${x.r_arts})<br>文理名次差 (理#−文#): <b>${x.d_rank > 0 ? "文科高 " + x.d_rank + " 名" : x.d_rank < 0 ? "理科高 " + (-x.d_rank) + " 名" : "持平"}</b>`,
      })), {
        xmin: 604, xmax: 676, ymin: 593, ymax: 652, w: 540, h: 400,
        xlab: "2012 五省理科录取平均分", ylab: "2012 五省文科录取平均分",
      });

      evT = makeTable($("#ev-table"), [
        { key: "r_sci", label: "理科#", num: true, fmt: rankBadge },
        { key: "school", label: "学校", cls: "name", fmt: (v, r) => `<b>${esc(v)}</b><small>${esc(r.city)}</small>` },
        { key: "r_arts", label: "文科#", num: true, fmt: rankBadge },
        { key: "d_rank", label: "理# − 文#", num: true, fmt: (v) => (v > 0 ? `<span class="up">文高 +${v}</span>` : v < 0 ? `<span class="down">理高 +${-v}</span>` : "0") },
        { key: "s_sci", label: "理科均分", num: true, fmt: (v) => `<b>${fix(v, 1)}</b>` },
        { key: "s_arts", label: "文科均分", num: true, fmt: (v) => `<b>${fix(v, 1)}</b>` },
        { key: "d_score", label: "理−文分差", num: true, fmt: (v) => `+${fix(v, 1)}`, hideSm: true },
      ], shared, {
        sortKey: "r_sci",
        asc: true,
        dense: true,
        onRowClick: (r) => { location.href = `cn-college.html?school=${encodeURIComponent(r.school)}#profile`; },
        onCount: (n, all) => ($("#ev-count").textContent = `${n} / ${all} 校`),
      });
      evT.search($("#eq").value);
    }
  }

  $$("#ev-tabs button").forEach((b) => (b.onclick = () => renderEvolution(b.dataset.ev)));
  $("#eq").addEventListener("input", (e) => evT && evT.search(e.target.value));
  renderEvolution("period");
})();
