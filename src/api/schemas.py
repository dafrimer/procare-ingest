from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class _ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class KidOut(_ORMBase):
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    status: Optional[str] = None
    room_id: Optional[str] = None
    profile_photo_url: Optional[str] = None
    allergies: Optional[str] = None
    notes: Optional[str] = None
    synced_at: Optional[datetime] = None


class RoomOut(_ORMBase):
    id: str
    name: Optional[str] = None
    capacity: Optional[int] = None
    age_group: Optional[str] = None
    status: Optional[str] = None
    synced_at: Optional[datetime] = None


class ContactOut(_ORMBase):
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    relationship_type: Optional[str] = None
    synced_at: Optional[datetime] = None


class StaffOut(_ORMBase):
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    room_id: Optional[str] = None
    synced_at: Optional[datetime] = None


class DailyActivityOut(_ORMBase):
    id: int
    procare_id: Optional[str] = None
    kid_id: str
    room_id: Optional[str] = None
    activity_date: Optional[date] = None
    activity_type: Optional[str] = None
    occurred_at: Optional[datetime] = None
    sign_in_time: Optional[datetime] = None
    sign_out_time: Optional[datetime] = None
    meal_type: Optional[str] = None
    meal_amount: Optional[str] = None
    nap_start: Optional[datetime] = None
    nap_end: Optional[datetime] = None
    notes: Optional[str] = None
    photo_url: Optional[str] = None
    synced_at: Optional[datetime] = None


class Page(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Any]