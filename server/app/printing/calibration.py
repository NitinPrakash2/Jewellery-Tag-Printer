"""Calibration helpers. Offsets in millimetres, stored in settings, applied here.

Applied as a real SVG transform, so preview AND paper move together:
  <g transform="translate(ox oy) ..."> around all printed ink.
The SVG viewBox is in millimetre units, so translate values ARE millimetres.
Scale (rarely needed) is applied about the tag centre.
"""
import re
from dataclasses import dataclass


@dataclass
class Calibration:
    offset_x_mm: float = 0.0
    offset_y_mm: float = 0.0
    scale: float = 1.0

    def is_neutral(self) -> bool:
        return self.offset_x_mm == 0 and self.offset_y_mm == 0 and self.scale == 1.0

    def describe(self) -> str:
        return (
            f"offset_x={self.offset_x_mm}mm "
            f"offset_y={self.offset_y_mm}mm scale={self.scale}"
        )


def _f(n: float) -> str:
    s = f"{float(n):.3f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def _canvas_mm(svg: str) -> tuple[float, float]:
    w = re.search(r'width="([\d.]+)mm"', svg)
    h = re.search(r'height="([\d.]+)mm"', svg)
    try:
        return float(w.group(1)) if w else 0.0, float(h.group(1)) if h else 0.0
    except (ValueError, AttributeError):
        return 0.0, 0.0


def calibration_transform(cal: Calibration, width_mm: float, height_mm: float) -> str:
    parts = []
    if cal.offset_x_mm or cal.offset_y_mm:
        parts.append(f"translate({_f(cal.offset_x_mm)} {_f(cal.offset_y_mm)})")
    if cal.scale != 1.0:
        cx, cy = width_mm / 2.0, height_mm / 2.0
        parts.append(
            f"translate({_f(cx)} {_f(cy)}) scale({_f(cal.scale)}) "
            f"translate({_f(-cx)} {_f(-cy)})"
        )
    return " ".join(parts)


def apply_calibration(svg: str, cal: Calibration) -> str:
    if cal.is_neutral() or "<svg" not in svg:
        return svg
    w, h = _canvas_mm(svg)
    transform = calibration_transform(cal, w, h)
    if not transform:
        return svg
    head_end = svg.find(">") + 1
    if head_end <= 0:
        return svg
    return (
        svg[:head_end]
        + f'<g transform="{transform}">'
        + svg[head_end:].replace("</svg>", "</g></svg>")
    )
