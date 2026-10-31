"""Engine / session wiring."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine_kwargs: dict = {
    "pool_pre_ping": True,
    "future": True,
}
if settings.is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, **engine_kwargs)


if settings.is_sqlite:

    @event.listens_for(Engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record) -> None:  # pragma: no cover
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def ensure_lightweight_migrations() -> None:
    """Add columns that predate Alembic to an existing SQLite database.

    ``create_all`` creates missing tables but never alters existing ones, so a
    scaffold database needs tiny forward-only patches like this one.
    """
    if not settings.is_sqlite:
        return
    with engine.begin() as connection:
        rows = connection.exec_driver_sql("PRAGMA table_info(customers)").fetchall()
        columns = {row[1] for row in rows}
        if columns and "contact_name" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE customers ADD COLUMN contact_name VARCHAR(160)"
            )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
