"""Models package — import all models so Alembic can detect them."""

from proxy_service.infrastructure.persistence.models.base import Base
from proxy_service.infrastructure.persistence.models.denylist import DenylistPhrase
from proxy_service.infrastructure.persistence.models.intervention import Intervention
from proxy_service.infrastructure.persistence.models.policy import Policy
from proxy_service.infrastructure.persistence.models.request import Request


def _register_control_plane_models() -> None:
    """Import control-plane models so Alembic's autogenerate sees them.

    Done as a function to avoid circular import at module load time
    (control_plane.models -> models.base is fine, but models.__init__ ->
    control_plane.models would trigger a loop).
    """
    import proxy_service.domain.control_plane.models  # noqa: F401


def _register_red_team_models() -> None:
    """Import red-team models so table metadata is registered."""
    import proxy_service.infrastructure.persistence.red_team.models  # noqa: F401


_register_control_plane_models()
_register_red_team_models()

__all__ = ["Base", "DenylistPhrase", "Intervention", "Policy", "Request"]
