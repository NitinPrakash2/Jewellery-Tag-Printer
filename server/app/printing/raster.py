"""SVG → print bitmap at exact physical size.

The tag SVG is canonical (preview + print share it). For paper output it is
rasterized here to the printer's native resolution so millimetres on screen
equal millimetres on the label:
    pixels = round(mm x DPI / 25.4),  DPI = 203 (thermal barcode standard)
"""
import io
import os
import re
import sys

from PIL import Image

# Top-level imports ON PURPOSE: reportlab loads its raster backend
# dynamically, which frozen builds (PyInstaller) cannot see. Static
# imports here guarantee rlPyCairo + cairo ship inside the .exe.
import cairo  # noqa: F401  (pycairo — native engine under rlPyCairo)
import rlPyCairo  # noqa: F401 (reportlab renderPM backend, loaded by name)
from reportlab.graphics import renderPM
from svglib.svglib import svg2rlg

from app.logging_setup import log
from app.tag.units import DPI, mm_to_dots


class RasterError(Exception):
    pass


def strip_preview_only(svg: str) -> str:
    """Remove preview-only helpers (e.g. the dashed tail outline) so they
    NEVER reach paper. Preview shows them; print does not."""
    return re.sub(r"<[^>]*data-preview-only=\"true\"[^>]*/?>", "", svg)


def _normalize_fonts(svg: str) -> str:
    """Map every font-family to a reportlab STANDARD font.

    Standard fonts (Helvetica/Times-*) are always registered — no system
    font discovery involved. Discovery (Arial/Georgia lookup) behaves
    differently frozen vs dev and once produced an unresolvable font that
    crashed rasterizing with `'NoneType' has no attribute 'encode'`.
    Glyph shapes at 2-3mm thermal sizes are effectively identical.
    """
    out = re.sub(r'font-family="Georgia,serif"', 'font-family="Times-Roman"', svg)
    out = re.sub(r'font-family="Arial,sans-serif"', 'font-family="Helvetica"', out)
    return out


def _ensure_font_files() -> None:
    """Make reportlab's standard Type-1 fonts findable when frozen.

    The raster backend resolves font FILES (Helvetica → _a______.pfb)
    through rl_config.T1SearchPath. PyInstaller never ships that data dir,
    so on a frozen exe the lookup returns None and rasterizing crashes.
    """
    try:
        from reportlab import rl_config
    except ImportError:
        return
    candidates: list[str] = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            candidates.append(os.path.join(meipass, "reportlab", "fonts"))
    try:
        import reportlab

        candidates.append(os.path.join(os.path.dirname(reportlab.__file__), "fonts"))
    except ImportError:
        pass
    for directory in candidates:
        try:
            if os.path.isdir(directory) and directory not in rl_config.T1SearchPath:
                rl_config.T1SearchPath.append(directory)
        except Exception:
            pass


def svg_to_png_bytes(svg: str, width_mm: float, height_mm: float, dpi: int = DPI) -> bytes:
    """Render SVG to PNG bytes of exactly (width_mm, height_mm) at dpi."""
    if not svg or "<svg" not in svg:
        raise RasterError("Print data was empty. Nothing was sent.")
    svg = strip_preview_only(svg)
    svg = _normalize_fonts(svg)
    _ensure_font_files()
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
