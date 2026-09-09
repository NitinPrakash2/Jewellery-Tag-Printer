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
    cleaned = {
        "purity_huid": req.purity_huid or "",
        "product_name": req.product_name or "",
        "gross_weight": req.gross_weight if req.gross_weight is not None else "",
        "net_weight": req.net_weight if req.net_weight is not None else "",
        "copies": 1,
        "printer_name": "",
    }
    from app.services import settings_service as ss

    s = ss.get_all_merged(db)
    w = req.tag_width_mm or float(s["tag"].get("width_mm", 50.0))
    h = req.tag_height_mm or float(s["tag"].get("height_mm", 25.0))
    shop = req.shop_name if req.shop_name is not None else s["shop"].get("name", "")
    from app.tag.renderer import build_back_svg, build_front_svg

    return {
        "front_svg": build_front_svg(
            cleaned["purity_huid"], cleaned["product_name"],
            cleaned["gross_weight"] or "", cleaned["net_weight"] or "",
            width_mm=w, height_mm=h, has_logo=bool(s["shop"].get("logo_path", "")),
        ),
        "back_svg": build_back_svg(shop, width_mm=w, height_mm=h),
    }
