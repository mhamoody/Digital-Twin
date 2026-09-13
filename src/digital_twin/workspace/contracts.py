"""V2 contracts. Unknown evidence is never silently converted to zero."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def digest(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class CoursePolicy(Contract):
    version: int = Field(default=1, ge=1)
    inactivity_warning_days: int = Field(default=7, ge=1, le=120)
    inactivity_high_days: int = Field(default=14, ge=2, le=180)
    day_basis: Literal["calendar", "teaching"] = "calendar"
    teaching_weekdays: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    break_ranges: list[tuple[int, int]] = Field(default_factory=list)
    require_academic_corroboration: bool = True
    low_grade_percent: float = Field(default=50, ge=0, le=100)

    @model_validator(mode="after")
    def coherent(self):
        if self.inactivity_high_days <= self.inactivity_warning_days:
            raise ValueError("Escalation must be later than the warning threshold.")
        if not self.teaching_weekdays or any(d not in range(7) for d in self.teaching_weekdays):
            raise ValueError("Teaching weekdays must be in 0..6 (Monday..Sunday).")
        if len(set(self.teaching_weekdays)) != len(self.teaching_weekdays):
            raise ValueError("Teaching weekdays must be unique.")
        if any(a < 0 or b < a or b > 420 for a, b in self.break_ranges):
            raise ValueError("Breaks require inclusive course-day ranges within 0..420.")
        return self


class EvidenceFact(Contract):
    evidence_id: str = Field(min_length=1, max_length=160)
    value: float | int | str | bool | None = None
    status: Literal[
        "observed",
        "structural_zero",
        "not_yet_applicable",
        "not_supported",
        "source_missing",
        "ingestion_incomplete",
        "no_activity_yet",
    ]
    unit: str = "count"
    window: str = "through checkpoint"
    source_ids: list[str] = Field(default_factory=list)
    available_day: int | None = None

    @model_validator(mode="after")
    def missingness(self):
        if self.status == "observed" and self.value is None:
            raise ValueError("Observed evidence requires a value.")
        if self.status == "structural_zero" and self.value != 0:
            raise ValueError("Structural zero must be zero.")
        if self.status not in {"observed", "structural_zero"} and self.value is not None:
            raise ValueError("Unavailable evidence must remain null.")
        return self


class LearnerSnapshot(Contract):
    schema_version: Literal["learner-snapshot-v2"] = "learner-snapshot-v2"
    state_id: str
    presentation_id: str
    learner_id: str
    checkpoint_week: int = Field(ge=1, le=60)
    cutoff_day: int = Field(ge=0, le=419)
    data_origin: Literal["empirical", "replayed", "synthetic", "manual_test"]
    feature_version: str = "rich-features-v2"
    built_at: str
    is_fresh: bool = True
    coverage: dict[str, Literal["complete", "partial", "missing", "not_supported"]]
    course_context: dict[str, Any] = Field(default_factory=dict)
    features: dict[str, EvidenceFact]

    @model_validator(mode="after")
    def identity(self):
        if self.cutoff_day != self.checkpoint_week * 7 - 1:
            raise ValueError("Checkpoint and cutoff disagree.")
        ids = [fact.evidence_id for fact in self.features.values()]
        if len(ids) != len(set(ids)):
            raise ValueError("Evidence IDs must be unique within a snapshot.")
        for fact in self.features.values():
            if fact.available_day is not None and fact.available_day > self.cutoff_day:
                raise ValueError("Evidence was not available at the checkpoint.")
        return self


class GroundedClaim(Contract):
    code: str = Field(min_length=1, max_length=64)
    evidence_ids: list[str] = Field(min_length=1, max_length=12)


class ModelOutput(Contract):
    """Only these fields come from the LLM; metadata is attached by the server."""

    risk_score: float | None = Field(ge=0, le=1)
    risk_band: Literal["low", "medium", "high"] | None
    claims: list[GroundedClaim] = Field(max_length=8)
    suggested_actions: list[
        Literal[
            "review_recent_work",
            "send_check_in",
            "offer_resources",
            "review_grades",
            "confirm_data",
            "no_action",
        ]
    ] = Field(max_length=6)
    abstain: bool
    abstention_reason: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def modes(self):
        if self.abstain:
            if (
                self.risk_score is not None
                or self.risk_band is not None
                or self.claims
                or self.suggested_actions
            ):
                raise ValueError("Abstention must not emit scores, bands, claims or actions.")
            if not self.abstention_reason:
                raise ValueError("Abstention needs a reason.")
        else:
            if self.risk_score is None or self.risk_band is None or not self.claims:
                raise ValueError("A prediction requires a score, band and grounded claims.")
            expected = (
                "high"
                if self.risk_score >= 0.65
                else "medium"
                if self.risk_score >= 0.35
                else "low"
            )
            if self.risk_band != expected:
                raise ValueError("Risk band disagrees with the documented score thresholds.")
            if self.abstention_reason is not None:
                raise ValueError("A prediction cannot also have an abstention reason.")
        return self


class CaseUpdate(Contract):
    status: Literal["new", "reviewed", "ongoing", "resolved", "dismissed"]
    expected_version: int = Field(ge=0)
    note: str = Field(default="", max_length=2000)
    action: Literal["note", "contact", "warning", "support", "resource", "follow_up"] = "note"
    action_state: Literal["planned", "completed", "cancelled"] = "completed"
    occurred_day: int = Field(ge=0, le=420)
    follow_up_day: int | None = Field(default=None, ge=0, le=420)
    resource_ids: list[str] = Field(default_factory=list, max_length=20)
    checkpoint_week: int = Field(ge=1, le=60)
