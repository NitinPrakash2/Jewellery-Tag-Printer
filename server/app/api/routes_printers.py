"""Printer discovery/status/test-print routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.printing.lp46neo_adapter import get_adapter
from app.printing.printer_adapter import PrinterNotFound
from app.services import settings_service

router = APIRouter(prefix="/api/printers", tags=["printers"])


# (name patterns, max print width mm) — matched case-insensitively.
PRINTER_LIMITS: list[tuple[tuple[str, ...], int]] = [
    (("dcode", "dc 423", "dc423", "dc 421", "dc421"), 104),
    (("tvs", "lp 46", "lp46"), 108),
]


def max_print_width_mm(printer_name: str) -> int | None:
    lname = str(printer_name or "").lower()
    for patterns, width in PRINTER_LIMITS:
        if any(p in lname for p in patterns):
            return width
    return None


@router.get("", response_model=dict)
def list_printers():
    printers = get_adapter().discover_printers()
    return {"printers": [p.__dict__ for p in printers]}


@router.get("/status", response_model=dict)
def printer_status(name: str = "", db: Session = Depends(get_db)):
    target = name.strip() or settings_service.get_category(db, "printer").get("selected", "")
    limit = max_print_width_mm(target)
    try:
        info = get_adapter().get_status(target)
        out = {"ok": True, "printer": info.__dict__}
    except PrinterNotFound as exc:
        out = {"ok": False, "message": str(exc), "printer": {"name": target, "status": "not-found"}}
    out["max_print_width_mm"] = limit
    return out


@router.post("/test", response_model=dict)
def test_print(payload: dict, db: Session = Depends(get_db)):
    target = str((payload or {}).get("printer_name", "") or "").strip()
    if not target:
        target = settings_service.get_category(db, "printer").get("selected", "")
    if not target:
        return {"ok": False, "message": "Please select a printer in Settings first."}
    res = get_adapter().print_test(target)
    return {"ok": res.ok, "message": res.message}


DRIVER_HELP = {
    "tvs_lp46neo": {
        "name": "TVS LP 46 Neo",
        "match": ["tvs", "lp 46", "lp46"],
        "download_url": "https://www.tvselectronics.in/product-support",
        "steps": [
            "Connect the printer via USB, switch it on, and keep internet on — Windows usually installs its driver automatically (plug-and-play).",
            "Check Windows Settings → Printers: if 'TVS LP 46 Neo' appears, you are done — come back and press Refresh.",
            "If not, use the driver CD from the printer box, or get it from the official TVS page (choose Label Printers → LP 46 Neo).",
        ],
    },
    "dcode_dc423pro": {
        "name": "DCode DC 423 Pro",
        "match": ["dcode", "dc 423", "dc423", "dc 421", "dc421"],
        "download_url": "https://www.dcodeinternational.in/support.php",
        "note": "Max print width is 104 mm — keep the total tag width at 104 mm or less (e.g. 100 x 12 mm) or the right edge will be cut off.",
        "steps": [
            "Download the Windows driver from the official DCode support page (or use the CD in the printer box).",
            "Run the installer, connect the printer via USB when asked, and finish the setup.",
            "Back in this app, press Refresh and select your printer below.",
        ],
    },
}


@router.get("/driver-help", response_model=dict)
def driver_help():
    return {"drivers": DRIVER_HELP}


@router.get("/usb-live", response_model=dict)
def usb_live(printer_name: str = ""):
    """Live USB detection: what printer is plugged in right now, which model
    it looks like, and whether its driver is installed. Polled by the UI."""
    from app.printing import usb_detect

    return usb_detect.live_status(printer_name.strip())


@router.post("/setup", response_model=dict)
def setup_printer(payload: dict, db: Session = Depends(get_db)):
    """One-click setup: detect printer -> create label size -> make it default.

    Returns shop-friendly steps so a non-technical user just presses one button.
    """
    from app.printing import windows_spool

    data = payload or {}
    target = str(data.get("printer_name", "") or "").strip()
    if not target:
        target = settings_service.get_category(db, "printer").get("selected", "")
    tag = settings_service.get_category(db, "tag")
    try:
        w = float(data.get("width_mm", tag.get("width_mm", 110.0)))
        h = float(data.get("height_mm", tag.get("height_mm", 12.0)))
    except (ValueError, TypeError):
        return {"ok": False, "steps": [], "message": "Label size must be numbers."}
    if not target:
        return {"ok": False, "steps": [], "message": "Please select a printer first."}

    steps: list[dict] = []

    # Step 1: printer detected?
    try:
        info = get_adapter().get_status(target)
        detected = info.status != "not-detected" and info.status != "not-found"
    except PrinterNotFound as exc:
        return {"ok": False, "steps": [{
            "key": "detect", "ok": False,
            "message": str(exc) + " Install the driver (see Driver Help), then Refresh."}],
            "message": "Printer not found."}
    steps.append({"key": "detect", "ok": bool(detected),
                  "message": f"Printer '{target}' found." if detected
                  else f"Printer '{target}' is not responding. Power it on and check USB."})
    if not detected:
        return {"ok": False, "steps": steps, "message": steps[-1]["message"]}

    # Step 2: label size (automatic, no Windows Settings needed).
    size = windows_spool.ensure_label_size(target, w, h)
    steps.append({"key": "label_size", "ok": bool(size.get("ok")),
                  "needs_admin": bool(size.get("needs_admin", False)),
                  "form_name": size.get("form_name", ""),
                  "message": size.get("message", "")})
    if not size.get("ok"):
        return {"ok": False, "steps": steps, "message": size.get("message", "")}

    # Step 3: readiness from live status.
    try:
        live = get_adapter().get_status(target)
        ready = not live.status.startswith("offline") and not live.status.startswith("error")
        steps.append({"key": "ready", "ok": bool(ready),
                      "message": "Printer is ready. Run a Test Print." if ready
                      else f"Printer reports: {live.status}. Check paper and power."})
    except PrinterNotFound as exc:
        steps.append({"key": "ready", "ok": False, "message": str(exc)})
        return {"ok": False, "steps": steps, "message": str(exc)}

    return {"ok": all(s["ok"] for s in steps), "steps": steps,
            "form_name": size.get("form_name", ""),
            "message": "Setup complete. Run a Test Print to confirm." if all(s["ok"] for s in steps)
            else "Setup finished with warnings — see steps."}
