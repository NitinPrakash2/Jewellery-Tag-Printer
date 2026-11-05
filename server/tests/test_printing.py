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
    # SetDIBitsToDevice wants a top-left 1:1 rect: thermal heads feed from
    # the top, and any stretch is what produced the dotted/blurry print.
    from app.printing.windows_spool import _fit_box

    assert _fit_box(799, 120, 800, 600) == (0, 0, 799, 120)
    assert _fit_box(799, 120, 799, 120) == (0, 0, 799, 120)
    # Never upscale ...
    assert _fit_box(799, 120, 2032, 1216) == (0, 0, 799, 120)
    # ... but still shrink proportionally if the driver page is tiny.
    assert _fit_box(1000, 200, 500, 500) == (0, 0, 500, 100)


def test_dib_payload_is_bottom_up_and_padded():
    # A Windows 1-bpp DIB is bottom-up with 4-byte aligned rows. Sending
    # top-down/unpadded bits shifts the whole label by a few pixels.
    from PIL import Image

    from app.printing.windows_spool import _dib_payload

    img = Image.new("1", (8, 2), 0)      # black
    img.paste(255, (0, 0, 8, 1))         # top row white
    bits = _dib_payload(img)
    assert len(bits) == 8                # 2 rows x 4-byte stride
    assert bits[0:4] == b"\x00\x00\x00\x00"   # bottom (black) row first
    assert bits[4:8] == b"\xff\x00\x00\x00"   # then the white top row
    # 799 px wide -> stride 100 bytes (799/8 = 99.875 -> 100)
    assert len(_dib_payload(Image.new("1", (799, 120), 0))) == 12000


def test_print_size_message_is_shown_in_monitor():
    # The shop screenshots Settings > Live Error Monitor, so the size line
    # must be readable there and must include the exact dot counts.
    from app.printing.windows_spool import print_size_message

    msg = print_size_message(799, 120, 799, 120, 100, 15)
    assert "799x120" in msg
    assert "100x15 mm" in msg
    assert "no-dither" in msg
    assert "clipped" not in msg

    smaller = print_size_message(799, 120, 790, 112, 100, 15)
    assert "790x112" in smaller
    assert "NOT rescaled" in smaller


def test_blit_declares_native_203dpi(monkeypatch):
    # Unidrv label drivers rescale a DIB whose biXPelsPerMeter is 0 (they assume
    # screen dpi) — that halftones solid text into dots. The header must say
    # 203 dpi so the driver maps one bitmap pixel to one printed dot.
    import ctypes

    from PIL import Image

    from app.printing import windows_spool as ws

    seen = {}

    class FakeGdi:
        def SetDIBitsToDevice(self, *args):
            bmi = args[10]._obj
            seen["bitcount"] = bmi.bmiHeader.biBitCount
            seen["xppm"] = bmi.bmiHeader.biXPelsPerMeter
            seen["yppm"] = bmi.bmiHeader.biYPelsPerMeter
            seen["height"] = bmi.bmiHeader.biHeight
            return 1

    class FakeWindll:
        gdi32 = FakeGdi()

    monkeypatch.setattr(ctypes, "windll", FakeWindll())
    ws._blit_1bit(0, Image.new("1", (8, 2), 0))

    assert seen["bitcount"] == 1
    assert seen["height"] == 2                  # bottom-up DIB, positive height
    assert seen["xppm"] == 7992 and seen["yppm"] == 7992   # 203 dpi


def test_raster_supersamples_for_smooth_curves():
    # Direct 203 dpi rendering made G/S/0/8 curves look like broken ink on the
    # thermal head; the raster must be rendered larger and downscaled smoothly.
    from app.printing import raster

    assert raster.SUPERSAMPLE >= 2


