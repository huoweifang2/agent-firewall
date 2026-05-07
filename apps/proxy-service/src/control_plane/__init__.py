"""Agent Control Plane — self-contained module for agent control.

This package owns all models, schemas, routers, services, and seeds
related to protected agent registration, OpenClaw bindings, runtime specs,
roles, tools, skills, rollout, and traces.

Usage in main.py:
    from src.control_plane import control_plane_router, seed_control_plane
    app.include_router(control_plane_router, prefix="/v1")
    await seed_control_plane()
"""

from src.control_plane.router import control_plane_router
from src.control_plane.seed import seed_control_plane

__all__ = ["control_plane_router", "seed_control_plane"]
