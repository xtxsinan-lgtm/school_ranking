(async function () {
  const C = await loadJSON("data/college.json");
  const R = C.ranking;
  const byAbbr = Object.fromEntries(R.map((r) => [r.abbr, r]));
  const bw = C.bandwidth || 1.0;

  /* pair lookup & per-school opponent lists */
  const pairMap = new Map();
  const oppMap = new Map();
  C.pairs.forEach(([a, b, p, lo, hi, n, k]) => {
    const pB = +(100 - p).toFixed(1), loB = +(100 - hi).toFixed(1), hiB = +(100 - lo).toFixed(1);
    const kB = n != null && k != null ? n - k : null;
    pairMap.set(a + "|" + b, { p, lo, hi, n, k });
    pairMap.set(b + "|" + a, { p: pB, lo: loB, hi: hiB, n, k: kB });
    if (!oppMap.has(a)) oppMap.set(a, []);
    if (!oppMap.has(b)) oppMap.set(b, []);
    oppMap.get(a).push({ opp: b, p, lo, hi, n, k });
    oppMap.get(b).push({ opp: a, p: pB, lo: loB, hi: hiB, n, k: kB });
  });

  /* ---------------- Section 01: Clean 97-School Main Ranking Table ---------------- */
  const N = R.length;
  const rankBar = (r) => {
    const s = (v) => ((v - 1) / (N - 1)) * 100;
    return `<div class="rcell"><div class="rbar"><div class="seg2" style="left:${s(r.lo)}%;width:${Math.max(s(r.hi) - s(r.lo), 1.5)}%"></div><div class="dot" style="left:${s(r.rank)}%"></div></div><small>${r.lo} – ${r.hi}</small></div>`;
  };

  const qs = new URLSearchParams(location.search);
  let filt = "all";
  let curA = qs.get("a") || qs.get("school") || "Stanford";
  if (!byAbbr[curA]) curA = "Stanford";
  let curB = qs.get("b") || (curA === "MIT" ? "Stanford" : "MIT");
  if (!byAbbr[curB] || curB === curA) curB = curA === "MIT" ? "Stanford" : "MIT";

  let T = makeTable($("#table"), [
    { key: "rank", label: "#", num: true, fmt: rankBadge },
    { key: "abbr", label: "学校", cls: "name", fmt: (v, r) => `<b>${esc(v)}</b><small>${esc(r.name)}</small>` },
    { key: "type", label: "类型", fmt: (v) => (v === "LAC" ? `<span class="tag lac">文理学院</span>` : `<span class="tag uni">综合大学</span>`), hideSm: true },
    { key: "theta", label: "偏好实力分 θ (±SE)", num: true, fmt: (v, r) => `<b>${fix(v, 3)}</b> <small>±${fix(r.se, 3)}</small>` },
    { key: "lo", label: "95% 名次区间", fmt: (v, r) => rankBar(r), sort: (r) => r.hi - r.lo, hideSm: true },
    { key: "wins", label: "实测战绩 (胜-负-平)", num: true, fmt: (v, r) => `${r.wins}胜 · ${r.losses}负 · ${r.ties}平` },
    { key: "n_opp", label: "对手数", num: true, hideSm: true },
    { key: "tot_n", label: "共同录取总人次", num: true, fmt: int, hideSm: true },
    { key: "eff", label: "同档有效人次", num: true, fmt: int, hideSm: true },
  ], R, {
    sortKey: "rank", asc: true, dense: true,
    rowId: (r) => r.abbr, activeId: curA,
    filter: (r) => filt === "all" || r.type === filt,
    onRowClick: (r) => {
      $("#sa").value = r.abbr;
      if ($("#sb").value === r.abbr) $("#sb").value = r.abbr === "MIT" ? "Stanford" : "MIT";
      duel(true);
      $("#h2h").scrollIntoView({ behavior: "smooth" });
    },
    onCount: (n, all) => ($("#count").textContent = n === all ? `${all} 校` : `${n} / ${all} 校`),
  });
  $$("#ftabs button").forEach((b) => (b.onclick = () => {
    filt = b.dataset.f;
    $$("#ftabs button").forEach((x) => x.classList.toggle("on", x === b));
    T.rerender();
  }));
  $("#q").addEventListener("input", (e) => T.search(e.target.value));

  /* ---------------- Section 02: Head to Head & Single-School All Opponents Table ---------------- */
  const opts = R.slice().sort((a, b) => a.rank - b.rank)
    .map((r) => `<option value="${esc(r.abbr)}">#${r.rank} ${esc(r.abbr)} — ${esc(r.name)} (θ=${fix(r.theta, 2)})</option>`).join("");
  $("#sa").innerHTML = opts; $("#sb").innerHTML = opts;

  let oppT;
  function renderOpponents(a) {
    const raw = oppMap.get(a.abbr) || [];
    const rows = raw.map((x) => {
      const b = byAbbr[x.opp] || { rank: 999, abbr: x.opp, name: x.opp, type: "University", theta: 0 };
      const dth = a.theta - b.theta;
      const pm = 100 * sig(dth);
      return {
        opp_rank: b.rank,
        opp: b.abbr,
        opp_name: b.name,
        type: b.type,
        opp_theta: b.theta,
        p: x.p,
        lo: x.lo,
        hi: x.hi,
        k: x.k,
        n: x.n,
        pm: +pm.toFixed(1),
        res: +(x.p - pm).toFixed(1),
      };
    });
    $("#opp-title").innerHTML = `${esc(a.abbr)} (${esc(a.name)}) 的全部实测对手档案`;
    $("#opp-summary").textContent = `总战绩: ${a.wins}胜 ${a.losses}负 ${a.ties}平 · 对手数: ${rows.length} · 共同录取总人次: ${int(a.tot_n)}`;
    oppT = makeTable($("#opp-table"), [
      { key: "opp_rank", label: "对手#", num: true, fmt: rankBadge },
      { key: "opp", label: "对手学校", cls: "name", fmt: (v, r) => `<b>${esc(v)}</b><small>${esc(r.opp_name)}</small>` },
      { key: "type", label: "类型", fmt: (v) => (v === "LAC" ? `<span class="tag lac">LAC</span>` : `<span class="tag uni">Univ</span>`), hideSm: true },
      { key: "opp_theta", label: "对手 θ", num: true, fmt: (v) => fix(v, 3) },
      { key: "p", label: `${esc(a.abbr)} 实测胜率`, num: true, fmt: (v) => `<b class="${v > 50 ? "up" : v < 50 ? "down" : ""}">${v.toFixed(1)}%</b>` },
      { key: "lo", label: "95% 置信区间", num: true, fmt: (v, r) => `<span class="muted">[${r.lo.toFixed(1)}%, ${r.hi.toFixed(1)}%]</span>`, hideSm: true },
      { key: "n", label: "反推人数 (k / n)", num: true, fmt: (v, r) => `${int(r.k)} / <b>${int(v)}</b>` },
      { key: "pm", label: "模型胜率", num: true, fmt: (v) => `${v.toFixed(1)}%` },
      { key: "res", label: "残差 (实测−模型)", num: true, fmt: (v) => `${sfix(v, 1)}%`, hideSm: true },
    ], rows, {
      sortKey: "opp_rank", asc: true, dense: true,
      onRowClick: (r) => { $("#sb").value = r.opp; duel(false); },
      onCount: (n, all) => ($("#opp-count").textContent = `${n} / ${all} 个对手`),
    });
    oppT.search($("#oq").value);
  }
  $("#oq").addEventListener("input", (e) => oppT && oppT.search(e.target.value));

  function duel(rebuildOpp = true) {
    const a = byAbbr[$("#sa").value], b = byAbbr[$("#sb").value];
    T.setActive(a.abbr);
    $$("#suggest .pchip").forEach((c) => c.classList.toggle("on", c.dataset.a === a.abbr && c.dataset.b === b.abbr));
    if (rebuildOpp) renderOpponents(a);
    if (a === b) { $("#duel").innerHTML = `<p class="muted">请选择两所不同的院校。</p>`; return; }
    const dth = a.theta - b.theta;
    const pm = 100 * sig(dth);
    const w = Math.exp(-(dth * dth) / (2 * bw * bw));
    const real = pairMap.get(a.abbr + "|" + b.abbr);
    const main = real ? real.p : pm;
    const bar = (p, cls) => `<div class="bar ${cls}"><div class="a" style="width:${Math.min(Math.max(p, 9), 91)}%">${esc(a.abbr)} ${p.toFixed(1)}%</div>
      <div class="b" style="width:${Math.min(Math.max(100 - p, 9), 91)}%">${(100 - p).toFixed(1)}% ${esc(b.abbr)}</div></div>`;
    let h = `<div class="duel-head">
      <div class="duel-team a"><div><div class="nm">${esc(a.abbr)} <span class="muted" style="font-weight:400;font-size:.78rem">${esc(a.name)}</span></div><div class="sub">#${a.rank} [95% 区间: ${a.lo}–${a.hi}] · θ = ${fix(a.theta, 3)} ±${fix(a.se, 3)}</div></div><div class="p">${main.toFixed(1)}%</div></div>
      <div class="duel-team b"><div><div class="nm">${esc(b.abbr)} <span class="muted" style="font-weight:400;font-size:.78rem">${esc(b.name)}</span></div><div class="sub">#${b.rank} [95% 区间: ${b.lo}–${b.hi}] · θ = ${fix(b.theta, 3)} ±${fix(b.se, 3)}</div></div><div class="p">${(100 - main).toFixed(1)}%</div></div></div>`;
    h += `<div class="row"><span class="lab">实测对决</span>${real ? bar(real.p, "") : `<span class="empty">Parchment 无该对院校实测记录</span>`}</div>`;
    h += `<div class="row"><span class="lab">模型预测</span>${bar(pm, "model")}</div>`;
    h += `<div class="expl mono">`;
    h += real
      ? `实测反推人数: k = <b>${int(real.k)}</b> / n = <b>${int(real.n)}</b> · 95% Wilson CI: [${real.lo}%, ${real.hi}%] · 残差: ${sfix(real.p - pm, 1)}% · `
      : `无直接实测样本 · `;
    h += `Δθ = ${sfix(dth, 3)} · 模型 P(${esc(a.abbr)} ≻ ${esc(b.abbr)}) = <b>${pm.toFixed(1)}%</b> · 同档权重 w_ij = ${fix(w, 3)}</div>`;
    $("#duel").innerHTML = h;
  }
  [["Harvard", "Yale"], ["Stanford", "MIT"], ["UCB", "UCLA"], ["Princeton", "Columbia"], ["UCLA", "Umich"], ["Pomona", "Williams"], ["CMU", "Cornell"], ["Chicago", "UPenn"]].forEach(([x, y]) => {
    if (!byAbbr[x] || !byAbbr[y]) return;
    const b = document.createElement("button");
    b.className = "pchip"; b.dataset.a = x; b.dataset.b = y; b.textContent = `${x} vs ${y}`;
    b.onclick = () => { $("#sa").value = x; $("#sb").value = y; duel(true); };
    $("#suggest").appendChild(b);
  });
  $("#sa").value = curA; $("#sb").value = curB;
  $("#sa").onchange = () => duel(true);
  $("#sb").onchange = () => duel(false);
  duel(true);
  if (qs.get("a") || qs.get("school")) {
    setTimeout(() => $("#h2h").scrollIntoView({ behavior: "smooth" }), 120);
  }
})();
