// Client-side SVG builder mirroring server/app/tag/{renderer,layout}.py.
// Auto-fit: user enters W x H only — every font is computed to fit and
// centre its zone. No textLength anywhere (print rasters ignore it).

export const GOLD = "#8C6A2F";

const CHAR_W = { sans: 0.55, serif: 0.62 };
const MIN_FONT_MM = 0.8;

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

export const TAGLINE_TEXT = "TRUST IN EVERY CARAT";
export const TAGLINE_SPACING = 0.3;
export const L1_SPACING = 1.0;
export const L2_SPACING = 1.0;

export function fitFont(text, maxW, maxH, family = "sans", bold = false, spacing = 0) {
  if (maxW <= 0 || maxH <= 0) return MIN_FONT_MM;
  const chars = String(text ?? "").length;
  if (chars === 0) return Math.round(Math.min(maxH, 12) * 100) / 100;
  const boost = bold ? 1.06 : 1.0;
  const avail = maxW - spacing * Math.max(chars - 1, 0);
  if (avail <= 0) return MIN_FONT_MM;
  const byW = avail / (chars * (CHAR_W[family] || 0.55) * boost);
  return Math.round(Math.max(MIN_FONT_MM, Math.min(maxH, byW)) * 100) / 100;
}

export function tagLayout(widthMm, heightMm, texts, showLess = true, tailMm = 0, showGross = true, showNet = true) {
  const w = Math.max(5, Number(widthMm) || 100);
  const h = Math.max(3, Number(heightMm) || 15);
  const tail = Math.max(0, Math.min(Number(tailMm) || 0, w - 5));
  const bodyW = w - tail;
  const bodyX = 0;
  const foldX = bodyW * 0.5;

  const logoCx = foldX * 0.27;
  const logoHw = foldX * 0.24;
  const ix = foldX * 0.76;
  const iw = foldX * 0.42;
  // Item + purity share ONE font so both lines always match in size.
  const backFont =
    Math.round(Math.min(
      fitFont(texts.product, iw, h * 0.17, "sans", true),
      fitFont(texts.purity, iw, h * 0.17, "sans", true)
    ) * 100) / 100;

  const fw = bodyW - foldX;
  const fullRows = [];
  if (showGross) fullRows.push(`Gross Wt. : ${texts.gross || ""}`);
  if (showLess) fullRows.push(`Less Wt. : ${texts.less || ""}`);
  if (showNet) fullRows.push(`Net Wt. : ${texts.net || ""}`);
  const n = fullRows.length;
  const rowFont =
    Math.round(Math.min(h * 0.2, ...fullRows.map((r) => fitFont(r, fw * 0.88, h * 0.2, "sans", true))) * 100) / 100;
  const rowYs = fullRows.map((_, i) => (n > 1 ? h * (0.3 + (0.5 * i) / (n - 1)) : h * 0.55));

  return {
    w, h, bodyX, bodyW, foldX, logoCx, logoHw, ix, iw,
    tail, tailX: bodyW,
    monoFont: fitFont(texts.initial, logoHw * 2, h * 0.42, "serif", true),
    l1Font: fitFont(texts.line1, logoHw * 2, h * 0.13, "serif", false, L1_SPACING),
    l2Font: fitFont(texts.line2, logoHw * 2, h * 0.095, "sans", false, L2_SPACING),
    taglineFont: fitFont(TAGLINE_TEXT, logoHw * 2, Math.min(h * 0.062, 1.6), "sans", false, TAGLINE_SPACING),
    itemFont: backFont,
    purityFont: backFont,
    rowFont, rowYs,
    rowLabels: [
      ...(showGross ? ["Gross Wt."] : []),
      ...(showLess ? ["Less Wt."] : []),
      ...(showNet ? ["Net Wt."] : []),
    ],
    cx: foldX + fw * 0.5,
  };
}

function overflowMm(text, zoneMm, family, bold, spacing = 0) {
  const s = String(text ?? "");
  if (!s.trim()) return 0;
  const cw = CHAR_W[family] || 0.55;
  const need = s.length * cw * (bold ? 1.06 : 1.0) * MIN_FONT_MM + spacing * Math.max(s.length - 1, 0);
  return Math.round(Math.max(0, need - zoneMm) * 100) / 100;
}

