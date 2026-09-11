// Client-side SVG builder mirroring server/app/tag/renderer.py for instant preview.
// Server remains canonical for print; geometry must stay in sync.
// Fold-over tag: BACK | FOLD (dashed) | FRONT + tail with string hole.

export const GOLD = "#8C6A2F";

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function toNum(v) {
  const n = parseFloat(String(v ?? "").trim());
  return Number.isFinite(n) ? n : 0;
}

export function fmt3(v) {
  if (v === "" || v == null) return "";
  return `${toNum(v).toFixed(3)} g`;
}

export function computeLess(gross, net) {
  if (gross === "" || gross == null || net === "" || net == null) return "";
  return `${(toNum(gross) - toNum(net)).toFixed(3)} g`;
}

export function computeNet(gross, less) {
  if (gross === "" || gross == null) return "";
  const l = less === "" || less == null ? 0 : toNum(less);
  return `${(toNum(gross) - l).toFixed(3)}`;
}

export function brandParts(name) {
  const words = String(name || "").trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return { initial: "", line1: "", line2: "" };
  if (words.length === 1) return { initial: words[0][0].toUpperCase(), line1: words[0].toUpperCase(), line2: "" };
  return {
    initial: words[0][0].toUpperCase(),
    line1: words[0].toUpperCase(),
    line2: words.slice(1).join(" ").toUpperCase(),
  };
}

