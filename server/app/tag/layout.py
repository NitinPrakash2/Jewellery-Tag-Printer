"""Auto-fit layout engine — the maths behind every tag, shared by preview
and print so both agree pixel-for-pixel.

Why this exists: browsers honour SVG textLength (condensing text to fit),
but print rasters ignore it — so text overflowed on paper while looking
fine on screen. Auto-fit instead computes a REAL font size that fits the
zone, so no textLength hacks are needed anywhere.

Rule:  font = min(height_budget, zone_width / (chars x avg_char_width))
  - avg advance ≈ 0.55 x font-size (Arial), 0.62 x (Georgia serif)
  - user only ever enters W x H; everything else derives from it.
"""
from __future__ import annotations


CHAR_W = {"sans": 0.55, "serif": 0.62}
MIN_FONT_MM = 0.8


TAGLINE_TEXT = "TRUST IN EVERY CARAT"
TAGLINE_SPACING = 0.3
L1_SPACING = 1.0
L2_SPACING = 1.0


def fit_font(text: str, max_width_mm: float, max_height_mm: float,
             family: str = "sans", bold: bool = False,
             spacing: float = 0.0) -> float:
    """Largest font (mm) letting `text` fit inside max_width x max_height.

    `spacing` is SVG letter-spacing in mm — it adds width after (almost)
    every glyph, so the fit must budget for it too. Ignoring it was letting
    spaced headlines (shop name, tagline) spill outside the tag border.
    """
    if max_width_mm <= 0 or max_height_mm <= 0:
        return MIN_FONT_MM
    chars = len(str(text or ""))
    if chars == 0:
        return round(min(max_height_mm, 12.0), 2)
    boost = 1.06 if bold else 1.0
    avail = max_width_mm - spacing * max(chars - 1, 0)
    if avail <= 0:
        return MIN_FONT_MM
    by_width = avail / (chars * CHAR_W.get(family, 0.55) * boost)
    return round(max(MIN_FONT_MM, min(max_height_mm, by_width)), 2)


def tag_layout(width_mm: float, height_mm: float, texts: dict,
               show_less: bool = True, tail_mm: float = 0.0,
               show_gross: bool = True, show_net: bool = True) -> dict:
    """Full geometry for a fold tag. All values in mm.

    The label is width_mm wide, but only the BODY prints — the TAIL
    (e.g. 35mm of a 100mm tag) is for folding/tying and gets ZERO ink.
    texts: purity, product, gross, less, net, shop_l1, shop_l2, initial.
    show_*=False omits that row (blank input never prints).
    Returns positions, zone widths and every font size.
    """
    w = max(5.0, float(width_mm or 100.0))
    h = max(3.0, float(height_mm or 15.0))
    tail = max(0.0, min(float(tail_mm or 0.0), w - 5.0))
    body_w = w - tail
    body_x = 0.0
    fold_x = body_w * 0.50  # fold line down the middle of the printable body

    # ---- back ----
    logo_cx = fold_x * 0.27
    logo_hw = fold_x * 0.24          # half-width of logo zone
    mono = texts.get("initial", "")
    l1 = texts.get("shop_l1", "")
    l2 = texts.get("shop_l2", "")
    ix = fold_x * 0.76
    iw = fold_x * 0.42               # full width of item zone
    purity = texts.get("purity", "")
    item = str(texts.get("product", ""))
    # Item + purity share ONE font so both lines always match in size.
    # It fits the longer of the two inside the item zone (both render bold).
    back_font = min(
        fit_font(item, iw, h * 0.17, bold=True),
        fit_font(purity, iw, h * 0.17, bold=True),
    )

    # ---- front rows (single centred "Label : value" line each) ----
    # Only filled rows exist — blank inputs leave no row at all.
    fw = body_w - fold_x
    full_rows = []
    if show_gross:
        full_rows.append(f"Gross Wt. : {texts.get('gross', '')}")
    if show_less:
        full_rows.append(f"Less Wt. : {texts.get('less', '')}")
    if show_net:
        full_rows.append(f"Net Wt. : {texts.get('net', '')}")
    # Height budget raised (0.17 -> 0.20 of tag height): thermal labels need
    # chunky glyphs — thin strokes print faint and unreadable.
    row_font = min(
        [h * 0.20]
        + [fit_font(r, fw * 0.88, h * 0.20, bold=True) for r in full_rows]
    )
    n = len(full_rows)
    row_ys = [h * (0.30 + 0.50 * i / max(n - 1, 1)) if n > 1 else h * 0.55
              for i in range(n)]

    return {
        "w": w, "h": h,
        "body_x": body_x, "body_w": body_w,
        "tail": tail, "tail_x": body_w,
        "fold_x": fold_x,
        "logo_cx": logo_cx, "logo_hw": logo_hw,
        "mono_font": fit_font(mono, logo_hw * 2, h * 0.42, "serif", bold=True),
        "l1_font": fit_font(l1, logo_hw * 2, h * 0.13, "serif", spacing=L1_SPACING),
        "l2_font": fit_font(l2, logo_hw * 2, h * 0.095, spacing=L2_SPACING),
        "tagline_font": fit_font(TAGLINE_TEXT, logo_hw * 2, min(h * 0.062, 1.6),
                                 spacing=TAGLINE_SPACING),
        "ix": ix, "iw": iw,
        "back_font": round(back_font, 2),
        "item_font": round(back_font, 2),
        "purity_font": round(back_font, 2),
        "row_font": round(row_font, 2),
        "row_ys": row_ys,
        "row_labels": (
            (["Gross Wt."] if show_gross else [])
            + (["Less Wt."] if show_less else [])
            + (["Net Wt."] if show_net else [])
        ),
        "label_x": fold_x + fw * 0.06,
        "colon_x": fold_x + fw * 0.52,
        "value_x": fold_x + fw * 0.94,
    }


