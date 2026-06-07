from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.db import get_session_dependency
from api.schemas import DailyActivityOut, Page
from shared.models import DailyActivity

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("", response_model=Page)
def list_activities(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    kid_id: Optional[str] = None,
    room_id: Optional[str] = None,
    activity_type: Optional[str] = None,
    date_from: Optional[date_type] = None,
    date_to: Optional[date_type] = None,
    db: Session = Depends(get_session_dependency),
):
    stmt = select(DailyActivity)
    count_stmt = select(func.count(DailyActivity.id))
    if kid_id:
        stmt = stmt.where(DailyActivity.kid_id == kid_id)
        count_stmt = count_stmt.where(DailyActivity.kid_id == kid_id)
    if room_id:
        stmt = stmt.where(DailyActivity.room_id == room_id)
        count_stmt = count_stmt.where(DailyActivity.room_id == room_id)
    if activity_type:
        stmt = stmt.where(DailyActivity.activity_type == activity_type)
        count_stmt = count_stmt.where(DailyActivity.activity_type == activity_type)
    if date_from:
        stmt = stmt.where(DailyActivity.activity_date >= date_from)
        count_stmt = count_stmt.where(DailyActivity.activity_date >= date_from)
    if date_to:
        stmt = stmt.where(DailyActivity.activity_date <= date_to)
        count_stmt = count_stmt.where(DailyActivity.activity_date <= date_to)
    total = db.execute(count_stmt).scalar() or 0
    rows = db.execute(stmt.order_by(DailyActivity.occurred_at.desc()).limit(limit).offset(offset)).scalars().all()
    return {"total": total, "limit": limit, "offset": offset, "items": [DailyActivityOut.model_validate(r) for r in rows]}


@router.get("/{activity_id}", response_model=DailyActivityOut)
def get_activity(activity_id: int, db: Session = Depends(get_session_dependency)):
    a = db.get(DailyActivity, activity_id)
    if not a:
        raise HTTPException(404, "activity not found")
    return DailyActivityOut.model_validate(a)