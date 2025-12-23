"""
GastroCore Reservation Slots Module
================================================================================
Konfigurierbare Slots & Durchgänge für Reservierungen

Features:
1. Slot-Regeln pro Wochentag (unabhängig von Öffnungszeiten)
2. Blocked Windows (Durchgänge / Küchenfenster)
3. Event-Cutoff (letzte à la carte vor Event)
4. Ausnahmen pro Datum
5. Effective Slots Endpoint für Widget & Admin

Prioritäten:
1. reservation_slot_exceptions (höchste)
2. reservation_slot_rules (nach priority)
3. Fallback: auto-generate

ADDITIV - Keine Breaking Changes
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, date, timedelta, time
from enum import Enum
import uuid

# Core imports
from core.database import db
from core.auth import require_admin, require_manager, get_current_user
from core.audit import create_audit_log, safe_dict_for_audit
from core.exceptions import NotFoundException, ValidationException, ConflictException

# Import Opening Hours für effective hours
from opening_hours_module import calculate_effective_hours, is_holiday_brandenburg

import logging
logger = logging.getLogger(__name__)


# ============== ROUTER ==============
slots_router = APIRouter(tags=["Reservation Slots"])


# ============== CONSTANTS ==============
DEFAULT_SLOT_INTERVAL = 30  # Minuten
DEFAULT_EVENT_CUTOFF = 120  # Minuten vor Event


# ============== HELPER FUNCTIONS ==============

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def time_to_minutes(time_str: str) -> int:
    """Konvertiere HH:MM zu Minuten seit Mitternacht"""
    h, m = map(int, time_str.split(":"))
    return h * 60 + m


def minutes_to_time(minutes: int) -> str:
    """Konvertiere Minuten seit Mitternacht zu HH:MM"""
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def generate_slots_between(start: str, end: str, interval: int) -> List[str]:
    """Generiere Slots zwischen start und end mit interval"""
    slots = []
    start_min = time_to_minutes(start)
    end_min = time_to_minutes(end)
    
    current = start_min
    while current <= end_min:  # Letzter Slot = end_min (z.B. 18:30)
        slots.append(minutes_to_time(current))
        current += interval
    
    return slots


def is_slot_in_blocked_window(slot: str, blocked_windows: List[dict]) -> tuple:
    """
    Prüft ob ein Slot in einem blocked window liegt.
    Returns: (is_blocked: bool, reason: str or None)
    """
    slot_min = time_to_minutes(slot)
    
    for window in blocked_windows:
        start_min = time_to_minutes(window.get("start", "00:00"))
        end_min = time_to_minutes(window.get("end", "23:59"))
        
        if start_min <= slot_min < end_min:
            return True, window.get("reason", "Gesperrt")
    
    return False, None


# ============== PYDANTIC MODELS ==============

class BlockedWindow(BaseModel):
    """Gesperrtes Zeitfenster (z.B. Durchgang)"""
    start: str  # HH:MM
    end: str    # HH:MM
    reason: Optional[str] = None
    
    @field_validator('start', 'end')
    @classmethod
    def validate_time(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError(f"Ungültiges Zeitformat: {v} (HH:MM erwartet)")
        return v


class GenerateBetween(BaseModel):
    """Automatische Slot-Generierung"""
    start: str  # HH:MM
    end: str    # HH:MM
    interval: int = Field(default=30, ge=15, le=120)
    
    @field_validator('start', 'end')
    @classmethod
    def validate_time(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError(f"Ungültiges Zeitformat: {v}")
        return v


class SlotRuleCreate(BaseModel):
    """Neue Slot-Regel erstellen - NUR automatische Generierung"""
    name: str = Field(..., min_length=2, max_length=100)
    valid_from: Optional[str] = None  # YYYY-MM-DD
    valid_to: Optional[str] = None    # YYYY-MM-DD
    applies_days: List[int] = Field(default_factory=lambda: [0,1,2,3,4,5,6])  # 0=Mo..6=So
    generate_between: GenerateBetween  # PFLICHT: Start/End/Interval
    blocked_windows: List[BlockedWindow] = Field(default_factory=list)
    active: bool = True
    priority: int = Field(default=10, ge=0, le=100)
    
    @field_validator('applies_days')
    @classmethod
    def validate_days(cls, v):
        for d in v:
            if d < 0 or d > 6:
                raise ValueError(f"Ungültiger Wochentag: {d} (0-6 erwartet)")
        return v


class SlotRuleUpdate(BaseModel):
    """Slot-Regel aktualisieren"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    applies_days: Optional[List[int]] = None
    generate_between: Optional[GenerateBetween] = None
    blocked_windows: Optional[List[BlockedWindow]] = None
    active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=100)


