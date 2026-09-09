from app.tag.renderer import build_back_svg, build_front_svg


def test_front_contains_fields():
    svg = build_front_svg("18kt HUID", "Ring", "2.146", "2.146")
    assert "18kt HUID" in svg
    assert "Ring" in svg
    assert "G.Wt." in svg and "N.Wt." in svg
    assert "2.146 g" in svg
    assert "<svg" in svg


def test_back_contains_shop():
    svg = build_back_svg("XYZ JEWELLERS")
    assert "XYZ JEWELLERS" in svg


def test_missing_logo_does_not_crash():
    svg = build_front_svg("18kt HUID", "Ring", "2.146", "2.146", has_logo=False)
    assert "<svg" in svg


def test_physical_dimensions_in_mm():
    svg = build_front_svg("18kt HUID", "Ring", "1", "1", width_mm=50.0, height_mm=25.0)
    assert 'width="50.0mm"' in svg
    assert 'height="25.0mm"' in svg


def test_escaping():
    svg = build_front_svg("<b>", "Ring", "1", "1")
    assert "<b>" not in svg
