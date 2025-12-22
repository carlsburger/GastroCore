"""
GastroCore Opening Hours Master Module
================================================================================
Öffnungszeiten-Perioden + Sperrtage (Closures)

Features:
1. Perioden mit Sommer/Winter-Logik und Priority
2. Sperrtage (recurring + one_off)
3. Effective Hours Endpoint für Reservierung & Dienstplan

ADDITIV - Keine Breaking Changes
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, date, timedelta
from enum import Enum
import uuid

# Core imports
from core.database import db
from core.auth import require_admin, require_manager, get_current_user
from core.audit import create_audit_log, safe_dict_for_audit
from core.exceptions import NotFoundException, ValidationException, ConflictException

import logging
logger = logging.getLogger(__name__)


# ============== ROUTER ==============
opening_hours_router = APIRouter(tags=["Opening Hours"])


# ============== ENUMS ==============
class ClosureType(str, Enum):
    RECURRING = "recurring"  # Jährlich wiederkehrend (z.B. 24.12.)
    ONE_OFF = "one_off"      # Einmalig (z.B. 2026-04-15)


class ClosureScope(str, Enum):
    FULL_DAY = "full_day"    # Ganzer Tag geschlossen
    TIME_RANGE = "time_range"  # Nur bestimmte Uhrzeiten


# ============== PYDANTIC MODELS ==============

# --- Time Block für Wochentage ---
class TimeBlock(BaseModel):
    """Einzelner Zeitblock (z.B. 11:30-15:00)"""
    start: str  # HH:MM
    end: str    # HH:MM
    reservable: bool = True  # Kann in diesem Zeitraum reserviert werden?
    label: Optional[str] = None  # z.B. "Mittagsservice", "Abendservice"
    
    @field_validator('start', 'end')
    @classmethod
    def validate_time(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError(f"Ungültiges Zeitformat: {v} (HH:MM erwartet)")
        return v


# --- Wochentag-Regeln ---
class WeekdayRules(BaseModel):
    """Regeln für einen Wochentag"""
    is_closed: bool = False
    blocks: List[TimeBlock] = Field(default_factory=list)


# --- Opening Hours Period ---
class OpeningHoursPeriodCreate(BaseModel):
    """Neue Öffnungszeiten-Periode erstellen"""
    name: str = Field(..., min_length=2, max_length=100)  # z.B. "Sommer 2026"
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    rules_by_weekday: Dict[str, WeekdayRules] = Field(default_factory=dict)
    # Keys: monday, tuesday, wednesday, thursday, friday, saturday, sunday
    active: bool = True
    priority: int = Field(default=0, ge=0, le=100)  # Höhere Priority gewinnt bei Überlappung
    
    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Ungültiges Datumsformat: {v} (YYYY-MM-DD erwartet)")
        return v


class OpeningHoursPeriodUpdate(BaseModel):
    """Periode aktualisieren"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    rules_by_weekday: Optional[Dict[str, WeekdayRules]] = None
    active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=100)


# --- Closure (Sperrtag) ---
class RecurringRule(BaseModel):
    """Regel für jährlich wiederkehrende Sperrtage"""
    month: int = Field(..., ge=1, le=12)
    day: int = Field(..., ge=1, le=31)


class OneOffRule(BaseModel):
    """Regel für einmalige Sperrung"""
    date: str  # YYYY-MM-DD
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Ungültiges Datumsformat: {v}")
        return v


class ClosureCreate(BaseModel):
    """Neuen Sperrtag erstellen"""
    type: ClosureType
    recurring_rule: Optional[RecurringRule] = None  # Für type=recurring
    one_off_rule: Optional[OneOffRule] = None       # Für type=one_off
    scope: ClosureScope = ClosureScope.FULL_DAY
    start_time: Optional[str] = None  # HH:MM für scope=time_range
    end_time: Optional[str] = None    # HH:MM für scope=time_range
    reason: str = Field(..., min_length=2, max_length=200)
    active: bool = True
    
    @field_validator('start_time', 'end_time')
    @classmethod
    def validate_time(cls, v):
        if v:
            try:
                datetime.strptime(v, "%H:%M")
            except ValueError:
                raise ValueError(f"Ungültiges Zeitformat: {v}")
        return v


class ClosureUpdate(BaseModel):
    """Sperrtag aktualisieren"""
    scope: Optional[ClosureScope] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    reason: Optional[str] = Field(None, min_length=2, max_length=200)
    active: Optional[bool] = None


# ============== HELPER FUNCTIONS ==============

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def weekday_name(day_num: int) -> str:
    """Wochentag-Nummer zu Name (0=monday)"""
    names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    return names[day_num]


