"""Desktop entrypoint: backend API + app window in one double-clickable program.

Usage:
  python desktop.py                 -> backend + window (dev)
  python desktop.py --smoke-test    -> boot backend, hit /, /api/health,
                                       /api/printers, then exit (headless CI/exe check)
  ManishTagPrinter.exe              -> same as default (frozen)

Database rule (dual mode, same as server):
  - DATABASE_URL env set      -> that database (PostgreSQL on deploy)
  - frozen .exe, nothing set  -> SQLite file next to the exe (zero-install)
  - dev, nothing set          -> default from app.config (PostgreSQL)
"""
import os
import sys
import threading

APP_TITLE = "Manish Ornaments — Tag Printer"
PORT = int(os.getenv("APP_PORT", "8000"))


def _base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))  # server/


BASE_DIR = _base_dir()

if getattr(sys, "frozen", False):
    # Windowed frozen apps have sys.stdout/sys.stderr = None. ANY library
    # that prints or warns (svglib, reportlab, ...) then crashes with
    # "'NoneType' object has no attribute 'write'". Restore real streams.
    try:
        _logdir = os.path.join(BASE_DIR, "logs")
        os.makedirs(_logdir, exist_ok=True)
        _out = open(os.path.join(_logdir, "stdout.log"), "a", encoding="utf-8")
        if sys.stdout is None:
            sys.stdout = _out
        if sys.stderr is None:
            sys.stderr = _out
    except Exception:
        pass

# Make bundled + relative paths (app_data, logs, client/dist) resolve.
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
try:
    os.chdir(BASE_DIR)
except OSError:
    pass

if not os.getenv("DATABASE_URL") and getattr(sys, "frozen", False):
    db_file = os.path.join(BASE_DIR, "app_data", "tagprinter.db")
    os.environ["DATABASE_URL"] = "sqlite:///" + db_file.replace("\\", "/")


def _resource(name: str) -> str:
    """Bundled read-only files: _internal/ when frozen, server/ in dev."""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, name)
    return os.path.join(BASE_DIR, name)


if getattr(sys, "frozen", False):
    # Tell the app layer where PyInstaller 6 actually placed the bundle.
    os.environ.setdefault("CLIENT_DIST_DIR", _resource(os.path.join("client", "dist")))


def _sqlite_db_path(url: str) -> str:
    path = url.split("sqlite:///", 1)[-1].split("?")[0]
    if not os.path.isabs(path):
        path = os.path.join(BASE_DIR, path)
    return os.path.normpath(path)


def _migrate_sqlite(db_path: str) -> None:
    """Bring old exe databases up to the current schema.

    create_all() never alters existing tables, so schema changes that
    need column changes (e.g. weights becoming nullable in v2) are
    applied here with a data-preserving table rebuild. A .bak copy is
    kept next to the database first.
    """
    import shutil
    import sqlite3

    if not os.path.isfile(db_path):
        return
    con = sqlite3.connect(db_path)
    try:
        cols = {r[1]: r for r in con.execute("PRAGMA table_info(print_history)").fetchall()}
        if not cols:
            return
        # name index: 0=cid,1=name,2=type,3=notnull,4=default,5=pk
        needs = cols.get("gross_weight", [None] * 4)[3] == 1 or cols.get("net_weight", [None] * 4)[3] == 1
        if not needs:
            return
        bak = db_path + ".bak"
        shutil.copy2(db_path, bak)
        col_defs = []
        for cid, name, ctype, notnull, default, pk in con.execute("PRAGMA table_info(print_history)").fetchall():
            if name in ("gross_weight", "net_weight"):
                notnull = 0
            d = f'"{name}" {ctype}'
            if pk:
                d += " PRIMARY KEY AUTOINCREMENT" if ctype.upper() == "INTEGER" else " PRIMARY KEY"
            if notnull:
                d += " NOT NULL"
            if default is not None:
                d += f" DEFAULT {default}"
            col_defs.append(d)
        names = ", ".join(f'"{r[1]}"' for r in con.execute("PRAGMA table_info(print_history)").fetchall())
        con.execute("BEGIN")
        con.execute(f"CREATE TABLE print_history_new ({', '.join(col_defs)})")
        con.execute(f"INSERT INTO print_history_new ({names}) SELECT {names} FROM print_history")
        con.execute("DROP TABLE print_history")
        con.execute("ALTER TABLE print_history_new RENAME TO print_history")
        con.execute("COMMIT")
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        con.close()


