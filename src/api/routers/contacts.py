from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.db import get_session_dependency
from api.schemas import ContactOut, Page
from shared.models import Contact

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=Page)
def list_contacts(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    email: Optional[str] = None,
    db: Session = Depends(get_session_dependency),
):
    stmt = select(Contact)
    count_stmt = select(func.count(Contact.id))
    if email:
        stmt = stmt.where(Contact.email == email)
        count_stmt = count_stmt.where(Contact.email == email)
    total = db.execute(count_stmt).scalar() or 0
    rows = db.execute(stmt.order_by(Contact.last_name).limit(limit).offset(offset)).scalars().all()
    return {"total": total, "limit": limit, "offset": offset, "items": [ContactOut.model_validate(r) for r in rows]}


@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: str, db: Session = Depends(get_session_dependency)):
    c = db.get(Contact, contact_id)
    if not c:
        raise HTTPException(404, "contact not found")
    return ContactOut.model_validate(c)