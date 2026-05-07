"""Development schema compatibility helpers for control-plane tables."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine


async def ensure_agent_hierarchy_columns(engine: AsyncEngine) -> None:
    """Add hierarchy columns when dev DBs were created before this migration.

    Production should still use Alembic. This mirrors the existing dev
    convenience of ``Base.metadata.create_all`` by handling additive columns.
    """
    async with engine.begin() as conn:
        dialect = conn.dialect.name
        if dialect == "postgresql":
            await conn.execute(
                sa.text(
                    """
                    DO $$ BEGIN ALTER TYPE agent_framework ADD VALUE IF NOT EXISTS 'openclaw';
                    EXCEPTION WHEN undefined_object THEN null; END $$;
                    DO $$ BEGIN ALTER TYPE protection_level ADD VALUE IF NOT EXISTS 'openclaw';
                    EXCEPTION WHEN undefined_object THEN null; END $$;
                    UPDATE agents SET framework = 'openclaw'
                    WHERE framework::text != 'openclaw';
                    UPDATE agents SET protection_level = 'openclaw'
                    WHERE protection_level IS NOT NULL
                      AND protection_level::text NOT IN ('openclaw', 'agent_runtime', 'full');
                    """
                )
            )
            await conn.execute(
                sa.text(
                    """
                    DO $$ BEGIN
                        CREATE TYPE agent_kind AS ENUM ('MAIN_AGENT', 'SUB_AGENT');
                    EXCEPTION WHEN duplicate_object THEN null;
                    END $$;
                    """
                )
            )
            await conn.execute(
                sa.text(
                    """
                    DO $$ BEGIN
                        CREATE TYPE agent_created_from AS ENUM ('MANUAL', 'SANDBOX_CHAT', 'TEMPLATE');
                    EXCEPTION WHEN duplicate_object THEN null;
                    END $$;
                    """
                )
            )
        if dialect == "postgresql":
            await conn.execute(
                sa.text(
                    "ALTER TABLE agents ADD COLUMN IF NOT EXISTS agent_kind agent_kind NOT NULL DEFAULT 'MAIN_AGENT'"
                )
            )
            await conn.execute(
                sa.text(
                    "ALTER TABLE agents ADD COLUMN IF NOT EXISTS created_from "
                    "agent_created_from NOT NULL DEFAULT 'MANUAL'"
                )
            )
            await conn.execute(sa.text("ALTER TABLE agents ADD COLUMN IF NOT EXISTS template_key VARCHAR(64)"))
            await conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_agents_agent_kind ON agents (agent_kind)"))
        else:
            # SQLite test/dev fallback.
            columns = await conn.execute(sa.text("PRAGMA table_info(agents)"))
            existing = {row[1] for row in columns}
            if "agent_kind" not in existing:
                await conn.execute(
                    sa.text("ALTER TABLE agents ADD COLUMN agent_kind VARCHAR(16) NOT NULL DEFAULT 'MAIN_AGENT'")
                )
            if "created_from" not in existing:
                await conn.execute(
                    sa.text("ALTER TABLE agents ADD COLUMN created_from VARCHAR(16) NOT NULL DEFAULT 'MANUAL'")
                )
            if "template_key" not in existing:
                await conn.execute(sa.text("ALTER TABLE agents ADD COLUMN template_key VARCHAR(64)"))
            await conn.execute(sa.text("UPDATE agents SET framework = 'openclaw' WHERE framework != 'openclaw'"))
            await conn.execute(
                sa.text(
                    "UPDATE agents SET protection_level = 'openclaw' "
                    "WHERE protection_level IS NOT NULL "
                    "AND protection_level NOT IN ('openclaw', 'agent_runtime', 'full')"
                )
            )
