import logging
from datetime import datetime, date, timedelta
from typing import Optional

from client import ProcareClient
from config import Config
from sync.api_client import ApiClient

logger = logging.getLogger(__name__)

_DT_FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
]


def _parse_dt(value) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    s = str(value).strip()
    for fmt in _DT_FORMATS:
        try:
            return datetime.strptime(s[:len(fmt)], fmt).isoformat()
        except ValueError:
            continue
    return None


def _parse_date(value) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, date):
        return value.isoformat()
    dt = _parse_dt(value)
    return dt[:10] if dt else None


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


def sync_daily_activities(client: ProcareClient, api: ApiClient, config: Config) -> int:
    logger.info("Syncing daily activities...")
    date_from = (datetime.utcnow().date() - timedelta(days=config.activity_lookback_days)).isoformat()
    date_to = datetime.utcnow().date().isoformat()

    kid_ids = api.list_active_kid_ids()
    if not kid_ids:
        logger.warning("No active kids known to procare-api; skipping daily activities sync")
        return 0

    total = 0
    for kid_id in kid_ids:
        total += _sync_kid_activities(client, api, kid_id, date_from, date_to)
    logger.info("Synced %d daily activity records", total)
    return total


def _sync_kid_activities(client: ProcareClient, api: ApiClient, kid_id: str, date_from: str, date_to: str) -> int:
    path = "/api/web/parent/daily_activities/"
    params = {
        "kid_id": kid_id,
        "filters[daily_activity][date_from]": date_from,
        "filters[daily_activity][date_to]": date_to,
    }
    rows: list[dict] = []
    try:
        for page in client.paginate(path, extra_params=params):
            for raw in page:
                m = _map(raw)
                if m.get("procare_id") and m.get("kid_id"):
                    rows.append(m)
    except Exception as e:
        logger.error("Error fetching activities for kid %s: %s", kid_id, e)
        return 0
    return api.post_ingest("activities", rows) if rows else 0