"""Print service — validation → render SVG → adapter → history.

Flow per spec: data → validation → preview (SVG) → PRINT → output →
LP 46 Neo → result → save history. Success is reported only from the
adapter result, never from the button click.
"""
from decimal import Decimal

from app.database.repositories import history_repo
from app.diagnostics import record
from app.domain import validators
from app.logging_setup import log
from app.printing.calibration import Calibration, apply_calibration
from app.services import settings_service
from app.tag.renderer import DEFAULT_TAG_HEIGHT_MM, DEFAULT_TAG_WIDTH_MM, TEMPLATE_VERSION, build_tag_svg


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

    # Net weight is automatic: net = gross - less. The form sends less_weight;
    # a direct net_weight is still accepted for backwards compatibility.
    less_raw = data.get("less_weight", None)
    less_is_given = less_raw is not None and str(less_raw).strip() != ""
    net = None
    less = None
    if less_is_given:
        less, e = validators.parse_weight(less_raw, "Less")
        if e:
            errors["less_weight"] = e
        elif "gross_weight" not in errors:
            if less < 0:
                errors["less_weight"] = "Less weight cannot be negative."
            elif less > gross:
                errors["less_weight"] = "Less weight is more than gross weight. Please check the weights."
            else:
                net = gross - less
    else:
        net_raw = data.get("net_weight", None)
        net_is_given = net_raw is not None and str(net_raw).strip() != ""
        if not net_is_given and "gross_weight" not in errors:
            # Nothing deducted: less defaults to 0, net equals gross.
            from decimal import Decimal as _D

            less = _D("0")
            net = gross
        else:
            net, e = validators.parse_weight(net_raw, "Net")
            if e:
                errors["net_weight"] = e
            elif "gross_weight" not in errors:
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
        "less_weight": less if "less_weight" not in errors else (less_raw or ""),
        "net_weight": net if net is not None else data.get("net_weight"),
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


def render_tag(db, cleaned: dict) -> str:
    """Render the single fold-over tag (back + fold + front + tail)."""
    s = _settings_snapshot(db)
    try:
        w = float(s["tag"].get("width_mm", DEFAULT_TAG_WIDTH_MM))
        h = float(s["tag"].get("height_mm", DEFAULT_TAG_HEIGHT_MM))
    except ValueError:
        w, h = DEFAULT_TAG_WIDTH_MM, DEFAULT_TAG_HEIGHT_MM
    shop_name = s["shop"].get("name", "")
    logo_path = s["shop"].get("logo_path", "")
    has_logo = bool(logo_path)
    tag = build_tag_svg(
        cleaned["purity_huid"], cleaned["product_name"],
        cleaned["gross_weight"], cleaned["net_weight"],
        width_mm=w, height_mm=h, shop_name=shop_name, has_logo=has_logo,
        logo_path=logo_path,
    )
    try:
        cal = Calibration(
            offset_x_mm=float(s["calibration"].get("offset_x_mm", 0.0)),
            offset_y_mm=float(s["calibration"].get("offset_y_mm", 0.0)),
            scale=float(s["calibration"].get("scale", 1.0)),
        )
    except ValueError:
        cal = Calibration()
    return apply_calibration(tag, cal)


def execute_print(db, adapter, cleaned: dict) -> dict:
    """Print the fold-over tag in a single pass (one label, folded at FOLD)."""
    printer_name = cleaned.get("printer_name", "")
    if not printer_name:
        try:
            printer_name = _settings_snapshot(db)["printer"].get("selected", "")
        except Exception:
            printer_name = ""
    if not printer_name:
        return {"ok": False, "message": "Please select a printer in Settings first.",
                "history_id": None, "tag_svg": None}

    tag_svg = render_tag(db, cleaned)
    copies = int(cleaned.get("copies", 1))

    res = adapter.print_svg(printer_name, tag_svg, copies=copies)
    if not res.ok:
        log.error("print failed on %s: %s", printer_name, res.message)
        record("PRINTER", "error", f"Print failed on '{printer_name}'. {res.message}")
        row = history_repo.create(
            db, purity_huid=cleaned["purity_huid"], product_name=cleaned["product_name"],
            gross_weight=Decimal(str(cleaned["gross_weight"])),
            net_weight=Decimal(str(cleaned["net_weight"])), copies=copies,
            printer_name=printer_name, template_version=TEMPLATE_VERSION,
            status="failed", error_message=res.message,
        )
        return {"ok": False, "message": res.message, "history_id": row.id,
                "tag_svg": tag_svg}

    row = history_repo.create(
        db, purity_huid=cleaned["purity_huid"], product_name=cleaned["product_name"],
        gross_weight=Decimal(str(cleaned["gross_weight"])),
        net_weight=Decimal(str(cleaned["net_weight"])), copies=copies,
        printer_name=printer_name, template_version=TEMPLATE_VERSION, status="success",
    )
    log.info("print success id=%s printer=%s copies=%s", row.id, printer_name, copies)
    record("PRINT", "info",
           f"Printed {copies} copie(s) of '{cleaned['product_name']}' on '{printer_name}'.")
    return {"ok": True, "message": f"Printed {copies} copie(s) on {printer_name}.",
            "history_id": row.id, "tag_svg": tag_svg}
