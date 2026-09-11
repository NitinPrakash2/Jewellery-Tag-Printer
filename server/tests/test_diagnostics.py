"""Diagnostics feed tests: events recorded, listed newest-first, clearable."""
from app import diagnostics


def test_empty_feed_shape(client):
    diagnostics.clear()
    r = client.get("/api/diagnostics/events")
    assert r.status_code == 200
    assert r.json()["events"] == []


def test_failed_test_print_is_recorded(client):
    diagnostics.clear()
    r = client.post("/api/printers/test", json={"printer_name": "No Such Printer XYZ"})
    assert r.status_code == 200
    assert r.json()["ok"] is False
    events = client.get("/api/diagnostics/events").json()["events"]
    assert any(e["source"] == "PRINTER" and e["level"] == "error" for e in events)


def test_failed_print_is_recorded(client, monkeypatch):
    diagnostics.clear()
    import app.api.routes_history as rh
    import app.api.routes_print as rp
    from app.printing.printer_adapter import PrintJobResult

    class DeadAdapter:
        def discover_printers(self):
            return []

        def get_status(self, name):
            from app.printing.printer_adapter import PrinterInfo
            return PrinterInfo(name=name, status="ready")

        def print_svg(self, printer_name, svg, copies=1):
            return PrintJobResult(ok=False, message="cable unplugged (simulated)")

        def print_test(self, printer_name):
            return PrintJobResult(ok=False, message="nope")

    monkeypatch.setattr(rp, "get_adapter", lambda: DeadAdapter())
    monkeypatch.setattr(rh, "get_adapter", lambda: DeadAdapter())
    client.put("/api/settings/printer", json={"selected": "Fake LP"})
    r = client.post("/api/print", json={"purity_huid": "18kt HUID", "product_name": "Ring",
                                        "gross_weight": "2.146", "less_weight": "0",
                                        "copies": 1})
    assert r.status_code == 200
    events = client.get("/api/diagnostics/events").json()["events"]
    assert any("cable unplugged" in e["message"] for e in events)


def test_auto_capture_of_logged_errors(client):
    diagnostics.clear()
    from app.logging_setup import log

    log.error("simulated app failure XYZ123")
    events = client.get("/api/diagnostics/events").json()["events"]
    assert any(e["source"] == "APP" and "XYZ123" in e["message"] for e in events)


def test_clear(client):
    diagnostics.clear()
    from app.logging_setup import log

    log.error("to be cleared")
    assert len(client.get("/api/diagnostics/events").json()["events"]) > 0
    assert client.delete("/api/diagnostics/events").json()["ok"] is True
    assert client.get("/api/diagnostics/events").json()["events"] == []
