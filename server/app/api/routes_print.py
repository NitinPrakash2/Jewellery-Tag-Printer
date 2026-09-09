"""Print + tag-render routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.domain.schemas import TagRenderRequest
from app.printing.lp46neo_adapter import get_adapter
from app.services import print_service

router = APIRouter(prefix="/api", tags=["print"])


@router.post("/print", response_model=dict)
def print_tag(payload: dict, db: Session = Depends(get_db)):
    cleaned, errors = print_service.validate_print_data(payload or {})
    if errors:
        return {"ok": False, "message": "Please fix the highlighted fields.", "errors": errors}
    result = print_service.execute_print(db, get_adapter(), cleaned)
    out = {"ok": result["ok"], "message": result["message"]}
    if result.get("history_id"):
        out["history_id"] = result["history_id"]
    return out


@router.post("/print/validate", response_model=dict)
def validate_only(payload: dict):
    cleaned, errors = print_service.validate_print_data(payload or {})
    if errors:
        return {"ok": False, "errors": errors}
    return {"ok": True, "cleaned": {k: str(v) for k, v in cleaned.items()}}


@router.post("/tag/render", response_model=dict)
def render_tag(req: TagRenderRequest, db: Session = Depends(get_db)):
    from app.services import settings_service as ss
    from app.tag.renderer import (
        DEFAULT_TAG_HEIGHT_MM,
        DEFAULT_TAG_WIDTH_MM,
        build_tag_svg,
    )

    s = ss.get_all_merged(db)
    try:
        w = req.tag_width_mm or float(s["tag"].get("width_mm", DEFAULT_TAG_WIDTH_MM))
        h = req.tag_height_mm or float(s["tag"].get("height_mm", DEFAULT_TAG_HEIGHT_MM))
    except ValueError:
        w, h = DEFAULT_TAG_WIDTH_MM, DEFAULT_TAG_HEIGHT_MM
    shop = req.shop_name if req.shop_name is not None else s["shop"].get("name", "")
    return {
        "tag_svg": build_tag_svg(
            req.purity_huid or "", req.product_name or "",
            req.gross_weight if req.gross_weight is not None else "",
            req.net_weight if req.net_weight is not None else "",
            width_mm=w, height_mm=h, shop_name=shop,
            has_logo=bool(s["shop"].get("logo_path", "")),
        ),
    }
