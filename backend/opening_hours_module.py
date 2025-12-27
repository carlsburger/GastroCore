"""
GastroCore Opening Hours Master Module
================================================================================
Öffnungszeiten-Perioden + Sperrtage (Closures) + Feiertage (Holidays)

Features:
1. Perioden mit Sommer/Winter-Logik und Priority
2. Sperrtage (recurring + one_off)
3. Feiertage mit Override (z.B. Mo/Di normalerweise zu, aber Feiertag offen)
4. Effective Hours Endpoint für Reservierung & Dienstplan

Prioritäten (höchste zuerst):
1. closures (ganztags geschlossen)
2. holidays (können Ruhetag überschreiben → offen)
3. opening_hours_periods
4. Fallback: geschlossen

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


# ============== BRANDENBURG FEIERTAGE ==============
# Gesetzliche Feiertage für Brandenburg (Region BB)
BRANDENBURG_HOLIDAYS = {
    # Feste Feiertage (MM-DD)
    "01-01": "Neujahr",
    "05-01": "Tag der Arbeit",
    "10-03": "Tag der Deutschen Einheit",
    "10-31": "Reformationstag",  # Brandenburg-spezifisch
    "12-25": "1. Weihnachtsfeiertag",
    "12-26": "2. Weihnachtsfeiertag",
}

# Bewegliche Feiertage werden dynamisch berechnet (Ostern-basiert)
def calculate_easter(year: int) -> date:
    """Berechne Ostersonntag nach Gauß-Algorithmus"""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def get_moveable_holidays(year: int) -> Dict[str, str]:
    """Berechne bewegliche Feiertage für ein Jahr"""
    easter = calculate_easter(year)
    return {
        (easter - timedelta(days=2)).strftime("%Y-%m-%d"): "Karfreitag",
        (easter + timedelta(days=1)).strftime("%Y-%m-%d"): "Ostermontag",
        (easter + timedelta(days=39)).strftime("%Y-%m-%d"): "Christi Himmelfahrt",
        (easter + timedelta(days=50)).strftime("%Y-%m-%d"): "Pfingstmontag",
    }


def is_holiday_brandenburg(target_date: date) -> tuple:
    """
    Prüft ob ein Datum ein Feiertag in Brandenburg ist.
    Returns: (is_holiday: bool, holiday_name: str or None)
    """
    # Feste Feiertage prüfen
    mm_dd = target_date.strftime("%m-%d")
    if mm_dd in BRANDENBURG_HOLIDAYS:
        return True, BRANDENBURG_HOLIDAYS[mm_dd]
    
    # Bewegliche Feiertage prüfen
    moveable = get_moveable_holidays(target_date.year)
    date_str = target_date.strftime("%Y-%m-%d")
    if date_str in moveable:
        return True, moveable[date_str]
    
    return False, None


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


# --- Neues einfaches Closure-Modell mit Datumsbereich ---
class SimpleClosure(BaseModel):
    """Einfacher Sperrtag/Override mit Datumsbereich - HÖCHSTE PRIORITÄT"""
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD (default = start_date für Einzeltag)
    type: str = Field(default="closed_all_day", pattern="^(closed_all_day|closed_partial)$")
    start_time: Optional[str] = None  # HH:MM nur bei closed_partial
    end_time: Optional[str] = None    # HH:MM nur bei closed_partial
    reason: str = Field(..., min_length=2, max_length=200)
    
    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Ungültiges Datumsformat: {v} (YYYY-MM-DD erwartet)")
        return v
    
    @field_validator('start_time', 'end_time')
    @classmethod
    def validate_time(cls, v):
        if v:
            try:
                datetime.strptime(v, "%H:%M")
            except ValueError:
                raise ValueError(f"Ungültiges Zeitformat: {v} (HH:MM erwartet)")
        return v


# --- NEUES Override-Modell (kann OFFEN oder GESCHLOSSEN sein) ---
class OpeningOverrideCreate(BaseModel):
    """
    Override für einzelne Tage oder Zeiträume.
    HÖCHSTE PRIORITÄT - überschreibt Perioden UND Feiertage.
    
    status = "closed": Tag komplett geschlossen
    status = "open": Tag offen mit angegebenen Zeiten
    """
    date_from: str  # YYYY-MM-DD
    date_to: Optional[str] = None  # YYYY-MM-DD (default = date_from)
    status: str = Field(default="closed", pattern="^(closed|open)$")
    open_from: Optional[str] = None  # HH:MM wenn status=open
    open_to: Optional[str] = None    # HH:MM wenn status=open
    last_reservation_time: Optional[str] = None  # HH:MM optional
    note: str = Field(..., min_length=2, max_length=300)
    priority: int = Field(default=100, ge=0, le=1000)  # Höhere Priority gewinnt
    
    @field_validator('date_from', 'date_to')
    @classmethod
    def validate_date(cls, v):
        if v:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Ungültiges Datumsformat: {v} (YYYY-MM-DD erwartet)")
        return v
    
    @field_validator('open_from', 'open_to', 'last_reservation_time')
    @classmethod
    def validate_time(cls, v):
        if v:
            try:
                datetime.strptime(v, "%H:%M")
            except ValueError:
                raise ValueError(f"Ungültiges Zeitformat: {v} (HH:MM erwartet)")
        return v


class OpeningOverrideUpdate(BaseModel):
    """Update für Override"""
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(closed|open)$")
    open_from: Optional[str] = None
    open_to: Optional[str] = None
    last_reservation_time: Optional[str] = None
    note: Optional[str] = Field(None, min_length=2, max_length=300)
    priority: Optional[int] = Field(None, ge=0, le=1000)
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
    Unterstützt:
    - Feste Datumsbereiche (start_date/end_date im Format YYYY-MM-DD)
    - Wiederkehrende Saisons (start_month_day/end_month_day im Format MM-DD)
    Bei Überlappung gewinnt höhere Priority.
    """
    date_str = target_date.strftime("%Y-%m-%d")
    month_day = target_date.strftime("%m-%d")
    
    # Alle aktiven Perioden laden
    periods = await db.opening_hours_master.find(
        {"active": True, "archived": {"$ne": True}}
    ).to_list(100)
    
    matching = []
    for period in periods:
        # Variante 1: Wiederkehrende Saison (MM-DD Format)
        if period.get("start_month_day") and period.get("end_month_day"):
            start_md = period["start_month_day"]
            end_md = period["end_month_day"]
            
            # Prüfe ob Datum in Saison fällt
            if start_md <= end_md:
                # Normale Saison (z.B. 04-01 bis 10-31)
                if start_md <= month_day <= end_md:
                    matching.append(period)
            else:
                # Saison über Jahreswechsel (z.B. 11-01 bis 03-31)
                if month_day >= start_md or month_day <= end_md:
                    matching.append(period)
        
        # Variante 2: Feste Datumsbereich (YYYY-MM-DD)
        elif period.get("start_date") and period.get("end_date"):
            start = period["start_date"]
            end = period["end_date"]
            if start <= date_str <= end:
                matching.append(period)
    
    if not matching:
        return None
    
    # Sortiere nach Priority (höchste zuerst)
    matching.sort(key=lambda x: x.get("priority", 0), reverse=True)
    return matching[0]


