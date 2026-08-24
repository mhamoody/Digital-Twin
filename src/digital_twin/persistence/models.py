"""SQLAlchemy schema for immutable lineage and audited alert review."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

ORIGINS = "'empirical','replayed','synthetic','manual_test'"


class Base(DeclarativeBase):
    pass


class SourceDataset(Base):
    __tablename__ = "source_dataset"
    __table_args__ = ({"schema": "registry"},)

    source_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    licence_note: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IngestionRun(Base):
    __tablename__ = "ingestion_run"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_ingestion_run_idempotency"),
        CheckConstraint(
            "status IN ('started','accepted','failed')", name="ck_ingestion_run_status"
        ),
        {"schema": "registry"},
    )

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("registry.source_dataset.source_id", ondelete="RESTRICT"), nullable=False
    )
    adapter_version: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    counts_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class SyncCursor(Base):
    __tablename__ = "sync_cursor"
    __table_args__ = (
        CheckConstraint("status IN ('current','failed')", name="ck_sync_cursor_status"),
        CheckConstraint("consecutive_failures >= 0", name="ck_sync_cursor_failures"),
        CheckConstraint("processed_count >= 0", name="ck_sync_cursor_processed"),
        CheckConstraint("quarantined_count >= 0", name="ck_sync_cursor_quarantined"),
        CheckConstraint("stale_after_minutes > 0", name="ck_sync_cursor_stale_after"),
        {"schema": "registry"},
    )

    connector_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("registry.source_dataset.source_id", ondelete="RESTRICT"), nullable=False
    )
    presentation_id: Mapped[str] = mapped_column(
        ForeignKey("core.course_presentation.presentation_id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    cursor_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cursor_key: Mapped[str | None] = mapped_column(String(128))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quarantined_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stale_after_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QuarantinedRecord(Base):
    __tablename__ = "quarantined_record"
    __table_args__ = (
        UniqueConstraint(
            "connector_id", "source_record_id", name="uq_quarantine_connector_record"
        ),
        {"schema": "registry"},
    )

    quarantine_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    connector_id: Mapped[str] = mapped_column(
        ForeignKey("registry.sync_cursor.connector_id", ondelete="RESTRICT"), nullable=False
    )
    source_record_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    error_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recovery_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("registry.ingestion_run.run_id", ondelete="RESTRICT")
    )


class CoursePresentation(Base):
    __tablename__ = "course_presentation"
    __table_args__ = ({"schema": "core"},)

    presentation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("registry.source_dataset.source_id", ondelete="RESTRICT"), nullable=False
    )
    module_code: Mapped[str] = mapped_column(String(64), nullable=False)
    presentation_code: Mapped[str] = mapped_column(String(64), nullable=False)
    length_days: Mapped[int] = mapped_column(Integer, nullable=False)
    data_origin: Mapped[str] = mapped_column(String(32), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class Learner(Base):
    __tablename__ = "learner"
    __table_args__ = ({"schema": "core"},)

    learner_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("registry.source_dataset.source_id", ondelete="RESTRICT"), nullable=False
    )
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class Enrolment(Base):
    __tablename__ = "enrolment"
    __table_args__ = (
        ForeignKeyConstraint(
            ["presentation_id"],
            ["core.course_presentation.presentation_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["learner_id"], ["core.learner.learner_id"], ondelete="RESTRICT"
        ),
        UniqueConstraint("source_record_id", name="uq_enrolment_source_record"),
        {"schema": "core"},
    )

    presentation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    learner_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    registration_day: Mapped[int | None] = mapped_column(Integer)
    registration_missing_reason: Mapped[str] = mapped_column(String(32), nullable=False)
    unregistration_day: Mapped[int | None] = mapped_column(Integer)
    unregistration_missing_reason: Mapped[str] = mapped_column(String(32), nullable=False)
    previous_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    studied_credits: Mapped[int] = mapped_column(Integer, nullable=False)
    data_origin: Mapped[str] = mapped_column(String(32), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(128), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class SourceObservation(Base):
    __tablename__ = "source_observation"
    __table_args__ = (
        CheckConstraint(f"data_origin IN ({ORIGINS})", name="ck_source_observation_origin"),
        CheckConstraint(
            "event_count IS NULL OR event_count >= 0",
            name="ck_source_observation_event_count",
        ),
        {"schema": "core"},
    )

    observation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("registry.ingestion_run.run_id", ondelete="RESTRICT"), nullable=False
    )
    presentation_id: Mapped[str] = mapped_column(
        ForeignKey("core.course_presentation.presentation_id", ondelete="RESTRICT"),
        nullable=False,
    )
    learner_id: Mapped[str | None] = mapped_column(
        ForeignKey("core.learner.learner_id", ondelete="RESTRICT")
    )
    observation_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(128), nullable=False)
    course_day: Mapped[int | None] = mapped_column(Integer)
    event_code: Mapped[str | None] = mapped_column(String(128))
    event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    time_precision: Mapped[str | None] = mapped_column(String(32))
    value_json: Mapped[object | None] = mapped_column(JSON)
    event_count: Mapped[int | None] = mapped_column(Integer)
    adapter_version: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    data_origin: Mapped[str] = mapped_column(String(32), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class FeatureSet(Base):
    __tablename__ = "feature_set"
    __table_args__ = ({"schema": "analytics"},)

    feature_set_version: Mapped[str] = mapped_column(String(64), primary_key=True)
    definition_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    definition_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WeeklyStateRecord(Base):
    __tablename__ = "weekly_state"
    __table_args__ = (
        ForeignKeyConstraint(
            ["presentation_id", "learner_id"],
            ["core.enrolment.presentation_id", "core.enrolment.learner_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "presentation_id",
            "learner_id",
            "checkpoint_week",
            "feature_set_version",
            name="uq_weekly_state_grain",
        ),
        CheckConstraint("checkpoint_week >= 1", name="ck_weekly_state_week"),
        CheckConstraint("completeness >= 0 AND completeness <= 1", name="ck_state_complete"),
        CheckConstraint(f"data_origin IN ({ORIGINS})", name="ck_weekly_state_origin"),
        {"schema": "analytics"},
    )

    state_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    presentation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    learner_id: Mapped[str] = mapped_column(String(128), nullable=False)
    checkpoint_week: Mapped[int] = mapped_column(Integer, nullable=False)
    cutoff_course_day: Mapped[int] = mapped_column(Integer, nullable=False)
    feature_set_version: Mapped[str] = mapped_column(
        ForeignKey("analytics.feature_set.feature_set_version", ondelete="RESTRICT"),
        nullable=False,
    )
    built_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_fresh: Mapped[bool] = mapped_column(Boolean, nullable=False)
    completeness: Mapped[float] = mapped_column(Float, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    data_origin: Mapped[str] = mapped_column(String(32), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class WeeklyFeatureRecord(Base):
    __tablename__ = "weekly_feature"
    __table_args__ = (
        UniqueConstraint("evidence_id", name="uq_weekly_feature_evidence"),
        CheckConstraint("source_observation_count >= 0", name="ck_feature_source_count"),
        {"schema": "analytics"},
    )

    state_id: Mapped[str] = mapped_column(
        ForeignKey("analytics.weekly_state.state_id", ondelete="RESTRICT"), primary_key=True
    )
    feature_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    value_json: Mapped[object | None] = mapped_column(JSON)
    missing_reason: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provenance_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    source_observation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_observation_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class FeatureSourceSample(Base):
    __tablename__ = "feature_source_sample"
    __table_args__ = ({"schema": "analytics"},)

    state_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    feature_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    observation_id: Mapped[str] = mapped_column(
        ForeignKey("core.source_observation.observation_id", ondelete="RESTRICT"),
        primary_key=True,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["state_id", "feature_name"],
            ["analytics.weekly_feature.state_id", "analytics.weekly_feature.feature_name"],
            ondelete="RESTRICT",
        ),
        {"schema": "analytics"},
    )


class ModelVersion(Base):
    __tablename__ = "model_version"
    __table_args__ = (
        UniqueConstraint("model_kind", "model_version", name="uq_model_kind_version"),
        {"schema": "analytics"},
    )

    model_ref: Mapped[str] = mapped_column(String(128), primary_key=True)
    model_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    approved_scope: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PredictionRecord(Base):
    __tablename__ = "prediction"
    __table_args__ = (
        CheckConstraint(
            "raw_risk_score IS NULL OR (raw_risk_score >= 0 AND raw_risk_score <= 1)",
            name="ck_prediction_raw_score",
        ),
        CheckConstraint(
            "display_probability IS NULL OR "
            "(display_probability >= 0 AND display_probability <= 1)",
            name="ck_prediction_display_score",
        ),
        CheckConstraint(f"data_origin IN ({ORIGINS})", name="ck_prediction_origin"),
        {"schema": "analytics"},
    )

    prediction_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    state_id: Mapped[str] = mapped_column(
        ForeignKey("analytics.weekly_state.state_id", ondelete="RESTRICT"), nullable=False
    )
    model_ref: Mapped[str] = mapped_column(
        ForeignKey("analytics.model_version.model_ref", ondelete="RESTRICT"), nullable=False
    )
    raw_risk_score: Mapped[float | None] = mapped_column(Float)
    display_probability: Mapped[float | None] = mapped_column(Float)
    calibration_version: Mapped[str | None] = mapped_column(String(64))
    risk_band: Mapped[str | None] = mapped_column(String(16))
    uncertainty_note: Mapped[str] = mapped_column(String(300), nullable=False)
    abstain: Mapped[bool] = mapped_column(Boolean, nullable=False)
    abstention_reason: Mapped[str | None] = mapped_column(String(200))
    quality_gate_passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_origin: Mapped[str] = mapped_column(String(32), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class PredictionClaim(Base):
    __tablename__ = "prediction_claim"
    __table_args__ = ({"schema": "analytics"},)

    prediction_id: Mapped[str] = mapped_column(
        ForeignKey("analytics.prediction.prediction_id", ondelete="RESTRICT"), primary_key=True
    )
    claim_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    evidence_id: Mapped[str] = mapped_column(
        ForeignKey("analytics.weekly_feature.evidence_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    claim_code: Mapped[str] = mapped_column(String(64), nullable=False)


class PredictionAction(Base):
    __tablename__ = "prediction_action"
    __table_args__ = ({"schema": "analytics"},)

    prediction_id: Mapped[str] = mapped_column(
        ForeignKey("analytics.prediction.prediction_id", ondelete="RESTRICT"), primary_key=True
    )
    action_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    action_code: Mapped[str] = mapped_column(String(64), nullable=False)


class AlertRecord(Base):
    __tablename__ = "alert"
    __table_args__ = (
        CheckConstraint(
            "status IN ('new','reviewed','resolved','dismissed')", name="ck_alert_status"
        ),
        CheckConstraint(f"data_origin IN ({ORIGINS})", name="ck_alert_origin"),
        {"schema": "analytics"},
    )

    alert_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    prediction_id: Mapped[str] = mapped_column(
        ForeignKey("analytics.prediction.prediction_id", ondelete="RESTRICT"), nullable=False
    )
    state_id: Mapped[str] = mapped_column(
        ForeignKey("analytics.weekly_state.state_id", ondelete="RESTRICT"), nullable=False
    )
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    is_fresh: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_origin: Mapped[str] = mapped_column(String(32), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class AlertEvidence(Base):
    __tablename__ = "alert_evidence"
    __table_args__ = ({"schema": "analytics"},)

    alert_id: Mapped[str] = mapped_column(
        ForeignKey("analytics.alert.alert_id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_id: Mapped[str] = mapped_column(
        ForeignKey("analytics.weekly_feature.evidence_id", ondelete="RESTRICT"),
        primary_key=True,
    )


class AlertReview(Base):
    __tablename__ = "alert_review"
    __table_args__ = (
        CheckConstraint(
            "new_status IN ('reviewed','resolved','dismissed')", name="ck_review_new_status"
        ),
        {"schema": "analytics"},
    )

    review_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    alert_id: Mapped[str] = mapped_column(
        ForeignKey("analytics.alert.alert_id", ondelete="RESTRICT"), nullable=False
    )
    reviewer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reviewer_role: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_status: Mapped[str] = mapped_column(String(16), nullable=False)
    new_status: Mapped[str] = mapped_column(String(16), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class PersistenceEvent(Base):
    __tablename__ = "persistence_event"
    __table_args__ = ({"schema": "audit"},)

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("registry.ingestion_run.run_id", ondelete="RESTRICT")
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
