import logging
from datetime import date

from client import ProcareClient
from sync.api_client import ApiClient

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
            dob = date.fromisoformat(str(dob_raw)[:10]).isoformat()
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


def sync_kids(client: ProcareClient, api: ApiClient) -> int:
    logger.info("Syncing kids...")
    rows = []
    for page in client.paginate("/api/web/parent/kids/"):
        rows.extend(_map(r) for r in page if r.get("id"))
    count = api.post_ingest("kids", rows) if rows else 0
    logger.info("Synced %d kids", count)
    return count