async def get_special_day_for_date(target_date: date) -> Optional[dict]:
    """
    Prüfe ob ein fester Sondertag (z.B. 24.12, 01.01, 31.12) vorliegt.
    Sondertage haben höchste Priorität über Saisons.
    """
    month_day = target_date.strftime("%m-%d")
    
    special_day = await db.special_days.find_one({
        "month_day": month_day,
        "active": True
    })
    
    return special_day


async def get_closures_for_date(target_date: date) -> List[dict]:
    """
    Finde alle aktiven Sperrtage für ein Datum.
    Prüft:
    1. Einfache Datumsbereiche (start_date/end_date) - HÖCHSTE PRIORITÄT
    2. Recurring (jährlich wiederkehrend)
    3. One-off (einmalig mit one_off_rule)
    
    Bei Überlappung: closed_all_day > closed_partial
    """
    date_str = target_date.strftime("%Y-%m-%d")
    month = target_date.month
    day = target_date.day
    
    closures = await db.closures.find(
        {"active": True, "archived": {"$ne": True}}
    ).to_list(200)
    
    matching = []
    for closure in closures:
        closure_type = closure.get("type", "")
        
        # 1. Neues Format: Datumsbereich (start_date/end_date)
        if closure.get("start_date") and closure.get("end_date"):
            start = closure["start_date"]
            end = closure["end_date"]
            if start <= date_str <= end:
                # Priorität basierend auf Typ
                priority = 100 if closure_type == "closed_all_day" else 50
                closure["_match_priority"] = priority
                matching.append(closure)
        
        # 2. Legacy: Recurring (jährlich)
        elif closure_type == "recurring":
            rule = closure.get("recurring_rule", {})
            if rule.get("month") == month and rule.get("day") == day:
                closure["_match_priority"] = 90
                matching.append(closure)
        
        # 3. Legacy: One-off (einmalig)
        elif closure_type == "one_off":
            rule = closure.get("one_off_rule", {})
            if rule.get("date") == date_str:
                closure["_match_priority"] = 80
                matching.append(closure)
    
    # Sortiere: closed_all_day vor closed_partial, dann nach Priority
    matching.sort(key=lambda x: x.get("_match_priority", 0), reverse=True)
    
    return matching


