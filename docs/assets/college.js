(async function () {
  const C = await loadJSON("data/college.json");
  const R = C.ranking;
  const byAbbr = Object.fromEntries(R.map((r) => [r.abbr, r]));

  $("#s-n").textContent = C.counts.schools;
  $("#s-p").textContent = int(C.counts.pairs);
  $("#s-s").textContent = (C.counts.students / 10000).toFixed(0) + " 万";
  $("#src-pairs").textContent = `${int(C.counts.pairs)} 组两校对决`;
  $("#src-old").textContent = int(C.counts.old_pairs);
  $("#bw").textContent = C.bandwidth;

  /* pair lookup (stored once per unordered pair) */
  const pairMap = new Map();
  C.pairs.forEach(([a, b, p, lo, hi, n]) => {
    pairMap.set(a + "|" + b, { p, lo, hi, n });
    pairMap.set(b + "|" + a, { p: +(100 - p).toFixed(1), lo: +(100 - hi).toFixed(1), hi: +(100 - lo).toFixed(1), n });
  });
  const hy = pairMap.get("Harvard|Yale");
  if (hy) {
    $("#ex-pair").innerHTML = `例如：同时被哈佛和耶鲁录取的学生中，<b>${hy.p}%</b> 选了哈佛、<b>${100 - hy.p}%</b> 选了耶鲁。可以理解为“哈佛 vs 耶鲁”这场比赛，哈佛赢了 ${hy.p}% 的回合。`;
    $("#ex-n").innerHTML = `实例：哈佛 vs 耶鲁公布的是 ${hy.p}%，区间 ${hy.lo}%–${hy.hi}%。能同时吻合这两个数字的是 <b>约 ${int(hy.n)} 人</b>。`;
  }

  /* ---------------- head to head ---------------- */
  const opts = R.slice().sort((a, b) => a.abbr.localeCompare(b.abbr))
    .map((r) => `<option value="${esc(r.abbr)}">${esc(r.abbr)} — ${esc(r.name)}</option>`).join("");
  $("#sa").innerHTML = opts; $("#sb").innerHTML = opts;
  $("#sa").value = "Stanford"; $("#sb").value = "MIT";
  function duel() {
    const a = byAbbr[$("#sa").value], b = byAbbr[$("#sb").value];
    if (a === b) { $("#duel").innerHTML = `<p class="muted">请选择两所不同的学校。</p>`; return; }
    const pm = 100 * sig(a.theta - b.theta);
    const real = pairMap.get(a.abbr + "|" + b.abbr);
    const bar = (p, tag) => `<div class="row"><span class="lab">${tag}</span><div class="bar">
      <div class="a" style="width:${Math.max(p, 8)}%">${esc(a.abbr)} ${p.toFixed(0)}%</div>
      <div class="b" style="width:${Math.max(100 - p, 8)}%">${(100 - p).toFixed(0)}% ${esc(b.abbr)}</div></div></div>`;
    let h = "";
    h += real ? bar(real.p, "真实数据") : `<div class="row"><span class="lab">真实数据</span><span class="muted">Parchment 上两校没有足够的共同录取学生，无直接数据。</span></div>`;
    h += bar(pm, "模型预测");
    h += `<p class="muted" style="font-size:.9rem;margin-bottom:0">`;
    if (real) h += `真实数据：约 ${int(real.n)} 名同时被两校录取的学生，${esc(a.abbr)} 的 95% 区间为 ${real.lo}%–${real.hi}%。<br>`;
    h += `模型：${esc(a.abbr)} 实力分 ${fix(a.theta, 2)}（第 ${a.rank} 名），${esc(b.abbr)} 实力分 ${fix(b.theta, 2)}（第 ${b.rank} 名），分差 ${fix(a.theta - b.theta, 2)} → ${esc(a.abbr)} 被选中的概率 ${pm.toFixed(0)}%。`;
    if (real && Math.abs(real.p - pm) > 12) h += `<br>两者差距较大：说明这组对决与两校对其他学校的整体表现不太一致（例如地域、专业、学费等特殊因素）。`;
    h += `</p>`;
    $("#duel").innerHTML = h;
  }
  $("#sa").onchange = duel; $("#sb").onchange = duel;
  duel();

  /* ---------------- ranking table ---------------- */
  const N = R.length;
  const rankBar = (r) => {
    const s = (v) => ((v - 1) / (N - 1)) * 100;
    return `<div class="rbar"><div class="seg" style="left:${s(r.lo)}%;width:${Math.max(s(r.hi) - s(r.lo), 1)}%"></div><div class="dot" style="left:${s(r.rank)}%"></div></div>`;
  };
  const diff = (v, r) => { const d = v - r.rank; return `${v} ${d > 0 ? `<span class="up" title="分档加权后上升">↑${d}</span>` : d < 0 ? `<span class="down">↓${-d}</span>` : ""}`; };
  let filt = "all";
  const T = makeTable($("#table"), [
    { key: "rank", label: "名次", num: true },
    { key: "abbr", label: "学校", cls: "name", fmt: (v, r) => `${esc(v)}<br><small>${esc(r.name)}</small>` },
    { key: "type", label: "类型", fmt: (v) => (v === "LAC" ? `<span class="tag lac">文理学院</span>` : `<span class="tag uni">综合大学</span>`) },
    { key: "theta", label: "实力分 θ", num: true, fmt: (v, r) => `<b>${fix(v, 2)}</b> <small>±${fix(r.se, 2)}</small>` },
    { key: "lo", label: "95% 名次区间", fmt: (v, r) => rankBar(r) + `<small>${r.lo} – ${r.hi}</small>`, sort: (r) => r.hi - r.lo, num: true },
    { key: "plain", label: "普通 BT 名次", num: true, fmt: diff, title: "不做分档加权时的名次；箭头表示加权版相对它的变化" },
    { key: "cap50", label: "封顶版名次", num: true, title: "每组对决最多按 50 人计算的稳健性检查" },
    { key: "eff", label: "有效人次", num: true, fmt: (v) => int(v) },
  ], R, { sortKey: "rank", asc: true, filter: (r) => filt === "all" || r.type === filt });
  document.querySelectorAll("#ftabs button").forEach((b) => (b.onclick = () => {
    filt = b.dataset.f;
    document.querySelectorAll("#ftabs button").forEach((x) => x.classList.toggle("on", x === b));
    T.rerender();
  }));
  $("#q").addEventListener("input", (e) => T.search(e.target.value));

  /* ---------------- old vs new ---------------- */
  const O = C.oldnew;
  const M = Math.max(...O.map((o) => Math.max(o.old_rank, o.new_rank)));
  const changes = O.map((o) => ({ ...o, d: o.old_rank - o.new_rank }));
  const top = changes.slice().sort((a, b) => b.d - a.d);
  const lab = new Set([...top.slice(0, 5), ...top.slice(-5)].map((o) => o.school));
  ["MIT", "Harvard", "UCLA", "Pomona", "Williams"].forEach((s) => lab.add(s));
  scatter($("#scatter"), changes.map((o) => ({
    x: M + 1 - o.old_rank, y: M + 1 - o.new_rank, color: o.type === "LAC" ? "#d08a1f" : "#4b4fc4", r: 5,
    label: o.school, showLabel: lab.has(o.school),
    html: `<b>${esc(o.school)}</b><br>旧数据第 ${o.old_rank} 名 → 新数据第 ${o.new_rank} 名<br>标准分 ${fix(o.old_z)} → ${fix(o.new_z)}`,
  })), { xmin: 0, xmax: M + 1, ymin: 0, ymax: M + 1, xlab: "旧数据名次（越往右越靠前）", ylab: "新数据名次（越往上越靠前）",
    diag: true, diagLabel: "名次不变", fmtX: (v) => (v > 0 ? Math.round(M + 1 - v) : ""), fmtY: (v) => (v > 0 ? Math.round(M + 1 - v) : "") });
  const li = (o) => `<div style="display:flex;justify-content:space-between;border-bottom:1px solid #f0f0ec;padding:3px 0;font-size:.92rem">
    <span>${esc(o.school)} <small class="muted">${o.type === "LAC" ? "LAC" : ""}</small></span>
    <span class="muted">${o.old_rank} → ${o.new_rank} <span class="${o.d > 0 ? "up" : "down"}">${o.d > 0 ? "↑" + o.d : "↓" + -o.d}</span></span></div>`;
  $("#risers").innerHTML = top.slice(0, 8).map(li).join("");
  $("#fallers").innerHTML = top.slice(-8).reverse().map(li).join("");
})();