class SlotExceptionCreate(BaseModel):
    """Ausnahme für ein Datum"""
    date: str  # YYYY-MM-DD
    allowed_start_times_override: Optional[List[str]] = None
    blocked_windows_override: Optional[List[BlockedWindow]] = None
    reason: str = Field(..., min_length=2, max_length=200)
    active: bool = True
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Ungültiges Datumsformat: {v}")
        return v


class SlotExceptionUpdate(BaseModel):
    """Ausnahme aktualisieren"""
    allowed_start_times_override: Optional[List[str]] = None
    blocked_windows_override: Optional[List[BlockedWindow]] = None
    reason: Optional[str] = Field(None, min_length=2, max_length=200)
    active: Optional[bool] = None


# ============== CORE BUSINESS LOGIC ==============

async def get_slot_rule_for_date(target_date: date) -> Optional[dict]:
    """
    Finde die passende Slot-Regel für ein Datum.
    Berücksichtigt valid_from/to und applies_days.
    Bei mehreren: höchste priority gewinnt.
    """
    date_str = target_date.strftime("%Y-%m-%d")
    weekday = target_date.weekday()  # 0=Mo..6=So
    
    rules = await db.reservation_slot_rules.find(
        {"active": True, "archived": {"$ne": True}}
    ).to_list(100)
    
    matching = []
    for rule in rules:
        # Prüfe Wochentag
        if weekday not in rule.get("applies_days", [0,1,2,3,4,5,6]):
            continue
        
        # Prüfe valid_from/to
        valid_from = rule.get("valid_from")
        valid_to = rule.get("valid_to")
        
        if valid_from:
            from_date = datetime.strptime(valid_from, "%Y-%m-%d").date()
            if target_date < from_date:
                continue
        
        if valid_to:
            to_date = datetime.strptime(valid_to, "%Y-%m-%d").date()
            if target_date > to_date:
                continue
        
        matching.append(rule)
    
    if not matching:
        return None
    
    # Sortiere nach Priority (höchste zuerst)
    matching.sort(key=lambda x: x.get("priority", 0), reverse=True)
    return matching[0]


async def get_slot_exception_for_date(target_date: date) -> Optional[dict]:
    """Finde Ausnahme für ein Datum"""
    date_str = target_date.strftime("%Y-%m-%d")
    
    exception = await db.reservation_slot_exceptions.find_one(
        {"date": date_str, "active": True, "archived": {"$ne": True}}
    )
    
    return exception


async def get_events_for_date(target_date: date) -> List[dict]:
    """Finde Events für ein Datum"""
    date_str = target_date.strftime("%Y-%m-%d")
    
    # Events mit dates-Array prüfen
    events = await db.events.find(
        {
            "archived": {"$ne": True},
            "$or": [
                {"dates": date_str},
                {"start_date": date_str}
            ]
        }
    ).to_list(50)
    
    return events