// Live printability check — mirrors server layout_warnings.
export function tagWarnings(widthMm, heightMm, texts, showLess = true, tailMm = 0, showGross = true, showNet = true) {
  const lay = tagLayout(widthMm, heightMm, texts, showLess, tailMm, showGross, showNet);
  const fw = lay.bodyW - lay.foldX;
  const out = [];
  const add = (field, over, zone) => {
    if (over > 0) {
      out.push({
        field,
        overflowMm: over,
        message: `${field} overflows by ~${over} mm on a ${lay.w} x ${lay.h} mm tag — shorten it or use a wider tag, else this part will print cut (${zone}).`,
      });
    }
  };
  add("Purity / HUID", overflowMm(texts.purity, lay.iw, "sans", true), "item zone");
  add("Product name", overflowMm(texts.product, lay.iw, "sans", true), "item zone");
  add("Shop headline", overflowMm(texts.shop_l1, lay.logoHw * 2, "serif", false, L1_SPACING), "logo zone");
  add("Shop subline", overflowMm(texts.shop_l2, lay.logoHw * 2, "sans", false, L2_SPACING), "logo zone");
  add("Shop tagline", overflowMm(TAGLINE_TEXT, lay.logoHw * 2, "sans", false, TAGLINE_SPACING), "logo zone");
  const keyOf = { "Gross Wt.": "gross", "Less Wt.": "less", "Net Wt.": "net" };
  lay.rowLabels.forEach((label) => {
    const val = texts[keyOf[label]];
    if (String(val ?? "").trim()) {
      add(label, overflowMm(`${label} : ${val}`, fw * 0.88, "sans", true), "weight zone");
    }
  });
  return out;
}

