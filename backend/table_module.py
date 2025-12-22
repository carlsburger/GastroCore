"""
GastroCore Table Management Module - Sprint: Tischplan & Belegung
==================================================================

FEATURES:
1. Tisch-Stammdaten mit Bereichen & Subbereichen
2. Tischkombinationen (zeitgebunden)
3. Belegungsberechnung
4. KI-Vorschläge für Tischzuweisungen

BEREICHE:
- Restaurant (Subbereiche: saal, wintergarten)
- Terrasse
- Event

REGELN:
- Kombinationen NUR innerhalb gleicher Bereiche & Subbereiche
- Tisch 3 ist Sonderfall (oval) - NIE kombinierbar

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


# ============== ENUMS ==============
class TableArea(str, Enum):
    RESTAURANT = "restaurant"
    TERRASSE = "terrasse"
    EVENT = "event"


class TableSubArea(str, Enum):
    SAAL = "saal"
    WINTERGARTEN = "wintergarten"


class OccupancyStatus(str, Enum):
    FREI = "frei"
    RESERVIERT = "reserviert"
    BELEGT = "belegt"
    GESPERRT = "gesperrt"


# ============== PYDANTIC MODELS ==============

# --- Tisch-Stammdaten ---
class TableCreate(BaseModel):
    """Tisch-Stammdaten erstellen"""
    table_number: str = Field(..., min_length=1, max_length=20)
    area: TableArea
    sub_area: Optional[TableSubArea] = None  # Nur für Restaurant
    seats_max: int = Field(..., ge=1, le=30)
    seats_default: Optional[int] = None  # Default = 4 oder seats_max wenn < 4
    combinable: bool = True
    combinable_with: List[str] = Field(default_factory=list)  # Tischnummern
    fixed: bool = False  # Nicht verschiebbar im grafischen Plan
    active: bool = True
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    notes: Optional[str] = None
    
    @field_validator('sub_area')
    @classmethod
    def validate_sub_area(cls, v, info):
        # sub_area nur bei Restaurant erlaubt
        area = info.data.get('area')
        if v and area != TableArea.RESTAURANT:
            raise ValueError("Subbereich nur für Restaurant erlaubt")
        return v


class TableUpdate(BaseModel):
    """Tisch-Stammdaten aktualisieren"""
    table_number: Optional[str] = None
    area: Optional[TableArea] = None
    sub_area: Optional[TableSubArea] = None
    seats_max: Optional[int] = Field(None, ge=1, le=30)
    seats_default: Optional[int] = None
    combinable: Optional[bool] = None
    combinable_with: Optional[List[str]] = None
    fixed: Optional[bool] = None
    active: Optional[bool] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    notes: Optional[str] = None


class TableResponse(BaseModel):
    """Tisch-Response"""
    id: str
    table_number: str
    area: str
    sub_area: Optional[str]
    seats_max: int
    seats_default: int
    combinable: bool
    combinable_with: List[str]
    fixed: bool
    active: bool
    position_x: Optional[int]
    position_y: Optional[int]
    notes: Optional[str]
    created_at: str
    updated_at: str


# --- Tischkombinationen ---
class TableCombinationCreate(BaseModel):
    """Tischkombination erstellen"""
    date: str  # YYYY-MM-DD
    time_slot: str  # z.B. "18:00-20:00" oder Zeit "18:00"
    table_ids: List[str] = Field(..., min_length=2)  # Mind. 2 Tische
    name: Optional[str] = None  # z.B. "Große Tafel Terrasse"
    reservation_id: Optional[str] = None
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Ungültiges Datumsformat (YYYY-MM-DD)")
        return v


class TableCombinationResponse(BaseModel):
    """Tischkombination Response"""
    id: str
    name: Optional[str]
    date: str
    time_slot: str
    table_ids: List[str]
    table_numbers: List[str]
    total_seats: int
    reservation_id: Optional[str]
    active: bool
    created_by: str
    created_at: str


# --- Belegung ---
class TableOccupancy(BaseModel):
    """Tisch-Belegungsstatus"""
    table_id: str
    table_number: str
    status: OccupancyStatus
    reservation_id: Optional[str] = None
    reservation: Optional[dict] = None
    combination_id: Optional[str] = None
    is_extended: bool = False


class OccupancyRequest(BaseModel):
    """Belegungsabfrage"""
    date: str
    time_slot: Optional[str] = None  # "18:00-20:00"
    time: Optional[str] = None  # "18:00"
    area: Optional[TableArea] = None


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


async def get_table_by_id(table_id: str) -> Optional[dict]:
    """Hole Tisch nach ID"""
    return await db.tables.find_one(
        {"id": table_id, "archived": False},
        {"_id": 0}
    )


async def get_table_by_number(table_number: str) -> Optional[dict]:
    """Hole Tisch nach Nummer"""
    return await db.tables.find_one(
        {"table_number": table_number, "archived": False},
        {"_id": 0}
    )


async def validate_combination_tables(table_ids: List[str]) -> Dict[str, Any]:
    """
    Validiere dass Tische kombiniert werden dürfen.
    Regeln:
    - Alle Tische müssen existieren und aktiv sein
    - Alle Tische müssen kombinierbar sein
    - Alle Tische müssen im gleichen Bereich sein
    - Alle Tische müssen im gleichen Subbereich sein (für Restaurant)
    - Tisch 3 darf NIE kombiniert werden
    """
    tables = []
    for tid in table_ids:
        table = await get_table_by_id(tid)
        if not table:
            return {"valid": False, "error": f"Tisch mit ID {tid} nicht gefunden"}
        if not table.get("active"):
            return {"valid": False, "error": f"Tisch {table['table_number']} ist nicht aktiv"}
        if not table.get("combinable", True):
            return {"valid": False, "error": f"Tisch {table['table_number']} ist nicht kombinierbar"}
        # Sonderfall: Tisch 3 (oval/Exot)
        if table.get("table_number") == "3":
            return {"valid": False, "error": "Tisch 3 (Exot/Oval) darf nicht kombiniert werden"}
        tables.append(table)
    
    if len(tables) < 2:
        return {"valid": False, "error": "Mindestens 2 Tische erforderlich"}
    
    # Prüfe gleicher Bereich
    areas = set(t["area"] for t in tables)
    if len(areas) > 1:
        return {"valid": False, "error": "Alle Tische müssen im gleichen Bereich sein"}
    
    # Prüfe gleicher Subbereich (für Restaurant)
    area = tables[0]["area"]
    if area == TableArea.RESTAURANT.value:
        sub_areas = set(t.get("sub_area") for t in tables)
        if len(sub_areas) > 1:
            return {
                "valid": False, 
                "error": "Tische aus Saal und Wintergarten dürfen NICHT kombiniert werden"
            }
    
    # Berechne Gesamtplätze
    total_seats = sum(t.get("seats_max", 0) for t in tables)
    table_numbers = [t["table_number"] for t in tables]
    
    return {
        "valid": True,
        "tables": tables,
        "total_seats": total_seats,
        "table_numbers": table_numbers,
        "area": area,
        "sub_area": tables[0].get("sub_area")
    }


async def check_combination_conflict(
    table_ids: List[str],
    date_str: str,
    time_slot: str,
    exclude_combination_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Prüfe ob einer der Tische bereits in einer aktiven Kombination ist.
    """
    query = {
        "date": date_str,
        "time_slot": time_slot,
        "active": True,
        "archived": False,
        "table_ids": {"$in": table_ids}
    }
    if exclude_combination_id:
        query["id"] = {"$ne": exclude_combination_id}
    
    existing = await db.table_combinations.find_one(query, {"_id": 0})
    
    if existing:
        return {
            "conflict": True,
            "existing_combination": existing,
            "message": f"Tisch bereits in Kombination '{existing.get('name', existing['id'])}'"
        }
    
    return {"conflict": False}


