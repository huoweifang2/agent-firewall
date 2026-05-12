"""Human intervention queue for Telegram-first Agent-Firewall."""

from __future__ import annotations

from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from proxy_service.infrastructure.persistence.models.base import JSON_VARIANT, Base, TimestampMixin, UUIDMixin


class Intervention(UUIDMixin, TimestampMixin, Base):
    """Operator approval item created when the firewall pauses execution."""

    __tablename__ = "interventions"

    source: Mapped[str] = mapped_column(String(64), nullable=False, default="telegram", index=True)
    account: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    chat_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)

    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    policy: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    tool_payload: Mapped[dict | None] = mapped_column(JSON_VARIANT, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    result_payload: Mapped[dict | None] = mapped_column(JSON_VARIANT, nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Intervention kind={self.kind!r} status={self.status!r} session={self.session_id!r}>"
