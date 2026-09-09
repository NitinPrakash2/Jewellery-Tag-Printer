"""One-click printer setup tests (real Windows print server, temp form, reverted)."""
import win32print

from app.printing import windows_spool

PRINTER = "Microsoft Print to PDF"
W, H = 13.7, 9.1
FORM = windows_spool.form_name_for(W, H)


def _cleanup():
    srv = win32print.OpenPrinter(None)
    try:
        try:
            win32print.DeleteForm(srv, FORM)
        except Exception:
            pass
    finally:
        win32print.ClosePrinter(srv)


def test_form_name():
    assert windows_spool.form_name_for(110, 12) == "JewelleryTag 110x12mm"
    assert windows_spool.form_name_for(13.7, 9.1) == "JewelleryTag 13.7x9.1mm"


def test_ensure_label_size_creates_and_sets():
    hp = win32print.OpenPrinter(PRINTER)
    try:
        try:
            original = win32print.GetPrinter(hp, 9).get("pDevMode")
        except Exception:
            original = None
    finally:
        win32print.ClosePrinter(hp)
    try:
        res = windows_spool.ensure_label_size(PRINTER, W, H)
        assert res["ok"] is True, res
        assert res["form_name"] == FORM
        srv = win32print.OpenPrinter(None)
        try:
            assert FORM in {f.get("Name") for f in win32print.EnumForms(srv)}
        finally:
            win32print.ClosePrinter(srv)
        hp2 = win32print.OpenPrinter(PRINTER)
        try:
            back = win32print.GetPrinter(hp2, 9)["pDevMode"]
            assert back.FormName == FORM
            assert back.PaperWidth == 137
            assert back.PaperLength == 91
        finally:
            win32print.ClosePrinter(hp2)
    finally:
        # revert per-user devmode + remove temp form
        try:
            hp3 = win32print.OpenPrinter(PRINTER)
            try:
                if original is not None:
                    win32print.SetPrinter(hp3, 9, {"pDevMode": original}, 0)
            finally:
                win32print.ClosePrinter(hp3)
        finally:
            _cleanup()


def test_ensure_rejects_bad_dims():
    assert windows_spool.ensure_label_size(PRINTER, 0, 12)["ok"] is False
    assert windows_spool.ensure_label_size("", 110, 12)["ok"] is False


def test_setup_endpoint(client):
    hp = win32print.OpenPrinter(PRINTER)
    try:
        try:
            original = win32print.GetPrinter(hp, 9).get("pDevMode")
        except Exception:
            original = None
    finally:
        win32print.ClosePrinter(hp)
    try:
        r = client.post("/api/printers/setup", json={
            "printer_name": PRINTER, "width_mm": W, "height_mm": H})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True, body
        assert [s["key"] for s in body["steps"]] == ["detect", "label_size", "ready"]
    finally:
        try:
            hp3 = win32print.OpenPrinter(PRINTER)
            try:
                if original is not None:
                    win32print.SetPrinter(hp3, 9, {"pDevMode": original}, 0)
            finally:
                win32print.ClosePrinter(hp3)
        finally:
            _cleanup()


def test_setup_unknown_printer(client):
    r = client.post("/api/printers/setup", json={
        "printer_name": "No Such Printer XYZ", "width_mm": 110, "height_mm": 12})
    assert r.status_code == 200
    assert r.json()["ok"] is False


def test_driver_help(client):
    r = client.get("/api/printers/driver-help")
    drivers = r.json()["drivers"]
    assert "tvselectronics.in" in drivers["tvs_lp46neo"]["download_url"]
    assert "dcodeinternational.in" in drivers["dcode_dc423pro"]["download_url"]


def test_status_carries_max_width(client):
    r = client.get("/api/printers/status", params={"name": "DCode DC423 Pro"})
    assert r.json()["max_print_width_mm"] == 104
    r2 = client.get("/api/printers/status", params={"name": "TVS LP 46 Neo"})
    assert r2.json()["max_print_width_mm"] == 108
    r3 = client.get("/api/printers/status", params={"name": "Some Unknown Printer"})
    assert r3.json()["max_print_width_mm"] is None
