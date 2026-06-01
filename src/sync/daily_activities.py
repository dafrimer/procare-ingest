import logging
from datetime import datetime, date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from client import ProcareClient
from config import Config
from models import DailyActivity, Kid
from sync.base import set_watermark

logger = logging.getLogger(__name__)

_DT_FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
]


def _parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    for fmt in _DT_FORMATS:
        try:
            return datetime.strptime(s[:len(fmt)], fmt)
        except ValueError:
            continue
    logger.debug("Could not parse datetime: %r", value)
    return None


def _parse_date(value) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date):
        return value
    dt = _parse_dt(value)
    return dt.date() if dt else None


def _map(raw: dict) -> dict:
    def get(*keys):
        for k in keys:
            if k in raw and raw[k] is not None:
                return raw[k]
        return None

    return {
        "procare_id": get("id", "uuid", "activity_id"),
        "kid_id": get("kid_id", "kidId", "child_id"),
        "room_id": get("room_id", "roomId", "classroom_id"),
        "activity_date": _parse_date(get("date", "activity_date", "occurred_date")),
        "activity_type": get("type", "activity_type", "category", "kind"),
        "occurred_at": _parse_dt(get("occurred_at", "timestamp", "created_at", "time")),
        "sign_in_time": _parse_dt(get("sign_in_time", "checkin_time", "check_in")),
        "sign_out_time": _parse_dt(get("sign_out_time", "checkout_time", "check_out")),
        "meal_type": get("meal_type", "mealType", "food_type"),
        "meal_amount": get("meal_amount", "amount", "serving_size"),
        "nap_start": _parse_dt(get("nap_start", "nap_start_time", "sleep_start")),
        "nap_end": _parse_dt(get("nap_end", "nap_end_time", "sleep_end")),
        "notes": get("notes", "description", "comment"),
        "photo_url": get("photo_url", "image_url", "attachment_url"),
        "raw_json": raw,
    }


def sync_daily_activities(db: Session, client: ProcareClient, config: Config) -> int:
    logger.info("Syncing daily activities...")
    date_from = (datetime.utcnow().date() - timedelta(days=config.activity_lookback_days)).isoformat()
    date_to = datetime.utcnow().date().isoformat()

    kids = db.execute(
        select(Kid).where(Kid.status != "inactive")
    ).scalars().all()

    if not kids:
        logger.warning("No active kids found in DB; skipping daily activities sync")
        return 0

    total = 0
    for kid in kids:
        kid_total = _sync_kid_activities(db, client, config, kid.id, date_from, date_to)
        total += kid_total

    set_watermark(db, "daily_activities", datetime.utcnow(), total)
    logger.info("Synced %d daily activity records", total)
    return total


def _sync_kid_activities(
    db: Session,
    client: ProcareClient,
    config: Config,
    kid_id: str,
    date_from: str,
    date_to: str,
) -> int:
    path = "/api/web/parent/daily_activities/"
    params = {
        "kid_id": kid_id,
        "filters[daily_activity][date_from]": date_from,
        "filters[daily_activity][date_to]": date_to,
    }
    count = 0
    try:
        for page in client.paginate(path, extra_params=params):
            for raw in page:
                mapped = _map(raw)
                if not mapped.get("procare_id") or not mapped.get("kid_id"):
                    continue
                existing = db.execute(
                    select(DailyActivity).where(DailyActivity.procare_id == mapped["procare_id"])
                ).scalar_one_or_none()
                if existing is None:
                    db.add(DailyActivity(**mapped))
                else:
                    for k, v in mapped.items():
                        if k != "id":
                            setattr(existing, k, v)
                count += 1
            db.commit()
    except Exception as e:
        logger.error("Error syncing activities for kid %s: %s", kid_id, e)
        db.rollback()
    return count
