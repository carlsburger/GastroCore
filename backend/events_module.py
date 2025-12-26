"""
GastroCore Events Module - Sprint 4
Veranstaltungen-Submodul für spezielle Reservierungen/Ticketbuchungen
A) Kabarett: fester Eintrittspreis, begrenzte Plätze
B) Gänseabend: Event mit verpflichtender Vorbestellung

ADDITIV - Keine Breaking Changes an bestehenden Tabellen/Endpunkten
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime, timezone, date
from decimal import Decimal
from enum import Enum
import uuid

# Import from main server module
from core.database import db
from core.auth import require_admin, require_manager, get_current_user
from core.audit import create_audit_log, safe_dict_for_audit, SYSTEM_ACTOR
from core.exceptions import NotFoundException, ValidationException, ConflictException


# ============== ENUMS ==============
class EventStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    SOLD_OUT = "sold_out"
    CANCELLED = "cancelled"


class BookingMode(str, Enum):
    TICKET_ONLY = "ticket_only"  # Kabarett
    RESERVATION_WITH_PREORDER = "reservation_with_preorder"  # Gänseabend


class PricingMode(str, Enum):
    FIXED_TICKET_PRICE = "fixed_ticket_price"
    FREE_CONFIG = "free_config"


class SelectionType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTI_CHOICE = "multi_choice"


class EventBookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class PaymentStatus(str, Enum):
    UNPAID = "unpaid"
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"


# ============== CONTENT CATEGORY ENUM (Sprint: Aktionen-Infrastruktur) ==============
class ContentCategory(str, Enum):
    """
    Kategorisierung von Events nach Inhalt/Zweck.
    
    VERANSTALTUNG: Kultur-Events (Kabarett, Konzert, Comedy, etc.)
    AKTION: Zeitlich begrenzte Aktionen (Rippchen satt, Spargelzeit, etc.)
    AKTION_MENUE: Menü-Aktionen mit eingeschränkter Karte (Ente satt, etc.)
    """
    VERANSTALTUNG = "VERANSTALTUNG"  # Default für Kultur-Events
    AKTION = "AKTION"                # Zeitlich begrenzte Aktion
    AKTION_MENUE = "AKTION_MENUE"    # Menü-Aktion mit eingeschränkter Karte


# ============== ACTION TYPE ENUM (Sprint: Aktionen-Infrastruktur) ==============
class ActionType(str, Enum):
    """
    Spezifischer Typ einer Aktion (für zukünftige Logik).
    
    Diese Typen können später für spezielle Geschäftslogik verwendet werden,
    z.B. unterschiedliche Hinweistexte oder Buchungsregeln.
    """
    RIPPCHEN = "RIPPCHEN"      # Rippchen satt
    ENTE = "ENTE"              # Ente satt
    GANS = "GANS"              # Gänsebraten
    SPARGEL = "SPARGEL"        # Spargelzeit
    GRILLBUFFET = "GRILLBUFFET"  # Grillbuffet
    SONSTIGES = "SONSTIGES"    # Andere Aktionen


# ============== EVENT PRICING ENUMS (Sprint: Event-Preise) ==============
class EventPricingMode(str, Enum):
    """Preismodus für Events"""
    SINGLE = "single"      # Ein fester Preis pro Person
    VARIANTS = "variants"  # Mehrere Varianten zur Auswahl


class PaymentPolicyMode(str, Enum):
    """Zahlungsmodus bei Reservierung"""
    NONE = "none"        # Keine Zahlung erforderlich
    DEPOSIT = "deposit"  # Anzahlung erforderlich
    FULL = "full"        # Volle Zahlung erforderlich (z.B. Eintritt Kultur)


class DepositType(str, Enum):
    """Anzahlungstyp"""
    FIXED_PER_PERSON = "fixed_per_person"    # Fester Betrag pro Person
    PERCENT_OF_TOTAL = "percent_of_total"    # Prozent vom Gesamtpreis


class ReservationPaymentStatus(str, Enum):
    """Zahlungsstatus einer Reservierung mit Event"""
    PENDING_PAYMENT = "pending_payment"  # Warten auf Zahlung
    PAID = "paid"                        # Bezahlt
    EXPIRED = "expired"                  # Zahlungsfrist abgelaufen
    REFUNDED = "refunded"                # Erstattet


# ============== EVENT PRICING MODELS (Sprint: Event-Preise) ==============
class EventPricingVariant(BaseModel):
    """Eine Preisvariante für ein Event (z.B. 3-Gänge-Menü)"""
    code: str = Field(..., min_length=1, max_length=50)  # z.B. "menu_3g", "main_only"
    name: str = Field(..., min_length=1, max_length=100)  # Anzeigename
    price_per_person: float = Field(..., ge=0)
    description: Optional[str] = None


class EventPricing(BaseModel):
    """Preisstruktur für ein Event"""
    pricing_mode: EventPricingMode = EventPricingMode.SINGLE
    currency: str = "EUR"
    single_price_per_person: Optional[float] = Field(None, ge=0)  # Bei pricing_mode="single"
    variants: Optional[List[EventPricingVariant]] = None  # Bei pricing_mode="variants"


class PaymentPolicy(BaseModel):
    """Zahlungsrichtlinie für ein Event"""
    mode: PaymentPolicyMode = PaymentPolicyMode.NONE
    basis: str = "per_person"  # "per_person" oder "per_booking"
    required: bool = False
    deposit_value: Optional[float] = Field(None, ge=0)  # Betrag oder Prozent
    deposit_type: Optional[DepositType] = None
    payment_window_minutes: int = Field(default=30, ge=5, le=1440)  # 5 min bis 24h
    hold_reservation_until_paid: bool = True


# ============== PYDANTIC MODELS ==============

# --- Event Models ---
class EventCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    image_url: Optional[str] = None
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    location_area_id: Optional[str] = None
    capacity_total: int = Field(..., ge=1, le=1000)
    status: EventStatus = EventStatus.DRAFT
    last_alacarte_reservation_minutes: Optional[int] = Field(default=120, ge=0)  # Minutes before event start
    booking_mode: BookingMode = BookingMode.TICKET_ONLY
    pricing_mode: PricingMode = PricingMode.FIXED_TICKET_PRICE
    ticket_price: Optional[float] = Field(default=None, ge=0)
    currency: str = "EUR"
    requires_payment: bool = False
    # Menu options (Sprint: Data Onboarding)
    requires_menu_choice: bool = False
    menu_options: Optional[List[dict]] = None  # [{option_id, title, description, price_delta}]
    content_category: Optional[str] = None  # VERANSTALTUNG, AKTION, AKTION_MENUE
    
    # ============== AKTIONEN-FELDER (Sprint: Aktionen-Infrastruktur) ==============
    # Diese Felder sind für zukünftige Aktionen vorbereitet, aktuell nullable
    action_type: Optional[str] = None  # RIPPCHEN, ENTE, SPARGEL, etc.
    menu_only: Optional[bool] = None  # True = nur eingeschränkte Karte verfügbar
    restriction_notice: Optional[str] = None  # Hinweis für Service: "Nur eingeschränkte Karte"
    guest_notice: Optional[str] = None  # Hinweis für Gäste bei Buchung
    last_alacarte_time: Optional[str] = None  # Letzte à-la-carte Bestellung (z.B. "18:30")
    
    # ============== EVENT-PREISE + ZAHLUNG (Sprint: Event-Preise) ==============
    event_pricing: Optional[dict] = None  # EventPricing als dict
    payment_policy: Optional[dict] = None  # PaymentPolicy als dict


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    image_url: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    location_area_id: Optional[str] = None
    capacity_total: Optional[int] = Field(None, ge=1, le=1000)
    status: Optional[EventStatus] = None
    last_alacarte_reservation_minutes: Optional[int] = Field(None, ge=0)
    booking_mode: Optional[BookingMode] = None
    pricing_mode: Optional[PricingMode] = None
    ticket_price: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = None
    requires_payment: Optional[bool] = None
    # Menu options (Sprint: Data Onboarding)
    requires_menu_choice: Optional[bool] = None
    menu_options: Optional[List[dict]] = None
    content_category: Optional[str] = None
    
    # ============== AKTIONEN-FELDER (Sprint: Aktionen-Infrastruktur) ==============
    action_type: Optional[str] = None
    menu_only: Optional[bool] = None
    restriction_notice: Optional[str] = None
    guest_notice: Optional[str] = None
    last_alacarte_time: Optional[str] = None
    
    # ============== EVENT-PREISE + ZAHLUNG (Sprint: Event-Preise) ==============
    event_pricing: Optional[dict] = None  # EventPricing als dict
    payment_policy: Optional[dict] = None  # PaymentPolicy als dict


# --- EventProduct Models (Vorbestell-Items) ---
class EventProductCreate(BaseModel):
    event_id: str
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    price_delta: float = Field(default=0, ge=0)
    required: bool = False
    selection_type: SelectionType = SelectionType.SINGLE_CHOICE
    max_quantity_per_booking: Optional[int] = Field(default=None, ge=1)
    sort_order: int = Field(default=0)
    is_active: bool = True


class EventProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    price_delta: Optional[float] = Field(None, ge=0)
    required: Optional[bool] = None
    selection_type: Optional[SelectionType] = None
    max_quantity_per_booking: Optional[int] = Field(None, ge=1)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


# --- EventBooking Models ---
class EventBookingItemCreate(BaseModel):
    event_product_id: str
    quantity: int = Field(..., ge=1)
    note: Optional[str] = None


class EventBookingCreate(BaseModel):
    event_id: str
    guest_name: str = Field(..., min_length=2, max_length=100)
    guest_phone: str = Field(..., min_length=5, max_length=30)
    guest_email: Optional[EmailStr] = None
    party_size: int = Field(..., ge=1, le=50)
    notes: Optional[str] = None
    items: Optional[List[EventBookingItemCreate]] = None  # Vorbestellungen


class EventBookingUpdate(BaseModel):
    status: Optional[EventBookingStatus] = None
    payment_status: Optional[PaymentStatus] = None
    notes: Optional[str] = None


# ============== HELPER FUNCTIONS ==============
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_entity(data: dict) -> dict:
    """Create a new entity with standard fields"""
    return {
        "id": str(uuid.uuid4()),
        **data,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "archived": False
    }


async def get_event_booked_count(event_id: str, include_pending: bool = False) -> int:
    """Get total booked party_size for an event
    
    Args:
        event_id: Event ID
        include_pending: If False, only count confirmed/paid bookings (prevents overbooking)
                        If True, count all non-cancelled bookings (for display purposes)
    """
    if include_pending:
        # For display: count all non-cancelled bookings
        match_query = {"event_id": event_id, "status": {"$nin": ["cancelled"]}, "archived": False}
    else:
        # For capacity check: only count confirmed bookings OR paid bookings
        # This prevents overbooking when multiple users book but don't pay
        match_query = {
            "event_id": event_id,
            "archived": False,
            "$or": [
                {"status": "confirmed"},
                {"payment_status": "paid"}
            ]
        }
    
    pipeline = [
        {"$match": match_query},
        {"$group": {"_id": None, "total": {"$sum": "$party_size"}}}
    ]
    result = await db.event_bookings.aggregate(pipeline).to_list(1)
    return result[0]["total"] if result else 0


async def check_event_capacity(event_id: str, party_size: int, exclude_booking_id: str = None) -> bool:
    """Check if event has enough capacity"""
    event = await db.events.find_one({"id": event_id, "archived": False})
    if not event:
        return False
    
    booked = await get_event_booked_count(event_id)
    if exclude_booking_id:
        # Subtract existing booking if updating
        existing = await db.event_bookings.find_one({"id": exclude_booking_id})
        if existing:
            booked -= existing.get("party_size", 0)
    
    return (booked + party_size) <= event.get("capacity_total", 0)


async def update_event_status_if_needed(event_id: str):
    """Update event status to sold_out if capacity reached"""
    event = await db.events.find_one({"id": event_id, "archived": False})
    if not event or event.get("status") != "published":
        return
    
    booked = await get_event_booked_count(event_id)
    if booked >= event.get("capacity_total", 0):
        await db.events.update_one(
            {"id": event_id},
            {"$set": {"status": "sold_out", "updated_at": now_iso()}}
        )


async def validate_preorder_items(event: dict, items: List[EventBookingItemCreate], party_size: int):
    """Validate preorder items against event products"""
    if event.get("booking_mode") != "reservation_with_preorder":
        return  # No validation needed for ticket_only
    
    # Get required products
    required_products = await db.event_products.find({
        "event_id": event["id"],
        "required": True,
        "is_active": True,
        "archived": False
    }).to_list(100)
    
    if not required_products:
        return  # No required products
    
    # Group required products by selection_type
    single_choice_required = [p for p in required_products if p.get("selection_type") == "single_choice"]
    
    if single_choice_required and not items:
        raise ValidationException("Bitte wählen Sie die erforderlichen Optionen aus")
    
    if items:
        item_product_ids = [item.event_product_id for item in items]
        
        # For single_choice required: at least one must be selected
        if single_choice_required:
            required_ids = [p["id"] for p in single_choice_required]
            if not any(pid in item_product_ids for pid in required_ids):
                raise ValidationException("Bitte wählen Sie eine der erforderlichen Optionen aus")
        
        # Validate total quantity matches party_size for required items
        total_qty = sum(item.quantity for item in items if item.event_product_id in [p["id"] for p in required_products])
        if total_qty != party_size:
            raise ValidationException(f"Bitte wählen Sie für alle {party_size} Personen eine Option aus")


def generate_confirmation_code() -> str:
    """Generate a short confirmation code"""
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


# ============== ROUTER ==============
events_router = APIRouter(prefix="/api/events", tags=["Events"])
public_events_router = APIRouter(prefix="/api/public/events", tags=["Public Events"])


# ============== DASHBOARD SUMMARY ENDPOINT ==============
DEFAULT_KULTUR_CAPACITY = 96

@events_router.get("/dashboard/kultur-summary")
async def get_kultur_events_summary(user: dict = Depends(require_manager)):
    """
    Get Kulturveranstaltungen (category=VERANSTALTUNG) with utilization for Dashboard.
    Returns events in next 60 days with booked/capacity info.
    Default capacity: 96 if not set.
    """
    from datetime import datetime, timedelta
    
    today = datetime.now().strftime("%Y-%m-%d")
    future = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")  # Erweitert auf 90 Tage
    
    # Query: VERANSTALTUNG events
    # Include events with future dates OR events without dates (to show them)
    query = {
        "archived": False,
        "content_category": "VERANSTALTUNG",  # BUGFIX: war "category", korrigiert zu "content_category"
        "$or": [
            {"start_datetime": {"$gte": today, "$lte": future + "T23:59:59"}},
            {"start_datetime": {"$exists": False}},
            {"start_datetime": None},
            {"start_datetime": ""}
        ]
    }
    
    events = await db.events.find(query, {"_id": 0}).sort("start_datetime", 1).to_list(100)
    
    result = []
    for event in events:
        event_id = event.get("id")
        
        # Capacity: use capacity_total if set, else DEFAULT_KULTUR_CAPACITY
        capacity = event.get("capacity_total") or DEFAULT_KULTUR_CAPACITY
        
        # Booked count from event_bookings
        booked = await get_event_booked_count(event_id, include_pending=True)
        
        # Calculate utilization
        utilization = round((booked / capacity) * 100, 1) if capacity > 0 else 0
        
        # Status based on utilization
        if utilization >= 90:
            status = "critical"  # rot
        elif utilization >= 70:
            status = "warning"   # gelb
        else:
            status = "ok"        # grün
        
        # Parse date
        start_dt = event.get("start_datetime", "")
        date_str = start_dt[:10] if start_dt and len(start_dt) >= 10 else None
        time_str = start_dt[11:16] if start_dt and len(start_dt) > 11 else None
        
        result.append({
            "id": event_id,
            "title": event.get("title", ""),
            "date": date_str,
            "start_time": time_str,
            "capacity": capacity,
            "booked": booked,
            "utilization": utilization,
            "status": status,
            "is_default_capacity": event.get("capacity_total") is None,
            "has_date": date_str is not None
        })
    
    return {
        "events": result,
        "default_capacity": DEFAULT_KULTUR_CAPACITY,
        "total_events": len(result)
    }


# ============== ADMIN EVENT ENDPOINTS ==============
@events_router.get("")
async def list_events(
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    user: dict = Depends(require_manager)
):
    """List all events with optional filters"""
    query = {"archived": False}
    
    if status:
        query["status"] = status
    
    if from_date:
        query["start_datetime"] = {"$gte": from_date}
    if to_date:
        if "start_datetime" in query:
            query["start_datetime"]["$lte"] = to_date + "T23:59:59"
        else:
            query["start_datetime"] = {"$lte": to_date + "T23:59:59"}
    
    events = await db.events.find(query, {"_id": 0}).sort("start_datetime", 1).to_list(500)
    
    # Add booked count to each event (include_pending=True for display)
    for event in events:
        event["booked_count"] = await get_event_booked_count(event["id"], include_pending=True)
        event["available_capacity"] = event.get("capacity_total", 0) - event["booked_count"]
    
    return events


@events_router.get("/{event_id}")
async def get_event(event_id: str, user: dict = Depends(require_manager)):
    """Get single event with details"""
    event = await db.events.find_one({"id": event_id, "archived": False}, {"_id": 0})
    if not event:
        raise NotFoundException("Event")
    
    event["booked_count"] = await get_event_booked_count(event_id, include_pending=True)
    event["available_capacity"] = event.get("capacity_total", 0) - event["booked_count"]
    
    # Get products if reservation_with_preorder
    if event.get("booking_mode") == "reservation_with_preorder":
        event["products"] = await db.event_products.find(
            {"event_id": event_id, "archived": False, "is_active": True},
            {"_id": 0}
        ).sort("sort_order", 1).to_list(100)
    
    return event


@events_router.post("")
async def create_event(data: EventCreate, user: dict = Depends(require_admin)):
    """Create a new event"""
    event_data = data.model_dump()
    
    # Convert datetime to ISO string if needed
    if isinstance(event_data.get("start_datetime"), datetime):
        event_data["start_datetime"] = event_data["start_datetime"].isoformat()
    if event_data.get("end_datetime") and isinstance(event_data["end_datetime"], datetime):
        event_data["end_datetime"] = event_data["end_datetime"].isoformat()
    
    event = create_entity(event_data)
    await db.events.insert_one(event)
    
    await create_audit_log(user, "event", event["id"], "create", None, safe_dict_for_audit(event))
    
    return {k: v for k, v in event.items() if k != "_id"}


@events_router.patch("/{event_id}")
async def update_event(event_id: str, data: EventUpdate, user: dict = Depends(require_admin)):
    """Update an event"""
    existing = await db.events.find_one({"id": event_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Event")
    
    before = safe_dict_for_audit(existing)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    # Convert datetime to ISO string if needed
    if "start_datetime" in update_data and isinstance(update_data["start_datetime"], datetime):
        update_data["start_datetime"] = update_data["start_datetime"].isoformat()
    if "end_datetime" in update_data and isinstance(update_data["end_datetime"], datetime):
        update_data["end_datetime"] = update_data["end_datetime"].isoformat()
    
    update_data["updated_at"] = now_iso()
    
    await db.events.update_one({"id": event_id}, {"$set": update_data})
    
    updated = await db.events.find_one({"id": event_id}, {"_id": 0})
    await create_audit_log(user, "event", event_id, "update", before, safe_dict_for_audit(updated))
    
    return {k: v for k, v in updated.items() if k != "_id"}


@events_router.delete("/{event_id}")
async def archive_event(event_id: str, user: dict = Depends(require_admin)):
    """Archive an event (soft delete)"""
    existing = await db.events.find_one({"id": event_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Event")
    
    before = safe_dict_for_audit(existing)
    await db.events.update_one({"id": event_id}, {"$set": {"archived": True, "updated_at": now_iso()}})
    
    await create_audit_log(user, "event", event_id, "archive", before, {**before, "archived": True})
    
    return {"message": "Event archiviert", "success": True}


@events_router.post("/{event_id}/publish")
async def publish_event(event_id: str, user: dict = Depends(require_admin)):
    """Publish a draft event"""
    existing = await db.events.find_one({"id": event_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Event")
    
    if existing.get("status") != "draft":
        raise ValidationException("Nur Events im Status 'draft' können veröffentlicht werden")
    
    before = safe_dict_for_audit(existing)
    await db.events.update_one({"id": event_id}, {"$set": {"status": "published", "updated_at": now_iso()}})
    
    updated = await db.events.find_one({"id": event_id}, {"_id": 0})
    await create_audit_log(user, "event", event_id, "publish", before, safe_dict_for_audit(updated))
    
    return {"message": "Event veröffentlicht", "success": True}


@events_router.post("/{event_id}/cancel")
async def cancel_event(event_id: str, user: dict = Depends(require_admin)):
    """Cancel an event"""
    existing = await db.events.find_one({"id": event_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Event")
    
    before = safe_dict_for_audit(existing)
    await db.events.update_one({"id": event_id}, {"$set": {"status": "cancelled", "updated_at": now_iso()}})
    
    # Cancel all bookings
    await db.event_bookings.update_many(
        {"event_id": event_id, "status": {"$in": ["pending", "confirmed"]}},
        {"$set": {"status": "cancelled", "updated_at": now_iso()}}
    )
    
    updated = await db.events.find_one({"id": event_id}, {"_id": 0})
    await create_audit_log(user, "event", event_id, "cancel", before, safe_dict_for_audit(updated))
    
    return {"message": "Event abgesagt", "success": True}


# ============== EVENT PRICING & PAYMENT ENDPOINTS (Sprint: Event-Preise) ==============

# Default-Preise für bekannte Aktionen
DEFAULT_EVENT_PRICES = {
    # AKTIONEN (einzelpreis)
    "schnitzel_satt": {"pricing_mode": "single", "single_price_per_person": 29.90, "currency": "EUR"},
    "rippchen_satt": {"pricing_mode": "single", "single_price_per_person": 23.90, "currency": "EUR"},
    "garnelen_satt": {"pricing_mode": "single", "single_price_per_person": 35.90, "currency": "EUR"},
    # MENÜ-AKTIONEN (varianten)
    "gaensemenue": {
        "pricing_mode": "variants",
        "currency": "EUR",
        "variants": [
            {"code": "main_only", "name": "Hauptgang", "price_per_person": 34.90, "description": "Gänsebraten mit Beilagen"},
            {"code": "menu_3g", "name": "3-Gänge-Menü", "price_per_person": 49.90, "description": "Suppe + Gänsebraten + Dessert"},
        ]
    },
    "valentinstag": {
        "pricing_mode": "variants",
        "currency": "EUR",
        "variants": [
            {"code": "menu_classic", "name": "Klassisches Menü", "price_per_person": 59.90, "description": "5-Gänge Genussmenü"},
            {"code": "menu_veg", "name": "Vegetarisches Menü", "price_per_person": 49.90, "description": "5-Gänge vegetarisch"},
        ]
    },
}

# Default Payment Policies nach Kategorie
DEFAULT_PAYMENT_POLICIES = {
    "VERANSTALTUNG": {
        "mode": "full",
        "basis": "per_person",
        "required": True,
        "payment_window_minutes": 30,
        "hold_reservation_until_paid": True
    },
    "AKTION": {
        "mode": "none",
        "basis": "per_person",
        "required": False,
        "payment_window_minutes": 30,
        "hold_reservation_until_paid": False
    },
    "AKTION_MENUE": {
        "mode": "deposit",
        "basis": "per_person",
        "required": True,
        "deposit_value": 20.0,
        "deposit_type": "fixed_per_person",
        "payment_window_minutes": 30,
        "hold_reservation_until_paid": True
    },
}


class EventPricingUpdate(BaseModel):
    """Update für Event-Pricing"""
    pricing_mode: str = Field(..., pattern="^(single|variants)$")
    currency: str = "EUR"
    single_price_per_person: Optional[float] = Field(None, ge=0)
    variants: Optional[List[dict]] = None


class PaymentPolicyUpdate(BaseModel):
    """Update für Payment Policy"""
    mode: str = Field(..., pattern="^(none|deposit|full)$")
    basis: str = Field(default="per_person", pattern="^(per_person|per_booking)$")
    required: bool = False
    deposit_value: Optional[float] = Field(None, ge=0)
    deposit_type: Optional[str] = Field(None, pattern="^(fixed_per_person|percent_of_total)$")
    payment_window_minutes: int = Field(default=30, ge=5, le=1440)
    hold_reservation_until_paid: bool = True


@events_router.patch("/{event_id}/pricing")
async def update_event_pricing(
    event_id: str,
    data: EventPricingUpdate,
    user: dict = Depends(require_admin)
):
    """
    Update event pricing (Preise/Varianten).
    Dieses Feld wird bei WP-Sync NICHT überschrieben.
    """
    existing = await db.events.find_one({"id": event_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Event")
    
    before = safe_dict_for_audit(existing)
    
    # Validierung
    if data.pricing_mode == "single" and data.single_price_per_person is None:
        raise ValidationException("Bei pricing_mode='single' muss single_price_per_person angegeben werden")
    if data.pricing_mode == "variants" and (not data.variants or len(data.variants) == 0):
        raise ValidationException("Bei pricing_mode='variants' müssen Varianten angegeben werden")
    
    # Validiere Varianten
    if data.variants:
        for v in data.variants:
            if not v.get("code") or not v.get("name") or v.get("price_per_person") is None:
                raise ValidationException("Jede Variante braucht code, name und price_per_person")
    
    pricing_data = data.model_dump()
    
    await db.events.update_one(
        {"id": event_id},
        {"$set": {
            "event_pricing": pricing_data,
            "event_pricing_modified_at": now_iso(),  # Marker für WP-Sync Schutz
            "updated_at": now_iso()
        }}
    )
    
    updated = await db.events.find_one({"id": event_id}, {"_id": 0})
    await create_audit_log(user, "event", event_id, "update_pricing", before, safe_dict_for_audit(updated))
    
    return {
        "message": "Event-Preise aktualisiert",
        "event_pricing": pricing_data,
        "success": True
    }


@events_router.patch("/{event_id}/payment-policy")
async def update_event_payment_policy(
    event_id: str,
    data: PaymentPolicyUpdate,
    user: dict = Depends(require_admin)
):
    """
    Update event payment policy (Zahlungsrichtlinie).
    Dieses Feld wird bei WP-Sync NICHT überschrieben.
    """
    existing = await db.events.find_one({"id": event_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Event")
    
    before = safe_dict_for_audit(existing)
    category = existing.get("content_category", "VERANSTALTUNG")
    
    # Validierung nach Kategorie
    if category == "VERANSTALTUNG" and data.mode != "full":
        raise ValidationException("Veranstaltungen (Kultur) erfordern volle Zahlung (mode='full')")
    
    if category == "AKTION_MENUE" and data.mode == "none":
        raise ValidationException("Menü-Aktionen erfordern mindestens eine Anzahlung")
    
    if data.mode == "deposit":
        if data.deposit_value is None or data.deposit_value <= 0:
            raise ValidationException("Bei Anzahlung muss deposit_value > 0 sein")
        if data.deposit_type is None:
            raise ValidationException("Bei Anzahlung muss deposit_type angegeben werden")
    
    policy_data = data.model_dump()
    
    await db.events.update_one(
        {"id": event_id},
        {"$set": {
            "payment_policy": policy_data,
            "payment_policy_modified_at": now_iso(),  # Marker für WP-Sync Schutz
            "updated_at": now_iso()
        }}
    )
    
    updated = await db.events.find_one({"id": event_id}, {"_id": 0})
    await create_audit_log(user, "event", event_id, "update_payment_policy", before, safe_dict_for_audit(updated))
    
    return {
        "message": "Zahlungsrichtlinie aktualisiert",
        "payment_policy": policy_data,
        "success": True
    }


@events_router.get("/{event_id}/pricing-info")
async def get_event_pricing_info(event_id: str, seats: int = Query(1, ge=1, le=50)):
    """
    Öffentlicher Endpoint: Berechnet Preisinformationen für ein Event.
    Für Reservierungsformular - zeigt Preis p.P., Gesamtpreis, Anzahlung.
    """
    event = await db.events.find_one({"id": event_id, "archived": False}, {"_id": 0})
    if not event:
        raise NotFoundException("Event")
    
    pricing = event.get("event_pricing", {})
    policy = event.get("payment_policy", {})
    category = event.get("content_category", "VERANSTALTUNG")
    
    result = {
        "event_id": event_id,
        "event_title": event.get("title"),
        "content_category": category,
        "seats": seats,
        "currency": pricing.get("currency", "EUR"),
        "pricing_mode": pricing.get("pricing_mode", "single"),
        "variants": None,
        "single_price_per_person": None,
        "payment_policy": {
            "mode": policy.get("mode", "none"),
            "required": policy.get("required", False),
            "payment_window_minutes": policy.get("payment_window_minutes", 30),
        }
    }
    
    # Preis-Infos
    if pricing.get("pricing_mode") == "variants" and pricing.get("variants"):
        result["variants"] = [
            {
                "code": v["code"],
                "name": v["name"],
                "price_per_person": v["price_per_person"],
                "description": v.get("description"),
                "total_price": round(v["price_per_person"] * seats, 2)
            }
            for v in pricing["variants"]
        ]
    elif pricing.get("single_price_per_person"):
        price_pp = pricing["single_price_per_person"]
        result["single_price_per_person"] = price_pp
        result["total_price"] = round(price_pp * seats, 2)
    elif event.get("ticket_price"):
        # Fallback auf altes ticket_price Feld
        price_pp = event["ticket_price"]
        result["single_price_per_person"] = price_pp
        result["total_price"] = round(price_pp * seats, 2)
    
    # Anzahlung berechnen wenn required
    if policy.get("required") and policy.get("mode") in ["deposit", "full"]:
        if policy["mode"] == "full":
            result["payment_policy"]["amount_due"] = result.get("total_price", 0)
            result["payment_policy"]["amount_due_label"] = "Voller Eintrittspreis"
        elif policy["mode"] == "deposit":
            deposit_type = policy.get("deposit_type", "fixed_per_person")
            deposit_value = policy.get("deposit_value", 0)
            
            if deposit_type == "fixed_per_person":
                amount_due = round(deposit_value * seats, 2)
                result["payment_policy"]["amount_due"] = amount_due
                result["payment_policy"]["amount_due_label"] = f"Anzahlung {deposit_value:.2f} € × {seats} Pers."
            elif deposit_type == "percent_of_total":
                total = result.get("total_price", 0)
                amount_due = round(total * (deposit_value / 100), 2)
                result["payment_policy"]["amount_due"] = amount_due
                result["payment_policy"]["amount_due_label"] = f"Anzahlung {deposit_value}% vom Gesamtpreis"
    
    return result


@events_router.post("/{event_id}/calculate-price")
async def calculate_event_price(
    event_id: str,
    seats: int = Query(..., ge=1, le=50),
    variant_code: Optional[str] = None
):
    """
    Berechnet den Preis für eine Event-Reservierung.
    
    Args:
        event_id: Event ID
        seats: Anzahl Personen
        variant_code: Bei Varianten: welche Variante gewählt wurde
    
    Returns:
        Preisberechnung mit total_price, amount_due, payment_info
    """
    event = await db.events.find_one({"id": event_id, "archived": False}, {"_id": 0})
    if not event:
        raise NotFoundException("Event")
    
    pricing = event.get("event_pricing", {})
    policy = event.get("payment_policy", {})
    
    # Preis pro Person ermitteln
    price_per_person = 0
    variant_name = None
    
    if pricing.get("pricing_mode") == "variants":
        if not variant_code:
            raise ValidationException("Bei Varianten-Pricing muss variant_code angegeben werden")
        
        variants = pricing.get("variants", [])
        selected = next((v for v in variants if v["code"] == variant_code), None)
        if not selected:
            raise ValidationException(f"Variante '{variant_code}' nicht gefunden")
        
        price_per_person = selected["price_per_person"]
        variant_name = selected["name"]
    else:
        price_per_person = pricing.get("single_price_per_person") or event.get("ticket_price", 0)
    
    total_price = round(price_per_person * seats, 2)
    
    # Zahlungsbetrag berechnen
    amount_due = 0
    payment_required = policy.get("required", False)
    payment_mode = policy.get("mode", "none")
    
    if payment_required:
        if payment_mode == "full":
            amount_due = total_price
        elif payment_mode == "deposit":
            deposit_type = policy.get("deposit_type", "fixed_per_person")
            deposit_value = policy.get("deposit_value", 0)
            
            if deposit_type == "fixed_per_person":
                amount_due = round(deposit_value * seats, 2)
            elif deposit_type == "percent_of_total":
                amount_due = round(total_price * (deposit_value / 100), 2)
    
    return {
        "event_id": event_id,
        "seats": seats,
        "variant_code": variant_code,
        "variant_name": variant_name,
        "price_per_person": price_per_person,
        "total_price": total_price,
        "currency": pricing.get("currency", "EUR"),
        "payment_required": payment_required,
        "payment_mode": payment_mode,
        "amount_due": amount_due,
        "payment_window_minutes": policy.get("payment_window_minutes", 30),
        "calculated_at": now_iso()
    }


# ============== RESERVATION PAYMENT ENDPOINTS ==============

@events_router.post("/reservations/{reservation_id}/confirm-payment")
async def confirm_reservation_payment(
    reservation_id: str,
    amount_paid: float = Query(..., ge=0),
    payment_method: str = Query(default="manual", description="bar, karte, ueberweisung, manual"),
    user: dict = Depends(require_manager)
):
    """
    Bestätigt die Zahlung einer Reservierung und setzt Status auf 'bestätigt'.
    
    Nur für Reservierungen mit status='pending_payment'.
    """
    reservation = await db.reservations.find_one({"id": reservation_id, "archived": False})
    if not reservation:
        raise NotFoundException("Reservierung")
    
    if reservation.get("status") != "pending_payment":
        raise ValidationException(f"Reservierung hat Status '{reservation.get('status')}', erwartet 'pending_payment'")
    
    amount_due = reservation.get("amount_due", 0)
    if amount_paid < amount_due:
        raise ValidationException(f"Gezahlter Betrag ({amount_paid}€) ist kleiner als fälliger Betrag ({amount_due}€)")
    
    before = safe_dict_for_audit(reservation)
    
    update_data = {
        "status": "bestätigt",
        "payment_status": "paid",
        "amount_paid": amount_paid,
        "payment_method": payment_method,
        "payment_confirmed_at": now_iso(),
        "payment_confirmed_by": user.get("email", "unknown"),
        "updated_at": now_iso()
    }
    
    await db.reservations.update_one({"id": reservation_id}, {"$set": update_data})
    
    updated = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    await create_audit_log(user, "reservation", reservation_id, "confirm_payment", before, safe_dict_for_audit(updated))
    
    return {
        "message": "Zahlung bestätigt, Reservierung bestätigt",
        "reservation_id": reservation_id,
        "status": "bestätigt",
        "amount_paid": amount_paid,
        "success": True
    }


@events_router.post("/reservations/expire-unpaid")
async def expire_unpaid_reservations(user: dict = Depends(require_admin)):
    """
    Setzt alle abgelaufenen pending_payment Reservierungen auf 'expired'.
    
    Sollte regelmäßig (z.B. alle 5 Minuten) per Cron/Scheduler aufgerufen werden.
    """
    now = datetime.now(timezone.utc).isoformat()
    
    # Finde alle Reservierungen mit status=pending_payment und payment_due_at < jetzt
    query = {
        "status": "pending_payment",
        "payment_due_at": {"$lt": now},
        "archived": False
    }
    
    reservations = await db.reservations.find(query).to_list(500)
    
    expired_count = 0
    expired_ids = []
    
    for res in reservations:
        await db.reservations.update_one(
            {"id": res["id"]},
            {"$set": {
                "status": "expired",
                "payment_status": "expired",
                "expired_at": now_iso(),
                "updated_at": now_iso()
            }}
        )
        expired_count += 1
        expired_ids.append(res["id"])
    
    if expired_count > 0:
        await create_audit_log(
            actor=SYSTEM_ACTOR,
            action="expire_unpaid",
            entity="reservations",
            entity_id="batch",
            after={"expired_count": expired_count, "expired_ids": expired_ids[:20]}
        )
    
    return {
        "message": f"{expired_count} Reservierungen auf 'expired' gesetzt",
        "expired_count": expired_count,
        "expired_ids": expired_ids[:20],  # Max 20 IDs in Response
        "success": True
    }


@events_router.get("/reservations/pending-payments")
async def list_pending_payment_reservations(user: dict = Depends(require_manager)):
    """
    Listet alle Reservierungen mit ausstehender Zahlung.
    """
    now = datetime.now(timezone.utc).isoformat()
    
    reservations = await db.reservations.find(
        {"status": "pending_payment", "archived": False},
        {"_id": 0}
    ).sort("payment_due_at", 1).to_list(100)
    
    result = []
    for res in reservations:
        due_at = res.get("payment_due_at", "")
        is_overdue = due_at < now if due_at else False
        
        result.append({
            "id": res["id"],
            "guest_name": res.get("guest_name"),
            "guest_phone": res.get("guest_phone"),
            "date": res.get("date"),
            "time": res.get("time"),
            "party_size": res.get("party_size"),
            "event_title": res.get("event_title"),
            "variant_name": res.get("variant_name"),
            "total_price": res.get("total_price"),
            "amount_due": res.get("amount_due"),
            "payment_due_at": due_at,
            "is_overdue": is_overdue,
            "created_at": res.get("created_at")
        })
    
    return {
        "reservations": result,
        "total": len(result),
        "overdue_count": sum(1 for r in result if r["is_overdue"])
    }


@events_router.post("/seed-default-prices")
async def seed_default_event_prices(user: dict = Depends(require_admin)):
    """
    Setzt Default-Preise für bekannte Aktionen.
    Nur Events OHNE event_pricing werden aktualisiert.
    """
    updated_count = 0
    skipped_count = 0
    results = []
    
    # Mapping von Event-Titeln zu Preis-Keys
    title_to_price_key = {
        "schnitzel satt": "schnitzel_satt",
        "rippchen satt": "rippchen_satt",
        "garnelen satt": "garnelen_satt",
        "gänsemenü": "gaensemenue",
        "gänsebraten": "gaensemenue",
        "martinsgans": "gaensemenue",
        "valentinstag": "valentinstag",
    }
    
    # Alle Events ohne event_pricing holen
    events = await db.events.find({
        "archived": False,
        "event_pricing": {"$exists": False}
    }).to_list(500)
    
    for event in events:
        title_lower = event.get("title", "").lower()
        category = event.get("content_category", "")
        
        # Suche passenden Preis-Key
        price_key = None
        for pattern, key in title_to_price_key.items():
            if pattern in title_lower:
                price_key = key
                break
        
        if price_key and price_key in DEFAULT_EVENT_PRICES:
            pricing = DEFAULT_EVENT_PRICES[price_key]
            policy = DEFAULT_PAYMENT_POLICIES.get(category, DEFAULT_PAYMENT_POLICIES["AKTION"])
            
            await db.events.update_one(
                {"id": event["id"]},
                {"$set": {
                    "event_pricing": pricing,
                    "payment_policy": policy,
                    "updated_at": now_iso()
                }}
            )
            updated_count += 1
            results.append({"id": event["id"], "title": event.get("title"), "price_key": price_key})
        else:
            # Setze zumindest Default-Payment-Policy nach Kategorie
            if category in DEFAULT_PAYMENT_POLICIES:
                policy = DEFAULT_PAYMENT_POLICIES[category]
                await db.events.update_one(
                    {"id": event["id"]},
                    {"$set": {
                        "payment_policy": policy,
                        "updated_at": now_iso()
                    }}
                )
            skipped_count += 1
    
    await create_audit_log(user, "event", "seed_prices", "seed", None, {
        "updated": updated_count,
        "skipped": skipped_count
    })
    
    return {
        "message": f"{updated_count} Events mit Default-Preisen versehen",
        "updated": updated_count,
        "skipped": skipped_count,
        "details": results[:20],  # Max 20 Details
        "success": True
    }


# ============== EVENT PRODUCTS ENDPOINTS ==============
@events_router.get("/{event_id}/products")
async def list_event_products(event_id: str, user: dict = Depends(require_manager)):
    """List all products for an event"""
    products = await db.event_products.find(
        {"event_id": event_id, "archived": False},
        {"_id": 0}
    ).sort("sort_order", 1).to_list(100)
    return products


@events_router.post("/{event_id}/products")
async def create_event_product(event_id: str, data: EventProductCreate, user: dict = Depends(require_admin)):
    """Create a new product/option for an event"""
    # Verify event exists
    event = await db.events.find_one({"id": event_id, "archived": False})
    if not event:
        raise NotFoundException("Event")
    
    product_data = data.model_dump()
    product_data["event_id"] = event_id  # Ensure correct event_id
    product = create_entity(product_data)
    
    await db.event_products.insert_one(product)
    await create_audit_log(user, "event_product", product["id"], "create", None, safe_dict_for_audit(product))
    
    return {k: v for k, v in product.items() if k != "_id"}


@events_router.patch("/{event_id}/products/{product_id}")
async def update_event_product(event_id: str, product_id: str, data: EventProductUpdate, user: dict = Depends(require_admin)):
    """Update an event product"""
    existing = await db.event_products.find_one({"id": product_id, "event_id": event_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Produkt")
    
    before = safe_dict_for_audit(existing)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now_iso()
    
    await db.event_products.update_one({"id": product_id}, {"$set": update_data})
    
    updated = await db.event_products.find_one({"id": product_id}, {"_id": 0})
    await create_audit_log(user, "event_product", product_id, "update", before, safe_dict_for_audit(updated))
    
    return {k: v for k, v in updated.items() if k != "_id"}


@events_router.delete("/{event_id}/products/{product_id}")
async def archive_event_product(event_id: str, product_id: str, user: dict = Depends(require_admin)):
    """Archive an event product"""
    existing = await db.event_products.find_one({"id": product_id, "event_id": event_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Produkt")
    
    before = safe_dict_for_audit(existing)
    await db.event_products.update_one({"id": product_id}, {"$set": {"archived": True, "updated_at": now_iso()}})
    
    await create_audit_log(user, "event_product", product_id, "archive", before, {**before, "archived": True})
    
    return {"message": "Produkt archiviert", "success": True}


# ============== EVENT BOOKINGS ENDPOINTS ==============
@events_router.get("/{event_id}/bookings")
async def list_event_bookings(
    event_id: str,
    status: Optional[str] = None,
    user: dict = Depends(require_manager)
):
    """List all bookings for an event"""
    query = {"event_id": event_id, "archived": False}
    if status:
        query["status"] = status
    
    bookings = await db.event_bookings.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    # Add items to each booking
    for booking in bookings:
        booking["items"] = await db.event_booking_items.find(
            {"event_booking_id": booking["id"], "archived": False},
            {"_id": 0}
        ).to_list(50)
        
        # Add product names to items
        for item in booking["items"]:
            product = await db.event_products.find_one({"id": item["event_product_id"]}, {"_id": 0})
            if product:
                item["product_name"] = product.get("name")
    
    return bookings


@events_router.get("/{event_id}/bookings/{booking_id}")
async def get_event_booking(event_id: str, booking_id: str, user: dict = Depends(require_manager)):
    """Get single booking with details"""
    booking = await db.event_bookings.find_one(
        {"id": booking_id, "event_id": event_id, "archived": False},
        {"_id": 0}
    )
    if not booking:
        raise NotFoundException("Buchung")
    
    # Get items
    booking["items"] = await db.event_booking_items.find(
        {"event_booking_id": booking_id, "archived": False},
        {"_id": 0}
    ).to_list(50)
    
    # Add product names
    for item in booking["items"]:
        product = await db.event_products.find_one({"id": item["event_product_id"]}, {"_id": 0})
        if product:
            item["product_name"] = product.get("name")
    
    return booking


@events_router.patch("/{event_id}/bookings/{booking_id}")
async def update_event_booking(
    event_id: str,
    booking_id: str,
    data: EventBookingUpdate,
    user: dict = Depends(require_manager)
):
    """Update booking status"""
    existing = await db.event_bookings.find_one(
        {"id": booking_id, "event_id": event_id, "archived": False},
        {"_id": 0}
    )
    if not existing:
        raise NotFoundException("Buchung")
    
    before = safe_dict_for_audit(existing)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now_iso()
    
    await db.event_bookings.update_one({"id": booking_id}, {"$set": update_data})
    
    # Check if event should be marked as sold_out
    if data.status == EventBookingStatus.CANCELLED:
        event = await db.events.find_one({"id": event_id})
        if event and event.get("status") == "sold_out":
            # Check if capacity is available again (use strict count for capacity check)
            booked = await get_event_booked_count(event_id, include_pending=False)
            if booked < event.get("capacity_total", 0):
                await db.events.update_one({"id": event_id}, {"$set": {"status": "published", "updated_at": now_iso()}})
    
    updated = await db.event_bookings.find_one({"id": booking_id}, {"_id": 0})
    await create_audit_log(user, "event_booking", booking_id, "update", before, safe_dict_for_audit(updated))
    
    return {k: v for k, v in updated.items() if k != "_id"}


# ============== PUBLIC EVENT ENDPOINTS ==============
@public_events_router.get("")
async def list_public_events():
    """List all published events for public booking"""
    query = {"status": "published", "archived": False}
    events = await db.events.find(query, {"_id": 0}).sort("start_datetime", 1).to_list(100)
    
    result = []
    for event in events:
        # For public display: show actual available capacity (only confirmed/paid bookings count)
        booked = await get_event_booked_count(event["id"], include_pending=False)
        available = event.get("capacity_total", 0) - booked
        
        result.append({
            "id": event["id"],
            "title": event.get("title"),
            "description": event.get("description"),
            "image_url": event.get("image_url"),
            "start_datetime": event.get("start_datetime"),
            "end_datetime": event.get("end_datetime"),
            "booking_mode": event.get("booking_mode"),
            "ticket_price": event.get("ticket_price"),
            "currency": event.get("currency", "EUR"),
            "capacity_total": event.get("capacity_total"),
            "available_capacity": available,
            "requires_payment": event.get("requires_payment", False),
        })
    
    return result


@public_events_router.get("/{event_id}")
async def get_public_event(event_id: str):
    """Get public event details"""
    event = await db.events.find_one(
        {"id": event_id, "status": "published", "archived": False},
        {"_id": 0}
    )
    if not event:
        raise NotFoundException("Event nicht gefunden oder nicht verfügbar")
    
    # For public display: show actual available capacity (only confirmed/paid bookings count)
    booked = await get_event_booked_count(event_id, include_pending=False)
    available = event.get("capacity_total", 0) - booked
    
    result = {
        "id": event["id"],
        "title": event.get("title"),
        "description": event.get("description"),
        "image_url": event.get("image_url"),
        "start_datetime": event.get("start_datetime"),
        "end_datetime": event.get("end_datetime"),
        "booking_mode": event.get("booking_mode"),
        "pricing_mode": event.get("pricing_mode"),
        "ticket_price": event.get("ticket_price"),
        "currency": event.get("currency", "EUR"),
        "capacity_total": event.get("capacity_total"),
        "available_capacity": available,
        "requires_payment": event.get("requires_payment", False),
        "last_alacarte_reservation_minutes": event.get("last_alacarte_reservation_minutes"),
    }
    
    # Include products for reservation_with_preorder mode
    if event.get("booking_mode") == "reservation_with_preorder":
        result["products"] = await db.event_products.find(
            {"event_id": event_id, "is_active": True, "archived": False},
            {"_id": 0}
        ).sort("sort_order", 1).to_list(100)
    
    return result


@public_events_router.post("/{event_id}/book")
async def create_public_event_booking(event_id: str, data: EventBookingCreate):
    """Create a public event booking"""
    # Get event
    event = await db.events.find_one(
        {"id": event_id, "status": "published", "archived": False},
        {"_id": 0}
    )
    if not event:
        raise NotFoundException("Event nicht gefunden oder nicht verfügbar")
    
    # Check capacity
    if not await check_event_capacity(event_id, data.party_size):
        raise ConflictException("Keine ausreichende Kapazität verfügbar")
    
    # Validate preorder items if required
    if data.items:
        await validate_preorder_items(event, data.items, data.party_size)
    elif event.get("booking_mode") == "reservation_with_preorder":
        # Check if there are required products
        required_products = await db.event_products.find(
            {"event_id": event_id, "required": True, "is_active": True, "archived": False}
        ).to_list(100)
        if required_products:
            raise ValidationException("Bitte wählen Sie die erforderlichen Optionen aus")
    
    # Calculate total price
    total_price = 0
    if event.get("pricing_mode") == "fixed_ticket_price" and event.get("ticket_price"):
        total_price = float(event["ticket_price"]) * data.party_size
    
    # Add price deltas from items
    if data.items:
        for item in data.items:
            product = await db.event_products.find_one({"id": item.event_product_id})
            if product:
                total_price += float(product.get("price_delta", 0)) * item.quantity
    
    # Create booking
    booking_data = {
        "event_id": event_id,
        "guest_name": data.guest_name,
        "guest_phone": data.guest_phone,
        "guest_email": data.guest_email,
        "party_size": data.party_size,
        "notes": data.notes,
        "status": "confirmed" if not event.get("requires_payment") else "pending",
        "payment_status": "unpaid" if event.get("requires_payment") else "paid",
        "total_price": total_price,
        "currency": event.get("currency", "EUR"),
        "confirmation_code": generate_confirmation_code(),
    }
    
    booking = create_entity(booking_data)
    await db.event_bookings.insert_one(booking)
    
    # Create booking items
    if data.items:
        for item in data.items:
            item_data = {
                "event_booking_id": booking["id"],
                "event_product_id": item.event_product_id,
                "quantity": item.quantity,
                "note": item.note,
            }
            item_entity = create_entity(item_data)
            await db.event_booking_items.insert_one(item_entity)
    
    # Update event status if sold out
    await update_event_status_if_needed(event_id)
    
    # Audit log
    await create_audit_log(SYSTEM_ACTOR, "event_booking", booking["id"], "create", None, safe_dict_for_audit(booking))
    
    # Get items for response
    items = []
    if data.items:
        for item in data.items:
            product = await db.event_products.find_one({"id": item.event_product_id})
            items.append({
                "product_name": product.get("name") if product else "Unknown",
                "quantity": item.quantity,
                "note": item.note,
            })
    
    return {
        "id": booking["id"],
        "confirmation_code": booking["confirmation_code"],
        "event_title": event.get("title"),
        "event_date": event.get("start_datetime"),
        "guest_name": booking["guest_name"],
        "party_size": booking["party_size"],
        "total_price": total_price,
        "currency": booking["currency"],
        "status": booking["status"],
        "items": items,
        "message": "Buchung erfolgreich erstellt",
        "success": True
    }


# ============== INTEGRATION WITH RESERVATIONS ==============
async def check_alacarte_blocked_by_event(date_str: str, time_str: str, area_id: str = None) -> dict:
    """
    Check if a la carte reservations are blocked due to an event.
    Returns blocking event info if blocked, None otherwise.
    """
    from datetime import datetime
    
    # Parse the requested reservation datetime
    try:
        req_datetime = datetime.fromisoformat(f"{date_str}T{time_str}:00")
    except:
        return None
    
    # Find events on this date
    query = {
        "status": "published",
        "archived": False,
        "start_datetime": {"$gte": date_str, "$lt": date_str + "T23:59:59"}
    }
    
    if area_id:
        query["$or"] = [
            {"location_area_id": area_id},
            {"location_area_id": None},  # Events without specific area affect all areas
            {"location_area_id": {"$exists": False}}
        ]
    
    events = await db.events.find(query, {"_id": 0}).to_list(100)
    
    for event in events:
        event_start = datetime.fromisoformat(event["start_datetime"].replace("Z", "+00:00").replace("+00:00", ""))
        
        # Calculate cutoff time
        minutes_before = event.get("last_alacarte_reservation_minutes", 120)
        cutoff_time = event_start - timedelta(minutes=minutes_before)
        
        # If the reservation time is after cutoff and before event end, block it
        if req_datetime >= cutoff_time:
            event_end = event_start + timedelta(hours=3)  # Default 3 hour event
            if event.get("end_datetime"):
                event_end = datetime.fromisoformat(event["end_datetime"].replace("Z", "+00:00").replace("+00:00", ""))
            
            if req_datetime <= event_end:
                return {
                    "blocked": True,
                    "event_id": event["id"],
                    "event_title": event.get("title"),
                    "message": f"À la carte Reservierungen sind ab {cutoff_time.strftime('%H:%M')} Uhr nicht mehr möglich wegen: {event.get('title')}"
                }
    
    return {"blocked": False}


# ============== SEED DATA ==============
async def seed_events():
    """Seed sample events: Kabarett and Gänseabend"""
    # Check if events already exist
    existing = await db.events.count_documents({"archived": False})
    if existing > 0:
        return {"message": "Events bereits vorhanden", "seeded": False}
    
    # Event 1: Kabarett (ticket_only)
    kabarett_id = str(uuid.uuid4())
    kabarett = {
        "id": kabarett_id,
        "title": "Kabarett-Abend mit Max Müller",
        "description": """Ein unvergesslicher Abend voller Humor und Satire!

