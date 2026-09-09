"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import routes_history, routes_print, routes_printers, routes_settings
from app.config import APP_ENV, get_cors_origins
from app.database.session import get_engine
from app.logging_setup import log


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        log.info("startup: database reachable")
    except Exception as exc:
        log.error("startup: database NOT reachable: %s", str(exc).split(chr(10))[0][:300])
    yield


app = FastAPI(title="Jewellery Tag Printer API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_history.router)
app.include_router(routes_settings.router)
app.include_router(routes_printers.router)
app.include_router(routes_print.router)


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


