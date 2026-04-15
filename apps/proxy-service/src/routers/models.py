"""GET /v1/models — available models catalog."""

from __future__ import annotations

import httpx
import structlog
from fastapi import APIRouter

from src.config import get_settings
from src.llm.providers import EXTERNAL_MODELS
from src.schemas.models import ModelInfo, ModelsResponse

logger = structlog.get_logger()

router = APIRouter(tags=["models"])



@router.get("/v1/models", response_model=ModelsResponse)
async def list_models() -> ModelsResponse:
    """Return catalog of available models.

    Static catalog of well-known external models

    External models are always listed — the frontend knows
    which providers have a key stored in browser SessionStorage.
    """
    settings = get_settings()

    models: list[ModelInfo] = []

    # External models catalog (always listed)
    models.extend(ModelInfo(**m) for m in EXTERNAL_MODELS)


    return ModelsResponse(models=models)
