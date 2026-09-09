from app.tag.renderer import build_tag_svg, compute_less_weight


def test_tag_contains_fields():
    svg = build_tag_svg("18kt HUID", "Ring", "2.146", "2.146",
                        shop_name="Manish Ornaments", has_logo=True)
    assert "18kt HUID" in svg
    assert "ITEM - Ring" in svg
    assert "Gross Wt." in svg and "Less Wt." in svg and "Net Wt." in svg
    assert "2.146 g" in svg
    assert "0.000 g" in svg  # less = gross - net
    assert "MANISH" in svg
    assert "<svg" in svg


def test_less_weight_computed():
    assert str(compute_less_weight("2.146", "2.146")) == "0.000"
    assert str(compute_less_weight("5.000", "4.900")) == "0.100"


def test_back_contains_shop():
    svg = build_tag_svg("18kt HUID", "Ring", "1", "1",
                        shop_name="XYZ JEWELLERS", has_logo=True)
    assert "XYZ" in svg


def test_missing_logo_does_not_crash():
    svg = build_tag_svg("18kt HUID", "Ring", "2.146", "2.146", has_logo=False)
    assert "<svg" in svg


def test_physical_dimensions_in_mm():
    svg = build_tag_svg("18kt HUID", "Ring", "1", "1", width_mm=110.0, height_mm=12.0)
    assert 'width="110.0mm"' in svg
    assert 'height="12.0mm"' in svg


def test_escaping():
    svg = build_tag_svg("<b>", "Ring", "1", "1")
    assert "<b>" not in svg
