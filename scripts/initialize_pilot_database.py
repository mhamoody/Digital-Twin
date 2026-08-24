"""Initialize or upgrade the file-backed SQLite database used by the Lobot pilot."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from digital_twin.persistence import create_twin_engine, create_validation_schema  # noqa: E402

SOURCE_OBSERVATION_ADDITIONS = {
    "event_code": "VARCHAR(128)",
    "event_at": "DATETIME",
    "available_at": "DATETIME",
    "time_precision": "VARCHAR(32)",
    "value_json": "JSON",
    "event_count": "INTEGER",
    "adapter_version": "VARCHAR(64)",
    "metadata_json": "JSON",
}


def add_legacy_observation_columns(engine) -> list[str]:
    """Upgrade the pre-sync SQLite pilot without rewriting existing records."""

    existing = {
        column["name"] for column in inspect(engine).get_columns("source_observation")
    }
    additions = [name for name in SOURCE_OBSERVATION_ADDITIONS if name not in existing]
    if not additions:
        return []
    with engine.begin() as connection:
        for name in additions:
            column_type = SOURCE_OBSERVATION_ADDITIONS[name]
            connection.execute(
                text(f"ALTER TABLE source_observation ADD COLUMN {name} {column_type}")
            )
    return additions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.environ.get("DIGITAL_TWIN_DATABASE_URL"))
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("DIGITAL_TWIN_DATABASE_URL is required.")
    parsed = make_url(args.database_url)
    if not parsed.drivername.startswith("sqlite") or not parsed.database:
        raise SystemExit(
            "This initializer is only for a file-backed SQLite pilot. "
            "PostgreSQL must use Alembic migrations."
        )
    database_path = Path(parsed.database)
    if not database_path.is_absolute():
        database_path = (Path.cwd() / database_path).resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_twin_engine(args.database_url)
    try:
        create_validation_schema(engine)
        additions = add_legacy_observation_columns(engine)
        table_count = len(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    print(f"SQLite pilot database ready: {database_path}")
    print(f"Application tables available: {table_count}")
    print(
        "Legacy observation columns added: "
        + (", ".join(additions) if additions else "none")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
