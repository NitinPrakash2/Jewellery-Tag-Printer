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
    from app.printing.calibration import Calibration, apply_calibration, parse_rotate_180
    from app.services import settings_service as ss
    from app.tag.renderer import (
        DEFAULT_TAG_HEIGHT_MM,
        DEFAULT_TAG_WIDTH_MM,
        DEFAULT_TAIL_MM,
        build_tag_svg,
    )

    s = ss.get_all_merged(db)
    try:
        w = req.tag_width_mm or float(s["tag"].get("width_mm", DEFAULT_TAG_WIDTH_MM))
        h = req.tag_height_mm or float(s["tag"].get("height_mm", DEFAULT_TAG_HEIGHT_MM))
        tail = float(s["tag"].get("tail_width_mm", DEFAULT_TAIL_MM))
    except ValueError:
        w, h, tail = DEFAULT_TAG_WIDTH_MM, DEFAULT_TAG_HEIGHT_MM, DEFAULT_TAIL_MM
    shop = req.shop_name if req.shop_name is not None else s["shop"].get("name", "")
    logo_path = s["shop"].get("logo_path", "")
    try:
        cal = Calibration(
            offset_x_mm=float(s["calibration"].get("offset_x_mm", 0.0)),
            offset_y_mm=float(s["calibration"].get("offset_y_mm", 0.0)),
            scale=float(s["calibration"].get("scale", 1.0)),
            rotate_180=parse_rotate_180(s["calibration"].get("rotate_180", 0)),
        )
    except ValueError:
        cal = Calibration()
    show_less = not (req.less_weight is not None and str(req.less_weight).strip() == "")
    gross_in = req.gross_weight if req.gross_weight is not None else ""
    net_in = req.net_weight if req.net_weight is not None else ""
    show_gross = str(gross_in).strip() != ""
    show_net = str(net_in).strip() != ""
    show_lines = str(s["tag"].get("show_lines", "0")).strip().lower() in ("1", "true")
    tag = build_tag_svg(
        req.purity_huid or "", req.product_name or "",
        gross_in, net_in,
        width_mm=w, height_mm=h, shop_name=shop,
        has_logo=bool(logo_path), logo_path=logo_path, show_less=show_less,
        tail_mm=tail, show_gross=show_gross, show_net=show_net,
        show_lines=show_lines,
    )
    from app.tag.layout import layout_warnings
    from app.tag.renderer import brand_parts

    initial, line1, line2 = brand_parts(shop)
    warnings = layout_warnings(w, h, {
        "purity": req.purity_huid or "", "product": req.product_name or "",
        "gross": f"{gross_in} g" if str(gross_in).strip() else "",
        "less": "",
        "net": f"{net_in} g" if str(net_in).strip() else "",
        "shop_l1": line1, "shop_l2": line2, "initial": initial,
    }, show_less=show_less, tail_mm=tail)
    return {"tag_svg": apply_calibration(tag, cal), "warnings": warnings}
