"""Live USB detection tests (safe on machines with no USB printer)."""
from app.printing import usb_detect


def test_identify_known_models():
    assert usb_detect.identify_model("DCode DC423 Pro") == "dcode_dc423pro"
    assert usb_detect.identify_model("TVS LP 46 Neo") == "tvs_lp46neo"
    assert usb_detect.identify_model("Zebra GK420") == "zebra"
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