async def calculate_effective_hours(target_date: date) -> dict:
    """
    Berechne die effektiven Öffnungszeiten für ein Datum.
    
    Prioritäten (höchste zuerst):
    0. opening_overrides (ABSOLUT HÖCHSTE PRIORITÄT - auch über Closures!)
    1. closures (ganztags geschlossen)
    2. holidays (können Ruhetag überschreiben → offen 11:30-20:00)
    3. opening_hours_periods (Sommer/Winter Regelwerk)
    4. Fallback: Standard-Öffnungszeiten
    """
    date_str = target_date.strftime("%Y-%m-%d")
    weekday = target_date.weekday()
    weekday_key = weekday_name(weekday)
    
    # Feiertag prüfen
    is_holiday, holiday_name = is_holiday_brandenburg(target_date)
    
    result = {
        "date": date_str,
        "weekday": weekday_key,
        "weekday_de": weekday_name_de(weekday),
        "is_open": True,
        "is_closed_full_day": False,
        "closure_reason": None,
        "period_name": None,
        "is_holiday": is_holiday,
        "holiday_name": holiday_name,
        "blocks": [],
        "closures": [],
        "last_reservation_time": None,
        "override_note": None
    }
    
    # ========== 0. OPENING OVERRIDES (ABSOLUT HÖCHSTE PRIORITÄT) ==========
    override = await get_override_for_date(target_date)
    if override:
        if override.get("status") == "closed":
            result["is_open"] = False
            result["is_closed_full_day"] = True
            result["closure_reason"] = override.get("note", "Override: Geschlossen")
            result["override_note"] = override.get("note")
            logger.info(f"Override CLOSED für {date_str}: {override.get('note')}")
            return result
        
        elif override.get("status") == "open":
            result["is_open"] = True
            result["is_closed_full_day"] = False
            open_from = override.get("open_from", "11:30")
            open_to = override.get("open_to", "20:00")
            result["blocks"] = [
                {"start": open_from, "end": open_to, "reservable": True, "label": override.get("note", "Override")}
            ]
            result["last_reservation_time"] = override.get("last_reservation_time")
            result["override_note"] = override.get("note")
            result["period_name"] = "Override"
            logger.info(f"Override OPEN für {date_str}: {open_from}-{open_to}")
            return result
    
    # ========== 1. CLOSURES (SPERRTAGE) ==========
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
    
    # Wenn ganztägig geschlossen (Sperrtag hat Vorrang)
    if full_day_closure:
        result["is_open"] = False
        result["is_closed_full_day"] = True
        result["closure_reason"] = full_day_closure["reason"]
        return result
    
    # ========== 1.5 FESTE SONDERTAGE (Priorität über Saisons) ==========
    special_day = await get_special_day_for_date(target_date)
    if special_day:
        if special_day.get("is_closed"):
            result["is_open"] = False
            result["is_closed_full_day"] = True
            result["closure_reason"] = special_day.get("reason", special_day.get("name", "Sondertag"))
            result["period_name"] = special_day.get("name")
            return result
        else:
            # Sonderöffnung
            result["is_open"] = True
            result["is_closed_full_day"] = False
            result["blocks"] = [{
                "start": special_day.get("opening_time", "12:00"),
                "end": special_day.get("closing_time", "16:00"),
                "reservable": True,
                "label": special_day.get("name", "Sonderöffnung")
            }]
            result["period_name"] = special_day.get("name")
            return result
    
    # ========== 2. FEIERTAGE ==========
    # NEU: Feiertage ändern NICHTS automatisch
    # Ruhetag bleibt Ruhetag, Öffnungszeiten bleiben gleich
    # Sonderöffnungen nur via Event/Override oder special_days
    # (is_holiday Flag wird trotzdem gesetzt für Info-Zwecke)
    
    # ========== 3. PERIODEN (Saisons) ==========
    period = await get_active_period_for_date(target_date)
    
    if period:
        result["period_name"] = period.get("name")
        rules = period.get("rules_by_weekday", {})
        day_rules = rules.get(weekday_key, {})
        
        # Prüfe ob Ruhetag (Feiertage wurden bereits oben behandelt)
        if day_rules.get("is_closed", False):
            # Normaler Ruhetag
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
        after=safe_dict_for_audit(period)
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
        before=safe_dict_for_audit(old_period),
        after=safe_dict_for_audit(update_data)
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
        after=safe_dict_for_audit(closure)
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
        before=safe_dict_for_audit(old_closure),
        after=safe_dict_for_audit(update_data)
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


