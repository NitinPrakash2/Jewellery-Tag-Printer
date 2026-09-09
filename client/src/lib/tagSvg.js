// Client-side SVG builder mirroring server/app/tag/renderer.py for instant preview.
// Server remains canonical for print; geometry must stay in sync.

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmtWeight(v) {
  if (v === "" || v == null) return "";
  return `${String(v).trim()} g`;
}

// Jewellery tag shape: rounded body + narrow tail with string hole.
function tagShell(w, h) {
  const f = (n) => +n.toFixed(2);
  return (
    `<rect x="${f(w * 0.56)}" y="${f(h * 0.32)}" width="${f(w * 0.4)}" height="${f(h * 0.36)}" rx="${f(h * 0.18)}" fill="#fff" stroke="black" stroke-width="0.35"/>` +
    `<rect x="${f(w * 0.02)}" y="${f(h * 0.04)}" width="${f(w * 0.6)}" height="${f(h * 0.92)}" rx="${f(h * 0.14)}" fill="#fff" stroke="black" stroke-width="0.35"/>` +
    `<circle cx="${f(w * 0.925)}" cy="${f(h * 0.5)}" r="${f(h * 0.09)}" fill="#fff" stroke="black" stroke-width="0.3"/>`
  );
}

export function buildFrontSvg({ purity_huid, product_name, gross_weight, net_weight, monogram = "", width_mm = 50, height_mm = 25, has_logo = false }) {
  const w = Number(width_mm) || 50;
  const h = Number(height_mm) || 25;
  const f = (n) => +n.toFixed(2);
  const branded = Boolean(has_logo && monogram);
  const tx = f(w * (branded ? 0.225 : 0.06));
  const tw = f(w * (branded ? 0.375 : 0.52));
  const logo = branded
    ? `<text x="${f(w * 0.05)}" y="${f(h * 0.62)}" font-family="Georgia,serif" font-size="${f(h * 0.26)}" font-weight="bold" font-style="italic">${esc(monogram)}</text>`
    : "";
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" width="${w}mm" height="${h}mm" viewBox="0 0 ${w} ${h}" data-side="front">` +
    tagShell(w, h) +
    logo +
    `<text x="${tx}" y="${f(h * 0.32)}" font-family="Arial,sans-serif" font-size="${f(h * 0.13)}" font-weight="bold" textLength="${tw}" lengthAdjust="spacingAndGlyphs">${esc(purity_huid)}</text>` +
    `<text x="${tx}" y="${f(h * 0.505)}" font-family="Arial,sans-serif" font-size="${f(h * 0.1)}" textLength="${tw}" lengthAdjust="spacingAndGlyphs">Name<tspan dx="4">:</tspan><tspan dx="4">${esc(product_name)}</tspan></text>` +
    `<text x="${tx}" y="${f(h * 0.675)}" font-family="Arial,sans-serif" font-size="${f(h * 0.1)}" textLength="${tw}" lengthAdjust="spacingAndGlyphs">G.Wt.<tspan dx="4">:</tspan><tspan dx="4">${esc(fmtWeight(gross_weight))}</tspan></text>` +
    `<text x="${tx}" y="${f(h * 0.845)}" font-family="Arial,sans-serif" font-size="${f(h * 0.1)}" textLength="${tw}" lengthAdjust="spacingAndGlyphs">N.Wt.<tspan dx="4">:</tspan><tspan dx="4">${esc(fmtWeight(net_weight))}</tspan></text>` +
    `</svg>`
  );
}

export function backOrnament(w, h) {
  const f = (n) => +n.toFixed(2);
  const y = f(h * 0.68);
  const cx = f(w * 0.32);
  const r = f(h * 0.035);
  return (
    `<line x1="${f(w * 0.12)}" y1="${y}" x2="${f(w * 0.27)}" y2="${y}" stroke="black" stroke-width="0.35"/>` +
    `<line x1="${f(w * 0.37)}" y1="${y}" x2="${f(w * 0.52)}" y2="${y}" stroke="black" stroke-width="0.35"/>` +
    `<circle cx="${f(w * 0.295)}" cy="${y}" r="${f(h * 0.012)}" fill="black"/>` +
    `<circle cx="${f(w * 0.345)}" cy="${y}" r="${f(h * 0.012)}" fill="black"/>` +
    `<polygon points="${cx},${f(h * 0.60)} ${f(w * 0.32 + h * 0.045)},${y} ${cx},${f(h * 0.76)} ${f(w * 0.32 - h * 0.045)},${y}" fill="black"/>` +
    `<circle cx="${cx}" cy="${f(h * 0.545)}" r="${r}" fill="none" stroke="black" stroke-width="0.25"/>`
  );
}

export function buildBackSvg({ shop_name, width_mm = 50, height_mm = 25 }) {
  const w = Number(width_mm) || 50;
  const h = Number(height_mm) || 25;
  const f = (n) => +n.toFixed(2);
  const long = String(shop_name || "").length > 14;
  const nameAttrs = long ? ` textLength="${f(w * 0.5)}" lengthAdjust="spacingAndGlyphs"` : "";
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" width="${w}mm" height="${h}mm" viewBox="0 0 ${w} ${h}" data-side="back">` +
    tagShell(w, h) +
    `<text x="${f(w * 0.32)}" y="${f(h * 0.46)}" text-anchor="middle" font-family="Arial,sans-serif" font-size="${f(h * 0.15)}" font-weight="bold"${nameAttrs}>${esc(shop_name)}</text>` +
    backOrnament(w, h) +
    `</svg>`
  );
}

export function shopInitials(name) {
  const words = String(name || "").trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}
