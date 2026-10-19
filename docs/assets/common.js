/* Shared helpers: formatting, sortable/searchable tables, tiny SVG charts, tooltip. No dependencies. */
const $ = (s, el = document) => el.querySelector(s);
const pct = (x, d = 1) => (x == null || isNaN(x) ? "—" : (x * 100).toFixed(d) + "%");
const fix = (x, d = 2) => (x == null || isNaN(x) ? "—" : Number(x).toFixed(d));
const int = (x) => (x == null ? "—" : Number(x).toLocaleString("en-US"));
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const sig = (z) => 1 / (1 + Math.exp(-z));
const logit = (p) => { p = Math.min(Math.max(p, 0.01), 0.99); return Math.log(p / (1 - p)); };

async function loadJSON(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(path + " " + r.status);
  return r.json();
}

/* ---------- tooltip ---------- */
const tip = document.createElement("div");
tip.className = "tip";
document.addEventListener("DOMContentLoaded", () => document.body.appendChild(tip));
function showTip(html, ev) {
  tip.innerHTML = html;
  tip.style.opacity = 1;
  const x = Math.min(ev.clientX + 14, window.innerWidth - 300);
  tip.style.left = x + "px";
  tip.style.top = ev.clientY + 14 + "px";
}
function hideTip() { tip.style.opacity = 0; }

/* ---------- table ----------
   cols: [{key, label, num?, fmt?(v,row) -> html, cls?, sort?(row) -> value, title?}] */
function makeTable(el, cols, data, opts = {}) {
  let sortKey = opts.sortKey || cols[0].key, asc = opts.asc ?? true, query = "";
  const filter = opts.filter || (() => true);
  el.innerHTML = `<table class="data"><thead><tr>${cols.map((c) =>
    `<th class="${c.num ? "num" : ""}" data-k="${c.key}" title="${esc(c.title || "")}">${c.label}</th>`).join("")}</tr></thead><tbody></tbody></table>`;
  const tbody = $("tbody", el);
  const val = (c, r) => (c.sort ? c.sort(r) : r[c.key]);
  function render() {
    const c = cols.find((x) => x.key === sortKey);
    let rows = data.filter(filter);
    if (query) {
      const q = query.toLowerCase();
      rows = rows.filter((r) => cols.some((c) => String(r[c.key] ?? "").toLowerCase().includes(q)));
    }
    rows.sort((a, b) => {
      let x = val(c, a), y = val(c, b);
      if (x == null) return 1; if (y == null) return -1;
      if (typeof x === "string") return asc ? x.localeCompare(y) : y.localeCompare(x);
      return asc ? x - y : y - x;
    });
    tbody.innerHTML = rows.map((r) => `<tr>${cols.map((c) =>
      `<td class="${c.num ? "num " : ""}${c.cls || ""}">${c.fmt ? c.fmt(r[c.key], r) : esc(r[c.key] ?? "—")}</td>`).join("")}</tr>`).join("")
      || `<tr><td colspan="${cols.length}" class="muted">没有匹配的记录</td></tr>`;
    el.querySelectorAll("th").forEach((th) => {
      th.classList.toggle("sorted", th.dataset.k === sortKey);
      th.classList.toggle("asc", th.dataset.k === sortKey && asc);
    });
  }
  el.querySelectorAll("th").forEach((th) => th.addEventListener("click", () => {
    if (sortKey === th.dataset.k) asc = !asc; else { sortKey = th.dataset.k; asc = !cols.find((c) => c.key === sortKey).num; }
    render();
  }));
  render();
  return { search(q) { query = q; render(); }, setFilter(f) { opts.filter = f; data = data; render(); }, rerender: render,
           setData(d) { data = d; render(); } };
}

/* range bar: lo/hi/point/truth all in the same unit, scaled to [0, max] */
function rangeBar(lo, hi, pt, max, truth) {
  const s = (v) => Math.max(0, Math.min(100, (v / max) * 100));
  return `<div class="rbar"><div class="seg" style="left:${s(lo)}%;width:${s(hi) - s(lo)}%"></div>` +
    `<div class="dot" style="left:${s(pt)}%"></div>` + (truth != null ? `<div class="tru" style="left:${s(truth)}%" title="真实"></div>` : "") + `</div>`;
}

