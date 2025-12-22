"""
GastroCore Reservation Configuration Module - Sprint: Reservierung Live-Ready
================================================================================

FEATURES:
1. Aufenthaltsdauer (Standard + Verlängerung)
2. Durchgänge & Sperrzeiten (konfigurierbar pro Wochentag)
3. Zeitraum-basierte Öffnungszeiten (Sommer/Winter)

ADDITIV - Keine Breaking Changes an bestehenden Tabellen/Endpunkten
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


# ============== CONSTANTS ==============
DEFAULT_DURATION_MINUTES = 110  # 1h 50min Standard-Aufenthaltsdauer


# ============== ENUMS ==============
class DayOfWeek(int, Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


# ============== PYDANTIC MODELS ==============

# --- Time Slot (einzelner buchbarer Slot) ---
class TimeSlot(BaseModel):
    time: str  # HH:MM
    is_blocked: bool = False
    label: Optional[str] = None  # z.B. "Durchgang 1"


# --- Durchgänge & Sperrzeiten Konfiguration pro Tag ---
class TimeSlotConfigCreate(BaseModel):
    """
    Konfiguration der buchbaren Zeiten und Sperrzeiten für einen Wochentag.
    
    Beispiel Samstag/Sonntag:
    - slots: ["11:30", "12:00", "14:00", "16:00", "16:30", "17:00", ...]
    - blocked_ranges: [{"start": "12:05", "end": "13:55"}, {"start": "14:05", "end": "15:55"}]
    """
    day_of_week: int = Field(..., ge=0, le=6)  # 0=Monday, 6=Sunday
    slots: List[str] = Field(default_factory=list)  # Buchbare Zeiten ["11:30", "12:00", ...]
    blocked_ranges: List[Dict[str, str]] = Field(default_factory=list)  # [{"start": "12:05", "end": "13:55"}]
    slot_interval_minutes: int = Field(default=30, ge=15, le=60)  # Standard-Intervall für Auto-Generierung
    use_manual_slots: bool = False  # True = nur explizit definierte Slots, False = Auto-Generierung
    
    @field_validator('slots')
    @classmethod
    def validate_slots(cls, v):
        for slot in v:
            try:
                datetime.strptime(slot, "%H:%M")
            except ValueError:
                raise ValueError(f"Ungültiges Zeitformat: {slot} (HH:MM erwartet)")
        return sorted(v)
    
    @field_validator('blocked_ranges')
    @classmethod
    def validate_blocked_ranges(cls, v):
        for br in v:
            if 'start' not in br or 'end' not in br:
                raise ValueError("Sperrzeit benötigt 'start' und 'end'")
            try:
                datetime.strptime(br['start'], "%H:%M")
                datetime.strptime(br['end'], "%H:%M")
            except ValueError:
                raise ValueError(f"Ungültiges Zeitformat in Sperrzeit: {br}")
        return v


class TimeSlotConfigUpdate(BaseModel):
    slots: Optional[List[str]] = None
    blocked_ranges: Optional[List[Dict[str, str]]] = None
    slot_interval_minutes: Optional[int] = Field(None, ge=15, le=60)
    use_manual_slots: Optional[bool] = None


# --- Zeitraum-basierte Öffnungszeiten (Sommer/Winter) ---
class OpeningHourEntry(BaseModel):
    """Einzelner Öffnungszeiten-Eintrag"""
    day_of_week: int = Field(..., ge=0, le=6)
    open_time: str  # HH:MM
    close_time: str  # HH:MM
    is_closed: bool = False
    
    @field_validator('open_time', 'close_time')
    @classmethod
    def validate_time(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError(f"Ungültiges Zeitformat: {v}")
        return v


class OpeningHoursPeriodCreate(BaseModel):
    """
    Zeitraum-basierte Öffnungszeiten (z.B. Sommer, Winter, Weihnachten)
    """
    name: str = Field(..., min_length=2, max_length=100)  # z.B. "Sommerzeit", "Winterzeit"
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    is_default: bool = False  # Falls kein Zeitraum passt, wird dieser verwendet
    hours: List[OpeningHourEntry] = Field(default_factory=list)
    
    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Ungültiges Datumsformat: {v} (YYYY-MM-DD erwartet)")
        return v


class OpeningHoursPeriodUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_default: Optional[bool] = None
    hours: Optional[List[OpeningHourEntry]] = None


# --- Aufenthaltsdauer Verlängerung ---
class ExtendDurationRequest(BaseModel):
    additional_minutes: int = Field(..., ge=15, le=180)  # 15min bis 3h Verlängerung
    reason: Optional[str] = None


# ============== HELPER FUNCTIONS ==============

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_entity(data: dict, extra_fields: dict = None) -> dict:
    entity = {
        "id": str(uuid.uuid4()),
        **data,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "archived": False
    }
    if extra_fields:
        entity.update(extra_fields)
    return entity


async def get_default_duration() -> int:
    """Hole Standard-Aufenthaltsdauer aus Settings"""
    setting = await db.settings.find_one({"key": "default_duration_minutes"})
    if setting:
        return int(setting.get("value", DEFAULT_DURATION_MINUTES))
    return DEFAULT_DURATION_MINUTES


async def get_time_slot_config_for_day(day_of_week: int) -> Optional[dict]:
    """Hole Zeitslot-Konfiguration für einen Wochentag"""
    return await db.time_slot_configs.find_one(
        {"day_of_week": day_of_week, "archived": False},
        {"_id": 0}
    )


async def get_opening_hours_for_date(date_str: str) -> Optional[dict]:
    """
    Hole Öffnungszeiten für ein bestimmtes Datum.
    Prüft erst zeitraumbasierte Perioden, dann Default.
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        day_of_week = target_date.weekday()
        
        # Suche passenden Zeitraum
        periods = await db.opening_hours_periods.find(
            {"archived": False}
        ).to_list(100)
        
        for period in periods:
            start = datetime.strptime(period["start_date"], "%Y-%m-%d").date()
            end = datetime.strptime(period["end_date"], "%Y-%m-%d").date()
            
            if start <= target_date <= end:
                # Finde Eintrag für diesen Wochentag
                for entry in period.get("hours", []):
                    if entry["day_of_week"] == day_of_week:
                        return {
                            "period_name": period["name"],
                            "period_id": period["id"],
                            **entry
                        }
        
        # Kein Zeitraum gefunden - suche Default-Periode
        default_period = await db.opening_hours_periods.find_one(
            {"is_default": True, "archived": False}
        )
        if default_period:
            for entry in default_period.get("hours", []):
                if entry["day_of_week"] == day_of_week:
                    return {
                        "period_name": default_period["name"],
                        "period_id": default_period["id"],
                        **entry
                    }
        
        # Fallback auf alte opening_hours Collection
        old_hours = await db.opening_hours.find_one(
            {"day_of_week": day_of_week},
            {"_id": 0}
        )
        if old_hours:
            return old_hours
        
        # Absoluter Fallback
        return {
            "day_of_week": day_of_week,
            "open_time": "11:00",
            "close_time": "22:00",
            "is_closed": False,
            "period_name": "Standard"
        }
        
    except Exception as e:
        logger.error(f"Fehler beim Laden der Öffnungszeiten: {e}")
        return None