def _init_db() -> None:
    from app.config import get_database_url, is_sqlite

    url = get_database_url()
    if is_sqlite(url):
        from app.database.session import create_all

        _migrate_sqlite(_sqlite_db_path(url))
        create_all()  # idempotent — safe on every launch
        return
    # PostgreSQL: proper migrations.
    try:
        from alembic import command
        from alembic.config import Config

        cfg = Config(_resource("alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
        cfg.set_main_option("script_location", _resource("alembic"))
        command.upgrade(cfg, "head")
    except Exception as exc:
        from app.logging_setup import log

        log.error("startup migrations failed: %s", exc)
        raise


_server_errors: list[str] = []


def _start_backend() -> str:
    import threading
    import traceback

    import uvicorn

    # NOTE: the app OBJECT (not "app.main:app" string) — uvicorn's own
    # module importer is unreliable once frozen, while a plain import here
    # provably works (DB init above already imports app.*).
    from app.main import app as asgi_app

    # log_config=None: uvicorn's own dictConfig breaks when frozen;
    # the app has its own rotating file logging (see app/logging_setup.py).
    config = uvicorn.Config(asgi_app, host="127.0.0.1", port=PORT,
                            log_level="warning", log_config=None, access_log=False)
    server = uvicorn.Server(config)

    def _run() -> None:
        try:
            server.run()
        except Exception:
            _server_errors.append(traceback.format_exc())

    thread = threading.Thread(target=_run, daemon=True, name="uvicorn")
    thread.start()
    return f"http://127.0.0.1:{PORT}/"


def _wait_ready(url: str, timeout: float = 30.0) -> bool:
    import time
    import urllib.request

    deadline = time.time() + timeout
    last: str = ""
    tries = 0
    while time.time() < deadline:
        tries += 1
        try:
            with urllib.request.urlopen(url + "api/health", timeout=2) as r:
                if r.status == 200:
                    return True
                last = f"HTTP {r.status}"
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(0.3)
    _server_errors.append(f"health poll failed after {tries} tries, last: {last}")
    return False


def _smoke_raster(say) -> bool:
    """Prove the frozen raster engine works (missing backends fail here,
    exactly like the real print path would)."""
    try:
        from app.printing.raster import svg_to_png_bytes
        from app.tag.renderer import build_tag_svg
        from app.tag.units import mm_to_dots
    except Exception as exc:
        say(f"SMOKE FAIL raster imports: {exc}")
        return False
    try:
        svg = build_tag_svg("18Kt HUID", "Ring", "2.146", "2.146",
                            width_mm=100, height_mm=15, tail_mm=35,
                            shop_name="Manish Ornaments", has_logo=False)
        png = svg_to_png_bytes(svg, 100, 15)
        import io as _io

        from PIL import Image as _Image

        got = _Image.open(_io.BytesIO(png)).size
        want = (mm_to_dots(100), mm_to_dots(15))
        say(f"SMOKE raster -> {got} (want {want})")
        return got == want
    except Exception as exc:
        import traceback as _tb

        say(f"SMOKE FAIL raster: {exc}\n{_tb.format_exc()}")
        return False


def smoke_test() -> int:
    """Headless boot check for CI and frozen-exe verification."""
    import json
    import traceback
    import urllib.request

    lines: list[str] = []

    def say(msg: str) -> None:
        lines.append(msg)
        print(msg, flush=True)

    code = 1
    try:
        _init_db()
        say("SMOKE db init ok")
        url = _start_backend()
        # Give the server thread a moment; surface an early crash verbatim.
        import time as _time

        _time.sleep(3.0)
        alive = any(t.name == "uvicorn" and t.is_alive() for t in threading.enumerate())
        if not alive and _server_errors:
            say("SMOKE FAIL server thread died:\n" + _server_errors[-1])
            return 1
        if not _wait_ready(url, timeout=60.0):
            say("SMOKE FAIL: backend did not become ready")
            if _server_errors:
                say(_server_errors[-1])
            alive_now = [t.name for t in threading.enumerate() if t.name == "uvicorn" and t.is_alive()]
            say(f"uvicorn thread alive at end: {bool(alive_now)}")
            try:
                import socket as _s

                s = _s.create_connection(("127.0.0.1", PORT), timeout=3)
                say("TCP connect to 127.0.0.1:8000: OPEN (listening, app not responding?)")
                s.close()
            except Exception as exc2:
                say(f"TCP connect to 127.0.0.1:8000: {exc2} (nothing listening)")
            return 1
        checks = ["/", "/api/health", "/api/printers", "/api/settings"]
        ok = True
        for path in checks:
            try:
                with urllib.request.urlopen(url.rstrip("/") + path, timeout=10) as r:
                    say(f"SMOKE OK  {path} -> {r.status}")
                    if path == "/api/health":
                        body = json.loads(r.read().decode())
                        say(f"SMOKE health: {body}")
                        ok = ok and bool(body.get("db_ok"))
            except Exception as exc:
                say(f"SMOKE FAIL {path}: {exc}")
                ok = False
        ok = _smoke_raster(say) and ok
        say("SMOKE PASS" if ok else "SMOKE FAIL")
        code = 0 if ok else 1
        return code
    except Exception:
        say("SMOKE FAIL exception:\n" + traceback.format_exc())
        return 1
    finally:
        try:
            with open(os.path.join(BASE_DIR, "smoke-result.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + f"\nEXIT:{code}\n")
        except OSError:
            pass


def run_gui(url: str) -> int:
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QIcon
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    win = QMainWindow()
    win.setWindowTitle(APP_TITLE)
    icon = os.path.join(BASE_DIR, "client", "dist", "Favicon.jpeg")
    if os.path.isfile(icon):
        win.setWindowIcon(QIcon(icon))
    view = QWebEngineView()
    win.setCentralWidget(view)
    win.resize(1280, 860)
    win.showMaximized()
    view.setUrl(QUrl(url))
    return app.exec()


def main() -> int:
    if "--smoke-test" in sys.argv:
        return smoke_test()
    _init_db()
    url = _start_backend()
    if not _wait_ready(url):
        print("Backend did not start. See logs/server output for details.")
        return 1
    return run_gui(url)


if __name__ == "__main__":
    raise SystemExit(main())
