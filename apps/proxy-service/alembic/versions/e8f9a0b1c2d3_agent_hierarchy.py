"""agent_hierarchy

Revision ID: e8f9a0b1c2d3
Revises: d5e6f7a8b9c0
Create Date: 2026-04-25 14:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8f9a0b1c2d3"
down_revision: str | Sequence[str] | None = "d5e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add explicit main/subagent hierarchy metadata."""
    agent_kind = sa.Enum("MAIN_AGENT", "SUB_AGENT", name="agent_kind")
    agent_created_from = sa.Enum("MANUAL", "SANDBOX_CHAT", "TEMPLATE", name="agent_created_from")
    agent_kind.create(op.get_bind(), checkfirst=True)
    agent_created_from.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "agents",
        sa.Column("agent_kind", agent_kind, nullable=False, server_default="MAIN_AGENT"),
    )
    op.add_column(
        "agents",
        sa.Column("created_from", agent_created_from, nullable=False, server_default="MANUAL"),
    )
    op.add_column("agents", sa.Column("template_key", sa.String(length=64), nullable=True))
    op.create_index("ix_agents_agent_kind", "agents", ["agent_kind"])


def downgrade() -> None:
    """Remove hierarchy metadata."""
    op.drop_index("ix_agents_agent_kind", table_name="agents")
    op.drop_column("agents", "template_key")
    op.drop_column("agents", "created_from")
    op.drop_column("agents", "agent_kind")

    sa.Enum(name="agent_created_from").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="agent_kind").drop(op.get_bind(), checkfirst=True)
