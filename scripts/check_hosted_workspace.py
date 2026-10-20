"""Operator check of storage and the real model, with a non-secret evidence report."""

import argparse
import json
import os
import time
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from digital_twin.persistence import create_twin_engine
from digital_twin.workspace.llm import OllamaClient, analyze
from digital_twin.workspace.models import Analysis, Snapshot
from digital_twin.workspace.store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--llm", action="store_true", help="Perform one real inference; may take up to 120 seconds"
    )
    args = parser.parse_args()
    url = os.environ.get("DIGITAL_TWIN_DATABASE_URL")
    if not url:
        parser.error("Load .env.lobot first")
    approved = Path("var/models/predictor.json")
    if approved.is_file():
        os.environ.setdefault(
            "DIGITAL_TWIN_LLM_DIGEST", json.loads(approved.read_text())["digest"]
        )
    engine = create_twin_engine(url)
    store = Store(engine)
    report = {
        "database_backend": engine.dialect.name,
        "model": OllamaClient().readiness(),
        "jobs": store.job_summary(),
        "courses": [],
    }
    with engine.connect() as connection:
        report["database_check"] = (
            connection.scalar(text("PRAGMA quick_check"))
            if engine.dialect.name == "sqlite"
            else str(connection.scalar(text("SELECT 1")))
        )
    for course in store.courses():
        if not course["checkpoints"]:
            continue
        started = time.perf_counter()
        current = store.workspace(course["presentation_id"], course["checkpoints"][-1])
        report["courses"].append(
            {
                "presentation_id": course["presentation_id"],
                "summary": current["summary"],
                "overview_seconds": round(time.perf_counter() - started, 3),
            }
        )
        if sum(current["distribution"].values()) != current["summary"]["enrolled"]:
            raise SystemExit("Course totals do not reconcile")
    with Session(engine) as session:
        report["stored_snapshots"] = session.scalar(select(func.count()).select_from(Snapshot))
        report["stored_results"] = session.scalar(select(func.count()).select_from(Analysis))
        state = session.scalar(
            select(Snapshot)
            .where(Snapshot.course_id.like("synthetic:%"), Snapshot.week == 8)
            .order_by(Snapshot.course_id, Snapshot.learner_id)
            .limit(1)
        )
        if args.llm:
            if state is None:
                raise SystemExit("No synthetic week-eight snapshot found")
            result = analyze(store.get_snapshot(state.id), store.get_policy(state.course_id))
            report["real_inference"] = result
            if not result.get("inference_performed"):
                raise SystemExit(
                    "Pre-inference abstention: a live model call has not yet been verified"
                )
    output = Path("artifacts/workspace/hosted-check.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    engine.dispose()
    print(json.dumps(report, indent=2))
    print("Check report:", output)
    print("Synthetic/operational checks do not establish empirical predictive accuracy.")


if __name__ == "__main__":
    main()
