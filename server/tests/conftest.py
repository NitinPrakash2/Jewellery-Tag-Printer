"""Pytest setup: isolated test DB (Postgres OR SQLite), no seed data,
tables truncated per test. Set DATABASE_URL to run on either backend."""
import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/jewellery_tags_test")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database.session import Base
import app.database.models  # noqa: F401
from app.database.session import get_db
from app.main import app


def _test_url():
    return os.environ["DATABASE_URL"]


@pytest.fixture(scope="session")
def engine():
    url = _test_url()
    if url.strip().lower().startswith("sqlite"):
        # Fresh file per run for determinism.
        path = url.split("sqlite:///", 1)[-1].split("?")[0]
        if path and path != ":memory:" and os.path.isfile(path):
            os.remove(path)
        eng = create_engine(url, future=True, connect_args={"check_same_thread": False})
    else:
        # Create the test database if missing (connect to postgres db)
        base = url.rsplit("/", 1)[0] + "/postgres"
        eng0 = create_engine(base, isolation_level="AUTOCOMMIT")
        with eng0.connect() as conn:
            exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname='jewellery_tags_test'")).scalar()
            if not exists:
                conn.execute(text("CREATE DATABASE jewellery_tags_test"))
        eng = create_engine(url, future=True)
    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine):
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = TestingSession()
    yield session
    session.close()
    # Truncate all tables after each test — no leftover / seed data
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture()
def client(db):
    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
