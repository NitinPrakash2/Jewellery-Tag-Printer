from app.tag.layout import fit_font, layout_warnings, tag_layout
from app.tag.renderer import build_tag_svg, compute_less_weight


def _tag(**kw):
    args = dict(purity_huid="18Kt HUID", product_name="Ring",
                gross_weight="2.146", net_weight="2.146",
                width_mm=100, height_mm=15, tail_mm=35,
                shop_name="Manish Ornaments", has_logo=False)
    args.update(kw)
    return build_tag_svg(**args)


def test_tag_contains_fields():
    svg = _tag(has_logo=True)
    assert "18Kt HUID" in svg
    assert "Ring" in svg
    assert "ITEM -" not in svg  # final design: product name only
    assert "Gross Wt." in svg and "Less Wt." in svg and "Net Wt." in svg
    assert "2.146 g" in svg
    assert "0.000 g" in svg  # less = gross - net
    assert "MANISH" in svg
    assert "<svg" in svg
    assert 'data-template="v5"' in svg


def test_lines_toggle():
    # OFF (default): dashed grey guides, preview-only — positions identical.
    off = build_tag_svg("18Kt HUID", "Ring", "2.146", "2.146",
                        width_mm=100, height_mm=15, tail_mm=35, show_lines=False)
    assert 'data-preview-only="true"' in off
    assert 'stroke="black" stroke-width="0.4"' not in off
    assert 'stroke="black" stroke-width="0.35"' not in off
    # ON: solid black lines print, no guides except the tail outline.
    on = build_tag_svg("18Kt HUID", "Ring", "2.146", "2.146",
                       width_mm=100, height_mm=15, tail_mm=35, show_lines=True)
    assert 'stroke="black" stroke-width="0.4"' in on
    assert on.count('data-preview-only="true"') == 1  # tail outline only


def test_body_only_tail_has_zero_ink():
    svg = _tag()
    # printable body rect + preview-only dashed tail outline, nothing else
    assert svg.count("<rect") == 2
    assert 'width="65"' in svg  # 100 - 35 tail
    assert "<circle" not in svg  # string hole removed with the old tail
    assert 'data-preview-only="true"' in svg


def test_tail_zero_means_full_width_body():
    svg = build_tag_svg("18Kt HUID", "Ring", "1", "1", width_mm=50, height_mm=25, tail_mm=0)
    assert svg.count("<rect") == 1
    assert 'width="50"' in svg
    # lines ON + no tail = zero preview-only elements: everything prints.
    solid = build_tag_svg("18Kt HUID", "Ring", "1", "1", width_mm=50, height_mm=25,
                          tail_mm=0, show_lines=True)
    assert "data-preview-only" not in solid


def test_no_text_length_hacks():
    # Print rasters ignore textLength — auto-fit must size fonts for real.
    assert "textLength" not in _tag()


def test_print_text_is_bold_and_chunky():
    # Thermal labels need thick glyphs — everything readable must be bold.
    svg = _tag(has_logo=True)
    assert svg.count('font-weight="bold"') >= 5
    # Row font budget grew for readability (0.20 of tag height).
    lay = tag_layout(100, 15, {"gross": "2.146 g", "less": "0.000 g",
                               "net": "2.146 g", "purity": "", "product": "",
                               "shop_l1": "", "shop_l2": "", "initial": ""},
                     tail_mm=35)
    assert lay["row_font"] >= 2.5


def test_item_and_purity_fonts_synced():
    lay = tag_layout(100, 15, {"purity": "18Kt HUID", "product": "Ring",
                               "gross": "2.146 g", "less": "", "net": "2.146 g",
                               "shop_l1": "MANISH", "shop_l2": "ORNAMENTS",
                               "initial": "M"}, show_less=False, tail_mm=35)
    assert lay["item_font"] == lay["purity_font"]
    assert lay["item_font"] >= 2.0


def test_spaced_headlines_stay_inside_zone():
    # Regression: letter-spacing used to push ORNAMENTS/tagline outside
    # the body border. Rendered width incl. spacing must fit the zone.
    from app.tag.layout import CHAR_W, L1_SPACING, L2_SPACING, TAGLINE_SPACING, TAGLINE_TEXT

    lay = tag_layout(100, 15, {"purity": "", "product": "",
                               "gross": "", "less": "", "net": "",
                               "shop_l1": "MANISH", "shop_l2": "ORNAMENTS",
                               "initial": "M"}, show_less=False,
                     show_gross=False, show_net=False, tail_mm=35)
    zone = lay["logo_hw"] * 2
    for text, font, spacing in [
        ("MANISH", lay["l1_font"], L1_SPACING),
        ("ORNAMENTS", lay["l2_font"], L2_SPACING),
        (TAGLINE_TEXT, lay["tagline_font"], TAGLINE_SPACING),
    ]:
        rendered = len(text) * 0.62 * font + spacing * (len(text) - 1) \
            if text == "MANISH" else len(text) * CHAR_W["sans"] * font + spacing * (len(text) - 1)
        assert rendered <= zone + 0.01, (text, rendered, zone)


