"""Live diagnostics feed — every important event (errors AND key successes)
lands here with a plain-language message and a source tag, so the Settings
page can show a non-technical user exactly WHERE a problem is:
in the APP, the PRINTER, USB, SERVER or DATABASE.

Thread-safe in-memory ring buffer (last 200 events). No database needed —
if the DB itself is down, this still works.
"""
import logging
import threading
from collections import deque
from datetime import datetime, timezone

MAX_EVENTS = 200

_lock = threading.Lock()
_events: deque = deque(maxlen=MAX_EVENTS)


def record(source: str, level: str, message: str) -> dict:
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": source.upper(),
        "level": level.lower(),
        "message": str(message)[:500],
    }
    with _lock:
        _events.append(event)
    return event


def get_events(limit: int = 100) -> list[dict]:
    with _lock:
        items = list(_events)
    try:
        n = max(1, min(int(limit or 100), MAX_EVENTS))
    except (ValueError, TypeError):
        n = 100
    return items[-n:][::-1]  # newest first


def clear() -> None:
    with _lock:
        _events.clear()


class _FeedHandler(logging.Handler):
    """Auto-captures every WARNING+ from the app logger as an APP event,
    so no error can pass silently even if someone forgets record()."""

    def emit(self, entry) -> None:
        try:
            if entry.levelno < logging.WARNING:
                return
            record("APP", entry.levelname, entry.getMessage())
        except Exception:
            pass


_attached = False


def attach_to_app_logger() -> None:
    global _attached
    if _attached:
        return
    logger = logging.getLogger("tagprinter")
    for h in logger.handlers:
        if isinstance(h, _FeedHandler):
            _attached = True
            return
    logger.addHandler(_FeedHandler(level=logging.WARNING))
    _attached = True
