"""HTTP Client — sends attack prompts to target endpoints."""

from proxy_service.domain.red_team.engine.http_client.client import (
    HttpResponse,
    TargetEndpoint,
    send_prompt,
)

__all__ = [
    "HttpResponse",
    "TargetEndpoint",
    "send_prompt",
]
