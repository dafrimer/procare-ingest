import logging
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from client import ProcareClient
from shared.models import Staff
from sync.base import upsert_batch, set_watermark

logger = logging.getLogger(__name__)


def _map(raw: dict) -> dict:
    def get(*keys):
        for k in keys:
            if k in raw and raw[k] is not None:
                return raw[k]
        return None

    return {
        "id": get("id", "uuid", "staff_id", "employee_id"),
        "first_name": get("first_name", "firstName"),
        "last_name": get("last_name", "lastName"),
        "email": get("email", "email_address"),
        "role": get("role", "position", "job_title"),
        "status": get("status", "employment_status"),
        "room_id": get("room_id", "roomId", "classroom_id"),
        "raw_json": raw,
    }


def sync_staff(db: Session, client: ProcareClient) -> int:
    logger.info("Syncing staff...")
    try:
        total = 0
        for page in client.paginate("/api/web/parent/staff/"):
            mapped = [_map(r) for r in page if r.get("id")]
            if mapped:
                total += upsert_batch(db, Staff, mapped)
        set_watermark(db, "staff", datetime.utcnow(), total)
        logger.info("Synced %d staff", total)
        return total
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (403, 404):
            logger.warning("Staff endpoint not available (%d), skipping", e.response.status_code)
            return 0
        raise