def test_crop_never_throws_away_ink():
    # The 799 -> 779 trim is only allowed on blank margin. If the driver page
    # were genuinely narrower than the content, cropping would silently cut text.
    from PIL import Image

    from app.printing.windows_spool import _is_blank

    assert _is_blank(Image.new("1", (3, 3), 255))
    assert _is_blank(Image.new("1", (0, 0), 255))       # empty crop is "nothing lost"
    inked = Image.new("1", (3, 3), 255)
    inked.putpixel((2, 1), 0)
    assert not _is_blank(inked)


def test_test_tag_svg_has_solid_black_bar():
    # The Test Print must contain a solid bar: if that bar prints dotted, the
    # driver/printer is halftoning and the app cannot fix it from inside.
    from app.printing.lp46neo_adapter import _test_tag_svg

    svg = _test_tag_svg(100, 15)
    assert 'width="100mm" height="15mm"' in svg
    assert "fill='black'" in svg
    assert "TEST PRINT" in svg


def test_print_records_size_line_in_live_monitor(monkeypatch):
    """print_png must push the dot/page sizes into the app event feed.

    The shop is non-technical: it screenshots Settings > Live Error Monitor
    instead of digging through _internal/logs/app.log.
    """
    import sys
    import types

    from app.printing import windows_spool as ws
    from app.printing.raster import svg_to_png_bytes

    recorded = []
    blitted = {}
    monkeypatch.setattr(ws, "record", lambda src, lvl, msg: recorded.append((src, lvl, msg)))
    monkeypatch.setattr(ws, "_ensure_win32_dlls", lambda: None)
    monkeypatch.setattr(ws, "ensure_label_size", lambda *a, **k: {"ok": True})
    monkeypatch.setattr(
        ws, "_blit_1bit",
        lambda hdc, img, x=0, y=0: blitted.setdefault("size", img.size),
    )
    monkeypatch.setattr(
        ws, "_win32print",
        lambda: types.SimpleNamespace(
            OpenPrinter=lambda name: (_ for _ in ()).throw(RuntimeError("stub"))
        ),
    )

    hdc = types.SimpleNamespace(
        GetDeviceCaps=lambda cap: 779 if cap == 8 else 120,
        CreatePrinterDC=lambda name: None,
        StartDoc=lambda *a: None,
        StartPage=lambda *a: None,
        EndPage=lambda *a: None,
        EndDoc=lambda *a: None,
        GetHandleOutput=lambda: 1,
        DeleteDC=lambda: None,
    )
    fake_ui = types.SimpleNamespace(CreateDC=lambda: hdc)
    fake_con = types.SimpleNamespace(HORZRES=8, VERTRES=4)
    monkeypatch.setitem(sys.modules, "win32con", fake_con)
    monkeypatch.setitem(sys.modules, "win32gui", types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, "win32ui", fake_ui)

    png = svg_to_png_bytes(
        build_tag_svg("18Kt HUID", "Ring", "2.146", "2.146", width_mm=100,
                      height_mm=15, tail_mm=35, shop_name="Manish Ornaments",
                      has_logo=False),
        100, 15,
    )
    ws.print_png("Fake Printer", png, copies=1, width_mm=100, height_mm=15)

    assert recorded, "print did not reach the Live Error Monitor"
    src, lvl, msg = recorded[0]
    assert (src, lvl) == ("PRINT", "info")
    assert "779x120" in msg and "100x15 mm" in msg and "no-dither" in msg
    # 799-wide bitmap on a 779-wide driver page: the blank margin is cropped so
    # the driver gets an exact 1:1 bitmap instead of shrinking it (dotted text).
    assert "clipped" not in msg
    assert blitted["size"] == (779, 120)


def test_threshold_output_is_pure_1bit():
    # The spooler must hand GDI a mode "1" image: any grey lets the driver
    # halftone it into the dotted print the shop complained about.
    import io

    from PIL import Image

    from app.printing.raster import svg_to_png_bytes

    png = svg_to_png_bytes(_tag(), 100, 15)
    img = Image.open(io.BytesIO(png)).convert("L").point(
        lambda p: 255 if p > 200 else 0, mode="1"
    )
    assert img.mode == "1"
    assert set(img.convert("L").getdata()) == {0, 255}


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
