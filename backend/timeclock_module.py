"""
GastroCore Timeclock Module - V1
Zeiterfassung mit strenger State-Machine

ARCHITEKTUR-GRUNDSÄTZE:
- shifts sind die einzige Source of Truth für Dienstplan
- Max 1 time_session pro Mitarbeiter & Tag (Europe/Berlin)
- Clock-out während BREAK ist BLOCKIERT
- Alle Events sind append-only mit Idempotency

State-Machine:
OFF → WORKING ↔ BREAK → CLOSED
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta, date
from enum import Enum
import uuid
import pytz
import logging
import hashlib

from core.database import db, client
from core.auth import get_current_user, require_manager, require_admin
from core.audit import create_audit_log, safe_dict_for_audit
from core.exceptions import NotFoundException, ValidationException, ConflictException

logger = logging.getLogger(__name__)

# ============== CONSTANTS ==============
BERLIN_TZ = pytz.timezone("Europe/Berlin")
SHIFT_LINK_WINDOW_BEFORE_MINUTES = 60  # Clock-in bis 60 min vor Schichtbeginn
SHIFT_LINK_WINDOW_AFTER_MINUTES = 120  # Clock-in bis 120 min nach Schichtende


# ============== ENUMS ==============
class TimeSessionState(str, Enum):
    WORKING = "WORKING"
    BREAK = "BREAK"
    CLOSED = "CLOSED"


class TimeEventType(str, Enum):
    CLOCK_IN = "CLOCK_IN"
    BREAK_START = "BREAK_START"
    BREAK_END = "BREAK_END"
    CLOCK_OUT = "CLOCK_OUT"


class LinkMethod(str, Enum):
    AUTO = "AUTO"
    MANUAL = "MANUAL"
    NONE = "NONE"


class EventSource(str, Enum):
    APP = "APP"
    TERMINAL = "TERMINAL"
    ADMIN_CORRECTION = "ADMIN_CORRECTION"


class ShiftStatusV2(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"


# ============== PYDANTIC MODELS ==============
class BreakRecord(BaseModel):
    start_at: str  # ISO UTC
    end_at: Optional[str] = None  # ISO UTC, null wenn aktiv
    duration_seconds: int = 0


class TimeSessionResponse(BaseModel):
    id: str
    staff_member_id: str
    staff_name: Optional[str] = None
    day_key: str
    state: TimeSessionState
    shift_id: Optional[str] = None
    shift_info: Optional[Dict[str, Any]] = None
    link_method: LinkMethod
    clock_in_at: str
    clock_out_at: Optional[str] = None
    total_work_seconds: int = 0
    total_break_seconds: int = 0
    net_work_seconds: int = 0
    breaks: List[BreakRecord] = []
    created_at: str
    updated_at: str


class ClockInRequest(BaseModel):
    idempotency_key: Optional[str] = None
    source: EventSource = EventSource.APP
    notes: Optional[str] = None


class ClockOutRequest(BaseModel):
    idempotency_key: Optional[str] = None
    source: EventSource = EventSource.APP
    notes: Optional[str] = None


class BreakRequest(BaseModel):
    idempotency_key: Optional[str] = None
    source: EventSource = EventSource.APP


class TimeclockStatusResponse(BaseModel):
    has_session: bool
    state: Optional[TimeSessionState] = None
    session_id: Optional[str] = None
    clock_in_at: Optional[str] = None
    current_break_start: Optional[str] = None
    total_work_seconds: int = 0
    total_break_seconds: int = 0
    net_work_seconds: int = 0
    shift_linked: bool = False
    shift_info: Optional[Dict[str, Any]] = None


class AdminSessionCorrection(BaseModel):
    """Admin-Korrektur einer Time Session"""
    clock_in_at: Optional[str] = None  # ISO UTC
    clock_out_at: Optional[str] = None  # ISO UTC
    breaks: Optional[List[BreakRecord]] = None
    correction_reason: str = Field(..., min_length=5, max_length=500)


# ============== HELPER FUNCTIONS ==============
def now_utc() -> datetime:
    """Current UTC datetime"""
    return datetime.now(timezone.utc)


def now_iso() -> str:
    """Current UTC datetime as ISO string"""
    return now_utc().isoformat()


def get_berlin_date(dt: datetime = None) -> str:
    """Get date in Europe/Berlin timezone as YYYY-MM-DD"""
    if dt is None:
        dt = now_utc()
    berlin_dt = dt.astimezone(BERLIN_TZ)
    return berlin_dt.strftime("%Y-%m-%d")


def get_berlin_time(dt: datetime = None) -> str:
    """Get time in Europe/Berlin timezone as HH:MM:SS"""
    if dt is None:
        dt = now_utc()
    berlin_dt = dt.astimezone(BERLIN_TZ)
    return berlin_dt.strftime("%H:%M:%S")


def generate_idempotency_key(staff_id: str, event_type: str) -> str:
    """Generate idempotency key based on staff, event type, and minute"""
    now = now_utc()
    minute_key = now.strftime("%Y%m%d%H%M")
    raw = f"{staff_id}:{event_type}:{minute_key}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def calculate_session_totals(session: dict) -> dict:
    """Calculate total work and break seconds for a session"""
    now = now_utc()
    
    # Parse times
    clock_in = datetime.fromisoformat(session["clock_in_at"].replace("Z", "+00:00"))
    clock_out = None
    if session.get("clock_out_at"):
        clock_out = datetime.fromisoformat(session["clock_out_at"].replace("Z", "+00:00"))
    
    # Calculate total break seconds
    total_break_seconds = 0
    breaks = session.get("breaks", [])
    for brk in breaks:
        if brk.get("end_at"):
            brk_start = datetime.fromisoformat(brk["start_at"].replace("Z", "+00:00"))
            brk_end = datetime.fromisoformat(brk["end_at"].replace("Z", "+00:00"))
            total_break_seconds += int((brk_end - brk_start).total_seconds())
        elif session.get("state") == TimeSessionState.BREAK.value:
            # Active break
            brk_start = datetime.fromisoformat(brk["start_at"].replace("Z", "+00:00"))
            total_break_seconds += int((now - brk_start).total_seconds())
    
    # Calculate total work seconds (gross)
    if clock_out:
        total_work_seconds = int((clock_out - clock_in).total_seconds())
    else:
        total_work_seconds = int((now - clock_in).total_seconds())
    
    # Net work = gross - breaks
    net_work_seconds = max(0, total_work_seconds - total_break_seconds)
    
    return {
        "total_work_seconds": total_work_seconds,
        "total_break_seconds": total_break_seconds,
        "net_work_seconds": net_work_seconds
    }


async def get_staff_member_for_user(user: dict) -> dict:
    """Get staff member linked to user"""
    # Method 1: Direct link via staff_member_id
    staff_member_id = user.get("staff_member_id")
    if staff_member_id:
        staff = await db.staff_members.find_one({"id": staff_member_id, "archived": False}, {"_id": 0})
        if staff:
            return staff
    
    # Method 2: Email matching
    staff = await db.staff_members.find_one({"email": user.get("email"), "archived": False}, {"_id": 0})
    return staff


async def find_matching_shift(staff_member_id: str, clock_in_time: datetime) -> Optional[dict]:
    """
    Find a shift that matches the clock-in time for auto-linking.
    
    Rules:
    - Staff must be in assigned_staff_ids
    - Clock-in within window: start-60min to end+120min
    - Exactly 1 match → return shift
    - 0 or >1 matches → return None
    """
    day_key = get_berlin_date(clock_in_time)
    
    # Find shifts where this staff member is assigned
    query = {
        "assigned_staff_ids": staff_member_id,
        "date_local": day_key,
        "status": ShiftStatusV2.PUBLISHED.value,
        "archived": {"$ne": True}
    }
    
    shifts = await db.shifts.find(query, {"_id": 0}).to_list(100)
    
    if not shifts:
        # Fallback: Check old structure (staff_member_id single field)
        query_legacy = {
            "staff_member_id": staff_member_id,
            "$or": [
                {"shift_date": day_key},
                {"date_local": day_key},
                {"date": day_key}
            ],
            "archived": {"$ne": True}
        }
        shifts = await db.shifts.find(query_legacy, {"_id": 0}).to_list(100)
    
    # Filter by time window
    matching_shifts = []
    for shift in shifts:
        # Parse shift times
        start_utc = shift.get("start_at_utc")
        end_utc = shift.get("end_at_utc")
        
        if not start_utc or not end_utc:
            # Legacy: Convert from local times
            shift_date = shift.get("date_local") or shift.get("shift_date") or shift.get("date")
            start_time = shift.get("start_time", "00:00")
            end_time = shift.get("end_time", "23:59")
            
            try:
                start_local = BERLIN_TZ.localize(datetime.strptime(f"{shift_date} {start_time}", "%Y-%m-%d %H:%M"))
                end_local = BERLIN_TZ.localize(datetime.strptime(f"{shift_date} {end_time}", "%Y-%m-%d %H:%M"))
                
                # Handle overnight shifts
                if end_local <= start_local:
                    end_local += timedelta(days=1)
                
                start_utc = start_local.astimezone(timezone.utc)
                end_utc = end_local.astimezone(timezone.utc)
            except Exception as e:
                logger.warning(f"Could not parse shift times: {e}")
                continue
        else:
            start_utc = datetime.fromisoformat(start_utc.replace("Z", "+00:00"))
            end_utc = datetime.fromisoformat(end_utc.replace("Z", "+00:00"))
        
        # Calculate window
        window_start = start_utc - timedelta(minutes=SHIFT_LINK_WINDOW_BEFORE_MINUTES)
        window_end = end_utc + timedelta(minutes=SHIFT_LINK_WINDOW_AFTER_MINUTES)
        
        if window_start <= clock_in_time <= window_end:
            matching_shifts.append(shift)
    
    # Return only if exactly 1 match
    if len(matching_shifts) == 1:
        return matching_shifts[0]
    
    return None


async def create_time_event(
    session_id: str,
    staff_member_id: str,
    event_type: TimeEventType,
    source: EventSource,
    idempotency_key: str,
    metadata: dict = None
) -> dict:
    """Create an append-only time event"""
    now = now_utc()
    
    event = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "staff_member_id": staff_member_id,
        "event_type": event_type.value,
        "timestamp_utc": now.isoformat(),
        "timestamp_local": get_berlin_time(now),
        "day_key": get_berlin_date(now),
        "source": source.value,
        "idempotency_key": idempotency_key,
        "metadata": metadata or {},
        "created_at": now.isoformat()
    }
    
    await db.time_events.insert_one(event)
    return {k: v for k, v in event.items() if k != "_id"}


# ============== ROUTER ==============
timeclock_router = APIRouter(prefix="/api/timeclock", tags=["Timeclock"])


# ============== TIMECLOCK ENDPOINTS ==============

@timeclock_router.get("/status", response_model=TimeclockStatusResponse)
async def get_timeclock_status(user: dict = Depends(get_current_user)):
    """
    Get current timeclock status for the logged-in user.
    Returns current state, session info, and linked shift.
    """
    staff = await get_staff_member_for_user(user)
    if not staff:
        return TimeclockStatusResponse(
            has_session=False,
            state=None,
            total_work_seconds=0,
            total_break_seconds=0,
            net_work_seconds=0,
            shift_linked=False
        )
    
    day_key = get_berlin_date()
    session = await db.time_sessions.find_one({
        "staff_member_id": staff["id"],
        "day_key": day_key
    }, {"_id": 0})
    
    if not session:
        return TimeclockStatusResponse(
            has_session=False,
            state=None,
            total_work_seconds=0,
            total_break_seconds=0,
            net_work_seconds=0,
            shift_linked=False
        )
    
    totals = calculate_session_totals(session)
    
    # Get current break start if in break
    current_break_start = None
    if session["state"] == TimeSessionState.BREAK.value:
        breaks = session.get("breaks", [])
        for brk in breaks:
            if not brk.get("end_at"):
                current_break_start = brk["start_at"]
                break
    
    # Get shift info if linked
    shift_info = None
    if session.get("shift_id"):
        shift = await db.shifts.find_one({"id": session["shift_id"]}, {"_id": 0})
        if shift:
            shift_info = {
                "id": shift["id"],
                "role": shift.get("role"),
                "start_time": shift.get("start_time"),
                "end_time": shift.get("end_time"),
                "date_local": shift.get("date_local") or shift.get("shift_date")
            }
    
    return TimeclockStatusResponse(
        has_session=True,
        state=TimeSessionState(session["state"]),
        session_id=session["id"],
        clock_in_at=session["clock_in_at"],
        current_break_start=current_break_start,
        total_work_seconds=totals["total_work_seconds"],
        total_break_seconds=totals["total_break_seconds"],
        net_work_seconds=totals["net_work_seconds"],
        shift_linked=session.get("shift_id") is not None,
        shift_info=shift_info
    )


@timeclock_router.post("/clock-in")
async def clock_in(
    data: ClockInRequest = ClockInRequest(),
    user: dict = Depends(get_current_user)
):
    """
    Clock in for the current day.
    
    Rules:
    - Max 1 session per staff member per day
    - Second clock-in → 409 CONFLICT
    - Auto-links to shift if exactly 1 matching shift found
    """
    staff = await get_staff_member_for_user(user)
    if not staff:
        raise HTTPException(
            status_code=400,
            detail="Kein Mitarbeiterprofil verknüpft. Bitte wende dich an die Schichtleitung."
        )
    
    staff_id = staff["id"]
    now = now_utc()
    day_key = get_berlin_date(now)
    
    # Check for existing session today
    existing = await db.time_sessions.find_one({
        "staff_member_id": staff_id,
        "day_key": day_key
    })
    
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Du bist heute bereits eingestempelt. Status: {existing['state']}"
        )
    
    # Generate idempotency key
    idem_key = data.idempotency_key or generate_idempotency_key(staff_id, "CLOCK_IN")
    
    # Check for duplicate event
    dup_event = await db.time_events.find_one({"idempotency_key": idem_key})
    if dup_event:
        # Return existing session
        session = await db.time_sessions.find_one({"id": dup_event["session_id"]}, {"_id": 0})
        return {
            "success": True,
            "message": "Bereits eingestempelt (idempotent)",
            "session": session,
            "duplicate": True
        }
    
    # Try to auto-link to shift
    matching_shift = await find_matching_shift(staff_id, now)
    shift_id = matching_shift["id"] if matching_shift else None
    link_method = LinkMethod.AUTO if matching_shift else LinkMethod.NONE
    
    # Create session
    session_id = str(uuid.uuid4())
    session = {
        "id": session_id,
        "staff_member_id": staff_id,
        "day_key": day_key,
        "state": TimeSessionState.WORKING.value,
        "shift_id": shift_id,
        "link_method": link_method.value,
        "clock_in_at": now.isoformat(),
        "clock_out_at": None,
        "total_work_seconds": 0,
        "total_break_seconds": 0,
        "breaks": [],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.time_sessions.insert_one(session)
    
    # Create event
    await create_time_event(
        session_id=session_id,
        staff_member_id=staff_id,
        event_type=TimeEventType.CLOCK_IN,
        source=data.source,
        idempotency_key=idem_key,
        metadata={"notes": data.notes, "shift_linked": shift_id is not None}
    )
    
    # Audit log
    await create_audit_log(
        user, "time_session", session_id, "clock_in",
        None,
        {"staff_id": staff_id, "day_key": day_key, "shift_id": shift_id}
    )
    
    shift_info = None
    if matching_shift:
        shift_info = {
            "id": matching_shift["id"],
            "role": matching_shift.get("role"),
            "start_time": matching_shift.get("start_time"),
            "end_time": matching_shift.get("end_time")
        }
    
    return {
        "success": True,
        "message": "Erfolgreich eingestempelt",
        "session_id": session_id,
        "state": TimeSessionState.WORKING.value,
        "clock_in_at": session["clock_in_at"],
        "shift_linked": shift_id is not None,
        "link_method": link_method.value,
        "shift_info": shift_info
    }


@timeclock_router.post("/clock-out")
async def clock_out(
    data: ClockOutRequest = ClockOutRequest(),
    user: dict = Depends(get_current_user)
):
    """
    Clock out for the current day.
    
    Rules:
    - Must have active session
    - BLOCKED if state is BREAK → 409 CONFLICT
    - Transitions to CLOSED
    """
    staff = await get_staff_member_for_user(user)
    if not staff:
        raise HTTPException(status_code=400, detail="Kein Mitarbeiterprofil verknüpft")
    
    staff_id = staff["id"]
    day_key = get_berlin_date()
    
    session = await db.time_sessions.find_one({
        "staff_member_id": staff_id,
        "day_key": day_key
    }, {"_id": 0})
    
    if not session:
        raise HTTPException(status_code=404, detail="Keine aktive Session gefunden. Bitte zuerst einstempeln.")
    
    if session["state"] == TimeSessionState.CLOSED.value:
        raise HTTPException(status_code=409, detail="Session ist bereits abgeschlossen")
    
    # ========== CRITICAL: BLOCK CLOCK-OUT DURING BREAK ==========
    if session["state"] == TimeSessionState.BREAK.value:
        raise HTTPException(
            status_code=409,
            detail="Ausstempeln während einer Pause nicht möglich! Bitte erst die Pause beenden."
        )
    
    # Generate idempotency key
    idem_key = data.idempotency_key or generate_idempotency_key(staff_id, "CLOCK_OUT")
    
    # Check for duplicate
    dup_event = await db.time_events.find_one({"idempotency_key": idem_key})
    if dup_event:
        updated_session = await db.time_sessions.find_one({"id": session["id"]}, {"_id": 0})
        return {
            "success": True,
            "message": "Bereits ausgestempelt (idempotent)",
            "session": updated_session,
            "duplicate": True
        }
    
    now = now_utc()
    
    # Calculate totals
    totals = calculate_session_totals({**session, "clock_out_at": now.isoformat()})
    
    # Update session
    update_data = {
        "state": TimeSessionState.CLOSED.value,
        "clock_out_at": now.isoformat(),
        "total_work_seconds": totals["total_work_seconds"],
        "total_break_seconds": totals["total_break_seconds"],
        "updated_at": now.isoformat()
    }
    
    await db.time_sessions.update_one({"id": session["id"]}, {"$set": update_data})
    
    # Create event
    await create_time_event(
        session_id=session["id"],
        staff_member_id=staff_id,
        event_type=TimeEventType.CLOCK_OUT,
        source=data.source,
        idempotency_key=idem_key,
        metadata={
            "notes": data.notes,
            "total_work_seconds": totals["total_work_seconds"],
            "total_break_seconds": totals["total_break_seconds"],
            "net_work_seconds": totals["net_work_seconds"]
        }
    )
    
    # Audit log
    await create_audit_log(
        user, "time_session", session["id"], "clock_out",
        {"state": session["state"]},
        {"state": TimeSessionState.CLOSED.value, "totals": totals}
    )
    
    return {
        "success": True,
        "message": "Erfolgreich ausgestempelt",
        "session_id": session["id"],
        "state": TimeSessionState.CLOSED.value,
        "clock_out_at": now.isoformat(),
        "total_work_seconds": totals["total_work_seconds"],
        "total_break_seconds": totals["total_break_seconds"],
        "net_work_seconds": totals["net_work_seconds"]
    }


@timeclock_router.post("/break-start")
async def start_break(
    data: BreakRequest = BreakRequest(),
    user: dict = Depends(get_current_user)
):
    """
    Start a break.
    
    Rules:
    - Must be in WORKING state
    - Only one active break at a time
    - Transitions to BREAK state
    """
    staff = await get_staff_member_for_user(user)
    if not staff:
        raise HTTPException(status_code=400, detail="Kein Mitarbeiterprofil verknüpft")
    
    staff_id = staff["id"]
    day_key = get_berlin_date()
    
    session = await db.time_sessions.find_one({
        "staff_member_id": staff_id,
        "day_key": day_key
    }, {"_id": 0})
    
    if not session:
        raise HTTPException(status_code=404, detail="Keine aktive Session gefunden")
    
    if session["state"] == TimeSessionState.CLOSED.value:
        raise HTTPException(status_code=409, detail="Session ist bereits abgeschlossen")
    
    if session["state"] == TimeSessionState.BREAK.value:
        raise HTTPException(status_code=409, detail="Du bist bereits in einer Pause")
    
    # Generate idempotency key
    idem_key = data.idempotency_key or generate_idempotency_key(staff_id, "BREAK_START")
    
    # Check duplicate
    dup_event = await db.time_events.find_one({"idempotency_key": idem_key})
    if dup_event:
        return {"success": True, "message": "Pause bereits gestartet (idempotent)", "duplicate": True}
    
    now = now_utc()
    
    # Add new break
    new_break = {
        "start_at": now.isoformat(),
        "end_at": None,
        "duration_seconds": 0
    }
    
    breaks = session.get("breaks", [])
    breaks.append(new_break)
    
    # Update session
    await db.time_sessions.update_one(
        {"id": session["id"]},
        {"$set": {
            "state": TimeSessionState.BREAK.value,
            "breaks": breaks,
            "updated_at": now.isoformat()
        }}
    )
    
    # Create event
    await create_time_event(
        session_id=session["id"],
        staff_member_id=staff_id,
        event_type=TimeEventType.BREAK_START,
        source=data.source,
        idempotency_key=idem_key
    )
    
    # Audit log
    await create_audit_log(
        user, "time_session", session["id"], "break_start",
        {"state": session["state"]},
        {"state": TimeSessionState.BREAK.value, "break_count": len(breaks)}
    )
    
    return {
        "success": True,
        "message": "Pause gestartet",
        "session_id": session["id"],
        "state": TimeSessionState.BREAK.value,
        "break_start_at": now.isoformat(),
        "break_count": len(breaks)
    }


@timeclock_router.post("/break-end")
async def end_break(
    data: BreakRequest = BreakRequest(),
    user: dict = Depends(get_current_user)
):
    """
    End current break.
    
    Rules:
    - Must be in BREAK state
    - Closes active break and transitions to WORKING
    """
    staff = await get_staff_member_for_user(user)
    if not staff:
        raise HTTPException(status_code=400, detail="Kein Mitarbeiterprofil verknüpft")
    
    staff_id = staff["id"]
    day_key = get_berlin_date()
    
    session = await db.time_sessions.find_one({
        "staff_member_id": staff_id,
        "day_key": day_key
    }, {"_id": 0})
    
    if not session:
        raise HTTPException(status_code=404, detail="Keine aktive Session gefunden")
    
    if session["state"] != TimeSessionState.BREAK.value:
        raise HTTPException(status_code=409, detail="Keine aktive Pause vorhanden")
    
    # Generate idempotency key
    idem_key = data.idempotency_key or generate_idempotency_key(staff_id, "BREAK_END")
    
    # Check duplicate
    dup_event = await db.time_events.find_one({"idempotency_key": idem_key})
    if dup_event:
        return {"success": True, "message": "Pause bereits beendet (idempotent)", "duplicate": True}
    
    now = now_utc()
    
    # Find and close active break
    breaks = session.get("breaks", [])
    active_break_index = None
    for i, brk in enumerate(breaks):
        if brk.get("end_at") is None:
            active_break_index = i
            break
    
    if active_break_index is None:
        raise HTTPException(status_code=409, detail="Keine offene Pause gefunden")
    
    # Calculate break duration
    break_start = datetime.fromisoformat(breaks[active_break_index]["start_at"].replace("Z", "+00:00"))
    duration_seconds = int((now - break_start).total_seconds())
    
    breaks[active_break_index]["end_at"] = now.isoformat()
    breaks[active_break_index]["duration_seconds"] = duration_seconds
    
    # Update session
    await db.time_sessions.update_one(
        {"id": session["id"]},
        {"$set": {
            "state": TimeSessionState.WORKING.value,
            "breaks": breaks,
            "updated_at": now.isoformat()
        }}
    )
    
    # Create event
    await create_time_event(
        session_id=session["id"],
        staff_member_id=staff_id,
        event_type=TimeEventType.BREAK_END,
        source=data.source,
        idempotency_key=idem_key,
        metadata={"break_duration_seconds": duration_seconds}
    )
    
    # Audit log
    await create_audit_log(
        user, "time_session", session["id"], "break_end",
        {"state": TimeSessionState.BREAK.value},
        {"state": TimeSessionState.WORKING.value, "break_duration_seconds": duration_seconds}
    )
    
    return {
        "success": True,
        "message": "Pause beendet",
        "session_id": session["id"],
        "state": TimeSessionState.WORKING.value,
        "break_duration_seconds": duration_seconds,
        "break_count": len(breaks)
    }


@timeclock_router.get("/today")
async def get_today_session(user: dict = Depends(get_current_user)):
    """Get today's time session with full details"""
    staff = await get_staff_member_for_user(user)
    if not staff:
        return {
            "has_session": False,
            "message": "Kein Mitarbeiterprofil verknüpft"
        }
    
    day_key = get_berlin_date()
    session = await db.time_sessions.find_one({
        "staff_member_id": staff["id"],
        "day_key": day_key
    }, {"_id": 0})
    
    if not session:
        return {
            "has_session": False,
            "day_key": day_key,
            "message": "Heute noch nicht eingestempelt"
        }
    
    # Enrich with staff name
    session["staff_name"] = staff.get("full_name") or f"{staff.get('first_name', '')} {staff.get('last_name', '')}".strip()
    
    # Calculate totals
    totals = calculate_session_totals(session)
    session.update(totals)
    session["net_work_seconds"] = totals["net_work_seconds"]
    
    # Get shift info if linked
    if session.get("shift_id"):
        shift = await db.shifts.find_one({"id": session["shift_id"]}, {"_id": 0})
        if shift:
            session["shift_info"] = {
                "id": shift["id"],
                "role": shift.get("role"),
                "start_time": shift.get("start_time"),
                "end_time": shift.get("end_time"),
                "station": shift.get("station")
            }
    
    # Format times for display
    session["formatted"] = {
        "work_time": f"{totals['total_work_seconds'] // 3600}h {(totals['total_work_seconds'] % 3600) // 60}m",
        "break_time": f"{totals['total_break_seconds'] // 3600}h {(totals['total_break_seconds'] % 3600) // 60}m",
        "net_time": f"{totals['net_work_seconds'] // 3600}h {(totals['net_work_seconds'] % 3600) // 60}m"
    }
    
    return {
        "has_session": True,
        "session": session
    }


