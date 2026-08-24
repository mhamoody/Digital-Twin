"""Deterministic integration predictor; not an empirical research model."""

from __future__ import annotations

import hashlib
from datetime import datetime

from digital_twin.schemas import (
    ClaimCode,
    EvidenceClaim,
    ModelKind,
    ReviewAction,
    RiskBand,
    ValidatedRiskResult,
    WeeklyState,
    validate_prediction_grounding,
)


DEMO_MODEL_VERSION = "simple-rules-v1"


def _prediction_id(state: WeeklyState) -> str:
    digest = hashlib.sha256(f"{state.state_id}:{DEMO_MODEL_VERSION}".encode()).hexdigest()[:16]
    return f"prediction:demo:{digest}"


def predict_demo_risk(state: WeeklyState, generated_at: datetime) -> ValidatedRiskResult:
    """Create deterministic risk solely to exercise downstream architecture."""

    feature = {item.name: item for item in state.features}
    if not state.is_fresh or state.completeness < 0.70:
        return ValidatedRiskResult(
            prediction_id=_prediction_id(state),
            state_id=state.state_id,
            model_kind=ModelKind.SIMPLE_DEMO,
            model_version=DEMO_MODEL_VERSION,
            uncertainty_note="State quality is insufficient for the demo predictor.",
            abstain=True,
            abstention_reason="INCOMPLETE_OR_STALE_STATE",
            quality_gate_passed=True,
            fallback_used=False,
            generated_at=generated_at,
            data_origin=state.data_origin,
        )

    score = 0.05
    claims: list[EvidenceClaim] = []
    days_since = feature["days_since_last_activity"].value
    clicks_7 = int(feature["clicks_last_7"].value or 0)
    active_14 = int(feature["active_days_last_14"].value or 0)
    missed = int(feature["assessments_missed"].value or 0)
    due = feature["assessments_due"].value
    submission_rate = feature["submission_rate"].value

    if days_since is None:
        score += 0.35
        claims.append(
            EvidenceClaim(
                claim_code=ClaimCode.INACTIVITY_GAP,
                evidence_ids=[feature["clicks_cumulative"].evidence_id],
            )
        )
    elif int(days_since) > 14:
        score += 0.35
        claims.append(
            EvidenceClaim(
                claim_code=ClaimCode.INACTIVITY_GAP,
                evidence_ids=[feature["days_since_last_activity"].evidence_id],
            )
        )
    elif int(days_since) > 7:
        score += 0.25
        claims.append(
            EvidenceClaim(
                claim_code=ClaimCode.INACTIVITY_GAP,
                evidence_ids=[feature["days_since_last_activity"].evidence_id],
            )
        )
    elif int(days_since) > 3:
        score += 0.10

    if clicks_7 == 0:
        score += 0.20
        claims.append(
            EvidenceClaim(
                claim_code=ClaimCode.LOW_RECENT_ACTIVITY,
                evidence_ids=[feature["clicks_last_7"].evidence_id],
            )
        )
    if active_14 < 2:
        score += 0.15
        if not any(claim.claim_code is ClaimCode.LOW_RECENT_ACTIVITY for claim in claims):
            claims.append(
                EvidenceClaim(
                    claim_code=ClaimCode.LOW_RECENT_ACTIVITY,
                    evidence_ids=[feature["active_days_last_14"].evidence_id],
                )
            )
    if missed:
        score += min(0.40, missed * 0.20)
        claims.append(
            EvidenceClaim(
                claim_code=ClaimCode.MISSED_ASSESSMENT,
                evidence_ids=[feature["assessments_missed"].evidence_id],
            )
        )
    elif due and submission_rate is not None:
        if float(submission_rate) < 0.5:
            score += 0.25
        elif float(submission_rate) < 0.8:
            score += 0.10

    score = round(min(score, 0.95), 4)
    if score >= 0.65:
        band = RiskBand.HIGH
        actions = [ReviewAction.REVIEW_RECENT_WORK, ReviewAction.SEND_CHECK_IN]
    elif score >= 0.35:
        band = RiskBand.MEDIUM
        actions = [ReviewAction.REVIEW_RECENT_WORK]
    else:
        band = RiskBand.LOW
        actions = [ReviewAction.NO_ACTION]

    if not claims:
        if missed == 0 and due:
            claims.append(
                EvidenceClaim(
                    claim_code=ClaimCode.ASSESSMENTS_ON_TRACK,
                    evidence_ids=[feature["assessments_missed"].evidence_id],
                )
            )
        else:
            claims.append(
                EvidenceClaim(
                    claim_code=ClaimCode.RECENT_ACTIVITY_PRESENT,
                    evidence_ids=[feature["active_days_last_14"].evidence_id],
                )
            )

    prediction = ValidatedRiskResult(
        prediction_id=_prediction_id(state),
        state_id=state.state_id,
        model_kind=ModelKind.SIMPLE_DEMO,
        model_version=DEMO_MODEL_VERSION,
        raw_risk_score=score,
        display_probability=score,
        calibration_version="identity-demo-v1",
        risk_band=band,
        claims=claims,
        suggested_actions=actions,
        uncertainty_note=(
            "Deterministic integration-demo score; not trained or calibrated for research use."
        ),
        abstain=False,
        abstention_reason=None,
        quality_gate_passed=True,
        fallback_used=False,
        generated_at=generated_at,
        data_origin=state.data_origin,
    )
    return validate_prediction_grounding(state, prediction)
