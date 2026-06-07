"""MCP server exposing read-only tools over Streamable HTTP at /mcp."""
import json
import logging
from datetime import date as date_type
from typing import Optional

from sqlalchemy import func, select

from api.db import get_db
from shared.models import Contact, DailyActivity, Kid, Room, Staff

logger = logging.getLogger(__name__)


def _serialize(obj) -> dict:
    out = {}
    for col in obj.__table__.columns:
        v = getattr(obj, col.name)
        if hasattr(v, "isoformat"):
            v = v.isoformat()
        out[col.name] = v
    return out


def build_mcp_server():
    """Lazily import + construct the FastMCP app so the dep is optional."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(name="procare-api", stateless_http=True)

    @mcp.tool()
    def list_kids(room_id: Optional[str] = None, status: Optional[str] = None, limit: int = 100) -> str:
        """List children. Optional filters: room_id, status. Returns JSON array."""
        with get_db() as db:
            stmt = select(Kid)
            if room_id:
                stmt = stmt.where(Kid.room_id == room_id)
            if status:
                stmt = stmt.where(Kid.status == status)
            rows = db.execute(stmt.limit(limit)).scalars().all()
            return json.dumps([_serialize(r) for r in rows], default=str)

    @mcp.tool()
    def get_kid(kid_id: str) -> str:
        """Return a single kid by ID as JSON, or empty object if not found."""
        with get_db() as db:
            kid = db.get(Kid, kid_id)
            return json.dumps(_serialize(kid) if kid else {}, default=str)

    @mcp.tool()
    def list_rooms(limit: int = 100) -> str:
        """List all rooms."""
        with get_db() as db:
            rows = db.execute(select(Room).limit(limit)).scalars().all()
            return json.dumps([_serialize(r) for r in rows], default=str)

    @mcp.tool()
    def list_staff(room_id: Optional[str] = None, limit: int = 100) -> str:
        """List staff members. Optional room_id filter."""
        with get_db() as db:
            stmt = select(Staff)
            if room_id:
                stmt = stmt.where(Staff.room_id == room_id)
            rows = db.execute(stmt.limit(limit)).scalars().all()
            return json.dumps([_serialize(r) for r in rows], default=str)

    @mcp.tool()
    def list_contacts(limit: int = 100) -> str:
        """List contacts (parents / authorized pickups)."""
        with get_db() as db:
            rows = db.execute(select(Contact).limit(limit)).scalars().all()
            return json.dumps([_serialize(r) for r in rows], default=str)

    @mcp.tool()
    def list_activities(
        kid_id: Optional[str] = None,
        activity_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 200,
    ) -> str:
        """List daily activities. Dates are ISO YYYY-MM-DD strings."""
        with get_db() as db:
            stmt = select(DailyActivity)
            if kid_id:
                stmt = stmt.where(DailyActivity.kid_id == kid_id)
            if activity_type:
                stmt = stmt.where(DailyActivity.activity_type == activity_type)
            if date_from:
                stmt = stmt.where(DailyActivity.activity_date >= date_type.fromisoformat(date_from))
            if date_to:
                stmt = stmt.where(DailyActivity.activity_date <= date_type.fromisoformat(date_to))
            rows = db.execute(stmt.order_by(DailyActivity.occurred_at.desc()).limit(limit)).scalars().all()
            return json.dumps([_serialize(r) for r in rows], default=str)

    @mcp.tool()
    def counts() -> str:
        """Return row counts for each entity. Useful as a health check."""
        with get_db() as db:
            result = {
                "kids": db.execute(select(func.count(Kid.id))).scalar() or 0,
                "rooms": db.execute(select(func.count(Room.id))).scalar() or 0,
                "contacts": db.execute(select(func.count(Contact.id))).scalar() or 0,
                "staff": db.execute(select(func.count(Staff.id))).scalar() or 0,
                "activities": db.execute(select(func.count(DailyActivity.id))).scalar() or 0,
            }
            return json.dumps(result)

    return mcp