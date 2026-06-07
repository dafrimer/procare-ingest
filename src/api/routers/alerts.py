import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from api.db import get_session_dependency
from api.routers.ingest import require_ingest_token
from shared.models import Alert

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])
ingest_router = APIRouter(prefix="/ingest/alerts", tags=["ingest"])


class AlertIn(BaseModel):
    severity: str = "warning"
    code: str
    entity: Optional[str] = None
    message: str
    details: Optional[dict[str, Any]] = None


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    severity: str
    code: str
    entity: Optional[str] = None
    message: str
    details: Optional[dict[str, Any]] = None
    acknowledged: bool
    acknowledged_at: Optional[datetime] = None


def _cooldown_minutes(request: Request) -> int:
    import os
    return int(os.getenv("ALERT_COOLDOWN_MINUTES", "60"))


def _record_alert(db: Session, payload: AlertIn, cooldown_minutes: int) -> tuple[Alert, bool]:
    """Insert an alert unless an identical (code, entity, unack) alert exists within cooldown.
    Returns (alert, created)."""
    cutoff = datetime.utcnow() - timedelta(minutes=cooldown_minutes)
    existing = db.execute(
        select(Alert).where(
            and_(
                Alert.code == payload.code,
                Alert.entity == payload.entity,
                Alert.acknowledged.is_(False),
                Alert.created_at >= cutoff,
            )
        ).order_by(desc(Alert.created_at)).limit(1)
    ).scalar_one_or_none()
    if existing:
        return existing, False
    a = Alert(
        severity=payload.severity,
        code=payload.code,
        entity=payload.entity,
        message=payload.message,
        details=payload.details,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a, True


@ingest_router.post("", dependencies=[Depends(require_ingest_token)])
def post_alert(
    request: Request,
    payload: AlertIn,
    db: Session = Depends(get_session_dependency),
):
    cooldown = _cooldown_minutes(request)
    alert, created = _record_alert(db, payload, cooldown)
    if created:
        logger.warning("ALERT [%s/%s] %s: %s", alert.severity, alert.code, alert.entity or "-", alert.message)
    else:
        logger.info("ALERT deduped (code=%s entity=%s)", payload.code, payload.entity)
    return {"id": alert.id, "created": created, "deduped": not created}


@router.get("", response_model=list[AlertOut])
def list_alerts(
    severity: Optional[str] = None,
    code: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_session_dependency),
):
    stmt = select(Alert)
    if severity:
        stmt = stmt.where(Alert.severity == severity)
    if code:
        stmt = stmt.where(Alert.code == code)
    if acknowledged is not None:
        stmt = stmt.where(Alert.acknowledged.is_(acknowledged))
    rows = db.execute(stmt.order_by(desc(Alert.created_at)).limit(limit)).scalars().all()
    return [AlertOut.model_validate(r) for r in rows]


@router.post("/{alert_id}/ack")
def ack_alert(alert_id: int, db: Session = Depends(get_session_dependency)):
    a = db.get(Alert, alert_id)
    if not a:
        raise HTTPException(404, "alert not found")
    a.acknowledged = True
    a.acknowledged_at = datetime.utcnow()
    db.commit()
    return {"id": a.id, "acknowledged": True}


@router.get("/summary")
def summary(db: Session = Depends(get_session_dependency)):
    rows = db.execute(
        select(Alert.severity, func.count(Alert.id))
        .where(Alert.acknowledged.is_(False))
        .group_by(Alert.severity)
    ).all()
    return {sev: count for sev, count in rows}