async def get_available_slots_for_date(date_str: str) -> List[str]:
    """
    Berechne alle verfügbaren Buchungsslots für ein Datum.
    Berücksichtigt: Öffnungszeiten, Durchgänge, Sperrzeiten
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        day_of_week = target_date.weekday()
        
        # Öffnungszeiten laden
        hours = await get_opening_hours_for_date(date_str)
        if not hours or hours.get("is_closed"):
            return []
        
        open_time = hours.get("open_time", "11:00")
        close_time = hours.get("close_time", "22:00")
        
        # Zeitslot-Konfiguration laden
        slot_config = await get_time_slot_config_for_day(day_of_week)
        
        if slot_config and slot_config.get("use_manual_slots") and slot_config.get("slots"):
            # Manuelle Slots verwenden
            base_slots = slot_config["slots"]
        else:
            # Auto-generierte Slots
            interval = slot_config.get("slot_interval_minutes", 30) if slot_config else 30
            base_slots = generate_time_slots(open_time, close_time, interval)
        
        # Sperrzeiten anwenden
        blocked_ranges = slot_config.get("blocked_ranges", []) if slot_config else []
        available_slots = filter_blocked_slots(base_slots, blocked_ranges)
        
        # Nur Slots innerhalb der Öffnungszeiten
        available_slots = [s for s in available_slots if open_time <= s <= close_time]
        
        return sorted(available_slots)
        
    except Exception as e:
        logger.error(f"Fehler bei Slot-Berechnung: {e}")
        return []


def generate_time_slots(open_time: str, close_time: str, interval_minutes: int) -> List[str]:
    """Generiere Zeitslots basierend auf Intervall"""
    slots = []
    current = datetime.strptime(open_time, "%H:%M")
    end = datetime.strptime(close_time, "%H:%M")
    
    while current <= end:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=interval_minutes)
    
    return slots


def filter_blocked_slots(slots: List[str], blocked_ranges: List[Dict[str, str]]) -> List[str]:
    """Filtere Slots die in Sperrzeiten fallen"""
    if not blocked_ranges:
        return slots
    
    available = []
    for slot in slots:
        slot_time = datetime.strptime(slot, "%H:%M")
        is_blocked = False
        
        for br in blocked_ranges:
            start = datetime.strptime(br["start"], "%H:%M")
            end = datetime.strptime(br["end"], "%H:%M")
            
            if start <= slot_time <= end:
                is_blocked = True
                break
        
        if not is_blocked:
            available.append(slot)
    
    return available


async def check_capacity_with_duration(
    date_str: str,
    time_str: str,
    party_size: int,
    duration_minutes: int,
    area_id: Optional[str] = None,
    exclude_reservation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Erweiterte Kapazitätsprüfung mit Berücksichtigung der Aufenthaltsdauer.
    Prüft alle Überlappungen im Zeitraum der geplanten Reservierung.
    """
    try:
        # Berechne Zeitfenster der neuen Reservierung
        start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        
        # Alle aktiven Reservierungen des Tages laden
        query = {
            "date": date_str,
            "status": {"$in": ["neu", "bestaetigt", "angekommen"]},
            "archived": False
        }
        if area_id:
            query["area_id"] = area_id
        if exclude_reservation_id:
            query["id"] = {"$ne": exclude_reservation_id}
        
        existing = await db.reservations.find(query, {"_id": 0}).to_list(1000)
        
        # Finde überlappende Reservierungen
        default_duration = await get_default_duration()
        overlapping_guests = 0
        overlapping_reservations = []
        
        for res in existing:
            res_start = datetime.strptime(f"{res['date']} {res['time']}", "%Y-%m-%d %H:%M")
            res_duration = res.get("duration_minutes", default_duration)
            res_end = res_start + timedelta(minutes=res_duration)
            
            # Prüfe Überlappung
            if start_dt < res_end and end_dt > res_start:
                overlapping_guests += res.get("party_size", 0)
                overlapping_reservations.append({
                    "id": res["id"],
                    "guest_name": res.get("guest_name"),
                    "time": res["time"],
                    "party_size": res.get("party_size"),
                    "duration": res_duration
                })
        
        # Kapazität ermitteln
        max_capacity = 100
        if area_id:
            area = await db.areas.find_one({"id": area_id, "archived": False}, {"_id": 0})
            if area and area.get("capacity"):
                max_capacity = area["capacity"]
        else:
            cap_setting = await db.settings.find_one({"key": "max_total_capacity"})
            if cap_setting:
                max_capacity = int(cap_setting.get("value", 100))
        
        available_seats = max_capacity - overlapping_guests
        
        return {
            "available": available_seats >= party_size,
            "current_guests": overlapping_guests,
            "max_capacity": max_capacity,
            "available_seats": available_seats,
            "overlapping_count": len(overlapping_reservations),
            "duration_checked": duration_minutes
        }
        
    except Exception as e:
        logger.error(f"Kapazitätsprüfung fehlgeschlagen: {e}")
        return {"available": True, "error": str(e)}


