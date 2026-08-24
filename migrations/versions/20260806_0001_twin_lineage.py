"""Create the version-one twin lineage schemas.

Revision ID: 20260806_0001
Revises: None
"""

from __future__ import annotations

from pathlib import Path

from alembic import op


revision = "20260806_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql_path = Path(__file__).parents[1] / "sql" / "20260806_0001_twin_lineage.sql"
    statements = sql_path.read_text(encoding="utf-8").split("-- statement")
    for statement in statements:
        if statement.strip():
            op.execute(statement.strip())


def downgrade() -> None:
    for schema in ("audit", "analytics", "core", "registry"):
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
