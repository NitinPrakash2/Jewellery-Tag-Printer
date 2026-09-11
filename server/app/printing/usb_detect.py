"""Live USB printer detection — the moment a barcode printer is plugged in
via USB, the app knows a device arrived, identifies the likely model, and
tells whether its Windows driver is installed yet.

How it works: Windows lists a driver-less printer as a generic USB device
("USB Printing Support" / printer-class USB). We watch for those via WMI
and match names against known models. Nothing to install, no admin needed.
"""
import re

from app.logging_setup import log

PRINTER_CLASS_GUID = "{4d36e979-e325-11ce-bfc1-08002be10318}"

# (driver key, name patterns) — first match wins.
MODEL_MATCH: list[tuple[str, tuple[str, ...]]] = [
    ("tvs_lp46neo", ("tvs", "lp 46", "lp46", "snbc")),
    ("dcode_dc423pro", ("dcode", "dc 423", "dc423", "dc 421", "dc421")),
    ("fourbarcode_4b2054tg", ("4barcode", "4b-2054", "4b2054", "2054tg")),
    ("zebra", ("zebra", "gx420", "gk420", "zd420", "zd410")),
    ("tsc", ("tsc", "te200", "te210", "ttp-244", "ttp244", "dae")),
    ("honeywell", ("honeywell", "intermec", "pc42", "pc43")),
]

_NAME_SIGNALS = ("print", "label", "pos", "barcode", "receipt", "zebra",
                 "tsc", "tvs", "dcode", "honeywell", "intermec", "snbc")


def _wmi():
    # Uvicorn serves requests on worker threads where COM is not
    # initialized — WMI fails there without this (CoInitialize error).
    try:
        import pythoncom

        try:
            pythoncom.CoInitialize()
        except Exception:
            pass
    except ImportError:
        pass
    try:
        from app.printing.windows_spool import _ensure_win32_dlls

        _ensure_win32_dlls()
    except Exception:
        pass
    try:
        import wmi
    except ImportError:
        return None
    try:
        return wmi.WMI()
    except Exception as exc:
        log.error("WMI unavailable: %s", exc)
        return None


def _vid_pid(device_id: str) -> tuple[str, str]:
    m = re.search(r"VID_([0-9A-Fa-f]{4}).*?PID_([0-9A-Fa-f]{4})", device_id or "")
    if m:
        return m.group(1).upper(), m.group(2).upper()
    return "", ""


def _looks_like_printer(name: str, device_id: str, class_guid: str) -> bool:
    lname = (name or "").lower()
    did = (device_id or "").upper()
    if (class_guid or "").lower() == PRINTER_CLASS_GUID:
        return True
    if "CLASS_07" in did or "USBPRINT" in did:
        return True
    # Word boundaries: "pos" must not match "composite",
    # but "print" still matches "printing"/"printer".
    return any(re.search(r"\b" + re.escape(s) + r"\w*\b", lname) for s in _NAME_SIGNALS)


def list_usb_printer_devices() -> list[dict]:
    """USB-bus devices that look like printers (driver or not)."""
    c = _wmi()
    if c is None:
        raise RuntimeError("USB detection is unavailable on this machine.")
    out = []
    try:
        devices = c.Win32_PnPEntity()
    except Exception as exc:
        raise RuntimeError(f"Could not read USB devices: {exc}")
    for d in devices:
        pid = getattr(d, "PNPDeviceID", "") or ""
        if not pid.upper().startswith("USB"):
            continue
        name = getattr(d, "Name", "") or ""
        guid = getattr(d, "ClassGuid", "") or ""
        if not _looks_like_printer(name, pid, guid):
            continue
        vid, pidv = _vid_pid(pid)
        out.append({
            "name": name,
            "device_id": pid[:120],
            "vid": vid,
            "pid": pidv,
            "status": getattr(d, "Status", "") or "",
        })
    return out


def identify_model(name: str, device_id: str = "") -> str | None:
    hay = f"{name or ''} {device_id or ''}".lower()
    for key, patterns in MODEL_MATCH:
        if any(p in hay for p in patterns):
            return key
    return None


def live_status(printer_name: str = "") -> dict:
    """Facts for the live panel. Never raises — degrades to available=False."""
    try:
        from app.printing import windows_spool
        installed = windows_spool.list_printer_names()
    except Exception:
        installed = []
    try:
        usb_devices = list_usb_printer_devices()
    except Exception as exc:
        return {"available": False, "message": str(exc),
                "usb_devices": [], "installed": installed,
                "detected_model": None, "driver_key": None,
                "driver_installed": False}
    for dev in usb_devices:
        dev["driver_key"] = identify_model(dev["name"], dev["device_id"])
    detected = usb_devices[0] if usb_devices else None
    driver_key = (detected or {}).get("driver_key")
    # Driver counts as installed ONLY when an installed Windows printer
    # actually matches the detected USB device (or the selected printer).
    # A different printer (e.g. EPSON inkjet) must NOT mark it installed.
    driver_installed = False
    if detected:
        if driver_key:
            from app.api.routes_printers import DRIVER_HELP

            patterns = DRIVER_HELP.get(driver_key, {}).get("match", [])
            driver_installed = any(
                p in n.lower() for n in installed for p in patterns
            )
        if not driver_installed:
            # Fallback: Windows queue usually carries the USB model name.
            dtokens = {t for t in re.split(r"[^a-z0-9]+", detected.get("name", "").lower()) if len(t) > 3}
            for n in installed:
                ntokens = set(re.split(r"[^a-z0-9]+", n.lower()))
                if dtokens & ntokens:
                    driver_installed = True
                    break
    elif printer_name and installed:
        pl = printer_name.lower()
        driver_installed = any(pl in n.lower() or n.lower() in pl for n in installed)
    return {"available": True, "usb_devices": usb_devices, "installed": installed,
            "detected_model": (detected or {}).get("name"),
            "driver_key": driver_key, "driver_installed": driver_installed}
