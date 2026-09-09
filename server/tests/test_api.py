"""End-to-end API tests against isolated Postgres test DB. No seed data."""
from app.printing.printer_adapter import PrintJobResult


class FakeAdapter:
    def discover_printers(self):
        from app.printing.printer_adapter import PrinterInfo
        return [PrinterInfo(name="Fake LP 46", status="ready")]

    def get_status(self, name):
        from app.printing.printer_adapter import PrinterInfo
        return PrinterInfo(name=name, status="ready")

    def print_svg(self, printer_name, svg, copies=1):
        assert "<svg" in svg
        return PrintJobResult(ok=True, message="fake ok")

    def print_test(self, printer_name):
        return PrintJobResult(ok=True, message="fake test ok")


def _patch(monkeypatch):
    import app.api.routes_print as rp
    import app.api.routes_history as rh
    monkeypatch.setattr(rp, "get_adapter", lambda: FakeAdapter())
    monkeypatch.setattr(rh, "get_adapter", lambda: FakeAdapter())


def test_health_db_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["db_ok"] is True


def test_settings_defaults_no_seed(client):
    r = client.get("/api/settings/shop")
    assert r.status_code == 200
    assert "name" in r.json()


def test_settings_update_and_read(client):
    r = client.put("/api/settings/shop", json={"name": "XYZ JEWELLERS"})
    assert r.status_code == 200
    assert r.json()["name"] == "XYZ JEWELLERS"
    r2 = client.get("/api/settings/shop")
    assert r2.json()["name"] == "XYZ JEWELLERS"


def test_settings_invalid_tag_rejected(client):
    r = client.put("/api/settings/tag", json={"width_mm": "-5"})
    assert r.status_code == 422


def test_history_empty_initially(client):
    r = client.get("/api/history")
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_print_validate_errors(client):
    r = client.post("/api/print/validate", json={})
    assert r.status_code == 200
    assert r.json()["ok"] is False


def test_print_success_creates_history(client, monkeypatch):
    _patch(monkeypatch)
    client.put("/api/settings/printer", json={"selected": "Fake LP 46"})
    payload = {"purity_huid": "18kt HUID", "product_name": "Ring",
               "gross_weight": "2.146", "net_weight": "2.146", "copies": 1}
    r = client.post("/api/print", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    hid = r.json()["history_id"]
    h = client.get("/api/history")
    assert h.json()["total"] == 1
    d = client.get(f"/api/history/{hid}")
    assert d.json()["product_name"] == "Ring"


def test_reprint_creates_new_row(client, monkeypatch):
    _patch(monkeypatch)
    client.put("/api/settings/printer", json={"selected": "Fake LP 46"})
    payload = {"purity_huid": "22kt HUID", "product_name": "Bangle",
               "gross_weight": "5.000", "net_weight": "4.900", "copies": 2}
    r = client.post("/api/print", json=payload)
    hid = r.json()["history_id"]
    r2 = client.post(f"/api/history/{hid}/reprint")
    assert r2.status_code == 200
    h = client.get("/api/history")
    assert h.json()["total"] == 2


def test_search_filter(client, monkeypatch):
    _patch(monkeypatch)
    client.put("/api/settings/printer", json={"selected": "Fake LP 46"})
    client.post("/api/print", json={"purity_huid": "18kt HUID", "product_name": "Ring",
                                    "gross_weight": "1", "net_weight": "1", "copies": 1})
    client.post("/api/print", json={"purity_huid": "22kt HUID", "product_name": "Necklace",
                                    "gross_weight": "1", "net_weight": "1", "copies": 1})
    r = client.get("/api/history", params={"q": "Ring"})
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["product_name"] == "Ring"


def test_tag_render(client):
    r = client.post("/api/tag/render", json={"purity_huid": "18kt HUID",
                                             "product_name": "Ring",
                                             "gross_weight": "2.146",
                                             "net_weight": "2.146"})
    assert r.status_code == 200
    assert "18kt HUID" in r.json()["front_svg"]