Max Müller präsentiert sein neues Programm „Alles wird gut – oder auch nicht" und nimmt dabei kein Blatt vor den Mund. Freuen Sie sich auf bissigen Humor, scharfsinnige Beobachtungen und garantiert viele Lacher.

Im Ticketpreis enthalten:
• Begrüßungsgetränk
• Reservierter Sitzplatz
• 2 Stunden beste Unterhaltung

Einlass ab 19:00 Uhr, Beginn 20:00 Uhr.""",
        "image_url": "https://images.unsplash.com/photo-1514306191717-452ec28c7814?w=800",
        "start_datetime": "2025-01-25T20:00:00",
        "end_datetime": "2025-01-25T22:30:00",
        "location_area_id": None,
        "capacity_total": 80,
        "status": "published",
        "last_alacarte_reservation_minutes": 180,
        "booking_mode": "ticket_only",
        "pricing_mode": "fixed_ticket_price",
        "ticket_price": 29.00,
        "currency": "EUR",
        "requires_payment": False,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "archived": False
    }
    
    # Event 2: Gänseabend (reservation_with_preorder)
    gaense_id = str(uuid.uuid4())
    gaense = {
        "id": gaense_id,
        "title": "Traditioneller Gänseabend",
        "description": """Genießen Sie unser traditionelles Gänse-Menü in festlicher Atmosphäre!

