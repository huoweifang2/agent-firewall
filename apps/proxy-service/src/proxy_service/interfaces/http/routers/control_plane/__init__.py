"""HTTP router assembly for the Agent Control Plane."""

from proxy_service.infrastructure.persistence.control_plane_seed import seed_control_plane
from proxy_service.interfaces.http.routers.control_plane.router import control_plane_router

__all__ = ["control_plane_router", "seed_control_plane"]
