"""Lightweight runtime schema maintenance for local development."""
from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from config import is_sqlite


def _column_names(engine: Engine, table_name: str) -> set[str]:
    inspector = inspect(engine)
    try:
        return {col["name"] for col in inspector.get_columns(table_name)}
    except Exception:
        return set()


def _table_names(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def ensure_runtime_schema(engine: Engine) -> None:
    dialect = "sqlite" if is_sqlite() else "mysql"
    with engine.begin() as conn:
        user_cols = _column_names(engine, "users")
        if "users" in _table_names(engine) and "role" not in user_cols:
            if dialect == "sqlite":
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'"))
            else:
                conn.execute(
                    text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'")
                )

        appt_cols = _column_names(engine, "appointments")
        if "appointments" in _table_names(engine) and "status" not in appt_cols:
            conn.execute(
                text("ALTER TABLE appointments ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'scheduled'")
            )
