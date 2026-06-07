import logging
import sys
from datetime import datetime

from client import ProcareClient
from config import Config
from sync.api_client import ApiClient
from sync.contacts import sync_contacts
from sync.daily_activities import sync_daily_activities
from sync.error_reporting import AuthFailure, report_errors
from sync.kids import sync_kids
from sync.rooms import sync_rooms
from sync.staff import sync_staff

logger = logging.getLogger(__name__)


def run_full_sync(client: ProcareClient, api: ApiClient, config: Config) -> dict:
    start = datetime.utcnow()
    logger.info("=== Starting full sync at %s ===", start.isoformat())

    counts: dict[str, int] = {}
    steps = [
        ("rooms", lambda: sync_rooms(client, api)),
        ("kids", lambda: sync_kids(client, api)),
        ("contacts", lambda: sync_contacts(client, api)),
        ("daily_activities", lambda: sync_daily_activities(client, api, config)),
        ("staff", lambda: sync_staff(client, api)),
    ]
    try:
        for name, fn in steps:
            with report_errors(api, name):
                counts[name] = fn()
    except AuthFailure as e:
        logger.error("Aborting sync run: %s", e)
        elapsed = (datetime.utcnow() - start).total_seconds()
        logger.error("=== Sync aborted after %.1fs (auth failure): %s ===", elapsed, counts)
        return counts

    elapsed = (datetime.utcnow() - start).total_seconds()
    logger.info("=== Full sync complete in %.1fs: %s ===", elapsed, counts)
    return counts


def run_and_exit(client: ProcareClient, api: ApiClient, config: Config) -> int:
    """RUN_ONCE entrypoint: return process exit code reflecting auth health."""
    start = datetime.utcnow()
    logger.info("=== Starting full sync at %s ===", start.isoformat())

    counts: dict[str, int] = {}
    steps = [
        ("rooms", lambda: sync_rooms(client, api)),
        ("kids", lambda: sync_kids(client, api)),
        ("contacts", lambda: sync_contacts(client, api)),
        ("daily_activities", lambda: sync_daily_activities(client, api, config)),
        ("staff", lambda: sync_staff(client, api)),
    ]
    auth_failed = False
    try:
        for name, fn in steps:
            with report_errors(api, name):
                counts[name] = fn()
    except AuthFailure:
        auth_failed = True

    elapsed = (datetime.utcnow() - start).total_seconds()
    if auth_failed:
        logger.error("=== Sync aborted after %.1fs (auth failure): %s ===", elapsed, counts)
        return 2
    logger.info("=== Full sync complete in %.1fs: %s ===", elapsed, counts)
    return 0