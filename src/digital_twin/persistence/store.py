"""Idempotent relational store for prepared records and model artifacts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, func, insert, select
from sqlalchemy.orm import Session

from digital_twin.schemas import Alert, ValidatedRiskResult, WeeklyState

from .models import (
    AlertEvidence,
    AlertRecord,
    AlertReview,
    CoursePresentation,
    Enrolment,
    FeatureSet,
    FeatureSourceSample,
    IngestionRun,
    Learner,
    ModelVersion,
    PersistenceEvent,
    PredictionAction,
    PredictionClaim,
    PredictionRecord,
    QuarantinedRecord,
    SourceDataset,
    SourceObservation,
    SyncCursor,
    WeeklyFeatureRecord,
    WeeklyStateRecord,
)


class PersistenceConflict(RuntimeError):
    """An existing immutable identifier was presented with different content."""


@dataclass
class PersistenceSummary:
    inserted: dict[str, int] = field(default_factory=dict)
    replayed: dict[str, int] = field(default_factory=dict)

    def mark(self, entity: str, *, created: bool, count: int = 1) -> None:
        target = self.inserted if created else self.replayed
        target[entity] = target.get(entity, 0) + count


def stable_hash(value: Any, *, drop_keys: Iterable[str] = ()) -> str:
    """Hash JSON-compatible content with optional non-semantic timestamps removed."""

    dropped = set(drop_keys)

    def normalize(item: Any) -> Any:
        if isinstance(item, dict):
            return {key: normalize(val) for key, val in sorted(item.items()) if key not in dropped}
        if isinstance(item, list):
            return [normalize(val) for val in item]
        if isinstance(item, datetime):
            return item.isoformat()
        return item

    payload = json.dumps(normalize(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TwinStore:
    """Persist immutable artifacts and append-only alert review history."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def register_source(
        self,
        *,
        source_id: str,
        name: str,
        version: str,
        licence_note: str,
        manifest_hash: str,
        imported_at: datetime,
    ) -> bool:
        with Session(self.engine) as session, session.begin():
            existing = session.get(SourceDataset, source_id)
            if existing:
                if existing.manifest_hash != manifest_hash:
                    raise PersistenceConflict(f"source dataset changed for {source_id}")
                return False
            session.add(
                SourceDataset(
                    source_id=source_id,
                    name=name,
                    version=version,
                    licence_note=licence_note,
                    manifest_hash=manifest_hash,
                    imported_at=imported_at,
                )
            )
            return True

    def begin_run(
        self,
        *,
        run_id: str,
        source_id: str,
        idempotency_key: str,
        started_at: datetime,
        adapter_version: str = "oulad-phase3-store-v1",
        schema_version: str = "twin-lineage-v1",
    ) -> bool:
        with Session(self.engine) as session, session.begin():
            existing = session.get(IngestionRun, run_id)
            if existing:
                if existing.idempotency_key != idempotency_key:
                    raise PersistenceConflict(f"ingestion run changed for {run_id}")
                return False
            session.add(
                IngestionRun(
                    run_id=run_id,
                    source_id=source_id,
                    adapter_version=adapter_version,
                    schema_version=schema_version,
                    idempotency_key=idempotency_key,
                    status="started",
                    started_at=started_at,
                    counts_json={},
                )
            )
            return True

    def persist_prepared_core(
        self,
        *,
        run_id: str,
        presentation: dict[str, Any],
        enrolments: list[dict[str, Any]],
        observations: list[dict[str, Any]],
    ) -> PersistenceSummary:
        summary = PersistenceSummary()
        with Session(self.engine) as session, session.begin():
            presentation_values = {
                "presentation_id": presentation["presentation_id"],
                "source_id": presentation["source_id"],
                "module_code": presentation["module_code"],
                "presentation_code": presentation["presentation_code"],
                "length_days": int(presentation["length_days"]),
                "data_origin": presentation["data_origin"],
            }
            self._immutable(
                session,
                CoursePresentation,
                presentation["presentation_id"],
                {**presentation_values, "record_hash": stable_hash(presentation_values)},
                summary,
                "course_presentation",
            )

            for row in enrolments:
                learner_values = {
                    "learner_id": row["learner_id"],
                    "source_id": row["source_id"],
                }
                self._immutable(
                    session,
                    Learner,
                    row["learner_id"],
                    {**learner_values, "record_hash": stable_hash(learner_values)},
                    summary,
                    "learner",
                )
                values = {
                    "presentation_id": row["presentation_id"],
                    "learner_id": row["learner_id"],
                    "registration_day": _optional_int(row["registration_day"]),
                    "registration_missing_reason": row["registration_missing_reason"],
                    "unregistration_day": _optional_int(row["unregistration_day"]),
                    "unregistration_missing_reason": row["unregistration_missing_reason"],
                    "previous_attempts": int(row["previous_attempts"]),
                    "studied_credits": int(row["studied_credits"]),
                    "data_origin": row["data_origin"],
                    "source_record_id": row["source_record_id"],
                }
                self._immutable(
                    session,
                    Enrolment,
                    {
                        "presentation_id": row["presentation_id"],
                        "learner_id": row["learner_id"],
                    },
                    {**values, "record_hash": stable_hash(values)},
                    summary,
                    "enrolment",
                )

            self._bulk_observations(session, run_id, observations, summary)
        return summary

    def persist_analytics(
        self,
        *,
        run_id: str,
        states: list[WeeklyState],
        predictions: list[ValidatedRiskResult],
        alerts: list[Alert],
        occurred_at: datetime,
    ) -> PersistenceSummary:
        if not states:
            raise ValueError("at least one weekly state is required")
        summary = PersistenceSummary()
        with Session(self.engine) as session, session.begin():
            existing_features = {
                (state_id, feature_name): record_hash
                for state_id, feature_name, record_hash in session.execute(
                    select(
                        WeeklyFeatureRecord.state_id,
                        WeeklyFeatureRecord.feature_name,
                        WeeklyFeatureRecord.record_hash,
                    )
                ).tuples()
            }
            existing_source_samples = set(
                session.execute(
                    select(
                        FeatureSourceSample.state_id,
                        FeatureSourceSample.feature_name,
                        FeatureSourceSample.observation_id,
                    )
                )
                .tuples()
                .all()
            )
            feature_names = sorted({feature.name for state in states for feature in state.features})
            feature_definition = {
                "schema_version": "weekly-state-v1",
                "features": feature_names,
                "cutoff_rule": "7 * checkpoint_week - 1",
            }
            feature_version = states[0].feature_set_version
            feature_values = {
                "feature_set_version": feature_version,
                "definition_json": feature_definition,
                "definition_hash": stable_hash(feature_definition),
                "created_at": occurred_at,
            }
            self._immutable(
                session,
                FeatureSet,
                feature_version,
                feature_values,
                summary,
                "feature_set",
                compare_field="definition_hash",
            )

            for state in states:
                self._persist_state(
                    session,
                    state,
                    run_id,
                    occurred_at,
                    summary,
                    existing_features,
                    existing_source_samples,
                )
            for prediction in predictions:
                self._persist_prediction(session, prediction, run_id, occurred_at, summary)
            for alert in alerts:
                self._persist_alert(session, alert, run_id, occurred_at, summary)
        return summary

    def accept_run(
        self, *, run_id: str, accepted_at: datetime, counts: dict[str, int]
    ) -> None:
        with Session(self.engine) as session, session.begin():
            run = session.get(IngestionRun, run_id)
            if run is None:
                raise KeyError(run_id)
            if run.status == "accepted":
                if run.counts_json != counts:
                    raise PersistenceConflict(f"accepted counts changed for {run_id}")
                return
            run.status = "accepted"
            run.accepted_at = accepted_at
            run.counts_json = counts
            self._audit(
                session,
                run_id,
                "ingestion_run",
                run_id,
                "accepted",
                stable_hash(counts),
                accepted_at,
            )

    def fail_run(self, *, run_id: str, failed_at: datetime, counts: dict[str, int]) -> None:
        with Session(self.engine) as session, session.begin():
            run = session.get(IngestionRun, run_id)
            if run is None:
                raise KeyError(run_id)
            if run.status == "accepted":
                raise PersistenceConflict(f"accepted run cannot fail: {run_id}")
            run.status = "failed"
            run.counts_json = counts
            self._audit(
                session,
                run_id,
                "ingestion_run",
                run_id,
                "failed",
                stable_hash(counts),
                failed_at,
            )

    def initialize_sync(
        self,
        *,
        connector_id: str,
        source_id: str,
        presentation_id: str,
        stale_after_minutes: int,
        initialized_at: datetime,
    ) -> None:
        with Session(self.engine) as session, session.begin():
            cursor = session.get(SyncCursor, connector_id)
            if cursor is not None:
                if cursor.source_id != source_id or cursor.presentation_id != presentation_id:
                    raise PersistenceConflict(f"sync connector identity changed: {connector_id}")
                return
            session.add(
                SyncCursor(
                    connector_id=connector_id,
                    source_id=source_id,
                    presentation_id=presentation_id,
                    cursor_at=None,
                    cursor_key=None,
                    last_success_at=None,
                    status="current",
                    consecutive_failures=0,
                    processed_count=0,
                    quarantined_count=0,
                    stale_after_minutes=stale_after_minutes,
                    updated_at=initialized_at,
                )
            )

    def record_sync_success(
        self,
        *,
        connector_id: str,
        cursor_at: datetime | None,
        cursor_key: str | None,
        succeeded_at: datetime,
        processed_count: int,
        quarantined_count: int,
    ) -> None:
        with Session(self.engine) as session, session.begin():
            cursor = session.scalar(
                select(SyncCursor)
                .where(SyncCursor.connector_id == connector_id)
                .with_for_update()
            )
            if cursor is None:
                raise KeyError(connector_id)
            prior = _cursor_tuple(cursor.cursor_at, cursor.cursor_key)
            proposed = _cursor_tuple(cursor_at, cursor_key)
            if proposed < prior:
                if processed_count == 0 and quarantined_count == 0:
                    return
                raise PersistenceConflict(f"sync cursor moved backwards: {connector_id}")
            cursor.cursor_at = cursor_at
            cursor.cursor_key = cursor_key
            cursor.last_success_at = succeeded_at
            cursor.status = "current"
            cursor.consecutive_failures = 0
            cursor.processed_count += processed_count
            cursor.quarantined_count += quarantined_count
            cursor.updated_at = succeeded_at

    def record_sync_failure(self, *, connector_id: str, failed_at: datetime) -> None:
        with Session(self.engine) as session, session.begin():
            cursor = session.scalar(
                select(SyncCursor)
                .where(SyncCursor.connector_id == connector_id)
                .with_for_update()
            )
            if cursor is None:
                raise KeyError(connector_id)
            cursor.status = "failed"
            cursor.consecutive_failures += 1
            cursor.updated_at = failed_at

    def quarantine_record(
        self,
        *,
        connector_id: str,
        source_record_id: str,
        reason_code: str,
        payload_hash: str,
        error_json: dict[str, Any],
        seen_at: datetime,
    ) -> bool:
        identity = stable_hash({"connector_id": connector_id, "source": source_record_id})
        quarantine_id = f"quarantine:{identity[:24]}"
        with Session(self.engine) as session, session.begin():
            record = session.get(QuarantinedRecord, quarantine_id)
            if record is None:
                session.add(
                    QuarantinedRecord(
                        quarantine_id=quarantine_id,
                        connector_id=connector_id,
                        source_record_id=source_record_id,
                        reason_code=reason_code,
                        payload_hash=payload_hash,
                        error_json=error_json,
                        first_seen_at=seen_at,
                        last_seen_at=seen_at,
                        recovered_at=None,
                        recovery_run_id=None,
                    )
                )
                return True
            record.reason_code = reason_code
            record.payload_hash = payload_hash
            record.error_json = error_json
            record.last_seen_at = seen_at
            record.recovered_at = None
            record.recovery_run_id = None
            return False

    def recover_quarantine(
        self,
        *,
        connector_id: str,
        source_record_id: str,
        recovery_run_id: str,
        recovered_at: datetime,
    ) -> bool:
        with Session(self.engine) as session, session.begin():
            record = session.scalar(
                select(QuarantinedRecord).where(
                    QuarantinedRecord.connector_id == connector_id,
                    QuarantinedRecord.source_record_id == source_record_id,
                )
            )
            if record is None or record.recovered_at is not None:
                return False
            record.recovered_at = recovered_at
            record.recovery_run_id = recovery_run_id
            return True

    def sync_snapshot(self, *, presentation_id: str, now: datetime) -> dict[str, Any]:
        with Session(self.engine) as session:
            cursor = session.scalar(
                select(SyncCursor).where(SyncCursor.presentation_id == presentation_id)
            )
            if cursor is None:
                return {"status": "not_configured"}
            last_success = _aware(cursor.last_success_at)
            age_minutes = (
                None
                if last_success is None
                else max(0.0, (now - last_success).total_seconds() / 60)
            )
            if cursor.status == "failed":
                status = "failed"
            elif age_minutes is None or age_minutes > cursor.stale_after_minutes:
                status = "stale"
            else:
                status = "current"
            active_quarantine = session.scalar(
                select(func.count())
                .select_from(QuarantinedRecord)
                .where(
                    QuarantinedRecord.connector_id == cursor.connector_id,
                    QuarantinedRecord.recovered_at.is_(None),
                )
            ) or 0
            return {
                "status": status,
                "connector_id": cursor.connector_id,
                "last_success_at": last_success,
                "age_minutes": age_minutes,
                "stale_after_minutes": cursor.stale_after_minutes,
                "consecutive_failures": cursor.consecutive_failures,
                "processed_count": cursor.processed_count,
                "quarantined_count": cursor.quarantined_count,
                "active_quarantine_count": active_quarantine,
                "cursor_at": _aware(cursor.cursor_at),
                "cursor_key": cursor.cursor_key,
            }

    def review_alert(
        self,
        *,
        review_id: str,
        alert_id: str,
        reviewer_id: str,
        reviewer_role: str,
        new_status: str,
        note: str | None,
        reviewed_at: datetime,
    ) -> bool:
        transitions = {
            "new": {"reviewed", "dismissed", "resolved"},
            "reviewed": {"resolved", "dismissed"},
            "resolved": set(),
            "dismissed": set(),
        }
        with Session(self.engine) as session, session.begin():
            existing = session.get(AlertReview, review_id)
            review_payload = {
                "review_id": review_id,
                "alert_id": alert_id,
                "reviewer_id": reviewer_id,
                "reviewer_role": reviewer_role,
                "new_status": new_status,
                "note": note,
            }
            review_hash = stable_hash(review_payload)
            if existing:
                if existing.record_hash != review_hash:
                    raise PersistenceConflict(f"alert review changed for {review_id}")
                return False
            alert = session.scalar(
                select(AlertRecord)
                .where(AlertRecord.alert_id == alert_id)
                .with_for_update()
            )
            if alert is None:
                raise KeyError(alert_id)
            if new_status not in transitions[alert.status]:
                raise ValueError(f"invalid alert transition: {alert.status} -> {new_status}")
            prior = alert.status
            session.add(
                AlertReview(
                    **review_payload,
                    previous_status=prior,
                    reviewed_at=reviewed_at,
                    record_hash=review_hash,
                )
            )
            alert.status = new_status
            self._audit(
                session,
                None,
                "alert_review",
                review_id,
                f"{prior}_to_{new_status}",
                review_hash,
                reviewed_at,
            )
            return True

    def lineage_for_alert(self, alert_id: str) -> list[dict[str, Any]]:
        """Return evidence-to-source samples for an alert without exposing outcomes."""

        with Session(self.engine) as session:
            statement = (
                select(
                    AlertRecord.alert_id,
                    PredictionRecord.prediction_id,
                    WeeklyStateRecord.state_id,
                    WeeklyFeatureRecord.feature_name,
                    WeeklyFeatureRecord.evidence_id,
                    SourceObservation.observation_id,
                    SourceObservation.source_record_id,
                )
                .join(PredictionRecord, AlertRecord.prediction_id == PredictionRecord.prediction_id)
                .join(WeeklyStateRecord, PredictionRecord.state_id == WeeklyStateRecord.state_id)
                .join(AlertEvidence, AlertRecord.alert_id == AlertEvidence.alert_id)
                .join(
                    WeeklyFeatureRecord,
                    AlertEvidence.evidence_id == WeeklyFeatureRecord.evidence_id,
                )
                .outerjoin(
                    FeatureSourceSample,
                    (WeeklyFeatureRecord.state_id == FeatureSourceSample.state_id)
                    & (WeeklyFeatureRecord.feature_name == FeatureSourceSample.feature_name),
                )
                .outerjoin(
                    SourceObservation,
                    FeatureSourceSample.observation_id == SourceObservation.observation_id,
                )
                .where(AlertRecord.alert_id == alert_id)
            )
            return [dict(row._mapping) for row in session.execute(statement)]

    def table_counts(self) -> dict[str, int]:
        models = (
            SourceObservation,
            SyncCursor,
            QuarantinedRecord,
            WeeklyStateRecord,
            WeeklyFeatureRecord,
            PredictionRecord,
            PredictionClaim,
            AlertRecord,
            AlertReview,
            PersistenceEvent,
        )
        with Session(self.engine) as session:
            return {
                model.__tablename__: session.scalar(select(func.count()).select_from(model)) or 0
                for model in models
            }

    def _persist_state(
        self,
        session: Session,
        state: WeeklyState,
        run_id: str,
        occurred_at: datetime,
        summary: PersistenceSummary,
        existing_features: dict[tuple[str, str], str],
        existing_source_samples: set[tuple[str, str, str]],
    ) -> None:
        payload = state.model_dump(mode="json")
        record_hash = stable_hash(payload, drop_keys=("built_at",))
        values = {
            "state_id": state.state_id,
            "presentation_id": state.presentation_id,
            "learner_id": state.learner_id,
            "checkpoint_week": state.checkpoint_week,
            "cutoff_course_day": state.cutoff_course_day,
            "feature_set_version": state.feature_set_version,
            "built_at": state.built_at,
            "is_fresh": state.is_fresh,
            "completeness": state.completeness,
            "input_hash": state.input_hash,
            "data_origin": state.data_origin.value,
            "record_hash": record_hash,
        }
        created = self._immutable(
            session, WeeklyStateRecord, state.state_id, values, summary, "weekly_state"
        )
        pending_samples: list[tuple[str, str, str]] = []
        for feature in state.features:
            feature_payload = feature.model_dump(mode="json")
            feature_values = {
                "state_id": state.state_id,
                "feature_name": feature.name,
                "value_json": feature.value,
                "missing_reason": feature.missing_reason.value,
                "evidence_id": feature.evidence_id,
                "provenance_reference": feature.provenance_reference,
                "source_observation_count": feature.source_observation_count,
                "source_observation_hash": feature.source_observation_hash,
                "record_hash": stable_hash(feature_payload),
            }
            feature_key = (state.state_id, feature.name)
            previous_hash = existing_features.get(feature_key)
            if previous_hash is not None:
                if previous_hash != feature_values["record_hash"]:
                    raise PersistenceConflict(f"weekly_feature changed for {feature_key}")
                summary.mark("weekly_feature", created=False)
            else:
                session.add(WeeklyFeatureRecord(**feature_values))
                existing_features[feature_key] = feature_values["record_hash"]
                summary.mark("weekly_feature", created=True)
            for observation_id in feature.source_observation_ids:
                sample_key = (state.state_id, feature.name, observation_id)
                if sample_key in existing_source_samples:
                    summary.mark("feature_source_sample", created=False)
                else:
                    pending_samples.append(sample_key)
                    existing_source_samples.add(sample_key)
                    summary.mark("feature_source_sample", created=True)
        session.flush()
        session.add_all(
            FeatureSourceSample(
                state_id=state_id,
                feature_name=feature_name,
                observation_id=observation_id,
            )
            for state_id, feature_name, observation_id in pending_samples
        )
        session.flush()
        if created:
            self._audit(
                session,
                run_id,
                "weekly_state",
                state.state_id,
                "inserted",
                record_hash,
                occurred_at,
            )

    def _persist_prediction(
        self,
        session: Session,
        prediction: ValidatedRiskResult,
        run_id: str,
        occurred_at: datetime,
        summary: PersistenceSummary,
    ) -> None:
        model_ref = f"{prediction.model_kind.value}:{prediction.model_version}"
        model_config = {
            "warning": "Architecture demo only; not a trained or calibrated research model.",
            "calibration_version": prediction.calibration_version,
        }
        model_values = {
            "model_ref": model_ref,
            "model_kind": prediction.model_kind.value,
            "model_version": prediction.model_version,
            "config_json": model_config,
            "config_hash": stable_hash(model_config),
            "approved_scope": "integration_demo_only",
            "created_at": occurred_at,
        }
        self._immutable(
            session,
            ModelVersion,
            model_ref,
            model_values,
            summary,
            "model_version",
            compare_field="config_hash",
        )
        payload = prediction.model_dump(mode="json")
        record_hash = stable_hash(payload, drop_keys=("generated_at",))
        values = {
            "prediction_id": prediction.prediction_id,
            "state_id": prediction.state_id,
            "model_ref": model_ref,
            "raw_risk_score": prediction.raw_risk_score,
            "display_probability": prediction.display_probability,
            "calibration_version": prediction.calibration_version,
            "risk_band": prediction.risk_band.value if prediction.risk_band else None,
            "uncertainty_note": prediction.uncertainty_note,
            "abstain": prediction.abstain,
            "abstention_reason": prediction.abstention_reason,
            "quality_gate_passed": prediction.quality_gate_passed,
            "fallback_used": prediction.fallback_used,
            "generated_at": prediction.generated_at,
            "data_origin": prediction.data_origin.value,
            "record_hash": record_hash,
        }
        created = self._immutable(
            session, PredictionRecord, prediction.prediction_id, values, summary, "prediction"
        )
        for claim_index, claim in enumerate(prediction.claims):
            for evidence_id in claim.evidence_ids:
                claim_values = {
                    "prediction_id": prediction.prediction_id,
                    "claim_index": claim_index,
                    "evidence_id": evidence_id,
                    "claim_code": claim.claim_code.value,
                }
                self._immutable(
                    session,
                    PredictionClaim,
                    {
                        "prediction_id": prediction.prediction_id,
                        "claim_index": claim_index,
                        "evidence_id": evidence_id,
                    },
                    claim_values,
                    summary,
                    "prediction_claim",
                    compare_field=None,
                )
        for action_index, action in enumerate(prediction.suggested_actions):
            action_values = {
                "prediction_id": prediction.prediction_id,
                "action_index": action_index,
                "action_code": action.value,
            }
            self._immutable(
                session,
                PredictionAction,
                {"prediction_id": prediction.prediction_id, "action_index": action_index},
                action_values,
                summary,
                "prediction_action",
                compare_field=None,
            )
        if created:
            self._audit(
                session,
                run_id,
                "prediction",
                prediction.prediction_id,
                "inserted",
                record_hash,
                occurred_at,
            )

    def _persist_alert(
        self,
        session: Session,
        alert: Alert,
        run_id: str,
        occurred_at: datetime,
        summary: PersistenceSummary,
    ) -> None:
        payload = alert.model_dump(mode="json")
        record_hash = stable_hash(payload, drop_keys=("created_at", "status"))
        values = {
            "alert_id": alert.alert_id,
            "prediction_id": alert.prediction_id,
            "state_id": alert.state_id,
            "policy_version": alert.policy_version,
            "priority": alert.priority.value,
            "status": alert.status.value,
            "is_fresh": alert.is_fresh,
            "created_at": alert.created_at,
            "data_origin": alert.data_origin.value,
            "record_hash": record_hash,
        }
        created = self._immutable(
            session, AlertRecord, alert.alert_id, values, summary, "alert"
        )
        for evidence_id in alert.evidence_ids:
            link = {"alert_id": alert.alert_id, "evidence_id": evidence_id}
            self._immutable(
                session,
                AlertEvidence,
                link,
                link,
                summary,
                "alert_evidence",
                compare_field=None,
            )
        if created:
            self._audit(
                session, run_id, "alert", alert.alert_id, "inserted", record_hash, occurred_at
            )

    def _bulk_observations(
        self,
        session: Session,
        run_id: str,
        observations: list[dict[str, Any]],
        summary: PersistenceSummary,
    ) -> None:
        existing = dict(
            session.execute(
                select(SourceObservation.observation_id, SourceObservation.record_hash)
            )
            .tuples()
            .all()
        )
        pending: list[dict[str, Any]] = []
        for row in observations:
            values = {
                "observation_id": row["observation_id"],
                "run_id": run_id,
                "presentation_id": row["presentation_id"],
                "learner_id": row.get("learner_id") or None,
                "observation_kind": row["observation_kind"],
                "source_record_id": row["source_record_id"],
                "course_day": _optional_int(row.get("course_day")),
                "event_code": row.get("event_code"),
                "event_at": row.get("event_at"),
                "available_at": row.get("available_at"),
                "time_precision": row.get("time_precision"),
                "value_json": row.get("value"),
                "event_count": _optional_int(row.get("count")),
                "adapter_version": row.get("adapter_version"),
                "metadata_json": row.get("metadata") or None,
                "data_origin": row["data_origin"],
                "record_hash": stable_hash(row),
            }
            previous_hash = existing.get(row["observation_id"])
            if previous_hash is not None:
                if previous_hash != values["record_hash"]:
                    raise PersistenceConflict(
                        f"source observation changed for {row['observation_id']}"
                    )
                summary.mark("source_observation", created=False)
            else:
                pending.append(values)
        for start in range(0, len(pending), 5000):
            session.execute(insert(SourceObservation), pending[start : start + 5000])
        summary.mark("source_observation", created=True, count=len(pending))

    @staticmethod
    def _immutable(
        session: Session,
        model,
        key,
        values: dict[str, Any],
        summary: PersistenceSummary,
        entity: str,
        *,
        compare_field: str | None = "record_hash",
    ) -> bool:
        existing = session.get(model, key)
        if existing is not None:
            if compare_field and getattr(existing, compare_field) != values[compare_field]:
                raise PersistenceConflict(f"{entity} changed for {key}")
            if compare_field is None:
                for name, value in values.items():
                    if getattr(existing, name) != value:
                        raise PersistenceConflict(f"{entity} changed for {key}")
            summary.mark(entity, created=False)
            return False
        session.add(model(**values))
        session.flush()
        summary.mark(entity, created=True)
        return True

    @staticmethod
    def _audit(
        session: Session,
        run_id: str | None,
        entity_type: str,
        entity_id: str,
        action: str,
        payload_hash: str,
        occurred_at: datetime,
    ) -> None:
        identity = stable_hash(
            {
                "run_id": run_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "action": action,
                "payload_hash": payload_hash,
            }
        )
        event_id = f"audit:{identity[:24]}"
        if session.get(PersistenceEvent, event_id) is None:
            session.add(
                PersistenceEvent(
                    event_id=event_id,
                    run_id=run_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    action=action,
                    payload_hash=payload_hash,
                    occurred_at=occurred_at,
                )
            )


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def _cursor_tuple(value_at: datetime | None, value_key: str | None) -> tuple[str, str]:
    aware = _aware(value_at)
    return (aware.isoformat() if aware else "", value_key or "")