async def get_reservation_config() -> dict:
    """Hole Reservierungskonfiguration"""
    config = {
        "default_duration_minutes": 110,
        "buffer_minutes": 10,
        "event_cutoff_minutes_default": 120,
        "max_party_size": 20,
        "min_advance_hours": 2,
        "max_advance_days": 90
    }
    
    # Lade aus Settings
    settings = await db.settings.find(
        {"key": {"$in": [
            "default_duration_minutes",
            "buffer_minutes", 
            "event_cutoff_minutes_default",
            "max_party_size",
            "min_advance_hours",
            "max_advance_days"
        ]}}
    ).to_list(20)
    
    for s in settings:
        key = s.get("key")
        value = s.get("value")
        if key and value:
            try:
                config[key] = int(value)
            except:
                config[key] = value
    
    return config


async def calculate_effective_slots(target_date: date) -> dict:
    """
    KERN-LOGIK: Berechne effektive Slots für ein Datum.
    
    Prioritäten:
    1. Prüfe Öffnungsstatus (opening hours)
    2. Hole Slot-Exception (überschreibt alles)
    3. Hole Slot-Rule
    4. Generiere/lese Slots
    5. Entferne blocked windows
    6. Berücksichtige Event-Cutoff
    """
    date_str = target_date.strftime("%Y-%m-%d")
    weekday = target_date.weekday()
    weekday_names = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    
    result = {
        "date": date_str,
        "weekday": weekday,
        "weekday_de": weekday_names[weekday],
        "open": True,
        "slots": [],
        "blocked": [],
        "notes": [],
        "rule_name": None,
        "exception_active": False
    }
    
    # 1. Prüfe Öffnungsstatus
    effective_hours = await calculate_effective_hours(target_date)
    
    if not effective_hours.get("is_open", False):
        result["open"] = False
        result["notes"].append(effective_hours.get("closure_reason") or "Geschlossen")
        return result
    
    # 2. Hole Konfiguration
    config = await get_reservation_config()
    event_cutoff = config.get("event_cutoff_minutes_default", DEFAULT_EVENT_CUTOFF)
    
    # 3. Prüfe Exception
    exception = await get_slot_exception_for_date(target_date)
    blocked_windows = []
    
    if exception:
        result["exception_active"] = True
        result["notes"].append(f"Ausnahme: {exception.get('reason', '')}")
        
        # Override Slots
        if exception.get("allowed_start_times_override"):
            result["slots"] = exception["allowed_start_times_override"].copy()
            result["rule_name"] = "Ausnahme"
        
        # Override Blocked Windows
        if exception.get("blocked_windows_override"):
            blocked_windows = [
                {"start": bw.get("start"), "end": bw.get("end"), "reason": bw.get("reason")}
                for bw in exception["blocked_windows_override"]
            ]
    
    # 4. Wenn keine Exception-Slots: Hole Regel und generiere Slots
    if not result["slots"]:
        rule = await get_slot_rule_for_date(target_date)
        
        if rule:
            result["rule_name"] = rule.get("name")
            
            # IMMER automatisch generieren (keine exakten Slot-Listen)
            gen = rule.get("generate_between")
            if gen:
                result["slots"] = generate_slots_between(
                    gen.get("start", "12:00"),
                    gen.get("end", "18:30"),
                    gen.get("interval", 30)
                )
            else:
                # Fallback: generiere aus Öffnungszeiten
                blocks = effective_hours.get("blocks", [])
                for block in blocks:
                    if block.get("reservable", True):
                        start = block.get("start", "12:00")
                        end = block.get("end", "18:30")
                        result["slots"].extend(generate_slots_between(start, end, DEFAULT_SLOT_INTERVAL))
            
            # Blocked Windows aus Regel
            if not blocked_windows and rule.get("blocked_windows"):
                blocked_windows = [
                    {"start": bw.get("start"), "end": bw.get("end"), "reason": bw.get("reason")}
                    for bw in rule["blocked_windows"]
                ]
        else:
            # Fallback ohne Regel: generiere aus Öffnungszeiten
            result["rule_name"] = "Auto (Öffnungszeiten)"
            blocks = effective_hours.get("blocks", [])
            for block in blocks:
                if block.get("reservable", True):
                    start = block.get("start", "12:00")
                    end = block.get("end", "18:30")
                    result["slots"].extend(generate_slots_between(start, end, DEFAULT_SLOT_INTERVAL))
    
    # 5. Entferne Slots in blocked windows
    if blocked_windows:
        filtered_slots = []
        for slot in result["slots"]:
            is_blocked, reason = is_slot_in_blocked_window(slot, blocked_windows)
            if not is_blocked:
                filtered_slots.append(slot)
        result["slots"] = filtered_slots
        result["blocked"] = blocked_windows
    
    # 6. Event-Cutoff
    events = await get_events_for_date(target_date)
    
    for event in events:
        event_start = event.get("start_time")
        if not event_start:
            continue
        
        # Berechne Cutoff-Zeit
        event_cutoff_custom = event.get("event_cutoff_minutes", event_cutoff)
        event_start_min = time_to_minutes(event_start)
        cutoff_min = event_start_min - event_cutoff_custom
        cutoff_time = minutes_to_time(max(0, cutoff_min))
        
        # Entferne Slots >= cutoff
        filtered_slots = []
        for slot in result["slots"]:
            slot_min = time_to_minutes(slot)
            if slot_min < cutoff_min:
                filtered_slots.append(slot)
        
        if len(filtered_slots) < len(result["slots"]):
            result["slots"] = filtered_slots
            result["notes"].append(f"Event '{event.get('title', 'Veranstaltung')}' ab {event_start} – letzte à la carte {cutoff_time}")
            result["blocked"].append({
                "start": cutoff_time,
                "end": "23:59",
                "reason": f"Event: {event.get('title', 'Veranstaltung')}"
            })
    
    # Sortiere Slots
    result["slots"] = sorted(set(result["slots"]), key=lambda x: time_to_minutes(x))
    
    return result


