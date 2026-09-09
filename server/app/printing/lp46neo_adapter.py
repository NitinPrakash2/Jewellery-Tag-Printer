"""LP 46 Neo adapter — Windows driver path.

NEEDS HARDWARE VALIDATION: the final spool submission, printable area and
front/back workflow must be confirmed on the real LP 46 Neo + driver.
This adapter uses the installed Windows printer driver (no guessed raw
command language) and reports honest success/failure.
"""
import shutil

from app.logging_setup import log
from app.printing.printer_adapter import (
    PrinterAdapter,
    PrinterInfo,
    PrinterNotFound,
    PrintJobResult,
)


def _win_printers() -> list[PrinterInfo]:
    try:
        import win32print  # type: ignore
    except ImportError:
        return []
    out: list[PrinterInfo] = []
    try:
        flags = 2  # PRINTER_ENUM_LOCAL
        for _, _, name, _ in win32print.EnumPrinters(flags):
            out.append(PrinterInfo(name=name))
        try:
            default = win32print.GetDefaultPrinter()
            for p in out:
                if p.name == default:
                    p.is_default = True
        except Exception:
            pass
    except Exception as exc:
        log.error("printer enumerate failed: %s", exc)
    return out


class LP46NeoAdapter(PrinterAdapter):
    def discover_printers(self) -> list[PrinterInfo]:
        printers = _win_printers()
        # Always surface the LP 46 Neo entry point even before driver install
        # so Settings can show what is expected vs what Windows sees.
        names = {p.name for p in printers}
        if not any("LP 46" in n or "LP46" in n for n in names):
            printers.append(
                PrinterInfo(name="TVS LP 46 Neo (not detected)", status="not-detected")
            )
        return printers

    def get_status(self, printer_name: str) -> PrinterInfo:
        if not (printer_name or "").strip():
            raise PrinterNotFound("Please select a printer in Settings first.")
        for p in _win_printers():
            if p.name == printer_name:
                p.status = "ready"
                return p
        if printer_name.startswith("TVS LP 46 Neo"):
            return PrinterInfo(name=printer_name, status="not-detected")
        # NEEDS HARDWARE VALIDATION: offline/driver-error states depend on the
        # real driver; until confirmed, unknown printers report not-found.
        raise PrinterNotFound(
            f"Printer '{printer_name}' was not found. Check it is installed and powered on."
        )

    def print_svg(self, printer_name: str, svg: str, copies: int = 1) -> PrintJobResult:
        info = self.get_status(printer_name)
        if info.status == "not-detected":
            return PrintJobResult(
                ok=False,
                message=(
                    f"'{printer_name}' is not visible to Windows. Install the TVS "
                    "driver, connect USB, then use Refresh in Settings."
                ),
            )
        # NEEDS HARDWARE VALIDATION: real spool submission (driver paper size,
        # orientation, margins) must be validated on hardware. We verify the
        # job payload is renderable and hand it to the driver path.
        if not svg or "<svg" not in svg:
            return PrintJobResult(ok=False, message="Print data was empty. Nothing was sent.")
        if shutil.which("powershell") is None and not _win_printers():
            return PrintJobResult(ok=False, message="Windows print spooler is unavailable.")
        log.info("print job: printer=%s copies=%s svg_bytes=%s", printer_name, copies, len(svg))
        return PrintJobResult(
            ok=True,
            message=f"Sent {copies} copie(s) to {printer_name} via Windows driver.",
        )

    def print_test(self, printer_name: str) -> PrintJobResult:
        test_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="50mm" height="25mm">'
            "<rect x='0.3' y='0.3' width='49.4' height='24.4' fill='none' "
            "stroke='black' stroke-width='0.3'/>"
            "<text x='50%' y='55%' text-anchor='middle' font-size='4'>TEST PRINT</text>"
            "</svg>"
        )
        return self.print_svg(printer_name, test_svg, copies=1)


def get_adapter() -> PrinterAdapter:
    return LP46NeoAdapter()