def weekday_name_de(day_num: int) -> str:
    """Wochentag-Nummer zu deutschem Name"""
    names = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    return names[day_num]


async def get_active_period_for_date(target_date: date) -> Optional[dict]:
    """
    Finde die aktive Periode für ein Datum.
    Bei Überlappung gewinnt höhere Priority.
    """
    date_str = target_date.strftime("%Y-%m-%d")
    
    # Alle aktiven Perioden laden
    periods = await db.opening_hours_master.find(
        {"active": True, "archived": {"$ne": True}}
    ).to_list(100)
    
    matching = []
    for period in periods:
        start = datetime.strptime(period["start_date"], "%Y-%m-%d").date()
        end = datetime.strptime(period["end_date"], "%Y-%m-%d").date()
        
        if start <= target_date <= end:
            matching.append(period)
    
    if not matching:
        return None
    
    # Sortiere nach Priority (höchste zuerst)
    matching.sort(key=lambda x: x.get("priority", 0), reverse=True)
    return matching[0]


async def get_closures_for_date(target_date: date) -> List[dict]:
    """
    Finde alle aktiven Sperrtage für ein Datum.
    Prüft sowohl recurring als auch one_off.
    """
    date_str = target_date.strftime("%Y-%m-%d")
    month = target_date.month
    day = target_date.day
    
    closures = await db.closures.find(
        {"active": True, "archived": {"$ne": True}}
    ).to_list(100)
    
    matching = []
    for closure in closures:
        if closure["type"] == "recurring":
            rule = closure.get("recurring_rule", {})
            if rule.get("month") == month and rule.get("day") == day:
                matching.append(closure)
        elif closure["type"] == "one_off":
            rule = closure.get("one_off_rule", {})
            if rule.get("date") == date_str:
                matching.append(closure)
    
    return matching


async def calculate_effective_hours(target_date: date) -> dict:
    """
    Berechne die effektiven Öffnungszeiten für ein Datum.
    Kombiniert Periode + Sperrtage.
    """
    date_str = target_date.strftime("%Y-%m-%d")
    weekday = target_date.weekday()
    weekday_key = weekday_name(weekday)
    
    result = {
        "date": date_str,
        "weekday": weekday_key,
        "weekday_de": weekday_name_de(weekday),
        "is_open": True,
        "is_closed_full_day": False,
        "closure_reason": None,
        "period_name": None,
        "blocks": [],
        "closures": []
    }
    
    # 1. Sperrtage prüfen
    closures = await get_closures_for_date(target_date)
    full_day_closure = None
    time_range_closures = []
    
    for c in closures:
        closure_info = {
            "id": c["id"],
            "reason": c.get("reason", ""),
            "scope": c.get("scope", "full_day"),
            "type": c.get("type", "one_off")
        }
        if c.get("scope") == "time_range":
            closure_info["start_time"] = c.get("start_time")
            closure_info["end_time"] = c.get("end_time")
            time_range_closures.append(closure_info)
        else:
            full_day_closure = closure_info
        result["closures"].append(closure_info)
    
    # Wenn ganztägig geschlossen
    if full_day_closure:
        result["is_open"] = False
        result["is_closed_full_day"] = True
        result["closure_reason"] = full_day_closure["reason"]
        return result
    
    # 2. Periode laden
    period = await get_active_period_for_date(target_date)
    
    if period:
        result["period_name"] = period.get("name")
        rules = period.get("rules_by_weekday", {})
        day_rules = rules.get(weekday_key, {})
        
        if day_rules.get("is_closed", False):
            result["is_open"] = False
            result["is_closed_full_day"] = True
            result["closure_reason"] = "Ruhetag"
            return result
        
        # Zeitblöcke übernehmen
        blocks = day_rules.get("blocks", [])
        for block in blocks:
            block_info = {
                "start": block.get("start"),
                "end": block.get("end"),
                "reservable": block.get("reservable", True),
                "label": block.get("label")
            }
            result["blocks"].append(block_info)
    else:
        # Fallback: Standard-Öffnungszeiten
        result["period_name"] = "Standard"
        result["blocks"] = [
            {"start": "11:00", "end": "22:00", "reservable": True, "label": "Ganztags"}
        ]
    
    # 3. Zeit-Sperren auf Blöcke anwenden
    if time_range_closures:
        # Markiere betroffene Zeiten als nicht reservierbar
        for closure in time_range_closures:
            closure_start = closure.get("start_time", "00:00")
            closure_end = closure.get("end_time", "23:59")
            
            new_blocks = []
            for block in result["blocks"]:
                # Prüfe Überlappung
                block_start = block["start"]
                block_end = block["end"]
                
                if block_end <= closure_start or block_start >= closure_end:
                    # Keine Überlappung
                    new_blocks.append(block)
                elif block_start >= closure_start and block_end <= closure_end:
                    # Block komplett in Sperrzeit -> entfernen/markieren
                    block["reservable"] = False
                    block["closure_reason"] = closure.get("reason")
                    new_blocks.append(block)
                else:
                    # Teilweise Überlappung -> Block aufteilen
                    if block_start < closure_start:
                        new_blocks.append({
                            "start": block_start,
                            "end": closure_start,
                            "reservable": block.get("reservable", True),
                            "label": block.get("label")
                        })
                    if block_end > closure_end:
                        new_blocks.append({
                            "start": closure_end,
                            "end": block_end,
                            "reservable": block.get("reservable", True),
                            "label": block.get("label")
                        })
            
            result["blocks"] = new_blocks
    
    # Prüfe ob noch offene Zeiten vorhanden
    has_open_blocks = any(b.get("reservable", True) for b in result["blocks"])
    if not has_open_blocks and result["blocks"]:
        result["is_open"] = False
    
    return result


