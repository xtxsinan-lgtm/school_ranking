(async function () {
  const C = await loadJSON("data/college.json");
  const R = C.ranking;
  const byAbbr = Object.fromEntries(R.map((r) => [r.abbr, r]));
  const bw = C.bandwidth || 1.0;

  $("#s-n").innerHTML = `${C.counts.schools}<span>校</span>`;
  $("#s-p").innerHTML = `${int(C.counts.pairs)}<span>组对决</span>`;
  $("#s-s").innerHTML = `${int(C.counts.students)}<span>人次</span>`;
  $("#src-old").textContent = int(C.counts.old_pairs);
  $("#bw").textContent = fix(bw, 1);

  /* pair lookup */
  const pairMap = new Map();
  const allPairs = [];
  C.pairs.forEach(([a, b, p, lo, hi, n, k]) => {
    const pB = +(100 - p).toFixed(1), loB = +(100 - hi).toFixed(1), hiB = +(100 - lo).toFixed(1);
    const kB = n != null && k != null ? n - k : null;
    pairMap.set(a + "|" + b, { p, lo, hi, n, k });
    pairMap.set(b + "|" + a, { p: pB, lo: loB, hi: hiB, n, k: kB });
    const ra = byAbbr[a], rb = byAbbr[b];
    if (ra && rb && n != null) {
      const hiSch = ra.rank < rb.rank ? ra : rb;
      const loSch = ra.rank < rb.rank ? rb : ra;
      const pr = pairMap.get(hiSch.abbr + "|" + loSch.abbr);
      const dth = hiSch.theta - loSch.theta;
      const pm = 100 * sig(dth);
      allPairs.push({
        pair: `${hiSch.abbr} vs ${loSch.abbr}`,
        a: hiSch.abbr, b: loSch.abbr,
        a_rank: hiSch.rank, b_rank: loSch.rank,
        dth: +dth.toFixed(3),
        obs: pr.p, lo: pr.lo, hi: pr.hi,
        pm: +pm.toFixed(1),
        res: +(pr.p - pm).toFixed(1),
        abs_res: +Math.abs(pr.p - pm).toFixed(1),
        k: pr.k, n: pr.n,
        w: +Math.exp(-(dth * dth) / (2 * bw * bw)).toFixed(3),
      });
    }
  });
  const hy = pairMap.get("Harvard|Yale");
  if (hy && $("#ex-hy")) {
    $("#ex-hy").textContent = `${hy.p}% [${hy.lo}%–${hy.hi}%] → k=${int(hy.k)}, n=${int(hy.n)}`;
  }

  /* ---------------- Section 01: 2D Cross-Admit Matrix ---------------- */
  const ivyUcList = ["MIT", "Harvard", "Stanford", "Yale", "Princeton", "Caltech", "Columbia", "Chicago", "Brown", "UPenn", "Duke", "Dartmouth", "Cornell", "UCB", "UCLA"];
  const mSets = {
    top20: () => R.slice(0, 20),
    uni20: () => R.filter((r) => r.type === "University").slice(0, 20),
    lac15: () => R.filter((r) => r.type === "LAC").slice(0, 15),
    ivyuc: () => ivyUcList.map((k) => byAbbr[k]).filter(Boolean),
  };
  const cellBg = (p) => {
    if (p == null) return "";
    const d = (p - 50) / 50;
    return d > 0
      ? `background:rgba(40,56,145,${(Math.min(d, 1) * 0.4).toFixed(2)})`
      : `background:rgba(200,75,21,${(Math.min(-d, 1) * 0.36).toFixed(2)})`;
  };
  function renderMatrix(mode) {
    const list = mSets[mode]();
    let html = `<table class="matrix"><thead><tr><th>行校 i \\ 列校 j</th>${list.map((c) => `<th data-tip="${esc(c.name)} (#${c.rank}, θ=${fix(c.theta, 2)})">${esc(c.abbr)}</th>`).join("")}</tr></thead><tbody>`;
    list.forEach((ra) => {
      html += `<tr><th data-tip="${esc(ra.name)} (#${ra.rank}, θ=${fix(ra.theta, 2)})">#${ra.rank} ${esc(ra.abbr)}</th>`;
      list.forEach((cb) => {
        if (ra.abbr === cb.abbr) { html += `<td class="diag">—</td>`; return; }
        const pr = pairMap.get(ra.abbr + "|" + cb.abbr);
        const dth = ra.theta - cb.theta;
        const pm = 100 * sig(dth);
        const w = Math.exp(-(dth * dth) / (2 * bw * bw));
        if (pr) {
          const tip = `<b>${esc(ra.abbr)} (#${ra.rank}) vs ${esc(cb.abbr)} (#${cb.rank})</b><br>实测选择 ${esc(ra.abbr)}: <b>${pr.p.toFixed(0)}%</b> [${pr.lo}%–${pr.hi}%]<br>反推人数: k = ${int(pr.k)} / n = ${int(pr.n)}<br>模型预测: ${pm.toFixed(1)}% (Δθ=${sfix(dth, 2)}, w=${fix(w, 2)})`;
          html += `<td class="cell" data-a="${esc(ra.abbr)}" data-b="${esc(cb.abbr)}" style="${cellBg(pr.p)}" data-tip-html="1" data-tip="${esc(tip)}">${pr.p.toFixed(0)}</td>`;
        } else {
          const tip = `<b>${esc(ra.abbr)} (#${ra.rank}) vs ${esc(cb.abbr)} (#${cb.rank})</b><br>无实测样本<br>模型预测选择 ${esc(ra.abbr)}: <b>${pm.toFixed(1)}%</b> (Δθ=${sfix(dth, 2)})`;
          html += `<td class="cell mod" data-a="${esc(ra.abbr)}" data-b="${esc(cb.abbr)}" data-tip-html="1" data-tip="${esc(tip)}">${pm.toFixed(0)}</td>`;
        }
      });
      html += `</tr>`;
    });
    html += `</tbody></table>`;
    $("#mat-box").innerHTML = html;
    $$("#mtabs button").forEach((b) => b.classList.toggle("on", b.dataset.m === mode));
    $$("#mat-box td.cell").forEach((td) => {
      td.onclick = () => {
        location.href = `college.html?a=${encodeURIComponent(td.dataset.a)}&b=${encodeURIComponent(td.dataset.b)}#h2h`;
      };
    });
  }
  $$("#mtabs button").forEach((b) => (b.onclick = () => renderMatrix(b.dataset.m)));
  renderMatrix("top20");

  /* ---------------- Section 02: 4-Model Comparison Table ---------------- */
  const diffFmt = (v, r) => {
    if (v == null) return `<span class="muted">—</span>`;
    const d = v - r.rank;
    return `${v} ${d > 0 ? `<span class="up">↑${d}</span>` : d < 0 ? `<span class="down">↓${-d}</span>` : ""}`;
  };
  let filt = "all";
  const shortFull = (s) => s.replace(/^Massachusetts Institute of Technology$/, "Mass. Inst. of Tech.")
    .replace(/^University of California, /, "UC ").replace(/^University of /, "U ")
    .replace(/ in the City of New York$/, "").replace(/ - Ann Arbor$/, "").replace(/ - Main Campus$/, "");
  const T = makeTable($("#table"), [
    { key: "rank", label: "加权#", num: true, fmt: rankBadge },
    { key: "abbr", label: "学校", cls: "name", fmt: (v, r) => `<b>${esc(v)}</b><small>${esc(shortFull(r.name))}</small>` },
    { key: "type", label: "类型", fmt: (v) => (v === "LAC" ? `<span class="tag lac">LAC</span>` : `<span class="tag uni">Univ</span>`), hideSm: true },
    { key: "theta", label: "加权 θ (±SE)", num: true, fmt: (v, r) => `<b>${fix(v, 3)}</b> <small>±${fix(r.se, 3)}</small>` },
    { key: "lo", label: "加权 95% 区间", num: true, fmt: (v, r) => `${r.lo}–${r.hi}`, hideSm: true },
    { key: "plain", label: "普通#", num: true, fmt: diffFmt },
    { key: "plain_theta", label: "普通 θ [区间]", num: true, fmt: (v, r) => `${fix(v, 3)} <small>[${r.plain_lo ?? "—"}–${r.plain_hi ?? "—"}]</small>`, hideSm: true },
    { key: "cap50", label: "封顶#", num: true, fmt: diffFmt },
    { key: "cap50_theta", label: "封顶 θ [区间]", num: true, fmt: (v, r) => `${fix(v, 3)} <small>[${r.cap50_lo ?? "—"}–${r.cap50_hi ?? "—"}]</small>`, hideSm: true },
    { key: "old_bt_rank", label: "旧表#", num: true, fmt: (v, r) => (v == null ? `<span class="muted">—</span>` : `${v} <small>(${fix(r.old_bt_theta, 2)})</small>`) },
    { key: "tot_n", label: "总人次 N", num: true, fmt: int, hideSm: true },
    { key: "eff", label: "有效 N_eff", num: true, fmt: int },
  ], R, {
    sortKey: "rank", asc: true, dense: true,
    filter: (r) => filt === "all" || r.type === filt,
    onRowClick: (r) => { location.href = `college.html?school=${encodeURIComponent(r.abbr)}`; },
    onCount: (n, all) => ($("#count").textContent = n === all ? `${all} 校` : `${n} / ${all} 校`),
  });
  $$("#ftabs button").forEach((b) => (b.onclick = () => {
    filt = b.dataset.f;
    $$("#ftabs button").forEach((x) => x.classList.toggle("on", x === b));
    T.rerender();
  }));
  $("#q").addEventListener("input", (e) => T.search(e.target.value));

  /* ---------------- Section 03: Old vs New 95 Schools ---------------- */
  const O = C.oldnew.map((o) => ({
    ...o,
    d_rank: o.old_rank - o.new_rank,
    d_pct: (o.new_pct ?? 0) - (o.old_pct ?? 0),
  }));
  const M = Math.max(...O.map((o) => Math.max(o.old_rank, o.new_rank)));
  const top = O.slice().sort((a, b) => b.d_rank - a.d_rank);
  const lab = new Set([...top.slice(0, 7), ...top.slice(-7)].map((o) => o.school));
  ["MIT", "Harvard", "Stanford", "UCLA", "UCB", "Pomona", "Williams"].forEach((s) => lab.add(s));
  const ticks = [1, 20, 40, 60, 80, M].map((t) => M + 1 - t);
  scatter($("#scatter"), O.map((o) => ({
    x: M + 1 - o.old_rank, y: M + 1 - o.new_rank, color: o.type === "LAC" ? "#b87314" : "#283891", r: 4.5,
    label: o.school, showLabel: lab.has(o.school),
    html: `<b>${esc(o.school)}</b> (${o.type})<br>旧表 #${o.old_rank} → 新数据 #${o.new_rank} (${o.d_rank > 0 ? "+" + o.d_rank : o.d_rank})<br>Z 分数: ${fix(o.old_z, 2)} → ${fix(o.new_z, 2)} (ΔZ = ${sfix(o.delta_z, 2)})`,
  })), {
    xmin: 0, xmax: M + 1, ymin: 0, ymax: M + 1, xticks: ticks, yticks: ticks, w: 540, h: 410,
    xlab: "早年手工表名次 (n=40 等权)", ylab: "新抓取数据名次 (n=40 等权)", diag: true, diagLabel: "new = old",
    fmtX: (v) => Math.round(M + 1 - v), fmtY: (v) => Math.round(M + 1 - v),
  });

  let onFilt = "all";
  const ONT = makeTable($("#on-table"), [
    { key: "new_rank", label: "新#", num: true, fmt: rankBadge },
    { key: "school", label: "学校", cls: "name", fmt: (v, r) => `<b>${esc(v)}</b><small>${r.type === "LAC" ? "LAC" : "Univ"}</small>` },
    { key: "old_rank", label: "旧#", num: true },
    { key: "d_rank", label: "Δ名次 (旧−新)", num: true, fmt: (v) => (v > 0 ? `<span class="up">+${v}</span>` : v < 0 ? `<span class="down">${v}</span>` : "0") },
    { key: "sheet_rank", label: "旧表原序#", num: true, fmt: (v) => v ?? "—", hideSm: true },
    { key: "new_z", label: "新 Z", num: true, fmt: (v) => fix(v, 2) },
    { key: "old_z", label: "旧 Z", num: true, fmt: (v) => fix(v, 2) },
    { key: "delta_z", label: "ΔZ", num: true, fmt: (v) => `<span class="${v > 0 ? "up" : v < 0 ? "down" : ""}">${sfix(v, 2)}</span>` },
    { key: "new_pct", label: "新百分位", num: true, fmt: (v) => (v != null ? `P${v}` : "—"), hideSm: true },
    { key: "old_pct", label: "旧百分位", num: true, fmt: (v) => (v != null ? `P${v}` : "—"), hideSm: true },
  ], O, {
    sortKey: "new_rank", asc: true, dense: true,
    onRowClick: (r) => { location.href = `college.html?school=${encodeURIComponent(r.school)}`; },
    filter: (r) => onFilt === "all" || r.type === onFilt,
    onCount: (n, all) => ($("#on-count").textContent = `${n} / ${all} 校`),
  });
  $$("#on-tabs button").forEach((b) => (b.onclick = () => {
    onFilt = b.dataset.onf;
    $$("#on-tabs button").forEach((x) => x.classList.toggle("on", x === b));
    ONT.rerender();
  }));
  $("#onq").addEventListener("input", (e) => ONT.search(e.target.value));

  /* ---------------- Section 04: Largest Pairwise Residuals Table ---------------- */
  let minN = 30;
  const RT = makeTable($("#res-table"), [
    { key: "pair", label: "对决院校 (高排名 A vs 低排名 B)", cls: "name", fmt: (v, r) => `<b>#${r.a_rank} ${esc(r.a)}</b> vs <b>#${r.b_rank} ${esc(r.b)}</b>` },
    { key: "n", label: "样本 k / n", num: true, fmt: (v, r) => `${int(r.k)} / <b>${int(v)}</b>` },
    { key: "obs", label: "A 实测胜率", num: true, fmt: (v) => `<b>${v.toFixed(1)}%</b>` },
    { key: "lo", label: "95% Wilson CI", num: true, fmt: (v, r) => `<span class="muted">[${r.lo.toFixed(1)}%, ${r.hi.toFixed(1)}%]</span>`, hideSm: true },
    { key: "pm", label: "全局模型 P(A≻B)", num: true, fmt: (v) => `${v.toFixed(1)}%` },
    { key: "res", label: "残差 (实测−模型)", num: true, fmt: (v) => `<b class="${v > 0 ? "up" : v < 0 ? "down" : ""}">${sfix(v, 1)}%</b>` },
    { key: "abs_res", label: "|残差|", num: true, fmt: (v) => `${v.toFixed(1)}%` },
    { key: "dth", label: "分差 Δθ", num: true, fmt: (v) => fix(v, 3), hideSm: true },
    { key: "w", label: "核权重 w_ij", num: true, fmt: (v) => fix(v, 2), hideSm: true },
  ], allPairs, {
    sortKey: "abs_res", asc: false, dense: true,
    filter: (r) => r.n >= minN,
    onRowClick: (r) => { location.href = `college.html?a=${encodeURIComponent(r.a)}&b=${encodeURIComponent(r.b)}#h2h`; },
    onCount: (n, all) => ($("#res-count").textContent = `${n} 组对决`),
  });
  $$("#res-tabs button").forEach((b) => (b.onclick = () => {
    minN = Number(b.dataset.rn);
    $$("#res-tabs button").forEach((x) => x.classList.toggle("on", x === b));
    RT.rerender();
  }));
  $("#rq").addEventListener("input", (e) => RT.search(e.target.value));
})();
