"""FastAPI application factory for the proxy service."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from proxy_service.bootstrap.lifespan import lifespan
from proxy_service.bootstrap.routers import include_routers
from proxy_service.infrastructure.config import get_settings
from proxy_service.infrastructure.llm.exceptions import LLMError
from proxy_service.infrastructure.telemetry.logger import CorrelationIdMiddleware
from proxy_service.interfaces.http.schemas.chat import ErrorDetail, ErrorResponse


def create_app() -> FastAPI:
    """Create and wire the proxy FastAPI application."""
    settings = get_settings()
    app = FastAPI(
        title="Agent-Firewall - Proxy Service",
        description="LLM Firewall with agentic security pipeline",
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "x-client-id",
            "x-policy",
            "x-api-key",
            "x-correlation-id",
            "x-middlewares",
        ],
        expose_headers=[
            "x-decision",
            "x-intent",
            "x-risk-score",
            "x-pipeline",
            "x-correlation-id",
        ],
    )
    app.add_middleware(CorrelationIdMiddleware)
    include_routers(app)
    register_exception_handlers(app)
    return app


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(LLMError)
    async def llm_error_handler(_request: Request, exc: LLMError) -> JSONResponse:
        body = ErrorResponse(
            error=ErrorDetail(
                message=exc.message,
                type=exc.error_type,
                code=str(exc.status_code),
            )
        )
        return JSONResponse(status_code=exc.status_code, content=body.model_dump())
