"""Settings repository — simple key/value over ORM. No seed writes."""
from sqlalchemy import select

from app.database.models import AppSetting


def get_all(db) -> dict[str, str]:
    rows = db.execute(select(AppSetting)).scalars().all()
    return {r.key: r.value for r in rows}


def upsert_many(db, values: dict[str, str]) -> None:
    for key, value in values.items():
        existing = db.execute(select(AppSetting).where(AppSetting.key == key)).scalar_one_or_none()
        if existing is None:
            db.add(AppSetting(key=key, value=value))
        else:
            existing.value = value
    db.commit()
