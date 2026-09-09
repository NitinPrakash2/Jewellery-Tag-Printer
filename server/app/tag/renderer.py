"""SVG tag engine — the single canonical layout for preview AND print.

Jewellery-tag shape: rounded body + narrow tail with string hole.
Front: monogram/logo, purity/HUID, Name / G.Wt / N.Wt rows.
Back: shop name + ornament divider.
Physical size comes from settings (mm); SVG uses mm units so preview
matches the real tag size. Missing logo never crashes — it is skipped.
"""
import html
from decimal import Decimal

TEMPLATE_VERSION = "v2"

# NEEDS HARDWARE VALIDATION: exact media size must be confirmed on the real
# LP 46 Neo + label stock. These defaults are configurable placeholders only.
DEFAULT_TAG_WIDTH_MM = 50.0
DEFAULT_TAG_HEIGHT_MM = 25.0


def _fmt_weight(value) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        return ""
    d = Decimal(str(value).strip())
    s = format(d.normalize(), "f") if d == d.to_integral_value() else format(d, "f")
    return f"{s} g"


def _esc(text) -> str:
    return html.escape(str(text or ""), quote=True)


def _f(n: float) -> str:
    s = f"{float(n):.2f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def shop_initials(name: str) -> str:
    words = str(name or "").strip().split()
    if not words:
        return ""
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


def _tag_shell(w: float, h: float) -> str:
    return (
        f'<rect x="{_f(w * 0.56)}" y="{_f(h * 0.32)}" width="{_f(w * 0.4)}" '
        f'height="{_f(h * 0.36)}" rx="{_f(h * 0.18)}" fill="#fff" '
        f'stroke="black" stroke-width="0.35"/>'
        f'<rect x="{_f(w * 0.02)}" y="{_f(h * 0.04)}" width="{_f(w * 0.6)}" '
        f'height="{_f(h * 0.92)}" rx="{_f(h * 0.14)}" fill="#fff" '
        f'stroke="black" stroke-width="0.35"/>'
        f'<circle cx="{_f(w * 0.925)}" cy="{_f(h * 0.5)}" r="{_f(h * 0.09)}" '
        f'fill="#fff" stroke="black" stroke-width="0.3"/>'
    )


def build_front_svg(
    purity_huid: str,
    product_name: str,
    gross_weight,
    net_weight,
    width_mm: float = DEFAULT_TAG_WIDTH_MM,
    height_mm: float = DEFAULT_TAG_HEIGHT_MM,
    has_logo: bool = False,
    monogram: str = "",
) -> str:
    w = float(width_mm or DEFAULT_TAG_WIDTH_MM)
    h = float(height_mm or DEFAULT_TAG_HEIGHT_MM)
    branded = bool(has_logo and monogram)
    tx, tw = _f(w * (0.225 if branded else 0.06)), _f(w * (0.375 if branded else 0.52))
    logo = ""
    if branded:
        logo = (
            f'<text x="{_f(w * 0.05)}" y="{_f(h * 0.62)}" '
            f'font-family="Georgia,serif" font-size="{_f(h * 0.26)}" '
            f'font-weight="bold" font-style="italic">{_esc(monogram)}</text>'
        )
    fs_big, fs_row = _f(h * 0.13), _f(h * 0.10)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" '
        f'viewBox="0 0 {w} {h}" data-side="front" data-template="{TEMPLATE_VERSION}">'
        f"{_tag_shell(w, h)}"
        f"{logo}"
        f'<text x="{tx}" y="{_f(h * 0.32)}" font-family="Arial,sans-serif" '
        f'font-size="{fs_big}" font-weight="bold" textLength="{tw}" '
        f'lengthAdjust="spacingAndGlyphs">{_esc(purity_huid)}</text>'
        f'<text x="{tx}" y="{_f(h * 0.505)}" font-family="Arial,sans-serif" '
        f'font-size="{fs_row}" textLength="{tw}" lengthAdjust="spacingAndGlyphs">'
        f"Name : {_esc(product_name)}</text>"
        f'<text x="{tx}" y="{_f(h * 0.675)}" font-family="Arial,sans-serif" '
        f'font-size="{fs_row}" textLength="{tw}" lengthAdjust="spacingAndGlyphs">'
        f"G.Wt. : {_esc(_fmt_weight(gross_weight))}</text>"
        f'<text x="{tx}" y="{_f(h * 0.845)}" font-family="Arial,sans-serif" '
        f'font-size="{fs_row}" textLength="{tw}" lengthAdjust="spacingAndGlyphs">'
        f"N.Wt. : {_esc(_fmt_weight(net_weight))}</text>"
        "</svg>"
    )


def _back_ornament(w: float, h: float) -> str:
    y = _f(h * 0.68)
    cx = _f(w * 0.32)
    return (
        f'<line x1="{_f(w * 0.12)}" y1="{y}" x2="{_f(w * 0.27)}" y2="{y}" '
        f'stroke="black" stroke-width="0.35"/>'
        f'<line x1="{_f(w * 0.37)}" y1="{y}" x2="{_f(w * 0.52)}" y2="{y}" '
        f'stroke="black" stroke-width="0.35"/>'
        f'<circle cx="{_f(w * 0.295)}" cy="{y}" r="{_f(h * 0.012)}" fill="black"/>'
        f'<circle cx="{_f(w * 0.345)}" cy="{y}" r="{_f(h * 0.012)}" fill="black"/>'
        f'<polygon points="{cx},{_f(h * 0.60)} {_f(w * 0.32 + h * 0.045)},{y} '
        f'{cx},{_f(h * 0.76)} {_f(w * 0.32 - h * 0.045)},{y}" fill="black"/>'
    )


def build_back_svg(
    shop_name: str,
    width_mm: float = DEFAULT_TAG_WIDTH_MM,
    height_mm: float = DEFAULT_TAG_HEIGHT_MM,
) -> str:
    w = float(width_mm or DEFAULT_TAG_WIDTH_MM)
    h = float(height_mm or DEFAULT_TAG_HEIGHT_MM)
    long_name = f' textLength="{_f(w * 0.5)}" lengthAdjust="spacingAndGlyphs"' if len(str(shop_name or "")) > 14 else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" '
        f'viewBox="0 0 {w} {h}" data-side="back" data-template="{TEMPLATE_VERSION}">'
        f"{_tag_shell(w, h)}"
        f'<text x="{_f(w * 0.32)}" y="{_f(h * 0.46)}" text-anchor="middle" '
        f'font-family="Arial,sans-serif" font-size="{_f(h * 0.15)}" '
        f'font-weight="bold"{long_name}>{_esc(shop_name or "")}</text>'
        f"{_back_ornament(w, h)}"
        "</svg>"
    )
