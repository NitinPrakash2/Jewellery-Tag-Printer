"""Settings routes: shop / printer / tag / calibration / app."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services import settings_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=dict)
def get_all(db: Session = Depends(get_db)):
    return settings_service.get_all_merged(db)


@router.get("/{category}", response_model=dict)
def get_category(category: str, db: Session = Depends(get_db)):
    try:
        return settings_service.get_category(db, category)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown settings category.")


@router.put("/{category}", response_model=dict)
def update_category(category: str, payload: dict, db: Session = Depends(get_db)):
    try:
        return settings_service.update_category(db, category, payload or {})
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown settings category.")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
