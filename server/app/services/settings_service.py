"""Settings service — defaults merged over DB, no seed rows written."""
from app.database.repositories import settings_repo

# NEEDS HARDWARE VALIDATION: tag dimensions/media defaults must be confirmed
# with the real label stock. Values below are configurable placeholders.
DEFAULTS: dict[str, dict[str, str]] = {
    "shop": {"name": "", "logo_path": ""},
    "printer": {"selected": "", "status_note": ""},
    "tag": {"width_mm": "100.0", "height_mm": "15.0", "tail_width_mm": "35.0", "orientation": "landscape"},
    "calibration": {"offset_x_mm": "0.0", "offset_y_mm": "0.0", "scale": "1.0"},
    "app": {"theme": "light", "default_copies": "1"},
}

CATEGORIES = set(DEFAULTS)


def _prefix(category: str) -> str:
    return f"{category}."


def get_category(db, category: str) -> dict[str, str]:
    if category not in CATEGORIES:
        raise KeyError(f"Unknown settings category: {category}")
    stored = settings_repo.get_all(db)
    merged = dict(DEFAULTS[category])
    p = _prefix(category)
    for key, value in stored.items():
        if key.startswith(p) and key[len(p):] in merged:
            merged[key[len(p):]] = value
    return merged


def get_all_merged(db) -> dict[str, dict[str, str]]:
    return {cat: get_category(db, cat) for cat in CATEGORIES}


def update_category(db, category: str, values: dict[str, str]) -> dict[str, str]:
    if category not in CATEGORIES:
        raise KeyError(f"Unknown settings category: {category}")
    allowed = set(DEFAULTS[category])
    clean = {k: str(v) for k, v in values.items() if k in allowed}
    # Light validation with shop-friendly errors raised as ValueError
    if category == "tag":
        for dim in ("width_mm", "height_mm"):
            if dim in clean:
                try:
                    v = float(clean[dim])
                except ValueError:
                    raise ValueError("Tag width/height must be numbers (millimetres).")
                if v <= 0 or v > 500:
                    raise ValueError("Tag width/height must be between 0 and 500 mm.")
        if "tail_width_mm" in clean:
            try:
                t = float(clean["tail_width_mm"])
            except ValueError:
                raise ValueError("Tail width must be a number (millimetres).")
            try:
                w = float(clean.get("width_mm", "100"))
            except ValueError:
                w = 100.0
            if t < 0 or t >= w:
                raise ValueError("Tail must be 0 or more, and less than the total width.")
        if "orientation" in clean and clean["orientation"] not in ("landscape", "portrait"):
            raise ValueError("Orientation must be landscape or portrait.")
    if category == "calibration":
        for k in ("offset_x_mm", "offset_y_mm"):
            if k in clean:
                try:
                    v = float(clean[k])
                except ValueError:
                    raise ValueError("Calibration offsets must be numbers (millimetres).")
                if abs(v) > 50:
                    raise ValueError("Calibration offset is too large (max 50 mm).")
        if "scale" in clean:
            try:
                s = float(clean["scale"])
            except ValueError:
                raise ValueError("Calibration scale must be a number.")
            if s <= 0 or s > 3:
                raise ValueError("Calibration scale must be between 0 and 3.")
    if category == "app" and "default_copies" in clean:
        try:
            n = int(clean["default_copies"])
        except ValueError:
            raise ValueError("Default copies must be a whole number.")
        if n < 1 or n > 99:
            raise ValueError("Default copies must be between 1 and 99.")
    settings_repo.upsert_many(db, {f"{category}.{k}": v for k, v in clean.items()})
    return get_category(db, category)
