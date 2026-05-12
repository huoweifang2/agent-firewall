"""FastAPI dependency injection helpers."""

from proxy_service.infrastructure.persistence.session import get_db, get_redis

__all__ = ["get_db", "get_redis"]
