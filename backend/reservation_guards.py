"""
GastroCore Reservation Guards Module
================================================================================
Backend-Guards für Modul 20 - Reservierung

IMPLEMENTIERTE GUARDS:
B1) Standarddauer erzwingen (115 Minuten)
B2) Event sperrt à la carte
B3) Slots bei Event deaktivieren
B4) Wartelisten-Trigger bei Stornierung
B5) Wartelisten-Bestätigungsfenster (24h)

C1) Gäste pro Stunde aggregieren
C2) Event-Flag prüfen

KEINE PARALLELENTWICKLUNG - NUR GUARDS AUF BESTEHENDEM SYSTEM!
"""

from datetime import datetime, timezone, timedelta, date
from typing import Optional, Dict, Any, List, Tuple
import logging

from core.database import db
from core.exceptions import ValidationException, ConflictException

logger = logging.getLogger(__name__)


# ============== CONSTANTS ==============
# B1: Standarddauer für normale Reservierungen
STANDARD_RESERVATION_DURATION_MINUTES = 115  # 1:55 für Gast

# B5: Wartelisten-Bestätigungsfenster
WAITLIST_OFFER_VALIDITY_HOURS = 24


# ============== GUARD B1: STANDARDDAUER ERZWINGEN ==============

def enforce_standard_duration(data: dict, is_event: bool = False) -> dict:
    """
    B1) Standarddauer erzwingen
    - Normale Reservierung = 115 Minuten (fest)
    - Keine manuelle Dauer für normale Reservierungen
    - Event-Reservierungen können eigene Dauer haben
    
    Returns: data mit korrigierter duration_minutes
    """
    if is_event:
        # Event-Reservierungen behalten ihre Dauer
        return data
    
    # Normale Reservierung: Dauer immer 115 Minuten
    data["duration_minutes"] = STANDARD_RESERVATION_DURATION_MINUTES
    
    # Warnung loggen wenn manuelle Dauer übergeben wurde
    if "duration_minutes" in data and data.get("_original_duration"):
        logger.warning(
            f"Manuelle Dauer {data['_original_duration']} ignoriert. "
            f"Standarddauer {STANDARD_RESERVATION_DURATION_MINUTES} Min verwendet."
        )
    
    return data


