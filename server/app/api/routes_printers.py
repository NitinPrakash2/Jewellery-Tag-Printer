"""Printer discovery/status/test-print routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.printing.lp46neo_adapter import get_adapter
from app.printing.printer_adapter import PrinterNotFound
from app.services import settings_service

router = APIRouter(prefix="/api/printers", tags=["printers"])


@router.get("", response_model=dict)
def list_printers():
    printers = get_adapter().discover_printers()
    return {"printers": [p.__dict__ for p in printers]}


@router.get("/status", response_model=dict)
def printer_status(name: str = "", db: Session = Depends(get_db)):
    target = name.strip() or settings_service.get_category(db, "printer").get("selected", "")
    try:
        info = get_adapter().get_status(target)
        return {"ok": True, "printer": info.__dict__}
    except PrinterNotFound as exc:
        return {"ok": False, "message": str(exc), "printer": {"name": target, "status": "not-found"}}


@router.post("/test", response_model=dict)
def test_print(payload: dict, db: Session = Depends(get_db)):
    target = str((payload or {}).get("printer_name", "") or "").strip()
    if not target:
        target = settings_service.get_category(db, "printer").get("selected", "")
    if not target:
        return {"ok": False, "message": "Please select a printer in Settings first."}
    res = get_adapter().print_test(target)
    return {"ok": res.ok, "message": res.message}
