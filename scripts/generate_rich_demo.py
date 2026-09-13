"""Generate an isolated, reproducible rich synthetic instructor demonstration."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from digital_twin.persistence.database import (  # noqa: E402
    create_twin_engine,
    create_validation_schema,
)
from digital_twin.workspace.features import degrade_snapshot  # noqa: E402
from digital_twin.workspace.store import Store  # noqa: E402
from digital_twin.workspace.synthetic import generate_dataset, seed_support_history  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--learners-per-course", type=int, default=120)
    parser.add_argument("--weeks", type=int, default=16)
    parser.add_argument("--database-url", default=os.environ.get("DIGITAL_TWIN_DATABASE_URL"))
    parser.add_argument("--export-dir", type=Path)
    parser.add_argument(
        "--include-private-oracle",
        action="store_true",
        help="Export hidden trajectory labels separately, never as model input.",
    )
    parser.add_argument(
        "--export-fault-fixtures",
        action="store_true",
        help="Export paired missing/stale/partial snapshots separately from the base cohort.",
    )
    args = parser.parse_args()
    if not args.database_url and not args.export_dir:
        parser.error("Choose --export-dir or configure DIGITAL_TWIN_DATABASE_URL / --database-url.")
    if (args.include_private_oracle or args.export_fault_fixtures) and not args.export_dir:
        parser.error("The optional fixture/oracle export flags require --export-dir.")
    if args.export_dir:
        expected_files = [
            "courses.jsonl",
            "enrolments.jsonl",
            "events.jsonl",
            "snapshots.jsonl",
            "manifest.json",
        ]
        if args.include_private_oracle:
            expected_files.append("private_scenario_oracle.json")
        if args.export_fault_fixtures:
            expected_files.append("fault_fixtures.jsonl")
        for filename in expected_files:
            target = args.export_dir.resolve() / filename
            if target.exists():
                raise SystemExit(f"Refusing to overwrite an existing export: {target}")
    dataset = generate_dataset(args.seed, args.learners_per_course, args.weeks)
    if args.database_url:
        engine = create_twin_engine(args.database_url)
        try:
            if engine.dialect.name == "sqlite":
                create_validation_schema(engine)
            store = Store(engine)
            counts = store.ingest_dataset(dataset)
            print("Synthetic workspace import:", json.dumps(counts, sort_keys=True))
            print(
                "Synthetic support history:",
                json.dumps(seed_support_history(store, dataset), sort_keys=True),
            )
        finally:
            engine.dispose()
    if args.export_dir:
        output = args.export_dir.resolve()
        output.mkdir(parents=True, exist_ok=True)
        for key in ("courses", "enrolments", "events", "snapshots"):
            target = output / f"{key}.jsonl"
            if target.exists():
                raise SystemExit(f"Refusing to overwrite an existing export: {target}")
        for key in ("courses", "enrolments", "events", "snapshots"):
            with (output / f"{key}.jsonl").open("x", encoding="utf-8") as stream:
                for item in dataset[key]:
                    payload = item.model_dump(mode="json") if hasattr(item, "model_dump") else item
                    stream.write(json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n")
        with (output / "manifest.json").open("x", encoding="utf-8") as stream:
            json.dump(dataset["manifest"], stream, indent=2, sort_keys=True)
        if args.include_private_oracle:
            with (output / "private_scenario_oracle.json").open("x", encoding="utf-8") as stream:
                json.dump(dataset["oracle"], stream, indent=2)
        if args.export_fault_fixtures:
            with (output / "fault_fixtures.jsonl").open("x", encoding="utf-8") as stream:
                for snapshot in dataset["snapshots"]:
                    if snapshot.checkpoint_week != args.weeks:
                        continue
                    for mode in ("missing_grades", "partial_activity", "stale_activity"):
                        fixture = {
                            "base_state_id": snapshot.state_id,
                            "fault_mode": mode,
                            "snapshot": degrade_snapshot(snapshot, mode).model_dump(mode="json"),
                        }
                        stream.write(json.dumps(fixture, sort_keys=True) + "\n")
        print(f"Synthetic exports written to {output}")
    print(json.dumps(dataset["manifest"], indent=2, sort_keys=True))
    print("All generated records are synthetic; empirical course data is unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