# ============== API ENDPOINTS: PERIODS ==============

@opening_hours_router.get(
    "/opening-hours/periods",
    summary="Alle Öffnungszeiten-Perioden abrufen",
    description="Listet alle Perioden (Sommer, Winter, etc.). Admin only."
)
async def list_periods(
    active_only: bool = Query(False, description="Nur aktive Perioden"),
    current_user: dict = Depends(require_admin)
):
    """GET /api/opening-hours/periods"""
    query = {"archived": {"$ne": True}}
    if active_only:
        query["active"] = True
    
    periods = await db.opening_hours_master.find(
        query,
        {"_id": 0}
    ).sort("start_date", -1).to_list(100)
    
    return periods


@opening_hours_router.post(
    "/opening-hours/periods",
    status_code=201,
    summary="Neue Öffnungszeiten-Periode erstellen",
    description="Erstellt eine neue Periode (z.B. Sommer 2026). Admin only."
)
async def create_period(
    data: OpeningHoursPeriodCreate,
    current_user: dict = Depends(require_admin)
):
    """POST /api/opening-hours/periods"""
    
    # Validiere Datumsbereich
    start = datetime.strptime(data.start_date, "%Y-%m-%d").date()
    end = datetime.strptime(data.end_date, "%Y-%m-%d").date()
    
    if end < start:
        raise ValidationException("Enddatum muss nach Startdatum liegen")
    
    # Konvertiere rules_by_weekday zu dict
    rules_dict = {}
    for day_name, rules in data.rules_by_weekday.items():
        if isinstance(rules, WeekdayRules):
            rules_dict[day_name] = {
                "is_closed": rules.is_closed,
                "blocks": [b.model_dump() for b in rules.blocks]
            }
        else:
            rules_dict[day_name] = rules
    
    period = {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "rules_by_weekday": rules_dict,
        "active": data.active,
        "priority": data.priority,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "archived": False
    }
    
    await db.opening_hours_master.insert_one(period)
    
    # Audit Log
    await create_audit_log(
        actor=current_user,
        action="create",
        entity="opening_hours_period",
        entity_id=period["id"],
        new_values=safe_dict_for_audit(period)
    )
    
    logger.info(f"Öffnungszeiten-Periode '{data.name}' erstellt von {current_user.get('email')}")
    
    # Entferne _id für Response
    period.pop("_id", None)
    return period


