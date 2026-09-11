"""Live USB detection tests (safe on machines with no USB printer)."""
from app.printing import usb_detect


def test_identify_known_models():
    assert usb_detect.identify_model("DCode DC423 Pro") == "dcode_dc423pro"
    assert usb_detect.identify_model("TVS LP 46 Neo") == "tvs_lp46neo"
    assert usb_detect.identify_model("Zebra GK420") == "zebra"
    assert usb_detect.identify_model("4BARCODE 4B-2054TG") == "fourbarcode_4b2054tg"
    assert usb_detect.identify_model("Some Random Camera") is None


def test_usb_live_shape(client):
    r = client.get("/api/printers/usb-live", params={"printer_name": ""})
    assert r.status_code == 200
    body = r.json()
    assert "available" in body
    assert isinstance(body["usb_devices"], list)
    assert isinstance(body["installed"], list)
    assert "driver_installed" in body
    # This dev machine has no USB printer plugged in.
    assert body["usb_devices"] == []
    # Virtual printers are hidden — only real external printers matter.
    assert all("Print to PDF" not in n and "OneNote" not in n for n in body["installed"])


def test_driver_help_has_4barcode(client):
    drivers = client.get("/api/printers/driver-help").json()["drivers"]
    d = drivers["fourbarcode_4b2054tg"]
    assert "bartendersoftware.com" in d["download_url"]
    assert "4b-2054tg" in d["download_url"]


def test_wrong_printer_does_not_mark_driver_installed(monkeypatch):
    """Friend's case: USB shows 4BARCODE, Windows has only EPSON inkjet."""
    from app.printing import usb_detect, windows_spool

    monkeypatch.setattr(
        usb_detect, "list_usb_printer_devices",
        lambda: [{"name": "4BARCODE 4B-2054TG", "device_id": "USB\\VID_1234&PID_5678",
                  "vid": "1234", "pid": "5678", "status": "OK"}],
    )
    monkeypatch.setattr(
        windows_spool, "list_printer_names", lambda *a, **k: ["EPSON L360 Series"]
    )
    out = usb_detect.live_status("EPSON L360 Series")
    assert out["driver_key"] == "fourbarcode_4b2054tg"
    assert out["driver_installed"] is False


def test_matching_printer_marks_driver_installed(monkeypatch):
    from app.printing import usb_detect, windows_spool

    monkeypatch.setattr(
        usb_detect, "list_usb_printer_devices",
        lambda: [{"name": "4BARCODE 4B-2054TG", "device_id": "USB\\VID_1234&PID_5678",
                  "vid": "1234", "pid": "5678", "status": "OK"}],
    )
    monkeypatch.setattr(
        windows_spool, "list_printer_names", lambda *a, **k: ["4BARCODE 4B-2054TG"]
    )
    out = usb_detect.live_status("")
    assert out["driver_installed"] is True
