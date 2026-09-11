"""Shop-friendly validation. All messages are plain, non-technical."""
from decimal import Decimal, InvalidOperation

MAX_TEXT_LEN = 120
MAX_COPIES = 99
MAX_WEIGHT = Decimal("99999.999")


def validate_purity_huid(value: str) -> str:
    # Optional: blank fields simply don't print. Only length is enforced.
    v = (value or "").strip()
    if len(v) > MAX_TEXT_LEN:
        return f"Purity / HUID is too long (max {MAX_TEXT_LEN} characters)."
    return ""


def validate_product_name(value: str) -> str:
    # Optional: blank fields simply don't print. Only length is enforced.
    v = (value or "").strip()
    if len(v) > MAX_TEXT_LEN:
        return f"Product name is too long (max {MAX_TEXT_LEN} characters)."
    return ""


def parse_weight(value, label: str) -> tuple[Decimal | None, str]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, f"Please enter {label} weight."
    try:
        d = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        return None, f"{label} weight must be a number (e.g. 2.146)."
    if d < 0:
        return None, f"{label} weight cannot be negative."
    if d > MAX_WEIGHT:
        return None, f"{label} weight is too large."
    return d, ""


def validate_copies(value) -> tuple[int | None, str]:
    try:
        n = int(str(value).strip()) if isinstance(value, str) else int(value)
    except (ValueError, TypeError):
        return None, "Copies must be a whole number (1 or more)."
    if n < 1:
        return None, "Copies must be at least 1."
    if n > MAX_COPIES:
        return None, f"Copies cannot exceed {MAX_COPIES} at once."
    return n, ""


def validate_weights_relation(gross: Decimal, net: Decimal) -> str:
    if net > gross:
        return "Net weight is more than gross weight. Please check the weights."
    return ""
