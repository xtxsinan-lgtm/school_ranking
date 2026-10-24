/* Shared helpers: formatting, tables, SVG charts, tooltips and minimal chrome. */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const pct = (x, d = 1) => (x == null || isNaN(x) ? "—" : (x * 100).toFixed(d) + "%");
const fix = (x, d = 2) => (x == null || isNaN(x) ? "—" : Number(x).toFixed(d));
const sfix = (x, d = 2) => (x == null || isNaN(x) ? "—" : (Number(x) >= 0 ? "+" : "") + Number(x).toFixed(d));
const int = (x) => (x == null || isNaN(x) ? "—" : Number(x).toLocaleString("en-US"));
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const sig = (z) => 1 / (1 + Math.exp(-z));
const logit = (p) => { p = Math.min(Math.max(p, 0.01), 0.99); return Math.log(p / (1 - p)); };
const REPO = "https://github.com/xtxsinan-lgtm/school_ranking";

async function loadJSON(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(path + " " + r.status);
  return r.json();
}

/* ---------- tooltip (charts + any [data-tip]) ---------- */
const tip = document.createElement("div");
tip.className = "tip";
function showTip(html, ev) {
  tip.innerHTML = html;
  tip.classList.add("on");
  const w = tip.offsetWidth, h = tip.offsetHeight;
  let x = ev.clientX + 12, y = ev.clientY + 14;
  if (x + w > innerWidth - 10) x = ev.clientX - w - 12;
  if (y + h > innerHeight - 10) y = ev.clientY - h - 10;
  tip.style.left = x + "px"; tip.style.top = y + "px";
}
function hideTip() { tip.classList.remove("on"); }
document.addEventListener("mouseover", (e) => {
  const t = e.target.closest && e.target.closest("[data-tip]");
  if (t) showTip(t.dataset.tipHtml ? t.dataset.tip : esc(t.dataset.tip), e);
});
document.addEventListener("mousemove", (e) => {
  const t = e.target.closest && e.target.closest("[data-tip]");
  if (t) showTip(t.dataset.tipHtml ? t.dataset.tip : esc(t.dataset.tip), e);
});
document.addEventListener("mouseout", (e) => {
  if (e.target.closest && e.target.closest("[data-tip]")) hideTip();
});