def test_less_weight_computed():
    assert str(compute_less_weight("2.146", "2.146")) == "0.000"
    assert str(compute_less_weight("5.000", "4.900")) == "0.100"


def test_back_contains_shop():
    svg = build_tag_svg("18Kt HUID", "Ring", "1", "1",
                        shop_name="XYZ JEWELLERS", has_logo=True)
    assert "XYZ" in svg


def test_missing_logo_does_not_crash():
    assert "<svg" in _tag()


def test_physical_dimensions_in_mm():
    svg = build_tag_svg("18Kt HUID", "Ring", "1", "1", width_mm=100.0, height_mm=15.0, tail_mm=35)
    assert 'width="100.0mm"' in svg
    assert 'height="15.0mm"' in svg


def test_escaping():
    assert "<b>" not in build_tag_svg("<b>", "Ring", "1", "1")


def test_fit_font_shrinks_long_text():
    small = fit_font("A very long product name indeed", 20.0, 5.0)
    big = fit_font("Ring", 20.0, 5.0)
    assert small < big
    assert small * len("A very long product name indeed") * 0.55 <= 20.0 + 0.01


def test_fit_font_caps_at_height():
    assert fit_font("Hi", 500.0, 3.0) == 3.0


def test_layout_centres_rows():
    lay = tag_layout(100, 15, {"purity": "18Kt HUID", "product": "Ring",
                               "gross": "2.146 g", "less": "0.000 g",
                               "net": "2.146 g", "shop_l1": "MANISH",
                               "shop_l2": "ORNAMENTS", "initial": "M"}, tail_mm=35)
    fw = lay["body_w"] - lay["fold_x"]
    # row centre == centre of the FRONT zone (centred print in its zone)
    cx = (lay["label_x"] + lay["value_x"]) / 2.0
    assert abs(cx - (lay["fold_x"] + fw / 2.0)) < 0.01
    # fold splits the printable body 50/50 (middle, like the real label)
    assert abs(lay["fold_x"] / lay["body_w"] - 0.50) < 0.001


def test_layout_adapts_to_small_tag():
    big = tag_layout(110, 12, {"gross": "2.146 g", "less": "0.000 g", "net": "2.146 g",
                               "purity": "x", "product": "x", "shop_l1": "",
                               "shop_l2": "", "initial": ""})["row_font"]
    small = tag_layout(40, 8, {"gross": "2.146 g", "less": "0.000 g", "net": "2.146 g",
                               "purity": "x", "product": "x", "shop_l1": "",
                               "shop_l2": "", "initial": ""})["row_font"]
    assert small < big


def test_blank_less_hides_row():
    svg = build_tag_svg("18Kt HUID", "Ring", "2.146", "2.146",
                        width_mm=110, height_mm=12, show_less=False)
    assert "Less Wt." not in svg
    assert "Gross Wt." in svg and "Net Wt." in svg


def test_explicit_less_shows_row():
    svg = build_tag_svg("18Kt HUID", "Ring", "2.146", "2.046",
                        width_mm=110, height_mm=12, show_less=True)
    assert "Less Wt." in svg
    assert "0.100 g" in svg


def test_warnings_empty_for_sane_input():
    w = layout_warnings(110, 12, {"purity": "18Kt HUID", "product": "Ring",
                                  "gross": "2.146 g", "less": "0.000 g",
                                  "net": "2.146 g", "shop_l1": "MANISH",
                                  "shop_l2": "ORNAMENTS", "initial": "M"})
    assert w == []


def test_warnings_flag_overflow_with_mm():
    w = layout_warnings(40, 8, {"purity": "18Kt HUID", "product": "A very long product name indeed",
                                "gross": "2.146 g", "less": "0.000 g",
                                "net": "2.146 g", "shop_l1": "", "shop_l2": "",
                                "initial": ""})
    assert any(x["field"] == "Product name" and x["overflow_mm"] > 0 for x in w)
    assert all("mm" in x["message"] for x in w)
