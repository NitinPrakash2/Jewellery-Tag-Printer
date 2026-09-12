"""Windows print spool path — works with ANY printer that has a Windows
driver installed (TVS, Zebra, TSC, Honeywell, ...). No per-brand command
language is used: the tag bitmap is drawn onto the printer device context,
so label size comes from the driver/paper settings.

Setup required once per printer (Windows Settings > Printers):
  1. Install the manufacturer's Windows driver, connect USB.
  2. Printing Preferences > set the exact label size (e.g. 110 x 12 mm).
  3. Use TEST PRINT in the app and adjust Calibration offsets if needed.
"""
import io
import os

from app.logging_setup import log
from app.printing.printer_adapter import PrinterInfo


class SpoolError(Exception):
    pass


def _ensure_win32_dlls() -> None:
    """Frozen exe: point Windows at the bundled native DLLs before import.

    PyInstaller 6 puts everything under _internal/ (NOT next to the exe),
    which Windows does not search by default — so win32ui (needs MFC) and
    pywin32 DLLs must be registered explicitly. Without this, printing
    fails on clean PCs while mysteriously working on dev machines.
    """
    import sys

    if not getattr(sys, "frozen", False):
        return
    candidates = []
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        candidates.append(os.path.join(meipass, "pywin32_system32"))
        candidates.append(meipass)  # mfc140u.dll and friends live here
    candidates.append(
        os.path.join(os.path.dirname(sys.executable), "pywin32_system32")
    )
    for cand in candidates:
        if not cand or not os.path.isdir(cand):
            continue
        try:
            os.add_dll_directory(cand)
        except Exception:
            pass
        path = os.environ.get("PATH", "")
        if cand.lower() not in path.lower():
            os.environ["PATH"] = cand + os.pathsep + path


def _win32print():
    _ensure_win32_dlls()
    try:
        import win32print
    except Exception as exc:
        raise SpoolError(
            "Windows printing libraries failed to load "
            f"({type(exc).__name__}: {str(exc)[:160]}). "
            "Reinstall the app folder completely (exe + _internal together) "
            "or install Microsoft Visual C++ Redistributable (vc_redist.x64)."
        )
    return win32print


# Virtual/software printers — useless for label printing, hidden everywhere.
VIRTUAL_PRINTERS = (
    "microsoft print to pdf",
    "microsoft xps document writer",
    "onenote",
    "fax",
    "print to file",
    "anydesk printer",
)


def is_virtual_printer(name: str) -> bool:
    lname = str(name or "").lower()
    return any(v in lname for v in VIRTUAL_PRINTERS)


def list_printer_names(include_virtual: bool = False) -> list[str]:
    win32print = _win32print()
    try:
        names = [name for _, _, name, _ in win32print.EnumPrinters(2)]
    except Exception as exc:
        raise SpoolError(f"Could not list Windows printers: {exc}")
    if include_virtual:
        return names
    return [n for n in names if not is_virtual_printer(n)]


def default_printer_name() -> str:
    win32print = _win32print()
    try:
        return win32print.GetDefaultPrinter() or ""
    except Exception:
        return ""


# win32 status flag -> human text (subset that matters to a shop operator)
_STATUS_BITS = (
    (0x00000002, "error"),
    (0x00000004, "pending deletion"),
    (0x00000010, "out of paper"),
    (0x00000020, "manual feed"),
    (0x00000040, "paper problem"),
    (0x00000080, "offline"),
    (0x00000100, "I/O active"),
    (0x00000200, "busy"),
    (0x00000400, "printing"),
    (0x00000800, "output bin full"),
    (0x00001000, "not available"),
    (0x00002000, "waiting"),
    (0x00004000, "processing"),
    (0x00008000, "warming up"),
    (0x00010000, "door open"),
    (0x00400000, "server unknown"),
    (0x01000000, "power save"),
)

_BAD = {"error", "out of paper", "paper problem", "offline", "not available", "door open"}


