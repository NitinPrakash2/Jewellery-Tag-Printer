"""SVG tag engine — the single canonical layout for preview AND print.

Fold-over jewellery tag (one label, printed once):
  BACK SIDE  |  FOLD (dashed)  |  FRONT SIDE  + tail with string hole.

Back:  gold monogram + shop name, divider, "ITEM - {product}" + purity/HUID.
Front: Gross Wt. / Less Wt. (= gross - net) / Net Wt. rows.
Physical size comes from settings (mm); SVG uses mm units so preview
matches the real tag size. Missing logo never crashes — it is skipped.

NOTE: the LP 46 Neo is monochrome — gold renders as brand color in preview
and dithers on thermal print. Layout/positions are device-independent.
"""
import html
from decimal import Decimal, InvalidOperation

TEMPLATE_VERSION = "v3"
GOLD = "#8C6A2F"

# NEEDS HARDWARE VALIDATION: exact media size must be confirmed on the real
# LP 46 Neo + label stock. These defaults are configurable placeholders only.
DEFAULT_TAG_WIDTH_MM = 110.0
DEFAULT_TAG_HEIGHT_MM = 12.0


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


def _tag_shell(w: float, h: float) -> str:
    body_w = w * 0.65
    sw = "0.3"
    return (
        # tail (drawn first so the body overlaps its seam)
        f'<rect x="{_f(w * 0.63)}" y="{_f(h * 0.30)}" width="{_f(w * 0.35)}" '
        f'height="{_f(h * 0.40)}" rx="{_f(h * 0.20)}" fill="#fff" '
        f'stroke="black" stroke-width="{sw}"/>'
        # body
        f'<rect x="{_f(w * 0.005)}" y="{_f(h * 0.04)}" width="{_f(body_w)}" '
        f'height="{_f(h * 0.92)}" rx="{_f(h * 0.12)}" fill="#fff" '
        f'stroke="black" stroke-width="{sw}"/>'
        # string hole
        f'<circle cx="{_f(w * 0.945)}" cy="{_f(h * 0.5)}" r="{_f(h * 0.11)}" '
        f'fill="#fff" stroke="black" stroke-width="{sw}"/>'
    )


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
) -> str:
    w = float(width_mm or DEFAULT_TAG_WIDTH_MM)
    h = float(height_mm or DEFAULT_TAG_HEIGHT_MM)
    body_w = w * 0.65
    fold_x = body_w * 0.40

    initial, line1, line2 = brand_parts(shop_name)
    less = compute_less_weight(gross_weight, net_weight)

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" '
        f'viewBox="0 0 {w} {h}" data-side="fold-tag" data-template="{TEMPLATE_VERSION}">',
        _tag_shell(w, h),
        # fold line (dashed)
        f'<line x1="{_f(fold_x)}" y1="{_f(h * 0.06)}" x2="{_f(fold_x)}" '
        f'y2="{_f(h * 0.94)}" stroke="black" stroke-width="0.3" stroke-dasharray="1.2 0.8"/>',
    ]

    # ---- BACK SIDE ----
    logo_cx = fold_x * 0.27
    logo_uri = None
    if has_logo:
        from app.services.logo_service import load_data_uri

        logo_uri = load_data_uri(logo_path)
    if logo_uri:
        # Real uploaded logo replaces the text monogram block entirely.
        lw, lh = fold_x * 0.48, h * 0.80
        parts.append(
            f'<image x="{_f(logo_cx - lw / 2)}" y="{_f(h * 0.10)}" '
            f'width="{_f(lw)}" height="{_f(lh)}" '
            f'preserveAspectRatio="xMidYMid meet" href="{logo_uri}"/>'
        )
    else:
        if has_logo and initial:
            parts.append(
                f'<text x="{_f(logo_cx)}" y="{_f(h * 0.44)}" text-anchor="middle" '
                f'font-family="Georgia,serif" font-size="{_f(h * 0.40)}" '
                f'font-weight="bold" fill="{GOLD}">{_esc(initial)}</text>'
            )
        if line1:
            parts.append(
                f'<text x="{_f(logo_cx)}" y="{_f(h * 0.62)}" text-anchor="middle" '
                f'font-family="Georgia,serif" font-size="{_f(h * 0.115)}" '
                f'letter-spacing="1" fill="{GOLD}">{_esc(line1)}</text>'
            )
        if line2:
            lw = fold_x * 0.44
            parts.append(
                f'<text x="{_f(logo_cx)}" y="{_f(h * 0.75)}" text-anchor="middle" '
                f'font-family="Arial,sans-serif" font-size="{_f(h * 0.085)}" '
                f'letter-spacing="1.5" textLength="{_f(lw)}" '
                f'lengthAdjust="spacingAndGlyphs" fill="{GOLD}">{_esc(line2)}</text>'
            )
            parts.append(
                f'<text x="{_f(logo_cx)}" y="{_f(h * 0.87)}" text-anchor="middle" '
                f'font-family="Arial,sans-serif" font-size="{_f(h * 0.06)}" '
                f'letter-spacing="1">TRUST IN EVERY CARAT</text>'
            )
    # vertical divider between logo and item zones
    parts.append(
        f'<line x1="{_f(fold_x * 0.52)}" y1="{_f(h * 0.12)}" '
        f'x2="{_f(fold_x * 0.52)}" y2="{_f(h * 0.88)}" '
        f'stroke="black" stroke-width="0.3"/>'
    )
    # item zone
    ix = fold_x * 0.76
    iw = fold_x * 0.42
    parts.append(
        f'<text x="{_f(ix)}" y="{_f(h * 0.34)}" text-anchor="middle" '
        f'font-family="Arial,sans-serif" font-size="{_f(h * 0.115)}" '
        f'textLength="{_f(iw)}" lengthAdjust="spacingAndGlyphs">'
        f"ITEM - {_esc(product_name)}</text>"
    )
    parts.append(
        f'<line x1="{_f(ix - iw / 2)}" y1="{_f(h * 0.50)}" '
        f'x2="{_f(ix + iw / 2)}" y2="{_f(h * 0.50)}" '
        f'stroke="{GOLD}" stroke-width="0.4"/>'
    )
    parts.append(
        f'<text x="{_f(ix)}" y="{_f(h * 0.72)}" text-anchor="middle" '
        f'font-family="Arial,sans-serif" font-size="{_f(h * 0.15)}" '
        f'font-weight="bold" textLength="{_f(iw)}" '
        f'lengthAdjust="spacingAndGlyphs">{_esc(purity_huid)}</text>'
    )

    # ---- FRONT SIDE : weight rows ----
    fw = body_w - fold_x
    fs = _f(h * 0.135)
    rows = [
        ("Gross Wt.", _fmt3(gross_weight), 0.30),
        ("Less Wt.", _fmt3(less), 0.55),
        ("Net Wt.", _fmt3(net_weight), 0.80),
    ]
    for label, value, yfrac in rows:
        y = _f(h * yfrac)
        parts.append(
            f'<text x="{_f(fold_x + fw * 0.06)}" y="{y}" '
            f'font-family="Arial,sans-serif" font-size="{fs}" '
            f'textLength="{_f(fw * 0.38)}" lengthAdjust="spacingAndGlyphs">{label}</text>'
        )
        parts.append(
            f'<text x="{_f(fold_x + fw * 0.52)}" y="{y}" '
            f'font-family="Arial,sans-serif" font-size="{fs}">:</text>'
        )
        parts.append(
            f'<text x="{_f(fold_x + fw * 0.94)}" y="{y}" text-anchor="end" '
            f'font-family="Arial,sans-serif" font-size="{fs}" '
            f'font-weight="bold" textLength="{_f(fw * 0.36)}" '
            f'lengthAdjust="spacingAndGlyphs">{_esc(value)}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)
