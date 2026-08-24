"""Build replay-origin states, demo predictions, and alerts from PostgreSQL."""

from __future__ import annotations

import csv
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from digital_twin.alerts import create_demo_alert
from digital_twin.models import DEMO_MODEL_VERSION, predict_demo_risk
from digital_twin.persistence import TwinStore
from digital_twin.persistence.models import (
    CoursePresentation,
    Enrolment,
    SourceObservation,
)
from digital_twin.persistence.store import stable_hash
from digital_twin.schemas import DataOrigin
from digital_twin.state import build_weekly_states

REPLAY_PRESENTATION_ID = "moodle-replay:AAA:2030A"
# Replay and empirical states use the same feature definition. Origin and
# presentation identifiers separate them; a second version name would violate
# the store's content-addressed feature-definition invariant.
REPLAY_FEATURE_SET_VERSION = "oulad-demo-features-v1"
CHECKPOINTS = (3, 5, 8, 10)


def build_replay_vertical_slice(
    engine: Engine,
    *,
    prepared_dir: Path,
    built_at: datetime | None = None,
) -> dict[str, Any]:
    built_at = built_at or datetime.now(UTC)
    store = TwinStore(engine)
    sync = store.sync_snapshot(presentation_id=REPLAY_PRESENTATION_ID, now=built_at)
    is_fresh = sync["status"] == "current"
    with Session(engine) as session:
        presentation = session.get(CoursePresentation, REPLAY_PRESENTATION_ID)
        if presentation is None:
            raise RuntimeError("Phase 6 replay presentation is missing")
        enrolment_records = session.scalars(
            select(Enrolment)
            .where(Enrolment.presentation_id == REPLAY_PRESENTATION_ID)
            .order_by(Enrolment.learner_id)
        ).all()
        observations = session.scalars(
            select(SourceObservation)
            .where(SourceObservation.presentation_id == REPLAY_PRESENTATION_ID)
            .where(SourceObservation.observation_kind != "assessment_definition")
            .order_by(SourceObservation.observation_id)
        ).all()
    enrolment_observation = {
        row.learner_id: row.observation_id
        for row in observations
        if row.observation_kind == "enrolment" and row.learner_id is not None
    }
    persistence_enrolments = [
        _persistence_enrolment(row, presentation.source_id) for row in enrolment_records
    ]
    builder_enrolments = [
        {
            **row,
            "source_record_id": enrolment_observation[row["learner_id"]],
        }
        for row in persistence_enrolments
    ]
    activities = [
        {
            "learner_id": row.learner_id,
            "course_day": str(row.course_day),
            "click_count": str(row.event_count or 0),
            "activity_group": (row.event_code or "activity_other").removeprefix("activity_"),
            "source_record_id": row.observation_id,
        }
        for row in observations
        if row.observation_kind == "activity" and row.learner_id is not None
    ]
    assessment_observations = [
        {
            "learner_id": row.learner_id,
            "assessment_id": (row.metadata_json or {})["assessment_id"],
            "submitted_course_day": str(row.course_day),
            "is_banked": "0",
            "score": "" if row.value_json is None else str(row.value_json),
            "score_missing_reason": (row.metadata_json or {}).get(
                "score_missing_reason", "observed"
            ),
            "source_record_id": row.observation_id,
        }
        for row in observations
        if row.observation_kind == "assessment" and row.learner_id is not None
    ]
    assessments, definition_observations = _assessment_definitions(prepared_dir, built_at)
    run_key = stable_hash(
        {
            "presentation": REPLAY_PRESENTATION_ID,
            "feature_set": REPLAY_FEATURE_SET_VERSION,
            "checkpoints": CHECKPOINTS,
            "source_records": [row.record_hash for row in observations],
            "assessment_definitions": definition_observations,
        }
    )
    run_id = f"run:phase7:replay:{run_key[:20]}"
    store.begin_run(
        run_id=run_id,
        source_id=presentation.source_id,
        idempotency_key=run_key,
        started_at=built_at,
        adapter_version="phase7-replay-state-v1",
        schema_version="weekly-state-v1",
    )
    core_summary = store.persist_prepared_core(
        run_id=run_id,
        presentation={
            "presentation_id": presentation.presentation_id,
            "source_id": presentation.source_id,
            "module_code": presentation.module_code,
            "presentation_code": presentation.presentation_code,
            "length_days": presentation.length_days,
            "data_origin": presentation.data_origin,
        },
        enrolments=persistence_enrolments,
        observations=definition_observations,
    )
    states = build_weekly_states(
        enrolments=builder_enrolments,
        activities=activities,
        assessments=assessments,
        assessment_observations=assessment_observations,
        checkpoints=CHECKPOINTS,
        built_at=built_at,
        data_origin=DataOrigin.REPLAYED,
        feature_set_version=REPLAY_FEATURE_SET_VERSION,
        is_fresh=is_fresh,
    )
    predictions = [predict_demo_risk(state, built_at) for state in states]
    alerts = [
        alert
        for state, prediction in zip(states, predictions, strict=True)
        if (
            alert := create_demo_alert(
                prediction,
                is_fresh=state.is_fresh,
                created_at=built_at,
            )
        )
        is not None
    ]
    analytics_summary = store.persist_analytics(
        run_id=run_id,
        states=states,
        predictions=predictions,
        alerts=alerts,
        occurred_at=built_at,
    )
    counts = {
        "states": len(states),
        "predictions": len(predictions),
        "alerts": len(alerts),
        "assessment_definitions": len(definition_observations),
    }
    store.accept_run(run_id=run_id, accepted_at=built_at, counts=counts)
    return {
        "run_id": run_id,
        "presentation_id": REPLAY_PRESENTATION_ID,
        "data_origin": "replayed",
        "sync_status": sync["status"],
        "is_fresh": is_fresh,
        "model_version": DEMO_MODEL_VERSION,
        "warning": (
            "Operational architecture demo only; replay data and simple-rules-v1 "
            "are not predictive research evidence."
        ),
        **counts,
        "states_by_checkpoint": dict(
            sorted(Counter(state.checkpoint_week for state in states).items())
        ),
        "risk_bands": dict(
            sorted(
                Counter(
                    prediction.risk_band.value if prediction.risk_band else "abstain"
                    for prediction in predictions
                ).items()
            )
        ),
        "inserted": {
            **core_summary.inserted,
            **analytics_summary.inserted,
        },
        "replayed": {
            **core_summary.replayed,
            **analytics_summary.replayed,
        },
    }


