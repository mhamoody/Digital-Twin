"""Add versioned instructor workspace without altering legacy empirical records."""

from pathlib import Path

from alembic import op

revision = "20260913_0003"
down_revision = "20260806_0002"
branch_labels = None
depends_on = None


def upgrade():
    path = Path(__file__).parents[1] / "sql" / "20260913_0003_workspace.sql"
    for statement in path.read_text(encoding="utf-8").split("-- statement"):
        if statement.strip():
            op.execute(statement.strip())


def downgrade():
    raise RuntimeError(
        "Workspace history is durable. "
        "Restore a verified pre-upgrade backup instead of deleting it."
    )