/* ---------- table ---------- */
function makeTable(el, cols, data, opts = {}) {
  let sortKey = opts.sortKey || cols[0].key, asc = opts.asc ?? true, query = "";
  let activeId = opts.activeId ?? null;
  const rowId = opts.rowId || ((r, i) => i);
  el.innerHTML = `<table class="data${opts.dense ? " dense" : ""}${opts.onRowClick ? " clickable" : ""}"><thead><tr>${cols.map((c) =>
    `<th class="${c.num ? "num " : ""}${c.hideSm ? "hide-sm" : ""}" data-k="${c.key}" ${c.title ? `data-tip="${esc(c.title)}"` : ""}>${c.label}</th>`).join("")}</tr></thead><tbody></tbody></table>`;
  const tbody = $("tbody", el);
  const val = (c, r) => (c.sort ? c.sort(r) : r[c.key]);
  let curRows = [];
  function render() {
    const c = cols.find((x) => x.key === sortKey) || cols[0];
    let rows = data.filter(opts.filter || (() => true));
    if (query) {
      const q = query.toLowerCase();
      rows = rows.filter((r) => cols.some((col) => String(r[col.key] ?? "").toLowerCase().includes(q)) ||
        String(r.name || r.school || r.abbr || r.city || r.county || "").toLowerCase().includes(q));
    }
    rows.sort((a, b) => {
      const x = val(c, a), y = val(c, b);
      if (x == null || x === "") return 1;
      if (y == null || y === "") return -1;
      if (typeof x === "string") return asc ? x.localeCompare(y) : y.localeCompare(x);
      return asc ? x - y : y - x;
    });
    curRows = rows;
    tbody.innerHTML = rows.map((r, i) => {
      const id = rowId(r, i);
      const isAct = activeId != null && String(id) === String(activeId);
      return `<tr data-idx="${i}" data-id="${esc(id)}" class="${isAct ? "active-row" : ""}">${cols.map((col) =>
        `<td class="${col.num ? "num " : ""}${col.cls || ""} ${col.hideSm ? "hide-sm" : ""}">${col.fmt ? col.fmt(r[col.key], r) : esc(r[col.key] ?? "—")}</td>`).join("")}</tr>`;
    }).join("") || `<tr><td colspan="${cols.length}" class="muted" style="text-align:center;padding:20px">无匹配记录</td></tr>`;
    $$("th", el).forEach((th) => {
      th.classList.toggle("sorted", th.dataset.k === sortKey);
      th.classList.toggle("asc", th.dataset.k === sortKey && asc);
    });
    if (opts.onCount) opts.onCount(rows.length, data.filter(opts.filter || (() => true)).length);
  }
  if (opts.onRowClick) {
    tbody.addEventListener("click", (e) => {
      const tr = e.target.closest("tr[data-idx]");
      if (!tr) return;
      const r = curRows[+tr.dataset.idx];
      if (!r) return;
      activeId = tr.dataset.id;
      $$("tr.active-row", tbody).forEach((x) => x.classList.remove("active-row"));
      tr.classList.add("active-row");
      opts.onRowClick(r);
    });
  }
  $$("th", el).forEach((th) => th.addEventListener("click", () => {
    if (sortKey === th.dataset.k) asc = !asc;
    else { sortKey = th.dataset.k; asc = !cols.find((c) => c.key === sortKey).num || /rank|名次|#|原序/.test(th.textContent); }
    render();
  }));
  render();
  return {
    search(q) { query = q; render(); },
    setActive(id) { activeId = id; render(); },
    rerender: render,
  };
}

const rankBadge = (n) => (n == null ? `<span class="muted">—</span>` : `<span class="rk ${n <= 3 ? "t" + n : ""}">${n}</span>`);

function rangeBar(lo, hi, pt, max, truth) {
  const s = (v) => Math.max(0, Math.min(100, (v / max) * 100));
  return `<div class="rbar"><div class="seg2" style="left:${s(lo)}%;width:${s(hi) - s(lo)}%"></div>` +
    (truth != null ? `<div class="tru" style="left:${s(truth)}%"></div>` : "") +
    `<div class="dot" style="left:${s(pt)}%"></div></div>`;
}

/* ---------- SVG scatter ---------- */
function scatter(el, pts, o) {
  const W = o.w || 640, H = o.h || 400, m = { l: 52, r: 18, t: 14, b: 42 };
  const tf = o.log ? Math.log10 : (v) => v;
  const X = (v) => m.l + ((tf(v) - tf(o.xmin)) / (tf(o.xmax) - tf(o.xmin))) * (W - m.l - m.r);
  const Y = (v) => H - m.b - ((tf(v) - tf(o.ymin)) / (tf(o.ymax) - tf(o.ymin))) * (H - m.t - m.b);
  const lin = (a, b, n) => Array.from({ length: n + 1 }, (_, i) => a + ((b - a) * i) / n);
  const xt = o.xticks || lin(o.xmin, o.xmax, 5), yt = o.yticks || lin(o.ymin, o.ymax, 5);
  const fx = o.fmtX || ((v) => v), fy = o.fmtY || ((v) => v);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(o.xlab)} vs ${esc(o.ylab)}">`;
  s += xt.map((t) => `<line class="gl" x1="${X(t)}" x2="${X(t)}" y1="${m.t}" y2="${H - m.b}"/>`).join("");
  s += yt.map((t) => `<line class="gl" y1="${Y(t)}" y2="${Y(t)}" x1="${m.l}" x2="${W - m.r}"/>`).join("");
  s += `<rect x="${m.l}" y="${m.t}" width="${W - m.l - m.r}" height="${H - m.t - m.b}" fill="none" stroke="#dcd9d0"/>`;
  s += xt.map((t) => `<text x="${X(t)}" y="${H - m.b + 16}" text-anchor="middle">${fx(t)}</text>`).join("");
  s += yt.map((t) => `<text x="${m.l - 8}" y="${Y(t) + 4}" text-anchor="end">${fy(t)}</text>`).join("");
  s += `<text class="axt" x="${(W + m.l - m.r) / 2}" y="${H - 6}" text-anchor="middle">${o.xlab}</text>`;
  s += `<text class="axt" transform="translate(13,${(H - m.b + m.t) / 2}) rotate(-90)" text-anchor="middle">${o.ylab}</text>`;
  if (o.band) {
    const f = o.band, a = o.xmin, b = o.xmax;
    s += `<path d="M${X(a)},${Y(Math.min(a * f, o.ymax))} L${X(b / f)},${Y(o.ymax)} L${X(b)},${Y(o.ymax)} L${X(b)},${Y(b / f)} L${X(a * f)},${Y(o.ymin)} L${X(a)},${Y(o.ymin)} Z" fill="currentColor" style="color:var(--accent)" fill-opacity=".07"/>`;
  }
  if (o.diag) {
    const a = Math.max(o.xmin, o.ymin), b = Math.min(o.xmax, o.ymax);
    s += `<line x1="${X(a)}" y1="${Y(a)}" x2="${X(b)}" y2="${Y(b)}" stroke="#8c8b85" stroke-dasharray="4 4"/>`;
    s += `<text x="${W - m.r - 8}" y="${H - m.b - 8}" text-anchor="end" style="font-style:italic">${o.diagLabel || "y = x"}</text>`;
  }
  const order = pts.map((p, i) => i).sort((a, b) => (pts[b].r || 5) - (pts[a].r || 5));
  order.forEach((i) => {
    const p = pts[i];
    s += `<circle class="pt" data-i="${i}" cx="${X(p.x)}" cy="${Y(p.y)}" r="${p.r || 5}" fill="${p.color}" fill-opacity=".78" stroke="#fff" stroke-width="1.1"/>`;
  });
  const boxes = pts.map((p) => ({ x: X(p.x) - (p.r || 5), y: Y(p.y) - (p.r || 5), w: 2 * (p.r || 5), h: 2 * (p.r || 5) }));
  const hit = (b) => boxes.some((q) => b.x < q.x + q.w && b.x + b.w > q.x && b.y < q.y + q.h && b.y + b.h > q.y);
  pts.forEach((p) => {
    if (!p.showLabel) return;
    const cx = X(p.x), cy = Y(p.y), r = p.r || 5, w = [...p.label].reduce((a, ch) => a + (ch.charCodeAt(0) > 255 ? 10 : 5.8), 0), h = 11.5;
    const cands = [[cx + r + 4, cy - h / 2, "start"], [cx - r - 4 - w, cy - h / 2, "end"], [cx - w / 2, cy - r - 3 - h, "middle"], [cx - w / 2, cy + r + 3, "middle"],
      [cx + r + 2, cy - r - h, "start"], [cx + r + 2, cy + r, "start"], [cx - r - 2 - w, cy - r - h, "end"], [cx - r - 2 - w, cy + r, "end"]];
    for (const [bx, by, anchor] of cands) {
      const b = { x: bx, y: by, w, h };
      if (bx < m.l || bx + w > W - m.r + 8 || by < m.t - 4 || by + h > H - m.b) continue;
      if (hit(b)) continue;
      boxes.push(b);
      const tx = anchor === "start" ? bx : anchor === "end" ? bx + w : bx + w / 2;
      s += `<text class="lbl" x="${tx}" y="${by + h - 2.5}" text-anchor="${anchor}">${esc(p.label)}</text>`;
      break;
    }
  });
  s += `</svg>`;
  el.innerHTML = s;
  $$("circle.pt", el).forEach((c) => {
    const p = pts[+c.dataset.i], r0 = p.r || 5;
    c.addEventListener("mousemove", (e) => { showTip(p.html, e); c.setAttribute("r", r0 + 2); });
    c.addEventListener("mouseleave", () => { hideTip(); c.setAttribute("r", r0); });
  });
}