async def calculate_table_occupancy(
    date_str: str,
    time_str: Optional[str] = None,
    time_slot: Optional[str] = None,
    area: Optional[str] = None,
    duration_minutes: int = 110
) -> List[TableOccupancy]:
    """
    Berechne Belegungsstatus für alle Tische.
    Quelle der Wahrheit: Reservierungen + Kombinationen + Events.
    KEINE persistente occupancy-Tabelle.
    """
    # Alle aktiven Tische laden
    table_query = {"archived": False, "active": True}
    if area:
        table_query["area"] = area
    
    tables = await db.tables.find(table_query, {"_id": 0}).to_list(500)
    
    # Zeit-Bereich berechnen
    if time_str:
        start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=duration_minutes)
    elif time_slot:
        # Parse time_slot "18:00-20:00"
        parts = time_slot.split("-")
        start_dt = datetime.strptime(f"{date_str} {parts[0]}", "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(f"{date_str} {parts[1]}", "%Y-%m-%d %H:%M")
    else:
        # Ganzer Tag
        start_dt = datetime.strptime(f"{date_str} 00:00", "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(f"{date_str} 23:59", "%Y-%m-%d %H:%M")
    
    # Reservierungen laden
    res_query = {
        "date": date_str,
        "status": {"$in": ["neu", "bestaetigt", "angekommen"]},
        "archived": False
    }
    reservations = await db.reservations.find(res_query, {"_id": 0}).to_list(1000)
    
    # Aktive Kombinationen laden
    comb_query = {
        "date": date_str,
        "active": True,
        "archived": False
    }
    combinations = await db.table_combinations.find(comb_query, {"_id": 0}).to_list(100)
    
    # Events laden (für Sperrungen)
    event_query = {
        "date": date_str,
        "status": {"$in": ["published", "aktiv"]},
        "archived": False
    }
    events = await db.events.find(event_query, {"_id": 0}).to_list(50)
    
    # Belegung pro Tisch berechnen
    occupancy_list = []
    
    for table in tables:
        table_id = table["id"]
        table_number = table["table_number"]
        status = OccupancyStatus.FREI
        res_id = None
        res_data = None
        comb_id = None
        is_extended = False
        
        # Prüfe Reservierungen für diesen Tisch
        for res in reservations:
            if res.get("table_id") == table_id or res.get("table_number") == table_number:
                # Prüfe zeitliche Überlappung
                res_start = datetime.strptime(f"{res['date']} {res['time']}", "%Y-%m-%d %H:%M")
                res_duration = res.get("duration_minutes", 110)
                res_end = res_start + timedelta(minutes=res_duration)
                
                if start_dt < res_end and end_dt > res_start:
                    res_status = res.get("status")
                    if res_status == "angekommen":
                        status = OccupancyStatus.BELEGT
                    elif res_status in ["neu", "bestaetigt"]:
                        status = OccupancyStatus.RESERVIERT
                    res_id = res.get("id")
                    res_data = {
                        "id": res.get("id"),
                        "guest_name": res.get("guest_name"),
                        "party_size": res.get("party_size"),
                        "time": res.get("time"),
                        "status": res.get("status"),
                        "occasion": res.get("occasion"),
                        "allergies": res.get("allergies"),
                        "notes": res.get("notes"),
                        "is_extended": res.get("is_extended", False)
                    }
                    is_extended = res.get("is_extended", False)
                    break
        
        # Prüfe Kombinationen
        for comb in combinations:
            if table_id in comb.get("table_ids", []):
                comb_id = comb["id"]
                # Wenn Kombination eine Reservierung hat, Status übernehmen
                if comb.get("reservation_id") and not res_id:
                    res_id = comb["reservation_id"]
                    # Reservierung laden
                    comb_res = next(
                        (r for r in reservations if r.get("id") == res_id),
                        None
                    )
                    if comb_res:
                        if comb_res.get("status") == "angekommen":
                            status = OccupancyStatus.BELEGT
                        else:
                            status = OccupancyStatus.RESERVIERT
                        res_data = {
                            "id": comb_res.get("id"),
                            "guest_name": comb_res.get("guest_name"),
                            "party_size": comb_res.get("party_size"),
                            "time": comb_res.get("time"),
                            "status": comb_res.get("status"),
                            "combination_id": comb_id,
                            "combination_tables": comb.get("table_numbers", [])
                        }
                break
        
        # Prüfe Event-Sperrungen (für Event-Bereich)
        if table.get("area") == TableArea.EVENT.value:
            for event in events:
                # Event-Zeit kann in verschiedenen Formaten sein
                event_start = event.get("start_datetime", event.get("start_time", event.get("time", "")))
                if event_start:
                    try:
                        # Parse event datetime
                        if isinstance(event_start, str):
                            if "T" in event_start:
                                event_dt = datetime.fromisoformat(event_start.replace("Z", "+00:00"))
                            else:
                                event_dt = datetime.strptime(f"{date_str} {event_start}", "%Y-%m-%d %H:%M")
                        else:
                            event_dt = event_start
                        
                        # Event Cut-Off berücksichtigen (Standard: 120 Min)
                        cutoff_minutes = event.get("last_alacarte_reservation_minutes", 
                                                   event.get("last_alacarte_minutes_before", 120))
                        block_start = event_dt - timedelta(minutes=cutoff_minutes)
                        
                        if start_dt >= block_start:
                            status = OccupancyStatus.GESPERRT
                            event_time_str = event_dt.strftime("%H:%M") if hasattr(event_dt, 'strftime') else str(event_start)
                            res_data = {
                                "blocked_by": "event",
                                "event_id": event.get("id"),
                                "event_name": event.get("title", event.get("name")),
                                "message": f"Event ab {event_time_str}"
                            }
                            break
                    except (ValueError, TypeError):
                        # Wenn Event-Zeit nicht parsbar ist, ignorieren
                        pass
        
        occupancy_list.append(TableOccupancy(
            table_id=table_id,
            table_number=table_number,
            status=status,
            reservation_id=res_id,
            reservation=res_data,
            combination_id=comb_id,
            is_extended=is_extended
        ))
    
    return occupancy_list


async def suggest_tables_for_party(
    date_str: str,
    time_str: str,
    party_size: int,
    area: Optional[str] = None,
    duration_minutes: int = 110
) -> List[Dict[str, Any]]:
    """
    KI-Vorschläge für passende Tische/Kombinationen.
    Gibt Empfehlungen zurück, KEINE automatische Zuweisung.
    """
    suggestions = []
    
    # Belegung berechnen
    occupancy = await calculate_table_occupancy(date_str, time_str, area=area)
    free_tables = [o for o in occupancy if o.status == OccupancyStatus.FREI]
    
    # Alle Tische laden für Details
    table_docs = {t["id"]: t for t in await db.tables.find(
        {"archived": False, "active": True}, {"_id": 0}
    ).to_list(500)}
    
    # 1. Einzeltische die passen
    for occ in free_tables:
        table = table_docs.get(occ.table_id)
        if table and table.get("seats_max", 0) >= party_size:
            # Bewertung: Je näher an party_size, desto besser
            waste = table["seats_max"] - party_size
            score = 100 - (waste * 10)  # Weniger Platzverschwendung = höherer Score
            
            suggestions.append({
                "type": "single",
                "table_id": table["id"],
                "table_number": table["table_number"],
                "seats": table["seats_max"],
                "area": table["area"],
                "sub_area": table.get("sub_area"),
                "score": max(score, 0),
                "message": f"Tisch {table['table_number']} ({table['seats_max']} Plätze)"
            })
    
    # 2. Kombinationsvorschläge
    if party_size > 4:  # Nur für größere Gruppen
        # Gruppiere freie Tische nach Bereich+Subbereich
        grouped = {}
        for occ in free_tables:
            table = table_docs.get(occ.table_id)
            if table and table.get("combinable", True) and table.get("table_number") != "3":
                key = f"{table['area']}_{table.get('sub_area', '')}"
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(table)
        
        # Finde Kombinationen
        for key, tables in grouped.items():
            if len(tables) < 2:
                continue
            
            # Sortiere nach Plätzen
            tables.sort(key=lambda x: x["seats_max"], reverse=True)
            
            # Versuche 2er-Kombinationen
            for i, t1 in enumerate(tables):
                for t2 in tables[i+1:]:
                    combined_seats = t1["seats_max"] + t2["seats_max"]
                    if combined_seats >= party_size:
                        waste = combined_seats - party_size
                        score = 80 - (waste * 5)  # Kombinationen leicht niedriger bewertet
                        
                        suggestions.append({
                            "type": "combination",
                            "table_ids": [t1["id"], t2["id"]],
                            "table_numbers": [t1["table_number"], t2["table_number"]],
                            "seats": combined_seats,
                            "area": t1["area"],
                            "sub_area": t1.get("sub_area"),
                            "score": max(score, 0),
                            "message": f"Kombination Tisch {t1['table_number']} + {t2['table_number']} ({combined_seats} Plätze)"
                        })
    
    # Sortiere nach Score (höchster zuerst)
    suggestions.sort(key=lambda x: x["score"], reverse=True)
    
    return suggestions[:5]  # Max 5 Vorschläge


# ============== ROUTER ==============
table_router = APIRouter(prefix="/tables", tags=["Tables"])
combination_router = APIRouter(prefix="/table-combinations", tags=["Table Combinations"])


# ============== TISCH-STAMMDATEN ENDPOINTS ==============

@table_router.get("")
async def list_tables(
    area: Optional[TableArea] = None,
    sub_area: Optional[TableSubArea] = None,
    active_only: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Liste alle Tische"""
    query = {"archived": False}
    if area:
        query["area"] = area.value
    if sub_area:
        query["sub_area"] = sub_area.value
    if active_only:
        query["active"] = True
    
    tables = await db.tables.find(query, {"_id": 0}).sort([
        ("area", 1),
        ("sub_area", 1),
        ("sort_order", 1),
        ("table_number", 1)
    ]).to_list(500)
    
    return tables


@table_router.get("/by-area/{area}")
async def get_tables_by_area(
    area: TableArea,
    sub_area: Optional[TableSubArea] = None,
    current_user: dict = Depends(get_current_user)
):
    """Hole Tische eines Bereichs"""
    query = {"area": area.value, "archived": False, "active": True}
    if sub_area:
        query["sub_area"] = sub_area.value
    
    tables = await db.tables.find(query, {"_id": 0}).sort("table_number", 1).to_list(100)
    
    # Gruppiere nach Subbereich (für Restaurant)
    if area == TableArea.RESTAURANT:
        result = {
            "saal": [t for t in tables if t.get("sub_area") == "saal"],
            "wintergarten": [t for t in tables if t.get("sub_area") == "wintergarten"],
            "total": len(tables)
        }
        return result
    
    return {"tables": tables, "total": len(tables)}


@table_router.get("/suggest")
async def suggest_tables(
    date_str: str = Query(..., alias="date"),
    time: str = Query(...),
    party_size: int = Query(..., ge=1, le=50),
    area: Optional[TableArea] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    KI-Vorschläge für passende Tische.
    Gibt Empfehlungen zurück - KEINE automatische Zuweisung.
    """
    suggestions = await suggest_tables_for_party(
        date,
        date_str,
        time,
        party_size,
        area=area.value if area else None
    )
    
    return {
        "date": date_str,
        "time": time,
        "party_size": party_size,
        "suggestions": suggestions,
        "message": "KI-Vorschläge - bitte manuell auswählen"
    }


@table_router.get("/{table_id}")
async def get_table(
    table_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Hole Tisch-Details"""
    table = await get_table_by_id(table_id)
    if not table:
        raise NotFoundException("Tisch")
    return table


@table_router.post("")
async def create_table(
    data: TableCreate,
    current_user: dict = Depends(require_admin)
):
    """Erstelle neuen Tisch (nur Admin)"""
    # Prüfe ob Tischnummer bereits existiert
    existing = await get_table_by_number(data.table_number)
    if existing:
        raise ConflictException(f"Tisch {data.table_number} existiert bereits")
    
    # Sub_area Pflicht für Restaurant
    if data.area == TableArea.RESTAURANT and not data.sub_area:
        raise ValidationException("Restaurant-Tische benötigen einen Subbereich (saal/wintergarten)")
    
    # Default seats_default
    seats_default = data.seats_default
    if seats_default is None:
        seats_default = min(4, data.seats_max)
    
    # Sonderfall Tisch 3: Immer nicht kombinierbar
    combinable = data.combinable
    if data.table_number == "3":
        combinable = False
    
    table_data = {
        "table_number": data.table_number,
        "area": data.area.value,
        "sub_area": data.sub_area.value if data.sub_area else None,
        "seats_max": data.seats_max,
        "seats_default": seats_default,
        "combinable": combinable,
        "combinable_with": data.combinable_with,
        "fixed": data.fixed,
        "active": data.active,
        "position_x": data.position_x,
        "position_y": data.position_y,
        "notes": data.notes
    }
    
    doc = create_entity(table_data)
    await db.tables.insert_one(doc)
    
    # Entferne _id für Audit und Response
    doc_clean = {k: v for k, v in doc.items() if k != "_id"}
    await create_audit_log(current_user, "table", doc["id"], "create", None, safe_dict_for_audit(doc_clean))
    
    return {"message": f"Tisch {data.table_number} erstellt", "id": doc["id"], "table": doc_clean}


@table_router.patch("/{table_id}")
async def update_table(
    table_id: str,
    data: TableUpdate,
    current_user: dict = Depends(require_admin)
):
    """Aktualisiere Tisch (nur Admin)"""
    table = await get_table_by_id(table_id)
    if not table:
        raise NotFoundException("Tisch")
    
    before = safe_dict_for_audit(table)
    
    update_data = {"updated_at": now_iso()}
    for field, value in data.model_dump(exclude_none=True).items():
        if isinstance(value, Enum):
            update_data[field] = value.value
        else:
            update_data[field] = value
    
    # Sonderfall Tisch 3
    if table.get("table_number") == "3" or data.table_number == "3":
        update_data["combinable"] = False
    
    await db.tables.update_one({"id": table_id}, {"$set": update_data})
    
    updated = await get_table_by_id(table_id)
    await create_audit_log(current_user, "table", table_id, "update", before, safe_dict_for_audit(updated))
    
    return {"message": "Tisch aktualisiert", "table": updated}


@table_router.delete("/{table_id}")
async def archive_table(
    table_id: str,
    current_user: dict = Depends(require_admin)
):
    """Archiviere Tisch (soft delete, nur Admin)"""
    table = await get_table_by_id(table_id)
    if not table:
        raise NotFoundException("Tisch")
    
    before = safe_dict_for_audit(table)
    await db.tables.update_one(
        {"id": table_id},
        {"$set": {"archived": True, "active": False, "updated_at": now_iso()}}
    )
    
    await create_audit_log(current_user, "table", table_id, "archive", before, {**before, "archived": True})
    
    return {"message": f"Tisch {table['table_number']} archiviert"}


# ============== TISCHKOMBINATIONEN ENDPOINTS ==============

@combination_router.get("")
async def list_combinations(
    date_filter: Optional[str] = Query(None, alias="date"),
    active_only: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Liste Tischkombinationen"""
    query = {"archived": False}
    if date_filter:
        query["date"] = date_filter
    if active_only:
        query["active"] = True
    
    combinations = await db.table_combinations.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return combinations


@combination_router.get("/for-date/{date_str}")
async def get_combinations_for_date(
    date_str: str,
    time_slot: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Hole aktive Kombinationen für ein Datum"""
    query = {"date": date_str, "active": True, "archived": False}
    if time_slot:
        query["time_slot"] = time_slot
    
    combinations = await db.table_combinations.find(query, {"_id": 0}).to_list(50)
    return combinations


@combination_router.post("")
async def create_combination(
    data: TableCombinationCreate,
    current_user: dict = Depends(require_manager)
):
    """Erstelle Tischkombination (Admin & Schichtleiter)"""
    # Validiere Tische
    validation = await validate_combination_tables(data.table_ids)
    if not validation["valid"]:
        raise ValidationException(validation["error"])
    
    # Prüfe Konflikte
    conflict = await check_combination_conflict(data.table_ids, data.date, data.time_slot)
    if conflict["conflict"]:
        raise ConflictException(conflict["message"])
    
    # Erstelle Kombination
    comb_data = {
        "name": data.name or f"Kombination {' + '.join(validation['table_numbers'])}",
        "date": data.date,
        "time_slot": data.time_slot,
        "table_ids": data.table_ids,
        "table_numbers": validation["table_numbers"],
        "total_seats": validation["total_seats"],
        "area": validation["area"],
        "sub_area": validation.get("sub_area"),
        "reservation_id": data.reservation_id,
        "active": True,
        "created_by": current_user.get("id")
    }
    
    doc = create_entity(comb_data)
    await db.table_combinations.insert_one(doc)
    
    # Entferne _id für Audit und Response
    doc_clean = {k: v for k, v in doc.items() if k != "_id"}
    await create_audit_log(current_user, "table_combination", doc["id"], "create", None, safe_dict_for_audit(doc_clean))
    
    return {
        "message": f"Kombination erstellt: {validation['table_numbers']}",
        "id": doc["id"],
        "combination": doc_clean
    }


@combination_router.patch("/{combination_id}/assign-reservation")
async def assign_reservation_to_combination(
    combination_id: str,
    reservation_id: str,
    current_user: dict = Depends(require_manager)
):
    """Weise Reservierung einer Kombination zu"""
    comb = await db.table_combinations.find_one(
        {"id": combination_id, "archived": False},
        {"_id": 0}
    )
    if not comb:
        raise NotFoundException("Tischkombination")
    
    # Prüfe Reservierung
    res = await db.reservations.find_one(
        {"id": reservation_id, "archived": False},
        {"_id": 0}
    )
    if not res:
        raise NotFoundException("Reservierung")
    
    await db.table_combinations.update_one(
        {"id": combination_id},
        {"$set": {"reservation_id": reservation_id, "updated_at": now_iso()}}
    )
    
    # Aktualisiere auch Reservierung
    await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": {
            "combination_id": combination_id,
            "table_ids": comb["table_ids"],
            "table_numbers": comb["table_numbers"],
            "updated_at": now_iso()
        }}
    )
    
    await create_audit_log(current_user, "table_combination", combination_id, "assign_reservation")
    
    return {"message": "Reservierung zugewiesen", "combination_id": combination_id}


@combination_router.delete("/{combination_id}")
async def dissolve_combination(
    combination_id: str,
    current_user: dict = Depends(require_manager)
):
    """Löse Kombination auf"""
    comb = await db.table_combinations.find_one(
        {"id": combination_id, "archived": False},
        {"_id": 0}
    )
    if not comb:
        raise NotFoundException("Tischkombination")
    
    before = safe_dict_for_audit(comb)
    
    # Deaktiviere Kombination
    await db.table_combinations.update_one(
        {"id": combination_id},
        {"$set": {"active": False, "dissolved_at": now_iso(), "updated_at": now_iso()}}
    )
    
    # Entferne Kombinationsreferenz aus Reservierung
    if comb.get("reservation_id"):
        await db.reservations.update_one(
            {"id": comb["reservation_id"]},
            {"$unset": {"combination_id": "", "table_ids": "", "table_numbers": ""}}
        )
    
    await create_audit_log(current_user, "table_combination", combination_id, "dissolve", before)
    
    return {"message": "Kombination aufgelöst"}


# ============== BELEGUNGS-ENDPOINTS ==============

@table_router.get("/occupancy/{date}")
async def get_table_occupancy(
    date: str,
    time: Optional[str] = None,
    time_slot: Optional[str] = None,
    area: Optional[TableArea] = None,
    current_user: dict = Depends(get_current_user)
):
    """Hole Belegungsstatus für alle Tische"""
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise ValidationException("Ungültiges Datumsformat (YYYY-MM-DD)")
    
    occupancy = await calculate_table_occupancy(
        date,
        time_str=time,
        time_slot=time_slot,
        area=area.value if area else None
    )
    
    # Statistik
    stats = {
        "frei": len([o for o in occupancy if o.status == OccupancyStatus.FREI]),
        "reserviert": len([o for o in occupancy if o.status == OccupancyStatus.RESERVIERT]),
        "belegt": len([o for o in occupancy if o.status == OccupancyStatus.BELEGT]),
        "gesperrt": len([o for o in occupancy if o.status == OccupancyStatus.GESPERRT]),
        "total": len(occupancy)
    }
    
    return {
        "date": date,
        "time": time,
        "time_slot": time_slot,
        "occupancy": [o.model_dump() for o in occupancy],
        "stats": stats
    }


# ============== TISCH-ZUWEISUNG FÜR RESERVIERUNGEN ==============

@table_router.post("/assign/{reservation_id}")
async def assign_table_to_reservation(
    reservation_id: str,
    table_id: str,
    current_user: dict = Depends(require_manager)
):
    """Weise Tisch einer Reservierung zu"""
    # Prüfe Reservierung
    res = await db.reservations.find_one(
        {"id": reservation_id, "archived": False},
        {"_id": 0}
    )
    if not res:
        raise NotFoundException("Reservierung")
    
    # Prüfe Tisch
    table = await get_table_by_id(table_id)
    if not table:
        raise NotFoundException("Tisch")
    
    # Prüfe ob Tisch frei ist
    occupancy = await calculate_table_occupancy(
        res["date"],
        time_str=res["time"]
    )
    table_occ = next((o for o in occupancy if o.table_id == table_id), None)
    
    if table_occ and table_occ.status not in [OccupancyStatus.FREI]:
        if table_occ.reservation_id != reservation_id:
            raise ConflictException(f"Tisch {table['table_number']} ist bereits belegt")
    
    # Zuweisung
    before = safe_dict_for_audit(res)
    await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": {
            "table_id": table_id,
            "table_number": table["table_number"],
            "area_id": None,  # Area kommt jetzt vom Tisch
            "updated_at": now_iso()
        }}
    )
    
    updated = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    await create_audit_log(current_user, "reservation", reservation_id, "assign_table", before, safe_dict_for_audit(updated))
    
    return {
        "message": f"Tisch {table['table_number']} zugewiesen",
        "reservation_id": reservation_id,
        "table_id": table_id,
        "table_number": table["table_number"]
    }


# ============== EXPORT ==============
__all__ = [
    "table_router",
    "combination_router",
    "TableArea",
    "TableSubArea",
    "OccupancyStatus",
    "calculate_table_occupancy",
    "suggest_tables_for_party",
    "validate_combination_tables"
]