# ============== API ENDPOINTS: SIMPLE CLOSURES (Datumsbereich) ==============

@opening_hours_router.post(
    "/opening-hours/closures",
    status_code=201,
    summary="Einfachen Sperrtag/Override erstellen",
    description="Erstellt einen Sperrtag mit Datumsbereich. Höchste Priorität - überschreibt alle Perioden."
)
async def create_simple_closure(
    data: SimpleClosure,
    current_user: dict = Depends(require_admin)
):
    """POST /api/opening-hours/closures - Einfacher Sperrtag mit start_date/end_date"""
    
    # Validierung
    if data.type == "closed_partial":
        if not data.start_time or not data.end_time:
            raise ValidationException("Bei teilweiser Sperrung müssen start_time und end_time angegeben werden")
    
    # End-Datum default auf Start-Datum
    end_date = data.end_date if data.end_date else data.start_date
    
    closure = {
        "id": str(uuid.uuid4()),
        "start_date": data.start_date,
        "end_date": end_date,
        "type": data.type,
        "scope": "full_day" if data.type == "closed_all_day" else "time_range",
        "start_time": data.start_time,
        "end_time": data.end_time,
        "reason": data.reason,
        "active": True,
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
        after=safe_dict_for_audit(closure)
    )
    
    date_range = f"{data.start_date}" if data.start_date == end_date else f"{data.start_date} bis {end_date}"
    logger.info(f"Sperrtag '{data.reason}' ({date_range}) erstellt von {current_user.get('email')}")
    
    closure.pop("_id", None)
    return closure


