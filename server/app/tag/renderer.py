"""SVG tag engine — the single canonical layout for preview AND print.

Body-only fold-over jewellery tag (one label, printed once):
  BACK SIDE  |  FOLD (dashed)  |  FRONT SIDE.   (No tail — body fills W.)

Back:  logo image (or gold monogram + shop name), divider,
       "ITEM - {product}" + purity/HUID.
Front: Gross Wt. / Less Wt. (= gross - net) / Net Wt. rows.
Sizes: the user enters W x H only — app/tag/layout.py auto-fits every
font so text is centred and never overflows, on screen AND on paper.
Physical size comes from settings (mm); SVG uses mm units.
Missing logo never crashes — monogram/text fallback is used.

NOTE: the LP 46 Neo is monochrome — gold renders as brand color in preview
and dithers on thermal print. Layout/positions are device-independent.
"""
import html
from decimal import Decimal, InvalidOperation

from app.tag.layout import tag_layout

TEMPLATE_VERSION = "v5"
GOLD = "#8C6A2F"

# NEEDS HARDWARE VALIDATION: exact media size must be confirmed on the real
# printer + label stock. These defaults are configurable placeholders only.
DEFAULT_TAG_WIDTH_MM = 100.0
DEFAULT_TAG_HEIGHT_MM = 15.0
DEFAULT_TAIL_MM = 35.0


def _esc(text) -> str:
    return html.escape(str(text or ""), quote=True)


def _f(n: float) -> str:
    s = f"{float(n):.2f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def _to_decimal(value) -> Decimal:
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        return Decimal("0")


def _fmt3(value) -> str:
    return f"{_to_decimal(value):.3f} g"


def compute_less_weight(gross_weight, net_weight) -> Decimal:
    return _to_decimal(gross_weight) - _to_decimal(net_weight)


def brand_parts(shop_name: str) -> tuple[str, str, str]:
    """(monogram initial, headline, subline) derived from the shop name."""
    words = str(shop_name or "").strip().split()
    if not words:
        return "", "", ""
    initial = words[0][0].upper()
    if len(words) == 1:
        return initial, words[0].upper(), ""
    return initial, words[0].upper(), " ".join(words[1:]).upper()