# ============== ROUTER ==============
reservation_config_router = APIRouter(prefix="/reservation-config", tags=["Reservation Config"])


# --- Zeitslot-Konfiguration (Durchgänge & Sperrzeiten) ---

@reservation_config_router.get("/time-slots")
async def list_time_slot_configs(current_user: dict = Depends(get_current_user)):
    """Liste alle Zeitslot-Konfigurationen"""
    configs = await db.time_slot_configs.find(
        {"archived": False},
        {"_id": 0}
    ).to_list(10)
    
    # Fülle fehlende Tage mit leerer Config
    day_configs = {c["day_of_week"]: c for c in configs}
    result = []
    
    day_names = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    for day in range(7):
        if day in day_configs:
            config = day_configs[day]
            config["day_name"] = day_names[day]
            result.append(config)
        else:
            result.append({
                "day_of_week": day,
                "day_name": day_names[day],
                "slots": [],
                "blocked_ranges": [],
                "slot_interval_minutes": 30,
                "use_manual_slots": False
            })
    
    return result


@reservation_config_router.get("/time-slots/{day_of_week}")
async def get_time_slot_config(
    day_of_week: int,
    current_user: dict = Depends(get_current_user)
):
    """Hole Zeitslot-Konfiguration für einen Wochentag"""
    if day_of_week < 0 or day_of_week > 6:
        raise ValidationException("Ungültiger Wochentag (0-6)")
    
    config = await get_time_slot_config_for_day(day_of_week)
    
    if not config:
        day_names = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        return {
            "day_of_week": day_of_week,
            "day_name": day_names[day_of_week],
            "slots": [],
            "blocked_ranges": [],
            "slot_interval_minutes": 30,
            "use_manual_slots": False
        }
    
    return config


