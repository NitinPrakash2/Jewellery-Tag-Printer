"""History routes: list/search, detail, reprint (new row, never overwrite)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.repositories import history_repo
from app.database.session import get_db
from app.domain.schemas import HistoryOut
from app.services import history_service, print_service
from app.printing.lp46neo_adapter import get_adapter

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=dict)
def list_history(
    q: str = Query(default=""),
    purity: str = Query(default=""),
    preset: str = Query(default=""),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    status: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    rows, total = history_service.list_history(
        db, q=q, purity=purity, preset=preset, date_from=date_from,
        date_to=date_to, status=status, limit=limit, offset=offset,
    )
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [HistoryOut.model_validate(r).model_dump(mode="json") for r in rows],
    }


@router.get("/{history_id}", response_model=dict)
def get_one(history_id: int, db: Session = Depends(get_db)):
    row = history_repo.get_by_id(db, history_id)
    if row is None:
        raise HTTPException(status_code=404, detail="History entry not found.")
    return HistoryOut.model_validate(row).model_dump(mode="json")


@router.post("/{history_id}/reprint", response_model=dict)
def reprint(history_id: int, db: Session = Depends(get_db)):
    row = history_repo.get_by_id(db, history_id)
    if row is None:
        raise HTTPException(status_code=404, detail="History entry not found.")
    cleaned = {
        "purity_huid": row.purity_huid,
        "product_name": row.product_name,
        "gross_weight": row.gross_weight,
        "net_weight": row.net_weight,
        "copies": row.copies,
        "printer_name": row.printer_name,
    }
    result = print_service.execute_print(db, get_adapter(), cleaned)
    status_code = 200 if result["ok"] else 502
    return {"status_code": status_code, **result}
