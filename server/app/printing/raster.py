"""SVG → print bitmap at exact physical size.

The tag SVG is canonical (preview + print share it). For paper output it is
rasterized here to the printer's native resolution so millimetres on screen
equal millimetres on the label:
    pixels = round(mm x DPI / 25.4),  DPI = 203 (thermal barcode standard)
"""
import io

from PIL import Image

from app.logging_setup import log
from app.tag.units import DPI, mm_to_dots


class RasterError(Exception):
    pass


def svg_to_png_bytes(svg: str, width_mm: float, height_mm: float, dpi: int = DPI) -> bytes:
    """Render SVG to PNG bytes of exactly (width_mm, height_mm) at dpi."""
    if not svg or "<svg" not in svg:
        raise RasterError("Print data was empty. Nothing was sent.")
    try:
        from reportlab.graphics import renderPM
        from svglib.svglib import svg2rlg
    except ImportError as exc:
        raise RasterError(f"Print raster libraries are missing: {exc}")
    try:
        drawing = svg2rlg(io.BytesIO(svg.encode("utf-8")))
    except Exception as exc:
        raise RasterError(f"Could not render the tag layout: {exc}")
    try:
        png = renderPM.drawToString(drawing, fmt="PNG", dpi=dpi, bg=0xFFFFFF)
    except Exception as exc:
        raise RasterError(f"Could not rasterize the tag: {exc}")

    target = (mm_to_dots(width_mm), mm_to_dots(height_mm))
    try:
        img = Image.open(io.BytesIO(png)).convert("RGB")
    except Exception as exc:
        raise RasterError(f"Could not decode the print image: {exc}")
    if img.size != target:
        img = img.resize(target, Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="PNG")
    log.info("raster: %smm x %smm @%sdpi -> %sx%s px", width_mm, height_mm, dpi, *target)
    return out.getvalue()