@reservation_config_router.post("/time-slots")
async def create_or_update_time_slot_config(
    data: TimeSlotConfigCreate,
    current_user: dict = Depends(require_admin)
):
    """Erstelle oder aktualisiere Zeitslot-Konfiguration für einen Tag"""
    existing = await db.time_slot_configs.find_one(
        {"day_of_week": data.day_of_week, "archived": False}
    )
    
    day_names = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    
    if existing:
        # Update
        update_data = {
            "slots": data.slots,
            "blocked_ranges": data.blocked_ranges,
            "slot_interval_minutes": data.slot_interval_minutes,
            "use_manual_slots": data.use_manual_slots,
            "updated_at": now_iso()
        }
        await db.time_slot_configs.update_one(
            {"id": existing["id"]},
            {"$set": update_data}
        )
        await create_audit_log(current_user, "time_slot_config", existing["id"], "update")
        
        return {
            "message": f"Zeitslot-Konfiguration für {day_names[data.day_of_week]} aktualisiert",
            "id": existing["id"]
        }
    else:
        # Create
        doc = create_entity(data.model_dump())
        doc["day_name"] = day_names[data.day_of_week]
        await db.time_slot_configs.insert_one(doc)
        await create_audit_log(current_user, "time_slot_config", doc["id"], "create")
        
        return {
            "message": f"Zeitslot-Konfiguration für {day_names[data.day_of_week]} erstellt",
            "id": doc["id"]
        }


@reservation_config_router.delete("/time-slots/{day_of_week}")
async def delete_time_slot_config(
    day_of_week: int,
    current_user: dict = Depends(require_admin)
):
    """Lösche Zeitslot-Konfiguration (setzt auf Standard zurück)"""
    result = await db.time_slot_configs.update_one(
        {"day_of_week": day_of_week, "archived": False},
        {"$set": {"archived": True, "updated_at": now_iso()}}
    )
    
    if result.modified_count == 0:
        raise NotFoundException("Zeitslot-Konfiguration")
    
    return {"message": "Zeitslot-Konfiguration gelöscht (Standard wird verwendet)"}


# --- Zeitraum-basierte Öffnungszeiten ---

@reservation_config_router.get("/opening-periods")
async def list_opening_periods(current_user: dict = Depends(get_current_user)):
    """Liste alle Öffnungszeiten-Perioden"""
    periods = await db.opening_hours_periods.find(
        {"archived": False},
        {"_id": 0}
    ).sort("start_date", 1).to_list(100)
    
    return periods


