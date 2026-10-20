"""Strict version-one contracts for the integration-demo vertical slice.

These contracts intentionally separate synthetic/replayed operational evidence from
empirical research evidence. The temporary predictor and the final LLM must both
return ``ValidatedRiskResult`` so replacing the predictor does not change the rest
of the pipeline.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
Version = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
FeatureValue = float | int | bool | str | None


class StrictContract(BaseModel):
    """Base contract that rejects undocumented fields."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


class DataOrigin(StrEnum):
    EMPIRICAL = "empirical"
    REPLAYED = "replayed"
    SYNTHETIC = "synthetic"
    MANUAL_TEST = "manual_test"


class ObservationKind(StrEnum):
    ACTIVITY = "activity"
    ASSESSMENT = "assessment"
    ENROLMENT = "enrolment"


class TimePrecision(StrEnum):
    EXACT = "exact"
    DAY = "day"
    RELATIVE_DAY = "relative_day"


class MissingReason(StrEnum):
    OBSERVED = "observed"
    STRUCTURAL_ZERO = "structural_zero"
    NOT_YET_APPLICABLE = "not_yet_applicable"
    SOURCE_MISSING = "source_missing"
    INGESTION_INCOMPLETE = "ingestion_incomplete"
    NOT_SUPPORTED = "not_supported"
    NO_ACTIVITY_YET = "no_activity_yet"


class ModelKind(StrEnum):
    SIMPLE_DEMO = "simple_demo"
    LLM = "llm"
    FALLBACK = "fallback"


