"""HTTP router composition for the proxy service."""

from __future__ import annotations

from fastapi import FastAPI

from proxy_service.interfaces.http.routers.analytics import router as analytics_router
from proxy_service.interfaces.http.routers.benchmark import router as benchmark_router
from proxy_service.interfaces.http.routers.chat import router as chat_router
from proxy_service.interfaces.http.routers.control_plane import control_plane_router
from proxy_service.interfaces.http.routers.direct import router as chat_direct_router
from proxy_service.interfaces.http.routers.health import router as health_router
from proxy_service.interfaces.http.routers.interventions import router as interventions_router
from proxy_service.interfaces.http.routers.models import router as models_router
from proxy_service.interfaces.http.routers.policies import router as policies_router
from proxy_service.interfaces.http.routers.requests import router as requests_router
from proxy_service.interfaces.http.routers.rules import router as rules_router
from proxy_service.interfaces.http.routers.scan import router as scan_router
from proxy_service.interfaces.http.routers.scenarios import router as scenarios_router


def include_routers(app: FastAPI) -> None:
    """Attach all public HTTP routers while preserving existing routes."""
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(chat_direct_router)
    app.include_router(models_router)
    app.include_router(control_plane_router, prefix="/v1")
    app.include_router(analytics_router, prefix="/v1")
    app.include_router(interventions_router, prefix="/v1")
    app.include_router(policies_router, prefix="/v1")
    app.include_router(requests_router, prefix="/v1")
    app.include_router(rules_router, prefix="/v1")
    app.include_router(scan_router)
    app.include_router(scenarios_router, prefix="/v1")
    app.include_router(benchmark_router, prefix="/v1")
