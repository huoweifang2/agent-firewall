"""GET /v1/models — available models catalog."""

from __future__ import annotations

import structlog
from fastapi import APIRouter

from proxy_service.infrastructure.llm.providers import EXTERNAL_MODELS
from proxy_service.interfaces.http.schemas.models import ModelInfo, ModelsResponse

logger = structlog.get_logger()

router = APIRouter(tags=["models"])


@router.get("/v1/models", response_model=ModelsResponse)
async def list_models() -> ModelsResponse:
    """Return catalog of available models.

    Static catalog of well-known external models

    External models are always listed — the frontend knows
    which providers have a key stored in browser SessionStorage.
    """

    models: list[ModelInfo] = []

    # External models catalog (always listed)
    models.extend(ModelInfo(**m) for m in EXTERNAL_MODELS)

    return ModelsResponse(models=models)
