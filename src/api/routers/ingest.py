import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from api.db import get_session_dependency
from shared.models import Contact, DailyActivity, Kid, Room, Staff

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])

_ENTITY_MAP = {
    "kids": (Kid, "id"),
    "rooms": (Room, "id"),
    "contacts": (Contact, "id"),
    "staff": (Staff, "id"),
    "activities": (DailyActivity, "procare_id"),
}


def require_ingest_token(request: Request, authorization: str | None = Header(default=None)) -> None:
    """Bearer token auth for ingest endpoints. Compares against INGEST_TOKEN env."""
    expected = request.app.state.config.ingest_token
    if not expected:
        raise HTTPException(503, "ingest disabled: INGEST_TOKEN not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(403, "invalid ingest token")


@router.post("/{entity}", dependencies=[Depends(require_ingest_token)])
def ingest(
    entity: str,
    records: list[dict[str, Any]],
    db: Session = Depends(get_session_dependency),
):
    if entity not in _ENTITY_MAP:
        raise HTTPException(400, f"unknown entity: {entity}")
    model_cls, _key = _ENTITY_MAP[entity]

    upserted = 0
    skipped = 0
    for rec in records:
        try:
            obj = model_cls(**rec)
            db.merge(obj)
            upserted += 1
        except Exception as e:
            logger.warning("ingest %s skipped record: %s", entity, e)
            skipped += 1
    db.commit()
    logger.info("ingested entity=%s upserted=%d skipped=%d", entity, upserted, skipped)
    return {"entity": entity, "upserted": upserted, "skipped": skipped}