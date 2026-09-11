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
