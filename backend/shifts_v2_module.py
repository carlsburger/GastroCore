"""
GastroCore Shifts V2 Module
Dienstplan - shifts als einzige Source of Truth

ARCHITEKTUR-GRUNDSÄTZE:
- assigned_staff_ids[] (Array) statt staff_member_id (Single)
- status: DRAFT | PUBLISHED | CANCELLED
- date_local + start_at_utc + end_at_utc für Zeitzone-Handling
- Nur PUBLISHED Schichten sind für Mitarbeiter sichtbar
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta, date
from enum import Enum
import uuid
import pytz
import logging

from core.database import db, client
from core.auth import get_current_user, require_manager, require_admin
from core.audit import create_audit_log, safe_dict_for_audit
from core.exceptions import NotFoundException, ValidationException, ConflictException

logger = logging.getLogger(__name__)

# ============== CONSTANTS ==============
BERLIN_TZ = pytz.timezone("Europe/Berlin")


# ============== ENUMS ==============
class ShiftStatusV2(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"


class ShiftRole(str, Enum):
    SERVICE = "service"
    KITCHEN = "kitchen"
    BAR = "bar"
    CLEANING = "cleaning"
    SCHICHTLEITER = "schichtleiter"
    AUSHILFE = "aushilfe"


# ============== PYDANTIC MODELS ==============

class ShiftV2Create(BaseModel):
    """Create a new shift (V2 schema)"""
    schedule_id: Optional[str] = None  # Optional reference to schedule
    template_id: Optional[str] = None  # Optional reference to template
    date_local: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")  # YYYY-MM-DD (Europe/Berlin)
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")  # HH:MM local
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")  # HH:MM local
    role: ShiftRole = ShiftRole.SERVICE
    station: Optional[str] = None
    event_id: Optional[str] = None
    assigned_staff_ids: List[str] = Field(default_factory=list)
    required_staff_count: int = Field(default=1, ge=1, le=20)
    notes_staff: Optional[str] = None
    notes_internal: Optional[str] = None
    work_area_id: Optional[str] = None


class ShiftV2Update(BaseModel):
    """Update a shift (V2 schema)"""
    date_local: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    role: Optional[ShiftRole] = None
    station: Optional[str] = None
    event_id: Optional[str] = None
    required_staff_count: Optional[int] = Field(None, ge=1, le=20)
    notes_staff: Optional[str] = None
    notes_internal: Optional[str] = None
    work_area_id: Optional[str] = None


class AssignStaffRequest(BaseModel):
    staff_member_id: str


class SwapRequest(BaseModel):
    """Request body for shift swap"""
    from_staff_id: str
    to_staff_id: str
    reason: Optional[str] = None


class GenerateFromTemplatesRequest(BaseModel):
    """Generate shifts from templates for a date range"""
    date_from: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    date_to: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    template_ids: Optional[List[str]] = None  # None = all active templates
    schedule_id: Optional[str] = None
    event_mode: Optional[str] = None  # "normal" or "kultur"


# ============== HELPER FUNCTIONS ==============

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now_utc().isoformat()


def parse_local_datetime(date_str: str, time_str: str) -> datetime:
    """Parse local date and time to timezone-aware datetime"""
    naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    return BERLIN_TZ.localize(naive)


def local_to_utc(dt: datetime) -> datetime:
    """Convert Berlin datetime to UTC"""
    return dt.astimezone(timezone.utc)


def calculate_hours(start_time: str, end_time: str) -> float:
    """Calculate hours between two HH:MM times"""
    start = datetime.strptime(start_time, "%H:%M")
    end = datetime.strptime(end_time, "%H:%M")
    if end <= start:
        end += timedelta(days=1)
    return (end - start).total_seconds() / 3600


def create_shift_entity(data: dict) -> dict:
    """Create a shift entity with all required fields"""
    now = now_iso()
    
    # Parse times to UTC
    date_local = data.get("date_local")
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    
    start_at_utc = None
    end_at_utc = None
    hours = 0
    
    if date_local and start_time and end_time:
        start_local = parse_local_datetime(date_local, start_time)
        end_local = parse_local_datetime(date_local, end_time)
        
        # Handle overnight shifts
        if end_local <= start_local:
            end_local += timedelta(days=1)
        
        start_at_utc = local_to_utc(start_local).isoformat()
        end_at_utc = local_to_utc(end_local).isoformat()
        hours = calculate_hours(start_time, end_time)
    
    return {
        "id": str(uuid.uuid4()),
        # V2 Fields
        "date_local": date_local,
        "start_at_utc": start_at_utc,
        "end_at_utc": end_at_utc,
        "assigned_staff_ids": data.get("assigned_staff_ids", []),
        "required_staff_count": data.get("required_staff_count", 1),
        "status": ShiftStatusV2.DRAFT.value,
        "notes_staff": data.get("notes_staff"),
        "notes_internal": data.get("notes_internal"),
        # Common fields
        "schedule_id": data.get("schedule_id"),
        "template_id": data.get("template_id"),
        "role": data.get("role", ShiftRole.SERVICE.value),
        "station": data.get("station"),
        "event_id": data.get("event_id"),
        "work_area_id": data.get("work_area_id"),
        # Legacy compatibility
        "start_time": start_time,
        "end_time": end_time,
        "shift_date": date_local,  # Legacy field
        "hours": hours,
        # Metadata
        "created_at": now,
        "updated_at": now,
        "archived": False
    }


# ============== ROUTER ==============
shifts_v2_router = APIRouter(prefix="/api/staff/shifts/v2", tags=["Shifts V2"])


# ============== CRUD ENDPOINTS ==============

@shifts_v2_router.get("")
async def list_shifts_v2(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    schedule_id: Optional[str] = None,
    status: Optional[ShiftStatusV2] = None,
    staff_member_id: Optional[str] = None,
    role: Optional[ShiftRole] = None,
    include_cancelled: bool = False,
    user: dict = Depends(require_manager)
):
    """
    List shifts (V2).
    Supports filtering by date range, schedule, status, staff member, and role.
    Supports both date_local (V2) and shift_date (legacy) fields.
    """
    query = {"archived": {"$ne": True}}
    
    # Date filter - support both date_local and shift_date (legacy)
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to
        # Query both date fields for compatibility
        query["$or"] = [
            {"date_local": date_query},
            {"shift_date": date_query}
        ]
    
    if schedule_id:
        query["schedule_id"] = schedule_id
    
    if status:
        query["status"] = status.value
    elif not include_cancelled:
        # Don't filter by status if status field doesn't exist (legacy shifts)
        query["$and"] = query.get("$and", [])
        query["$and"].append({
            "$or": [
                {"status": {"$exists": False}},
                {"status": None},
                {"status": {"$ne": ShiftStatusV2.CANCELLED.value}}
            ]
        })
    
    if staff_member_id:
        staff_query = [
            {"assigned_staff_ids": staff_member_id},
            {"staff_member_id": staff_member_id}  # Legacy support
        ]
        if "$or" in query:
            # Combine with existing $or using $and
            existing_or = query.pop("$or")
            query["$and"] = query.get("$and", [])
            query["$and"].append({"$or": existing_or})
            query["$and"].append({"$or": staff_query})
        else:
            query["$or"] = staff_query
    
    if role:
        query["role"] = role.value
    
    # Sort by date (prefer date_local, fallback to shift_date)
    shifts = await db.shifts.find(query, {"_id": 0}).sort([("date_local", 1), ("shift_date", 1), ("start_at_utc", 1), ("start_time", 1)]).to_list(1000)
    
    # Enrich with staff names
    all_staff_ids = set()
    for shift in shifts:
        all_staff_ids.update(shift.get("assigned_staff_ids", []))
        if shift.get("staff_member_id"):
            all_staff_ids.add(shift["staff_member_id"])
    
    staff_map = {}
    if all_staff_ids:
        staff_members = await db.staff_members.find(
            {"id": {"$in": list(all_staff_ids)}},
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "full_name": 1}
        ).to_list(len(all_staff_ids))
        staff_map = {s["id"]: s for s in staff_members}
    
    for shift in shifts:
        # Add staff info
        assigned_staff = []
        for sid in shift.get("assigned_staff_ids", []):
            staff = staff_map.get(sid, {})
            name = staff.get("full_name") or f"{staff.get('first_name', '')} {staff.get('last_name', '')}".strip() or sid
            assigned_staff.append({"id": sid, "name": name})
        shift["assigned_staff"] = assigned_staff
        
        # Legacy single staff support
        if shift.get("staff_member_id") and not shift.get("assigned_staff_ids"):
            staff = staff_map.get(shift["staff_member_id"], {})
            name = staff.get("full_name") or f"{staff.get('first_name', '')} {staff.get('last_name', '')}".strip()
            shift["assigned_staff"] = [{"id": shift["staff_member_id"], "name": name}]
    
    return {
        "shifts": shifts,
        "count": len(shifts)
    }


@shifts_v2_router.get("/{shift_id}")
async def get_shift_v2(shift_id: str, user: dict = Depends(require_manager)):
    """Get a single shift with full details"""
    shift = await db.shifts.find_one({"id": shift_id, "archived": {"$ne": True}}, {"_id": 0})
    if not shift:
        raise NotFoundException("Schicht")
    
    # Enrich with staff info
    all_staff_ids = list(set(shift.get("assigned_staff_ids", [])))
    if shift.get("staff_member_id"):
        all_staff_ids.append(shift["staff_member_id"])
    
    if all_staff_ids:
        staff_members = await db.staff_members.find(
            {"id": {"$in": all_staff_ids}},
            {"_id": 0}
        ).to_list(len(all_staff_ids))
        staff_map = {s["id"]: s for s in staff_members}
        
        assigned_staff = []
        for sid in shift.get("assigned_staff_ids", []):
            staff = staff_map.get(sid, {})
            assigned_staff.append({
                "id": sid,
                "name": staff.get("full_name") or f"{staff.get('first_name', '')} {staff.get('last_name', '')}".strip(),
                "role": staff.get("role"),
                "email": staff.get("email")
            })
        shift["assigned_staff"] = assigned_staff
    
    return shift


@shifts_v2_router.post("")
async def create_shift_v2(data: ShiftV2Create, user: dict = Depends(require_manager)):
    """Create a new shift (V2 schema)"""
    
    # Validate staff members exist
    if data.assigned_staff_ids:
        existing = await db.staff_members.count_documents({
            "id": {"$in": data.assigned_staff_ids},
            "archived": {"$ne": True}
        })
        if existing != len(data.assigned_staff_ids):
            raise ValidationException("Ein oder mehrere Mitarbeiter existieren nicht")
    
    # Validate schedule exists if provided
    if data.schedule_id:
        schedule = await db.schedules.find_one({"id": data.schedule_id, "archived": {"$ne": True}})
        if not schedule:
            raise NotFoundException("Dienstplan")
    
    # Create shift
    shift = create_shift_entity(data.model_dump())
    await db.shifts.insert_one(shift)
    
    # Audit log
    await create_audit_log(
        user, "shift", shift["id"], "create",
        None,
        safe_dict_for_audit(shift)
    )
    
    return {k: v for k, v in shift.items() if k != "_id"}


@shifts_v2_router.patch("/{shift_id}")
async def update_shift_v2(shift_id: str, data: ShiftV2Update, user: dict = Depends(require_manager)):
    """Update a shift"""
    shift = await db.shifts.find_one({"id": shift_id, "archived": {"$ne": True}}, {"_id": 0})
    if not shift:
        raise NotFoundException("Schicht")
    
    before = safe_dict_for_audit(shift)
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    if not update_data:
        return shift
    
    # Recalculate times if changed
    date_local = update_data.get("date_local", shift.get("date_local"))
    start_time = update_data.get("start_time", shift.get("start_time"))
    end_time = update_data.get("end_time", shift.get("end_time"))
    
    if any(k in update_data for k in ["date_local", "start_time", "end_time"]):
        if date_local and start_time and end_time:
            start_local = parse_local_datetime(date_local, start_time)
            end_local = parse_local_datetime(date_local, end_time)
            
            if end_local <= start_local:
                end_local += timedelta(days=1)
            
            update_data["start_at_utc"] = local_to_utc(start_local).isoformat()
            update_data["end_at_utc"] = local_to_utc(end_local).isoformat()
            update_data["hours"] = calculate_hours(start_time, end_time)
            update_data["shift_date"] = date_local  # Legacy
    
    update_data["updated_at"] = now_iso()
    
    await db.shifts.update_one({"id": shift_id}, {"$set": update_data})
    
    updated = await db.shifts.find_one({"id": shift_id}, {"_id": 0})
    
    await create_audit_log(
        user, "shift", shift_id, "update",
        before,
        safe_dict_for_audit(updated)
    )
    
    return updated


@shifts_v2_router.delete("/{shift_id}")
async def delete_shift_v2(shift_id: str, user: dict = Depends(require_manager)):
    """Archive a shift (soft delete)"""
    shift = await db.shifts.find_one({"id": shift_id, "archived": {"$ne": True}}, {"_id": 0})
    if not shift:
        raise NotFoundException("Schicht")
    
    await db.shifts.update_one(
        {"id": shift_id},
        {"$set": {"archived": True, "updated_at": now_iso()}}
    )
    
    await create_audit_log(
        user, "shift", shift_id, "archive",
        safe_dict_for_audit(shift),
        {"archived": True}
    )
    
    return {"success": True, "message": "Schicht gelöscht"}


# ============== STATUS TRANSITIONS ==============

@shifts_v2_router.post("/{shift_id}/publish")
async def publish_shift(shift_id: str, user: dict = Depends(require_manager)):
    """
    Publish a shift (DRAFT → PUBLISHED).
    Makes the shift visible to assigned staff members.
    """
    shift = await db.shifts.find_one({"id": shift_id, "archived": {"$ne": True}}, {"_id": 0})
    if not shift:
        raise NotFoundException("Schicht")
    
    current_status = shift.get("status", "DRAFT")
    
    if current_status == ShiftStatusV2.PUBLISHED.value:
        return {"success": True, "message": "Schicht ist bereits veröffentlicht", "status": current_status}
    
    if current_status == ShiftStatusV2.CANCELLED.value:
        raise ValidationException("Abgesagte Schichten können nicht veröffentlicht werden")
    
    before = {"status": current_status}
    
    await db.shifts.update_one(
        {"id": shift_id},
        {"$set": {
            "status": ShiftStatusV2.PUBLISHED.value,
            "published_at": now_iso(),
            "published_by": user.get("email"),
            "updated_at": now_iso()
        }}
    )
    
    await create_audit_log(
        user, "shift", shift_id, "publish",
        before,
        {"status": ShiftStatusV2.PUBLISHED.value}
    )
    
    return {
        "success": True,
        "message": "Schicht veröffentlicht",
        "status": ShiftStatusV2.PUBLISHED.value
    }


@shifts_v2_router.post("/{shift_id}/cancel")
async def cancel_shift(shift_id: str, reason: Optional[str] = None, user: dict = Depends(require_manager)):
    """
    Cancel a shift (any status → CANCELLED).
    """
    shift = await db.shifts.find_one({"id": shift_id, "archived": {"$ne": True}}, {"_id": 0})
    if not shift:
        raise NotFoundException("Schicht")
    
    current_status = shift.get("status", "DRAFT")
    
    if current_status == ShiftStatusV2.CANCELLED.value:
        return {"success": True, "message": "Schicht ist bereits abgesagt", "status": current_status}
    
    before = {"status": current_status}
    
    await db.shifts.update_one(
        {"id": shift_id},
        {"$set": {
            "status": ShiftStatusV2.CANCELLED.value,
            "cancelled_at": now_iso(),
            "cancelled_by": user.get("email"),
            "cancellation_reason": reason,
            "updated_at": now_iso()
        }}
    )
    
    await create_audit_log(
        user, "shift", shift_id, "cancel",
        before,
        {"status": ShiftStatusV2.CANCELLED.value, "reason": reason}
    )
    
    return {
        "success": True,
        "message": "Schicht abgesagt",
        "status": ShiftStatusV2.CANCELLED.value
    }


# ============== STAFF ASSIGNMENT ==============

@shifts_v2_router.post("/{shift_id}/assign")
async def assign_staff_to_shift(shift_id: str, data: AssignStaffRequest, user: dict = Depends(require_manager)):
    """
    Assign a staff member to a shift.
    Adds to assigned_staff_ids array if not already present.
    """
    shift = await db.shifts.find_one({"id": shift_id, "archived": {"$ne": True}}, {"_id": 0})
    if not shift:
        raise NotFoundException("Schicht")
    
    # Validate staff exists
    staff = await db.staff_members.find_one({"id": data.staff_member_id, "archived": {"$ne": True}})
    if not staff:
        raise NotFoundException("Mitarbeiter")
    
    assigned = shift.get("assigned_staff_ids", [])
    
    if data.staff_member_id in assigned:
        return {
            "success": True,
            "message": "Mitarbeiter ist bereits zugewiesen",
            "assigned_staff_ids": assigned
        }
    
    assigned.append(data.staff_member_id)
    
    await db.shifts.update_one(
        {"id": shift_id},
        {"$set": {
            "assigned_staff_ids": assigned,
            "updated_at": now_iso()
        }}
    )
    
    staff_name = staff.get("full_name") or f"{staff.get('first_name', '')} {staff.get('last_name', '')}".strip()
    
    await create_audit_log(
        user, "shift", shift_id, "assign_staff",
        {"assigned_staff_ids": shift.get("assigned_staff_ids", [])},
        {"assigned_staff_ids": assigned, "added": data.staff_member_id, "name": staff_name}
    )
    
    return {
        "success": True,
        "message": f"{staff_name} zugewiesen",
        "assigned_staff_ids": assigned
    }


@shifts_v2_router.post("/{shift_id}/unassign")
async def unassign_staff_from_shift(shift_id: str, data: AssignStaffRequest, user: dict = Depends(require_manager)):
    """
    Remove a staff member from a shift.
    Removes from assigned_staff_ids array.
    """
    shift = await db.shifts.find_one({"id": shift_id, "archived": {"$ne": True}}, {"_id": 0})
    if not shift:
        raise NotFoundException("Schicht")
    
    assigned = shift.get("assigned_staff_ids", [])
    
    if data.staff_member_id not in assigned:
        return {
            "success": True,
            "message": "Mitarbeiter war nicht zugewiesen",
            "assigned_staff_ids": assigned
        }
    
    assigned.remove(data.staff_member_id)
    
    await db.shifts.update_one(
        {"id": shift_id},
        {"$set": {
            "assigned_staff_ids": assigned,
            "updated_at": now_iso()
        }}
    )
    
    # Get staff name for audit
    staff = await db.staff_members.find_one({"id": data.staff_member_id}, {"_id": 0})
    staff_name = "Unbekannt"
    if staff:
        staff_name = staff.get("full_name") or f"{staff.get('first_name', '')} {staff.get('last_name', '')}".strip()
    
    await create_audit_log(
        user, "shift", shift_id, "unassign_staff",
        {"assigned_staff_ids": shift.get("assigned_staff_ids", [])},
        {"assigned_staff_ids": assigned, "removed": data.staff_member_id, "name": staff_name}
    )
    
    return {
        "success": True,
        "message": f"{staff_name} entfernt",
        "assigned_staff_ids": assigned
    }


# ============== SHIFT SWAP (ATOMIC) ==============

@shifts_v2_router.post("/{shift_id}/swap")
async def swap_shift_assignment(shift_id: str, data: SwapRequest, user: dict = Depends(require_manager)):
    """
    Atomic shift swap between two staff members.
    
    Rules:
    - Shift must be PUBLISHED
    - from_staff_id must be currently assigned
    - Uses MongoDB transaction for atomicity
    - Creates audit trail
    """
    shift = await db.shifts.find_one({"id": shift_id, "archived": {"$ne": True}}, {"_id": 0})
    if not shift:
        raise NotFoundException("Schicht")
    
    # Check status
    if shift.get("status") != ShiftStatusV2.PUBLISHED.value:
        raise HTTPException(
            status_code=400,
            detail="Schichttausch ist nur für veröffentlichte Schichten möglich"
        )
    
    assigned = shift.get("assigned_staff_ids", [])
    
    # Check from_staff is assigned
    if data.from_staff_id not in assigned:
        raise HTTPException(
            status_code=400,
            detail="Der abgebende Mitarbeiter ist dieser Schicht nicht zugewiesen"
        )
    
    # Validate to_staff exists
    to_staff = await db.staff_members.find_one({"id": data.to_staff_id, "archived": {"$ne": True}})
    if not to_staff:
        raise NotFoundException("Ziel-Mitarbeiter")
    
    # Check if to_staff is already assigned
    if data.to_staff_id in assigned:
        raise HTTPException(
            status_code=400,
            detail="Der Ziel-Mitarbeiter ist bereits dieser Schicht zugewiesen"
        )
    
    # Get from_staff name
    from_staff = await db.staff_members.find_one({"id": data.from_staff_id}, {"_id": 0})
    from_name = from_staff.get("full_name") if from_staff else "Unbekannt"
    to_name = to_staff.get("full_name") or f"{to_staff.get('first_name', '')} {to_staff.get('last_name', '')}".strip()
    
    # Perform swap atomically
    # Note: For full transaction support, MongoDB must be in replica set mode
    # Here we use update operations that are atomic at document level
    
    new_assigned = [sid for sid in assigned if sid != data.from_staff_id]
    new_assigned.append(data.to_staff_id)
    
    # Use findOneAndUpdate for atomic operation
    result = await db.shifts.find_one_and_update(
        {
            "id": shift_id,
            "assigned_staff_ids": data.from_staff_id,  # Guard: must still be assigned
            "status": ShiftStatusV2.PUBLISHED.value  # Guard: must still be published
        },
        {
            "$set": {
                "assigned_staff_ids": new_assigned,
                "updated_at": now_iso()
            }
        },
        return_document=True
    )
    
    if not result:
        raise HTTPException(
            status_code=409,
            detail="Schicht wurde zwischenzeitlich geändert. Bitte erneut versuchen."
        )
    
    # Create swap audit log
    await create_audit_log(
        user, "shift", shift_id, "swap",
        {
            "assigned_staff_ids": assigned,
            "from_staff_id": data.from_staff_id,
            "from_staff_name": from_name
        },
        {
            "assigned_staff_ids": new_assigned,
            "to_staff_id": data.to_staff_id,
            "to_staff_name": to_name,
            "reason": data.reason
        }
    )
    
    return {
        "success": True,
        "message": f"Schichttausch: {from_name} → {to_name}",
        "assigned_staff_ids": new_assigned,
        "swap": {
            "from": {"id": data.from_staff_id, "name": from_name},
            "to": {"id": data.to_staff_id, "name": to_name}
        }
    }


# ============== BULK PUBLISH ==============

@shifts_v2_router.post("/bulk/publish")
async def bulk_publish_shifts(
    shift_ids: List[str],
    user: dict = Depends(require_manager)
):
    """Publish multiple shifts at once"""
    result = await db.shifts.update_many(
        {
            "id": {"$in": shift_ids},
            "status": ShiftStatusV2.DRAFT.value,
            "archived": {"$ne": True}
        },
        {
            "$set": {
                "status": ShiftStatusV2.PUBLISHED.value,
                "published_at": now_iso(),
                "published_by": user.get("email"),
                "updated_at": now_iso()
            }
        }
    )
    
    await create_audit_log(
        user, "shift", "bulk", "bulk_publish",
        {"shift_ids": shift_ids},
        {"published_count": result.modified_count}
    )
    
    return {
        "success": True,
        "published_count": result.modified_count,
        "total_requested": len(shift_ids)
    }


# ============== GENERATE FROM TEMPLATES ==============

@shifts_v2_router.post("/generate-from-templates")
async def generate_shifts_from_templates(
    data: GenerateFromTemplatesRequest,
    user: dict = Depends(require_manager)
):
    """
    Generate shifts from templates for a date range.
    Does NOT assign staff - only creates the shift slots.
    """
    # Parse dates
    try:
        start_date = datetime.strptime(data.date_from, "%Y-%m-%d").date()
        end_date = datetime.strptime(data.date_to, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationException("Ungültiges Datumsformat")
    
    if end_date < start_date:
        raise ValidationException("Enddatum muss nach Startdatum liegen")
    
    if (end_date - start_date).days > 31:
        raise ValidationException("Maximaler Zeitraum: 31 Tage")
    
    # Get templates
    template_query = {"archived": {"$ne": True}, "active": True}
    if data.template_ids:
        template_query["id"] = {"$in": data.template_ids}
    if data.event_mode:
        template_query["event_mode"] = data.event_mode
    
    templates = await db.shift_templates.find(template_query, {"_id": 0}).to_list(100)
    
    if not templates:
        return {
            "success": False,
            "message": "Keine aktiven Vorlagen gefunden",
            "created_count": 0
        }
    
    # Generate shifts for each day
    created_shifts = []
    skipped_count = 0
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.isoformat()
        
        for template in templates:
            # Check if shift already exists
            existing = await db.shifts.find_one({
                "date_local": date_str,
                "template_id": template["id"],
                "archived": {"$ne": True}
            })
            
            if existing:
                skipped_count += 1
                continue
            
            # Determine start and end times
            start_time = template.get("start_time") or template.get("start_time_local", "09:00")
            end_time = template.get("end_time_fixed") or template.get("end_time_local", "17:00")
            
            # Handle close_plus_minutes - would need opening hours
            # For now, use fixed end time if close_plus_minutes
            if template.get("end_time_type") == "close_plus_minutes":
                # Default to 22:00 + offset
                close_plus = template.get("close_plus_minutes", 0)
                base_close = datetime.strptime("22:00", "%H:%M")
                end_dt = base_close + timedelta(minutes=close_plus)
                end_time = end_dt.strftime("%H:%M")
            
            # Map department to role
            role = template.get("role") or template.get("department", "service")
            
            shift_data = {
                "schedule_id": data.schedule_id,
                "template_id": template["id"],
                "date_local": date_str,
                "start_time": start_time,
                "end_time": end_time,
                "role": role,
                "station": template.get("station"),
                "required_staff_count": template.get("headcount_default", 1),
                "notes_internal": f"Aus Vorlage: {template.get('name')}"
            }
            
            shift = create_shift_entity(shift_data)
            await db.shifts.insert_one(shift)
            created_shifts.append({
                "id": shift["id"],
                "date": date_str,
                "template_name": template.get("name"),
                "start_time": start_time,
                "end_time": end_time
            })
        
        current_date += timedelta(days=1)
    
    await create_audit_log(
        user, "shift", "generate", "generate_from_templates",
        {"date_from": data.date_from, "date_to": data.date_to},
        {"created_count": len(created_shifts), "skipped_count": skipped_count}
    )
    
    return {
        "success": True,
        "message": f"{len(created_shifts)} Schichten erstellt, {skipped_count} übersprungen",
        "created_count": len(created_shifts),
        "skipped_count": skipped_count,
        "shifts": created_shifts
    }


# ============== MIGRATION ENDPOINT ==============

@shifts_v2_router.post("/migrate-legacy")
async def migrate_legacy_shifts(user: dict = Depends(require_admin)):
    """
    Migrate legacy shifts (staff_member_id) to V2 format (assigned_staff_ids).
    
    Migration rules:
    1. If staff_member_id set and assigned_staff_ids empty:
       → assigned_staff_ids = [staff_member_id]
    2. Set status = DRAFT (or PUBLISHED if schedule is published)
    3. Set date_local from shift_date
    4. Calculate start_at_utc and end_at_utc from local times
    """
    # Find shifts that need migration
    legacy_query = {
        "staff_member_id": {"$exists": True, "$ne": None},
        "$or": [
            {"assigned_staff_ids": {"$exists": False}},
            {"assigned_staff_ids": {"$size": 0}},
            {"assigned_staff_ids": None}
        ],
        "archived": {"$ne": True}
    }
    
    legacy_shifts = await db.shifts.find(legacy_query, {"_id": 0}).to_list(10000)
    
    migrated_count = 0
    errors = []
    
    for shift in legacy_shifts:
        try:
            update_data = {
                "updated_at": now_iso()
            }
            
            # 1. Migrate staff assignment
            staff_id = shift.get("staff_member_id")
            if staff_id:
                update_data["assigned_staff_ids"] = [staff_id]
            
            # 2. Set status (check if schedule is published)
            if not shift.get("status"):
                schedule_id = shift.get("schedule_id")
                if schedule_id:
                    schedule = await db.schedules.find_one({"id": schedule_id})
                    if schedule and schedule.get("status") == "veroeffentlicht":
                        update_data["status"] = ShiftStatusV2.PUBLISHED.value
                    else:
                        update_data["status"] = ShiftStatusV2.DRAFT.value
                else:
                    update_data["status"] = ShiftStatusV2.DRAFT.value
            
            # 3. Set date_local
            date_local = shift.get("date_local") or shift.get("shift_date") or shift.get("date")
            if date_local:
                update_data["date_local"] = date_local
            
            # 4. Calculate UTC times
            start_time = shift.get("start_time")
            end_time = shift.get("end_time")
            
            if date_local and start_time and end_time and not shift.get("start_at_utc"):
                try:
                    start_local = parse_local_datetime(date_local, start_time)
                    end_local = parse_local_datetime(date_local, end_time)
                    
                    if end_local <= start_local:
                        end_local += timedelta(days=1)
                    
                    update_data["start_at_utc"] = local_to_utc(start_local).isoformat()
                    update_data["end_at_utc"] = local_to_utc(end_local).isoformat()
                except Exception as e:
                    logger.warning(f"Could not parse times for shift {shift['id']}: {e}")
            
            # Apply update
            await db.shifts.update_one({"id": shift["id"]}, {"$set": update_data})
            migrated_count += 1
            
        except Exception as e:
            errors.append({"shift_id": shift["id"], "error": str(e)})
    
    # Create migration audit log
    await create_audit_log(
        user, "shift", "migration", "migrate_to_v2",
        {"legacy_count": len(legacy_shifts)},
        {"migrated_count": migrated_count, "error_count": len(errors)}
    )
    
    return {
        "success": True,
        "message": f"Migration abgeschlossen: {migrated_count} Schichten migriert",
        "total_legacy": len(legacy_shifts),
        "migrated_count": migrated_count,
        "error_count": len(errors),
        "errors": errors[:10]  # Only first 10 errors
    }


# ============== MY SHIFTS (EMPLOYEE VIEW) ==============

@shifts_v2_router.get("/my")
async def get_my_shifts_v2(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Get shifts assigned to the current user.
    Only returns PUBLISHED shifts.
    """
    # Find staff member for user
    staff = None
    
    if user.get("staff_member_id"):
        staff = await db.staff_members.find_one({
            "id": user["staff_member_id"],
            "archived": {"$ne": True}
        }, {"_id": 0})
    
    if not staff:
        staff = await db.staff_members.find_one({
            "email": user.get("email"),
            "archived": {"$ne": True}
        }, {"_id": 0})
    
    if not staff:
        return {
            "success": True,
            "data": [],
            "message": "Kein Mitarbeiterprofil verknüpft"
        }
    
    staff_id = staff["id"]
    
    # Build query - only PUBLISHED shifts
    query = {
        "$or": [
            {"assigned_staff_ids": staff_id},
            {"staff_member_id": staff_id}  # Legacy support
        ],
        "status": ShiftStatusV2.PUBLISHED.value,
        "archived": {"$ne": True}
    }
    
    # Date filter
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to
        query["date_local"] = date_query
    
    shifts = await db.shifts.find(query, {"_id": 0}).sort("date_local", 1).to_list(100)
    
    # Enrich with work area names
    work_area_ids = list(set(s.get("work_area_id") for s in shifts if s.get("work_area_id")))
    work_area_map = {}
    if work_area_ids:
        work_areas = await db.work_areas.find({"id": {"$in": work_area_ids}}, {"_id": 0}).to_list(len(work_area_ids))
        work_area_map = {w["id"]: w for w in work_areas}
    
    for shift in shifts:
        # Add work area info
        area = work_area_map.get(shift.get("work_area_id"), {})
        shift["work_area_name"] = area.get("name", shift.get("role", ""))
        shift["work_area_color"] = area.get("color", "#3B82F6")
        
        # Ensure shift_date for legacy frontend
        shift["shift_date"] = shift.get("date_local") or shift.get("shift_date")
        
        # Remove internal notes from employee view
        shift.pop("notes_internal", None)
    
    return {
        "success": True,
        "data": shifts,
        "count": len(shifts)
    }
