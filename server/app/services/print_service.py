"""Print service — validation → render SVG → adapter → history.

Flow per spec: data → validation → preview (SVG) → PRINT → output →
LP 46 Neo → result → save history. Success is reported only from the
adapter result, never from the button click.
"""
from decimal import Decimal

from app.database.repositories import history_repo
from app.domain import validators
from app.logging_setup import log
from app.printing.calibration import Calibration, apply_calibration
from app.services import settings_service
from app.tag.renderer import TEMPLATE_VERSION, build_back_svg, build_front_svg, shop_initials


def validate_print_data(data: dict) -> tuple[dict, dict[str, str]]:
    errors: dict[str, str] = {}
    purity = str(data.get("purity_huid", ""))
    product = str(data.get("product_name", ""))

    e = validators.validate_purity_huid(purity)
    if e:
        errors["purity_huid"] = e
    e = validators.validate_product_name(product)
    if e:
        errors["product_name"] = e

    gross, e = validators.parse_weight(data.get("gross_weight"), "Gross")
    if e:
        errors["gross_weight"] = e
    net, e = validators.parse_weight(data.get("net_weight"), "Net")
    if e:
        errors["net_weight"] = e
    if "gross_weight" not in errors and "net_weight" not in errors:
        e = validators.validate_weights_relation(gross, net)
        if e:
            errors["net_weight"] = e

    copies, e = validators.validate_copies(data.get("copies", 1))
    if e:
        errors["copies"] = e

    cleaned = {
        "purity_huid": purity.strip(),
        "product_name": product.strip(),
        "gross_weight": gross if "gross_weight" not in errors else data.get("gross_weight"),
        "net_weight": net if "net_weight" not in errors else data.get("net_weight"),
        "copies": copies if "copies" not in errors else data.get("copies"),
        "printer_name": str(data.get("printer_name", "") or "").strip(),
    }
    return cleaned, errors


def _settings_snapshot(db) -> dict:
    try:
        return settings_service.get_all_merged(db)
    except Exception as exc:
        log.error("settings load failed, using defaults: %s", exc)
        return {k: dict(v) for k, v in settings_service.DEFAULTS.items()}


def render_tag(db, cleaned: dict) -> tuple[str, str]:
    s = _settings_snapshot(db)
    try:
        w = float(s["tag"].get("width_mm", 50.0))
        h = float(s["tag"].get("height_mm", 25.0))
    except ValueError:
        w, h = 50.0, 25.0
    shop_name = s["shop"].get("name", "")
    has_logo = bool(s["shop"].get("logo_path", ""))
    front = build_front_svg(
        cleaned["purity_huid"], cleaned["product_name"],
        cleaned["gross_weight"], cleaned["net_weight"],
        width_mm=w, height_mm=h, has_logo=has_logo,
        monogram=shop_initials(shop_name),
    )
    back = build_back_svg(shop_name, width_mm=w, height_mm=h)
    try:
        cal = Calibration(
            offset_x_mm=float(s["calibration"].get("offset_x_mm", 0.0)),
            offset_y_mm=float(s["calibration"].get("offset_y_mm", 0.0)),
            scale=float(s["calibration"].get("scale", 1.0)),
        )
    except ValueError:
        cal = Calibration()
    return apply_calibration(front, cal), apply_calibration(back, cal)


def execute_print(db, adapter, cleaned: dict) -> dict:
    """Run front+back passes (separate passes — no duplex assumed)."""
    printer_name = cleaned.get("printer_name", "")
    if not printer_name:
        try:
            printer_name = _settings_snapshot(db)["printer"].get("selected", "")
        except Exception:
            printer_name = ""
    if not printer_name:
        return {"ok": False, "message": "Please select a printer in Settings first.",
                "history_id": None, "front_svg": None, "back_svg": None}

    front_svg, back_svg = render_tag(db, cleaned)
    copies = int(cleaned.get("copies", 1))

    # NEEDS HARDWARE VALIDATION: whether back prints in the same job or needs
    # a re-feed must be confirmed on hardware. We do two explicit passes.
    front_res = adapter.print_svg(printer_name, front_svg, copies=copies)
    if not front_res.ok:
        log.error("print front failed on %s: %s", printer_name, front_res.message)
        row = history_repo.create(
            db, purity_huid=cleaned["purity_huid"], product_name=cleaned["product_name"],
            gross_weight=Decimal(str(cleaned["gross_weight"])),
            net_weight=Decimal(str(cleaned["net_weight"])), copies=copies,
            printer_name=printer_name, template_version=TEMPLATE_VERSION,
            status="failed", error_message=front_res.message,
        )
        return {"ok": False, "message": front_res.message, "history_id": row.id,
                "front_svg": front_svg, "back_svg": back_svg}

    back_res = adapter.print_svg(printer_name, back_svg, copies=copies)
    if not back_res.ok:
        log.error("print back failed on %s: %s", printer_name, back_res.message)
        row = history_repo.create(
            db, purity_huid=cleaned["purity_huid"], product_name=cleaned["product_name"],
            gross_weight=Decimal(str(cleaned["gross_weight"])),
            net_weight=Decimal(str(cleaned["net_weight"])), copies=copies,
            printer_name=printer_name, template_version=TEMPLATE_VERSION,
            status="failed", error_message=f"Front printed. Back failed: {back_res.message}",
        )
        return {"ok": False, "message": f"Front printed. Back failed: {back_res.message}",
                "history_id": row.id, "front_svg": front_svg, "back_svg": back_svg}

    row = history_repo.create(
        db, purity_huid=cleaned["purity_huid"], product_name=cleaned["product_name"],
        gross_weight=Decimal(str(cleaned["gross_weight"])),
        net_weight=Decimal(str(cleaned["net_weight"])), copies=copies,
        printer_name=printer_name, template_version=TEMPLATE_VERSION, status="success",
    )
    log.info("print success id=%s printer=%s copies=%s", row.id, printer_name, copies)
    return {"ok": True, "message": f"Printed {copies} copie(s) on {printer_name}.",
            "history_id": row.id, "front_svg": front_svg, "back_svg": back_svg}
