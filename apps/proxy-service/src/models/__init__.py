"""Models package — import all models so Alembic can detect them."""

from src.models.base import Base
from src.models.denylist import DenylistPhrase
from src.models.intervention import Intervention
from src.models.policy import Policy
from src.models.request import Request


def _register_control_plane_models() -> None:
    """Import control-plane models so Alembic's autogenerate sees them.

    Done as a function to avoid circular import at module load time
    (control_plane.models -> models.base is fine, but models.__init__ ->
    control_plane.models would trigger a loop).
    """
    import src.control_plane.models  # noqa: F401


_register_control_plane_models()

__all__ = ["Base", "DenylistPhrase", "Intervention", "Policy", "Request"]
