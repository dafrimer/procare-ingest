"""Background task that watches sync_state for staleness and emits alerts."""
import asyncio
import logging
import os
from datetime import datetime, timedelta

from sqlalchemy import select

from api.db import get_db
from api.notifier import dispatch
from api.routers.alerts import AlertIn, _cooldown_minutes, _record_alert
from shared.models import SyncState

logger = logging.getLogger(__name__)


def _watched_entities() -> list[str]:
    raw = os.getenv("HEARTBEAT_ENTITIES", "kids,rooms,daily_activities")
    return [e.strip() for e in raw.split(",") if e.strip()]


def _stale_after_minutes() -> int:
    # Default: 2x the typical 15-min sync interval.
    return int(os.getenv("HEARTBEAT_STALE_MINUTES", "30"))


def _check_interval_seconds() -> int:
    return int(os.getenv("HEARTBEAT_CHECK_SECONDS", "300"))


def _check_once(notifiers) -> None:
    stale_threshold = timedelta(minutes=_stale_after_minutes())
    cooldown = _cooldown_minutes()
    now = datetime.utcnow()
    entities = _watched_entities()
    with get_db() as db:
        for entity in entities:
            state = db.execute(select(SyncState).where(SyncState.entity == entity)).scalar_one_or_none()
            if state is None:
                age = None
                stale = True
                reason = f"no sync_state row for '{entity}' (sync may have never run)"
            else:
                age = now - state.last_synced_at if state.last_synced_at else None
                stale = age is None or age > stale_threshold
                if stale:
                    reason = f"last sync was {age} ago (threshold {stale_threshold})"
                else:
                    reason = None
            if stale:
                payload = AlertIn(
                    severity="warning",
                    code="sync_stalled",
                    entity=entity,
                    message=f"sync stalled for entity '{entity}': {reason}",
                    details={"last_synced_at": state.last_synced_at.isoformat() if state and state.last_synced_at else None},
                )
                alert, created = _record_alert(db, payload, cooldown)
                if created and notifiers:
                    dispatch(notifiers, f"[sync_stalled] {entity}", payload.message, "warning")


async def heartbeat_loop(app) -> None:
    interval = _check_interval_seconds()
    logger.info("heartbeat monitor started (every %ds, stale=%dm, entities=%s)",
                interval, _stale_after_minutes(), _watched_entities())
    while True:
        try:
            await asyncio.to_thread(_check_once, app.state.notifiers)
        except Exception as e:
            logger.error("heartbeat check failed: %s", e, exc_info=True)
        await asyncio.sleep(interval)


def start_heartbeat(app) -> asyncio.Task | None:
    if os.getenv("HEARTBEAT_ENABLED", "true").lower() != "true":
        logger.info("heartbeat disabled via HEARTBEAT_ENABLED=false")
        return None
    return asyncio.create_task(heartbeat_loop(app))