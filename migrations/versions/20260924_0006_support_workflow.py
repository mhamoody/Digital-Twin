"""Add persistent support workflow on the team migration lineage."""
from alembic import op

revision = "20260924_0006"
down_revision = "20260914_0005"
branch_labels = None
depends_on = None


def upgrade():
    dialect = op.get_bind().dialect.name
    if dialect not in {"sqlite", "postgresql"}:
        raise ValueError("Unsupported workflow migration dialect")
    schema = "" if dialect == "sqlite" else "analytics."
    audit = "" if dialect == "sqlite" else "audit."
    op.execute(f"""CREATE TABLE {schema}support_case (
        case_id VARCHAR(128) PRIMARY KEY, presentation_id VARCHAR(128) NOT NULL,
        learner_id VARCHAR(128) NOT NULL, data_origin VARCHAR(32) NOT NULL,
        status VARCHAR(32) NOT NULL, opened_at {'DATETIME' if dialect == 'sqlite' else 'TIMESTAMP WITH TIME ZONE'} NOT NULL,
        last_action_at {'DATETIME' if dialect == 'sqlite' else 'TIMESTAMP WITH TIME ZONE'} NOT NULL,
        follow_up_due_at {'DATETIME' if dialect == 'sqlite' else 'TIMESTAMP WITH TIME ZONE'},
        closed_at {'DATETIME' if dialect == 'sqlite' else 'TIMESTAMP WITH TIME ZONE'}, version INTEGER NOT NULL,
        created_by VARCHAR(128) NOT NULL, created_by_role VARCHAR(32) NOT NULL,
        CONSTRAINT ck_support_status CHECK (status IN ('new_concern','reviewed','ongoing','resolved','dismissed')),
        CONSTRAINT ck_support_version CHECK (version >= 1),
        CONSTRAINT ck_support_closed CHECK ((status IN ('resolved','dismissed') AND closed_at IS NOT NULL) OR (status IN ('new_concern','reviewed','ongoing') AND closed_at IS NULL)),
        FOREIGN KEY(presentation_id, learner_id) REFERENCES {'enrolment' if dialect == 'sqlite' else 'core.enrolment'} (presentation_id, learner_id) ON DELETE RESTRICT
    )""")
    op.execute(f"CREATE UNIQUE INDEX uq_support_active ON {schema}support_case (presentation_id, learner_id, data_origin) WHERE status IN ('new_concern','reviewed','ongoing')")
    op.execute(f"""CREATE TABLE {audit}support_action (
        action_id VARCHAR(128) PRIMARY KEY, case_id VARCHAR(128) NOT NULL,
        action_type VARCHAR(32) NOT NULL, actor_id VARCHAR(128) NOT NULL, actor_role VARCHAR(32) NOT NULL,
        created_at {'DATETIME' if dialect == 'sqlite' else 'TIMESTAMP WITH TIME ZONE'} NOT NULL,
        idempotency_key VARCHAR(128) NOT NULL, request_hash VARCHAR(64) NOT NULL, creation_key VARCHAR(64),
        resulting_version INTEGER NOT NULL, note TEXT, previous_status VARCHAR(32), new_status VARCHAR(32),
        previous_follow_up_due_at {'DATETIME' if dialect == 'sqlite' else 'TIMESTAMP WITH TIME ZONE'},
        new_follow_up_due_at {'DATETIME' if dialect == 'sqlite' else 'TIMESTAMP WITH TIME ZONE'}, linked_alert_id VARCHAR(128),
        CONSTRAINT uq_support_action_retry UNIQUE (case_id, idempotency_key), CONSTRAINT uq_support_creation_retry UNIQUE (creation_key),
        FOREIGN KEY(case_id) REFERENCES {schema}support_case(case_id) ON DELETE RESTRICT,
        FOREIGN KEY(linked_alert_id) REFERENCES {schema}alert(alert_id) ON DELETE RESTRICT
    )""")
    op.execute(f"""CREATE TABLE {schema}support_case_alert (
        case_id VARCHAR(128) NOT NULL, alert_id VARCHAR(128) NOT NULL,
        linked_at {'DATETIME' if dialect == 'sqlite' else 'TIMESTAMP WITH TIME ZONE'} NOT NULL,
        link_reason VARCHAR(64) NOT NULL, PRIMARY KEY(case_id, alert_id), UNIQUE(alert_id),
        FOREIGN KEY(case_id) REFERENCES {schema}support_case(case_id) ON DELETE RESTRICT,
        FOREIGN KEY(alert_id) REFERENCES {schema}alert(alert_id) ON DELETE RESTRICT
    )""")


def downgrade():
    dialect = op.get_bind().dialect.name
    schema = "" if dialect == "sqlite" else "analytics."
    audit = "" if dialect == "sqlite" else "audit."
    op.execute(f"DROP TABLE {schema}support_case_alert")
    op.execute(f"DROP TABLE {audit}support_action")
    op.execute(f"DROP TABLE {schema}support_case")
