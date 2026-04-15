"""Pydantic schemas for the models catalog endpoint."""

from __future__ import annotations

from pydantic import BaseModel


class ModelInfo(BaseModel):
    """A single model entry in the catalog."""

    id: str  # e.g. "deepseek/deepseek-chat" or "openai/gpt-4"
    provider: str  # "openai", "anthropic", "google", "mistral"
    name: str  # Human-readable: "GPT-4o", "Llama 3.1 8B"


class ModelsResponse(BaseModel):
    """Response for GET /v1/models."""

    models: list[ModelInfo]
