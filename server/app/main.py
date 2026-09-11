"""FastAPI application entrypoint.

Serves BOTH the API (/api/...) and the built client (/) from one port, so a
single URL works from any laptop on the network:
    http://<shop-pc-ip>:8000   ->   full app (prints on this PC's printer)

LAN mode: set CORS_ORIGINS=* and bind uvicorn --host 0.0.0.0 (see start-lan.bat).
WARNING: LAN mode has no login — anyone on the network can print. Never put
this directly on the public internet without adding authentication.
"""
from contextlib import asynccontextmanager
from pathlib import Path
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api import routes_diagnostics, routes_history, routes_print, routes_printers, routes_settings
from app.config import APP_ENV, get_cors_origins
from app.database.session import get_engine
from app.diagnostics import attach_to_app_logger, record
from app.logging_setup import log

attach_to_app_logger()

CLIENT_DIST = (
    Path(os.environ["CLIENT_DIST_DIR"])
    if os.getenv("CLIENT_DIST_DIR")
    else Path(__file__).resolve().parent.parent.parent / "client" / "dist"
)


def _lan_ip() -> str:
    import socket

    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "127.0.0.1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        log.info("startup: database reachable")
    except Exception as exc:
        msg = str(exc).split(chr(10))[0][:300]
        log.error("startup: database NOT reachable: %s", msg)
        record("DATABASE", "error", f"Database not reachable at startup. {msg}")
    log.info("open the app at http://%s:8000 (this PC) or http://localhost:8000", _lan_ip())
    yield


app = FastAPI(title="Jewellery Tag Printer API", version="0.1.0", lifespan=lifespan)

_cors = get_cors_origins()
if "*" in _cors:
    # LAN mode: any laptop on the network may call the API. Our fetch uses
    # no cookies, so wildcard without credentials is correct and safe here.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        log.info("startup: database reachable")
    except Exception as exc:
        msg = str(exc).split(chr(10))[0][:300]
        log.error("startup: database NOT reachable: %s", msg)
        record("DATABASE", "error", f"Database not reachable at startup. {msg}")
    yield


app.include_router(routes_history.router)
app.include_router(routes_settings.router)
app.include_router(routes_printers.router)
app.include_router(routes_print.router)
app.include_router(routes_diagnostics.router)


@app.get("/api/health")
def health():
    db_ok = False
    db_error = ""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        db_error = str(exc).split("\n")[0][:300]
        log.error("health: database unavailable: %s", db_error)
    out = {"ok": True, "app": "jewellery-tag-printer", "env": APP_ENV, "db_ok": db_ok}
    if not db_ok:
        out["ok"] = False
        out["db_error"] = db_error
        out["hint"] = "Check DATABASE_URL and that PostgreSQL is running."
    return out


# ---- Built client (single-URL mode) ---------------------------------------
# Served AFTER all /api routes so API calls always win over static files.
if CLIENT_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=CLIENT_DIST / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def _index():
        return FileResponse(CLIENT_DIST / "index.html")

    @app.get("/{path:path}", include_in_schema=False)
    def _spa_or_file(path: str):
        target = (CLIENT_DIST / path) if path else None
        if target is not None:
            try:
                if target.is_file() and CLIENT_DIST in target.resolve().parents:
                    return FileResponse(target)
            except (OSError, RuntimeError):
                pass
        return FileResponse(CLIENT_DIST / "index.html")
else:
    log.warning("client dist not found at %s — API-only mode (run npm run build)", CLIENT_DIST)


