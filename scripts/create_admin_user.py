"""Create or update the production admin user.

Run on Render with DATABASE_URL set:
    python scripts/create_admin_user.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from security import hash_password  # noqa: E402


ADMIN_NAME = os.getenv("ADMIN_NAME", "Admin")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "dishantdishanth1234@gmail.com").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "dishanthmnaik")


def database_url_from_env() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required.")

    # SQLAlchemy needs an explicit MySQL driver. The project already installs pymysql.
    if database_url.startswith("mysql://"):
        return database_url.replace("mysql://", "mysql+pymysql://", 1)

    # Render-style Postgres URLs commonly use this deprecated scheme spelling.
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)

    return database_url


def ensure_role_column(engine) -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        raise RuntimeError("The users table does not exist. Run the app/database migrations first.")

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "role" in user_columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'"))


def upsert_admin_user() -> None:
    engine = create_engine(database_url_from_env(), pool_pre_ping=True, pool_recycle=3600)
    password_hash = hash_password(ADMIN_PASSWORD)

    try:
        ensure_role_column(engine)
        with engine.begin() as connection:
            existing_user = connection.execute(
                text("SELECT id, role FROM users WHERE email = :email"),
                {"email": ADMIN_EMAIL},
            ).mappings().first()

            if existing_user:
                connection.execute(
                    text(
                        """
                        UPDATE users
                        SET name = :name,
                            password_hash = :password_hash,
                            role = 'admin'
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": existing_user["id"],
                        "name": ADMIN_NAME,
                        "password_hash": password_hash,
                    },
                )
                print(f"Updated existing admin user: {ADMIN_EMAIL}")
                return

            connection.execute(
                text(
                    """
                    INSERT INTO users (name, email, password_hash, role)
                    VALUES (:name, :email, :password_hash, 'admin')
                    """
                ),
                {
                    "name": ADMIN_NAME,
                    "email": ADMIN_EMAIL,
                    "password_hash": password_hash,
                },
            )
            print(f"Created admin user: {ADMIN_EMAIL}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    upsert_admin_user()
