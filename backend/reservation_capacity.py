"""
GastroCore Reservation Capacity Module
================================================================================
Kapazitätslogik + Durchgänge + Slots für Reservierungen

FEATURES:
1. Durchgänge (Seatings) mit Kapazität pro Durchgang
2. Slots innerhalb von Durchgängen (30-Min-Raster)
3. Tagestyp-Erkennung: Wochentag/Wochenende/Feiertag
4. Blockdauer-Berechnung (Standard: 120 Min, Feiertag: 140 Min)
5. Kapazitätsberechnung pro Slot basierend auf bestehenden Reservierungen
6. Admin-Override für Sondertage

GESCHÄFTSREGELN:
- Kapazität: 95 Plätze pro Durchgang
- Blockdauer Normal: 120 Minuten (1:50 Gast + 0:10 Service)
- Blockdauer Feiertag: 140 Minuten (2:10 Gast + 0:10 Service)
- Wochenende: 2 Durchgänge mittags + ab 16:00 alle 30 Min
- Feiertag: 4 Durchgänge, Startzeiten aus Blockdauer berechnet
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, date, timedelta, time
from enum import Enum
import uuid

# Core imports
from core.database import db
from core.auth import require_admin, require_manager, get_current_user
from core.audit import create_audit_log, safe_dict_for_audit
from core.exceptions import NotFoundException, ValidationException, ConflictException

# Import Opening Hours
from opening_hours_module import calculate_effective_hours

import logging
logger = logging.getLogger(__name__)


# ============== ROUTER ==============
capacity_router = APIRouter(tags=["Reservation Capacity"])


# ============== CONSTANTS ==============
DEFAULT_CAPACITY_PER_SEATING = 95  # Plätze pro Durchgang
DEFAULT_BLOCK_DURATION_MINUTES = 120  # Standard: 2h (1:50 + 0:10)
HOLIDAY_BLOCK_DURATION_MINUTES = 140  # Feiertag: 2:20 (2:10 + 0:10)
DEFAULT_SLOT_INTERVAL = 30  # Minuten zwischen Slots


# ============== ENUMS ==============
class DayType(str, Enum):
    WEEKDAY = "weekday"
    WEEKEND = "weekend"
    HOLIDAY = "holiday"


# ============== HELPER FUNCTIONS ==============

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def time_to_minutes(time_str: str) -> int:
    """Konvertiere HH:MM zu Minuten seit Mitternacht"""
    h, m = map(int, time_str.split(":"))
    return h * 60 + m


def minutes_to_time(minutes: int) -> str:
    """Konvertiere Minuten seit Mitternacht zu HH:MM"""
    h = (minutes // 60) % 24
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def round_to_slot(minutes: int, interval: int = 30) -> int:
    """Runde Minuten auf nächsten Slot-Zeitpunkt"""
    return ((minutes + interval - 1) // interval) * interval


# ============== PYDANTIC MODELS ==============

class Seating(BaseModel):
    """Ein Durchgang mit Slots"""
    seating_number: int
    name: str
    start_time: str  # HH:MM
    end_time: str    # HH:MM
    slots: List[str]  # ["11:00", "11:30", "12:00"]
    capacity: int = DEFAULT_CAPACITY_PER_SEATING


class SlotInfo(BaseModel):
    """Informationen zu einem einzelnen Slot"""
    time: str  # HH:MM
    seating: int  # Durchgang-Nummer
    capacity_total: int
    capacity_used: int
    capacity_available: int
    disabled: bool
    reason: Optional[str] = None


class CapacityConfigCreate(BaseModel):
    """Kapazitätskonfiguration für ein Datum/Regel"""
    capacity_per_seating: int = Field(default=95, ge=1, le=500)
    block_duration_minutes: int = Field(default=120, ge=60, le=240)
    seatings_override: Optional[List[Dict[str, Any]]] = None  # Manuelle Durchgänge
    

class HolidayConfigCreate(BaseModel):
    """Feiertag-Konfiguration"""
    date: str  # YYYY-MM-DD
    name: str
    block_duration_minutes: int = Field(default=140, ge=60, le=240)
    num_seatings: int = Field(default=4, ge=1, le=8)
    first_seating_start: str = "11:00"  # HH:MM
    capacity_per_seating: int = Field(default=95, ge=1, le=500)
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Ungültiges Datumsformat: {v}")
        return v


# ============== CORE BUSINESS LOGIC ==============

async def get_holidays_config() -> List[dict]:
    """Hole konfigurierte Feiertage aus der Datenbank"""
    holidays = await db.capacity_holidays.find(
        {"archived": {"$ne": True}}
    ).to_list(100)
    return holidays


async def get_day_type(target_date: date) -> Tuple[DayType, Optional[dict]]:
    """
    Ermittle den Tagestyp für ein Datum.
    Returns: (day_type, holiday_config or None)
    """
    date_str = target_date.strftime("%Y-%m-%d")
    
    # 1. Prüfe konfigurierte Feiertage
    holiday = await db.capacity_holidays.find_one({
        "date": date_str,
        "archived": {"$ne": True}
    })
    
    if holiday:
        return DayType.HOLIDAY, holiday
    
    # 2. Prüfe Standard-Feiertage aus Settings
    settings_holidays = await db.settings.find_one({"key": "holidays"})
    if settings_holidays:
        holiday_dates = settings_holidays.get("value", [])
        if isinstance(holiday_dates, str):
            holiday_dates = holiday_dates.split(",")
        if date_str in holiday_dates:
            return DayType.HOLIDAY, {"date": date_str, "name": "Feiertag"}
    
    # 3. Prüfe Wochenende
    weekday = target_date.weekday()
    if weekday >= 5:  # Samstag (5) oder Sonntag (6)
        return DayType.WEEKEND, None
    
    return DayType.WEEKDAY, None


async def get_capacity_config(target_date: date) -> dict:
    """
    Hole Kapazitätskonfiguration für ein Datum.
    Prüft: 1. Datum-spezifische Ausnahme, 2. Tagestyp-Config, 3. Defaults
    """
    date_str = target_date.strftime("%Y-%m-%d")
    
    # 1. Datum-spezifische Override
    override = await db.capacity_overrides.find_one({
        "date": date_str,
        "archived": {"$ne": True}
    })
    
    if override:
        return {
            "source": "override",
            "capacity_per_seating": override.get("capacity_per_seating", DEFAULT_CAPACITY_PER_SEATING),
            "block_duration_minutes": override.get("block_duration_minutes", DEFAULT_BLOCK_DURATION_MINUTES),
            "seatings_override": override.get("seatings_override"),
            "notes": override.get("notes", "")
        }
    
    # 2. Hole Tagestyp
    day_type, holiday_config = await get_day_type(target_date)
    
    if day_type == DayType.HOLIDAY and holiday_config:
        return {
            "source": "holiday",
            "day_type": day_type.value,
            "holiday_name": holiday_config.get("name", "Feiertag"),
            "capacity_per_seating": holiday_config.get("capacity_per_seating", DEFAULT_CAPACITY_PER_SEATING),
            "block_duration_minutes": holiday_config.get("block_duration_minutes", HOLIDAY_BLOCK_DURATION_MINUTES),
            "num_seatings": holiday_config.get("num_seatings", 4),
            "first_seating_start": holiday_config.get("first_seating_start", "11:00")
        }
    
    # 3. Defaults basierend auf Tagestyp
    return {
        "source": "default",
        "day_type": day_type.value,
        "capacity_per_seating": DEFAULT_CAPACITY_PER_SEATING,
        "block_duration_minutes": DEFAULT_BLOCK_DURATION_MINUTES if day_type != DayType.HOLIDAY else HOLIDAY_BLOCK_DURATION_MINUTES
    }


async def get_closing_time(target_date: date) -> Optional[str]:
    """Hole Schließzeit für ein Datum aus Öffnungszeiten"""
    effective_hours = await calculate_effective_hours(target_date)
    
    if not effective_hours.get("is_open", False):
        return None
    
    blocks = effective_hours.get("blocks", [])
    if blocks:
        # Nimm die späteste Endzeit
        latest_end = "00:00"
        for block in blocks:
            end = block.get("end", "00:00")
            if time_to_minutes(end) > time_to_minutes(latest_end):
                latest_end = end
        return latest_end
    
    return None


def generate_seatings_weekend(closing_time: str, block_duration: int = 120) -> List[dict]:
    """
    Generiere Durchgänge für Wochenende (Sa/So).
    
    Regeln:
    - Durchgang 1: 11:00-12:00 → Slots: 11:00, 11:30, 12:00
    - Durchgang 2: 13:00-14:00 → Slots: 13:00, 13:30, 14:00
    - Ab 16:00: alle 30 Min bis letzte Reservierung (Schließzeit - 90 Min)
    """
    seatings = []
    
    # Durchgang 1: Mittags früh
    seatings.append({
        "seating_number": 1,
        "name": "Durchgang 1 (Mittag)",
        "start_time": "11:00",
        "end_time": "12:00",
        "slots": ["11:00", "11:30", "12:00"],
        "capacity": DEFAULT_CAPACITY_PER_SEATING
    })
    
    # Durchgang 2: Mittags spät
    seatings.append({
        "seating_number": 2,
        "name": "Durchgang 2 (Mittag)",
        "start_time": "13:00",
        "end_time": "14:00",
        "slots": ["13:00", "13:30", "14:00"],
        "capacity": DEFAULT_CAPACITY_PER_SEATING
    })
    
    # Abend: ab 16:00 alle 30 Min
    closing_min = time_to_minutes(closing_time) if closing_time else time_to_minutes("20:00")
    # Letzte Reservierung = Schließzeit - 90 Minuten
    last_reservation_min = closing_min - 90
    
    evening_slots = []
    current = time_to_minutes("16:00")
    while current <= last_reservation_min:
        evening_slots.append(minutes_to_time(current))
        current += 30
    
    if evening_slots:
        seatings.append({
            "seating_number": 3,
            "name": "Abendservice",
            "start_time": "16:00",
            "end_time": minutes_to_time(last_reservation_min),
            "slots": evening_slots,
            "capacity": DEFAULT_CAPACITY_PER_SEATING
        })
    
    return seatings


def generate_seatings_holiday(
    num_seatings: int = 4,
    first_start: str = "11:00",
    block_duration: int = 140,
    closing_time: str = "21:00"
) -> List[dict]:
    """
    Generiere Durchgänge für Feiertage.
    
    Regeln:
    - 4 Durchgänge, je 3 Slots, Kapazität 95
    - Blockdauer: 140 Min (2:10 + 0:10)
    - Durchgang 1: 11:00, 11:30, 12:00
    - Folge-Durchgänge: Start = Ende vorheriger + Blockdauer (gerundet auf 30 Min)
    """
    seatings = []
    
    first_start_min = time_to_minutes(first_start)
    
    for i in range(num_seatings):
        if i == 0:
            seating_start_min = first_start_min
        else:
            # Berechne Start basierend auf vorherigem Durchgang + Blockdauer
            prev_last_slot_min = time_to_minutes(seatings[i-1]["slots"][-1])
            seating_start_min = round_to_slot(prev_last_slot_min + block_duration, 30)
        
        # 3 Slots pro Durchgang (30-Min-Raster)
        slots = [
            minutes_to_time(seating_start_min),
            minutes_to_time(seating_start_min + 30),
            minutes_to_time(seating_start_min + 60)
        ]
        
        seating_end_min = seating_start_min + 60
        
        seatings.append({
            "seating_number": i + 1,
            "name": f"Durchgang {i + 1}",
            "start_time": minutes_to_time(seating_start_min),
            "end_time": minutes_to_time(seating_end_min),
            "slots": slots,
            "capacity": DEFAULT_CAPACITY_PER_SEATING
        })
    
    return seatings


def generate_seatings_weekday(closing_time: str, block_duration: int = 120) -> List[dict]:
    """
    Generiere Durchgänge für Wochentage.
    
    Regeln:
    - Mittags: 11:30 - 14:00 alle 30 Min
    - Abends: 17:00 bis letzte Reservierung (Schließzeit - 90 Min)
    """
    seatings = []
    closing_min = time_to_minutes(closing_time) if closing_time else time_to_minutes("20:00")
    last_reservation_min = closing_min - 90
    
    # Mittags
    lunch_slots = []
    current = time_to_minutes("11:30")
    while current <= time_to_minutes("14:00"):
        lunch_slots.append(minutes_to_time(current))
        current += 30
    
    if lunch_slots:
        seatings.append({
            "seating_number": 1,
            "name": "Mittagsservice",
            "start_time": "11:30",
            "end_time": "14:00",
            "slots": lunch_slots,
            "capacity": DEFAULT_CAPACITY_PER_SEATING
        })
    
    # Abends
    evening_slots = []
    current = time_to_minutes("17:00")
    while current <= last_reservation_min:
        evening_slots.append(minutes_to_time(current))
        current += 30
    
    if evening_slots:
        seatings.append({
            "seating_number": 2,
            "name": "Abendservice",
            "start_time": "17:00",
            "end_time": minutes_to_time(last_reservation_min),
            "slots": evening_slots,
            "capacity": DEFAULT_CAPACITY_PER_SEATING
        })
    
    return seatings


async def calculate_seatings_and_slots(target_date: date) -> dict:
    """
    KERN-LOGIK: Berechne Durchgänge und Slots für ein Datum.
    """
    date_str = target_date.strftime("%Y-%m-%d")
    weekday = target_date.weekday()
    weekday_names = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    
    # Hole Konfiguration
    config = await get_capacity_config(target_date)
    closing_time = await get_closing_time(target_date)
    
    result = {
        "date": date_str,
        "weekday": weekday,
        "weekday_de": weekday_names[weekday],
        "day_type": config.get("day_type", "weekday"),
        "config_source": config.get("source", "default"),
        "capacity_per_seating": config.get("capacity_per_seating", DEFAULT_CAPACITY_PER_SEATING),
        "block_duration_minutes": config.get("block_duration_minutes", DEFAULT_BLOCK_DURATION_MINUTES),
        "closing_time": closing_time,
        "seatings": [],
        "all_slots": [],
        "notes": []
    }
    
    # Prüfe ob Restaurant geöffnet ist
    if not closing_time:
        result["open"] = False
        result["notes"].append("Restaurant geschlossen")
        return result
    
    result["open"] = True
    
    # Manuelle Override?
    if config.get("seatings_override"):
        result["seatings"] = config["seatings_override"]
        result["notes"].append("Manuelle Durchgänge (Override)")
    else:
        # Generiere basierend auf Tagestyp
        day_type = config.get("day_type", "weekday")
        block_duration = config.get("block_duration_minutes", DEFAULT_BLOCK_DURATION_MINUTES)
        
        if day_type == "holiday":
            result["seatings"] = generate_seatings_holiday(
                num_seatings=config.get("num_seatings", 4),
                first_start=config.get("first_seating_start", "11:00"),
                block_duration=block_duration,
                closing_time=closing_time
            )
            if config.get("holiday_name"):
                result["notes"].append(f"Feiertag: {config['holiday_name']}")
        elif day_type == "weekend":
            result["seatings"] = generate_seatings_weekend(closing_time, block_duration)
            result["notes"].append("Wochenend-Regelung")
        else:
            result["seatings"] = generate_seatings_weekday(closing_time, block_duration)
    
    # Sammle alle Slots mit Seating-Zuordnung
    for seating in result["seatings"]:
        for slot in seating.get("slots", []):
            result["all_slots"].append({
                "time": slot,
                "seating_number": seating["seating_number"],
                "seating_name": seating["name"]
            })
    
    # Sortiere Slots nach Zeit
    result["all_slots"].sort(key=lambda x: time_to_minutes(x["time"]))
    
    return result


async def get_reservations_for_date(target_date: date) -> List[dict]:
    """Hole alle Reservierungen für ein Datum"""
    date_str = target_date.strftime("%Y-%m-%d")
    
    reservations = await db.reservations.find({
        "date": date_str,
        "status": {"$nin": ["cancelled", "storniert", "no_show"]},
        "archived": {"$ne": True}
    }).to_list(500)
    
    return reservations


async def calculate_slot_capacity(target_date: date) -> dict:
    """
    Berechne Kapazität pro Slot für ein Datum.
    
    Returns: {
        "date": "2025-12-28",
        "day_type": "weekend",
        "capacity_per_seating": 95,
        "block_duration_minutes": 120,
        "slots": [
            {
                "time": "11:00",
                "seating": 1,
                "capacity_total": 95,
                "capacity_used": 12,
                "capacity_available": 83,
                "disabled": false,
                "reason": null
            },
            ...
        ]
    }
    """
    # Hole Durchgänge und Slots
    seatings_data = await calculate_seatings_and_slots(target_date)
    
    if not seatings_data.get("open", True):
        return {
            "date": seatings_data["date"],
            "open": False,
            "slots": [],
            "notes": seatings_data.get("notes", [])
        }
    
    # Hole bestehende Reservierungen
    reservations = await get_reservations_for_date(target_date)
    
    # Berechne belegte Plätze pro Slot
    slot_usage = {}  # time -> total party_size
    
    for res in reservations:
        res_time = res.get("time")
        party_size = res.get("party_size", res.get("guests", 1))
        
        if res_time:
            if res_time not in slot_usage:
                slot_usage[res_time] = 0
            slot_usage[res_time] += party_size
    
    # Berechne Kapazität pro Slot
    capacity_per_seating = seatings_data.get("capacity_per_seating", DEFAULT_CAPACITY_PER_SEATING)
    slots_result = []
    
    # Gruppiere Slots nach Seating für gemeinsame Kapazität
    seating_usage = {}  # seating_number -> total used
    
    for slot_info in seatings_data.get("all_slots", []):
        slot_time = slot_info["time"]
        seating_num = slot_info["seating_number"]
        
        if seating_num not in seating_usage:
            seating_usage[seating_num] = 0
        
        # Addiere Nutzung aus diesem Slot zum Seating
        seating_usage[seating_num] += slot_usage.get(slot_time, 0)
    
    # Jetzt berechne Verfügbarkeit pro Slot
    for slot_info in seatings_data.get("all_slots", []):
        slot_time = slot_info["time"]
        seating_num = slot_info["seating_number"]
        
        # Kapazität für diesen Durchgang
        total = capacity_per_seating
        used = seating_usage.get(seating_num, 0)
        available = max(0, total - used)
        
        slot_result = {
            "time": slot_time,
            "seating": seating_num,
            "seating_name": slot_info.get("seating_name", f"Durchgang {seating_num}"),
            "capacity_total": total,
            "capacity_used": used,
            "capacity_available": available,
            "disabled": available <= 0,
            "reason": "Ausgebucht" if available <= 0 else None
        }
        
        slots_result.append(slot_result)
    
    return {
        "date": seatings_data["date"],
        "weekday_de": seatings_data["weekday_de"],
        "day_type": seatings_data["day_type"],
        "open": True,
        "capacity_per_seating": capacity_per_seating,
        "block_duration_minutes": seatings_data["block_duration_minutes"],
        "closing_time": seatings_data["closing_time"],
        "seatings": seatings_data["seatings"],
        "slots": slots_result,
        "notes": seatings_data.get("notes", [])
    }


# ============== API ENDPOINTS ==============

@capacity_router.get(
    "/reservations/slots",
    summary="Verfügbare Slots mit Kapazität",
    description="Liefert alle Slots für ein Datum mit Restkapazität und disabled-Status."
)
async def get_reservation_slots(
    date: str = Query(..., description="Datum (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user)
):
    """
    GET /api/reservations/slots?date=YYYY-MM-DD
    
    Liefert Slots + Restkapazität + disabled=true/false
    """
    try:
        target = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationException("Ungültiges Datumsformat (YYYY-MM-DD erwartet)")
    
    return await calculate_slot_capacity(target)


@capacity_router.get(
    "/public/reservation-slots",
    summary="Öffentliche Slot-Abfrage mit Kapazität",
    description="Für Buchungs-Widget: Slots mit Verfügbarkeit ohne Auth."
)
async def get_public_reservation_slots(
    date: str = Query(..., description="Datum (YYYY-MM-DD)")
):
    """
    GET /api/public/reservation-slots?date=YYYY-MM-DD
    """
    try:
        target = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationException("Ungültiges Datumsformat")
    
    # Prüfe Vorlaufzeit
    today = datetime.now(timezone.utc).date()
    
    if target < today:
        return {
            "date": date,
            "open": False,
            "slots": [],
            "notes": ["Datum liegt in der Vergangenheit"]
        }
    
    if (target - today).days > 90:
        return {
            "date": date,
            "open": False,
            "slots": [],
            "notes": ["Buchung maximal 90 Tage im Voraus"]
        }
    
    result = await calculate_slot_capacity(target)
    
    # Für heute: Vergangene Slots entfernen
    if target == today:
        now = datetime.now(timezone.utc)
        min_time = (now + timedelta(hours=2)).strftime("%H:%M")
        result["slots"] = [s for s in result["slots"] if s["time"] >= min_time]
        
        if not result["slots"]:
            result["notes"].append("Keine Slots mehr verfügbar (min. 2h Vorlauf)")
    
    return result


# ============== ADMIN ENDPOINTS: HOLIDAYS ==============

@capacity_router.get(
    "/admin/capacity-holidays",
    summary="Konfigurierte Feiertage abrufen"
)
async def list_capacity_holidays(
    year: Optional[int] = None,
    current_user: dict = Depends(require_admin)
):
    """GET /api/admin/capacity-holidays"""
    query = {"archived": {"$ne": True}}
    
    if year:
        query["date"] = {"$regex": f"^{year}"}
    
    holidays = await db.capacity_holidays.find(
        query, {"_id": 0}
    ).sort("date", 1).to_list(100)
    
    return holidays


@capacity_router.post(
    "/admin/capacity-holidays",
    status_code=201,
    summary="Feiertag konfigurieren"
)
async def create_capacity_holiday(
    data: HolidayConfigCreate,
    current_user: dict = Depends(require_admin)
):
    """POST /api/admin/capacity-holidays"""
    
    # Prüfe ob bereits existiert
    existing = await db.capacity_holidays.find_one({
        "date": data.date,
        "archived": {"$ne": True}
    })
    
    if existing:
        raise ConflictException(f"Feiertag für {data.date} existiert bereits")
    
    holiday = {
        "id": str(uuid.uuid4()),
        "date": data.date,
        "name": data.name,
        "block_duration_minutes": data.block_duration_minutes,
        "num_seatings": data.num_seatings,
        "first_seating_start": data.first_seating_start,
        "capacity_per_seating": data.capacity_per_seating,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "archived": False
    }
    
    await db.capacity_holidays.insert_one(holiday)
    
    await create_audit_log(
        actor=current_user,
        action="create",
        entity="capacity_holiday",
        entity_id=holiday["id"],
        after=safe_dict_for_audit(holiday)
    )
    
    logger.info(f"Feiertag '{data.name}' ({data.date}) konfiguriert von {current_user.get('email')}")
    
    holiday.pop("_id", None)
    return holiday


@capacity_router.delete(
    "/admin/capacity-holidays/{holiday_id}",
    status_code=204,
    summary="Feiertag-Konfiguration löschen"
)
async def delete_capacity_holiday(
    holiday_id: str,
    current_user: dict = Depends(require_admin)
):
    """DELETE /api/admin/capacity-holidays/{id}"""
    
    holiday = await db.capacity_holidays.find_one({
        "id": holiday_id,
        "archived": {"$ne": True}
    })
    
    if not holiday:
        raise NotFoundException("Feiertag-Konfiguration nicht gefunden")
    
    await db.capacity_holidays.update_one(
        {"id": holiday_id},
        {"$set": {"archived": True, "updated_at": now_iso()}}
    )
    
    await create_audit_log(
        actor=current_user,
        action="delete",
        entity="capacity_holiday",
        entity_id=holiday_id
    )
    
    return None


# ============== ADMIN ENDPOINTS: OVERRIDES ==============

@capacity_router.get(
    "/admin/capacity-overrides",
    summary="Kapazitäts-Overrides abrufen"
)
async def list_capacity_overrides(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    current_user: dict = Depends(require_admin)
):
    """GET /api/admin/capacity-overrides"""
    query = {"archived": {"$ne": True}}
    
    if from_date:
        query["date"] = {"$gte": from_date}
    if to_date:
        if "date" in query:
            query["date"]["$lte"] = to_date
        else:
            query["date"] = {"$lte": to_date}
    
    overrides = await db.capacity_overrides.find(
        query, {"_id": 0}
    ).sort("date", 1).to_list(100)
    
    return overrides


@capacity_router.post(
    "/admin/capacity-overrides",
    status_code=201,
    summary="Kapazitäts-Override erstellen"
)
async def create_capacity_override(
    date: str = Query(..., description="Datum (YYYY-MM-DD)"),
    capacity_per_seating: int = Query(95, ge=1, le=500),
    block_duration_minutes: int = Query(120, ge=60, le=240),
    notes: Optional[str] = None,
    current_user: dict = Depends(require_admin)
):
    """POST /api/admin/capacity-overrides"""
    
    # Validiere Datum
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise ValidationException("Ungültiges Datumsformat")
    
    # Prüfe ob bereits existiert
    existing = await db.capacity_overrides.find_one({
        "date": date,
        "archived": {"$ne": True}
    })
    
    if existing:
        raise ConflictException(f"Override für {date} existiert bereits")
    
    override = {
        "id": str(uuid.uuid4()),
        "date": date,
        "capacity_per_seating": capacity_per_seating,
        "block_duration_minutes": block_duration_minutes,
        "notes": notes,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "archived": False
    }
    
    await db.capacity_overrides.insert_one(override)
    
    await create_audit_log(
        actor=current_user,
        action="create",
        entity="capacity_override",
        entity_id=override["id"],
        after=safe_dict_for_audit(override)
    )
    
    logger.info(f"Kapazitäts-Override für {date} erstellt von {current_user.get('email')}")
    
    override.pop("_id", None)
    return override


@capacity_router.delete(
    "/admin/capacity-overrides/{override_id}",
    status_code=204,
    summary="Kapazitäts-Override löschen"
)
async def delete_capacity_override(
    override_id: str,
    current_user: dict = Depends(require_admin)
):
    """DELETE /api/admin/capacity-overrides/{id}"""
    
    override = await db.capacity_overrides.find_one({
        "id": override_id,
        "archived": {"$ne": True}
    })
    
    if not override:
        raise NotFoundException("Override nicht gefunden")
    
    await db.capacity_overrides.update_one(
        {"id": override_id},
        {"$set": {"archived": True, "updated_at": now_iso()}}
    )
    
    await create_audit_log(
        actor=current_user,
        action="delete",
        entity="capacity_override",
        entity_id=override_id
    )
    
    return None


# ============== DEBUG ENDPOINT ==============

@capacity_router.get(
    "/admin/capacity-debug",
    summary="Debug: Kapazitätsberechnung für Datum",
    description="Zeigt detaillierte Berechnung für ein Datum."
)
async def debug_capacity(
    date: str = Query(..., description="Datum (YYYY-MM-DD)"),
    current_user: dict = Depends(require_admin)
):
    """GET /api/admin/capacity-debug?date=YYYY-MM-DD"""
    try:
        target = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationException("Ungültiges Datumsformat")
    
    # Sammle alle Debug-Infos
    day_type, holiday_config = await get_day_type(target)
    config = await get_capacity_config(target)
    closing_time = await get_closing_time(target)
    seatings = await calculate_seatings_and_slots(target)
    capacity = await calculate_slot_capacity(target)
    
    return {
        "date": date,
        "day_type_detection": {
            "day_type": day_type.value,
            "holiday_config": holiday_config
        },
        "capacity_config": config,
        "closing_time": closing_time,
        "seatings_calculation": seatings,
        "final_capacity": capacity
    }