def _persistence_enrolment(row: Enrolment, source_id: str) -> dict[str, Any]:
    return {
        "presentation_id": row.presentation_id,
        "learner_id": row.learner_id,
        "source_id": source_id,
        "registration_day": "" if row.registration_day is None else row.registration_day,
        "registration_missing_reason": row.registration_missing_reason,
        "unregistration_day": ("" if row.unregistration_day is None else row.unregistration_day),
        "unregistration_missing_reason": row.unregistration_missing_reason,
        "previous_attempts": row.previous_attempts,
        "studied_credits": row.studied_credits,
        "data_origin": row.data_origin,
        "source_record_id": row.source_record_id,
    }


def _assessment_definitions(
    prepared_dir: Path, built_at: datetime
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    del built_at
    with (prepared_dir / "assessments.csv").open(encoding="utf-8") as handle:
        source_rows = list(csv.DictReader(handle))
    calendar_start = datetime(2030, 1, 1, tzinfo=UTC)
    assessments: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    for row in source_rows:
        due_day = row["due_course_day"]
        observation_id = f"moodle-replay:assessment-def:{row['source_assessment_id']}"
        assessments.append(
            {
                **row,
                "presentation_id": REPLAY_PRESENTATION_ID,
                "source_record_id": observation_id,
            }
        )
        if due_day == "":
            continue
        due_at = calendar_start + timedelta(days=int(due_day))
        observations.append(
            {
                "observation_id": observation_id,
                "presentation_id": REPLAY_PRESENTATION_ID,
                "learner_id": None,
                "observation_kind": "assessment_definition",
                "source_record_id": f"assessment-def:{row['source_assessment_id']}",
                "course_day": due_day,
                "event_code": "assessment_due",
                "event_at": due_at,
                "available_at": due_at,
                "time_precision": "day",
                "value": row["weight"],
                "count": 1,
                "adapter_version": "phase7-replay-state-v1",
                "metadata": {"assessment_id": row["assessment_id"]},
                "data_origin": "replayed",
            }
        )
    return assessments, observations
