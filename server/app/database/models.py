"""ORM models. Weights use NUMERIC; timestamps use TIMESTAMPTZ."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def _utcnow():
    return datetime.now(timezone.utc)


class PrintHistory(Base):
    __tablename__ = "print_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purity_huid: Mapped[str] = mapped_column(String(120), nullable=False)
    product_name: Mapped[str] = mapped_column(String(120), nullable=False)
    gross_weight: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    net_weight: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    copies: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    printer_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    template_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    printed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class AppSetting(Base):
    """Generic key/value store: key like 'shop.name', 'printer.selected', ..."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
