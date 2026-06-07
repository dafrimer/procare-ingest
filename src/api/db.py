import logging
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from shared.models import Base

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def _enable_sqlite_pragmas(dbapi_connection, _conn_record):
    cur = dbapi_connection.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA busy_timeout=5000")
    cur.close()


def init_db(sqlite_path: str) -> Engine:
    """Initialize SQLite engine with WAL and create tables. Idempotent."""
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine

    os.makedirs(os.path.dirname(sqlite_path) or ".", exist_ok=True)
    url = f"sqlite+pysqlite:///{sqlite_path}"
    logger.info("Opening SQLite database: %s", sqlite_path)

    _engine = create_engine(
        url,
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_pre_ping=True,
    )
    event.listen(_engine, "connect", _enable_sqlite_pragmas)
    _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(_engine)
    logger.info("SQLite ready (WAL mode, FK on)")
    return _engine


@contextmanager
def get_db() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    db = _SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_session_dependency():
    """FastAPI dependency: yields a Session and ensures close."""
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized.")
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()