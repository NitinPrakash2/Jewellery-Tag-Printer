from app.tag import units


def test_dpi_constant():
    assert units.DPI == 203


def test_inch_conversion():
    assert units.mm_to_dots(25.4) == 203
    assert units.mm_to_dots(0) == 0


def test_dots_per_mm_approx():
    assert abs(units.DOTS_PER_MM - 7.992) < 0.01


def test_roundtrip():
    assert abs(units.dots_to_mm(units.mm_to_dots(50.0)) - 50.0) < 0.2
