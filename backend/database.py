"""SQLAlchemy engine and session factory."""
import os
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import is_sqlite, settings

_BACKEND_DIR = Path(__file__).resolve().parent


def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith("mysql://"):
        return database_url.replace("mysql://", "mysql+pymysql://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+pg8000://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+pg8000://", 1)
    return database_url


def _database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return _normalize_database_url(database_url)

    if is_sqlite():
        path = _BACKEND_DIR / settings.sqlite_path
        return f"sqlite:///{path.as_posix()}"
    user = quote_plus(settings.mysql_user)
    password = quote_plus(settings.mysql_password or "")
    host = settings.mysql_host
    port = settings.mysql_port
    db = quote_plus(settings.mysql_database)
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}?charset=utf8mb4"


_engine_url = _database_url()
_connect_args = {"check_same_thread": False} if _engine_url.startswith("sqlite") else {}

engine = create_engine(
    _engine_url,
    pool_pre_ping=not _engine_url.startswith("sqlite"),
    pool_recycle=3600,
    echo=False,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for ORM models."""
    pass


def get_db():
    """FastAPI dependency: yields a DB session and closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