@timeclock_router.get("/history")
async def get_session_history(
    days: int = Query(default=7, ge=1, le=90),
    user: dict = Depends(get_current_user)
):
    """Get historical time sessions for the logged-in user"""
    staff = await get_staff_member_for_user(user)
    if not staff:
        return {"sessions": [], "message": "Kein Mitarbeiterprofil verknüpft"}
    
    # Calculate date range
    today = date.today()
    start_date = (today - timedelta(days=days)).isoformat()
    
    sessions = await db.time_sessions.find({
        "staff_member_id": staff["id"],
        "day_key": {"$gte": start_date}
    }, {"_id": 0}).sort("day_key", -1).to_list(days)
    
    # Enrich sessions
    for session in sessions:
        totals = calculate_session_totals(session)
        session.update(totals)
        session["net_work_seconds"] = totals["net_work_seconds"]
    
    return {
        "sessions": sessions,
        "count": len(sessions),
        "date_range": {
            "from": start_date,
            "to": today.isoformat()
        }
    }


# ============== ADMIN ENDPOINTS ==============

@timeclock_router.get("/admin/sessions")
async def list_time_sessions(
    day_key: Optional[str] = None,
    staff_member_id: Optional[str] = None,
    state: Optional[TimeSessionState] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: dict = Depends(require_manager)
):
    """List time sessions with filters (Manager+)"""
    query = {}
    
    if day_key:
        query["day_key"] = day_key
    elif date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to
        if date_query:
            query["day_key"] = date_query
    else:
        # Default: today
        query["day_key"] = get_berlin_date()
    
    if staff_member_id:
        query["staff_member_id"] = staff_member_id
    
    if state:
        query["state"] = state.value
    
    sessions = await db.time_sessions.find(query, {"_id": 0}).sort("clock_in_at", -1).to_list(500)
    
    # Enrich with staff names
    staff_ids = list(set(s["staff_member_id"] for s in sessions))
    staff_map = {}
    if staff_ids:
        staff_members = await db.staff_members.find({"id": {"$in": staff_ids}}, {"_id": 0}).to_list(len(staff_ids))
        staff_map = {s["id"]: s for s in staff_members}
    
    for session in sessions:
        staff = staff_map.get(session["staff_member_id"], {})
        session["staff_name"] = staff.get("full_name") or f"{staff.get('first_name', '')} {staff.get('last_name', '')}".strip()
        
        # Calculate totals
        totals = calculate_session_totals(session)
        session.update(totals)
    
    return {
        "sessions": sessions,
        "count": len(sessions),
        "filters": {
            "day_key": query.get("day_key"),
            "staff_member_id": staff_member_id,
            "state": state.value if state else None
        }
    }