def calculate_end_time(start_time: str, duration_minutes: int = STANDARD_RESERVATION_DURATION_MINUTES) -> str:
    """
    Berechne end_time aus start_time + duration.
    
    Args:
        start_time: "HH:MM"
        duration_minutes: Dauer in Minuten (default: 115)
    
    Returns:
        end_time als "HH:MM"
    """
    hours, minutes = map(int, start_time.split(":"))
    total_minutes = hours * 60 + minutes + duration_minutes
    
    end_hours = (total_minutes // 60) % 24
    end_minutes = total_minutes % 60
    
    return f"{end_hours:02d}:{end_minutes:02d}"


# ============== GUARD B2: EVENT SPERRT À LA CARTE ==============

async def check_event_blocks_reservation(
    date_str: str,
    time_str: str,
    duration_minutes: int = STANDARD_RESERVATION_DURATION_MINUTES
) -> Tuple[bool, Optional[dict]]:
    """
    B2) Prüfe ob ein Event normale Reservierungen blockiert.
    
    Args:
        date_str: "YYYY-MM-DD"
        time_str: "HH:MM"
        duration_minutes: Geplante Reservierungsdauer
    
    Returns:
        (is_blocked, event_info or None)
    """
    # Hole alle aktiven Events für das Datum
    events = await db.events.find({
        "archived": {"$ne": True},
        "status": {"$in": ["published", "active"]},
        "$or": [
            {"date": date_str},
            {"event_date": date_str},
            {"dates": date_str}  # Für Multi-Date Events
        ]
    }).to_list(50)
    
    if not events:
        return False, None
    
    # Konvertiere Reservierungszeit zu Minuten
    res_start_minutes = _time_to_minutes(time_str)
    res_end_minutes = res_start_minutes + duration_minutes
    
    for event in events:
        # Hole Event-Zeitraum
        event_start = event.get("start_time") or event.get("event_start_time") or "00:00"
        event_end = event.get("end_time") or event.get("event_end_time") or "23:59"
        
        event_start_minutes = _time_to_minutes(event_start)
        event_end_minutes = _time_to_minutes(event_end)
        
        # Prüfe Überschneidung
        if _times_overlap(res_start_minutes, res_end_minutes, event_start_minutes, event_end_minutes):
            # Prüfe ob Event normale Reservierungen blockiert
            blocks_normal = event.get("blocks_normal_reservations", True)
            reservation_type = event.get("reservation_type", "event_only")
            
            if blocks_normal or reservation_type == "event_only":
                return True, {
                    "event_id": event.get("id"),
                    "event_title": event.get("title"),
                    "event_start": event_start,
                    "event_end": event_end,
                    "message": f"Event '{event.get('title')}' blockiert normale Reservierungen von {event_start} bis {event_end}"
                }
    
    return False, None


async def guard_event_blocks_reservation(
    date_str: str,
    time_str: str,
    event_id: Optional[str] = None,
    duration_minutes: int = STANDARD_RESERVATION_DURATION_MINUTES
) -> None:
    """
    B2) Guard: Wirft Exception wenn Event normale Reservierung blockiert.
    
    Wenn event_id übergeben wird, ist es eine Event-Buchung und der Guard greift nicht.
    """
    # Event-Buchungen sind erlaubt
    if event_id:
        return
    
    is_blocked, event_info = await check_event_blocks_reservation(date_str, time_str, duration_minutes)
    
    if is_blocked:
        raise ConflictException(
            event_info.get("message", "Event blockiert normale Reservierungen in diesem Zeitraum")
        )


# ============== GUARD B3: SLOTS BEI EVENT DEAKTIVIEREN ==============

async def get_event_blocked_slots(date_str: str) -> List[str]:
    """
    B3) Hole alle Slots, die durch Events blockiert sind.
    
    Diese Slots werden bei /public/slots als disabled markiert.
    
    Returns:
        Liste von Zeitslots ["18:00", "18:30", ...] die blockiert sind
    """
    blocked_slots = []
    
    events = await db.events.find({
        "archived": {"$ne": True},
        "status": {"$in": ["published", "active"]},
        "$or": [
            {"date": date_str},
            {"event_date": date_str},
            {"dates": date_str}
        ]
    }).to_list(50)
    
    for event in events:
        if not event.get("blocks_normal_reservations", True):
            continue
        
        event_start = event.get("start_time") or event.get("event_start_time")
        event_end = event.get("end_time") or event.get("event_end_time")
        
        if not event_start or not event_end:
            continue
        
        # Generiere alle 30-Min Slots im Event-Zeitraum
        start_minutes = _time_to_minutes(event_start)
        end_minutes = _time_to_minutes(event_end)
        
        current = start_minutes
        while current < end_minutes:
            slot_time = _minutes_to_time(current)
            if slot_time not in blocked_slots:
                blocked_slots.append(slot_time)
            current += 30
    
    return sorted(blocked_slots)


async def is_event_active_at(date_str: str, time_str: str) -> Tuple[bool, Optional[dict]]:
    """
    C2) Prüfe ob zu einem Zeitpunkt ein Event aktiv ist.
    
    Returns:
        (event_active, event_info or None)
    """
    is_blocked, event_info = await check_event_blocks_reservation(date_str, time_str, 0)
    return is_blocked, event_info


# ============== GUARD B4: WARTELISTEN-TRIGGER ==============

async def should_trigger_waitlist(
    old_status: str,
    new_status: str,
    reservation: dict
) -> bool:
    """
    B4) Prüfe ob Warteliste getriggert werden soll.
    
    REGEL: Nur bei Statuswechsel → STORNIERT
    NICHT bei: NO_SHOW, ABGESCHLOSSEN
    """
    if new_status != "storniert":
        return False
    
    # Nur triggern wenn vorher aktiv (neu, bestaetigt)
    if old_status not in ["neu", "bestaetigt"]:
        return False
    
    return True


async def process_waitlist_on_cancellation(reservation: dict) -> Optional[dict]:
    """
    B4) Verarbeite Warteliste bei Stornierung.
    
    Findet ersten passenden Wartelisten-Eintrag und sendet Angebot.
    
    Returns:
        Wartelisten-Eintrag der informiert wurde, oder None
    """
    date_str = reservation.get("date")
    party_size = reservation.get("party_size", 2)
    
    if not date_str:
        return None
    
    # Finde passenden Wartelisten-Eintrag
    # Priorität: Datum-Match, dann Größe, dann Priorität
    waitlist_entry = await db.waitlist.find_one({
        "date": date_str,
        "status": "offen",
        "party_size": {"$lte": party_size + 2},  # Etwas Spielraum
        "archived": {"$ne": True}
    }, sort=[("priority", -1), ("created_at", 1)])
    
    if not waitlist_entry:
        return None
    
    # B5: Setze Ablaufzeit für Angebot
    expires_at = datetime.now(timezone.utc) + timedelta(hours=WAITLIST_OFFER_VALIDITY_HOURS)
    
    # Update Status auf "informiert" mit Ablaufzeit
    await db.waitlist.update_one(
        {"id": waitlist_entry["id"]},
        {"$set": {
            "status": "informiert",
            "offer_expires_at": expires_at.isoformat(),
            "offered_reservation_id": reservation.get("id"),
            "offered_time": reservation.get("time"),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    logger.info(f"Warteliste informiert: {waitlist_entry['id']} für Stornierung {reservation.get('id')}")
    
    return waitlist_entry


# ============== GUARD B5: WARTELISTEN-ABLAUF ==============

async def check_expired_waitlist_offers() -> int:
    """
    B5) Prüfe und verfalle abgelaufene Wartelisten-Angebote.
    
    Wird periodisch aufgerufen (z.B. via Scheduler).
    
    Returns:
        Anzahl verfallener Angebote
    """
    now = datetime.now(timezone.utc).isoformat()
    
    # Finde alle abgelaufenen Angebote
    result = await db.waitlist.update_many(
        {
            "status": "informiert",
            "offer_expires_at": {"$lt": now},
            "archived": {"$ne": True}
        },
        {"$set": {
            "status": "erledigt",
            "expired_reason": "offer_expired",
            "updated_at": now
        }}
    )
    
    if result.modified_count > 0:
        logger.info(f"{result.modified_count} Wartelisten-Angebote verfallen")
    
    return result.modified_count


async def is_waitlist_offer_valid(waitlist_id: str) -> Tuple[bool, Optional[str]]:
    """
    B5) Prüfe ob Wartelisten-Angebot noch gültig ist.
    
    Returns:
        (is_valid, error_message or None)
    """
    entry = await db.waitlist.find_one({"id": waitlist_id}, {"_id": 0})
    
    if not entry:
        return False, "Wartelisten-Eintrag nicht gefunden"
    
    if entry.get("status") != "informiert":
        return False, "Kein aktives Angebot vorhanden"
    
    expires_at = entry.get("offer_expires_at")
    if expires_at:
        try:
            expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > expires:
                return False, "Angebot ist abgelaufen (24h Frist überschritten)"
        except:
            pass
    
    return True, None


# ============== C1: GÄSTE PRO STUNDE AGGREGIEREN ==============

async def get_guests_per_hour(date_str: str) -> Dict[str, int]:
    """
    C1) Aggregiere Gästeanzahl pro Stunde für ein Datum.
    
    Für Modul 30 Vorbereitung (Schichtbelegung).
    
    Returns:
        {"10": 15, "11": 42, "12": 78, ...} - Gäste pro Stunde
    """
    pipeline = [
        {
            "$match": {
                "date": date_str,
                "archived": {"$ne": True},
                "status": {"$in": ["neu", "bestaetigt", "angekommen", "abgeschlossen"]}
            }
        },
        {
            "$addFields": {
                "hour": {"$substr": ["$time", 0, 2]}
            }
        },
        {
            "$group": {
                "_id": "$hour",
                "guests": {"$sum": "$party_size"}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    
    results = await db.reservations.aggregate(pipeline).to_list(24)
    
    return {r["_id"]: r["guests"] for r in results}


async def get_hourly_overview(date_str: str) -> List[Dict[str, Any]]:
    """
    C1) Erweiterte Stundenübersicht für Dashboard/Modul 30.
    
    Returns:
        [{"hour": "11", "guests": 45, "reservations": 12}, ...]
    """
    pipeline = [
        {
            "$match": {
                "date": date_str,
                "archived": {"$ne": True},
                "status": {"$in": ["neu", "bestaetigt", "angekommen", "abgeschlossen"]}
            }
        },
        {
            "$addFields": {
                "hour": {"$substr": ["$time", 0, 2]}
            }
        },
        {
            "$group": {
                "_id": "$hour",
                "guests": {"$sum": "$party_size"},
                "reservations": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    
    results = await db.reservations.aggregate(pipeline).to_list(24)
    
    return [
        {
            "hour": r["_id"],
            "hour_display": f"{r['_id']}:00",
            "guests": r["guests"],
            "reservations": r["reservations"]
        }
        for r in results
    ]


# ============== HELPER FUNCTIONS ==============

def _time_to_minutes(time_str: str) -> int:
    """Konvertiere HH:MM zu Minuten seit Mitternacht"""
    try:
        h, m = map(int, time_str.split(":"))
        return h * 60 + m
    except:
        return 0


def _minutes_to_time(minutes: int) -> str:
    """Konvertiere Minuten seit Mitternacht zu HH:MM"""
    h = (minutes // 60) % 24
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def _times_overlap(start1: int, end1: int, start2: int, end2: int) -> bool:
    """Prüfe ob zwei Zeitbereiche sich überschneiden"""
    return start1 < end2 and end1 > start2


# ============== INTEGRATION HELPERS ==============

async def apply_reservation_guards(
    data: dict,
    is_public: bool = False
) -> dict:
    """
    Wendet alle relevanten Guards auf Reservierungsdaten an.
    
    Args:
        data: Reservierungsdaten (date, time, party_size, event_id, ...)
        is_public: True wenn öffentliche Buchung (/public/book)
    
    Returns:
        Modifizierte Daten mit enforced Guards
    
    Raises:
        ConflictException: Wenn Event normale Reservierung blockiert
    """
    date_str = data.get("date")
    time_str = data.get("time")
    event_id = data.get("event_id")
    
    if not date_str or not time_str:
        return data
    
    # B1: Standarddauer erzwingen
    is_event = bool(event_id)
    data = enforce_standard_duration(data, is_event=is_event)
    
    # B2: Event-Block prüfen
    await guard_event_blocks_reservation(
        date_str, 
        time_str, 
        event_id=event_id,
        duration_minutes=data.get("duration_minutes", STANDARD_RESERVATION_DURATION_MINUTES)
    )
    
    # end_time berechnen wenn nicht vorhanden
    if "end_time" not in data:
        data["end_time"] = calculate_end_time(
            time_str, 
            data.get("duration_minutes", STANDARD_RESERVATION_DURATION_MINUTES)
        )
    
    return data