def printer_status(printer_name: str) -> PrinterInfo:
    win32print = _win32print()
    if not (printer_name or "").strip():
        raise SpoolError("Please select a printer in Settings first.")
    try:
        handle = win32print.OpenPrinter(printer_name)
    except Exception:
        raise SpoolError(
            f"Printer '{printer_name}' was not found. "
            "Check it is installed, connected via USB and powered on."
        )
    try:
        info = win32print.GetPrinter(handle, 2)
    except Exception as exc:
        raise SpoolError(f"Could not read printer status: {exc}")
    finally:
        try:
            win32print.ClosePrinter(handle)
        except Exception:
            pass
    flags = info.get("Status", 0) or 0
    hits = [text for bit, text in _STATUS_BITS if flags & bit]
    bad = [t for t in hits if t in _BAD]
    if bad:
        return PrinterInfo(name=printer_name, status="offline:" + ",".join(bad))
    state = ",".join(hits) if hits else "ready"
    return PrinterInfo(
        name=printer_name,
        is_default=(printer_name == default_printer_name()),
        status=state,
    )


def _fit_box(img_w: int, img_h: int, page_w: int, page_h: int) -> tuple[int, int, int, int]:
    """Centered destination rect for Dib.draw as (x0, y0, x1, y1).

    Pillow rects are corners, NOT x/y/width/height. Passing height as y1
    inverts the rect whenever the driver page differs from the image
    (e.g. default page vs 100x15 label) — and an inverted rect draws
    NOTHING: paper comes out blank. That was the blank-paper bug.
    """
    scale = min(page_w / img_w, page_h / img_h)
    w, h = max(1, int(img_w * scale)), max(1, int(img_h * scale))
    x0, y0 = (page_w - w) // 2, (page_h - h) // 2
    return x0, y0, x0 + w, y0 + h


def print_png(printer_name: str, png_bytes: bytes, copies: int = 1) -> str:
    """Spool PNG bytes to the Windows printer. Returns a success message."""
    _ensure_win32_dlls()
    try:
        import win32con
        import win32ui
        from PIL.ImageWin import Dib
    except Exception as exc:
        raise SpoolError(
            "Windows printing libraries failed to load "
            f"({type(exc).__name__}: {str(exc)[:160]}). "
            "Install Microsoft Visual C++ Redistributable (vc_redist.x64) once, "
            "or reinstall the app folder completely (exe + _internal together)."
        )
    from PIL import Image

    copies = max(1, min(int(copies or 1), 99))
    try:
        img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    except Exception as exc:
        raise SpoolError(f"Print image was unreadable: {exc}")

    try:
        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(printer_name)
    except Exception:
        raise SpoolError(
            f"Printer '{printer_name}' was not found. "
            "Check it is installed, connected via USB and powered on."
        )
    try:
        page_w = hdc.GetDeviceCaps(win32con.HORZRES)
        page_h = hdc.GetDeviceCaps(win32con.VERTRES)
        box = _fit_box(img.size[0], img.size[1], page_w, page_h)
        dib = Dib(img)
        hdc.StartDoc("Jewellery Tag")
        try:
            for _ in range(copies):
                hdc.StartPage()
                try:
                    dib.draw(hdc.GetHandleOutput(), box)
                finally:
                    hdc.EndPage()
        finally:
            hdc.EndDoc()
    except SpoolError:
        raise
    except Exception as exc:
        raise SpoolError(f"Print failed on '{printer_name}': {exc}. "
                         "Check paper/ribbon, USB cable and driver paper size.")
    finally:
        try:
            hdc.DeleteDC()
        except Exception:
            pass
    log.info("spooled %s copie(s) to %s", copies, printer_name)
    return f"Printed {copies} copie(s) on {printer_name}."


def _fmt_mm(value: float) -> str:
    s = f"{float(value):.1f}"
    return s[:-2] if s.endswith(".0") else s


def form_name_for(width_mm: float, height_mm: float) -> str:
    return f"JewelleryTag {_fmt_mm(width_mm)}x{_fmt_mm(height_mm)}mm"


def _server_handle():
    win32print = _win32print()
    try:
        return win32print.OpenPrinter(None)
    except Exception as exc:
        raise SpoolError(f"Could not open the Windows print server: {exc}")