@timeclock_router.get("/admin/sessions/{session_id}")
async def get_time_session(session_id: str, user: dict = Depends(require_manager)):
    """Get a single time session with full event history"""
    session = await db.time_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise NotFoundException("Time Session")
    
    # Get staff info
    staff = await db.staff_members.find_one({"id": session["staff_member_id"]}, {"_id": 0})
    session["staff_name"] = staff.get("full_name") if staff else "Unbekannt"
    
    # Get events
    events = await db.time_events.find(
        {"session_id": session_id},
        {"_id": 0}
    ).sort("timestamp_utc", 1).to_list(100)
    
    # Calculate totals
    totals = calculate_session_totals(session)
    session.update(totals)
    
    return {
        "session": session,
        "events": events
    }


@timeclock_router.patch("/admin/sessions/{session_id}")
async def correct_time_session(
    session_id: str,
    data: AdminSessionCorrection,
    user: dict = Depends(require_admin)
):
    """
    Admin correction of a time session.
    Creates audit trail with correction reason.
    """
    session = await db.time_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise NotFoundException("Time Session")
    
    before = safe_dict_for_audit(session)
    update_data = {"updated_at": now_iso()}
    
    if data.clock_in_at:
        update_data["clock_in_at"] = data.clock_in_at
    
    if data.clock_out_at:
        update_data["clock_out_at"] = data.clock_out_at
        update_data["state"] = TimeSessionState.CLOSED.value
    
    if data.breaks is not None:
        update_data["breaks"] = [b.model_dump() for b in data.breaks]
    
    await db.time_sessions.update_one({"id": session_id}, {"$set": update_data})
    
    # Create correction event
    await create_time_event(
        session_id=session_id,
        staff_member_id=session["staff_member_id"],
        event_type=TimeEventType.CLOCK_OUT,  # Using CLOCK_OUT for corrections
        source=EventSource.ADMIN_CORRECTION,
        idempotency_key=str(uuid.uuid4()),
        metadata={
            "correction_reason": data.correction_reason,
            "corrected_by": user.get("email"),
            "original_values": before
        }
    )
    
    # Audit log
    await create_audit_log(
        user, "time_session", session_id, "admin_correction",
        before,
        {**update_data, "correction_reason": data.correction_reason}
    )
    
    updated = await db.time_sessions.find_one({"id": session_id}, {"_id": 0})
    totals = calculate_session_totals(updated)
    updated.update(totals)
    
    return {
        "success": True,
        "message": "Session korrigiert",
        "session": updated,
        "correction_reason": data.correction_reason
    }


