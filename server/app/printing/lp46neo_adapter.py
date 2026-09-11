"""LP 46 Neo adapter — real Windows-driver print path.

Brand-agnostic: any printer with a Windows driver works (TVS, Zebra, TSC,
...). The canonical tag SVG is rasterized to the printer's native 203 DPI
at exact millimetre size, then spooled through the Windows driver — no
guessed raw command language anywhere.

One-time setup on the shop PC (Windows Settings > Printers):
  driver installed + USB connected + exact label size in Printing
  Preferences (e.g. 110 x 12 mm). Then TEST PRINT + calibration in the app.
"""
from app.logging_setup import log
from app.printing import windows_spool
from app.printing.printer_adapter import (
    PrinterAdapter,
    PrinterInfo,
    PrinterNotFound,
    PrintJobResult,
)
from app.printing.raster import RasterError
from app.tag.units import DPI


def _names() -> list[str]:
    try:
        return windows_spool.list_printer_names()
    except Exception as exc:
        log.error("printer enumerate failed: %s", exc)
        return []


class LP46NeoAdapter(PrinterAdapter):
    """Default adapter. Despite the name it drives any Windows printer."""

    def discover_printers(self) -> list[PrinterInfo]:
        names = _names()
        try:
            default = windows_spool.default_printer_name()
        except Exception:
            default = ""
        out = [PrinterInfo(name=n, is_default=(n == default), status="ready") for n in names]
        # Known models appear as one-click setup targets even before install.
        placeholders = [
            ("TVS LP 46 Neo", ("LP 46", "LP46", "TVSE", "BPLE")),
            ("DCode DC 423 Pro", ("DCODE", "DC 423", "DC423", "DC 421", "DC421")),
            ("4BARCODE 4B-2054TG", ("4BARCODE", "4B-2054", "4B2054", "2054TG")),
        ]
        for label, patterns in placeholders:
            if not any(any(p in n.upper() for p in patterns) for n in names):
                out.append(PrinterInfo(name=f"{label} (not detected)", status="not-detected"))
        return out

    def get_status(self, printer_name: str) -> PrinterInfo:
        if not (printer_name or "").strip():
            raise PrinterNotFound("Please select a printer in Settings first.")
        if "(not detected)" in printer_name:
            return PrinterInfo(name=printer_name, status="not-detected")
        try:
            return windows_spool.printer_status(printer_name)
        except Exception as exc:
            msg = str(exc)
            if "not found" in msg:
                raise PrinterNotFound(msg)
            return PrinterInfo(name=printer_name, status=f"error:{msg[:120]}")

    def _print_bitmap(self, printer_name: str, png: bytes, copies: int) -> PrintJobResult:
        try:
            message = windows_spool.print_png(printer_name, png, copies=copies)
            return PrintJobResult(ok=True, message=message)
        except Exception as exc:
            log.error("spool failed on %s: %s", printer_name, exc)
            return PrintJobResult(ok=False, message=str(exc))

    def print_svg(self, printer_name: str, svg: str, copies: int = 1) -> PrintJobResult:
        from app.printing.raster import svg_to_png_bytes
        from app.tag.renderer import DEFAULT_TAG_HEIGHT_MM, DEFAULT_TAG_WIDTH_MM

        try:
            info = self.get_status(printer_name)
        except PrinterNotFound as exc:
            return PrintJobResult(ok=False, message=str(exc))
        if info.status == "not-detected" or info.status.startswith("offline"):
            return PrintJobResult(
                ok=False,
                message=(
                    f"'{printer_name}' is not ready ({info.status}). Install the driver, "
                    "connect USB, power on, then Refresh in Settings."
                ),
            )
        # Tag dimensions are user-configurable; raster uses the SVG's own
        # mm size so preview and paper always agree.
        w, h = _svg_mm_size(svg, DEFAULT_TAG_WIDTH_MM, DEFAULT_TAG_HEIGHT_MM)
        try:
            png = svg_to_png_bytes(svg, w, h, dpi=DPI)
        except RasterError as exc:
            return PrintJobResult(ok=False, message=str(exc))
        return self._print_bitmap(printer_name, png, copies)

    def print_test(self, printer_name: str) -> PrintJobResult:
        from app.printing.raster import svg_to_png_bytes

        try:
            info = self.get_status(printer_name)
        except PrinterNotFound as exc:
            return PrintJobResult(ok=False, message=str(exc))
        if info.status == "not-detected" or info.status.startswith("offline"):
            return PrintJobResult(
                ok=False,
                message=f"'{printer_name}' is not ready ({info.status}).",
            )
        test_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="50mm" height="25mm">'
            "<rect x='0.3' y='0.3' width='49.4' height='24.4' fill='none' "
            "stroke='black' stroke-width='0.3'/>"
            "<text x='50%' y='55%' text-anchor='middle' font-size='4'>TEST PRINT</text>"
            "</svg>"
        )
        try:
            png = svg_to_png_bytes(test_svg, 50.0, 25.0, dpi=DPI)
        except RasterError as exc:
            return PrintJobResult(ok=False, message=str(exc))
        return self._print_bitmap(printer_name, png, 1)


def _svg_mm_size(svg: str, default_w: float, default_h: float) -> tuple[float, float]:
    import re

    try:
        w = re.search(r'width="([\d.]+)mm"', svg)
        h = re.search(r'height="([\d.]+)mm"', svg)
        return float(w.group(1)) if w else default_w, float(h.group(1)) if h else default_h
    except (ValueError, AttributeError):
        return default_w, default_h


def get_adapter() -> PrinterAdapter:
    return LP46NeoAdapter()