@opening_hours_router.get(
    "/opening-hours/closures",
    summary="Sperrtage für Zeitraum abrufen",
    description="Listet alle Sperrtage, optional gefiltert nach Zeitraum."
)
async def get_simple_closures(
    from_date: Optional[str] = Query(None, alias="from", description="Startdatum (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, alias="to", description="Enddatum (YYYY-MM-DD)"),
    current_user: dict = Depends(require_manager)
):
    """GET /api/opening-hours/closures?from=...&to=..."""
    
    query = {"archived": {"$ne": True}}
    
    # Alle Closures laden
    closures = await db.closures.find(query, {"_id": 0}).sort("start_date", 1).to_list(500)
    
    # Wenn Zeitraum angegeben, filtern
    if from_date and to_date:
        filtered = []
        for c in closures:
            c_start = c.get("start_date") or c.get("one_off_rule", {}).get("date", "")
            c_end = c.get("end_date", c_start)
            
            # Überlappung prüfen
            if c_start and c_end:
                if c_start <= to_date and c_end >= from_date:
                    filtered.append(c)
            elif c_start:
                if from_date <= c_start <= to_date:
                    filtered.append(c)
        return filtered
    
    return closures


@opening_hours_router.delete(
    "/opening-hours/closures/{closure_id}",
    status_code=204,
    summary="Sperrtag löschen",
    description="Soft Delete eines Sperrtags. Admin only."
)
async def delete_simple_closure(
    closure_id: str,
    current_user: dict = Depends(require_admin)
):
    """DELETE /api/opening-hours/closures/{id}"""
    
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


# ============== API ENDPOINTS: getDayStatus HELPER ==============

@opening_hours_router.get(
    "/opening-hours/day-status/{date_str}",
    summary="Tagesstatus für ein Datum",
    description="Prüft ob ein Tag offen/geschlossen ist und warum. Für Quick-Checks."
)
async def get_day_status(
    date_str: str,
    current_user: dict = Depends(require_manager)
):
    """
    GET /api/opening-hours/day-status/2026-01-02
    
    Returns:
    - isClosed: bool
    - isPartialClosed: bool
    - openingWindow: { start, end } oder null
    - reason: string oder null
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationException("Ungültiges Datumsformat (YYYY-MM-DD erwartet)")
    
    # 1. HÖCHSTE PRIORITÄT: Closures prüfen
    closures = await get_closures_for_date(target_date)
    
    for closure in closures:
        closure_type = closure.get("type", "")
        scope = closure.get("scope", "full_day")
        
        # closed_all_day hat höchste Priorität
        if closure_type == "closed_all_day" or scope == "full_day":
            return {
                "date": date_str,
                "isClosed": True,
                "isPartialClosed": False,
                "openingWindow": None,
                "reason": closure.get("reason", "Geschlossen")
            }
        
        # closed_partial
        if closure_type == "closed_partial" or scope == "time_range":
            return {
                "date": date_str,
                "isClosed": False,
                "isPartialClosed": True,
                "closedFrom": closure.get("start_time"),
                "closedUntil": closure.get("end_time"),
                "reason": closure.get("reason", "Teilweise geschlossen")
            }
    
    # 2. Wenn keine Closures: Normale Öffnungszeiten
    effective = await calculate_effective_hours(target_date)
    
    if effective.get("is_closed_full_day"):
        return {
            "date": date_str,
            "isClosed": True,
            "isPartialClosed": False,
            "openingWindow": None,
            "reason": effective.get("closure_reason", "Geschlossen")
        }
    
    blocks = effective.get("blocks", [])
    opening_window = None
    if blocks:
        opening_window = {
            "start": blocks[0].get("start"),
            "end": blocks[-1].get("end")
        }
    
    return {
        "date": date_str,
        "isClosed": not effective.get("is_open", True),
        "isPartialClosed": False,
        "openingWindow": opening_window,
        "reason": None
    }


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


@opening_hours_router.get(
    "/opening-hours/effective/{date_str}",
    summary="Effektive Öffnungszeiten für einzelnes Datum",
    description="Berechnet die tatsächlichen Öffnungszeiten für ein Datum. Für Reservierung & Dienstplan."
)
async def get_effective_hours_single(
    date_str: str,
    current_user: dict = Depends(get_current_user)
):
    """GET /api/opening-hours/effective/YYYY-MM-DD"""
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationException("Ungültiges Datumsformat (YYYY-MM-DD erwartet)")
    
    return await calculate_effective_hours(target)


@opening_hours_router.get(
    "/holidays",
    summary="Feiertage für ein Jahr abrufen",
    description="Listet alle gesetzlichen Feiertage in Brandenburg für ein Jahr."
)
async def list_holidays(
    year: int = Query(..., ge=2020, le=2100, description="Jahr"),
    current_user: dict = Depends(get_current_user)
):
    """GET /api/holidays?year=2026"""
    holidays = []
    
    # Feste Feiertage
    for mm_dd, name in BRANDENBURG_HOLIDAYS.items():
        month, day = mm_dd.split("-")
        holiday_date = date(year, int(month), int(day))
        holidays.append({
            "date": holiday_date.strftime("%Y-%m-%d"),
            "name": name,
            "type": "fixed",
            "weekday": weekday_name(holiday_date.weekday()),
            "weekday_de": weekday_name_de(holiday_date.weekday()),
            "region": "BB"
        })
    
    # Bewegliche Feiertage
    moveable = get_moveable_holidays(year)
    for date_str, name in moveable.items():
        holiday_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        holidays.append({
            "date": date_str,
            "name": name,
            "type": "moveable",
            "weekday": weekday_name(holiday_date.weekday()),
            "weekday_de": weekday_name_de(holiday_date.weekday()),
            "region": "BB"
        })
    
    # Nach Datum sortieren
    holidays.sort(key=lambda x: x["date"])
    
    return {
        "year": year,
        "region": "Brandenburg (BB)",
        "count": len(holidays),
        "holidays": holidays
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


# ============== OVERRIDE FUNCTIONS (NEU) ==============

async def get_override_for_date(target_date: date) -> Optional[dict]:
    """
    Suche Override für ein Datum.
    Unterstützt:
    1. Datumsbereich (date_from/date_to)
    2. Recurring (jährlich wiederkehrend über recurring_rule)
    
    Bei mehreren Overlaps gewinnt höchste Priority.
    """
    date_str = target_date.strftime("%Y-%m-%d")
    month = target_date.month
    day = target_date.day
    
    overrides = await db.opening_overrides.find(
        {"active": {"$ne": False}, "archived": {"$ne": True}}
    ).to_list(500)
    
    matching = []
    for override in overrides:
        override_type = override.get("type", "")
        
        # 1. Recurring (jährlich wiederkehrend)
        if override_type == "recurring":
            rule = override.get("recurring_rule", {})
            if rule.get("month") == month and rule.get("day") == day:
                matching.append(override)
                continue
        
        # 2. Datumsbereich (date_from/date_to)
        date_from = override.get("date_from", "")
        date_to = override.get("date_to", date_from)
        
        if date_from and date_from <= date_str <= (date_to or date_from):
            matching.append(override)
    
    if not matching:
        return None
    
    # Sortiere nach Priority (höchste zuerst)
    matching.sort(key=lambda x: x.get("priority", 100), reverse=True)
    return matching[0]


async def resolve_opening_hours(target_date: date) -> dict:
    """
    MASTER-RESOLVER für Öffnungszeiten.
    
    Prioritäten (höchste zuerst):
    1. Overrides (opening_overrides Collection) - ABSOLUT HÖCHSTE PRIORITÄT
    2. Feiertage (Brandenburg) - können Ruhetage überschreiben → offen 12:00-20:00
    3. Perioden (opening_hours_master) - Sommer/Winter Regelwerk
    4. Fallback: geschlossen
    
    Returns:
    {
        date, status, open_from, open_to, last_reservation_time,
        reason: "override" | "holiday" | "period" | "weekday_closed" | "fallback",
        meta: { holiday_name?, period_name?, override_note? }
    }
    """
    date_str = target_date.strftime("%Y-%m-%d")
    weekday = target_date.weekday()
    weekday_key = weekday_name(weekday)
    
    # Basis-Response
    result = {
        "date": date_str,
        "weekday": weekday_key,
        "weekday_de": weekday_name_de(weekday),
        "status": "closed",
        "open_from": None,
        "open_to": None,
        "last_reservation_time": None,
        "reason": "fallback",
        "meta": {}
    }
    
    # ========== 1. OVERRIDES (HÖCHSTE PRIORITÄT) ==========
    override = await get_override_for_date(target_date)
    if override:
        if override.get("status") == "closed":
            result["status"] = "closed"
            result["reason"] = "override"
            result["meta"] = {
                "override_note": override.get("note", ""),
                "override_id": override.get("id")
            }
            logger.info(f"Override CLOSED für {date_str}: {override.get('note')}")
            return result
        
        elif override.get("status") == "open":
            result["status"] = "open"
            result["open_from"] = override.get("open_from")
            result["open_to"] = override.get("open_to")
            result["last_reservation_time"] = override.get("last_reservation_time")
            result["reason"] = "override"
            result["meta"] = {
                "override_note": override.get("note", ""),
                "override_id": override.get("id")
            }
            logger.info(f"Override OPEN für {date_str}: {override.get('open_from')}-{override.get('open_to')}")
            return result
    
    # ========== 2. FEIERTAGE (Brandenburg) ==========
    is_holiday, holiday_name_str = is_holiday_brandenburg(target_date)
    
    # ========== 3. PERIODEN ==========
    period = await get_active_period_for_date(target_date)
    
    if period:
        rules = period.get("rules_by_weekday", {})
        day_rules = rules.get(weekday_key, {})
        
        # Prüfe ob Ruhetag
        if day_rules.get("is_closed", False):
            # FEIERTAG-OVERRIDE: Wenn Feiertag auf Ruhetag fällt → offen 12:00-20:00
            if is_holiday:
                result["status"] = "open"
                result["open_from"] = "12:00"
                result["open_to"] = "20:00"
                result["reason"] = "holiday"
                result["meta"] = {
                    "holiday_name": holiday_name_str,
                    "period_name": period.get("name"),
                    "note": f"Feiertag '{holiday_name_str}' überschreibt Ruhetag"
                }
                logger.info(f"Feiertag-Override: {holiday_name_str} am {date_str}")
                return result
            else:
                # Normaler Ruhetag
                result["status"] = "closed"
                result["reason"] = "weekday_closed"
                result["meta"] = {
                    "period_name": period.get("name"),
                    "note": f"Ruhetag ({weekday_name_de(weekday)})"
                }
                return result
        
        # Normale Öffnung aus Periode
        blocks = day_rules.get("blocks", [])
        if blocks:
            # Ersten und letzten Block für open_from/open_to
            result["status"] = "open"
            result["open_from"] = blocks[0].get("start")
            result["open_to"] = blocks[-1].get("end")
            result["reason"] = "period"
            result["meta"] = {
                "period_name": period.get("name"),
                "blocks": blocks
            }
            
            # Wenn Feiertag, erweitern auf 12:00-20:00 (falls kürzer)
            if is_holiday:
                result["meta"]["holiday_name"] = holiday_name_str
                # Optional: Zeiten anpassen bei Feiertag
            
            return result
    
    # ========== 4. FALLBACK ==========
    # Keine Periode gefunden - Standard-Öffnung oder geschlossen
    if is_holiday:
        result["status"] = "open"
        result["open_from"] = "12:00"
        result["open_to"] = "20:00"
        result["reason"] = "holiday"
        result["meta"] = {"holiday_name": holiday_name_str}
        return result
    
    result["status"] = "closed"
    result["reason"] = "fallback"
    result["meta"] = {"note": "Keine Periode konfiguriert"}
    return result


# ============== API ENDPOINTS: OVERRIDES (NEU) ==============

@opening_hours_router.get(
    "/opening-hours/overrides",
    summary="Alle Overrides abrufen",
    description="Listet alle Datum-Overrides für Öffnungszeiten. Admin only."
)
async def list_overrides(
    from_date: Optional[str] = Query(None, alias="from", description="Ab Datum (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, alias="to", description="Bis Datum (YYYY-MM-DD)"),
    current_user: dict = Depends(require_admin)
):
    """GET /api/opening-hours/overrides"""
    query = {"archived": {"$ne": True}}
    
    overrides = await db.opening_overrides.find(query, {"_id": 0}).sort("date_from", 1).to_list(500)
    
    # Filtern wenn Zeitraum angegeben
    if from_date and to_date:
        filtered = []
        for o in overrides:
            o_from = o.get("date_from", "")
            o_to = o.get("date_to", o_from)
            if o_from <= to_date and o_to >= from_date:
                filtered.append(o)
        return filtered
    
    return overrides


@opening_hours_router.post(
    "/opening-hours/overrides",
    status_code=201,
    summary="Neuen Override erstellen",
    description="Erstellt einen Override (offen oder geschlossen). HÖCHSTE PRIORITÄT - überschreibt alles."
)
async def create_override(
    data: OpeningOverrideCreate,
    current_user: dict = Depends(require_admin)
):
    """POST /api/opening-hours/overrides"""
    
    # Validierung: Bei status=open müssen Zeiten angegeben sein
    if data.status == "open":
        if not data.open_from or not data.open_to:
            raise ValidationException("Bei status='open' müssen open_from und open_to angegeben werden")
    
    date_to = data.date_to if data.date_to else data.date_from
    
    override = {
        "id": str(uuid.uuid4()),
        "date_from": data.date_from,
        "date_to": date_to,
        "status": data.status,
        "open_from": data.open_from,
        "open_to": data.open_to,
        "last_reservation_time": data.last_reservation_time,
        "note": data.note,
        "priority": data.priority,
        "active": True,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "archived": False
    }
    
    await db.opening_overrides.insert_one(override)
    
    # Audit Log
    await create_audit_log(
        actor=current_user,
        action="create",
        entity="opening_override",
        entity_id=override["id"],
        after=safe_dict_for_audit(override)
    )
    
    date_range = f"{data.date_from}" if data.date_from == date_to else f"{data.date_from} bis {date_to}"
    status_text = "GESCHLOSSEN" if data.status == "closed" else f"OFFEN {data.open_from}-{data.open_to}"
    logger.info(f"Override erstellt: {date_range} → {status_text} ({data.note}) von {current_user.get('email')}")
    
    override.pop("_id", None)
    return override


@opening_hours_router.put(
    "/opening-hours/overrides/{override_id}",
    summary="Override aktualisieren",
    description="Aktualisiert einen bestehenden Override. Admin only."
)
async def update_override(
    override_id: str,
    data: OpeningOverrideUpdate,
    current_user: dict = Depends(require_admin)
):
    """PUT /api/opening-hours/overrides/{id}"""
    
    override = await db.opening_overrides.find_one(
        {"id": override_id, "archived": {"$ne": True}},
        {"_id": 0}
    )
    
    if not override:
        raise NotFoundException("Override nicht gefunden")
    
    old_override = override.copy()
    update_data = data.model_dump(exclude_unset=True)
    
    if not update_data:
        raise ValidationException("Keine Änderungen übergeben")
    
    update_data["updated_at"] = now_iso()
    
    await db.opening_overrides.update_one(
        {"id": override_id},
        {"$set": update_data}
    )
    
    # Audit Log
    await create_audit_log(
        actor=current_user,
        action="update",
        entity="opening_override",
        entity_id=override_id,
        before=safe_dict_for_audit(old_override),
        after=safe_dict_for_audit(update_data)
    )
    
    updated = await db.opening_overrides.find_one({"id": override_id}, {"_id": 0})
    logger.info(f"Override '{override_id}' aktualisiert von {current_user.get('email')}")
    return updated


@opening_hours_router.delete(
    "/opening-hours/overrides/{override_id}",
    status_code=204,
    summary="Override löschen",
    description="Soft Delete eines Overrides. Admin only."
)
async def delete_override(
    override_id: str,
    current_user: dict = Depends(require_admin)
):
    """DELETE /api/opening-hours/overrides/{id}"""
    
    override = await db.opening_overrides.find_one(
        {"id": override_id, "archived": {"$ne": True}}
    )
    
    if not override:
        raise NotFoundException("Override nicht gefunden")
    
    await db.opening_overrides.update_one(
        {"id": override_id},
        {"$set": {"archived": True, "updated_at": now_iso()}}
    )
    
    # Audit Log
    await create_audit_log(
        actor=current_user,
        action="delete",
        entity="opening_override",
        entity_id=override_id
    )
    
    logger.info(f"Override '{override_id}' gelöscht von {current_user.get('email')}")
    return None


# ============== API ENDPOINT: RESOLVE (NEU) ==============

@opening_hours_router.get(
    "/opening-hours/resolve",
    summary="Öffnungszeiten für Datum auflösen",
    description="Berechnet die effektiven Öffnungszeiten mit vollständiger Prioritätslogik."
)
async def resolve_opening_hours_endpoint(
    date: str = Query(..., description="Datum (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user)
):
    """
    GET /api/opening-hours/resolve?date=YYYY-MM-DD
    
    Returns:
    {
        date, status: "open"|"closed", open_from, open_to, last_reservation_time,
        reason: "override"|"holiday"|"period"|"weekday_closed"|"fallback",
        meta: { holiday_name?, period_name?, override_note? }
    }
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationException("Ungültiges Datumsformat (YYYY-MM-DD erwartet)")
    
    return await resolve_opening_hours(target_date)