@reservation_config_router.get("/opening-periods/{period_id}")
async def get_opening_period(
    period_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Hole eine Öffnungszeiten-Periode"""
    period = await db.opening_hours_periods.find_one(
        {"id": period_id, "archived": False},
        {"_id": 0}
    )
    
    if not period:
        raise NotFoundException("Öffnungszeiten-Periode")
    
    return period


@reservation_config_router.post("/opening-periods")
async def create_opening_period(
    data: OpeningHoursPeriodCreate,
    current_user: dict = Depends(require_admin)
):
    """Erstelle eine neue Öffnungszeiten-Periode"""
    # Wenn Default, alle anderen Default-Flags entfernen
    if data.is_default:
        await db.opening_hours_periods.update_many(
            {"archived": False},
            {"$set": {"is_default": False}}
        )
    
    doc = create_entity({
        "name": data.name,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "is_default": data.is_default,
        "hours": [h.model_dump() for h in data.hours]
    })
    
    await db.opening_hours_periods.insert_one(doc)
    await create_audit_log(current_user, "opening_period", doc["id"], "create")
    
    return {"message": f"Periode '{data.name}' erstellt", "id": doc["id"]}


@reservation_config_router.patch("/opening-periods/{period_id}")
async def update_opening_period(
    period_id: str,
    data: OpeningHoursPeriodUpdate,
    current_user: dict = Depends(require_admin)
):
    """Aktualisiere eine Öffnungszeiten-Periode"""
    period = await db.opening_hours_periods.find_one(
        {"id": period_id, "archived": False}
    )
    
    if not period:
        raise NotFoundException("Öffnungszeiten-Periode")
    
    update_data = {"updated_at": now_iso()}
    
    if data.name is not None:
        update_data["name"] = data.name
    if data.start_date is not None:
        update_data["start_date"] = data.start_date
    if data.end_date is not None:
        update_data["end_date"] = data.end_date
    if data.is_default is not None:
        if data.is_default:
            await db.opening_hours_periods.update_many(
                {"archived": False},
                {"$set": {"is_default": False}}
            )
        update_data["is_default"] = data.is_default
    if data.hours is not None:
        update_data["hours"] = [h.model_dump() for h in data.hours]
    
    await db.opening_hours_periods.update_one(
        {"id": period_id},
        {"$set": update_data}
    )
    await create_audit_log(current_user, "opening_period", period_id, "update")
    
    return {"message": "Periode aktualisiert", "id": period_id}


@reservation_config_router.delete("/opening-periods/{period_id}")
async def delete_opening_period(
    period_id: str,
    current_user: dict = Depends(require_admin)
):
    """Lösche (archiviere) eine Öffnungszeiten-Periode"""
    result = await db.opening_hours_periods.update_one(
        {"id": period_id, "archived": False},
        {"$set": {"archived": True, "updated_at": now_iso()}}
    )
    
    if result.modified_count == 0:
        raise NotFoundException("Öffnungszeiten-Periode")
    
    await create_audit_log(current_user, "opening_period", period_id, "archive")
    
    return {"message": "Periode gelöscht"}


# --- Verfügbarkeits-Endpoints ---

@reservation_config_router.get("/available-slots/{date}")
async def get_available_slots(
    date: str,
    area_id: Optional[str] = None
):
    """
    Öffentlicher Endpoint: Hole alle verfügbaren Buchungsslots für ein Datum.
    Berücksichtigt Öffnungszeiten, Durchgänge und Sperrzeiten.
    """
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise ValidationException("Ungültiges Datumsformat (YYYY-MM-DD erwartet)")
    
    slots = await get_available_slots_for_date(date)
    
    # Öffnungszeiten-Info
    hours = await get_opening_hours_for_date(date)
    
    return {
        "date": date,
        "slots": slots,
        "opening_hours": hours,
        "slot_count": len(slots)
    }


@reservation_config_router.get("/check-availability")
async def check_availability(
    date: str,
    time: str,
    party_size: int = Query(..., ge=1, le=50),
    duration_minutes: Optional[int] = None,
    area_id: Optional[str] = None
):
    """
    Prüfe Verfügbarkeit für eine Reservierung.
    Berücksichtigt Öffnungszeiten, Sperrzeiten und Kapazität mit Aufenthaltsdauer.
    """
    # Validiere Datum/Zeit
    try:
        datetime.strptime(date, "%Y-%m-%d")
        datetime.strptime(time, "%H:%M")
    except ValueError:
        raise ValidationException("Ungültiges Datums- oder Zeitformat")
    
    # Öffnungszeiten prüfen
    hours = await get_opening_hours_for_date(date)
    if not hours or hours.get("is_closed"):
        return {
            "available": False,
            "reason": "Restaurant geschlossen",
            "opening_hours": hours
        }
    
    if not (hours.get("open_time", "00:00") <= time <= hours.get("close_time", "23:59")):
        return {
            "available": False,
            "reason": f"Außerhalb der Öffnungszeiten ({hours.get('open_time')} - {hours.get('close_time')})",
            "opening_hours": hours
        }
    
    # Prüfe ob Zeit in Sperrzeit fällt
    target_date = datetime.strptime(date, "%Y-%m-%d")
    slot_config = await get_time_slot_config_for_day(target_date.weekday())
    
    if slot_config:
        time_dt = datetime.strptime(time, "%H:%M")
        for br in slot_config.get("blocked_ranges", []):
            start = datetime.strptime(br["start"], "%H:%M")
            end = datetime.strptime(br["end"], "%H:%M")
            if start <= time_dt <= end:
                return {
                    "available": False,
                    "reason": f"Zeit liegt in Sperrzeit ({br['start']} - {br['end']})",
                    "blocked_range": br
                }
    
    # Kapazität prüfen (mit Aufenthaltsdauer)
    if duration_minutes is None:
        duration_minutes = await get_default_duration()
    
    capacity = await check_capacity_with_duration(
        date, time, party_size, duration_minutes, area_id
    )
    
    return {
        "available": capacity["available"],
        "capacity": capacity,
        "duration_minutes": duration_minutes,
        "opening_hours": hours
    }


# --- Aufenthaltsdauer-Einstellungen ---

@reservation_config_router.get("/duration-settings")
async def get_duration_settings(current_user: dict = Depends(get_current_user)):
    """Hole Aufenthaltsdauer-Einstellungen"""
    default_duration = await get_default_duration()
    
    # Erweiterungsoptionen
    extension_options = await db.settings.find_one({"key": "duration_extension_options"})
    if extension_options:
        options = extension_options.get("value", "30,60,90,120")
    else:
        options = "30,60,90,120"
    
    return {
        "default_duration_minutes": default_duration,
        "default_duration_display": f"{default_duration // 60}h {default_duration % 60}min",
        "extension_options_minutes": [int(x) for x in options.split(",")]
    }


@reservation_config_router.post("/duration-settings")
async def update_duration_settings(
    default_minutes: int = Query(..., ge=30, le=300),
    extension_options: Optional[str] = None,
    current_user: dict = Depends(require_admin)
):
    """Aktualisiere Aufenthaltsdauer-Einstellungen"""
    # Default Duration
    await db.settings.update_one(
        {"key": "default_duration_minutes"},
        {"$set": {"key": "default_duration_minutes", "value": str(default_minutes), "updated_at": now_iso()}},
        upsert=True
    )
    
    if extension_options:
        await db.settings.update_one(
            {"key": "duration_extension_options"},
            {"$set": {"key": "duration_extension_options", "value": extension_options, "updated_at": now_iso()}},
            upsert=True
        )
    
    await create_audit_log(current_user, "settings", "duration", "update")
    
    return {
        "message": "Aufenthaltsdauer-Einstellungen aktualisiert",
        "default_minutes": default_minutes
    }


# --- Reservierungs-Verlängerung ---

@reservation_config_router.post("/reservations/{reservation_id}/extend")
async def extend_reservation_duration(
    reservation_id: str,
    data: ExtendDurationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Verlängere die Aufenthaltsdauer einer Reservierung.
    Prüft Kapazität für den erweiterten Zeitraum.
    """
    # Reservierung laden
    reservation = await db.reservations.find_one(
        {"id": reservation_id, "archived": False},
        {"_id": 0}
    )
    
    if not reservation:
        raise NotFoundException("Reservierung")
    
    # Aktuelle Dauer
    current_duration = reservation.get("duration_minutes", await get_default_duration())
    new_duration = current_duration + data.additional_minutes
    
    # Kapazität für neue Dauer prüfen
    capacity = await check_capacity_with_duration(
        reservation["date"],
        reservation["time"],
        reservation.get("party_size", 1),
        new_duration,
        reservation.get("area_id"),
        exclude_reservation_id=reservation_id
    )
    
    if not capacity["available"]:
        raise ConflictException(
            f"Verlängerung nicht möglich - Kapazität überschritten "
            f"(max. {capacity['available_seats']} Plätze verfügbar)"
        )
    
    # Update Reservierung
    update_data = {
        "duration_minutes": new_duration,
        "is_extended": True,
        "extension_reason": data.reason,
        "extended_at": now_iso(),
        "extended_by": current_user.get("id"),
        "updated_at": now_iso()
    }
    
    # Log Extension History
    extensions = reservation.get("extensions", [])
    extensions.append({
        "from_minutes": current_duration,
        "to_minutes": new_duration,
        "added_minutes": data.additional_minutes,
        "reason": data.reason,
        "extended_at": now_iso(),
        "extended_by": current_user.get("name", current_user.get("email"))
    })
    update_data["extensions"] = extensions
    
    await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": update_data}
    )
    
    await create_audit_log(
        current_user, "reservation", reservation_id, "extend",
        {"from_minutes": current_duration, "to_minutes": new_duration}
    )
    
    return {
        "message": f"Reservierung um {data.additional_minutes} Minuten verlängert",
        "old_duration": current_duration,
        "new_duration": new_duration,
        "is_extended": True
    }


# ============== EXPORT ==============
__all__ = [
    "reservation_config_router",
    "get_default_duration",
    "get_available_slots_for_date",
    "get_opening_hours_for_date",
    "check_capacity_with_duration",
    "TimeSlotConfigCreate",
    "OpeningHoursPeriodCreate",
    "DEFAULT_DURATION_MINUTES"
]