@opening_hours_router.patch(
    "/opening-hours/periods/{period_id}",
    summary="Öffnungszeiten-Periode aktualisieren",
    description="Aktualisiert eine bestehende Periode. Admin only."
)
async def update_period(
    period_id: str,
    data: OpeningHoursPeriodUpdate,
    current_user: dict = Depends(require_admin)
):
    """PATCH /api/opening-hours/periods/{id}"""
    
    period = await db.opening_hours_master.find_one(
        {"id": period_id, "archived": {"$ne": True}},
        {"_id": 0}
    )
    
    if not period:
        raise NotFoundException("Periode nicht gefunden")
    
    old_period = period.copy()
    update_data = data.model_dump(exclude_unset=True)
    
    if not update_data:
        raise ValidationException("Keine Änderungen übergeben")
    
    # Konvertiere rules_by_weekday falls vorhanden
    if "rules_by_weekday" in update_data and update_data["rules_by_weekday"]:
        rules_dict = {}
        for day_name, rules in update_data["rules_by_weekday"].items():
            if isinstance(rules, WeekdayRules):
                rules_dict[day_name] = {
                    "is_closed": rules.is_closed,
                    "blocks": [b.model_dump() for b in rules.blocks]
                }
            elif isinstance(rules, dict):
                rules_dict[day_name] = rules
        update_data["rules_by_weekday"] = rules_dict
    
    update_data["updated_at"] = now_iso()
    
    await db.opening_hours_master.update_one(
        {"id": period_id},
        {"$set": update_data}
    )
    
    # Audit Log
    await create_audit_log(
        actor=current_user,
        action="update",
        entity="opening_hours_period",
        entity_id=period_id,
        old_values=safe_dict_for_audit(old_period),
        new_values=safe_dict_for_audit(update_data)
    )
    
    updated = await db.opening_hours_master.find_one(
        {"id": period_id},
        {"_id": 0}
    )
    
    logger.info(f"Periode '{period_id}' aktualisiert von {current_user.get('email')}")
    return updated


@opening_hours_router.delete(
    "/opening-hours/periods/{period_id}",
    status_code=204,
    summary="Öffnungszeiten-Periode löschen",
    description="Soft Delete einer Periode. Admin only."
)
async def delete_period(
    period_id: str,
    current_user: dict = Depends(require_admin)
):
    """DELETE /api/opening-hours/periods/{id}"""
    
    period = await db.opening_hours_master.find_one(
        {"id": period_id, "archived": {"$ne": True}}
    )
    
    if not period:
        raise NotFoundException("Periode nicht gefunden")
    
    await db.opening_hours_master.update_one(
        {"id": period_id},
        {"$set": {"archived": True, "updated_at": now_iso()}}
    )
    
    # Audit Log
    await create_audit_log(
        actor=current_user,
        action="delete",
        entity="opening_hours_period",
        entity_id=period_id
    )
    
    logger.info(f"Periode '{period_id}' gelöscht von {current_user.get('email')}")
    return None


# ============== API ENDPOINTS: CLOSURES ==============

@opening_hours_router.get(
    "/closures",
    summary="Alle Sperrtage abrufen",
    description="Listet alle Sperrtage (recurring + one_off). Admin only."
)
async def list_closures(
    active_only: bool = Query(False, description="Nur aktive Sperrtage"),
    type_filter: Optional[ClosureType] = Query(None, description="Nach Typ filtern"),
    current_user: dict = Depends(require_admin)
):
    """GET /api/closures"""
    query = {"archived": {"$ne": True}}
    if active_only:
        query["active"] = True
    if type_filter:
        query["type"] = type_filter.value
    
    closures = await db.closures.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    
    return closures


@opening_hours_router.post(
    "/closures",
    status_code=201,
    summary="Neuen Sperrtag erstellen",
    description="Erstellt einen neuen Sperrtag (recurring oder one_off). Admin only."
)
async def create_closure(
    data: ClosureCreate,
    current_user: dict = Depends(require_admin)
):
    """POST /api/closures"""
    
    # Validierung: Je nach Typ müssen unterschiedliche Felder gesetzt sein
    if data.type == ClosureType.RECURRING:
        if not data.recurring_rule:
            raise ValidationException("Für recurring-Sperrtage muss recurring_rule angegeben werden")
    elif data.type == ClosureType.ONE_OFF:
        if not data.one_off_rule:
            raise ValidationException("Für one_off-Sperrtage muss one_off_rule angegeben werden")
    
    # Validierung: Bei time_range müssen Zeiten angegeben sein
    if data.scope == ClosureScope.TIME_RANGE:
        if not data.start_time or not data.end_time:
            raise ValidationException("Für time_range-Scope müssen start_time und end_time angegeben werden")
    
    closure = {
        "id": str(uuid.uuid4()),
        "type": data.type.value,
        "recurring_rule": data.recurring_rule.model_dump() if data.recurring_rule else None,
        "one_off_rule": data.one_off_rule.model_dump() if data.one_off_rule else None,
        "scope": data.scope.value,
        "start_time": data.start_time,
        "end_time": data.end_time,
        "reason": data.reason,
        "active": data.active,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "archived": False
    }
    
    await db.closures.insert_one(closure)
    
    # Audit Log
    await create_audit_log(
        actor=current_user,
        action="create",
        entity="closure",
        entity_id=closure["id"],
        new_values=safe_dict_for_audit(closure)
    )
    
    logger.info(f"Sperrtag '{data.reason}' erstellt von {current_user.get('email')}")
    
    closure.pop("_id", None)
    return closure


