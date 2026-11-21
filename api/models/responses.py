"""Pydantic response models for the documented HOSPITAL 360 API contract.

The models describe response *shape* only. KPI formulas and semantics remain the
single authoritative responsibility of the Phase 2 canonical KPI contract.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any = None
    generated_at: str


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class Pagination(BaseModel):
    model_config = ConfigDict(extra="allow")

    page: int
    page_size: int
    max_page_size: int | None = None
    total_records: int
    total_pages: int


class ResponseMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    date_from: str | None = None
    date_to: str | None = None
    hospital_ids: list[str] = Field(default_factory=list)
    generated_at: str
    pagination: Pagination | None = None
    filters_applied: dict[str, Any] | None = None


class KpiValue(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    label: str
    value: float | int | str | None = None
    previous: float | int | str | None = None
    change_pct: float | None = None
    trend: str | None = None
    favourable: str | None = None
    unit: str
    precision: int | None = None
    sparkline: list[float | int | None] = Field(default_factory=list)
    definition: str | None = None
    higher_is_better: bool | None = None
    date_filter_available: bool | None = None
    date_filter_note: str | None = None


class KpiEnvelope(BaseModel):
    model_config = ConfigDict(extra="allow")

    data: dict[str, KpiValue]
    metadata: ResponseMetadata
    pagination: Pagination | None = None


class TableItem(BaseModel):
    model_config = ConfigDict(extra="allow")


class PaginatedEnvelope(BaseModel):
    model_config = ConfigDict(extra="allow")

    data: list[TableItem]
    metadata: ResponseMetadata
    pagination: Pagination


class ChartEnvelope(BaseModel):
    model_config = ConfigDict(extra="allow")

    data: Any
    metadata: ResponseMetadata
    pagination: Pagination | None = None
