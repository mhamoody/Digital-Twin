"""Version-one API response and request contracts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(ApiContract):
    status: Literal["ok", "not_ready"]
    service: Literal["course-digital-twin-api"] = "course-digital-twin-api"
    database_backend: str | None = None
    migration_revision: str | None = None


class InstructorIdentity(ApiContract):
    reviewer_id: str = Field(min_length=1, max_length=128)
    role: Literal["instructor", "supervisor"]


class PresentationOverview(ApiContract):
    presentation_id: str
    module_code: str
    presentation_code: str
    data_origin: str
    learner_count: int = Field(ge=0)
    state_count: int = Field(ge=0)
    prediction_count: int = Field(ge=0)
    alert_count: int = Field(ge=0)
    alerts_by_status: dict[str, int]
    states_by_checkpoint: dict[int, int]
    latest_state_built_at: datetime | None
    all_current_alerts_fresh: bool
    ingestion_status: Literal["not_configured", "current", "stale", "failed"]
    last_ingestion_success_at: datetime | None = None
    ingestion_age_minutes: float | None = Field(default=None, ge=0)
    active_quarantine_count: int = Field(default=0, ge=0)


class LearnerListItem(ApiContract):
    learner_id: str
    presentation_id: str
    data_origin: str
    latest_checkpoint_week: int | None = Field(default=None, ge=1)
    latest_cutoff_course_day: int | None = None
    completeness: float | None = Field(default=None, ge=0, le=1)
    is_fresh: bool | None = None
    display_probability: float | None = Field(default=None, ge=0, le=1)
    previous_probability: float | None = Field(default=None, ge=0, le=1)
    probability_change: float | None = Field(default=None, ge=-1, le=1)
    risk_band: str | None = None
    model_version: str | None = None
    alert_id: str | None = None
    alert_status: str | None = None
    evidence_count: int = Field(default=0, ge=0)
    activity_count_14d: int | None = Field(default=None, ge=0)
    active_days_14d: int | None = Field(default=None, ge=0)
    days_since_last_activity: int | None = Field(default=None, ge=0)
    assessments_due: int | None = Field(default=None, ge=0)
    assessments_submitted: int | None = Field(default=None, ge=0)
    assessments_missed: int | None = Field(default=None, ge=0)
    submission_rate: float | None = Field(default=None, ge=0, le=1)


class LearnerListResponse(ApiContract):
    items: list[LearnerListItem]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)


class LearnerFeatureResponse(ApiContract):
    evidence_id: str
    feature_name: str
    value: Any = None
    missing_reason: str
    source_observation_count: int = Field(ge=0)


class LearnerActivityWeek(ApiContract):
    course_week: int
    activity_count: int = Field(ge=0)
    assessment_event_count: int = Field(ge=0)


class AlertListItem(ApiContract):
    alert_id: str
    learner_id: str
    presentation_id: str
    checkpoint_week: int
    cutoff_course_day: int
    display_probability: float
    risk_band: str
    model_kind: str
    model_version: str
    priority: str
    status: str
    is_fresh: bool
    generated_at: datetime
    data_origin: str
    evidence_count: int = Field(ge=0)


class AlertListResponse(ApiContract):
    items: list[AlertListItem]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)


class ClaimResponse(ApiContract):
    claim_code: str
    evidence_ids: list[str]


class EvidenceResponse(ApiContract):
    evidence_id: str
    feature_name: str
    value: Any = None
    missing_reason: str
    source_observation_count: int = Field(ge=0)
    source_observation_hash: str
    source_record_samples: list[str]


class ReviewHistoryItem(ApiContract):
    review_id: str
    reviewer_id: str
    reviewer_role: str
    previous_status: str
    new_status: str
    note: str | None
    reviewed_at: datetime


class PredictionTimelinePoint(ApiContract):
    checkpoint_week: int
    cutoff_course_day: int
    display_probability: float | None
    risk_band: str | None
    model_version: str
    generated_at: datetime
    is_selected_alert: bool


class LearnerDetailResponse(ApiContract):
    learner: LearnerListItem
    registration_day: int | None = None
    registration_missing_reason: str
    unregistration_day: int | None = None
    unregistration_missing_reason: str
    features: list[LearnerFeatureResponse]
    activity_timeline: list[LearnerActivityWeek]
    prediction_timeline: list[PredictionTimelinePoint]


class AlertDetail(ApiContract):
    alert: AlertListItem
    state_id: str
    input_hash: str
    feature_set_version: str
    completeness: float
    model_ref: str
    uncertainty_note: str
    quality_gate_passed: bool
    fallback_used: bool
    claims: list[ClaimResponse]
    suggested_actions: list[str]
    evidence: list[EvidenceResponse]
    prediction_timeline: list[PredictionTimelinePoint]
    review_history: list[ReviewHistoryItem]


class ReviewStatus(StrEnum):
    REVIEWED = "reviewed"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class AlertReviewRequest(ApiContract):
    new_status: ReviewStatus
    note: str | None = Field(default=None, max_length=1000)


class AlertReviewResponse(ApiContract):
    review_id: str
    alert_id: str
    status: ReviewStatus
    created: bool
    reviewed_at: datetime


class ApiError(ApiContract):
    detail: str
