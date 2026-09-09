"""History repository — ORM only."""
from datetime import datetime

from sqlalchemy import desc, func, or_, select

from app.database.models import PrintHistory


def create(db, *, purity_huid, product_name, gross_weight, net_weight,
           copies, printer_name, template_version, status, error_message="") -> PrintHistory:
    row = PrintHistory(
        purity_huid=purity_huid.strip(),
        product_name=product_name.strip(),
        gross_weight=gross_weight,
        net_weight=net_weight,
        copies=copies,
        printer_name=printer_name or "",
        template_version=template_version,
        status=status,
        error_message=error_message or "",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_by_id(db, history_id: int) -> PrintHistory | None:
    return db.get(PrintHistory, history_id)


def search(db, *, q="", purity="", date_from=None, date_to=None, status="",
           limit=50, offset=0) -> tuple[list[PrintHistory], int]:
    stmt = select(PrintHistory)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(
            PrintHistory.product_name.ilike(like),
            PrintHistory.purity_huid.ilike(like),
        ))
    if purity:
        stmt = stmt.where(PrintHistory.purity_huid.ilike(f"%{purity}%"))
    if status:
        stmt = stmt.where(PrintHistory.status == status)
    if date_from:
        stmt = stmt.where(PrintHistory.printed_at >= date_from)
    if date_to:
        stmt = stmt.where(PrintHistory.printed_at <= date_to)
    count = db.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
    rows = db.execute(stmt.order_by(desc(PrintHistory.id)).limit(limit).offset(offset)).scalars().all()
    return list(rows), int(count)


def _day_bounds(day: datetime):
    start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta

    return start, start + timedelta(days=1)
