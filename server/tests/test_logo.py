"""Logo upload / embedding tests. Uploads go to an isolated tmp dir."""
import app.services.logo_service as ls
from app.tag.renderer import build_tag_svg

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(ls, "LOGO_DIR", str(tmp_path))


def test_validate_ok_png():
    ext, err = ls.validate_upload("logo.png", PNG)
    assert err == "" and ext == ".png"


def test_validate_bad_ext():
    _, err = ls.validate_upload("logo.txt", b"hello")
    assert err != ""


def test_validate_bad_magic():
    _, err = ls.validate_upload("logo.png", b"not an image....")
    assert err != ""


def test_validate_too_big():
    big = b"\x89PNG\r\n\x1a\n" + b"0" * (3 * 1024 * 1024)
    _, err = ls.validate_upload("a.png", big)
    assert "large" in err.lower()


def test_renderer_embeds_uploaded_logo(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    path, err = ls.save_upload("logo.png", PNG)
    assert err == ""
    svg = build_tag_svg("18Kt HUID", "Ring", "2.146", "2.146",
                        shop_name="Manish Ornaments", has_logo=True, logo_path=path)
    assert "<image" in svg
    assert "data:image/png;base64" in svg


def test_renderer_missing_logo_falls_back():
    svg = build_tag_svg("18Kt HUID", "Ring", "2.146", "2.146",
                        shop_name="Manish Ornaments", has_logo=True,
                        logo_path="C:\\definitely\\not\\here.png")
    assert "<image" not in svg
    assert "<svg" in svg


def test_upload_endpoint(client, monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    r = client.post("/api/settings/logo", files={"file": ("logo.png", PNG, "image/png")})
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    g = client.get("/api/settings/logo")
    assert g.json()["data_uri"].startswith("data:image/png;base64,")
    d = client.delete("/api/settings/logo")
    assert d.json()["ok"] is True
    g2 = client.get("/api/settings/logo")
    assert g2.json()["data_uri"] is None


def test_upload_rejects_bad_file(client, monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    r = client.post("/api/settings/logo", files={"file": ("x.txt", b"hi", "text/plain")})
    assert r.status_code == 422