export function buildTagSvg({ purity_huid, product_name, gross_weight, net_weight, shop_name = "", width_mm = 100, height_mm = 15, has_logo = false, logo_image = null, cal_x_mm = 0, cal_y_mm = 0, cal_scale = 1, cal_rotate = false, show_less = true, tail_mm = 0, show_gross = true, show_net = true, show_lines = false }) {
  const f = (n) => +n.toFixed(2);
  const { initial, line1, line2 } = brandParts(shop_name);
  const less = computeLess(gross_weight, net_weight);
  const lay = tagLayout(width_mm, height_mm, {
    purity: purity_huid, product_name,
    gross: fmt3(gross_weight), less, net: fmt3(net_weight),
    shop_l1: line1, shop_l2: line2, initial,
  }, show_less, tail_mm, show_gross, show_net);
  const { w, h, bodyW, foldX } = { w: lay.w, h: lay.h, bodyW: lay.bodyW, foldX: lay.foldX };

  // Lines: solid black = printed. Dashed gray = preview-only area guide
  // (stripped before raster, paper stays clean). Same positions either way.
  let s;
  if (show_lines) {
    s =
      `<rect x="${f(lay.bodyX)}" y="${f(h * 0.04)}" width="${f(bodyW)}" height="${f(h * 0.92)}" rx="${f(h * 0.12)}" fill="#fff" stroke="black" stroke-width="0.4"/>` +
      `<line x1="${f(foldX)}" y1="${f(h * 0.06)}" x2="${f(foldX)}" y2="${f(h * 0.94)}" stroke="black" stroke-width="0.35" stroke-dasharray="1.2 0.8"/>`;
  } else {
    s =
      `<rect x="${f(lay.bodyX)}" y="${f(h * 0.04)}" width="${f(bodyW)}" height="${f(h * 0.92)}" rx="${f(h * 0.12)}" fill="none" stroke="#94a3b8" stroke-width="0.25" stroke-dasharray="1.5 1" data-preview-only="true"/>` +
      `<line x1="${f(foldX)}" y1="${f(h * 0.06)}" x2="${f(foldX)}" y2="${f(h * 0.94)}" stroke="#94a3b8" stroke-width="0.25" stroke-dasharray="1.5 1" data-preview-only="true"/>`;
  }
  if (lay.tail > 0) {
    // Tail outline is preview-only: fold here, never print here.
    s += `<rect x="${f(lay.tailX)}" y="${f(h * 0.3)}" width="${f(lay.tail)}" height="${f(h * 0.4)}" rx="${f(h * 0.18)}" fill="none" stroke="#94a3b8" stroke-width="0.25" stroke-dasharray="1.5 1" data-preview-only="true"/>`;
  }

  // ---- BACK ----
  const logoCx = lay.logoCx;
  if (logo_image) {
    const lw = foldX * 0.5;
    const lh = h * 0.88;
    s += `<image x="${f(logoCx - lw / 2)}" y="${f(h * 0.06)}" width="${f(lw)}" height="${f(lh)}" preserveAspectRatio="xMidYMid meet" href="${logo_image}"/>`;
  } else {
    if (has_logo && initial) {
      s += `<text x="${f(logoCx)}" y="${f(h * 0.44)}" text-anchor="middle" font-family="Georgia,serif" font-size="${f(lay.monoFont)}" font-weight="bold" fill="${GOLD}">${esc(initial)}</text>`;
    }
    if (line1) {
      s += `<text x="${f(logoCx)}" y="${f(h * 0.62)}" text-anchor="middle" font-family="Georgia,serif" font-size="${f(lay.l1Font)}" font-weight="bold" letter-spacing="1" fill="${GOLD}">${esc(line1)}</text>`;
    }
    if (line2) {
      s += `<text x="${f(logoCx)}" y="${f(h * 0.75)}" text-anchor="middle" font-family="Arial,sans-serif" font-size="${f(lay.l2Font)}" letter-spacing="1.0" fill="${GOLD}">${esc(line2)}</text>`;
      s += `<text x="${f(logoCx)}" y="${f(h * 0.87)}" text-anchor="middle" font-family="Arial,sans-serif" font-size="${f(lay.taglineFont)}" letter-spacing="0.3">TRUST IN EVERY CARAT</text>`;
    }
  }
  const divLine = show_lines
    ? `<line x1="${f(foldX * 0.52)}" y1="${f(h * 0.12)}" x2="${f(foldX * 0.52)}" y2="${f(h * 0.88)}" stroke="black" stroke-width="0.35"/>`
    : `<line x1="${f(foldX * 0.52)}" y1="${f(h * 0.12)}" x2="${f(foldX * 0.52)}" y2="${f(h * 0.88)}" stroke="#94a3b8" stroke-width="0.25" stroke-dasharray="1.5 1" data-preview-only="true"/>`;
  s += divLine;

  const hasProduct = String(product_name ?? "").trim() !== "";
  const hasPurity = String(purity_huid ?? "").trim() !== "";
  if (hasProduct) {
    s += `<text x="${f(lay.ix)}" y="${f(h * 0.34)}" text-anchor="middle" font-family="Arial,sans-serif" font-size="${f(lay.itemFont)}" font-weight="bold">${esc(product_name)}</text>`;
    s += show_lines
      ? `<line x1="${f(lay.ix - lay.iw / 2)}" y1="${f(h * 0.5)}" x2="${f(lay.ix + lay.iw / 2)}" y2="${f(h * 0.5)}" stroke="${GOLD}" stroke-width="0.4"/>`
      : `<line x1="${f(lay.ix - lay.iw / 2)}" y1="${f(h * 0.5)}" x2="${f(lay.ix + lay.iw / 2)}" y2="${f(h * 0.5)}" stroke="#94a3b8" stroke-width="0.25" stroke-dasharray="1.5 1" data-preview-only="true"/>`;
  }
  if (hasPurity) {
    s += `<text x="${f(lay.ix)}" y="${f(h * 0.72)}" text-anchor="middle" font-family="Arial,sans-serif" font-size="${f(lay.purityFont)}" font-weight="bold">${esc(purity_huid)}</text>`;
  }

  // ---- FRONT ----
  const labelOf = { "Gross Wt.": fmt3(gross_weight), "Less Wt.": less, "Net Wt.": fmt3(net_weight) };
  lay.rowLabels.forEach((label, i) => {
    s += `<text x="${f(lay.cx)}" y="${f(lay.rowYs[i])}" text-anchor="middle" font-family="Arial,sans-serif" font-size="${f(lay.rowFont)}" font-weight="bold">${label} : ${esc(labelOf[label])}</text>`;
  });

  // Calibration: same transform as the server — preview and paper agree.
  const calOx = Number(cal_x_mm) || 0;
  const calOy = Number(cal_y_mm) || 0;
  const calSc = Number(cal_scale) || 1;
  const calRot = cal_rotate === true || String(cal_rotate).toLowerCase() === "1" || String(cal_rotate).toLowerCase() === "true";
  let inner = s;
  const t = [];
  if (calOx || calOy) t.push(`translate(${calOx} ${calOy})`);
  if (calSc !== 1)
    t.push(`translate(${w / 2} ${h / 2}) scale(${calSc}) translate(${-w / 2} ${-h / 2})`);
  if (calRot) t.push(`rotate(180 ${w / 2} ${h / 2})`);
  if (t.length > 0) inner = `<g transform="${t.join(" ")}">${s}</g>`;

  return (
    `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${w}mm" height="${h}mm" viewBox="0 0 ${w} ${h}" data-side="fold-tag">` +
    inner +
    `</svg>`
  );
}