@timeclock_router.get("/admin/events")
async def list_time_events(
    session_id: Optional[str] = None,
    staff_member_id: Optional[str] = None,
    event_type: Optional[TimeEventType] = None,
    day_key: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    user: dict = Depends(require_admin)
):
    """List time events (Admin only) - append-only audit trail"""
    query = {}
    
    if session_id:
        query["session_id"] = session_id
    if staff_member_id:
        query["staff_member_id"] = staff_member_id
    if event_type:
        query["event_type"] = event_type.value
    if day_key:
        query["day_key"] = day_key
    
    events = await db.time_events.find(query, {"_id": 0}).sort("timestamp_utc", -1).to_list(limit)
    
    return {
        "events": events,
        "count": len(events)
    }


# ============== STATISTICS ENDPOINT ==============

@timeclock_router.get("/admin/daily-overview")
async def get_daily_overview(
    day_key: Optional[str] = None,
    user: dict = Depends(require_manager)
):
    """
    Get daily overview: who's working, on break, missing despite shift assignment.
    """
    if not day_key:
        day_key = get_berlin_date()
    
    # Get all sessions for the day
    sessions = await db.time_sessions.find({"day_key": day_key}, {"_id": 0}).to_list(500)
    
    # Get all published shifts for the day
    shifts = await db.shifts.find({
        "$or": [
            {"date_local": day_key},
            {"shift_date": day_key},
            {"date": day_key}
        ],
        "status": ShiftStatusV2.PUBLISHED.value,
        "archived": {"$ne": True}
    }, {"_id": 0}).to_list(500)
    
    # Collect all staff IDs
    session_staff_ids = {s["staff_member_id"] for s in sessions}
    shift_staff_ids = set()
    for shift in shifts:
        shift_staff_ids.update(shift.get("assigned_staff_ids", []))
        if shift.get("staff_member_id"):
            shift_staff_ids.add(shift["staff_member_id"])
    
    all_staff_ids = session_staff_ids | shift_staff_ids
    
    # Get staff info
    staff_members = await db.staff_members.find({"id": {"$in": list(all_staff_ids)}}, {"_id": 0}).to_list(len(all_staff_ids))
    staff_map = {s["id"]: s for s in staff_members}
    
    # Categorize
    working = []
    on_break = []
    completed = []
    missing = []
    unplanned = []
    
    session_map = {s["staff_member_id"]: s for s in sessions}
    
    for session in sessions:
        staff = staff_map.get(session["staff_member_id"], {})
        staff_name = staff.get("full_name") or f"{staff.get('first_name', '')} {staff.get('last_name', '')}".strip()
        totals = calculate_session_totals(session)
        
        entry = {
            "staff_id": session["staff_member_id"],
            "staff_name": staff_name,
            "session_id": session["id"],
            "clock_in_at": session["clock_in_at"],
            "clock_out_at": session.get("clock_out_at"),
            "shift_linked": session.get("shift_id") is not None,
            **totals
        }
        
        if session["state"] == TimeSessionState.WORKING.value:
            working.append(entry)
        elif session["state"] == TimeSessionState.BREAK.value:
            on_break.append(entry)
        else:
            completed.append(entry)
        
        # Check if this was a planned shift
        if session["staff_member_id"] not in shift_staff_ids:
            unplanned.append(entry)
    
    # Find missing (shift assigned but no session)
    for staff_id in shift_staff_ids:
        if staff_id not in session_staff_ids:
            staff = staff_map.get(staff_id, {})
            staff_name = staff.get("full_name") or f"{staff.get('first_name', '')} {staff.get('last_name', '')}".strip()
            
            # Find their shift(s)
            staff_shifts = []
            for shift in shifts:
                if staff_id in shift.get("assigned_staff_ids", []) or shift.get("staff_member_id") == staff_id:
                    staff_shifts.append({
                        "shift_id": shift["id"],
                        "start_time": shift.get("start_time"),
                        "end_time": shift.get("end_time"),
                        "role": shift.get("role")
                    })
            
            missing.append({
                "staff_id": staff_id,
                "staff_name": staff_name,
                "shifts": staff_shifts
            })
    
    return {
        "day_key": day_key,
        "summary": {
            "working_count": len(working),
            "on_break_count": len(on_break),
            "completed_count": len(completed),
            "missing_count": len(missing),
            "unplanned_count": len(unplanned)
        },
        "working": working,
        "on_break": on_break,
        "completed": completed,
        "missing": missing,
        "unplanned": unplanned
    }
