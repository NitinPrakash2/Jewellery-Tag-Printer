"""Diagnostics routes: live error/event monitor feed."""
from fastapi import APIRouter, Query

from app import diagnostics

router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])


@router.get("/events", response_model=dict)
def list_events(limit: int = Query(default=100, ge=1, le=200)):
    return {"events": diagnostics.get_events(limit)}


@router.delete("/events", response_model=dict)
def clear_events():
    diagnostics.clear()
    return {"ok": True}
