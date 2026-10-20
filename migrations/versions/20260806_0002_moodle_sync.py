"""Add Moodle synchronization cursor, quarantine, and observation timestamps.

Revision ID: 20260806_0002
Revises: 20260806_0001
"""

from __future__ import annotations

from pathlib import Path

from alembic import op


revision = "20260806_0002"
down_revision = "20260806_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql_path = Path(__file__).parents[1] / "sql" / "20260806_0002_moodle_sync.sql"
    statements = sql_path.read_text(encoding="utf-8").split("-- statement")
    for statement in statements:
        if statement.strip():
            op.execute(statement.strip())


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS registry.quarantined_record")
    op.execute("DROP TABLE IF EXISTS registry.sync_cursor")
    op.execute("ALTER TABLE core.source_observation DROP COLUMN IF EXISTS metadata_json")
    op.execute("ALTER TABLE core.source_observation DROP COLUMN IF EXISTS adapter_version")
    op.execute("ALTER TABLE core.source_observation DROP COLUMN IF EXISTS event_count")
    op.execute("ALTER TABLE core.source_observation DROP COLUMN IF EXISTS value_json")
    op.execute("ALTER TABLE core.source_observation DROP COLUMN IF EXISTS time_precision")
    op.execute("ALTER TABLE core.source_observation DROP COLUMN IF EXISTS available_at")
    op.execute("ALTER TABLE core.source_observation DROP COLUMN IF EXISTS event_at")
    op.execute("ALTER TABLE core.source_observation DROP COLUMN IF EXISTS event_code")
