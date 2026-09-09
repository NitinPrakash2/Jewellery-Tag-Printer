"""History service — search/filter + reprint data loading."""
from datetime import datetime, timedelta, timezone

from app.database.repositories import history_repo


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def resolve_preset(preset: str) -> tuple[datetime | None, datetime | None]:
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if preset == "today":
        return today, today + timedelta(days=1)
    if preset == "yesterday":
        return today - timedelta(days=1), today
    if preset == "week":
        return today - timedelta(days=7), None
    if preset == "month":
        return today - timedelta(days=30), None
    return None, None


def list_history(db, *, q="", purity="", preset="", date_from=None, date_to=None,
                 status="", limit=50, offset=0):
    if preset:
        p_from, p_to = resolve_preset(preset)
        date_from = date_from or p_from
        if preset != "week" or date_to is None:
            date_to = date_to or p_to
    else:
        date_from = _parse_dt(date_from) if isinstance(date_from, str) else date_from
        date_to = _parse_dt(date_to) if isinstance(date_to, str) else date_to
    limit = max(1, min(int(limit or 50), 200))
    offset = max(0, int(offset or 0))
    return history_repo.search(db, q=q or "", purity=purity or "",
                               date_from=date_from, date_to=date_to,
                               status=status or "", limit=limit, offset=offset)
