"""Database-engine helpers with SQLite schema translation for local validation."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.pool import StaticPool

from .models import Base

LOGICAL_SCHEMAS = ("registry", "core", "analytics", "audit")


def create_twin_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Create an engine; PostgreSQL retains schemas and SQLite flattens them."""

    engine_options = {"echo": echo}
    if database_url.startswith("sqlite") and ":memory:" in database_url:
        engine_options.update(
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    engine = create_engine(database_url, **engine_options)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine.execution_options(
            schema_translate_map={schema: None for schema in LOGICAL_SCHEMAS}
        )
    return engine


def create_validation_schema(engine: Engine) -> None:
    """Create tables only for isolated SQLite validation, never for PostgreSQL."""

    if engine.dialect.name != "sqlite":
        raise ValueError("PostgreSQL schemas must be created through Alembic migrations")
    from digital_twin.workspace import models  # noqa: F401 - register additive v2 tables

    Base.metadata.create_all(engine)
    from digital_twin.workspace.store import Store

    Store(engine).ensure_heads()
