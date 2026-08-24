"""Run and validate the complete replay-origin integration demonstration."""

from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from datetime import UTC, datetime
from pathlib import Path

warnings.filterwarnings("ignore", message="Using `httpx` with `starlette.testclient`.*")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import func, select, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from digital_twin.api import create_app  # noqa: E402
from digital_twin.ingestion import (  # noqa: E402
    build_oulad_controlled_export,
    replay_controlled_export,
)
from digital_twin.integration import (  # noqa: E402
    REPLAY_PRESENTATION_ID,
    build_replay_vertical_slice,
)
from digital_twin.persistence import create_twin_engine  # noqa: E402
from digital_twin.persistence.models import (  # noqa: E402
    AlertRecord,
    PredictionRecord,
    SourceObservation,
    WeeklyStateRecord,
)

AUTH = {
    "X-Instructor-ID": "instructor:phase7-gate",
    "X-Instructor-Role": "instructor",
}
EXPECTED_REVISION = "20260806_0002"


def validate(database_url: str, prepared_dir: Path, output_dir: Path) -> dict:
    engine = create_twin_engine(database_url)
    try:
        if engine.dialect.name != "postgresql":
            raise AssertionError("The final acceptance gate requires PostgreSQL")
        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        if revision != EXPECTED_REVISION:
            raise AssertionError(
                f"Expected migration {EXPECTED_REVISION}; found {revision}. "
                "Run `python -m alembic upgrade head`."
            )

        with Session(engine) as session:
            empirical_before = (
                session.scalar(
                    select(func.count())
                    .select_from(SourceObservation)
                    .where(SourceObservation.data_origin == "empirical")
                )
                or 0
            )

        output_dir.mkdir(parents=True, exist_ok=True)
        controlled_export = build_oulad_controlled_export(
            prepared_dir,
            learner_limit=24,
            through_week=12,
        )
        controlled_export.write(output_dir / "moodle_controlled_export.json")
        run_at = datetime.now(UTC)
        first_replay = replay_controlled_export(
            engine,
            controlled_export,
            weeks=12,
            ingestion_started_at=run_at,
        )
        second_replay = replay_controlled_export(
            engine,
            controlled_export,
            weeks=12,
            ingestion_started_at=run_at,
        )
        first_slice = build_replay_vertical_slice(
            engine,
            prepared_dir=prepared_dir,
            built_at=run_at,
        )
        second_slice = build_replay_vertical_slice(
            engine,
            prepared_dir=prepared_dir,
            built_at=run_at,
        )

        if second_replay["inserted_observations"] != 0:
            raise AssertionError("Identical Moodle replay inserted duplicate observations")
        if any(second_slice["inserted"].values()):
            raise AssertionError("Identical state/prediction run inserted duplicate artifacts")
        if first_slice["sync_status"] != "current" or not first_slice["is_fresh"]:
            raise AssertionError("Replay states were not built from a current ingestion snapshot")
        if first_slice["states"] != first_slice["predictions"]:
            raise AssertionError("Not every state received a validated predictor result")
        if first_slice["alerts"] < 1:
            raise AssertionError("Replay scenario produced no instructor-review alert")
        if set(first_slice["states_by_checkpoint"]) != {3, 5, 8, 10}:
            raise AssertionError("Replay scenario did not cover all approved checkpoints")

        with Session(engine) as session:
            empirical_after = (
                session.scalar(
                    select(func.count())
                    .select_from(SourceObservation)
                    .where(SourceObservation.data_origin == "empirical")
                )
                or 0
            )
            origins = {
                "observations": set(
                    session.scalars(
                        select(SourceObservation.data_origin).where(
                            SourceObservation.presentation_id == REPLAY_PRESENTATION_ID
                        )
                    )
                ),
                "states": set(
                    session.scalars(
                        select(WeeklyStateRecord.data_origin).where(
                            WeeklyStateRecord.presentation_id == REPLAY_PRESENTATION_ID
                        )
                    )
                ),
                "predictions": set(
                    session.scalars(
                        select(PredictionRecord.data_origin)
                        .join(
                            WeeklyStateRecord,
                            PredictionRecord.state_id == WeeklyStateRecord.state_id,
                        )
                        .where(WeeklyStateRecord.presentation_id == REPLAY_PRESENTATION_ID)
                    )
                ),
                "alerts": set(
                    session.scalars(
                        select(AlertRecord.data_origin)
                        .join(
                            WeeklyStateRecord,
                            AlertRecord.state_id == WeeklyStateRecord.state_id,
                        )
                        .where(WeeklyStateRecord.presentation_id == REPLAY_PRESENTATION_ID)
                    )
                ),
            }
        if empirical_before != empirical_after:
            raise AssertionError("Operational demo changed empirical observations")
        if any(values != {"replayed"} for values in origins.values()):
            raise AssertionError(f"Replay-origin separation failed: {origins}")

        with TestClient(create_app(engine=engine)) as client:
            overview_response = client.get(
                f"/api/v1/presentations/{REPLAY_PRESENTATION_ID}/overview",
                headers=AUTH,
            )
            alerts_response = client.get(
                "/api/v1/alerts",
                params={"presentation_id": REPLAY_PRESENTATION_ID},
                headers=AUTH,
            )
            overview_response.raise_for_status()
            alerts_response.raise_for_status()
            overview = overview_response.json()
            alert_page = alerts_response.json()
            detail_response = client.get(
                f"/api/v1/alerts/{alert_page['items'][0]['alert_id']}",
                headers=AUTH,
            )
            detail_response.raise_for_status()
            detail = detail_response.json()
        if overview["state_count"] != first_slice["states"]:
            raise AssertionError("API state count differs from the built replay slice")
        if alert_page["total"] != first_slice["alerts"]:
            raise AssertionError("API alert count differs from the built replay slice")
        if detail["feature_set_version"] != "oulad-demo-features-v1":
            raise AssertionError("API detail does not expose the replay feature version")
        if detail["alert"]["model_version"] != "simple-rules-v1":
            raise AssertionError("API hides the temporary predictor label")
        if not detail["claims"] or not detail["evidence"]:
            raise AssertionError("Sample alert is not grounded in persisted evidence")
        if len(detail["prediction_timeline"]) != 4:
            raise AssertionError("Sample learner does not have the four-checkpoint timeline")

        manifest = {
            "schema_version": "course-digital-twin-phase7-manifest-v1",
            "generated_at": datetime.now(UTC).isoformat(),
            "database_backend": engine.dialect.name,
            "migration_revision": revision,
            "presentation_id": REPLAY_PRESENTATION_ID,
            "data_origin": "replayed",
            "source_records": first_replay["record_count"],
            "learners": first_replay["learner_count"],
            "weeks_replayed": first_replay["weeks_replayed"],
            "states": first_slice["states"],
            "predictions": first_slice["predictions"],
            "alerts": first_slice["alerts"],
            "states_by_checkpoint": first_slice["states_by_checkpoint"],
            "risk_bands": first_slice["risk_bands"],
            "sync_status": first_slice["sync_status"],
            "model_kind": "simple_demo",
            "model_version": first_slice["model_version"],
            "sample_alert_id": detail["alert"]["alert_id"],
            "sample_timeline_points": len(detail["prediction_timeline"]),
            "empirical_observations_before": empirical_before,
            "empirical_observations_after": empirical_after,
            "checks": {
                "migration_head": "PASS",
                "twelve_week_replay": "PASS",
                "replay_idempotency": "PASS",
                "state_prediction_idempotency": "PASS",
                "freshness_gate": "PASS",
                "four_checkpoint_coverage": "PASS",
                "schema_valid_prediction_per_state": "PASS",
                "grounded_alert_evidence": "PASS",
                "api_dashboard_read_path": "PASS",
                "origin_separation": "PASS",
                "empirical_observations_unchanged": "PASS",
            },
            "warning": (
                "Operational architecture demo only. Replayed OULAD and simple-rules-v1 "
                "must not be reported as empirical Moodle or predictive-model performance."
            ),
        }
        (output_dir / "phase7_manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        return manifest
    finally:
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.environ.get("DIGITAL_TWIN_DATABASE_URL"))
    parser.add_argument("--prepared-dir", type=Path, default=Path("data/processed/oulad_demo_v1"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/processed/oulad_demo_phase7_v1")
    )
    args = parser.parse_args()
    if not args.database_url:
        raise ValueError("DIGITAL_TWIN_DATABASE_URL or --database-url is required")
    manifest = validate(args.database_url, args.prepared_dir, args.output_dir)
    print("COURSE DIGITAL TWIN PHASE 7 ACCEPTANCE GATE: PASS")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
