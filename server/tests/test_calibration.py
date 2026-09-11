"""Calibration must REALLY move the print — offsets/scales are baked into
the SVG transform, so preview and paper agree."""
from app.printing.calibration import Calibration, apply_calibration
from app.tag.renderer import build_tag_svg

SVG = build_tag_svg("18Kt HUID", "Ring", "2.146", "2.146",
                    width_mm=110, height_mm=12,
                    shop_name="Manish Ornaments", has_logo=False)


def test_neutral_is_untouched():
    assert apply_calibration(SVG, Calibration()) == SVG
    assert "<g transform" not in SVG


def test_offset_shifts_ink_in_mm():
    out = apply_calibration(SVG, Calibration(offset_x_mm=2.0, offset_y_mm=-1.5))
    assert 'transform="translate(2 -1.5)"' in out
    assert out.count("<g transform") == 1
    assert out.rstrip().endswith("</svg>")
    assert "</g></svg>" in out


def test_scale_applies_about_centre():
    out = apply_calibration(SVG, Calibration(scale=1.1))
    assert "scale(1.1)" in out
    # centre of 110x12 tag
    assert "translate(55 6)" in out


def test_offset_plus_scale_combined():
    out = apply_calibration(SVG, Calibration(offset_x_mm=1, scale=0.9))
    assert "translate(1 0)" in out
    assert "scale(0.9)" in out


def test_full_flow_settings_to_render(client):
    r = client.put("/api/settings/calibration",
                   json={"offset_x_mm": "2.5", "offset_y_mm": "0", "scale": "1.0"})
    assert r.status_code == 200
    r2 = client.post("/api/tag/render", json={"purity_huid": "18Kt HUID",
                                              "product_name": "Ring",
                                              "gross_weight": "2.146",
                                              "net_weight": "2.146"})
    assert r2.status_code == 200
    assert 'translate(2.5 0)' in r2.json()["tag_svg"]
