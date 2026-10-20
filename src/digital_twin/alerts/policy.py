"""Temporary alert policy for the architecture demonstration."""

from __future__ import annotations

import hashlib
from datetime import datetime

from digital_twin.schemas import (
    Alert,
    AlertPriority,
    RiskBand,
    ValidatedRiskResult,
    validate_alert_eligibility,
)


DEMO_ALERT_POLICY_VERSION = "demo-high-risk-v1"


def create_demo_alert(
    prediction: ValidatedRiskResult, *, is_fresh: bool, created_at: datetime
) -> Alert | None:
    """Create an instructor-review alert only for a validated high-risk result."""

    if prediction.abstain or prediction.risk_band is not RiskBand.HIGH:
        return None
    evidence_ids = sorted(
        {evidence_id for claim in prediction.claims for evidence_id in claim.evidence_ids}
    )
    digest = hashlib.sha256(
        f"{prediction.prediction_id}:{DEMO_ALERT_POLICY_VERSION}".encode()
    ).hexdigest()[:16]
    priority = (
        AlertPriority.HIGH
        if prediction.display_probability is not None and prediction.display_probability >= 0.8
        else AlertPriority.MEDIUM
    )
    alert = Alert(
        alert_id=f"alert:demo:{digest}",
        prediction_id=prediction.prediction_id,
        state_id=prediction.state_id,
        policy_version=DEMO_ALERT_POLICY_VERSION,
        priority=priority,
        evidence_ids=evidence_ids,
        is_fresh=is_fresh,
        created_at=created_at,
        data_origin=prediction.data_origin,
    )
    return validate_alert_eligibility(prediction, alert)
