"""Accelerated weekly replay orchestration for the Moodle adapter contract."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Engine

from digital_twin.persistence import TwinStore
from digital_twin.persistence.store import stable_hash

from .moodle import (
    MOODLE_ADAPTER_VERSION,
    ControlledExport,
    MoodleControlledExportAdapter,
    MoodleExportRecord,
    ReplayWatermark,
    _learner_id,
)

CONNECTOR_ID = "moodle-controlled-export:oulad-aaa-2030a-v1"


def replay_controlled_export(
    engine: Engine,
    controlled_export: ControlledExport,
    *,
    weeks: int = 12,
    ingestion_started_at: datetime | None = None,
) -> dict[str, Any]:
    if not 1 <= weeks <= 52:
        raise ValueError("replay weeks must be between 1 and 52")
    header = controlled_export.header
    store = TwinStore(engine)
    started = ingestion_started_at or datetime.now(UTC)
    manifest_hash = stable_hash(
        {
            "header": header.model_dump(mode="json", exclude={"exported_at"}),
            "records": controlled_export.records,
        }
    )
    store.register_source(
        source_id=header.source_id,
        name=header.source_name,
        version="controlled-export-v1",
        licence_note=(
            "Operational replay derived from locally prepared OULAD; not empirical Moodle data."
        ),
        manifest_hash=manifest_hash,
        imported_at=started,
    )
    presentation = {
        "presentation_id": header.presentation_id,
        "source_id": header.source_id,
        "module_code": header.module_code,
        "presentation_code": header.presentation_code,
        "length_days": header.length_days,
        "data_origin": "replayed",
    }
    enrolments = _enrolment_rows(controlled_export)
    bootstrap_key = stable_hash(
        {"connector": CONNECTOR_ID, "presentation": presentation, "enrolments": enrolments}
    )
    bootstrap_run = f"run:moodle:bootstrap:{bootstrap_key[:20]}"
    store.begin_run(
        run_id=bootstrap_run,
        source_id=header.source_id,
        idempotency_key=bootstrap_key,
        started_at=started,
        adapter_version=MOODLE_ADAPTER_VERSION,
        schema_version="canonical-observation-v1",
    )
    store.persist_prepared_core(
        run_id=bootstrap_run,
        presentation=presentation,
        enrolments=enrolments,
        observations=[],
    )
    bootstrap_counts = {
        "course_presentations": 1,
        "learners": len(enrolments),
        "enrolments": len(enrolments),
    }
    store.accept_run(
        run_id=bootstrap_run,
        accepted_at=started,
        counts=bootstrap_counts,
    )
    store.initialize_sync(
        connector_id=CONNECTOR_ID,
        source_id=header.source_id,
        presentation_id=header.presentation_id,
        stale_after_minutes=60,
        initialized_at=started,
    )

    adapter = MoodleControlledExportAdapter(header)
    watermark = ReplayWatermark()
    total_inserted = 0
    total_replayed = 0
    total_quarantined = 0
    weekly_results: list[dict[str, Any]] = []
    for week in range(1, weeks + 1):
        through_at = header.course_start_at + timedelta(days=week * 7) - timedelta(microseconds=1)
        provisional_run = f"run:moodle:w{week:02}"
        batch = adapter.map_records(
            controlled_export.records,
            run_id=provisional_run,
            after=watermark,
            through_at=through_at,
        )
        batch_key = stable_hash(
            {
                "connector": CONNECTOR_ID,
                "week": week,
                "observations": [
                    observation.model_dump(mode="json", exclude={"ingestion_run_id"})
                    for observation in batch.observations
                ],
                "quarantines": [item.payload_hash for item in batch.quarantines],
            }
        )
        run_id = f"run:moodle:w{week:02}:{batch_key[:16]}"
        run_created = store.begin_run(
            run_id=run_id,
            source_id=header.source_id,
            idempotency_key=batch_key,
            started_at=started + timedelta(seconds=week),
            adapter_version=MOODLE_ADAPTER_VERSION,
            schema_version="canonical-observation-v1",
        )
        observations = [
            _persistence_observation(observation.model_copy(update={"ingestion_run_id": run_id}))
            for observation in batch.observations
        ]
        summary = store.persist_prepared_core(
            run_id=run_id,
            presentation=presentation,
            enrolments=enrolments,
            observations=observations,
        )
        for item in batch.quarantines:
            store.quarantine_record(
                connector_id=CONNECTOR_ID,
                source_record_id=item.source_record_id,
                reason_code=item.reason_code,
                payload_hash=item.payload_hash,
                error_json={"errors": item.errors},
                seen_at=started + timedelta(seconds=week),
            )
        counts = {
            "observations": len(batch.observations),
            "quarantined": len(batch.quarantines),
        }
        store.accept_run(
            run_id=run_id,
            accepted_at=started + timedelta(seconds=week),
            counts=counts,
        )
        store.record_sync_success(
            connector_id=CONNECTOR_ID,
            cursor_at=batch.watermark.occurred_at,
            cursor_key=batch.watermark.source_record_id,
            succeeded_at=started + timedelta(seconds=week),
            processed_count=len(batch.observations) if run_created else 0,
            quarantined_count=len(batch.quarantines) if run_created else 0,
        )
        inserted = summary.inserted.get("source_observation", 0)
        replayed = summary.replayed.get("source_observation", 0)
        total_inserted += inserted
        total_replayed += replayed
        total_quarantined += len(batch.quarantines) if run_created else 0
        weekly_results.append(
            {
                "week": week,
                "scanned": batch.scanned_count,
                "inserted": inserted,
                "replayed": replayed,
                "quarantined": len(batch.quarantines),
                "watermark_at": batch.watermark.occurred_at.isoformat()
                if batch.watermark.occurred_at
                else None,
                "watermark_key": batch.watermark.source_record_id,
            }
        )
        watermark = batch.watermark
    snapshot = store.sync_snapshot(
        presentation_id=header.presentation_id,
        now=started + timedelta(seconds=weeks),
    )
    return {
        "connector_id": CONNECTOR_ID,
        "presentation_id": header.presentation_id,
        "source_origin": "replayed",
        "warning": header.warning,
        "weeks_replayed": weeks,
        "learner_count": len(enrolments),
        "record_count": len(controlled_export.records),
        "inserted_observations": total_inserted,
        "replayed_observations": total_replayed,
        "quarantined_records": total_quarantined,
        "weekly_results": weekly_results,
        "sync_snapshot": snapshot,
    }


def _enrolment_rows(controlled_export: ControlledExport) -> list[dict[str, Any]]:
    header = controlled_export.header
    rows = []
    for raw in controlled_export.records:
        if raw.get("record_type") != "enrolment":
            continue
        record = MoodleExportRecord.model_validate(raw)
        course_day = (record.occurred_at.date() - header.course_start_at.date()).days
        rows.append(
            {
                "presentation_id": header.presentation_id,
                "learner_id": _learner_id(header.scenario_id, record.source_user_id),
                "source_id": header.source_id,
                "registration_day": course_day,
                "registration_missing_reason": "observed",
                "unregistration_day": "",
                "unregistration_missing_reason": "not_applicable",
                "previous_attempts": int(record.metadata["previous_attempts"]),
                "studied_credits": int(record.metadata["studied_credits"]),
                "data_origin": "replayed",
                "source_record_id": record.source_record_id,
            }
        )
    return rows


def _persistence_observation(observation) -> dict[str, Any]:
    payload = observation.model_dump(mode="python")
    payload["observation_kind"] = observation.kind.value
    payload["data_origin"] = observation.data_origin.value
    payload["time_precision"] = observation.time_precision.value
    payload.pop("kind")
    payload.pop("schema_version")
    payload.pop("source_id")
    payload.pop("ingestion_run_id")
    payload.pop("available_course_day")
    return payload
