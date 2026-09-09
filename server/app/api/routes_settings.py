"""Settings routes: shop / printer / tag / calibration / app + shop logo."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services import logo_service, settings_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=dict)
def get_all(db: Session = Depends(get_db)):
    return settings_service.get_all_merged(db)


# NOTE: logo routes must stay above /{category} so they are not swallowed.
@router.post("/logo", response_model=dict)
async def upload_logo(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    path, err = logo_service.save_upload(file.filename or "", content)
    if err:
        raise HTTPException(status_code=422, detail=err)
    settings_service.update_category(db, "shop", {"logo_path": path})
    return {"ok": True, "logo_path": path}


@router.get("/logo", response_model=dict)
def get_logo(db: Session = Depends(get_db)):
    stored = settings_service.get_category(db, "shop").get("logo_path", "")
    uri = logo_service.load_data_uri(stored) or logo_service.load_data_uri(
        logo_service.current_logo_path()
    )
    return {"ok": True, "logo_path": stored, "data_uri": uri}


@router.delete("/logo", response_model=dict)
def remove_logo(db: Session = Depends(get_db)):
    logo_service.delete_logo()
    settings_service.update_category(db, "shop", {"logo_path": ""})
    return {"ok": True}


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
