"""Calibration helpers. Offsets in millimetres, stored in settings, applied here."""
from dataclasses import dataclass


@dataclass
class Calibration:
    offset_x_mm: float = 0.0
    offset_y_mm: float = 0.0
    scale: float = 1.0

    def describe(self) -> str:
        return (
            f"offset_x={self.offset_x_mm}mm "
            f"offset_y={self.offset_y_mm}mm scale={self.scale}"
        )


def apply_calibration(svg: str, cal: Calibration) -> str:
    # NEEDS HARDWARE VALIDATION: real offset/scale behaviour must be confirmed
    # on the LP 46 Neo with real label media. For the Windows-driver path the
    # driver handles placement; we annotate the job and pass SVG through.
    if cal.offset_x_mm == 0 and cal.offset_y_mm == 0 and cal.scale == 1.0:
        return svg
    marker = f"<!-- calibration {cal.describe()} -->"
    return svg.replace("</svg>", f"{marker}</svg>")