Unser Küchenchef bereitet für Sie das klassische Martinsgans-Menü zu:
• Gänsesuppe mit hausgemachten Klößchen
• Knusprige Gans vom Grill
• Hausgemachtes Rotkraut und Kartoffelklöße
• Dessert-Variation

Bitte wählen Sie bei der Buchung Ihre Hauptgang-Variante. Die Auswahl ist verbindlich für die Küchenplanung.

Preis: 49,00€ pro Person (Fisch/Vegetarisch: 45,00€)""",
        "image_url": "https://images.unsplash.com/photo-1574484284002-952d92456975?w=800",
        "start_datetime": "2025-02-15T18:00:00",
        "end_datetime": "2025-02-15T22:00:00",
        "location_area_id": None,
        "capacity_total": 60,
        "status": "published",
        "last_alacarte_reservation_minutes": 240,
        "booking_mode": "reservation_with_preorder",
        "pricing_mode": "fixed_ticket_price",
        "ticket_price": 49.00,
        "currency": "EUR",
        "requires_payment": False,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "archived": False
    }
    
    await db.events.insert_many([kabarett, gaense])
    
    # Products for Gänseabend
    products = [
        {
            "id": str(uuid.uuid4()),
            "event_id": gaense_id,
            "name": "Gans (klassisch)",
            "description": "Knusprige Martinsgans mit Rotkraut und Klößen",
            "price_delta": 0,
            "required": True,
            "selection_type": "single_choice",
            "sort_order": 1,
            "is_active": True,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "archived": False
        },
        {
            "id": str(uuid.uuid4()),
            "event_id": gaense_id,
            "name": "Fisch",
            "description": "Gebratenes Zanderfilet mit Kräuterbutter",
            "price_delta": -4.00,
            "required": True,
            "selection_type": "single_choice",
            "sort_order": 2,
            "is_active": True,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "archived": False
        },
        {
            "id": str(uuid.uuid4()),
            "event_id": gaense_id,
            "name": "Vegetarisch",
            "description": "Gefüllte Kürbis-Roulade mit Pilzragout",
            "price_delta": -4.00,
            "required": True,
            "selection_type": "single_choice",
            "sort_order": 3,
            "is_active": True,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "archived": False
        }
    ]
    
    await db.event_products.insert_many(products)
    
    return {
        "message": "Beispiel-Events erstellt",
        "seeded": True,
        "events": [
            {"id": kabarett_id, "title": kabarett["title"], "mode": "ticket_only", "price": 29.00},
            {"id": gaense_id, "title": gaense["title"], "mode": "reservation_with_preorder", "price": 49.00}
        ]
    }


# ============== WORDPRESS EVENT SYNC (Sprint: WordPress Integration) ==============
"""
WordPress Event Sync - READ-ONLY Import von The Events Calendar / Tribe
Single Source of Truth: WordPress (carlsburg.de)
GastroCore übernimmt Events, ändert sie aber nicht zurück.
"""

import httpx
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

WORDPRESS_EVENTS_API = "https://www.carlsburg.de/wp-json/tribe/events/v1/events"
SYNC_SOURCE = "wordpress"

# ============== KATEGORIE-MAPPING (Sprint: Aktionen-Infrastruktur) ==============
# WordPress Kategorie-Slug → GastroCore event_type
# Erweitert um zukünftige Aktionen-Kategorien
CATEGORY_MAPPING = {
    # Kultur-Events (bestehend)
    "comedy": "kultur",
    "musik": "kultur",
    "kabarett": "kultur",
    "lesung": "kultur",
    "theater": "kultur",
    "konzert": "kultur",
    "travestie": "kultur",
    
    # Kulinarik-Events (bestehend)
    "kulinarik": "kulinarik",
    "kulinarisch": "kulinarik",
    "menü": "kulinarik",
    "menu": "kulinarik",
    
    # Aktionen (vorbereitet für zukünftige WordPress-Kategorien)
    "aktion": "aktion",
    "aktionen": "aktion",
    "special": "aktion",
    "angebot": "aktion",
    
    # Menü-Aktionen (vorbereitet)
    "menue-aktion": "aktion_menue",
    "menueaktion": "aktion_menue",
    "menu-aktion": "aktion_menue",
    "ente-satt": "aktion_menue",
    "rippchen-satt": "aktion_menue",
}

# ============== CONTENT-CATEGORY-MAPPING (Sprint: Aktionen-Infrastruktur) ==============
# event_type → content_category
# Bestimmt welche content_category ein Event bekommt
CONTENT_CATEGORY_MAPPING = {
    "kultur": "VERANSTALTUNG",
    "kulinarik": "VERANSTALTUNG",
    "aktion": "AKTION",
    "aktion_menue": "AKTION_MENUE",
}

# ============== ACTION-TYPE-DETECTION (Sprint: Aktionen-Infrastruktur) ==============
# Keywords im Titel → action_type
# Wird verwendet um Aktionen automatisch zu kategorisieren
ACTION_TYPE_KEYWORDS = {
    "RIPPCHEN": ["rippchen", "ribs", "spare ribs"],
    "ENTE": ["ente", "duck", "entenbrust"],
    "GANS": ["gans", "gänse", "gänsebraten", "martinsgans"],
    "SPARGEL": ["spargel", "asparagus"],
    "GRILLBUFFET": ["grill", "bbq", "grillbuffet"],
}

def detect_action_type(title: str) -> Optional[str]:
    """
    Erkennt den Aktionstyp basierend auf Keywords im Titel.
    
    Erweitert: Prüft auch ob ein Event eine AKTION ist (unabhängig von Kategorien)
    """
    if not title:
        return None
    
    title_lower = title.lower()
    
    for action_type, keywords in ACTION_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in title_lower:
                return action_type
    
    return "SONSTIGES"


def determine_content_category(event_type: str, categories: List[str] = None, title: str = None) -> str:
    """
    Bestimmt die content_category basierend auf event_type UND Titel-Keywords.
    
    LOGIK (Priorität):
    1. Wenn Titel "satt" oder "buffet" enthält → AKTION (Satt-Essen Aktionen)
    2. Wenn event_type "aktion" oder "aktion_menue" → entsprechende Kategorie
    3. Sonst → VERANSTALTUNG
    
    Returns: VERANSTALTUNG, AKTION oder AKTION_MENUE
    """
    # 1. Titel-basierte Erkennung (höchste Priorität für Aktionen)
    if title:
        title_lower = title.lower()
        # "Satt Essen" Aktionen erkennen
        if "satt" in title_lower or "buffet" in title_lower or "all you can" in title_lower:
            # Prüfe auf spezifische Menü-Aktionen
            if any(kw in title_lower for kw in ["rippchen", "ribs", "ente", "gans", "spargel"]):
                return "AKTION_MENUE"
            return "AKTION"
    
    # 2. event_type basierte Zuordnung
    return CONTENT_CATEGORY_MAPPING.get(event_type, "VERANSTALTUNG")


def decode_html_entities(text: str) -> str:
    """
    Dekodiert HTML-Entities wie &#8211; &amp; &quot; etc.
    Macht Texte lesbar für das Cockpit.
    """
    if not text:
        return text
    import html
    # Doppelt dekodieren falls nötig (manchmal sind Entities verschachtelt)
    decoded = html.unescape(text)
    # Nochmal falls &#xxx; Entities übrig sind
    decoded = html.unescape(decoded)
    return decoded


def has_real_changes(existing: dict, mapped: dict) -> bool:
    """
    Prüft ob sich relevante Felder wirklich geändert haben.
    Nur dann zählt es als "echtes Update".
    """
    # Felder die verglichen werden
    compare_fields = [
        ("title", "title"),
        ("short_description", "short_description"),
        ("description", "description"),
        ("start_datetime", "start_datetime"),
        ("end_datetime", "end_datetime"),
        ("image_url", "image_url"),
        ("entry_price", "entry_price"),
    ]
    
    for existing_key, mapped_key in compare_fields:
        existing_val = existing.get(existing_key) or ""
        mapped_val = mapped.get(mapped_key) or ""
        
        # Normalisiere für Vergleich
        if isinstance(existing_val, str):
            existing_val = existing_val.strip()
        if isinstance(mapped_val, str):
            mapped_val = mapped_val.strip()
        
        if existing_val != mapped_val:
            return True
    
    return False


def map_wordpress_event_to_gastrocore(wp_event: dict) -> dict:
    """
    Mappt ein WordPress/Tribe Event auf das GastroCore Event-Schema.
    Dekodiert HTML-Entities für saubere Texte.
    """
    # Kategorie ermitteln
    event_type = "kultur"  # Default
    categories = wp_event.get("categories", [])
    for cat in categories:
        cat_slug = cat.get("slug", "").lower()
        if cat_slug in CATEGORY_MAPPING:
            event_type = CATEGORY_MAPPING[cat_slug]
            break
    
    # Datum parsen (Format: "2026-02-25 20:00:00")
    start_str = wp_event.get("start_date", "")
    end_str = wp_event.get("end_date", "")
    
    try:
        start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S") if start_str else None
    except ValueError:
        start_dt = None
    
    try:
        end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S") if end_str else None
    except ValueError:
        end_dt = None
    
    # Bild-URL
    image_url = None
    if wp_event.get("image"):
        image_url = wp_event["image"].get("url")
    
    # Preis extrahieren (z.B. "29.00 EUR" → "29.00 EUR")
    cost = wp_event.get("cost", "")
    if cost and not isinstance(cost, str):
        cost = str(cost)
    
    # Titel dekodieren (HTML-Entities wie &#8211; → –)
    title = decode_html_entities(wp_event.get("title", "Unbekannt"))
    
    # Description dekodieren
    description = decode_html_entities(wp_event.get("description", ""))
    
    # Excerpt / Kurzbeschreibung
    excerpt = wp_event.get("excerpt", "") or ""
    # HTML-Tags entfernen für Kurztext
    import re
    excerpt_clean = re.sub(r'<[^>]+>', '', excerpt).strip()
    excerpt_clean = decode_html_entities(excerpt_clean)
    
    # ============== AKTIONEN-LOGIK (Sprint: Aktionen-Infrastruktur) ==============
    # Bestimme content_category basierend auf event_type UND Titel
    content_category = determine_content_category(event_type, title=title)
    
    # Für Aktionen: Zusätzliche Felder ermitteln
    action_type = None
    menu_only = None
    restriction_notice = None
    guest_notice = None
    
    if content_category in ("AKTION", "AKTION_MENUE"):
        # Aktionstyp aus Titel erkennen
        action_type = detect_action_type(title)
        
        # Menü-Aktionen haben eingeschränkte Karte
        if content_category == "AKTION_MENUE":
            menu_only = True
            restriction_notice = "Während dieser Aktion steht nur eine eingeschränkte à la carte Karte zur Verfügung."
            guest_notice = "Bitte beachten Sie: Während dieser Aktion ist nur eine reduzierte Speisekarte verfügbar."
    
    return {
        "external_source": SYNC_SOURCE,
        "external_id": str(wp_event.get("id", "")),
        "title": title,
        "description": description,
        "short_description": excerpt_clean[:500] if excerpt_clean else None,
        "image_url": image_url,
        "start_datetime": start_dt.isoformat() if start_dt else None,
        "end_datetime": end_dt.isoformat() if end_dt else None,
        "entry_price": cost,
        "website_url": wp_event.get("url", ""),
        "slug": wp_event.get("slug", ""),
        "event_type": event_type,
        "content_category": content_category,
        "wp_categories": [c.get("name") for c in categories],
        # Aktionen-Felder (nullable, nur gefüllt für Aktionen)
        "action_type": action_type,
        "menu_only": menu_only,
        "restriction_notice": restriction_notice,
        "guest_notice": guest_notice,
    }


async def fetch_wordpress_events(min_date: date = None) -> List[dict]:
    """
    Holt alle Events von WordPress mit Pagination.
    Filtert auf zukünftige Events (ab min_date).
    """
    all_events = []
    page = 1
    per_page = 50
    
    if min_date is None:
        min_date = date.today() - timedelta(days=1)  # Ab gestern
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            try:
                params = {
                    "per_page": per_page,
                    "page": page,
                    "start_date": min_date.isoformat(),
                }
                
                response = await client.get(WORDPRESS_EVENTS_API, params=params)
                response.raise_for_status()
                
                data = response.json()
                events = data.get("events", [])
                
                if not events:
                    break
                
                # Nur veröffentlichte Events
                published = [e for e in events if e.get("status") == "publish"]
                all_events.extend(published)
                
                # Pagination prüfen
                total_pages = data.get("total_pages", 1)
                if page >= total_pages:
                    break
                
                page += 1
                
            except httpx.HTTPError as e:
                logger.error(f"WordPress API Fehler: {e}")
                raise HTTPException(status_code=502, detail=f"WordPress API nicht erreichbar: {str(e)}")
            except Exception as e:
                logger.error(f"Unerwarteter Fehler beim WordPress-Sync: {e}")
                raise HTTPException(status_code=500, detail=f"Sync-Fehler: {str(e)}")
    
    return all_events


@events_router.post("/sync/wordpress", tags=["Events Sync"])
async def sync_wordpress_events(user: dict = Depends(require_admin)):
    """
    Synchronisiert Events von WordPress (The Events Calendar / Tribe).
    
    - Idempotent: Mehrfach ausführbar ohne Duplikate
    - READ-ONLY: WordPress ist Single Source of Truth
    - Archiviert alte Events (löscht nicht)
    
    Returns: Report mit created, updated, archived, skipped
    """
    import time
    start_time = time.time()
    
    report = {
        "fetched": 0,
        "created": 0,
        "updated": 0,
        "unchanged": 0,  # NEU: Events ohne echte Änderungen
        "archived": 0,
        "skipped": 0,
        "errors": [],
    }
    
    try:
        # 1. Events von WordPress holen
        wp_events = await fetch_wordpress_events()
        report["fetched"] = len(wp_events)
        
        # Track welche external_ids wir gesehen haben
        seen_external_ids = set()
        
        # 2. Für jedes Event: Create oder Update
        for wp_event in wp_events:
            try:
                mapped = map_wordpress_event_to_gastrocore(wp_event)
                external_id = mapped["external_id"]
                seen_external_ids.add(external_id)
                
                # Prüfe ob Event bereits existiert
                existing = await db.events.find_one({
                    "external_source": SYNC_SOURCE,
                    "external_id": external_id,
                    "archived": {"$ne": True}
                })
                
                if existing:
                    # Prüfe ob sich wirklich etwas geändert hat
                    if has_real_changes(existing, mapped):
                        # ECHTES UPDATE - Nur gemappte Felder aktualisieren
                        update_fields = {
                            "title": mapped["title"],
                            "description": mapped["description"],
                            "short_description": mapped["short_description"],
                            "image_url": mapped["image_url"],
                            "start_datetime": mapped["start_datetime"],
                            "end_datetime": mapped["end_datetime"],
                            "entry_price": mapped["entry_price"],
                            "website_url": mapped["website_url"],
                            "slug": mapped["slug"],
                            "event_type": mapped["event_type"],
                            "wp_categories": mapped["wp_categories"],
                            "updated_at": now_iso(),
                            "last_sync_at": now_iso(),
                        }
                        
                        await db.events.update_one(
                            {"id": existing["id"]},
                            {"$set": update_fields}
                        )
                        report["updated"] += 1
                    else:
                        # Keine echten Änderungen - nur last_sync_at aktualisieren
                        await db.events.update_one(
                            {"id": existing["id"]},
                            {"$set": {"last_sync_at": now_iso()}}
                        )
                        report["unchanged"] += 1
                    
                else:
                    # CREATE - Neues Event
                    new_event = {
                        "id": str(uuid.uuid4()),
                        "external_source": mapped["external_source"],
                        "external_id": mapped["external_id"],
                        "title": mapped["title"],
                        "description": mapped["description"],
                        "short_description": mapped["short_description"],
                        "image_url": mapped["image_url"],
                        "start_datetime": mapped["start_datetime"],
                        "end_datetime": mapped["end_datetime"],
                        "entry_price": mapped["entry_price"],
                        "website_url": mapped["website_url"],
                        "slug": mapped["slug"],
                        "event_type": mapped["event_type"],
                        "content_category": "VERANSTALTUNG",
                        "wp_categories": mapped["wp_categories"],
                        # GastroCore Standard-Felder
                        "status": "published",
                        "capacity_total": 100,  # Default, manuell anpassbar
                        "booking_mode": "ticket_only",
                        "pricing_mode": "free_config",
                        "requires_payment": False,
                        "is_public": True,
                        "archived": False,
                        "created_at": now_iso(),
                        "updated_at": now_iso(),
                        "last_sync_at": now_iso(),
                    }
                    
                    await db.events.insert_one(new_event)
                    report["created"] += 1
                    
            except Exception as e:
                report["errors"].append(f"Event {wp_event.get('id')}: {str(e)}")
                report["skipped"] += 1
        
        # 3. Archivieren: Events die nicht mehr in WordPress sind
        # oder deren end_datetime > 2 Tage vergangen
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        
        # Finde alle WordPress-Events in DB
        all_wp_events_in_db = await db.events.find({
            "external_source": SYNC_SOURCE,
            "archived": {"$ne": True}
        }).to_list(1000)
        
        for db_event in all_wp_events_in_db:
            ext_id = db_event.get("external_id")
            end_dt = db_event.get("end_datetime")
            
            should_archive = False
            
            # Nicht mehr in WordPress vorhanden
            if ext_id not in seen_external_ids:
                should_archive = True
            
            # Oder Event ist abgelaufen (> 2 Tage)
            if end_dt and end_dt < cutoff_date:
                should_archive = True
            
            if should_archive:
                await db.events.update_one(
                    {"id": db_event["id"]},
                    {"$set": {"archived": True, "status": "archived", "updated_at": now_iso()}}
                )
                report["archived"] += 1
        
        # 4. Import-Log schreiben
        duration_ms = int((time.time() - start_time) * 1000)
        report["duration_ms"] = duration_ms
        
        # Bestimme Ergebnis-Status
        if len(report["errors"]) > 0:
            result_status = "partial" if report["created"] > 0 or report["updated"] > 0 else "error"
        else:
            result_status = "success"
        
        import_log = {
            "id": str(uuid.uuid4()),
            "type": "wordpress_events_sync",
            "timestamp": now_iso(),
            "user": user.get("email", "unknown"),
            "source": WORDPRESS_EVENTS_API,
            "fetched": report["fetched"],
            "created": report["created"],
            "updated": report["updated"],
            "unchanged": report["unchanged"],
            "archived": report["archived"],
            "skipped": report["skipped"],
            "errors": report["errors"][:10],  # Max 10 Fehler loggen
            "duration_ms": duration_ms,
            "success": result_status == "success",
            "result": result_status,
        }
        
        await db.import_logs.insert_one(import_log)
        
        # Audit Log
        await create_audit_log(
            actor=user,
            action="sync",
            entity="events",
            entity_id="wordpress",
            after={"report": report}
        )
        
        logger.info(f"WordPress Sync abgeschlossen: {report}")
        
        return {
            "success": True,
            "message": f"Sync abgeschlossen: {report['created']} neu, {report['updated']} geändert, {report['unchanged']} unverändert, {report['archived']} archiviert",
            "report": report
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"WordPress Sync Fehler: {e}")
        
        # Fehler-Log schreiben
        error_log = {
            "id": str(uuid.uuid4()),
            "type": "wordpress_events_sync",
            "timestamp": now_iso(),
            "user": user.get("email", "unknown"),
            "source": WORDPRESS_EVENTS_API,
            "success": False,
            "error": str(e),
        }
        await db.import_logs.insert_one(error_log)
        
        raise HTTPException(status_code=500, detail=f"Sync fehlgeschlagen: {str(e)}")


@events_router.get("/sync/wordpress/status", tags=["Events Sync"])
async def get_wordpress_sync_status(user: dict = Depends(require_manager)):
    """
    Liefert den Status des letzten WordPress-Syncs.
    Persistiert in import_logs - überlebt Neustarts.
    """
    last_sync = await db.import_logs.find_one(
        {"type": "wordpress_events_sync"},
        {"_id": 0},
        sort=[("timestamp", -1)]
    )
    
    if not last_sync:
        return {
            "last_run_at": None,
            "last_duration_ms": None,
            "last_result": None,
            "last_error": None,
            "message": "Noch kein Sync durchgeführt",
            "current_wordpress_events": 0,
        }
    
    # Zähle aktuelle WordPress-Events
    wp_events_count = await db.events.count_documents({
        "external_source": SYNC_SOURCE,
        "archived": {"$ne": True}
    })
    
    # Bestimme Result-Status
    result = last_sync.get("result", "success" if last_sync.get("success") else "error")
    
    return {
        "last_run_at": last_sync.get("timestamp"),
        "last_duration_ms": last_sync.get("duration_ms"),
        "last_result": result,
        "last_error": last_sync.get("error") if result == "error" else None,
        "counts": {
            "fetched": last_sync.get("fetched", 0),
            "created": last_sync.get("created", 0),
            "updated": last_sync.get("updated", 0),
            "unchanged": last_sync.get("unchanged", 0),
            "archived": last_sync.get("archived", 0),
            "skipped": last_sync.get("skipped", 0),
        },
        "current_wordpress_events": wp_events_count,
    }


@events_router.get("/sync/wordpress/preview", tags=["Events Sync"])
async def preview_wordpress_events(
    limit: int = Query(default=3, ge=1, le=10),
    user: dict = Depends(require_manager)
):
    """
    Zeigt eine Vorschau der WordPress-Events (gemappt).
    Nur zum Debuggen / Testen.
    """
    wp_events = await fetch_wordpress_events()
    
    preview = []
    for wp_event in wp_events[:limit]:
        mapped = map_wordpress_event_to_gastrocore(wp_event)
        preview.append({
            "wordpress_id": wp_event.get("id"),
            "mapped": mapped
        })
    
    return {
        "total_available": len(wp_events),
        "showing": len(preview),
        "preview": preview
    }
