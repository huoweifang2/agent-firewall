"""Compatibility aliases for the renamed Agent Control Plane package.

New code should import from ``proxy_service.interfaces.http.routers.control_plane``. This package remains so
older integrations using ``src.wizard`` resolve to the same module objects.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType

_ALIASES = (
    "models",
    "schemas",
    "schema_compat",
    "routers",
    "routers.agents",
    "routers.config",
    "routers.integration",
    "routers.openclaw",
    "routers.rollout",
    "routers.runtime",
    "routers.teams",
    "routers.tools_roles",
    "routers.trace_runs",
    "routers.traces",
    "routers.validation",
    "services",
    "services.config_gen",
    "services.gate",
    "services.integration_kit",
    "services.openclaw",
    "services.permissions",
    "services.policy_packs",
    "services.risk",
    "services.runtime_spec",
    "services.tools",
    "services.trace_recorder",
    "services.validation_runner",
)

for _suffix in _ALIASES:
    _module = importlib.import_module(f"proxy_service.interfaces.http.routers.control_plane.{_suffix}")
    sys.modules[f"{__name__}.{_suffix}"] = _module
    if "." not in _suffix:
        globals()[_suffix] = _module

from proxy_service.infrastructure.persistence.control_plane_seed import (  # noqa: E402
    REFERENCE_AGENT,
    seed_reference_agent,
    seed_reference_tools_and_roles,
)
from proxy_service.interfaces.http.routers.control_plane import control_plane_router, seed_control_plane  # noqa: E402

wizard_router = control_plane_router
seed_wizard = seed_control_plane

router = ModuleType(f"{__name__}.router")
router.control_plane_router = control_plane_router
router.wizard_router = control_plane_router
sys.modules[f"{__name__}.router"] = router

seed = ModuleType(f"{__name__}.seed")
seed.seed_control_plane = seed_control_plane
seed.seed_wizard = seed_control_plane
seed.REFERENCE_AGENT = REFERENCE_AGENT
seed.seed_reference_agent = seed_reference_agent
seed.seed_reference_tools_and_roles = seed_reference_tools_and_roles
sys.modules[f"{__name__}.seed"] = seed

__all__ = ["control_plane_router", "seed_control_plane", "wizard_router", "seed_wizard"]
