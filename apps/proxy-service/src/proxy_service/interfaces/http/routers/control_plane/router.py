"""Composite router for the Agent Control Plane.

Collects all control-plane sub-routers into a single mountable router.
main.py only needs:
    from proxy_service.interfaces.http.routers.control_plane import control_plane_router
    app.include_router(control_plane_router, prefix="/v1")
"""

from fastapi import APIRouter

from proxy_service.interfaces.http.routers.control_plane.agents import router as agents_router
from proxy_service.interfaces.http.routers.control_plane.config import packs_router
from proxy_service.interfaces.http.routers.control_plane.config import router as config_router
from proxy_service.interfaces.http.routers.control_plane.integration import router as integration_router
from proxy_service.interfaces.http.routers.control_plane.openclaw import router as openclaw_router
from proxy_service.interfaces.http.routers.control_plane.rollout import router as rollout_router
from proxy_service.interfaces.http.routers.control_plane.runtime import router as runtime_router
from proxy_service.interfaces.http.routers.control_plane.teams import router as teams_router
from proxy_service.interfaces.http.routers.control_plane.tools_roles import router as tools_roles_router
from proxy_service.interfaces.http.routers.control_plane.trace_runs import router as trace_runs_router
from proxy_service.interfaces.http.routers.control_plane.traces import router as traces_router
from proxy_service.interfaces.http.routers.control_plane.validation import router as validation_router

control_plane_router = APIRouter()
control_plane_router.include_router(agents_router)
control_plane_router.include_router(openclaw_router)
control_plane_router.include_router(tools_roles_router)
control_plane_router.include_router(config_router)
control_plane_router.include_router(packs_router)
control_plane_router.include_router(runtime_router)
control_plane_router.include_router(teams_router)
control_plane_router.include_router(integration_router)
control_plane_router.include_router(validation_router)
control_plane_router.include_router(rollout_router)
control_plane_router.include_router(traces_router)
control_plane_router.include_router(trace_runs_router)
