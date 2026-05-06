"""Pydantic schemas for health endpoint."""

from __future__ import annotations

from pydantic import BaseModel


class ServiceHealth(BaseModel):
    """Health status of a single service."""

    status: str  # "ok" | "error" | "skipped"
    detail: str | None = None


class SystemMetrics(BaseModel):
    """Real-time system resource metrics."""

    # Memory
    memory_used_mb: float
    memory_total_mb: float
    memory_percent: float

    # CPU
    cpu_percent: float

    # Disk
    disk_used_gb: float
    disk_total_gb: float
    disk_percent: float

    # Process
    uptime_seconds: float
    pid: int
    open_files: int
    threads: int

    # App
    total_requests: int


class HealthResponse(BaseModel):
    """Response for GET /health."""

    status: str  # "ok" | "degraded"
    mode: str = "dev"  # "dev" | "real"
    services: dict[str, ServiceHealth]
    version: str
    metrics: SystemMetrics | None = None


class RuntimeConfigResponse(BaseModel):
    """Redacted runtime configuration exposed to the local console."""

    database_kind: str
    database_url_safe: str
    sqlite_path: str | None = None
    cache_mode: str
    redis_configured: bool = False
    langfuse_enabled: bool = False
