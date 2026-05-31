import logging
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from client import ProcareClient
from models import Room
from sync.base import upsert_batch, set_watermark

logger = logging.getLogger(__name__)


def _map(raw: dict) -> dict:
    def get(*keys):
        for k in keys:
            if k in raw and raw[k] is not None:
                return raw[k]
        return None

    capacity = get("capacity", "max_capacity")
    try:
        capacity = int(capacity) if capacity is not None else None
    except (TypeError, ValueError):
        capacity = None

    return {
        "id": get("id", "uuid", "room_id"),
        "name": get("name", "room_name", "title"),
        "capacity": capacity,
        "age_group": get("age_group", "ageGroup", "age_range"),
        "status": get("status", "active"),
        "raw_json": raw,
    }


def sync_rooms(db: Session, client: ProcareClient) -> int:
    logger.info("Syncing rooms...")
    try:
        total = 0
        for page in client.paginate("/api/web/parent/rooms/"):
            mapped = [_map(r) for r in page if r.get("id")]
            if mapped:
                total += upsert_batch(db, Room, mapped)
        set_watermark(db, "rooms", datetime.utcnow(), total)
        logger.info("Synced %d rooms", total)
        return total
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (403, 404):
            logger.warning("Rooms endpoint not available (%d), skipping", e.response.status_code)
            return 0
        raise
