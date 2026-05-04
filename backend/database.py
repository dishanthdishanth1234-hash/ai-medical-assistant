"""SQLAlchemy engine and session factory (MySQL or SQLite)."""
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import is_sqlite, settings

_BACKEND_DIR = Path(__file__).resolve().parent


def _database_url() -> str:
    if is_sqlite():
        path = _BACKEND_DIR / settings.sqlite_path
        return f"sqlite:///{path.as_posix()}"
    user = quote_plus(settings.mysql_user)
    password = quote_plus(settings.mysql_password or "")
    host = settings.mysql_host
    port = settings.mysql_port
    db = quote_plus(settings.mysql_database)
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}?charset=utf8mb4"


_connect_args = {"check_same_thread": False} if is_sqlite() else {}

engine = create_engine(
    _database_url(),
    pool_pre_ping=not is_sqlite(),
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