def _needs_admin(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "access is denied" in msg or "access denied" in msg or "permission" in msg


def ensure_label_size(printer_name: str, width_mm: float, height_mm: float) -> dict:
    """One-click label setup: create the WxH mm paper form (if missing) and
    make it this printer's per-user default. Usually needs NO admin rights;
    on locked-down PCs returns needs_admin with shop-friendly guidance."""
    try:
        w, h = float(width_mm), float(height_mm)
    except (ValueError, TypeError):
        return {"ok": False, "message": "Label width/height must be numbers."}
    if not (1 <= w <= 500 and 1 <= h <= 500):
        return {"ok": False, "message": "Label size must be between 1 and 500 mm."}
    if not (printer_name or "").strip():
        return {"ok": False, "message": "Please select a printer first."}

    win32print = _win32print()
    form_name = form_name_for(w, h)

    # 1. Printer must exist.
    try:
        probe = win32print.OpenPrinter(printer_name)
        win32print.ClosePrinter(probe)
    except Exception:
        return {"ok": False,
                "message": f"Printer '{printer_name}' was not found. Install its driver first (see Driver Help)."}

    # 2. Create the paper form (AddForm works without admin on most PCs).
    srv = _server_handle()
    try:
        existing = {f.get("Name") for f in win32print.EnumForms(srv)}
        if form_name not in existing:
            win32print.AddForm(srv, {
                "Flags": 0,
                "Name": form_name,
                "Size": {"cx": int(round(w * 1000)), "cy": int(round(h * 1000))},
                "ImageableArea": {"left": 0, "top": 0,
                                  "right": int(round(w * 1000)), "bottom": int(round(h * 1000))},
            })
            log.info("created paper form %s", form_name)
    except Exception as exc:
        if _needs_admin(exc):
            return {"ok": False, "needs_admin": True, "form_name": form_name,
                    "message": "Windows blocked automatic setup. Right-click the app > 'Run as administrator' once, then try Setup again."}
        return {"ok": False, "message": f"Could not create the label size: {exc}"}
    finally:
        try:
            win32print.ClosePrinter(srv)
        except Exception:
            pass

    # 3. Make it this printer's default (per-user override, no admin).
    DMPAPER_USER = 256
    DM_FIELDS = 0x2 | 0x4 | 0x8 | 0x10000
    try:
        hp = win32print.OpenPrinter(printer_name)
    except Exception:
        return {"ok": False, "message": f"Printer '{printer_name}' was not found."}
    try:
        try:
            current = win32print.GetPrinter(hp, 9).get("pDevMode")
        except Exception:
            current = None
        if current is None:
            current = win32print.GetPrinter(hp, 2)["pDevMode"]
        current.Fields = current.Fields | DM_FIELDS
        current.PaperSize = DMPAPER_USER
        current.PaperWidth = int(round(w * 10))   # DEVMODE uses 0.1 mm
        current.PaperLength = int(round(h * 10))
        current.FormName = form_name
        win32print.SetPrinter(hp, 9, {"pDevMode": current}, 0)
    except Exception as exc:
        if _needs_admin(exc):
            return {"ok": False, "needs_admin": True, "form_name": form_name,
                    "message": "Windows blocked automatic setup. Right-click the app > 'Run as administrator' once, then try Setup again."}
        return {"ok": False, "message": f"Could not set the label size: {exc}"}
    finally:
        try:
            win32print.ClosePrinter(hp)
        except Exception:
            pass

    # 4. Verify it stuck.
    try:
        back = win32print.GetPrinter(win32print.OpenPrinter(printer_name), 9)["pDevMode"]
        if back.FormName != form_name:
            return {"ok": False, "form_name": form_name,
                    "message": f"Label size '{form_name}' was created but the driver did not keep it. Set it once in Printing Preferences."}
    except Exception:
        pass
    log.info("label size ready: %s on %s", form_name, printer_name)
    return {"ok": True, "form_name": form_name,
            "message": f"Label size {w} x {h} mm is ready on '{printer_name}'."}