class RiskBand(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ClaimCode(StrEnum):
    INACTIVITY_GAP = "INACTIVITY_GAP"
    LOW_RECENT_ACTIVITY = "LOW_RECENT_ACTIVITY"
    MISSED_ASSESSMENT = "MISSED_ASSESSMENT"
    LIMITED_EVIDENCE = "LIMITED_EVIDENCE"
    RECENT_ACTIVITY_PRESENT = "RECENT_ACTIVITY_PRESENT"
    ASSESSMENTS_ON_TRACK = "ASSESSMENTS_ON_TRACK"


class ReviewAction(StrEnum):
    REVIEW_RECENT_WORK = "review_recent_work"
    SEND_CHECK_IN = "send_check_in"
    NO_ACTION = "no_action"


class AlertPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AlertStatus(StrEnum):
    NEW = "new"
    REVIEWED = "reviewed"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class CanonicalObservation(StrictContract):
    """One source event or aggregate normalized without inventing precision."""

    schema_version: Literal["canonical-observation-v1"] = "canonical-observation-v1"
    observation_id: Identifier
    source_id: Identifier
    ingestion_run_id: Identifier
    learner_id: Identifier
    presentation_id: Identifier
    kind: ObservationKind
    event_code: Identifier
    event_at: AwareDatetime | None = None
    course_day: int | None = Field(default=None, ge=-365, le=3650)
    available_at: AwareDatetime | None = None
    available_course_day: int | None = Field(default=None, ge=-365, le=3650)
    time_precision: TimePrecision
    value: FeatureValue = None
    count: int | None = Field(default=None, ge=0)
    source_record_id: Identifier
    data_origin: DataOrigin
    adapter_version: Version
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_temporal_and_value_contract(self) -> CanonicalObservation:
        if self.event_at is None and self.course_day is None:
            raise ValueError("an observation requires event_at or course_day")
        if self.available_at is None and self.available_course_day is None:
            raise ValueError("an observation requires an explicit availability time/day")
        if self.time_precision is TimePrecision.RELATIVE_DAY and self.course_day is None:
            raise ValueError("relative_day precision requires course_day")
        if self.count is None and self.value is None:
            raise ValueError("an observation requires count or value")
        return self


class WeeklyFeature(StrictContract):
    """One typed state feature with compact provenance and a display evidence ID."""

    name: Identifier
    value: FeatureValue = None
    missing_reason: MissingReason
    evidence_id: Identifier
    source_observation_ids: list[Identifier] = Field(default_factory=list)
    provenance_reference: Identifier
    source_observation_count: int = Field(ge=0)
    source_observation_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_missingness(self) -> WeeklyFeature:
        if self.missing_reason is MissingReason.OBSERVED:
            if self.value is None:
                raise ValueError("observed features require a value")
            if self.source_observation_count < 1:
                raise ValueError("observed features require source observation provenance")
        elif self.missing_reason is MissingReason.STRUCTURAL_ZERO:
            if self.value not in (0, 0.0, False):
                raise ValueError("structural_zero features must have a zero value")
        elif self.value is not None:
            raise ValueError("unknown/not-applicable features must keep value null")
        return self


class WeeklyState(StrictContract):
    """Versioned learner/presentation/checkpoint state."""

    schema_version: Literal["weekly-state-v1"] = "weekly-state-v1"
    state_id: Identifier
    learner_id: Identifier
    presentation_id: Identifier
    checkpoint_week: int = Field(ge=1, le=60)
    cutoff_course_day: int = Field(ge=0, le=420)
    feature_set_version: Version
    data_origin: DataOrigin
    built_at: AwareDatetime
    is_fresh: bool
    completeness: float = Field(ge=0.0, le=1.0)
    input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    features: list[WeeklyFeature] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_state_identity(self) -> WeeklyState:
        expected_cutoff = 7 * self.checkpoint_week - 1
        if self.cutoff_course_day != expected_cutoff:
            raise ValueError(
                f"checkpoint week {self.checkpoint_week} requires cutoff day {expected_cutoff}"
            )
        names = [feature.name for feature in self.features]
        evidence_ids = [feature.evidence_id for feature in self.features]
        if len(names) != len(set(names)):
            raise ValueError("weekly feature names must be unique")
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("weekly evidence IDs must be unique")
        return self


class EvidenceClaim(StrictContract):
    """An allow-listed claim connected to the evidence that supports it."""

    claim_code: ClaimCode
    evidence_ids: list[Identifier] = Field(min_length=1)


class ValidatedRiskResult(StrictContract):
    """Shared output contract for the demo predictor, future LLM, and fallback."""

    schema_version: Literal["risk-result-v1"] = "risk-result-v1"
    prediction_id: Identifier
    state_id: Identifier
    model_kind: ModelKind
    model_version: Version
    raw_risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    display_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    calibration_version: Version | None = None
    risk_band: RiskBand | None = None
    claims: list[EvidenceClaim] = Field(default_factory=list)
    suggested_actions: list[ReviewAction] = Field(default_factory=list)
    uncertainty_note: str = Field(min_length=1, max_length=300)
    abstain: bool
    abstention_reason: str | None = Field(default=None, min_length=1, max_length=200)
    quality_gate_passed: bool
    fallback_used: bool
    generated_at: AwareDatetime
    data_origin: DataOrigin

    @model_validator(mode="after")
    def validate_prediction_modes(self) -> ValidatedRiskResult:
        if self.abstain:
            if self.raw_risk_score is not None or self.display_probability is not None:
                raise ValueError("abstention requires null scores")
            if self.risk_band is not None or self.claims or self.suggested_actions:
                raise ValueError("abstention cannot emit a band, claims, or actions")
            if not self.abstention_reason:
                raise ValueError("abstention requires a reason")
        else:
            if self.raw_risk_score is None or self.display_probability is None:
                raise ValueError("a non-abstaining result requires raw and display scores")
            if self.risk_band is None or not self.claims:
                raise ValueError("a non-abstaining result requires a band and grounded claims")
            if self.abstention_reason is not None:
                raise ValueError("a non-abstaining result cannot have an abstention reason")
        if self.fallback_used and self.model_kind is not ModelKind.FALLBACK:
            raise ValueError("fallback_used requires model_kind=fallback")
        return self


class Alert(StrictContract):
    """One human-review alert created only from an eligible validated prediction."""

    schema_version: Literal["alert-v1"] = "alert-v1"
    alert_id: Identifier
    prediction_id: Identifier
    state_id: Identifier
    policy_version: Version
    priority: AlertPriority
    status: AlertStatus = AlertStatus.NEW
    evidence_ids: list[Identifier] = Field(min_length=1)
    is_fresh: bool
    created_at: AwareDatetime
    data_origin: DataOrigin


def validate_prediction_grounding(
    state: WeeklyState, prediction: ValidatedRiskResult
) -> ValidatedRiskResult:
    """Reject cross-state, cross-origin, or nonexistent evidence references."""

    if prediction.state_id != state.state_id:
        raise ValueError("prediction state_id does not match the persisted weekly state")
    if prediction.data_origin is not state.data_origin:
        raise ValueError("prediction origin does not match state origin")
    available_evidence = {feature.evidence_id for feature in state.features}
    cited_evidence = {
        evidence_id for claim in prediction.claims for evidence_id in claim.evidence_ids
    }
    unknown = cited_evidence - available_evidence
    if unknown:
        raise ValueError(f"prediction cites unavailable evidence IDs: {sorted(unknown)}")
    return prediction


def validate_alert_eligibility(prediction: ValidatedRiskResult, alert: Alert) -> Alert:
    """Apply the minimum cross-contract safety checks before alert persistence."""

    if alert.prediction_id != prediction.prediction_id or alert.state_id != prediction.state_id:
        raise ValueError("alert does not reference the supplied prediction/state")
    if alert.data_origin is not prediction.data_origin:
        raise ValueError("alert origin does not match prediction origin")
    if prediction.abstain or not prediction.quality_gate_passed:
        raise ValueError("abstained or failed-quality predictions cannot create alerts")
    if not alert.is_fresh:
        raise ValueError("stale states cannot create new alerts")
    prediction_evidence = {
        evidence_id for claim in prediction.claims for evidence_id in claim.evidence_ids
    }
    if not set(alert.evidence_ids).issubset(prediction_evidence):
        raise ValueError("alert cites evidence not present in the validated prediction")
    return alert
