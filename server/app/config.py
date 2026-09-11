"""Application configuration. All secrets come from environment — never hard-coded.

Dual database: the URL decides.
  - PostgreSQL (deploy / multi-user):
      DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/jewellery_tags
  - SQLite (desktop .exe, zero-install, single shop):
      DATABASE_URL=sqlite:///./app_data/tagprinter.db   (path is relative
      to the server folder; parent folders are created automatically)
"""
import os

from dotenv import load_dotenv

load_dotenv()


def get_database_url() -> str:
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/jewellery_tags",
    )
    return url


def is_sqlite(url: str = "") -> bool:
    return (url or get_database_url()).strip().lower().startswith("sqlite")


def get_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [o.strip() for o in raw.split(",") if o.strip()]


APP_ENV = os.getenv("APP_ENV", "dev")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
