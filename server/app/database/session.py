"""SQLAlchemy engine/session. No raw SQL in UI layers — all access via ORM.

Works on PostgreSQL (deploy) and SQLite (desktop .exe) — the DATABASE_URL
decides. For SQLite the file's parent folder is created automatically and
the engine is set for multi-threaded desktop use.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import get_database_url, is_sqlite

Base = declarative_base()

_engine = None
_SessionLocal = None


def _prepare_sqlite_file(url: str) -> None:
    # sqlite:///./app_data/tagprinter.db -> ensure ./app_data exists.
    # Relative paths resolve from the server folder (process CWD).
    path = url.split("sqlite:///", 1)[-1].split("?")[0]
    if path and path != ":memory:":
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)


def get_engine():
    global _engine
    if _engine is None:
        url = get_database_url()
        if is_sqlite(url):
            _prepare_sqlite_file(url)
            _engine = create_engine(
                url,
                future=True,
                connect_args={"check_same_thread": False},
                pool_pre_ping=True,
            )
        else:
            _engine = create_engine(url, pool_pre_ping=True, future=True)
    return _engine


def reset_engine() -> None:
    """For tests only — drop the cached engine so a new URL takes effect."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)
    return _SessionLocal


def get_db():
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all():
    from app.database import models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())
