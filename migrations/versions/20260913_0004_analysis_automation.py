"""Add checkpoint revision pointers and automatic analysis operational state."""

from pathlib import Path

from alembic import op

revision = "20260913_0004"
down_revision = "20260913_0003"
branch_labels = None
depends_on = None


def upgrade():
    path = Path(__file__).parents[1] / "sql" / "20260913_0004_analysis_automation.sql"
    for statement in path.read_text(encoding="utf-8").split("-- statement"):
        if statement.strip():
            op.execute(statement.strip())


def downgrade():
    raise RuntimeError("Preserve analysis history; restore a verified pre-upgrade backup instead.")
