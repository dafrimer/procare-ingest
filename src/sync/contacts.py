import logging
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from client import ProcareClient
from models import Contact
from sync.base import upsert_batch, set_watermark

logger = logging.getLogger(__name__)


def _map(raw: dict) -> dict:
    def get(*keys):
        for k in keys:
            if k in raw and raw[k] is not None:
                return raw[k]
        return None

    return {
        "id": get("id", "uuid", "contact_id"),
        "first_name": get("first_name", "firstName"),
        "last_name": get("last_name", "lastName"),
        "email": get("email", "email_address"),
        "phone": get("phone", "phone_number", "mobile"),
        "relationship_type": get("relationship_type", "relationship", "type"),
        "raw_json": raw,
    }


def sync_contacts(db: Session, client: ProcareClient) -> int:
    logger.info("Syncing contacts...")
    try:
        total = 0
        for page in client.paginate("/api/web/parent/contacts/"):
            mapped = [_map(r) for r in page if r.get("id")]
            if mapped:
                total += upsert_batch(db, Contact, mapped)
        set_watermark(db, "contacts", datetime.utcnow(), total)
        logger.info("Synced %d contacts", total)
        return total
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (403, 404):
            logger.warning("Contacts endpoint not available (%d), skipping", e.response.status_code)
            return 0
        raise
