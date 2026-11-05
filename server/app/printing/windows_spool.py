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

from app.diagnostics import record
from app.logging_setup import log
from app.printing.printer_adapter import PrinterInfo
from app.tag.units import DPI


class SpoolError(Exception):
    pass


# Identifies the bitmap path in /api/health so support can prove which build
# is installed. "1-bit-dib" = direct SetDIBitsToDevice, no dithering possible.
PRINT_MODE = "1-bit-dib"


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
    """Destination rect as (x0, y0, x1, y1) — always 1:1, top-left.

    Thermal heads feed from the top edge, so the bitmap sits at (0, 0).
    Never upscale: GDI/pillow resampling is what turned crisp 1-bit text
    into the blurry dotted mess. The label size itself comes from the
    driver form (DEVMODE), not from stretching the image.
    """
    scale = min(1.0, page_w / img_w, page_h / img_h)
    w, h = max(1, int(img_w * scale)), max(1, int(img_h * scale))
    return 0, 0, w, h


def _dib_payload(img) -> bytes:
    """Bottom-up 1-bpp DIB bits for a PIL mode "1" image.

    PIL packs modes "1" rows top-down, MSB first, padded to whole bytes;
    a Windows DIB needs 4-byte aligned rows and bottom-up order.
    """
    w, h = img.size
    stride = ((w + 31) // 32) * 4
    src_stride = (w + 7) // 8
    raw = img.tobytes()
    rows = [
        raw[i * src_stride:(i + 1) * src_stride].ljust(stride, b"\x00")
        for i in range(h)
    ]
    return b"".join(reversed(rows))


def _blit_1bit(hdc_handle: int, img, x: int = 0, y: int = 0) -> None:
    """Draw a mode "1" image with SetDIBitsToDevice — no scaling, no halftone.

    Pillow's Dib.draw() goes through StretchDIBits, where the printer driver
    is free to halftone/dither the bitmap (the dotted, blurry text bug).
    Handing GDI a native 1-bit DIB means exactly one bit per printed dot:
    black stays black, white stays white, nothing to dither.
    """
    import ctypes
    from ctypes import wintypes

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    class RGBQUAD(ctypes.Structure):
        _fields_ = [
            ("rgbBlue", ctypes.c_ubyte),
            ("rgbGreen", ctypes.c_ubyte),
            ("rgbRed", ctypes.c_ubyte),
            ("rgbReserved", ctypes.c_ubyte),
        ]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", RGBQUAD * 2)]

    bits = _dib_payload(img)
    w, h = img.size

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = h       # positive: bottom-up (rows reversed above)
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 1
    bmi.bmiHeader.biCompression = 0  # BI_RGB
    # Tell the driver the bitmap is already at the printer's native 203 dpi.
    # Leaving these at 0 makes some Unidrv label drivers assume screen (96) dpi
    # and rescale the image, which is exactly what turns solid bold text into
    # a dithered/dotted mess.
    pels_per_metre = int(round(DPI / 0.0254))
    bmi.bmiHeader.biXPelsPerMeter = pels_per_metre
    bmi.bmiHeader.biYPelsPerMeter = pels_per_metre
    bmi.bmiColors[0] = RGBQUAD(0, 0, 0, 0)          # 0 -> black ink
    bmi.bmiColors[1] = RGBQUAD(255, 255, 255, 0)    # 1 -> white paper

    buf = ctypes.create_string_buffer(bits, len(bits))
    gdi32 = ctypes.windll.gdi32
    drawn = gdi32.SetDIBitsToDevice(
        wintypes.HDC(hdc_handle),
        int(x), int(y), w, h,
        0, 0, 0, h,
        ctypes.cast(buf, ctypes.c_void_p),
        ctypes.byref(bmi),
        0,  # DIB_RGB_COLORS
    )
    if not drawn:
        raise OSError("GDI rejected the 1-bit label bitmap")


def _is_blank(img) -> bool:
    """True when every pixel is white paper (nothing would be lost by cropping)."""
    if img.width == 0 or img.height == 0:
        return True
    return img.convert("L").getextrema() == (255, 255)


def print_size_message(img_w: int, img_h: int, page_w: int, page_h: int,
                       width_mm: float, height_mm: float) -> str:
    """Plain-language one-liner shown in Settings > Live Error Monitor.

    The shop can screenshot this instead of hunting for a log file, and the
    numbers say whether the driver ever had a chance to rescale the bitmap.
    """
    msg = (
        f"Print bitmap {img_w}x{img_h} dots -> driver page {page_w}x{page_h} dots, "
        f"{_fmt_mm(width_mm)}x{_fmt_mm(height_mm)} mm, 1-bit no-dither"
    )
    if page_w < img_w or page_h < img_h:
        msg += " (driver page smaller: edge clipped, NOT rescaled)"
    return msg


def print_png(printer_name: str, png_bytes: bytes, copies: int = 1,
              width_mm: float = 0.0, height_mm: float = 0.0) -> str:
    """Spool PNG bytes to the Windows printer with exact page size. Returns a success message."""
    _ensure_win32_dlls()
    try:
        import win32con
        import win32gui
        import win32ui
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
        raw_img = Image.open(io.BytesIO(png_bytes)).convert("L")
        # Pure B&W threshold: one bit per dot. Kept as mode "1" so the spooler
        # can hand the driver a 1-bpp DIB — no greys means nothing to dither.
        # Threshold 200 preserves crisp, thick, solid jet-black letter strokes.
        img = raw_img.point(lambda p: 255 if p > 200 else 0, mode="1")
    except Exception as exc:
        raise SpoolError(f"Print image was unreadable: {exc}")

    if width_mm <= 0:
        width_mm = round(img.size[0] / 203.0 * 25.4, 1)
    if height_mm <= 0:
        height_mm = round(img.size[1] / 203.0 * 25.4, 1)

    win32print = _win32print()

    # Automatically ensure Windows knows this custom form name and size
    try:
        ensure_label_size(printer_name, width_mm, height_mm)
    except Exception as exc:
        log.debug("ensure_label_size during print skipped: %s", exc)

    # Configure DEVMODE for this specific print job so the driver doesn't feed extra labels
    hdc = None
    devmode = None
    try:
        hp = win32print.OpenPrinter(printer_name)
        try:
            # Level 8 = the CURRENT USER's preferences (density, speed, media,
            # halftone...). Level 2 returns driver defaults, which silently
            # threw away the shop's printer settings on every job — a job that
            # resets density is exactly how solid text turns into a dotted one.
            try:
                devmode = win32print.GetPrinter(hp, 8).get("pDevMode")
            except Exception:
                devmode = None
            if devmode is None:
                devmode = win32print.GetPrinter(hp, 2).get("pDevMode")
        finally:
            win32print.ClosePrinter(hp)
    except Exception as exc:
        log.warning("could not read devmode for %s: %s", printer_name, exc)

    if devmode is not None:
        try:
            DMPAPER_USER = 256
            DM_FIELDS = (win32con.DM_PAPERSIZE | win32con.DM_PAPERLENGTH |
                         win32con.DM_PAPERWIDTH | win32con.DM_FORMNAME)
            devmode.Fields = devmode.Fields | DM_FIELDS
            devmode.PaperSize = DMPAPER_USER
            devmode.PaperWidth = int(round(width_mm * 10))   # tenths of a mm
            devmode.PaperLength = int(round(height_mm * 10)) # tenths of a mm
            devmode.FormName = form_name_for(width_mm, height_mm)
            # Force monochrome + no dithering. The label is already pure 1-bit,
            # so a driver halftone screen can only destroy it (the dotted print).
            # Set the value FIRST, then mark the field valid — if a driver
            # rejects the value we must not claim the field.
            try:
                devmode.DitherType = 1          # DMDITHER_NONE
                devmode.Fields = devmode.Fields | win32con.DM_DITHERTYPE
            except Exception as exc:
                log.debug("driver rejected dmDitherType: %s", exc)
            try:
                devmode.Color = 1               # DMCOLOR_MONOCHROME
                devmode.Fields = devmode.Fields | win32con.DM_COLOR
            except Exception as exc:
                log.debug("driver rejected dmColor: %s", exc)
            hdc_handle = win32gui.CreateDC("WINSPOOL", printer_name, devmode)
            if hdc_handle:
                hdc = win32ui.CreateDCFromHandle(hdc_handle)
        except Exception as exc:
            log.warning("CreateDC with custom devmode failed (%s), falling back to default DC", exc)
            hdc = None

    if hdc is None:
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
        img_w, img_h = img.size
        # Label drivers report a printable area a few dots narrower than the
        # bitmap (e.g. 779 vs 799 for a 100 mm tag). If the bitmap is handed
        # over bigger, the driver shrinks it to fit — and that 2.5% resample is
        # what puts a vertical dotted/ragged phase through some glyphs.
        # Trim the blank margin instead so driver page == bitmap, 1:1.
        if (img_w, img_h) != (page_w, page_h):
            cut_w = max(0, img_w - page_w)
            cut_h = max(0, img_h - page_h)
            if cut_w <= img_w * 0.06 and cut_h <= img_h * 0.06:
                right = img.crop((min(img_w, page_w), 0, img_w, img_h))
                bottom = img.crop((0, min(img_h, page_h), img_w, img_h))
                if _is_blank(right) and _is_blank(bottom):
                    cropped = img.crop((0, 0, min(img_w, page_w), min(img_h, page_h)))
                    log.info(
                        "cropped bitmap %sx%s -> %sx%s to match the driver page (1:1, no scaling)",
                        img_w, img_h, *cropped.size,
                    )
                    img = cropped
                    img_w, img_h = img.size
                else:
                    log.warning(
                        "driver page %sx%s is smaller and the bitmap has ink at that "
                        "edge — not cropping, the driver may clip or shrink",
                        page_w, page_h,
                    )
        msg = print_size_message(img_w, img_h, page_w, page_h, width_mm, height_mm)
        log.info(msg)
        # Also surface it in Settings > Live Error Monitor as a green info line,
        # so the shop can screenshot the exact bit/dot numbers straight from the app.
        record("PRINT", "info", msg)
        if page_w < img_w or page_h < img_h:
            log.warning(
                "driver page %sx%s px is SMALLER than the %sx%s bitmap — "
                "the label size in the printer driver does not match the tag",
                page_w, page_h, img_w, img_h,
            )
        hdc.StartDoc("Jewellery Tag")
        try:
            for _ in range(copies):
                hdc.StartPage()
                try:
                    _blit_1bit(hdc.GetHandleOutput(), img, 0, 0)
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
    log.info("spooled %s copie(s) to %s (size %sx%s mm, 1-bit no-dither)",
             copies, printer_name, width_mm, height_mm)
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
