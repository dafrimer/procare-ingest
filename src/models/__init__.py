from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Boolean,
    JSON,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Site(Base):
    __tablename__ = "sites"

    id = Column(String(64), primary_key=True)
    name = Column(String(255))
    base_url = Column(String(512))
    web_url = Column(String(512))
    pom_identifier = Column(String(128))
    tenancy = Column(String(128))
    raw_json = Column(JSON)
    synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Room(Base):
    __tablename__ = "rooms"

    id = Column(String(64), primary_key=True)
    name = Column(String(255))
    capacity = Column(Integer)
    age_group = Column(String(128))
    status = Column(String(64))
    raw_json = Column(JSON)
    synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Kid(Base):
    __tablename__ = "kids"

    id = Column(String(64), primary_key=True)
    first_name = Column(String(128))
    last_name = Column(String(128))
    display_name = Column(String(255))
    date_of_birth = Column(Date)
    gender = Column(String(32))
    status = Column(String(64))
    room_id = Column(String(64), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)
    profile_photo_url = Column(Text)
    allergies = Column(Text)
    notes = Column(Text)
    raw_json = Column(JSON)
    synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(String(64), primary_key=True)
    first_name = Column(String(128))
    last_name = Column(String(128))
    email = Column(String(255))
    phone = Column(String(64))
    relationship_type = Column(String(64))
    raw_json = Column(JSON)
    synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KidContact(Base):
    __tablename__ = "kid_contacts"
    __table_args__ = (UniqueConstraint("kid_id", "contact_id", name="uq_kid_contact"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    kid_id = Column(String(64), ForeignKey("kids.id", ondelete="CASCADE"), nullable=False)
    contact_id = Column(String(64), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    is_primary = Column(Boolean, default=False)
    can_pickup = Column(Boolean, default=False)
    relationship_label = Column(String(128))
    raw_json = Column(JSON)
    synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DailyActivity(Base):
    __tablename__ = "daily_activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    procare_id = Column(String(64), unique=True, index=True)
    kid_id = Column(String(64), ForeignKey("kids.id", ondelete="CASCADE"), nullable=False)
    room_id = Column(String(64), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)
    activity_date = Column(Date)
    activity_type = Column(String(128))
    occurred_at = Column(DateTime)
    sign_in_time = Column(DateTime)
    sign_out_time = Column(DateTime)
    meal_type = Column(String(64))
    meal_amount = Column(String(64))
    nap_start = Column(DateTime)
    nap_end = Column(DateTime)
    notes = Column(Text)
    photo_url = Column(Text)
    raw_json = Column(JSON)
    synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Staff(Base):
    __tablename__ = "staff"

    id = Column(String(64), primary_key=True)
    first_name = Column(String(128))
    last_name = Column(String(128))
    email = Column(String(255))
    role = Column(String(64))
    status = Column(String(64))
    room_id = Column(String(64), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)
    raw_json = Column(JSON)
    synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SyncState(Base):
    __tablename__ = "sync_state"

    entity = Column(String(64), primary_key=True)
    last_synced_at = Column(DateTime)
    last_record_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
