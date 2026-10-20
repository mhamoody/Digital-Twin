"""Read-only analysis diagnostics without account secrets or learner content."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from digital_twin.persistence.database import create_twin_engine  # noqa: E402
from digital_twin.workspace.errors import ERRORS  # noqa: E402
from digital_twin.workspace.llm import OllamaClient  # noqa: E402
from digital_twin.workspace.models import Analysis, AnalysisJob, Snapshot  # noqa: E402

KNOWN_CODES = set(ERRORS)
ERROR_HINTS = {code: failure.detail for code, failure in ERRORS.items()}


def safe_code(value: Any) -> str:
    if value is None or value == "":
        return "NO_ERROR_CODE_RECORDED"
    return value if isinstance(value, str) and value in KNOWN_CODES else "UNRECOGNIZED_ERROR_CODE"


def _safe_model(value: Any) -> str:
    return (
        value
        if isinstance(value, str) and re.fullmatch(r"[a-zA-Z0-9_.:-]{1,80}", value)
        else "unknown"
    )


def _safe_readiness(value: dict) -> dict:
    status = value.get("status")
    if status not in {
        "ready",
        "unavailable",
        "model_missing",
        "configuration_error",
        "not_checked",
    }:
        status = "unavailable"
    model_digest = value.get("digest")
    if not isinstance(model_digest, str) or not re.fullmatch(
        r"(?:sha256:)?[a-fA-F0-9]{12,128}", model_digest
    ):
        model_digest = None
    return {
        "status": status,
        "model": _safe_model(value.get("model")),
        "digest": model_digest,
        "error_code": safe_code(value.get("error_code")) if value.get("error_code") else None,
        "inference_verified": False,
        "meaning": "Readiness checks model metadata only; it does not perform a prediction.",
    }


def _quantile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * fraction
    left, right = math.floor(position), math.ceil(position)
    return round(values[left] + (values[right] - values[left]) * (position - left), 4)


def collect_diagnosis(
    engine: Any, course_id: str | None = None, readiness: dict | None = None
) -> dict:
    """Only SELECT/inspection operations; does not retry jobs or initialize tables."""
    report: dict[str, Any] = {
        "diagnostic_version": "analysis-diagnostics-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "database_backend": engine.dialect.name,
        "course_filter": course_id,
        "privacy": "No learner IDs/names, posts, prompts, account files, "
        "credentials, or environment values.",
        "read_only": True,
    }
    schema = None if engine.dialect.name == "sqlite" else "analytics"
    tables = set(inspect(engine).get_table_names(schema=schema))
    required = {"workspace_analysis_job", "workspace_snapshot", "workspace_analysis"}
    absent = sorted(required - tables)
    if absent:
        report.update(database_status="workspace_tables_missing", missing_tables=absent)
        return report
    with Session(engine) as session:
        query = select(AnalysisJob, Snapshot.course_id, Snapshot.week).join(
            Snapshot, AnalysisJob.state_id == Snapshot.id
        )
        if course_id:
            query = query.where(Snapshot.course_id == course_id)
        jobs = session.execute(query.order_by(AnalysisJob.updated_at.desc())).all()
        counts = Counter()
        failures = Counter()
        course_counts: dict[tuple[str, int], Counter] = defaultdict(Counter)
        latest_failures = []
        for job, actual_course, week in jobs:
            counts[(job.model_kind, job.status)] += 1
            course_counts[(actual_course, week)][job.status] += 1
            if job.status == "failed":
                code = safe_code(job.error_code)
                failures[(job.model_kind, code)] += 1
                if len(latest_failures) < 20:
                    # state_id may encode a learner ID in legacy adapters; never expose it.
                    latest_failures.append(
                        {
                            "job_id": job.id
                            if re.fullmatch(r"[a-f0-9]{64}", job.id)
                            else "nonstandard-job-id",
                            "course_id": actual_course,
                            "checkpoint_week": week,
                            "model_kind": job.model_kind,
                            "error_code": code,
                            "attempts": job.attempts,
                            "updated_at": job.updated_at.isoformat(),
                        }
                    )
        analyses = select(Analysis).join(Snapshot, Analysis.state_id == Snapshot.id)
        if course_id:
            analyses = analyses.where(Snapshot.course_id == course_id)
        observations = session.scalars(
            analyses.order_by(Analysis.created_at.desc()).limit(1000)
        ).all()
        latencies: dict[str, list[float]] = defaultdict(list)
        for item in observations:
            latency = item.payload.get("latency_seconds")
            if (
                item.model_kind == "llm"
                and item.payload.get("inference_performed") is True
                and isinstance(latency, (int, float))
                and not isinstance(latency, bool)
                and math.isfinite(latency)
                and latency >= 0
            ):
                latencies[_safe_model(item.payload.get("model_version"))].append(float(latency))
        report.update(
            database_status="ok",
            total_jobs=len(jobs),
            job_counts=[
                {"model_kind": kind, "status": status, "count": count}
                for (kind, status), count in sorted(counts.items())
            ],
            failure_counts=[
                {
                    "model_kind": kind,
                    "error_code": code,
                    "count": count,
                    "interpretation": ERROR_HINTS.get(
                        code,
                        "Check the corresponding structured worker error; "
                        "no cause is inferred from the count alone.",
                    ),
                }
                for (kind, code), count in sorted(failures.items())
            ],
            courses_and_checkpoints=[
                {"course_id": course, "checkpoint_week": week, "status_counts": dict(statuses)}
                for (course, week), statuses in sorted(course_counts.items())
            ],
            latest_failures=latest_failures,
            successful_llm_latency=[
                {
                    "model": model,
                    "sample_size": len(values),
                    "p50_seconds": _quantile(values, 0.5),
                    "p95_seconds": _quantile(values, 0.95),
                }
                for model, values in sorted(latencies.items())
            ],
            latency_scope="Successful LLM inferences among the newest 1,000 stored analyses; "
            "failed requests are excluded.",
            failure_scope="Persisted job state. A newer successful job can coexist "
            "with an older failed version.",
        )
    if readiness is None:
        try:
            readiness = OllamaClient().readiness()
        except (ValueError, OSError):
            readiness = {"status": "configuration_error"}
    report["model_readiness"] = _safe_readiness(readiness)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.environ.get("DIGITAL_TWIN_DATABASE_URL"))
    parser.add_argument(
        "--course", help="Optional exact course-offering ID; no learner filter is accepted."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional new JSON report file, e.g. artifacts/workspace/diagnosis.json.",
    )
    args = parser.parse_args()
    if not args.database_url:
        parser.error(
            "Configure DIGITAL_TWIN_DATABASE_URL after loading .env.lobot, or pass --database-url."
        )
    try:
        parsed = make_url(args.database_url)
    except (ValueError, SQLAlchemyError):
        parser.error(
            "Database configuration could not be parsed; the connection value is not printed."
        )
    if parsed.drivername.startswith("sqlite") and parsed.database not in (None, "", ":memory:"):
        if not Path(parsed.database).is_file():
            parser.error(
                "The configured SQLite database does not exist; diagnostic mode will not create it."
            )
    if args.output and args.output.exists():
        parser.error(
            "Output already exists. Choose a new --output path; existing diagnostics are preserved."
        )
    engine = None
    try:
        engine = create_twin_engine(args.database_url)
        report = collect_diagnosis(engine, args.course)
    except SQLAlchemyError:
        report = {
            "read_only": True,
            "database_status": "query_failed",
            "error_code": "DATABASE_QUERY_FAILED",
            "guidance": "Check operator database access and migrations. "
            "Connection details are intentionally omitted.",
        }
    finally:
        if engine is not None:
            engine.dispose()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("database_status") == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