# ============== API ENDPOINTS: EFFECTIVE SLOTS ==============

@slots_router.get(
    "/reservation-slots/effective",
    summary="Effektive Slots für Datum",
    description="Berechnet verfügbare Reservierungs-Slots inkl. Event-Cutoff und Blocked Windows."
)
async def get_effective_slots(
    date: str = Query(..., description="Datum (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user)
):
    """GET /api/reservation-slots/effective?date=YYYY-MM-DD"""
    try:
        target = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationException("Ungültiges Datumsformat (YYYY-MM-DD erwartet)")
    
    return await calculate_effective_slots(target)


@slots_router.get(
    "/reservation-slots/effective-range",
    summary="Effektive Slots für Zeitraum",
    description="Berechnet verfügbare Slots für mehrere Tage."
)
async def get_effective_slots_range(
    from_date: str = Query(..., alias="from", description="Startdatum (YYYY-MM-DD)"),
    to_date: str = Query(..., alias="to", description="Enddatum (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user)
):
    """GET /api/reservation-slots/effective-range?from=YYYY-MM-DD&to=YYYY-MM-DD"""
    try:
        start = datetime.strptime(from_date, "%Y-%m-%d").date()
        end = datetime.strptime(to_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationException("Ungültiges Datumsformat (YYYY-MM-DD erwartet)")
    
    if end < start:
        raise ValidationException("Enddatum muss nach Startdatum liegen")
    
    if (end - start).days > 30:
        raise ValidationException("Maximaler Zeitraum: 30 Tage")
    
    results = []
    current = start
    
    while current <= end:
        effective = await calculate_effective_slots(current)
        results.append(effective)
        current += timedelta(days=1)
    
    return {
        "from": from_date,
        "to": to_date,
        "days": results
    }


# ============== API ENDPOINTS: PUBLIC (Widget) ==============

@slots_router.get(
    "/public/slots",
    summary="Öffentliche Slot-Abfrage (Widget)",
    description="Für Buchungs-Widget: Verfügbare Slots ohne Auth."
)
async def get_public_slots(
    date: str = Query(..., description="Datum (YYYY-MM-DD)")
):
    """GET /api/public/slots?date=YYYY-MM-DD"""
    try:
        target = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationException("Ungültiges Datumsformat")
    
    # Prüfe Vorlaufzeit
    config = await get_reservation_config()
    min_advance = config.get("min_advance_hours", 2)
    max_advance = config.get("max_advance_days", 90)
    
    today = datetime.now(timezone.utc).date()
    
    if target < today:
        return {"date": date, "open": False, "slots": [], "notes": ["Datum liegt in der Vergangenheit"]}
    
    if (target - today).days > max_advance:
        return {"date": date, "open": False, "slots": [], "notes": [f"Buchung maximal {max_advance} Tage im Voraus"]}
    
    result = await calculate_effective_slots(target)
    
    # Für heute: Slots in der Vergangenheit entfernen
    if target == today:
        now = datetime.now(timezone.utc)
        min_time = (now + timedelta(hours=min_advance)).strftime("%H:%M")
        result["slots"] = [s for s in result["slots"] if s >= min_time]
        if not result["slots"]:
            result["notes"].append(f"Keine Slots mehr verfügbar (min. {min_advance}h Vorlauf)")
    
    return result


# ============== API ENDPOINTS: SLOT RULES (Admin) ==============

@slots_router.get(
    "/admin/reservation-slot-rules",
    summary="Alle Slot-Regeln abrufen",
    description="Listet alle Slot-Regeln. Admin only."
)
async def list_slot_rules(
    active_only: bool = Query(False),
    current_user: dict = Depends(require_admin)
):
    """GET /api/admin/reservation-slot-rules"""
    query = {"archived": {"$ne": True}}
    if active_only:
        query["active"] = True
    
    rules = await db.reservation_slot_rules.find(
        query, {"_id": 0}
    ).sort("priority", -1).to_list(100)
    
    return rules


@slots_router.post(
    "/admin/reservation-slot-rules",
    status_code=201,
    summary="Neue Slot-Regel erstellen"
)
async def create_slot_rule(
    data: SlotRuleCreate,
    current_user: dict = Depends(require_admin)
):
    """POST /api/admin/reservation-slot-rules"""
    
    rule = {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "valid_from": data.valid_from,
        "valid_to": data.valid_to,
        "applies_days": data.applies_days,
        "generate_between": data.generate_between.model_dump(),  # PFLICHT
        "blocked_windows": [bw.model_dump() for bw in data.blocked_windows],
        "active": data.active,
        "priority": data.priority,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "archived": False
    }
    
    await db.reservation_slot_rules.insert_one(rule)
    
    await create_audit_log(
        actor=current_user,
        action="create",
        entity="slot_rule",
        entity_id=rule["id"],
        after=safe_dict_for_audit(rule)
    )
    
    logger.info(f"Slot-Regel '{data.name}' erstellt von {current_user.get('email')}")
    
    rule.pop("_id", None)
    return rule


@slots_router.patch(
    "/admin/reservation-slot-rules/{rule_id}",
    summary="Slot-Regel aktualisieren"
)
async def update_slot_rule(
    rule_id: str,
    data: SlotRuleUpdate,
    current_user: dict = Depends(require_admin)
):
    """PATCH /api/admin/reservation-slot-rules/{id}"""
    
    rule = await db.reservation_slot_rules.find_one(
        {"id": rule_id, "archived": {"$ne": True}}, {"_id": 0}
    )
    
    if not rule:
        raise NotFoundException("Slot-Regel nicht gefunden")
    
    old_rule = rule.copy()
    update_data = data.model_dump(exclude_unset=True)
    
    if not update_data:
        raise ValidationException("Keine Änderungen übergeben")
    
    # Konvertiere Pydantic-Modelle
    if "generate_between" in update_data and update_data["generate_between"]:
        if isinstance(update_data["generate_between"], GenerateBetween):
            update_data["generate_between"] = update_data["generate_between"].model_dump()
    
    if "blocked_windows" in update_data and update_data["blocked_windows"]:
        update_data["blocked_windows"] = [
            bw.model_dump() if isinstance(bw, BlockedWindow) else bw 
            for bw in update_data["blocked_windows"]
        ]
    
    update_data["updated_at"] = now_iso()
    
    await db.reservation_slot_rules.update_one(
        {"id": rule_id},
        {"$set": update_data}
    )
    
    await create_audit_log(
        actor=current_user,
        action="update",
        entity="slot_rule",
        entity_id=rule_id,
        before=safe_dict_for_audit(old_rule),
        after=safe_dict_for_audit(update_data)
    )
    
    updated = await db.reservation_slot_rules.find_one(
        {"id": rule_id}, {"_id": 0}
    )
    
    return updated


@slots_router.delete(
    "/admin/reservation-slot-rules/{rule_id}",
    status_code=204,
    summary="Slot-Regel löschen"
)
async def delete_slot_rule(
    rule_id: str,
    current_user: dict = Depends(require_admin)
):
    """DELETE /api/admin/reservation-slot-rules/{id}"""
    
    rule = await db.reservation_slot_rules.find_one(
        {"id": rule_id, "archived": {"$ne": True}}
    )
    
    if not rule:
        raise NotFoundException("Slot-Regel nicht gefunden")
    
    await db.reservation_slot_rules.update_one(
        {"id": rule_id},
        {"$set": {"archived": True, "updated_at": now_iso()}}
    )
    
    await create_audit_log(
        actor=current_user,
        action="delete",
        entity="slot_rule",
        entity_id=rule_id
    )
    
    return None


# ============== API ENDPOINTS: SLOT EXCEPTIONS (Admin) ==============

@slots_router.get(
    "/admin/reservation-slot-exceptions",
    summary="Alle Slot-Ausnahmen abrufen"
)
async def list_slot_exceptions(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    current_user: dict = Depends(require_admin)
):
    """GET /api/admin/reservation-slot-exceptions"""
    query = {"archived": {"$ne": True}}
    
    if from_date:
        query["date"] = {"$gte": from_date}
    if to_date:
        if "date" in query:
            query["date"]["$lte"] = to_date
        else:
            query["date"] = {"$lte": to_date}
    
    exceptions = await db.reservation_slot_exceptions.find(
        query, {"_id": 0}
    ).sort("date", 1).to_list(100)
    
    return exceptions


@slots_router.post(
    "/admin/reservation-slot-exceptions",
    status_code=201,
    summary="Neue Slot-Ausnahme erstellen"
)
async def create_slot_exception(
    data: SlotExceptionCreate,
    current_user: dict = Depends(require_admin)
):
    """POST /api/admin/reservation-slot-exceptions"""
    
    # Prüfe ob Ausnahme für Datum existiert
    existing = await db.reservation_slot_exceptions.find_one(
        {"date": data.date, "archived": {"$ne": True}}
    )
    
    if existing:
        raise ConflictException(f"Ausnahme für {data.date} existiert bereits")
    
    exception = {
        "id": str(uuid.uuid4()),
        "date": data.date,
        "allowed_start_times_override": data.allowed_start_times_override,
        "blocked_windows_override": [bw.model_dump() for bw in data.blocked_windows_override] if data.blocked_windows_override else None,
        "reason": data.reason,
        "active": data.active,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "archived": False
    }
    
    await db.reservation_slot_exceptions.insert_one(exception)
    
    await create_audit_log(
        actor=current_user,
        action="create",
        entity="slot_exception",
        entity_id=exception["id"],
        after=safe_dict_for_audit(exception)
    )
    
    logger.info(f"Slot-Ausnahme für {data.date} erstellt von {current_user.get('email')}")
    
    exception.pop("_id", None)
    return exception


@slots_router.patch(
    "/admin/reservation-slot-exceptions/{exception_id}",
    summary="Slot-Ausnahme aktualisieren"
)
async def update_slot_exception(
    exception_id: str,
    data: SlotExceptionUpdate,
    current_user: dict = Depends(require_admin)
):
    """PATCH /api/admin/reservation-slot-exceptions/{id}"""
    
    exception = await db.reservation_slot_exceptions.find_one(
        {"id": exception_id, "archived": {"$ne": True}}, {"_id": 0}
    )
    
    if not exception:
        raise NotFoundException("Slot-Ausnahme nicht gefunden")
    
    old_exception = exception.copy()
    update_data = data.model_dump(exclude_unset=True)
    
    if not update_data:
        raise ValidationException("Keine Änderungen übergeben")
    
    if "blocked_windows_override" in update_data and update_data["blocked_windows_override"]:
        update_data["blocked_windows_override"] = [
            bw.model_dump() if isinstance(bw, BlockedWindow) else bw 
            for bw in update_data["blocked_windows_override"]
        ]
    
    update_data["updated_at"] = now_iso()
    
    await db.reservation_slot_exceptions.update_one(
        {"id": exception_id},
        {"$set": update_data}
    )
    
    await create_audit_log(
        actor=current_user,
        action="update",
        entity="slot_exception",
        entity_id=exception_id,
        before=safe_dict_for_audit(old_exception),
        after=safe_dict_for_audit(update_data)
    )
    
    updated = await db.reservation_slot_exceptions.find_one(
        {"id": exception_id}, {"_id": 0}
    )
    
    return updated


@slots_router.delete(
    "/admin/reservation-slot-exceptions/{exception_id}",
    status_code=204,
    summary="Slot-Ausnahme löschen"
)
async def delete_slot_exception(
    exception_id: str,
    current_user: dict = Depends(require_admin)
):
    """DELETE /api/admin/reservation-slot-exceptions/{id}"""
    
    exception = await db.reservation_slot_exceptions.find_one(
        {"id": exception_id, "archived": {"$ne": True}}
    )
    
    if not exception:
        raise NotFoundException("Slot-Ausnahme nicht gefunden")
    
    await db.reservation_slot_exceptions.update_one(
        {"id": exception_id},
        {"$set": {"archived": True, "updated_at": now_iso()}}
    )
    
    await create_audit_log(
        actor=current_user,
        action="delete",
        entity="slot_exception",
        entity_id=exception_id
    )
    
    return None


# ============== API ENDPOINTS: RESERVATION CONFIG ==============

@slots_router.get(
    "/reservation-config/slots",
    summary="Slot-Konfiguration abrufen"
)
async def get_slot_config(
    current_user: dict = Depends(get_current_user)
):
    """GET /api/reservation-config/slots"""
    config = await get_reservation_config()
    
    return {
        "default_duration_minutes": config.get("default_duration_minutes", 110),
        "buffer_minutes": config.get("buffer_minutes", 10),
        "event_cutoff_minutes_default": config.get("event_cutoff_minutes_default", 120),
        "default_slot_interval": DEFAULT_SLOT_INTERVAL
    }


@slots_router.put(
    "/reservation-config/slots",
    summary="Slot-Konfiguration aktualisieren"
)
async def update_slot_config(
    event_cutoff_minutes_default: Optional[int] = Query(None, ge=30, le=240),
    current_user: dict = Depends(require_admin)
):
    """PUT /api/reservation-config/slots"""
    
    if event_cutoff_minutes_default:
        await db.settings.update_one(
            {"key": "event_cutoff_minutes_default"},
            {"$set": {"value": str(event_cutoff_minutes_default), "updated_at": now_iso()}},
            upsert=True
        )
    
    return await get_slot_config(current_user)
