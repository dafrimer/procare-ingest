import logging
from datetime import datetime, date

from sqlalchemy.orm import Session

from client import ProcareClient
from models import Kid
from sync.base import upsert_batch, set_watermark

logger = logging.getLogger(__name__)


def _map(raw: dict) -> dict:
    def get(*keys):
        for k in keys:
            if k in raw and raw[k] is not None:
                return raw[k]
        return None

    dob_raw = get("date_of_birth", "dob", "birthday")
    dob = None
    if dob_raw:
        try:
            dob = date.fromisoformat(str(dob_raw)[:10])
        except (ValueError, TypeError):
            pass

    return {
        "id": get("id", "uuid", "kid_id"),
        "first_name": get("first_name", "firstName"),
        "last_name": get("last_name", "lastName"),
        "display_name": get("display_name", "displayName", "name"),
        "date_of_birth": dob,
        "gender": get("gender", "sex"),
        "status": get("status", "enrollment_status"),
        "room_id": get("room_id", "roomId", "classroom_id"),
        "profile_photo_url": get("profile_photo_url", "photo_url", "avatar_url"),
        "allergies": get("allergies", "allergy_info"),
        "notes": get("notes", "special_notes"),
        "raw_json": raw,
    }


def sync_kids(db: Session, client: ProcareClient) -> int:
    logger.info("Syncing kids...")
    total = 0
    for page in client.paginate("/api/web/parent/kids/"):
        mapped = [_map(r) for r in page if r.get("id")]
        if mapped:
            total += upsert_batch(db, Kid, mapped)
    set_watermark(db, "kids", datetime.utcnow(), total)
    logger.info("Synced %d kids", total)
    return total