def _overflow_mm(text: str, zone_mm: float, family: str, bold: bool,
                 spacing: float = 0.0) -> float:
    """How many mm `text` exceeds `zone_mm` even at the minimum font.
    Zero means it fits (auto-fit shrank it safely). Letter-spacing counts —
    it adds real width after (almost) every glyph."""
    s = str(text or "")
    if not s.strip():
        return 0.0
    need = (len(s) * CHAR_W.get(family, 0.55) * (1.06 if bold else 1.0) * MIN_FONT_MM
            + spacing * max(len(s) - 1, 0))
    return round(max(0.0, need - zone_mm), 2)


def layout_warnings(width_mm: float, height_mm: float, texts: dict,
                    show_less: bool = True, tail_mm: float = 0.0) -> list[dict]:
    """Real-time printability check. Each warning names the field, how many
    mm would be cut, and the fix — for the preview panel, live as you type."""
    lay = tag_layout(width_mm, height_mm, texts, show_less, tail_mm)
    fw = lay["body_w"] - lay["fold_x"]
    out = []

    def _add(field: str, over: float, zone: str) -> None:
        if over > 0:
            out.append({
                "field": field,
                "overflow_mm": over,
                "message": (
                    f"{field} overflows by ~{over} mm on a "
                    f"{lay['w']} x {lay['h']} mm tag — shorten it or use a wider tag, "
                    f"else this part will print cut ({zone})."
                ),
            })

    _add("Purity / HUID", _overflow_mm(texts.get("purity", ""), lay["iw"], "sans", True), "item zone")
    _add("Product name", _overflow_mm(str(texts.get("product", "")), lay["iw"], "sans", True), "item zone")
    _add("Shop headline", _overflow_mm(texts.get("shop_l1", ""), lay["logo_hw"] * 2, "serif", False, L1_SPACING), "logo zone")
    _add("Shop subline", _overflow_mm(texts.get("shop_l2", ""), lay["logo_hw"] * 2, "sans", False, L2_SPACING), "logo zone")
    _add("Shop tagline", _overflow_mm(TAGLINE_TEXT, lay["logo_hw"] * 2, "sans", False, TAGLINE_SPACING), "logo zone")
    for label in lay["row_labels"]:
        key = {"Gross Wt.": "gross", "Less Wt.": "less", "Net Wt.": "net"}[label]
        val = texts.get(key, "")
        if str(val or "").strip():
            _add(label, _overflow_mm(f"{label} : {val}", fw * 0.88, "sans", True), "weight zone")
    return out
