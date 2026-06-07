from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.db import get_session_dependency
from api.schemas import KidOut, Page
from shared.models import Kid

router = APIRouter(prefix="/kids", tags=["kids"])


@router.get("", response_model=Page)
def list_kids(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    room_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_session_dependency),
):
    stmt = select(Kid)
    count_stmt = select(func.count(Kid.id))
    if room_id:
        stmt = stmt.where(Kid.room_id == room_id)
        count_stmt = count_stmt.where(Kid.room_id == room_id)
    if status:
        stmt = stmt.where(Kid.status == status)
        count_stmt = count_stmt.where(Kid.status == status)
    total = db.execute(count_stmt).scalar() or 0
    rows = db.execute(stmt.order_by(Kid.last_name, Kid.first_name).limit(limit).offset(offset)).scalars().all()
    return {"total": total, "limit": limit, "offset": offset, "items": [KidOut.model_validate(r) for r in rows]}


@router.get("/{kid_id}", response_model=KidOut)
def get_kid(kid_id: str, db: Session = Depends(get_session_dependency)):
    kid = db.get(Kid, kid_id)
    if not kid:
        raise HTTPException(404, "kid not found")
    return KidOut.model_validate(kid)