/* ---------- minimal page chrome ---------- */
function footerHTML() {
  return `<footer><div class="wrap f-inner">
    <span>数据源：UC Information Center (2021–2025) · 27 校官方升学去向表 · Parchment Cross-Admit (3,350 组)</span>
    <div class="f-links">
      <a href="./">概览</a>
      <a href="highschool.html">湾区高中排名</a>
      <a href="highschool-analysis.html">高中数据分析</a>
      <a href="college.html">美国大学排名</a>
      <a href="college-analysis.html">大学数据分析</a>
      <a href="${REPO}">GitHub 仓库</a>
    </div>
  </div></footer>`;
}

document.addEventListener("DOMContentLoaded", () => {
  document.body.appendChild(tip);
  document.body.insertAdjacentHTML("afterbegin", `<div class="progress"></div>`);
  document.body.insertAdjacentHTML("beforeend", footerHTML() + `<button class="totop" aria-label="回到顶部">↑</button>`);
  const bar = $(".progress"), top = $(".totop");
  top.onclick = () => scrollTo({ top: 0, behavior: "smooth" });

  const links = $$(".subnav a");
  const secs = links.map((a) => document.querySelector(a.getAttribute("href"))).filter(Boolean);
  function onScroll() {
    const h = document.documentElement;
    bar.style.width = (100 * h.scrollTop) / Math.max(1, h.scrollHeight - h.clientHeight) + "%";
    top.classList.toggle("on", h.scrollTop > 800);
    let cur = secs[0] || null;
    for (const s of secs) if (s.getBoundingClientRect().top < 130) cur = s;
    links.forEach((a) => a.classList.toggle("on", !!(cur && a.getAttribute("href") === "#" + cur.id)));
  }
  addEventListener("scroll", onScroll, { passive: true });
  onScroll();
});

function paintRange(inp) {
  const p = ((inp.value - inp.min) / (inp.max - inp.min)) * 100;
  inp.style.setProperty("--p", p + "%");
}
