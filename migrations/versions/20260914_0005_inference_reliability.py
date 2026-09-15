"""Add course validation controls and safe generation audit metadata."""

from pathlib import Path

from alembic import op

revision = "20260914_0005"
down_revision = "20260913_0004"
branch_labels = None
depends_on = None


def upgrade():
    path = Path(__file__).parents[1] / "sql" / "20260914_0005_inference_reliability.sql"
    for statement in path.read_text(encoding="utf-8").split("-- statement"):
        if statement.strip():
            op.execute(statement.strip())


def downgrade():
    raise RuntimeError("Preserve inference history; restore a verified pre-upgrade backup instead.")
