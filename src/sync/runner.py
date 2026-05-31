import logging
from datetime import datetime

from sqlalchemy.orm import Session

from client import ProcareClient
from config import Config
from sync.contacts import sync_contacts
from sync.daily_activities import sync_daily_activities
from sync.kids import sync_kids
from sync.rooms import sync_rooms
from sync.staff import sync_staff

logger = logging.getLogger(__name__)


def run_full_sync(db: Session, client: ProcareClient, config: Config) -> dict:
    start = datetime.utcnow()
    logger.info("=== Starting full sync at %s ===", start.isoformat())

    counts = {}

    logger.info("--- Syncing rooms ---")
    counts["rooms"] = sync_rooms(db, client)

    logger.info("--- Syncing kids ---")
    counts["kids"] = sync_kids(db, client)

    logger.info("--- Syncing contacts ---")
    counts["contacts"] = sync_contacts(db, client)

    logger.info("--- Syncing daily activities ---")
    counts["daily_activities"] = sync_daily_activities(db, client, config)

    logger.info("--- Syncing staff ---")
    counts["staff"] = sync_staff(db, client)

    elapsed = (datetime.utcnow() - start).total_seconds()
    logger.info("=== Full sync complete in %.1fs: %s ===", elapsed, counts)
    return counts
