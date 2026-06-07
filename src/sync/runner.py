import logging
from datetime import datetime

from client import ProcareClient
from config import Config
from sync.api_client import ApiClient
from sync.contacts import sync_contacts
from sync.daily_activities import sync_daily_activities
from sync.kids import sync_kids
from sync.rooms import sync_rooms
from sync.staff import sync_staff

logger = logging.getLogger(__name__)


def run_full_sync(client: ProcareClient, api: ApiClient, config: Config) -> dict:
    start = datetime.utcnow()
    logger.info("=== Starting full sync at %s ===", start.isoformat())

    counts = {}
    counts["rooms"] = sync_rooms(client, api)
    counts["kids"] = sync_kids(client, api)
    counts["contacts"] = sync_contacts(client, api)
    counts["daily_activities"] = sync_daily_activities(client, api, config)
    counts["staff"] = sync_staff(client, api)

    elapsed = (datetime.utcnow() - start).total_seconds()
    logger.info("=== Full sync complete in %.1fs: %s ===", elapsed, counts)
    return counts