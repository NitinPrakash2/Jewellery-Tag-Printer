"""Pydantic request/response schemas for the API layer."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class TagPrintRequest(BaseModel):
    purity_huid: str = Field(..., max_length=120)
    product_name: str = Field(..., max_length=120)
    gross_weight: Decimal
    net_weight: Decimal
    copies: int = Field(default=1, ge=1, le=99)
    printer_name: Optional[str] = ""


class HistoryOut(BaseModel):
    id: int
    purity_huid: str
    product_name: str
    gross_weight: Decimal
    net_weight: Decimal
    copies: int
    printer_name: str
    template_version: str
    status: str
    error_message: str
    printed_at: datetime

    model_config = {"from_attributes": True}


class TagRenderRequest(BaseModel):
    purity_huid: str = ""
    product_name: str = ""
    gross_weight: Optional[Decimal] = None
    net_weight: Optional[Decimal] = None
    shop_name: Optional[str] = None
    tag_width_mm: Optional[float] = None
    tag_height_mm: Optional[float] = None


class TestPrintRequest(BaseModel):
    printer_name: Optional[str] = ""


class PrintResultOut(BaseModel):
    ok: bool
    message: str
    history_id: Optional[int] = None
    front_svg: Optional[str] = None
    back_svg: Optional[str] = None