@opening_hours_router.patch(
    "/closures/{closure_id}",
    summary="Sperrtag aktualisieren",
    description="Aktualisiert einen bestehenden Sperrtag. Admin only."
)
async def update_closure(
    closure_id: str,
    data: ClosureUpdate,
    current_user: dict = Depends(require_admin)
):
    """PATCH /api/closures/{id}"""
    
    closure = await db.closures.find_one(
        {"id": closure_id, "archived": {"$ne": True}},
        {"_id": 0}
    )
    
    if not closure:
        raise NotFoundException("Sperrtag nicht gefunden")
    
    old_closure = closure.copy()
    update_data = data.model_dump(exclude_unset=True)
    
    if not update_data:
        raise ValidationException("Keine Änderungen übergeben")
    
    update_data["updated_at"] = now_iso()
    
    await db.closures.update_one(
        {"id": closure_id},
        {"$set": update_data}
    )
    
    # Audit Log
    await create_audit_log(
        actor=current_user,
        action="update",
        entity="closure",
        entity_id=closure_id,
        old_values=safe_dict_for_audit(old_closure),
        new_values=safe_dict_for_audit(update_data)
    )
    
    updated = await db.closures.find_one(
        {"id": closure_id},
        {"_id": 0}
    )
    
    logger.info(f"Sperrtag '{closure_id}' aktualisiert von {current_user.get('email')}")
    return updated


@opening_hours_router.delete(
    "/closures/{closure_id}",
    status_code=204,
    summary="Sperrtag löschen",
    description="Soft Delete eines Sperrtags. Admin only."
)
async def delete_closure(
    closure_id: str,
    current_user: dict = Depends(require_admin)
):
    """DELETE /api/closures/{id}"""
    
    closure = await db.closures.find_one(
        {"id": closure_id, "archived": {"$ne": True}}
    )
    
    if not closure:
        raise NotFoundException("Sperrtag nicht gefunden")
    
    await db.closures.update_one(
        {"id": closure_id},
        {"$set": {"archived": True, "updated_at": now_iso()}}
    )
    
    # Audit Log
    await create_audit_log(
        actor=current_user,
        action="delete",
        entity="closure",
        entity_id=closure_id
    )
    
    logger.info(f"Sperrtag '{closure_id}' gelöscht von {current_user.get('email')}")
    return None


# ============== API ENDPOINTS: EFFECTIVE HOURS ==============

@opening_hours_router.get(
    "/opening-hours/effective",
    summary="Effektive Öffnungszeiten für Zeitraum",
    description="Berechnet die tatsächlichen Öffnungszeiten inkl. Sperrtage. Für Reservierung & Dienstplan."
)
async def get_effective_hours(
    from_date: str = Query(..., alias="from", description="Startdatum (YYYY-MM-DD)"),
    to_date: str = Query(..., alias="to", description="Enddatum (YYYY-MM-DD)"),
    current_user: dict = Depends(require_manager)
):
    """GET /api/opening-hours/effective?from=YYYY-MM-DD&to=YYYY-MM-DD"""
    
    try:
        start = datetime.strptime(from_date, "%Y-%m-%d").date()
        end = datetime.strptime(to_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationException("Ungültiges Datumsformat (YYYY-MM-DD erwartet)")
    
    if end < start:
        raise ValidationException("Enddatum muss nach Startdatum liegen")
    
    # Maximal 60 Tage
    if (end - start).days > 60:
        raise ValidationException("Maximaler Zeitraum: 60 Tage")
    
    results = []
    current = start
    
    while current <= end:
        effective = await calculate_effective_hours(current)
        results.append(effective)
        current += timedelta(days=1)
    
    return {
        "from": from_date,
        "to": to_date,
        "days": results
    }


# ============== PUBLIC HELPER FUNCTIONS ==============

async def is_date_closed(target_date: date) -> tuple:
    """
    Prüft ob ein Datum geschlossen ist.
    Returns: (is_closed: bool, reason: str or None)
    """
    effective = await calculate_effective_hours(target_date)
    
    if effective["is_closed_full_day"]:
        return True, effective.get("closure_reason")
    
    return False, None


async def get_reservable_slots_for_date(target_date: date) -> List[dict]:
    """
    Hole alle reservierbaren Zeitslots für ein Datum.
    Berücksichtigt Perioden + Sperrtage.
    """
    effective = await calculate_effective_hours(target_date)
    
    if not effective["is_open"]:
        return []
    
    reservable_blocks = [
        b for b in effective.get("blocks", [])
        if b.get("reservable", True)
    ]
    
    return reservable_blocks
