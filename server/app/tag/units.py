"""Single place for DPI/physical-dimension conversion. LP 46 Neo = 203 DPI."""

DPI = 203
MM_PER_INCH = 25.4
DOTS_PER_MM = DPI / MM_PER_INCH  # ≈ 7.992


def mm_to_dots(mm: float) -> int:
    return round(float(mm) * DPI / MM_PER_INCH)


def dots_to_mm(dots: int) -> float:
    return float(dots) * MM_PER_INCH / DPI
