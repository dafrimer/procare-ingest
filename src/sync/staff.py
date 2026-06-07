import logging

import httpx

from client import ProcareClient
from sync.api_client import ApiClient

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


def sync_staff(client: ProcareClient, api: ApiClient) -> int:
    logger.info("Syncing staff...")
    try:
        rows = []
        for page in client.paginate("/api/web/parent/staff/"):
            rows.extend(_map(r) for r in page if r.get("id"))
        count = api.post_ingest("staff", rows) if rows else 0
        logger.info("Synced %d staff", count)
        return count
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (403, 404):
            logger.warning("Staff endpoint not available (%d), skipping", e.response.status_code)
            return 0
        raise