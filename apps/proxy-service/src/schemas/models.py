"""Pydantic schemas for the models catalog endpoint."""

from __future__ import annotations

from pydantic import BaseModel


class ModelInfo(BaseModel):
    """A single model entry in the catalog."""

    id: str  # e.g. "deepseek-chat"
    provider: str  # "deepseek"
    name: str  # Human-readable: "DeepSeek Chat"


class ModelsResponse(BaseModel):
    """Response for GET /v1/models."""

    models: list[ModelInfo]