def build_tag_svg(
    purity_huid: str,
    product_name: str,
    gross_weight,
    net_weight,
    width_mm: float = DEFAULT_TAG_WIDTH_MM,
    height_mm: float = DEFAULT_TAG_HEIGHT_MM,
    shop_name: str = "",
    has_logo: bool = False,
    logo_path: str = "",
    show_less: bool = True,
    tail_mm: float = DEFAULT_TAIL_MM,
    show_gross: bool = True,
    show_net: bool = True,
) -> str:
    w = float(width_mm or DEFAULT_TAG_WIDTH_MM)
    h = float(height_mm or DEFAULT_TAG_HEIGHT_MM)
    initial, line1, line2 = brand_parts(shop_name)
    less = compute_less_weight(gross_weight, net_weight)

    lay = tag_layout(w, h, {
        "purity": purity_huid, "product": product_name,
        "gross": _fmt3(gross_weight),
        "less": _fmt3(less),
        "net": _fmt3(net_weight),
        "shop_l1": line1, "shop_l2": line2, "initial": initial,
    }, show_less=show_less, tail_mm=tail_mm,
       show_gross=show_gross, show_net=show_net)
    bw, fx = lay["body_w"], lay["fold_x"]

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" '
        f'viewBox="0 0 {w} {h}" data-side="fold-tag" data-template="{TEMPLATE_VERSION}">',
        # printable body only — the tail gets ZERO ink (fold only)
        f'<rect x="{_f(lay["body_x"])}" y="{_f(h * 0.04)}" width="{_f(bw)}" '
        f'height="{_f(h * 0.92)}" rx="{_f(h * 0.12)}" fill="#fff" '
        f'stroke="black" stroke-width="0.4"/>',
        # fold line (dashed)
        f'<line x1="{_f(fx)}" y1="{_f(h * 0.06)}" x2="{_f(fx)}" '
        f'y2="{_f(h * 0.94)}" stroke="black" stroke-width="0.35" stroke-dasharray="1.2 0.8"/>',
    ]
    if lay["tail"] > 0:
        # Tail outline is PREVIEW ONLY (stripped before raster/print).
        parts.append(
            f'<rect x="{_f(lay["tail_x"])}" y="{_f(h * 0.30)}" '
            f'width="{_f(lay["tail"])}" height="{_f(h * 0.40)}" '
            f'rx="{_f(h * 0.18)}" fill="none" stroke="#94a3b8" '
            f'stroke-width="0.25" stroke-dasharray="1.5 1" data-preview-only="true"/>'
        )

    # ---- BACK SIDE ----
    logo_cx = lay["logo_cx"]
    logo_uri = None
    if has_logo:
        from app.services.logo_service import load_data_uri

        logo_uri = load_data_uri(logo_path)
    if logo_uri:
        # Real uploaded logo fills the logo zone (aspect kept, never stretched).
        lw, lh = fx * 0.50, h * 0.88
        parts.append(
            f'<image x="{_f(logo_cx - lw / 2)}" y="{_f(h * 0.06)}" '
            f'width="{_f(lw)}" height="{_f(lh)}" '
            f'preserveAspectRatio="xMidYMid meet" href="{logo_uri}"/>'
        )
    else:
        if has_logo and initial:
            parts.append(
                f'<text x="{_f(logo_cx)}" y="{_f(h * 0.44)}" text-anchor="middle" '
                f'font-family="Georgia,serif" font-size="{_f(lay["mono_font"])}" '
                f'font-weight="bold" fill="{GOLD}">{_esc(initial)}</text>'
            )
        if line1:
            parts.append(
                f'<text x="{_f(logo_cx)}" y="{_f(h * 0.62)}" text-anchor="middle" '
                f'font-family="Georgia,serif" font-size="{_f(lay["l1_font"])}" '
                f'font-weight="bold" letter-spacing="1" fill="{GOLD}">{_esc(line1)}</text>'
            )
        if line2:
            parts.append(
                f'<text x="{_f(logo_cx)}" y="{_f(h * 0.75)}" text-anchor="middle" '
                f'font-family="Arial,sans-serif" font-size="{_f(lay["l2_font"])}" '
                f'letter-spacing="1.5" fill="{GOLD}">{_esc(line2)}</text>'
            )
            parts.append(
                f'<text x="{_f(logo_cx)}" y="{_f(h * 0.87)}" text-anchor="middle" '
                f'font-family="Arial,sans-serif" font-size="{_f(lay["tagline_font"])}" '
                f'letter-spacing="1">TRUST IN EVERY CARAT</text>'
            )
    # vertical divider between logo and item zones
    parts.append(
        f'<line x1="{_f(fx * 0.52)}" y1="{_f(h * 0.12)}" '
        f'x2="{_f(fx * 0.52)}" y2="{_f(h * 0.88)}" '
        f'stroke="black" stroke-width="0.35"/>'
    )
    # item zone — hidden entirely when the product is blank
    if str(product_name or "").strip():
        parts.append(
            f'<text x="{_f(lay["ix"])}" y="{_f(h * 0.34)}" text-anchor="middle" '
            f'font-family="Arial,sans-serif" font-size="{_f(lay["item_font"])}" '
            f'font-weight="bold">'
            f"ITEM - {_esc(product_name)}</text>"
        )
        parts.append(
            f'<line x1="{_f(lay["ix"] - lay["iw"] / 2)}" y1="{_f(h * 0.50)}" '
            f'x2="{_f(lay["ix"] + lay["iw"] / 2)}" y2="{_f(h * 0.50)}" '
            f'stroke="{GOLD}" stroke-width="0.4"/>'
        )
    if str(purity_huid or "").strip():
        parts.append(
            f'<text x="{_f(lay["ix"])}" y="{_f(h * 0.72)}" text-anchor="middle" '
            f'font-family="Arial,sans-serif" font-size="{_f(lay["purity_font"])}" '
            f'font-weight="bold">{_esc(purity_huid)}</text>'
        )

    # ---- FRONT SIDE : weight rows (single centred line each) ----
    values = {"Gross Wt.": _fmt3(gross_weight), "Less Wt.": _fmt3(less),
              "Net Wt.": _fmt3(net_weight)}
    cx = (lay["label_x"] + lay["value_x"]) / 2.0
    for (label, yfrac) in zip(lay["row_labels"], lay["row_ys"]):
        value = values[label]
        parts.append(
            f'<text x="{_f(cx)}" y="{_f(yfrac)}" text-anchor="middle" '
            f'font-family="Arial,sans-serif" font-size="{_f(lay["row_font"])}" '
            f'font-weight="bold">'
            f"{label} : {_esc(value)}</text>"
        )

    parts.append("</svg>")
    return "".join(parts)
