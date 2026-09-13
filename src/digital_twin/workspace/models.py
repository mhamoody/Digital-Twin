"""Additive workspace schema; legacy empirical tables are never rewritten."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from digital_twin.persistence.models import Base


class Course(Base):
    __tablename__ = "workspace_course"
    __table_args__ = {"schema": "core"}
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)


class Enrolment(Base):
    __tablename__ = "workspace_enrolment"
    __table_args__ = {"schema": "core"}
    course_id: Mapped[str] = mapped_column(ForeignKey("core.workspace_course.id"), primary_key=True)
    learner_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)


class Event(Base):
    __tablename__ = "workspace_event"
    __table_args__ = (
        ForeignKeyConstraint(
            ["course_id", "learner_id"],
            ["core.workspace_enrolment.course_id", "core.workspace_enrolment.learner_id"],
        ),
        {"schema": "core"},
    )
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    course_id: Mapped[str] = mapped_column(String(128), index=True)
    learner_id: Mapped[str] = mapped_column(String(128), index=True)
    course_day: Mapped[int] = mapped_column(Integer)
    available_day: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)


class Snapshot(Base):
    __tablename__ = "workspace_snapshot"
    __table_args__ = (
        ForeignKeyConstraint(
            ["course_id", "learner_id"],
            ["core.workspace_enrolment.course_id", "core.workspace_enrolment.learner_id"],
        ),
        UniqueConstraint(
            "course_id", "learner_id", "week", "input_hash", name="uq_workspace_snapshot"
        ),
        {"schema": "analytics"},
    )
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    course_id: Mapped[str] = mapped_column(String(128), index=True)
    learner_id: Mapped[str] = mapped_column(String(128), index=True)
    week: Mapped[int] = mapped_column(Integer)
    input_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)


class Policy(Base):
    __tablename__ = "workspace_policy"
    __table_args__ = {"schema": "analytics"}
    course_id: Mapped[str] = mapped_column(ForeignKey("core.workspace_course.id"), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    actor: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AnalysisJob(Base):
    __tablename__ = "workspace_analysis_job"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','running','validated','abstained','failed')",
            name="ck_workspace_job_status",
        ),
        {"schema": "analytics"},
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    state_id: Mapped[str] = mapped_column(ForeignKey("analytics.workspace_snapshot.id"), index=True)
    policy_version: Mapped[int] = mapped_column(Integer)
    model_kind: Mapped[str] = mapped_column(String(16))
    expected_model_digest: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(16), index=True)
    worker_id: Mapped[str | None] = mapped_column(String(128))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(128))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Analysis(Base):
    __tablename__ = "workspace_analysis"
    __table_args__ = {"schema": "analytics"}
    id: Mapped[str] = mapped_column(
        ForeignKey("analytics.workspace_analysis_job.id"), primary_key=True
    )
    state_id: Mapped[str] = mapped_column(ForeignKey("analytics.workspace_snapshot.id"), index=True)
    policy_version: Mapped[int] = mapped_column(Integer)
    model_kind: Mapped[str] = mapped_column(String(16))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SupportCase(Base):
    __tablename__ = "workspace_support_case"
    __table_args__ = (
        ForeignKeyConstraint(
            ["course_id", "learner_id"],
            ["core.workspace_enrolment.course_id", "core.workspace_enrolment.learner_id"],
        ),
        UniqueConstraint("course_id", "learner_id", name="uq_workspace_case_learner"),
        CheckConstraint(
            "status IN ('new','reviewed','ongoing','resolved','dismissed')",
            name="ck_workspace_case_status",
        ),
        {"schema": "audit"},
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    course_id: Mapped[str] = mapped_column(String(128))
    learner_id: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16))
    version: Mapped[int] = mapped_column(Integer)
    follow_up_day: Mapped[int | None] = mapped_column(Integer)


class CaseEvent(Base):
    __tablename__ = "workspace_case_event"
    __table_args__ = (
        UniqueConstraint("actor", "request_key", name="uq_workspace_case_request"),
        {"schema": "audit"},
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("audit.workspace_support_case.id"), index=True)
    actor: Mapped[str] = mapped_column(String(128))
    request_key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    occurred_day: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
