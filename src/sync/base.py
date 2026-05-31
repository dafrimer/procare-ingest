import logging
from datetime import datetime
from typing import Optional, Type

from sqlalchemy.orm import Session

from models import SyncState

logger = logging.getLogger(__name__)


def upsert_batch(db: Session, model_class: Type, records: list) -> int:
    count = 0
    for record in records:
        try:
            obj = model_class(**record)
            db.merge(obj)
            count += 1
        except Exception as e:
            logger.error("Error upserting %s record: %s | data: %s", model_class.__name__, e, record)
    db.commit()
    return count


def get_watermark(db: Session, entity: str) -> Optional[datetime]:
    state = db.get(SyncState, entity)
    return state.last_synced_at if state else None


def set_watermark(db: Session, entity: str, dt: datetime, count: int):
    state = db.get(SyncState, entity)
    if state is None:
        state = SyncState(entity=entity)
        db.add(state)
    state.last_synced_at = dt
    state.last_record_count = count
    state.updated_at = datetime.utcnow()
    db.commit()
