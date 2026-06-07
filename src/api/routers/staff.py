from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.db import get_session_dependency
from api.schemas import Page, StaffOut
from shared.models import Staff

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("", response_model=Page)
def list_staff(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    room_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_session_dependency),
):
    stmt = select(Staff)
    count_stmt = select(func.count(Staff.id))
    if room_id:
        stmt = stmt.where(Staff.room_id == room_id)
        count_stmt = count_stmt.where(Staff.room_id == room_id)
    if status:
        stmt = stmt.where(Staff.status == status)
        count_stmt = count_stmt.where(Staff.status == status)
    total = db.execute(count_stmt).scalar() or 0
    rows = db.execute(stmt.order_by(Staff.last_name).limit(limit).offset(offset)).scalars().all()
    return {"total": total, "limit": limit, "offset": offset, "items": [StaffOut.model_validate(r) for r in rows]}


@router.get("/{staff_id}", response_model=StaffOut)
def get_staff(staff_id: str, db: Session = Depends(get_session_dependency)):
    s = db.get(Staff, staff_id)
    if not s:
        raise HTTPException(404, "staff not found")
    return StaffOut.model_validate(s)