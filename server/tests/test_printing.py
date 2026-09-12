"""Real printing-path tests: raster dimensions + adapter failure honesty."""
import io

from PIL import Image

from app.printing.lp46neo_adapter import LP46NeoAdapter
from app.printing.printer_adapter import PrinterNotFound
from app.printing.raster import RasterError, svg_to_png_bytes
from app.tag.renderer import build_tag_svg


def _tag():
    return build_tag_svg("18Kt HUID", "Ring", "2.146", "2.146",
                         width_mm=110, height_mm=12,
                         shop_name="Manish Ornaments", has_logo=False)


def test_raster_exact_size_110x12():
    png = svg_to_png_bytes(_tag(), 110, 12)
    img = Image.open(io.BytesIO(png))
    assert img.size == (879, 96)  # 110mm x 12mm @ 203dpi


def test_raster_has_content():
    png = svg_to_png_bytes(_tag(), 110, 12)
    img = Image.open(io.BytesIO(png)).convert("L")
    dark = sum(1 for px in img.tobytes() if px < 128)
    assert dark > 100  # tag borders + text actually rendered


def test_raster_empty_raises():
    try:
        svg_to_png_bytes("", 110, 12)
        raise AssertionError("should have raised")
    except RasterError as exc:
        assert "empty" in str(exc).lower()


def test_raster_no_ink_on_tail():
    """The 35mm tail is fold-only: its pixels must stay paper-white."""
    from app.tag.units import mm_to_dots

    svg = build_tag_svg("18Kt HUID", "Ring", "2.146", "2.146",
                        width_mm=100, height_mm=15, tail_mm=35,
                        shop_name="Manish Ornaments", has_logo=False)
    png = svg_to_png_bytes(svg, 100, 15)
    img = Image.open(io.BytesIO(png)).convert("L")
    assert img.size == (mm_to_dots(100), mm_to_dots(15))
    body_px = mm_to_dots(65)
    # +4px margin: the body border itself sits on the boundary (its ink may
    # antialias ~3px over). Correct — but no content may print beyond it.
    tail_px = [px for x in range(body_px + 4, img.size[0])
               for px in [img.getpixel((x, y)) for y in range(img.size[1])]]
    assert min(tail_px) > 250, "tail zone must be blank paper"
    body_px_vals = [img.getpixel((x, y)) for x in range(body_px)
                    for y in range(img.size[1])]
    assert sum(1 for px in body_px_vals if px < 128) > 100


def test_raster_uses_only_standard_fonts():
    """Frozen builds have no system-font discovery — raster input must only
    name reportlab standard fonts (regression test for the frozen
    'NoneType has no attribute encode' crash)."""
    import re

    from app.printing.raster import _normalize_fonts

    svg = build_tag_svg("18Kt HUID", "Ring", "2.146", "2.146",
                        width_mm=100, height_mm=15, tail_mm=35,
                        shop_name="Manish Ornaments", has_logo=True,
                        logo_path="nonexistent.png")
    fams = set(re.findall(r'font-family="([^"]+)"', _normalize_fonts(svg)))
    assert fams <= {"Helvetica", "Times-Roman"}, fams


def test_fit_box_is_corners_not_size():
    # Dib.draw wants (x0, y0, x1, y1). A height-as-y1 rect inverts whenever
    # the driver page differs from the label — printing BLANK paper.
    from app.printing.windows_spool import _fit_box

    x0, y0, x1, y1 = _fit_box(799, 120, 800, 600)
    assert (x0, y0, x1, y1) == (0, 240, 800, 360)
    assert x1 > x0 and y1 > y0
    x0, y0, x1, y1 = _fit_box(799, 120, 799, 120)
    assert (x0, y0, x1, y1) == (0, 0, 799, 120)


def test_adapter_unknown_printer_returns_failure_not_raise():
    res = LP46NeoAdapter().print_svg("No Such Printer XYZ", _tag(), copies=1)
    assert res.ok is False
    assert "not found" in res.message.lower()


def test_adapter_blank_printer_name():
    try:
        LP46NeoAdapter().get_status("")
        raise AssertionError("should have raised")
    except PrinterNotFound:
        pass


def test_adapter_test_print_unknown():
    res = LP46NeoAdapter().print_test("No Such Printer XYZ")
    assert res.ok is False


def test_discover_lists_placeholders():
    names = [p.name for p in LP46NeoAdapter().discover_printers()]
    assert "TVS LP 46 Neo (not detected)" in names
    assert "DCode DC 423 Pro (not detected)" in names
    assert "4BARCODE 4B-2054TG (not detected)" in names


def test_discover_hides_virtual_printers():
    names = [p.name for p in LP46NeoAdapter().discover_printers()]
    assert not any("Print to PDF" in n or "OneNote" in n for n in names)
