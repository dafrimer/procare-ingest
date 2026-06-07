import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import Config
from shared.models import Base

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None


def init_db(config: Config):
    global _engine, _SessionLocal
    logger.info("Connecting to database: %s://%s:%s/%s", config.db_adapter, config.db_host, config.db_port, config.db_name)
    kwargs = {}
    if config.db_adapter == "mysql":
        kwargs["pool_pre_ping"] = True
        kwargs["pool_recycle"] = 3600
    _engine = create_engine(config.db_url, **kwargs)
    _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(_engine)
    logger.info("Database initialized")


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
