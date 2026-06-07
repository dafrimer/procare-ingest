from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.db import get_session_dependency
from api.schemas import Page, RoomOut
from shared.models import Room

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=Page)
def list_rooms(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    db: Session = Depends(get_session_dependency),
):
    stmt = select(Room)
    count_stmt = select(func.count(Room.id))
    if status:
        stmt = stmt.where(Room.status == status)
        count_stmt = count_stmt.where(Room.status == status)
    total = db.execute(count_stmt).scalar() or 0
    rows = db.execute(stmt.order_by(Room.name).limit(limit).offset(offset)).scalars().all()
    return {"total": total, "limit": limit, "offset": offset, "items": [RoomOut.model_validate(r) for r in rows]}


@router.get("/{room_id}", response_model=RoomOut)
def get_room(room_id: str, db: Session = Depends(get_session_dependency)):
    room = db.get(Room, room_id)
    if not room:
        raise HTTPException(404, "room not found")
    return RoomOut.model_validate(room)