export function shopInitials(name) {
  const words = String(name || "").trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

function tagShell(w, h) {
  const f = (n) => +n.toFixed(2);
  const bodyW = w * 0.65;
  return (
    `<rect x="${f(w * 0.63)}" y="${f(h * 0.3)}" width="${f(w * 0.35)}" height="${f(h * 0.4)}" rx="${f(h * 0.2)}" fill="#fff" stroke="black" stroke-width="0.3"/>` +
    `<rect x="${f(w * 0.005)}" y="${f(h * 0.04)}" width="${f(bodyW)}" height="${f(h * 0.92)}" rx="${f(h * 0.12)}" fill="#fff" stroke="black" stroke-width="0.3"/>` +
    `<circle cx="${f(w * 0.945)}" cy="${f(h * 0.5)}" r="${f(h * 0.11)}" fill="#fff" stroke="black" stroke-width="0.3"/>`
  );
}

export function buildTagSvg({ purity_huid, product_name, gross_weight, net_weight, shop_name = "", width_mm = 110, height_mm = 12, has_logo = false, logo_image = null, cal_x_mm = 0, cal_y_mm = 0, cal_scale = 1 }) {
  const w = Number(width_mm) || 110;
  const h = Number(height_mm) || 12;
  const f = (n) => +n.toFixed(2);
  const bodyW = w * 0.65;
  const foldX = bodyW * 0.4;
  const { initial, line1, line2 } = brandParts(shop_name);
  const less = computeLess(gross_weight, net_weight);

  // Calibration: same transform as the server — preview and paper agree.
  const calOx = Number(cal_x_mm) || 0;
  const calOy = Number(cal_y_mm) || 0;
  const calSc = Number(cal_scale) || 1;

  let s =
    tagShell(w, h) +
    `<line x1="${f(foldX)}" y1="${f(h * 0.06)}" x2="${f(foldX)}" y2="${f(h * 0.94)}" stroke="black" stroke-width="0.3" stroke-dasharray="1.2 0.8"/>`;

  // ---- BACK ----
  const logoCx = foldX * 0.27;

  // Uploaded logo image replaces the text monogram block entirely (mirrors server).
  if (logo_image) {
    const lw = foldX * 0.48;
    const lh = h * 0.8;
    s += `<image x="${f(logoCx - lw / 2)}" y="${f(h * 0.1)}" width="${f(lw)}" height="${f(lh)}" preserveAspectRatio="xMidYMid meet" href="${logo_image}"/>`;
  } else {
    if (has_logo && initial) {
      s += `<text x="${f(logoCx)}" y="${f(h * 0.44)}" text-anchor="middle" font-family="Georgia,serif" font-size="${f(h * 0.4)}" font-weight="bold" fill="${GOLD}">${esc(initial)}</text>`;
    }
    if (line1) {
      s += `<text x="${f(logoCx)}" y="${f(h * 0.62)}" text-anchor="middle" font-family="Georgia,serif" font-size="${f(h * 0.115)}" letter-spacing="1" fill="${GOLD}">${esc(line1)}</text>`;
    }
    if (line2) {
      s += `<text x="${f(logoCx)}" y="${f(h * 0.75)}" text-anchor="middle" font-family="Arial,sans-serif" font-size="${f(h * 0.085)}" letter-spacing="1.5" textLength="${f(foldX * 0.44)}" lengthAdjust="spacingAndGlyphs" fill="${GOLD}">${esc(line2)}</text>`;
      s += `<text x="${f(logoCx)}" y="${f(h * 0.87)}" text-anchor="middle" font-family="Arial,sans-serif" font-size="${f(h * 0.06)}" letter-spacing="1">TRUST IN EVERY CARAT</text>`;
    }
  }
  s += `<line x1="${f(foldX * 0.52)}" y1="${f(h * 0.12)}" x2="${f(foldX * 0.52)}" y2="${f(h * 0.88)}" stroke="black" stroke-width="0.3"/>`;

  const ix = foldX * 0.76;
  const iw = foldX * 0.42;
  s += `<text x="${f(ix)}" y="${f(h * 0.34)}" text-anchor="middle" font-family="Arial,sans-serif" font-size="${f(h * 0.115)}" textLength="${f(iw)}" lengthAdjust="spacingAndGlyphs">ITEM - ${esc(product_name)}</text>`;
  s += `<line x1="${f(ix - iw / 2)}" y1="${f(h * 0.5)}" x2="${f(ix + iw / 2)}" y2="${f(h * 0.5)}" stroke="${GOLD}" stroke-width="0.4"/>`;
  s += `<text x="${f(ix)}" y="${f(h * 0.72)}" text-anchor="middle" font-family="Arial,sans-serif" font-size="${f(h * 0.15)}" font-weight="bold" textLength="${f(iw)}" lengthAdjust="spacingAndGlyphs">${esc(purity_huid)}</text>`;

  // ---- FRONT ----
  const fw = bodyW - foldX;
  const fs = f(h * 0.135);
  const rows = [
    ["Gross Wt.", fmt3(gross_weight), 0.3],
    ["Less Wt.", less, 0.55],
    ["Net Wt.", fmt3(net_weight), 0.8],
  ];
  for (const [label, value, yfrac] of rows) {
    const y = f(h * yfrac);
    s += `<text x="${f(foldX + fw * 0.06)}" y="${y}" font-family="Arial,sans-serif" font-size="${fs}" textLength="${f(fw * 0.38)}" lengthAdjust="spacingAndGlyphs">${label}</text>`;
    s += `<text x="${f(foldX + fw * 0.52)}" y="${y}" font-family="Arial,sans-serif" font-size="${fs}">:</text>`;
    s += `<text x="${f(foldX + fw * 0.94)}" y="${y}" text-anchor="end" font-family="Arial,sans-serif" font-size="${fs}" font-weight="bold" textLength="${f(fw * 0.36)}" lengthAdjust="spacingAndGlyphs">${esc(value)}</text>`;
  }

  let inner = s;
  const t = [];
  if (calOx || calOy) t.push(`translate(${calOx} ${calOy})`);
  if (calSc !== 1)
    t.push(`translate(${w / 2} ${h / 2}) scale(${calSc}) translate(${-w / 2} ${-h / 2})`);
  if (t.length > 0) inner = `<g transform="${t.join(" ")}">${s}</g>`;

  return (
    `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${w}mm" height="${h}mm" viewBox="0 0 ${w} ${h}" data-side="fold-tag">` +
    inner +
    `</svg>`
  );
}