/* ---------- SVG scatter ----------
   pts: [{x, y, color, r?, label, html}] ; opts: {xmax, ymax, xlab, ylab, diag, fmtX, fmtY, w, h, labels?:Set} */
function scatter(el, pts, o) {
  const W = o.w || 640, H = o.h || 440, m = { l: 56, r: 18, t: 14, b: 46 };
  const xmin = o.xmin ?? 0, ymin = o.ymin ?? 0;
  const X = (v) => m.l + ((v - xmin) / (o.xmax - xmin)) * (W - m.l - m.r);
  const Y = (v) => H - m.b - ((v - ymin) / (o.ymax - ymin)) * (H - m.t - m.b);
  const ticks = (a, b, n) => Array.from({ length: n + 1 }, (_, i) => a + ((b - a) * i) / n);
  const fx = o.fmtX || ((v) => v), fy = o.fmtY || ((v) => v);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img">`;
  s += `<g class="grid">` + ticks(xmin, o.xmax, 5).map((t) => `<line x1="${X(t)}" x2="${X(t)}" y1="${m.t}" y2="${H - m.b}"/>`).join("") +
       ticks(ymin, o.ymax, 5).map((t) => `<line y1="${Y(t)}" y2="${Y(t)}" x1="${m.l}" x2="${W - m.r}"/>`).join("") + `</g>`;
  s += ticks(xmin, o.xmax, 5).map((t) => `<text x="${X(t)}" y="${H - m.b + 16}" text-anchor="middle">${fx(t)}</text>`).join("");
  s += ticks(ymin, o.ymax, 5).map((t) => `<text x="${m.l - 8}" y="${Y(t) + 4}" text-anchor="end">${fy(t)}</text>`).join("");
  s += `<text x="${(W + m.l) / 2}" y="${H - 6}" text-anchor="middle" style="font-weight:600">${o.xlab}</text>`;
  s += `<text transform="translate(14,${(H - m.b + m.t) / 2}) rotate(-90)" text-anchor="middle" style="font-weight:600">${o.ylab}</text>`;
  if (o.diag) {
    const e = Math.min(o.xmax, o.ymax), b = Math.max(xmin, ymin);
    s += `<line x1="${X(b)}" y1="${Y(b)}" x2="${X(e)}" y2="${Y(e)}" stroke="#9aa0ab" stroke-dasharray="5 4"/>`;
    s += `<text x="${X(e) - 4}" y="${Y(e) + 14}" text-anchor="end">${o.diagLabel || "预测 = 真实"}</text>`;
  }
  pts.forEach((p, i) => {
    s += `<circle data-i="${i}" cx="${X(p.x)}" cy="${Y(p.y)}" r="${p.r || 6}" fill="${p.color}" fill-opacity=".75" stroke="#fff" stroke-width="1.5" style="cursor:pointer"/>`;
    if (p.showLabel) s += `<text x="${X(p.x) + 8}" y="${Y(p.y) + 4}" style="fill:#1d2433">${esc(p.label)}</text>`;
  });
  s += `</svg>`;
  el.innerHTML = s;
  el.querySelectorAll("circle").forEach((c) => {
    c.addEventListener("mousemove", (e) => showTip(pts[+c.dataset.i].html, e));
    c.addEventListener("mouseleave", hideTip);
  });
}

/* highlight current section in the sub-navigation */
function wireSubnav() {
  const links = [...document.querySelectorAll(".subnav a")];
  const secs = links.map((a) => document.querySelector(a.getAttribute("href"))).filter(Boolean);
  const on = () => {
    let cur = secs[0];
    for (const s of secs) if (s.getBoundingClientRect().top < 120) cur = s;
    links.forEach((a) => (a.style.color = cur && a.getAttribute("href") === "#" + cur.id ? "var(--accent)" : ""));
  };
  window.addEventListener("scroll", on, { passive: true });
  on();
}
document.addEventListener("DOMContentLoaded", wireSubnav);
