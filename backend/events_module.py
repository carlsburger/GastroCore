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
