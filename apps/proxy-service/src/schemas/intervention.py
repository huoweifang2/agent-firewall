"""Schemas for operator intervention approvals."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

InterventionKind = Literal["input_block", "tool_confirmation", "tool_block"]
InterventionStatus = Literal["pending", "approved", "rejected", "completed", "failed"]


class InterventionCreate(BaseModel):
    source: str = Field(default="telegram", max_length=64)
    account: str | None = Field(default=None, max_length=128)
    chat_id: str | None = Field(default=None, max_length=128)
    session_id: str = Field(..., min_length=1, max_length=128)
    kind: InterventionKind
    message: str = Field(default="", max_length=4096)
    policy: str | None = Field(default=None, max_length=64)
    model: str | None = Field(default=None, max_length=128)
    reason: str | None = None
    risk_score: float | None = Field(default=None, ge=0, le=1)
    tool_payload: dict | None = None
    trace_id: str | None = Field(default=None, max_length=128)


class InterventionUpdate(BaseModel):
    status: InterventionStatus
    decided_by: str | None = Field(default=None, max_length=128)
    decision_note: str | None = None
    result_payload: dict | None = None


class InterventionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    account: str | None = None
    chat_id: str | None = None
    session_id: str
    kind: str
    status: str
    message: str
    policy: str | None = None
    model: str | None = None
    reason: str | None = None
    risk_score: float | None = None
    tool_payload: dict | None = None
    trace_id: str | None = None
    result_payload: dict | None = None
    decided_by: str | None = None
    decision_note: str | None = None
    created_at: datetime
    updated_at: datetime


class InterventionListResponse(BaseModel):
    items: list[InterventionRead]
    total: int
    limit: int
    offset: int
