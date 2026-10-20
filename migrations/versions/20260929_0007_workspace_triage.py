"""Add independent audited v2 instructor triage without changing existing history."""

from alembic import op

revision = "20260929_0007"
down_revision = "20260924_0006"
branch_labels = None
depends_on = None


def upgrade():
    dialect = op.get_bind().dialect.name
    if dialect not in {"sqlite", "postgresql"}:
        raise ValueError("Unsupported workspace triage migration dialect")
    audit = "" if dialect == "sqlite" else "audit."
    core = "" if dialect == "sqlite" else "core."
    timestamp = "DATETIME" if dialect == "sqlite" else "TIMESTAMP WITH TIME ZONE"
    op.execute(f"""CREATE TABLE {audit}workspace_triage (
        course_id VARCHAR(128) NOT NULL, learner_id VARCHAR(128) NOT NULL,
        version INTEGER NOT NULL, payload JSON NOT NULL, updated_at {timestamp} NOT NULL,
        PRIMARY KEY (course_id, learner_id),
        CONSTRAINT ck_workspace_triage_version CHECK (version >= 1),
        FOREIGN KEY (course_id, learner_id)
            REFERENCES {core}workspace_enrolment (course_id, learner_id)
    )""")
    op.execute(f"""CREATE TABLE {audit}workspace_triage_event (
        id VARCHAR(64) PRIMARY KEY, course_id VARCHAR(128) NOT NULL,
        learner_id VARCHAR(128) NOT NULL, version INTEGER NOT NULL,
        actor VARCHAR(128) NOT NULL, request_key VARCHAR(128) NOT NULL,
        request_hash VARCHAR(64) NOT NULL, payload JSON NOT NULL,
        created_at {timestamp} NOT NULL,
        CONSTRAINT uq_workspace_triage_request UNIQUE (actor, request_key),
        CONSTRAINT uq_workspace_triage_revision UNIQUE (course_id, learner_id, version),
        FOREIGN KEY (course_id, learner_id)
            REFERENCES {audit}workspace_triage (course_id, learner_id)
    )""")


def downgrade():
    raise RuntimeError(
        "Instructor audit history is durable. Restore a verified pre-upgrade backup "
        "instead of deleting it."
    )
