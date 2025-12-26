"""
GastroCore API v2.0.0 - Sprint 2: End-to-End Reservations
Features: Online Booking, Widget, Walk-ins, Waitlist, No-show Management, PDF Export
"""
from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, BackgroundTasks, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator
from typing import List, Optional, Any, Dict
import uuid
import re
import json
from datetime import datetime, timezone, timedelta, date
import logging
from pathlib import Path
from dotenv import load_dotenv
import os
import io

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Core imports
from core.config import settings
from core.database import db, client, close_db_connection
from core.auth import (
    get_current_user, require_roles, require_admin, require_manager, require_terminal,
    hash_password, verify_password, create_token, decode_token
)
from core.audit import create_audit_log, safe_dict_for_audit, SYSTEM_ACTOR
from core.models import UserRole, ReservationStatus, WaitlistStatus, GuestFlag, ReservationSource
from core.validators import (
    validate_status_transition, validate_reservation_data,
    validate_area_data, validate_user_data, validate_password_strength,
    validate_opening_hours, validate_capacity
)
from core.exceptions import (
    GastroCoreException, UnauthorizedException, ForbiddenException,
    NotFoundException, ValidationException, ConflictException,
    InvalidStatusTransitionException, CapacityExceededException
)
from email_service import (
    send_confirmation_email, send_reminder_email, send_cancellation_email,
    send_waitlist_notification, verify_cancel_token, get_email_templates,
    send_test_email, get_smtp_status, is_smtp_configured
)
from pdf_service import generate_table_plan_pdf
from import_module import (
    import_staff_from_json, import_staff_from_csv,
    import_predefined_carlsburg_data
)

# Reservation Config Module (Sprint: Reservierung Live-Ready)
from reservation_config_module import (
    reservation_config_router,
    get_default_duration,
    get_available_slots_for_date,
    get_opening_hours_for_date,
    check_capacity_with_duration,
    check_table_conflict,
    get_available_tables_for_slot,
    DEFAULT_DURATION_MINUTES
)

# System Settings Module (Sprint: System Settings & Opening Hours Master)
from system_settings_module import (
    system_settings_router,
    get_system_timezone,
    get_company_info
)

# Opening Hours Master Module (Sprint: System Settings & Opening Hours Master)
from opening_hours_module import (
    opening_hours_router,
    calculate_effective_hours,
    is_date_closed,
    get_reservable_slots_for_date
)

# Reservation Slots Module (Sprint: Slots & Durchgänge)
from reservation_slots_module import slots_router

# Table Module (Sprint: Tischplan & Belegung)
from table_module import (
    table_router,
    combination_router,
    TableArea,
    TableSubArea,
    OccupancyStatus,
    calculate_table_occupancy,
    suggest_tables_for_party
)

# ============== APP SETUP ==============
app = FastAPI(
    title="GastroCore API",
    version="2.0.0",
    description="End-to-End Restaurant Reservation System"
)

api_router = APIRouter(prefix="/api")
public_router = APIRouter(prefix="/api/public")  # No auth required

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============== EXCEPTION HANDLERS ==============
@app.exception_handler(GastroCoreException)
async def gastrocore_exception_handler(request: Request, exc: GastroCoreException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": exc.error_code, "success": False}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Ein unerwarteter Fehler ist aufgetreten", "error_code": "INTERNAL_ERROR", "success": False}
    )


# ============== PYDANTIC MODELS ==============
# Auth Models
class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8)
    role: UserRole

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    is_active: bool
    must_change_password: bool
    created_at: str
    staff_member_id: Optional[str] = None  # Verknüpfung mit Mitarbeiterprofil

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Area Models
class AreaCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    capacity: Optional[int] = Field(None, ge=1, le=500)
    table_count: Optional[int] = Field(None, ge=1, le=100)

# Reservation Models - Extended for Sprint 2 + Reservierung Live-Ready
class ReservationCreate(BaseModel):
    guest_name: str = Field(..., min_length=2, max_length=100)
    guest_phone: str = Field(..., min_length=6, max_length=30)
    guest_email: Optional[EmailStr] = None
    party_size: int = Field(..., ge=1, le=20)
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    area_id: Optional[str] = None
    table_number: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=1000)
    occasion: Optional[str] = Field(None, max_length=100)  # Anlass: Geburtstag, Hochzeit, etc.
    special_requests: Optional[List[str]] = Field(default_factory=list)  # ["🎂 Gesteck", "🐶 Hund dabei"]
    source: Optional[str] = "intern"  # widget, intern, walk-in
    language: Optional[str] = "de"  # de, en, pl
    # Sprint: Reservierung Live-Ready
    duration_minutes: Optional[int] = None  # None = Standard-Aufenthaltsdauer
    allergies: Optional[str] = Field(None, max_length=500)  # Allergien/Unverträglichkeiten
    menu_choice: Optional[str] = None  # Bei Menüpflicht
    # Sprint: Event-Pricing
    event_id: Optional[str] = None  # Verknüpftes Event (Aktion/Menü-Aktion/Kultur)
    variant_code: Optional[str] = None  # Bei Varianten-Pricing: gewählte Variante
    
    @field_validator('date')
    @classmethod
    def validate_date_format(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Ungültiges Datumsformat (YYYY-MM-DD erwartet)")
        return v
    
    @field_validator('time')
    @classmethod
    def validate_time_format(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError("Ungültiges Zeitformat (HH:MM erwartet)")
        return v

class ReservationUpdate(BaseModel):
    guest_name: Optional[str] = Field(None, min_length=2, max_length=100)
    guest_phone: Optional[str] = Field(None, min_length=6, max_length=30)
    guest_email: Optional[EmailStr] = None
    party_size: Optional[int] = Field(None, ge=1, le=20)
    date: Optional[str] = None
    time: Optional[str] = None
    area_id: Optional[str] = None
    table_number: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=1000)
    occasion: Optional[str] = None
    special_requests: Optional[List[str]] = None  # ["🎂 Gesteck", "🐶 Hund dabei"]
    # Sprint: Reservierung Live-Ready
    duration_minutes: Optional[int] = None
    allergies: Optional[str] = Field(None, max_length=500)
    menu_choice: Optional[str] = None

# Walk-in Quick Entry
class WalkInCreate(BaseModel):
    guest_name: str = Field(..., min_length=2, max_length=100)
    guest_phone: Optional[str] = Field(None, max_length=30)
    party_size: int = Field(..., ge=1, le=20)
    area_id: Optional[str] = None
    table_number: Optional[str] = None
    notes: Optional[str] = None

# Public Booking (Widget)
class PublicBookingCreate(BaseModel):
    guest_name: str = Field(..., min_length=2, max_length=100)
    guest_phone: str = Field(..., min_length=6, max_length=30)
    guest_email: EmailStr
    party_size: int = Field(..., ge=1, le=20)
    date: str
    time: str
    occasion: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=500)
    language: Optional[str] = "de"
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v):
        try:
            d = datetime.strptime(v, "%Y-%m-%d").date()
            if d < date.today():
                raise ValueError("Datum liegt in der Vergangenheit")
        except ValueError as e:
            if "Datum liegt" in str(e):
                raise e
            raise ValueError("Ungültiges Datumsformat")
        return v

# Waitlist Models
class WaitlistCreate(BaseModel):
    guest_name: str = Field(..., min_length=2, max_length=100)
    guest_phone: str = Field(..., min_length=6, max_length=30)
    guest_email: Optional[EmailStr] = None
    party_size: int = Field(..., ge=1, le=20)
    date: str
    preferred_time: Optional[str] = None
    priority: Optional[int] = Field(1, ge=1, le=5)  # 1=niedrig, 5=hoch
    notes: Optional[str] = None
    language: Optional[str] = "de"

class WaitlistUpdate(BaseModel):
    status: Optional[str] = None  # offen, informiert, eingeloest, erledigt
    priority: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = None

# Guest Models (for Grey/Blacklist)
class GuestCreate(BaseModel):
    phone: str = Field(..., min_length=6, max_length=30)
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    flag: Optional[str] = None  # none, greylist, blacklist
    no_show_count: Optional[int] = 0
    notes: Optional[str] = None

class GuestUpdate(BaseModel):
    flag: Optional[str] = None
    notes: Optional[str] = None

# Settings Models
class SettingCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    value: str
    description: Optional[str] = None

# Opening Hours
class OpeningHoursCreate(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)  # 0=Monday, 6=Sunday
    open_time: str  # HH:MM
    close_time: str  # HH:MM
    is_closed: bool = False

# Email Template
class EmailTemplateUpdate(BaseModel):
    template_type: str  # confirmation, reminder, cancellation, waitlist
    language: str  # de, en, pl
    subject: str
    body_html: str
    body_text: str


# ============== HELPER FUNCTIONS ==============
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def create_entity(data: dict, extra_fields: dict = None) -> dict:
    """Create a new entity with standard fields"""
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

async def get_guest_by_phone(phone: str) -> Optional[dict]:
    """Get guest record by phone number"""
    return await db.guests.find_one({"phone": phone, "archived": False}, {"_id": 0})

async def update_guest_no_show(phone: str, increment: int = 1):
    """Update guest no-show count and flag if threshold reached"""
    guest = await get_guest_by_phone(phone)
    
    # Get thresholds from settings
    greylist_threshold = 2
    blacklist_threshold = 4
    
    threshold_setting = await db.settings.find_one({"key": "no_show_greylist_threshold"})
    if threshold_setting:
        greylist_threshold = int(threshold_setting.get("value", 2))
    
    blacklist_setting = await db.settings.find_one({"key": "no_show_blacklist_threshold"})
    if blacklist_setting:
        blacklist_threshold = int(blacklist_setting.get("value", 4))
    
    if guest:
        new_count = guest.get("no_show_count", 0) + increment
        new_flag = guest.get("flag", "none")
        
        if new_count >= blacklist_threshold:
            new_flag = "blacklist"
        elif new_count >= greylist_threshold:
            new_flag = "greylist"
        
        await db.guests.update_one(
            {"phone": phone},
            {"$set": {"no_show_count": new_count, "flag": new_flag, "updated_at": now_iso()}}
        )
    else:
        # Create new guest record
        new_guest = {
            "id": str(uuid.uuid4()),
            "phone": phone,
            "no_show_count": increment,
            "flag": "greylist" if increment >= greylist_threshold else "none",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "archived": False
        }
        await db.guests.insert_one(new_guest)

async def check_capacity(date_str: str, time_str: str, party_size: int, area_id: str = None) -> dict:
    """Check if there's capacity for the reservation"""
    # Get all reservations for that time slot
    query = {
        "date": date_str,
        "time": time_str,
        "status": {"$in": ["neu", "bestaetigt", "angekommen"]},
        "archived": False
    }
    if area_id:
        query["area_id"] = area_id
    
    existing = await db.reservations.find(query, {"_id": 0}).to_list(1000)
    total_guests = sum(r.get("party_size", 0) for r in existing)
    
    # Get capacity from settings or area
    max_capacity = 100  # Default
    if area_id:
        area = await db.areas.find_one({"id": area_id, "archived": False}, {"_id": 0})
        if area and area.get("capacity"):
            max_capacity = area["capacity"]
    else:
        cap_setting = await db.settings.find_one({"key": "max_total_capacity"})
        if cap_setting:
            max_capacity = int(cap_setting.get("value", 100))
    
    available = max_capacity - total_guests
    
    return {
        "available": available >= party_size,
        "current_guests": total_guests,
        "max_capacity": max_capacity,
        "available_seats": available
    }

async def check_opening_hours(date_str: str, time_str: str) -> dict:
    """Check if restaurant is open at the given time"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day_of_week = dt.weekday()  # 0=Monday
        
        hours = await db.opening_hours.find_one({"day_of_week": day_of_week}, {"_id": 0})
        
        if not hours:
            # Default: open 11:00-22:00
            return {"open": True, "message": "Standard-Öffnungszeiten"}
        
        if hours.get("is_closed"):
            return {"open": False, "message": "Geschlossen an diesem Tag"}
        
        open_time = hours.get("open_time", "11:00")
        close_time = hours.get("close_time", "22:00")
        
        if open_time <= time_str <= close_time:
            return {"open": True, "open_time": open_time, "close_time": close_time}
        else:
            return {"open": False, "message": f"Öffnungszeiten: {open_time} - {close_time}"}
    except Exception:
        return {"open": True}  # Default to open on error


# ============== AUTH ENDPOINTS ==============
@api_router.post("/auth/login", response_model=TokenResponse, tags=["Auth"])
async def login(data: UserLogin):
    user = await db.users.find_one({"email": data.email, "archived": False}, {"_id": 0})
    
    if not user or not verify_password(data.password, user["password_hash"]):
        raise UnauthorizedException("Ungültige Anmeldedaten")
    
    if not user.get("is_active", True):
        raise UnauthorizedException("Konto deaktiviert")
    
    token = create_token(user["id"], user["email"], user["role"])
    await create_audit_log(user, "user", user["id"], "login")
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"], email=user["email"], name=user["name"], role=user["role"],
            is_active=user["is_active"], must_change_password=user.get("must_change_password", False),
            created_at=user["created_at"]
        )
    )

@api_router.get("/auth/me", response_model=UserResponse, tags=["Auth"])
async def get_me(user: dict = Depends(get_current_user)):
    return UserResponse(
        id=user["id"], email=user["email"], name=user["name"], role=user["role"],
        is_active=user["is_active"], must_change_password=user.get("must_change_password", False),
        created_at=user["created_at"],
        staff_member_id=user.get("staff_member_id")
    )

@api_router.post("/auth/change-password", tags=["Auth"])
async def change_password(data: PasswordChange, user: dict = Depends(get_current_user)):
    if not verify_password(data.current_password, user["password_hash"]):
        raise ValidationException("Aktuelles Passwort ist falsch")
    
    validate_password_strength(data.new_password)
    before = safe_dict_for_audit(user)
    
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": hash_password(data.new_password), "must_change_password": False, "updated_at": now_iso()}}
    )
    
    await create_audit_log(user, "user", user["id"], "password_change", before, {**before, "must_change_password": False})
    return {"message": "Passwort erfolgreich geändert", "success": True}


# ============== USER ENDPOINTS ==============
@api_router.get("/users", response_model=List[UserResponse], tags=["Users"])
async def get_users(user: dict = Depends(require_admin)):
    users = await db.users.find({"archived": False}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return [UserResponse(**u) for u in users]

@api_router.post("/users", response_model=UserResponse, tags=["Users"])
async def create_user(data: UserCreate, user: dict = Depends(require_admin)):
    existing = await db.users.find_one({"email": data.email, "archived": False})
    if existing:
        raise ConflictException("E-Mail bereits registriert")
    
    new_user = {
        "id": str(uuid.uuid4()), "email": data.email, "name": data.name, "role": data.role.value,
        "password_hash": hash_password(data.password), "is_active": True, "must_change_password": True,
        "created_at": now_iso(), "updated_at": now_iso(), "archived": False
    }
    
    await db.users.insert_one(new_user)
    await create_audit_log(user, "user", new_user["id"], "create", None, safe_dict_for_audit(new_user))
    
    return UserResponse(**{k: v for k, v in new_user.items() if k != "password_hash"})

@api_router.delete("/users/{user_id}", tags=["Users"])
async def archive_user(user_id: str, user: dict = Depends(require_admin)):
    if user_id == user["id"]:
        raise ValidationException("Eigenes Konto kann nicht archiviert werden")
    
    existing = await db.users.find_one({"id": user_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Benutzer")
    
    before = safe_dict_for_audit(existing)
    await db.users.update_one({"id": user_id}, {"$set": {"archived": True, "updated_at": now_iso()}})
    await create_audit_log(user, "user", user_id, "archive", before, {**before, "archived": True})
    
    return {"message": "Benutzer archiviert", "success": True}


@api_router.post("/users/{user_id}/link-staff", tags=["Users"])
async def link_user_to_staff(user_id: str, staff_member_id: str = None, user: dict = Depends(require_admin)):
    """
    Verknüpft einen User mit einem Mitarbeiterprofil (Admin-only).
    
    - User und Staff bleiben getrennte Entitäten
    - Admin entscheidet bewusst über Verknüpfung
    - Admin-Accounts sollten nicht verknüpft werden
    """
    # User existiert?
    target_user = await db.users.find_one({"id": user_id, "archived": False}, {"_id": 0})
    if not target_user:
        raise NotFoundException("Benutzer")
    
    # Admin-Accounts nicht verknüpfen (Warnung)
    if target_user.get("role") == "admin":
        raise ValidationException("Admin-Accounts sollten nicht mit Mitarbeiterprofilen verknüpft werden")
    
    # Wenn staff_member_id = None, dann Verknüpfung aufheben
    if not staff_member_id:
        before = safe_dict_for_audit(target_user)
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"staff_member_id": None, "updated_at": now_iso()}}
        )
        await create_audit_log(user, "user", user_id, "unlink_staff", before, {**before, "staff_member_id": None})
        return {"message": "Verknüpfung aufgehoben", "success": True}
    
    # Staff existiert?
    staff = await db.staff_members.find_one({"id": staff_member_id, "archived": False}, {"_id": 0})
    if not staff:
        raise NotFoundException("Mitarbeiterprofil")
    
    # Prüfe ob bereits ein anderer User verknüpft ist (Warnung, kein Blocker)
    existing_link = await db.users.find_one({
        "staff_member_id": staff_member_id, 
        "id": {"$ne": user_id},
        "archived": False
    })
    
    warning = None
    if existing_link:
        warning = f"Hinweis: Dieses Profil ist bereits mit {existing_link.get('email')} verknüpft"
    
    # Verknüpfung erstellen
    before = safe_dict_for_audit(target_user)
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"staff_member_id": staff_member_id, "updated_at": now_iso()}}
    )
    
    staff_name = f"{staff.get('first_name', '')} {staff.get('last_name', '')}".strip()
    await create_audit_log(user, "user", user_id, "link_staff", before, {**before, "staff_member_id": staff_member_id})
    
    return {
        "message": f"Benutzer erfolgreich mit '{staff_name}' verknüpft",
        "success": True,
        "staff_member_id": staff_member_id,
        "staff_name": staff_name,
        "warning": warning
    }


@api_router.get("/users/{user_id}/staff-link", tags=["Users"])
async def get_user_staff_link(user_id: str, user: dict = Depends(require_admin)):
    """Zeigt den aktuellen Verknüpfungsstatus eines Users"""
    target_user = await db.users.find_one({"id": user_id, "archived": False}, {"_id": 0})
    if not target_user:
        raise NotFoundException("Benutzer")
    
    staff_member_id = target_user.get("staff_member_id")
    
    if not staff_member_id:
        return {
            "linked": False,
            "staff_member_id": None,
            "staff_name": None
        }
    
    staff = await db.staff_members.find_one({"id": staff_member_id}, {"_id": 0})
    
    return {
        "linked": True,
        "staff_member_id": staff_member_id,
        "staff_name": f"{staff.get('first_name', '')} {staff.get('last_name', '')}".strip() if staff else "Unbekannt"
    }


# ============== AREA ENDPOINTS ==============
@api_router.get("/areas", tags=["Areas"])
async def get_areas(user: dict = Depends(get_current_user)):
    areas = await db.areas.find({"archived": False}, {"_id": 0}).to_list(1000)
    return areas

@api_router.post("/areas", tags=["Areas"])
async def create_area(data: AreaCreate, user: dict = Depends(require_admin)):
    area = create_entity(data.model_dump(exclude_none=True))
    await db.areas.insert_one(area)
    await create_audit_log(user, "area", area["id"], "create", None, safe_dict_for_audit(area))
    return {k: v for k, v in area.items() if k != "_id"}

@api_router.put("/areas/{area_id}", tags=["Areas"])
async def update_area(area_id: str, data: AreaCreate, user: dict = Depends(require_admin)):
    existing = await db.areas.find_one({"id": area_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Bereich")
    
    before = safe_dict_for_audit(existing)
    update_data = {**data.model_dump(exclude_none=True), "updated_at": now_iso()}
    await db.areas.update_one({"id": area_id}, {"$set": update_data})
    
    updated = await db.areas.find_one({"id": area_id}, {"_id": 0})
    await create_audit_log(user, "area", area_id, "update", before, safe_dict_for_audit(updated))
    return updated

@api_router.delete("/areas/{area_id}", tags=["Areas"])
async def archive_area(area_id: str, user: dict = Depends(require_admin)):
    existing = await db.areas.find_one({"id": area_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Bereich")
    
    before = safe_dict_for_audit(existing)
    await db.areas.update_one({"id": area_id}, {"$set": {"archived": True, "updated_at": now_iso()}})
    await create_audit_log(user, "area", area_id, "archive", before, {**before, "archived": True})
    return {"message": "Bereich archiviert", "success": True}


# ============== RESERVATION ENDPOINTS ==============
@api_router.get("/reservations", tags=["Reservations"])
async def get_reservations(
    date: Optional[str] = None,
    status: Optional[str] = None,
    area_id: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 200,
    user: dict = Depends(get_current_user)
):
    if user["role"] == UserRole.MITARBEITER.value:
        raise ForbiddenException("Kein Zugriff auf Reservierungen")
    
    query = {"archived": False}
    if date:
        query["date"] = date
    if status:
        query["status"] = status
    if area_id:
        query["area_id"] = area_id
    if source:
        query["source"] = source
    if search:
        query["$or"] = [
            {"guest_name": {"$regex": search, "$options": "i"}},
            {"guest_phone": {"$regex": search, "$options": "i"}}
        ]
    
    reservations = await db.reservations.find(query, {"_id": 0}).sort("time", 1).limit(limit).to_list(limit)
    
    # Enrich with guest flags
    for res in reservations:
        guest = await get_guest_by_phone(res.get("guest_phone", ""))
        if guest and guest.get("flag") and guest["flag"] != "none":
            res["guest_flag"] = guest["flag"]
            res["no_show_count"] = guest.get("no_show_count", 0)
    
    return reservations


@api_router.get("/reservations/summary", tags=["Reservations"])
async def get_reservations_summary(
    days: int = Query(default=7, ge=1, le=30, description="Anzahl Tage"),
    start: Optional[str] = Query(default=None, description="Startdatum (YYYY-MM-DD), default=heute"),
    user: dict = Depends(require_manager)
):
    """
    7-Tage Übersicht für Dashboard.
    Liefert pro Tag: Anzahl Reservierungen + Summe Gäste.
    
    Nur für Admin/Schichtleiter.
    """
    from datetime import datetime, timedelta
    
    # Deutsche Wochentags-Abkürzungen (VERBINDLICH)
    WEEKDAYS_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    
    # Startdatum bestimmen
    if start:
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Ungültiges Datumsformat (YYYY-MM-DD)")
    else:
        start_date = datetime.now().date()
    
    result = {
        "start": start_date.isoformat(),
        "days": []
    }
    
    # Für jeden Tag aggregieren
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.isoformat()
        weekday_de = WEEKDAYS_DE[current_date.weekday()]  # 0=Mo, 6=So
        
        # Aggregation: Zähle Reservierungen und summiere Gäste
        pipeline = [
            {"$match": {"date": date_str, "archived": False}},
            {"$group": {
                "_id": None,
                "reservations": {"$sum": 1},
                "guests": {"$sum": {"$ifNull": ["$party_size", 0]}}
            }}
        ]
        
        agg_result = await db.reservations.aggregate(pipeline).to_list(1)
        
        if agg_result:
            result["days"].append({
                "date": date_str,
                "weekday": weekday_de,
                "reservations": agg_result[0]["reservations"],
                "guests": agg_result[0]["guests"]
            })
        else:
            result["days"].append({
                "date": date_str,
                "weekday": weekday_de,
                "reservations": 0,
                "guests": 0
            })
    
    return result


@api_router.get("/reservations/{reservation_id}", tags=["Reservations"])
async def get_reservation(reservation_id: str, user: dict = Depends(get_current_user)):
    if user["role"] == UserRole.MITARBEITER.value:
        raise ForbiddenException("Kein Zugriff auf Reservierungen")
    
    reservation = await db.reservations.find_one({"id": reservation_id, "archived": False}, {"_id": 0})
    if not reservation:
        raise NotFoundException("Reservierung")
    return reservation

@api_router.post("/reservations", tags=["Reservations"])
async def create_reservation(
    data: ReservationCreate,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_manager)
):
    # Check guest flag
    guest = await get_guest_by_phone(data.guest_phone)
    if guest and guest.get("flag") == "blacklist":
        raise ValidationException("Gast ist auf der Blacklist")
    
    # Check capacity
    capacity = await check_capacity(data.date, data.time, data.party_size, data.area_id)
    if not capacity["available"]:
        raise CapacityExceededException(f"Keine Kapazität verfügbar. Verfügbare Plätze: {capacity['available_seats']}")
    
    # Sprint: Tisch-Doppelbelegungsprüfung
    if data.table_number:
        duration = data.duration_minutes or await get_default_duration()
        table_check = await check_table_conflict(data.date, data.time, data.table_number, duration)
        if not table_check["available"]:
            raise ConflictException(table_check.get("message", f"Tisch {data.table_number} ist bereits belegt"))
    
    # Sprint: Event-Pricing - Berechne Preise und setze Status
    event_pricing_data = {}
    initial_status = "neu"
    
    if data.event_id:
        event = await db.events.find_one({"id": data.event_id, "archived": False})
        if event:
            pricing = event.get("event_pricing", {})
            policy = event.get("payment_policy", {})
            
            # Preis pro Person ermitteln
            price_per_person = 0
            variant_name = None
            
            if pricing.get("pricing_mode") == "variants":
                if not data.variant_code:
                    raise ValidationException("Bei Varianten-Pricing muss eine Variante gewählt werden")
                variants = pricing.get("variants", [])
                selected = next((v for v in variants if v["code"] == data.variant_code), None)
                if not selected:
                    raise ValidationException(f"Variante '{data.variant_code}' nicht gefunden")
                price_per_person = selected["price_per_person"]
                variant_name = selected["name"]
            else:
                price_per_person = pricing.get("single_price_per_person", 0)
            
            # Gesamtpreis berechnen
            total_price = round(price_per_person * data.party_size, 2)
            
            # Event-Pricing Daten für Reservierung
            event_pricing_data = {
                "event_id": data.event_id,
                "event_title": event.get("title"),
                "content_category": event.get("content_category"),
                "variant_code": data.variant_code,
                "variant_name": variant_name,
                "price_per_person": price_per_person,
                "total_price": total_price,
                "currency": pricing.get("currency", "EUR"),
            }
            
            # Payment Policy verarbeiten
            if policy.get("required"):
                payment_mode = policy.get("mode", "none")
                
                if payment_mode == "deposit":
                    deposit_type = policy.get("deposit_type", "fixed_per_person")
                    deposit_value = policy.get("deposit_value", 0)
                    
                    if deposit_type == "fixed_per_person":
                        amount_due = round(deposit_value * data.party_size, 2)
                    elif deposit_type == "percent_of_total":
                        amount_due = round(total_price * (deposit_value / 100), 2)
                    else:
                        amount_due = 0
                    
                    event_pricing_data["payment_mode"] = "deposit"
                    event_pricing_data["amount_due"] = amount_due
                    event_pricing_data["deposit_per_person"] = deposit_value
                    
                elif payment_mode == "full":
                    event_pricing_data["payment_mode"] = "full"
                    event_pricing_data["amount_due"] = total_price
                
                # Status auf pending_payment setzen
                initial_status = "pending_payment"
                event_pricing_data["payment_status"] = "pending"
                event_pricing_data["payment_window_minutes"] = policy.get("payment_window_minutes", 30)
                event_pricing_data["payment_due_at"] = (
                    datetime.now(timezone.utc) + timedelta(minutes=policy.get("payment_window_minutes", 30))
                ).isoformat()
            else:
                event_pricing_data["payment_mode"] = "none"
                event_pricing_data["payment_status"] = "not_required"
    
    reservation = create_entity(
        data.model_dump(exclude_none=True),
        {
            "status": initial_status,
            "reminder_sent": False,
            "source": data.source or "intern",
            **event_pricing_data
        }
    )
    
    await db.reservations.insert_one(reservation)
    await create_audit_log(user, "reservation", reservation["id"], "create", None, safe_dict_for_audit(reservation))
    
    # Send confirmation email
    if data.guest_email:
        area_name = None
        if data.area_id:
            area_doc = await db.areas.find_one({"id": data.area_id}, {"_id": 0})
            area_name = area_doc.get("name") if area_doc else None
        background_tasks.add_task(send_confirmation_email, reservation, area_name, data.language or "de")
    
    return {k: v for k, v in reservation.items() if k != "_id"}

@api_router.put("/reservations/{reservation_id}", tags=["Reservations"])
async def update_reservation(reservation_id: str, data: ReservationUpdate, user: dict = Depends(require_manager)):
    existing = await db.reservations.find_one({"id": reservation_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Reservierung")
    
    if ReservationStatus.is_terminal(existing.get("status")):
        raise ValidationException("Abgeschlossene Reservierungen können nicht mehr bearbeitet werden")
    
    # Sprint: Tisch-Doppelbelegungsprüfung bei Tisch-Änderung
    new_table = data.table_number if data.table_number is not None else existing.get("table_number")
    new_date = data.date if data.date is not None else existing.get("date")
    new_time = data.time if data.time is not None else existing.get("time")
    
    if new_table and (new_table != existing.get("table_number") or new_date != existing.get("date") or new_time != existing.get("time")):
        duration = data.duration_minutes or existing.get("duration_minutes") or await get_default_duration()
        table_check = await check_table_conflict(new_date, new_time, new_table, duration, exclude_reservation_id=reservation_id)
        if not table_check["available"]:
            raise ConflictException(table_check.get("message", f"Tisch {new_table} ist bereits belegt"))
    
    before = safe_dict_for_audit(existing)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now_iso()
    
    await db.reservations.update_one({"id": reservation_id}, {"$set": update_data})
    
    updated = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    await create_audit_log(user, "reservation", reservation_id, "update", before, safe_dict_for_audit(updated))
    return updated

@api_router.patch("/reservations/{reservation_id}/status", tags=["Reservations"])
async def update_reservation_status(
    reservation_id: str,
    new_status: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_terminal)
):
    existing = await db.reservations.find_one({"id": reservation_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Reservierung")
    
    current_status = existing.get("status")
    validate_status_transition(current_status, new_status)
    
    before = safe_dict_for_audit(existing)
    update_data = {"status": new_status, "updated_at": now_iso()}
    
    # Handle no-show
    if new_status == "no_show":
        await update_guest_no_show(existing.get("guest_phone", ""))
    
    await db.reservations.update_one({"id": reservation_id}, {"$set": update_data})
    
    updated = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    await create_audit_log(user, "reservation", reservation_id, "status_change", before, safe_dict_for_audit(updated))
    
    # Send confirmation email when confirmed
    if new_status == "bestaetigt" and current_status != "bestaetigt":
        if updated.get("guest_email"):
            area_name = None
            if updated.get("area_id"):
                area_doc = await db.areas.find_one({"id": updated["area_id"]}, {"_id": 0})
                area_name = area_doc.get("name") if area_doc else None
            background_tasks.add_task(send_confirmation_email, updated, area_name, updated.get("language", "de"))
    
    return updated

@api_router.patch("/reservations/{reservation_id}/assign", tags=["Reservations"])
async def assign_table(
    reservation_id: str,
    area_id: Optional[str] = None,
    table_number: Optional[str] = None,
    user: dict = Depends(require_terminal)
):
    """Quick table/area assignment for walk-ins and service"""
    existing = await db.reservations.find_one({"id": reservation_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Reservierung")
    
    before = safe_dict_for_audit(existing)
    update_data = {"updated_at": now_iso()}
    if area_id:
        update_data["area_id"] = area_id
    if table_number:
        update_data["table_number"] = table_number
    
    await db.reservations.update_one({"id": reservation_id}, {"$set": update_data})
    
    updated = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    await create_audit_log(user, "reservation", reservation_id, "update", before, safe_dict_for_audit(updated))
    return updated

@api_router.delete("/reservations/{reservation_id}", tags=["Reservations"])
async def archive_reservation(reservation_id: str, user: dict = Depends(require_manager)):
    existing = await db.reservations.find_one({"id": reservation_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Reservierung")
    
    before = safe_dict_for_audit(existing)
    await db.reservations.update_one({"id": reservation_id}, {"$set": {"archived": True, "updated_at": now_iso()}})
    await create_audit_log(user, "reservation", reservation_id, "archive", before, {**before, "archived": True})
    return {"message": "Reservierung archiviert", "success": True}


# ============== WALK-IN ENDPOINTS ==============
@api_router.post("/walk-ins", tags=["Walk-ins"])
async def create_walk_in(data: WalkInCreate, user: dict = Depends(require_terminal)):
    """Quick walk-in entry - immediately set to 'angekommen'"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_time = datetime.now(timezone.utc).strftime("%H:%M")
    
    reservation = create_entity({
        "guest_name": data.guest_name,
        "guest_phone": data.guest_phone or "",
        "party_size": data.party_size,
        "date": today,
        "time": now_time,
        "area_id": data.area_id,
        "table_number": data.table_number,
        "notes": data.notes,
        "source": "walk-in",
        "status": "angekommen",  # Walk-ins are immediately seated
        "reminder_sent": True  # No reminder needed
    })
    
    await db.reservations.insert_one(reservation)
    await create_audit_log(user, "reservation", reservation["id"], "create", None, safe_dict_for_audit(reservation))
    
    return {k: v for k, v in reservation.items() if k != "_id"}


# ============== WAITLIST ENDPOINTS ==============
@api_router.get("/waitlist", tags=["Waitlist"])
async def get_waitlist(
    date: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(require_terminal)
):
    query = {"archived": False}
    if date:
        query["date"] = date
    if status:
        query["status"] = status
    
    entries = await db.waitlist.find(query, {"_id": 0}).sort([("priority", -1), ("created_at", 1)]).to_list(500)
    return entries

@api_router.post("/waitlist", tags=["Waitlist"])
async def create_waitlist_entry(data: WaitlistCreate, user: dict = Depends(require_terminal)):
    entry = create_entity(
        data.model_dump(exclude_none=True),
        {"status": "offen"}
    )
    
    await db.waitlist.insert_one(entry)
    await create_audit_log(user, "waitlist", entry["id"], "create", None, safe_dict_for_audit(entry))
    
    return {k: v for k, v in entry.items() if k != "_id"}

@api_router.patch("/waitlist/{entry_id}", tags=["Waitlist"])
async def update_waitlist_entry(
    entry_id: str,
    data: WaitlistUpdate,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_terminal)
):
    existing = await db.waitlist.find_one({"id": entry_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Wartelisten-Eintrag")
    
    before = safe_dict_for_audit(existing)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now_iso()
    
    await db.waitlist.update_one({"id": entry_id}, {"$set": update_data})
    
    updated = await db.waitlist.find_one({"id": entry_id}, {"_id": 0})
    await create_audit_log(user, "waitlist", entry_id, "status_change", before, safe_dict_for_audit(updated))
    
    # Send notification when status changes to "informiert"
    if data.status == "informiert" and existing.get("status") != "informiert":
        if updated.get("guest_email"):
            background_tasks.add_task(send_waitlist_notification, updated, updated.get("language", "de"))
    
    return updated

@api_router.post("/waitlist/{entry_id}/convert", tags=["Waitlist"])
async def convert_waitlist_to_reservation(
    entry_id: str,
    time: str,
    area_id: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    user: dict = Depends(require_manager)
):
    """Convert waitlist entry to actual reservation"""
    entry = await db.waitlist.find_one({"id": entry_id, "archived": False}, {"_id": 0})
    if not entry:
        raise NotFoundException("Wartelisten-Eintrag")
    
    # Create reservation from waitlist
    reservation = create_entity({
        "guest_name": entry["guest_name"],
        "guest_phone": entry.get("guest_phone", ""),
        "guest_email": entry.get("guest_email"),
        "party_size": entry["party_size"],
        "date": entry["date"],
        "time": time,
        "area_id": area_id,
        "notes": entry.get("notes"),
        "source": "waitlist",
        "language": entry.get("language", "de")
    }, {"status": "bestaetigt", "reminder_sent": False})
    
    await db.reservations.insert_one(reservation)
    await create_audit_log(user, "reservation", reservation["id"], "create", None, safe_dict_for_audit(reservation))
    
    # Update waitlist entry
    await db.waitlist.update_one(
        {"id": entry_id},
        {"$set": {"status": "eingeloest", "converted_reservation_id": reservation["id"], "updated_at": now_iso()}}
    )
    await create_audit_log(user, "waitlist", entry_id, "status_change", safe_dict_for_audit(entry), {"status": "eingeloest"})
    
    # Send confirmation
    if reservation.get("guest_email") and background_tasks:
        area_name = None
        if area_id:
            area_doc = await db.areas.find_one({"id": area_id}, {"_id": 0})
            area_name = area_doc.get("name") if area_doc else None
        background_tasks.add_task(send_confirmation_email, reservation, area_name, reservation.get("language", "de"))
    
    return {k: v for k, v in reservation.items() if k != "_id"}

@api_router.delete("/waitlist/{entry_id}", tags=["Waitlist"])
async def archive_waitlist_entry(entry_id: str, user: dict = Depends(require_manager)):
    existing = await db.waitlist.find_one({"id": entry_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Wartelisten-Eintrag")
    
    before = safe_dict_for_audit(existing)
    await db.waitlist.update_one({"id": entry_id}, {"$set": {"archived": True, "updated_at": now_iso()}})
    await create_audit_log(user, "waitlist", entry_id, "archive", before, {**before, "archived": True})
    return {"message": "Wartelisten-Eintrag archiviert", "success": True}


# ============== GUEST MANAGEMENT (Grey/Blacklist) ==============
def escape_regex(pattern: str) -> str:
    """Escape special regex characters for safe MongoDB regex search"""
    return re.escape(pattern)

@api_router.get("/guests", tags=["Guests"])
async def get_guests(
    flag: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(require_manager)
):
    query = {"archived": False}
    if flag:
        query["flag"] = flag
    if search:
        # Escape special regex characters to prevent MongoDB regex errors
        safe_search = escape_regex(search)
        query["$or"] = [
            {"phone": {"$regex": safe_search, "$options": "i"}},
            {"name": {"$regex": safe_search, "$options": "i"}},
            {"email": {"$regex": safe_search, "$options": "i"}}
        ]
    
    guests = await db.guests.find(query, {"_id": 0}).to_list(500)
    return guests


# Sprint: Gäste-Autocomplete für schnelle Auswahl
@api_router.get("/guests/autocomplete", tags=["Guests"])
async def autocomplete_guests(
    q: str = Query(..., min_length=2, description="Suchbegriff (min. 2 Zeichen)"),
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(get_current_user)
):
    """
    Schnelle Gäste-Suche für Autocomplete.
    Sucht in Name, Telefon und E-Mail.
    Gibt Besuchszähler und letzten Besuch mit zurück.
    """
    safe_search = escape_regex(q)
    
    # Suche in Gäste-Datenbank
    guests = await db.guests.find(
        {
            "archived": False,
            "$or": [
                {"name": {"$regex": safe_search, "$options": "i"}},
                {"phone": {"$regex": safe_search, "$options": "i"}},
                {"email": {"$regex": safe_search, "$options": "i"}}
            ]
        },
        {"_id": 0}
    ).limit(limit).to_list(limit)
    
    # Für jeden Gast: Besuchszähler und letzten Besuch hinzufügen
    result = []
    for guest in guests:
        # Zähle abgeschlossene Reservierungen
        visit_count = await db.reservations.count_documents({
            "guest_phone": guest.get("phone"),
            "status": {"$in": ["abgeschlossen", "angekommen"]},
            "archived": False
        })
        
        # Letzter Besuch
        last_visit = await db.reservations.find_one(
            {
                "guest_phone": guest.get("phone"),
                "status": {"$in": ["abgeschlossen", "angekommen"]},
                "archived": False
            },
            {"_id": 0, "date": 1, "time": 1},
            sort=[("date", -1), ("time", -1)]
        )
        
        result.append({
            "id": guest.get("id"),
            "name": guest.get("name"),
            "phone": guest.get("phone"),
            "email": guest.get("email"),
            "flag": guest.get("flag"),
            "notes": guest.get("notes"),
            "newsletter_subscribed": guest.get("newsletter_subscribed", True),
            "visit_count": visit_count,
            "last_visit": last_visit.get("date") if last_visit else None,
            "source": "guests"
        })
    
    # NEU: Suche auch in guest_contacts (Legacy-Import, nur Reservierung)
    if len(result) < limit:
        existing_phones = {g["phone"] for g in result if g.get("phone")}
        existing_emails = {g["email"] for g in result if g.get("email")}
        
        contacts = await db.guest_contacts.find(
            {
                "archived": False,
                "contact_type": "reservation_guest",
                "$or": [
                    {"first_name": {"$regex": safe_search, "$options": "i"}},
                    {"last_name": {"$regex": safe_search, "$options": "i"}},
                    {"phone": {"$regex": safe_search, "$options": "i"}},
                    {"email": {"$regex": safe_search, "$options": "i"}}
                ]
            },
            {"_id": 0}
        ).limit(limit * 2).to_list(limit * 2)
        
        for contact in contacts:
            # Skip wenn bereits über phone oder email gefunden
            if contact.get("phone") in existing_phones:
                continue
            if contact.get("email") and contact.get("email") in existing_emails:
                continue
            
            # Namen formatieren: "V. Nachname"
            fn = contact.get("first_name", "")
            ln = contact.get("last_name", "")
            if fn and ln:
                display_name = f"{fn[0]}. {ln}"
            elif ln:
                display_name = ln
            elif fn:
                display_name = fn
            else:
                display_name = "Unbekannt"
            
            result.append({
                "id": contact.get("id"),
                "name": display_name,
                "phone": contact.get("phone"),
                "email": contact.get("email"),
                "flag": None,
                "notes": contact.get("notes"),
                "newsletter_subscribed": False,  # WICHTIG: Legacy-Kontakte haben KEIN Marketing
                "marketing_consent": contact.get("marketing_consent", False),
                "visit_count": contact.get("reservation_count", 0),
                "last_visit": contact.get("last_reservation_date"),
                "source": "guest_contacts"
            })
            existing_phones.add(contact.get("phone"))
            if contact.get("email"):
                existing_emails.add(contact.get("email"))
            
            if len(result) >= limit:
                break
    
    # Auch in Reservierungen suchen (für Gäste die noch nicht in guests sind)
    if len(result) < limit:
        res_guests = await db.reservations.aggregate([
            {
                "$match": {
                    "archived": False,
                    "$or": [
                        {"guest_name": {"$regex": safe_search, "$options": "i"}},
                        {"guest_phone": {"$regex": safe_search, "$options": "i"}}
                    ]
                }
            },
            {
                "$group": {
                    "_id": "$guest_phone",
                    "name": {"$first": "$guest_name"},
                    "phone": {"$first": "$guest_phone"},
                    "email": {"$first": "$guest_email"},
                    "visit_count": {"$sum": 1},
                    "last_visit": {"$max": "$date"}
                }
            },
            {"$limit": limit - len(result)}
        ]).to_list(limit)
        
        # Nur hinzufügen wenn nicht bereits in result
        existing_phones = {g["phone"] for g in result}
        for rg in res_guests:
            if rg["_id"] and rg["_id"] not in existing_phones:
                result.append({
                    "id": None,
                    "name": rg["name"],
                    "phone": rg["phone"],
                    "email": rg.get("email"),
                    "flag": None,
                    "notes": None,
                    "newsletter_subscribed": True,
                    "visit_count": rg["visit_count"],
                    "last_visit": rg["last_visit"],
                    "source": "reservations"
                })
    
    # Sortiere nach Besuchszähler (Stammgäste zuerst)
    result.sort(key=lambda x: x["visit_count"], reverse=True)
    
    return result[:limit]


# NEU: Dedizierter Endpoint für guest_contacts (nur Reservierungskontakte, KEIN Marketing)
@api_router.get("/guest-contacts/search", tags=["Guests"])
async def search_guest_contacts(
    q: str = Query(..., min_length=2, description="Suchbegriff (min. 2 Zeichen)"),
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(get_current_user)
):
    """
    Suche in der Legacy-Gästekontakt-Datenbank.
    NUR für operative Reservierungszwecke - KEIN Marketing!
    
    Sucht in: first_name, last_name, phone, email
    """
    safe_search = escape_regex(q)
    
    contacts = await db.guest_contacts.find(
        {
            "archived": False,
            "contact_type": "reservation_guest",
            "$or": [
                {"first_name": {"$regex": safe_search, "$options": "i"}},
                {"last_name": {"$regex": safe_search, "$options": "i"}},
                {"phone": {"$regex": safe_search, "$options": "i"}},
                {"email": {"$regex": safe_search, "$options": "i"}}
            ]
        },
        {"_id": 0}
    ).limit(limit).to_list(limit)
    
    result = []
    for contact in contacts:
        fn = contact.get("first_name", "")
        ln = contact.get("last_name", "")
        if fn and ln:
            display_name = f"{fn[0]}. {ln}"
        elif ln:
            display_name = ln
        elif fn:
            display_name = fn
        else:
            display_name = "Unbekannt"
        
        result.append({
            "id": contact.get("id"),
            "display_name": display_name,
            "full_name": f"{fn} {ln}".strip(),
            "first_name": fn,
            "last_name": ln,
            "phone": contact.get("phone"),
            "email": contact.get("email"),
            "notes": contact.get("notes"),
            "marketing_consent": contact.get("marketing_consent", False),
            "last_reservation_date": contact.get("last_reservation_date"),
            "reservation_count": contact.get("reservation_count", 0)
        })
    
    return {
        "query": q,
        "count": len(result),
        "contacts": result
    }


@api_router.get("/guest-contacts/stats", tags=["Guests"])
async def get_guest_contacts_stats(user: dict = Depends(require_manager)):
    """
    Statistiken zur guest_contacts Collection.
    """
    total = await db.guest_contacts.count_documents({"archived": False})
    with_email = await db.guest_contacts.count_documents({"archived": False, "email": {"$ne": None, "$ne": ""}})
    with_phone = await db.guest_contacts.count_documents({"archived": False, "phone": {"$ne": None, "$ne": ""}})
    with_notes = await db.guest_contacts.count_documents({"archived": False, "notes": {"$ne": None, "$ne": ""}})
    marketing_false = await db.guest_contacts.count_documents({"archived": False, "marketing_consent": False})
    
    return {
        "total": total,
        "with_email": with_email,
        "with_phone": with_phone,
        "with_notes": with_notes,
        "marketing_consent_false": marketing_false,
        "dsgvo_compliant": marketing_false == total
    }


@api_router.post("/guests", tags=["Guests"])
async def create_guest(data: GuestCreate, user: dict = Depends(require_manager)):
    existing = await db.guests.find_one({"phone": data.phone, "archived": False})
    if existing:
        raise ConflictException("Gast mit dieser Telefonnummer existiert bereits")
    
    guest = create_entity(data.model_dump(exclude_none=True))
    # Sprint: Newsletter standardmäßig aktiviert
    if "newsletter_subscribed" not in guest:
        guest["newsletter_subscribed"] = True
    await db.guests.insert_one(guest)
    await create_audit_log(user, "guest", guest["id"], "create", None, safe_dict_for_audit(guest))
    
    return {k: v for k, v in guest.items() if k != "_id"}

@api_router.patch("/guests/{guest_id}", tags=["Guests"])
async def update_guest(guest_id: str, data: GuestUpdate, user: dict = Depends(require_manager)):
    existing = await db.guests.find_one({"id": guest_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Gast")
    
    before = safe_dict_for_audit(existing)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now_iso()
    
    await db.guests.update_one({"id": guest_id}, {"$set": update_data})
    
    updated = await db.guests.find_one({"id": guest_id}, {"_id": 0})
    await create_audit_log(user, "guest", guest_id, "update", before, safe_dict_for_audit(updated))
    return updated


# ============== PUBLIC BOOKING (Widget) ==============
@public_router.get("/availability", tags=["Public"])
async def check_availability(
    date: str,
    party_size: int = Query(..., ge=1, le=20)
):
    """Public endpoint to check availability for widget"""
    # Check opening hours
    hours = await check_opening_hours(date, "12:00")
    if not hours.get("open"):
        return {"available": False, "message": hours.get("message", "Geschlossen"), "slots": []}
    
    # Get available time slots
    open_time = hours.get("open_time", "11:00")
    close_time = hours.get("close_time", "22:00")
    
    # Generate time slots (every 30 minutes)
    slots = []
    current = datetime.strptime(open_time, "%H:%M")
    end = datetime.strptime(close_time, "%H:%M") - timedelta(hours=1)  # Last booking 1h before close
    
    while current <= end:
        time_str = current.strftime("%H:%M")
        capacity = await check_capacity(date, time_str, party_size)
        slots.append({
            "time": time_str,
            "available": capacity["available"],
            "available_seats": capacity["available_seats"]
        })
        current += timedelta(minutes=30)
    
    available_slots = [s for s in slots if s["available"]]
    
    return {
        "date": date,
        "party_size": party_size,
        "available": len(available_slots) > 0,
        "slots": slots,
        "open_time": open_time,
        "close_time": close_time
    }

@public_router.post("/book", tags=["Public"])
async def public_booking(data: PublicBookingCreate, background_tasks: BackgroundTasks):
    """Public endpoint for online reservations (widget)"""
    # Check opening hours
    hours = await check_opening_hours(data.date, data.time)
    if not hours.get("open"):
        raise ValidationException(hours.get("message", "Geschlossen zu dieser Zeit"))
    
    # Check capacity
    capacity = await check_capacity(data.date, data.time, data.party_size)
    if not capacity["available"]:
        # Create waitlist entry instead
        waitlist_entry = create_entity({
            "guest_name": data.guest_name,
            "guest_phone": data.guest_phone,
            "guest_email": data.guest_email,
            "party_size": data.party_size,
            "date": data.date,
            "preferred_time": data.time,
            "notes": data.notes,
            "language": data.language or "de",
            "priority": 1
        }, {"status": "offen"})
        
        await db.waitlist.insert_one(waitlist_entry)
        await create_audit_log(SYSTEM_ACTOR, "waitlist", waitlist_entry["id"], "create", None, safe_dict_for_audit(waitlist_entry))
        
        return {
            "success": True,
            "waitlist": True,
            "message": "Leider ausgebucht. Sie wurden auf die Warteliste gesetzt.",
            "waitlist_id": waitlist_entry["id"]
        }
    
    # Check guest blacklist
    guest = await get_guest_by_phone(data.guest_phone)
    if guest and guest.get("flag") == "blacklist":
        raise ValidationException("Reservierung nicht möglich. Bitte kontaktieren Sie uns telefonisch.")
    
    # Create reservation
    reservation = create_entity({
        "guest_name": data.guest_name,
        "guest_phone": data.guest_phone,
        "guest_email": data.guest_email,
        "party_size": data.party_size,
        "date": data.date,
        "time": data.time,
        "occasion": data.occasion,
        "notes": data.notes,
        "source": "widget",
        "language": data.language or "de"
    }, {"status": "neu", "reminder_sent": False})
    
    await db.reservations.insert_one(reservation)
    await create_audit_log(SYSTEM_ACTOR, "reservation", reservation["id"], "create", None, safe_dict_for_audit(reservation))
    
    # Send confirmation email
    background_tasks.add_task(send_confirmation_email, reservation, None, data.language or "de")
    
    return {
        "success": True,
        "waitlist": False,
        "message": "Reservierung erfolgreich",
        "reservation_id": reservation["id"]
    }

@public_router.post("/reservations/{reservation_id}/cancel", tags=["Public"])
async def cancel_reservation_public(reservation_id: str, token: str, background_tasks: BackgroundTasks):
    """Public cancellation via email link"""
    if not verify_cancel_token(reservation_id, token):
        raise ForbiddenException("Ungültiger Stornierungslink")
    
    existing = await db.reservations.find_one({"id": reservation_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Reservierung")
    
    if not ReservationStatus.can_cancel(existing.get("status")):
        raise ValidationException("Diese Reservierung kann nicht mehr storniert werden")
    
    before = safe_dict_for_audit(existing)
    await db.reservations.update_one({"id": reservation_id}, {"$set": {"status": "storniert", "updated_at": now_iso()}})
    await create_audit_log(SYSTEM_ACTOR, "reservation", reservation_id, "cancel_by_guest", before, {**before, "status": "storniert"})
    
    if existing.get("guest_email"):
        background_tasks.add_task(send_cancellation_email, existing, existing.get("language", "de"))
    
    return {"message": "Reservierung erfolgreich storniert", "success": True}


# ============== OPENING HOURS ==============
@api_router.get("/opening-hours", tags=["Settings"])
async def get_opening_hours(user: dict = Depends(get_current_user)):
    hours = await db.opening_hours.find({}, {"_id": 0}).sort("day_of_week", 1).to_list(7)
    return hours

@api_router.post("/opening-hours", tags=["Settings"])
async def set_opening_hours(data: OpeningHoursCreate, user: dict = Depends(require_admin)):
    existing = await db.opening_hours.find_one({"day_of_week": data.day_of_week}, {"_id": 0})
    
    if existing:
        before = safe_dict_for_audit(existing)
        await db.opening_hours.update_one(
            {"day_of_week": data.day_of_week},
            {"$set": {**data.model_dump(), "updated_at": now_iso()}}
        )
        updated = await db.opening_hours.find_one({"day_of_week": data.day_of_week}, {"_id": 0})
        await create_audit_log(user, "opening_hours", str(data.day_of_week), "update", before, safe_dict_for_audit(updated))
        return updated
    else:
        hours = create_entity(data.model_dump())
        await db.opening_hours.insert_one(hours)
        await create_audit_log(user, "opening_hours", str(data.day_of_week), "create", None, safe_dict_for_audit(hours))
        return {k: v for k, v in hours.items() if k != "_id"}


# ============== EMAIL TEMPLATES ==============
@api_router.get("/email-templates", tags=["Settings"])
async def get_email_templates_endpoint(user: dict = Depends(require_admin)):
    templates = await db.email_templates.find({}, {"_id": 0}).to_list(100)
    if not templates:
        # Return default templates
        return get_email_templates()
    return templates

@api_router.post("/email-templates", tags=["Settings"])
async def update_email_template(data: EmailTemplateUpdate, user: dict = Depends(require_admin)):
    key = f"{data.template_type}_{data.language}"
    existing = await db.email_templates.find_one({"key": key}, {"_id": 0})
    
    template_data = {
        "key": key,
        "template_type": data.template_type,
        "language": data.language,
        "subject": data.subject,
        "body_html": data.body_html,
        "body_text": data.body_text,
        "updated_at": now_iso()
    }
    
    if existing:
        before = safe_dict_for_audit(existing)
        await db.email_templates.update_one({"key": key}, {"$set": template_data})
        await create_audit_log(user, "email_template", key, "update", before, safe_dict_for_audit(template_data))
    else:
        template_data["id"] = str(uuid.uuid4())
        template_data["created_at"] = now_iso()
        await db.email_templates.insert_one(template_data)
        await create_audit_log(user, "email_template", key, "create", None, safe_dict_for_audit(template_data))
    
    return template_data


# ============== EMAIL LOG ==============
@api_router.get("/email-logs", tags=["Admin"])
async def get_email_logs(
    limit: int = 100,
    status: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    query = {}
    if status:
        query["status"] = status
    
    logs = await db.email_logs.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    return logs


# ============== SMTP CONFIGURATION ==============
@api_router.get("/smtp/status", tags=["Admin"])
async def get_smtp_status_endpoint(user: dict = Depends(require_admin)):
    """Get SMTP configuration status (without exposing secrets)"""
    return get_smtp_status()


@api_router.post("/smtp/test", tags=["Admin"])
async def send_test_email_endpoint(
    to_email: EmailStr,
    user: dict = Depends(require_admin)
):
    """Send a test email to verify SMTP configuration"""
    result = await send_test_email(to_email)
    
    # Audit log
    await create_audit_log(
        actor=user,
        entity="smtp",
        entity_id="test",
        action="test_email",
        after={"recipient": to_email, "success": result["success"]}
    )
    
    return result


# ============== DATA IMPORT (Sprint: Data Onboarding) ==============
class StaffImportRequest(BaseModel):
    data: str
    format: str = "json"
    override: bool = False


@api_router.post("/staff/import", tags=["Admin"])
async def import_staff_endpoint(
    request: StaffImportRequest,
    user: dict = Depends(require_admin)
):
    """
    Import staff members from JSON or CSV
    
    - format: "json" or "csv"
    - override: If true, update existing fields even if not empty
    - data: JSON array or CSV text
    """
    if not request.data:
        raise HTTPException(status_code=400, detail="Keine Daten übermittelt")
    
    if request.format.lower() == "csv":
        result = await import_staff_from_csv(request.data, request.override)
    else:
        try:
            json_data = json.loads(request.data)
            if not isinstance(json_data, list):
                json_data = [json_data]
            result = await import_staff_from_json(json_data, request.override)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Ungültiges JSON: {str(e)}")
    
    # Audit log
    await create_audit_log(
        actor=user,
        entity="staff_import",
        entity_id="batch",
        action="import",
        after={"created": result["created"], "updated": result["updated"], "skipped": result["skipped"]}
    )
    
    return result


@api_router.post("/import/carlsburg", tags=["Admin"])
async def import_carlsburg_endpoint(
    mode: str = "dry_run",
    user: dict = Depends(require_admin)
):
    """
    Import content from carlsburg.de (predefined data)
    
    - mode: "dry_run" (preview only) or "apply" (actually import)
    """
    if mode not in ["dry_run", "apply"]:
        raise HTTPException(status_code=400, detail="Mode must be 'dry_run' or 'apply'")
    
    result = await import_predefined_carlsburg_data(mode)
    
    if mode == "apply":
        # Audit log
        await create_audit_log(
            actor=user,
            entity="carlsburg_import",
            entity_id="batch",
            action="import",
            after={
                "veranstaltungen": result["veranstaltungen"],
                "aktionen": result["aktionen"]
            }
        )
    
    return result


# ============== PDF EXPORT ==============
@api_router.get("/export/table-plan", tags=["Export"])
async def export_table_plan(
    date: str,
    area_id: Optional[str] = None,
    user: dict = Depends(require_manager)
):
    """Generate PDF table plan for a specific date"""
    # Get reservations
    query = {"date": date, "archived": False, "status": {"$in": ["neu", "bestaetigt", "angekommen"]}}
    if area_id:
        query["area_id"] = area_id
    
    reservations = await db.reservations.find(query, {"_id": 0}).sort("time", 1).to_list(500)
    
    # Get areas
    areas = await db.areas.find({"archived": False}, {"_id": 0}).to_list(100)
    area_map = {a["id"]: a["name"] for a in areas}
    
    # Get restaurant name from settings
    restaurant_name = "Carlsburg Restaurant"
    name_setting = await db.settings.find_one({"key": "restaurant_name"})
    if name_setting:
        restaurant_name = name_setting.get("value", restaurant_name)
    
    # Generate PDF
    pdf_buffer = generate_table_plan_pdf(reservations, area_map, date, restaurant_name, area_id)
    
    filename = f"tischplan_{date}"
    if area_id and area_id in area_map:
        filename += f"_{area_map[area_id].replace(' ', '_')}"
    filename += ".pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============== SETTINGS ENDPOINTS ==============
@api_router.get("/settings", tags=["Settings"])
async def get_settings_endpoint(user: dict = Depends(require_admin)):
    settings_list = await db.settings.find({}, {"_id": 0}).to_list(1000)
    return settings_list

@api_router.post("/settings", tags=["Settings"])
async def create_or_update_setting(data: SettingCreate, user: dict = Depends(require_admin)):
    existing = await db.settings.find_one({"key": data.key}, {"_id": 0})
    
    if existing:
        before = safe_dict_for_audit(existing)
        await db.settings.update_one({"key": data.key}, {"$set": {"value": data.value, "description": data.description, "updated_at": now_iso()}})
        updated = await db.settings.find_one({"key": data.key}, {"_id": 0})
        await create_audit_log(user, "setting", data.key, "update", before, safe_dict_for_audit(updated))
        return updated
    else:
        setting = create_entity(data.model_dump())
        setting["key"] = data.key  # Ensure key is set
        await db.settings.insert_one(setting)
        await create_audit_log(user, "setting", data.key, "create", None, safe_dict_for_audit(setting))
        return {k: v for k, v in setting.items() if k != "_id"}


# ============== AUDIT LOG ==============
@api_router.get("/audit-logs", tags=["Audit"])
async def get_audit_logs(
    entity: Optional[str] = None,
    entity_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(require_admin)
):
    query = {}
    if entity:
        query["entity"] = entity
    if entity_id:
        query["entity_id"] = entity_id
    if actor_id:
        query["actor_id"] = actor_id
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    return logs


# ============== REMINDERS ==============
@api_router.post("/reservations/send-reminders", tags=["Admin"])
async def send_reservation_reminders(background_tasks: BackgroundTasks, user: dict = Depends(require_admin)):
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    
    reservations = await db.reservations.find({
        "date": tomorrow,
        "status": {"$in": ["neu", "bestaetigt"]},
        "archived": False,
        "reminder_sent": {"$ne": True}
    }, {"_id": 0}).to_list(1000)
    
    sent_count = 0
    for res in reservations:
        if res.get("guest_email"):
            area_name = None
            if res.get("area_id"):
                area_doc = await db.areas.find_one({"id": res["area_id"]}, {"_id": 0})
                area_name = area_doc.get("name") if area_doc else None
            
            background_tasks.add_task(send_reminder_email, res, area_name, res.get("language", "de"))
            await db.reservations.update_one({"id": res["id"]}, {"$set": {"reminder_sent": True}})
            sent_count += 1
    
    return {"message": f"Erinnerungen gesendet: {sent_count}", "count": sent_count, "success": True}


# ============== SEED DATA ==============
@api_router.post("/seed", tags=["Admin"])
async def seed_data():
    existing_users = await db.users.count_documents({"archived": False})
    if existing_users > 0:
        return {"message": "Daten bereits vorhanden", "seeded": False}
    
    # Create users
    test_users = [
        {"email": "admin@gastrocore.de", "name": "Admin User", "role": "admin", "password": "Admin123!"},
        {"email": "schichtleiter@gastrocore.de", "name": "Schicht Leiter", "role": "schichtleiter", "password": "Schicht123!"},
        {"email": "mitarbeiter@gastrocore.de", "name": "Mit Arbeiter", "role": "mitarbeiter", "password": "Mitarbeiter123!"},
    ]
    
    for u in test_users:
        user_doc = {
            "id": str(uuid.uuid4()), "email": u["email"], "name": u["name"], "role": u["role"],
            "password_hash": hash_password(u["password"]), "is_active": True, "must_change_password": True,
            "created_at": now_iso(), "updated_at": now_iso(), "archived": False
        }
        await db.users.insert_one(user_doc)
    
    # Create areas
    test_areas = [
        {"name": "Terrasse", "description": "Außenbereich mit Sonnenschirmen", "capacity": 40, "table_count": 10},
        {"name": "Saal", "description": "Hauptspeiseraum", "capacity": 80, "table_count": 20},
        {"name": "Wintergarten", "description": "Verglaster Bereich", "capacity": 30, "table_count": 8},
        {"name": "Bar", "description": "Barhocker und Stehtische", "capacity": 20, "table_count": 5},
    ]
    
    area_ids = []
    for a in test_areas:
        area_doc = create_entity(a)
        await db.areas.insert_one(area_doc)
        area_ids.append(area_doc["id"])
    
    # Create opening hours
    for day in range(7):
        is_closed = day == 0  # Closed on Monday
        hours = {
            "id": str(uuid.uuid4()),
            "day_of_week": day,
            "open_time": "11:00",
            "close_time": "22:00",
            "is_closed": is_closed,
            "created_at": now_iso(),
            "updated_at": now_iso()
        }
        await db.opening_hours.insert_one(hours)
    
    # Create settings
    default_settings = [
        {"key": "restaurant_name", "value": "Carlsburg Restaurant", "description": "Restaurant name"},
        {"key": "max_total_capacity", "value": "150", "description": "Maximum total guests"},
        {"key": "no_show_greylist_threshold", "value": "2", "description": "No-shows before greylist"},
        {"key": "no_show_blacklist_threshold", "value": "4", "description": "No-shows before blacklist"},
    ]
    
    for s in default_settings:
        setting_doc = create_entity(s)
        setting_doc["key"] = s["key"]
        await db.settings.insert_one(setting_doc)
    
    # Create sample reservations
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    test_reservations = [
        {"guest_name": "Familie Müller", "guest_phone": "+49 170 1234567", "guest_email": "mueller@example.de", "party_size": 4, "date": today, "time": "12:00", "area_id": area_ids[1], "source": "widget", "occasion": "Geburtstag"},
        {"guest_name": "Hans Schmidt", "guest_phone": "+49 171 2345678", "party_size": 2, "date": today, "time": "13:00", "area_id": area_ids[0], "source": "intern"},
        {"guest_name": "Lisa Weber", "guest_phone": "+49 172 3456789", "guest_email": "lisa@example.de", "party_size": 6, "date": today, "time": "18:30", "area_id": area_ids[2], "source": "widget"},
        {"guest_name": "Peter Braun", "guest_phone": "+49 173 4567890", "party_size": 3, "date": today, "time": "19:00", "area_id": area_ids[1], "source": "walk-in", "table_number": "T5"},
        {"guest_name": "Maria Schwarz", "guest_phone": "+49 174 5678901", "guest_email": "maria@example.de", "party_size": 8, "date": today, "time": "20:00", "area_id": area_ids[1], "source": "intern", "occasion": "Hochzeitstag"},
    ]
    
    for r in test_reservations:
        res_doc = create_entity(r, {"status": "neu", "reminder_sent": False, "language": "de"})
        await db.reservations.insert_one(res_doc)
    
    return {
        "message": "Testdaten erstellt",
        "seeded": True,
        "users": [{"email": u["email"], "password": u["password"], "role": u["role"]} for u in test_users]
    }


# ============== HEALTH CHECK ==============
@api_router.get("/", tags=["Health"])
async def root():
    return {"message": "GastroCore API v2.0.0", "status": "running", "success": True}

@api_router.get("/health", tags=["Health"])
async def health_check():
    try:
        await client.admin.command('ping')
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return {"status": "healthy" if db_status == "connected" else "degraded", "database": db_status, "version": "3.0.0"}


@api_router.get("/version", tags=["Health"])
async def get_version():
    """
    Public endpoint for build identification and module status.
    No authentication required. Does not expose secrets.
    """
    import subprocess
    
    # Get git info (if available)
    commit_hash = None
    branch = None
    try:
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], 
            cwd=ROOT_DIR, 
            stderr=subprocess.DEVNULL
        ).decode().strip()
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], 
            cwd=ROOT_DIR, 
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        pass
    
    # Build ID from env or generate from git hash + timestamp
    build_id = os.environ.get("BUILD_ID")
    if not build_id:
        short_hash = commit_hash[:8] if commit_hash else "unknown"
        build_id = f"{short_hash}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    
    return {
        "build_id": build_id,
        "commit_hash": commit_hash,
        "branch": branch,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "health_version": "3.0.0",
        "modules": {
            "core": True,
            "reservations": True,
            "tables": True,  # Sprint: Tischplan & Belegung
            "events": True,
            "payments": True,
            "staff": True,
            "schedules": True,
            "taxoffice": True,
            "loyalty": True,
            "marketing": True,
            "ai": True
        }
    }


# ============== SPRINT 3: REMINDER & NO-SHOW SYSTEM ==============

# --- Pydantic Models for Sprint 3 ---
class ReminderRuleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    hours_before: int = Field(..., ge=1, le=168)  # 1h to 7 days
    channel: str = Field(..., pattern="^(email|whatsapp|both)$")
    is_active: bool = True
    template_key: Optional[str] = None  # e.g., "reminder_24h"

class GuestConfirmRequest(BaseModel):
    confirmed: bool = True

class MessageLogCreate(BaseModel):
    reservation_id: str
    channel: str  # email, whatsapp
    message_type: str  # confirmation, reminder, cancellation
    recipient: str
    status: str  # sent, failed, pending
    error_message: Optional[str] = None


# --- WhatsApp Deep-Link Generator ---
def generate_whatsapp_link(phone: str, message: str) -> str:
    """Generate WhatsApp deep-link with pre-filled message"""
    import urllib.parse
    # Clean phone number (remove spaces, dashes, etc.)
    clean_phone = ''.join(filter(str.isdigit, phone))
    # Ensure country code (default to Germany +49)
    if not clean_phone.startswith('49') and not clean_phone.startswith('+'):
        if clean_phone.startswith('0'):
            clean_phone = '49' + clean_phone[1:]
        else:
            clean_phone = '49' + clean_phone
    encoded_message = urllib.parse.quote(message)
    return f"https://wa.me/{clean_phone}?text={encoded_message}"


def get_reminder_message(reservation: dict, language: str = "de") -> str:
    """Generate reminder message text for WhatsApp"""
    messages = {
        "de": f"""Erinnerung: Ihre Reservierung

📅 {reservation.get('date', '')}
⏰ {reservation.get('time', '')} Uhr
👥 {reservation.get('party_size', '')} Personen

Bei Verhinderung bitten wir um rechtzeitige Absage.

Ihr Restaurant-Team""",
        "en": f"""Reminder: Your reservation

📅 {reservation.get('date', '')}
⏰ {reservation.get('time', '')}
👥 {reservation.get('party_size', '')} guests

Please let us know if you cannot make it.

Your Restaurant Team""",
        "pl": f"""Przypomnienie: Twoja rezerwacja

📅 {reservation.get('date', '')}
⏰ {reservation.get('time', '')}
👥 {reservation.get('party_size', '')} osób

Prosimy o anulowanie w przypadku niemożności przybycia.

Zespół Restauracji"""
    }
    return messages.get(language, messages["de"])


# --- Message Log Helper ---
async def log_message(reservation_id: str, channel: str, message_type: str, 
                       recipient: str, status: str, error_message: str = None):
    """Log sent messages for audit purposes"""
    log_entry = {
        "id": str(uuid.uuid4()),
        "reservation_id": reservation_id,
        "channel": channel,
        "message_type": message_type,
        "recipient": recipient,
        "status": status,
        "error_message": error_message,
        "timestamp": now_iso()
    }
    await db.message_logs.insert_one(log_entry)
    return log_entry


# --- Confirmation Token ---
def generate_confirm_token(reservation_id: str) -> str:
    """Generate secure confirmation token"""
    message = f"confirm:{reservation_id}:{CANCEL_SECRET}"
    return hashlib.sha256(message.encode()).hexdigest()[:32]


def verify_confirm_token(reservation_id: str, token: str) -> bool:
    """Verify confirmation token"""
    expected = generate_confirm_token(reservation_id)
    return hmac.compare_digest(expected, token)


def get_confirm_url(reservation_id: str) -> str:
    """Generate confirmation URL"""
    token = generate_confirm_token(reservation_id)
    return f"{APP_URL}/confirm/{reservation_id}?token={token}"


# Import for token generation
from email_service import generate_cancel_token, get_cancel_url
import hashlib
import hmac
CANCEL_SECRET = os.environ.get('JWT_SECRET', 'secret-key')
APP_URL = os.environ.get('APP_URL', 'http://localhost:3000')


# --- Reminder Rules Endpoints ---
@api_router.get("/reminder-rules", tags=["Reminders"])
async def get_reminder_rules(user: dict = Depends(require_admin)):
    """Get all reminder rules"""
    rules = await db.reminder_rules.find({"archived": False}, {"_id": 0}).to_list(100)
    return rules


@api_router.post("/reminder-rules", tags=["Reminders"])
async def create_reminder_rule(data: ReminderRuleCreate, user: dict = Depends(require_admin)):
    """Create a new reminder rule"""
    rule = create_entity(data.model_dump())
    await db.reminder_rules.insert_one(rule)
    await create_audit_log(user, "reminder_rule", rule["id"], "create", None, safe_dict_for_audit(rule))
    return {k: v for k, v in rule.items() if k != "_id"}


@api_router.patch("/reminder-rules/{rule_id}", tags=["Reminders"])
async def update_reminder_rule(rule_id: str, data: ReminderRuleCreate, user: dict = Depends(require_admin)):
    """Update a reminder rule"""
    existing = await db.reminder_rules.find_one({"id": rule_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Reminder-Regel")
    
    before = safe_dict_for_audit(existing)
    update_data = {**data.model_dump(), "updated_at": now_iso()}
    await db.reminder_rules.update_one({"id": rule_id}, {"$set": update_data})
    
    updated = await db.reminder_rules.find_one({"id": rule_id}, {"_id": 0})
    await create_audit_log(user, "reminder_rule", rule_id, "update", before, safe_dict_for_audit(updated))
    return updated


@api_router.delete("/reminder-rules/{rule_id}", tags=["Reminders"])
async def delete_reminder_rule(rule_id: str, user: dict = Depends(require_admin)):
    """Archive a reminder rule"""
    existing = await db.reminder_rules.find_one({"id": rule_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Reminder-Regel")
    
    before = safe_dict_for_audit(existing)
    await db.reminder_rules.update_one({"id": rule_id}, {"$set": {"archived": True, "updated_at": now_iso()}})
    await create_audit_log(user, "reminder_rule", rule_id, "archive", before, {**before, "archived": True})
    return {"message": "Reminder-Regel archiviert", "success": True}


# --- WhatsApp Reminder Endpoint ---
@api_router.post("/reservations/{reservation_id}/whatsapp-reminder", tags=["Reminders"])
async def get_whatsapp_reminder_link(reservation_id: str, user: dict = Depends(require_manager)):
    """Generate WhatsApp reminder link for a reservation"""
    reservation = await db.reservations.find_one({"id": reservation_id, "archived": False}, {"_id": 0})
    if not reservation:
        raise NotFoundException("Reservierung")
    
    if not reservation.get("guest_phone"):
        raise ValidationException("Keine Telefonnummer hinterlegt")
    
    language = reservation.get("language", "de")
    message = get_reminder_message(reservation, language)
    whatsapp_link = generate_whatsapp_link(reservation["guest_phone"], message)
    
    # Log the action
    await log_message(
        reservation_id=reservation_id,
        channel="whatsapp",
        message_type="reminder",
        recipient=reservation["guest_phone"],
        status="link_generated"
    )
    
    return {
        "whatsapp_link": whatsapp_link,
        "phone": reservation["guest_phone"],
        "message": message,
        "success": True
    }


# --- Smart Reminder Processing ---
@api_router.post("/reminders/process", tags=["Reminders"])
async def process_reminders(background_tasks: BackgroundTasks, user: dict = Depends(require_admin)):
    """Process all due reminders based on configured rules"""
    now = datetime.now(timezone.utc)
    
    # Get active reminder rules
    rules = await db.reminder_rules.find({"is_active": True, "archived": False}, {"_id": 0}).to_list(100)
    if not rules:
        return {"message": "Keine aktiven Reminder-Regeln", "processed": 0}
    
    processed = 0
    for rule in rules:
        hours_before = rule.get("hours_before", 24)
        channel = rule.get("channel", "email")
        
        # Calculate target datetime
        target_time = now + timedelta(hours=hours_before)
        target_date = target_time.strftime("%Y-%m-%d")
        target_hour = target_time.strftime("%H")
        
        # Find reservations that need reminders
        reminder_key = f"reminder_{hours_before}h_sent"
        query = {
            "date": target_date,
            "status": "bestaetigt",  # Only confirmed reservations
            "archived": False,
            reminder_key: {"$ne": True}
        }
        
        reservations = await db.reservations.find(query, {"_id": 0}).to_list(500)
        
        for res in reservations:
            # Check if reservation time matches (within the hour)
            res_hour = res.get("time", "00:00").split(":")[0]
            if res_hour == target_hour or hours_before >= 24:  # For 24h+ reminders, send for all
                
                if channel in ["email", "both"] and res.get("guest_email"):
                    area_name = None
                    if res.get("area_id"):
                        area_doc = await db.areas.find_one({"id": res["area_id"]}, {"_id": 0})
                        area_name = area_doc.get("name") if area_doc else None
                    
                    background_tasks.add_task(send_reminder_email, res, area_name, res.get("language", "de"))
                    await log_message(res["id"], "email", "reminder", res["guest_email"], "sent")
                
                # Mark as sent
                await db.reservations.update_one(
                    {"id": res["id"]}, 
                    {"$set": {reminder_key: True, "updated_at": now_iso()}}
                )
                processed += 1
    
    return {"message": f"Reminders verarbeitet: {processed}", "processed": processed, "success": True}


# --- Guest Confirmation Endpoints ---
@public_router.get("/reservations/{reservation_id}/confirm-info", tags=["Public"])
async def get_confirmation_info(reservation_id: str, token: str):
    """Get reservation info for confirmation page"""
    if not verify_confirm_token(reservation_id, token):
        raise ForbiddenException("Ungültiger Bestätigungslink")
    
    reservation = await db.reservations.find_one({"id": reservation_id, "archived": False}, {"_id": 0})
    if not reservation:
        raise NotFoundException("Reservierung")
    
    # Get area name
    area_name = None
    if reservation.get("area_id"):
        area_doc = await db.areas.find_one({"id": reservation["area_id"]}, {"_id": 0})
        area_name = area_doc.get("name") if area_doc else None
    
    return {
        "id": reservation["id"],
        "guest_name": reservation.get("guest_name"),
        "date": reservation.get("date"),
        "time": reservation.get("time"),
        "party_size": reservation.get("party_size"),
        "area_name": area_name,
        "status": reservation.get("status"),
        "guest_confirmed": reservation.get("guest_confirmed", False)
    }


@public_router.post("/reservations/{reservation_id}/confirm", tags=["Public"])
async def confirm_reservation_by_guest(reservation_id: str, token: str):
    """Guest confirms their reservation via email link"""
    if not verify_confirm_token(reservation_id, token):
        raise ForbiddenException("Ungültiger Bestätigungslink")
    
    reservation = await db.reservations.find_one({"id": reservation_id, "archived": False}, {"_id": 0})
    if not reservation:
        raise NotFoundException("Reservierung")
    
    if reservation.get("status") not in ["neu", "bestaetigt"]:
        raise ValidationException("Diese Reservierung kann nicht mehr bestätigt werden")
    
    before = safe_dict_for_audit(reservation)
    await db.reservations.update_one(
        {"id": reservation_id}, 
        {"$set": {"guest_confirmed": True, "status": "bestaetigt", "updated_at": now_iso()}}
    )
    
    await create_audit_log(SYSTEM_ACTOR, "reservation", reservation_id, "guest_confirm", before, 
                           {**before, "guest_confirmed": True, "status": "bestaetigt"})
    
    return {"message": "Reservierung erfolgreich bestätigt", "success": True}


# --- Cancellation Deadline Check ---
async def check_cancellation_allowed(reservation: dict) -> dict:
    """Check if cancellation is still allowed based on configured deadline"""
    # Get cancellation deadline from settings (default: 24 hours)
    deadline_setting = await db.settings.find_one({"key": "cancellation_deadline_hours"})
    deadline_hours = int(deadline_setting.get("value", 24)) if deadline_setting else 24
    
    # Parse reservation datetime
    try:
        res_date = reservation.get("date", "")
        res_time = reservation.get("time", "12:00")
        res_datetime = datetime.strptime(f"{res_date} {res_time}", "%Y-%m-%d %H:%M")
        res_datetime = res_datetime.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        deadline = res_datetime - timedelta(hours=deadline_hours)
        
        return {
            "allowed": now < deadline,
            "deadline": deadline.isoformat(),
            "deadline_hours": deadline_hours,
            "message": f"Stornierung bis {deadline_hours}h vorher möglich" if now < deadline 
                       else f"Stornierungsfrist ({deadline_hours}h vorher) abgelaufen"
        }
    except Exception:
        return {"allowed": True, "message": "Stornierung möglich"}


# --- Enhanced Public Cancellation ---
@public_router.get("/reservations/{reservation_id}/cancel-info", tags=["Public"])
async def get_cancellation_info(reservation_id: str, token: str):
    """Get reservation info and check if cancellation is allowed"""
    if not verify_cancel_token(reservation_id, token):
        raise ForbiddenException("Ungültiger Stornierungslink")
    
    reservation = await db.reservations.find_one({"id": reservation_id, "archived": False}, {"_id": 0})
    if not reservation:
        raise NotFoundException("Reservierung")
    
    cancellation_check = await check_cancellation_allowed(reservation)
    
    return {
        "id": reservation["id"],
        "guest_name": reservation.get("guest_name"),
        "date": reservation.get("date"),
        "time": reservation.get("time"),
        "party_size": reservation.get("party_size"),
        "status": reservation.get("status"),
        "cancellation_allowed": cancellation_check["allowed"],
        "cancellation_message": cancellation_check["message"],
        "deadline_hours": cancellation_check.get("deadline_hours")
    }


# --- Message Log Endpoint ---
@api_router.get("/message-logs", tags=["Admin"])
async def get_message_logs(
    reservation_id: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(require_admin)
):
    """Get message log entries"""
    query = {}
    if reservation_id:
        query["reservation_id"] = reservation_id
    if channel:
        query["channel"] = channel
    
    logs = await db.message_logs.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    return logs


# --- Guest Info with No-Show History ---
@api_router.get("/guests/{guest_id}/history", tags=["Guests"])
async def get_guest_history(guest_id: str, user: dict = Depends(require_manager)):
    """Get guest with full no-show history"""
    guest = await db.guests.find_one({"id": guest_id, "archived": False}, {"_id": 0})
    if not guest:
        raise NotFoundException("Gast")
    
    # Get all reservations for this guest
    reservations = await db.reservations.find({
        "guest_phone": guest.get("phone"),
        "archived": False
    }, {"_id": 0}).sort("date", -1).to_list(100)
    
    # Filter no-shows
    no_shows = [r for r in reservations if r.get("status") == "no_show"]
    
    return {
        **guest,
        "reservation_count": len(reservations),
        "no_show_history": no_shows,
        "recent_reservations": reservations[:10]
    }


# --- Check Guest Status for New Reservations ---
@api_router.get("/guests/check/{phone}", tags=["Guests"])
async def check_guest_status(phone: str, user: dict = Depends(require_manager)):
    """Check guest status by phone (for reservation creation)"""
    guest = await get_guest_by_phone(phone)
    
    if not guest:
        return {
            "found": False,
            "flag": "none",
            "no_show_count": 0,
            "message": "Neuer Gast"
        }
    
    flag = guest.get("flag", "none")
    no_show_count = guest.get("no_show_count", 0)
    
    messages = {
        "none": "Gast in Ordnung",
        "greylist": f"⚠️ Greylist: {no_show_count} No-Shows - Bestätigungspflicht empfohlen",
        "blacklist": f"🚫 Blacklist: {no_show_count} No-Shows - Online-Reservierung blockiert"
    }
    
    return {
        "found": True,
        "guest_id": guest.get("id"),
        "flag": flag,
        "no_show_count": no_show_count,
        "message": messages.get(flag, "Unbekannter Status"),
        "requires_confirmation": flag in ["greylist", "blacklist"]
    }


# --- Default Settings Initializer ---
async def init_default_settings():
    """Initialize default settings if not present"""
    defaults = [
        {"key": "no_show_greylist_threshold", "value": "2", "description": "No-Shows bis Greylist"},
        {"key": "no_show_blacklist_threshold", "value": "4", "description": "No-Shows bis Blacklist"},
        {"key": "cancellation_deadline_hours", "value": "24", "description": "Stornierungsfrist in Stunden"},
        {"key": "require_guest_confirmation", "value": "false", "description": "Gast-Bestätigung erforderlich"},
        {"key": "greylist_requires_confirmation", "value": "true", "description": "Greylist-Gäste müssen bestätigen"},
        {"key": "restaurant_name", "value": "Carlsburg Restaurant", "description": "Restaurant-Name"},
    ]
    
    for setting in defaults:
        existing = await db.settings.find_one({"key": setting["key"]})
        if not existing:
            await db.settings.insert_one({
                "id": str(uuid.uuid4()),
                **setting,
                "created_at": now_iso(),
                "updated_at": now_iso()
            })


# Initialize default reminder rules
async def init_default_reminder_rules():
    """Initialize default reminder rules if not present"""
    existing = await db.reminder_rules.count_documents({"archived": False})
    if existing == 0:
        defaults = [
            {"name": "24h Erinnerung", "hours_before": 24, "channel": "email", "is_active": True},
            {"name": "3h Erinnerung", "hours_before": 3, "channel": "whatsapp", "is_active": True},
        ]
        for rule in defaults:
            await db.reminder_rules.insert_one({
                "id": str(uuid.uuid4()),
                **rule,
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "archived": False
            })


# ============== APP CONFIG ==============

# Import Events Module (Sprint 4 - ADDITIV)
from events_module import events_router, public_events_router, seed_events

# Import Payment Module (Sprint 4 - Zahlungen)
from payment_module import payment_router, payment_webhook_router, seed_payment_rules

# Import Staff Module (Sprint 5 - Mitarbeiter & Dienstplan)
from staff_module import staff_router, seed_work_areas, seed_sample_staff

# Import Tax Office Module (Sprint 6 - Steuerbüro Exporte)
from taxoffice_module import taxoffice_router

# Import Loyalty Module (Sprint 7 - Kunden-App & Punkte-System)
from loyalty_module import loyalty_router, customer_router

# Import Marketing Module (Sprint 8 - Newsletter & Social Automation)
from marketing_module import marketing_router, marketing_public_router

# Import AI Assistant Module (Sprint 9 - KI-Assistenz)
from ai_assistant import ai_router

# Import Backup Module (Sprint: Admin Backup/Export)
from backup_module import backup_router

# Import Table Import & Seed Module
from table_import_module import import_router

# ============== FIRST-RUN SEED SYSTEM (Sprint 11) ==============
from seed_system import run_full_seed, verify_seed, bootstrap_admin_on_startup

# Internal seed endpoint (no auth required for first-run)
internal_router = APIRouter(prefix="/internal", tags=["Internal"])

@internal_router.post("/seed")
async def seed_endpoint(force: bool = False):
    """
    FIRST-RUN SEED ENDPOINT
    
    Initialisiert das System mit Stammdaten für einen frischen Clone.
    Idempotent: Kann mehrfach ausgeführt werden ohne Duplikate.
    
    Query Params:
    - force: bool (default: false) - Seed auch wenn Daten existieren
    
    Sicherheit:
    - Nur ausführen wenn DB leer ODER force=true
    - Produktivdaten werden nie überschrieben
    """
    force_env = os.environ.get("FORCE_SEED", "false").lower() == "true"
    return await run_full_seed(force=force or force_env)

@internal_router.get("/seed/verify")
async def verify_seed_endpoint():
    """
    Prüft ob Seed erfolgreich war und System testfähig ist.
    """
    return await verify_seed()

@internal_router.get("/seed/status")
async def seed_status_endpoint():
    """
    Zeigt aktuellen Datenbank-Status für Seed-Entscheidung.
    """
    return {
        "users": await db.users.count_documents({"archived": False}),
        "areas": await db.areas.count_documents({"archived": False}),
        "opening_hours": await db.opening_hours.count_documents({}),
        "events": await db.events.count_documents({"archived": False}),
        "staff_members": await db.staff_members.count_documents({"archived": False}),
        "rewards": await db.rewards.count_documents({"archived": False}),
        "payment_rules": await db.payment_rules.count_documents({"archived": False}),
        "recommendation": "SEED_REQUIRED" if await db.users.count_documents({}) == 0 else "DATA_EXISTS"
    }

# Legacy seed endpoints (require admin, for partial re-seeding)
@api_router.post("/seed-events", tags=["Admin"])
async def seed_events_endpoint(user: dict = Depends(require_admin)):
    """Seed sample events (Kabarett + Gänseabend)"""
    return await seed_events()

@api_router.post("/seed-payment-rules", tags=["Admin"])
async def seed_payment_rules_endpoint(user: dict = Depends(require_admin)):
    """Seed default payment rules"""
    return await seed_payment_rules()

@api_router.post("/seed-staff", tags=["Admin"])
async def seed_staff_endpoint(user: dict = Depends(require_admin)):
    """Seed work areas and sample staff"""
    areas_result = await seed_work_areas()
    staff_result = await seed_sample_staff()
    return {
        "work_areas": areas_result,
        "staff": staff_result
    }

app.include_router(api_router)
app.include_router(public_router)
app.include_router(internal_router)  # First-Run Seed System
app.include_router(events_router)
app.include_router(public_events_router)
app.include_router(payment_router)
app.include_router(payment_webhook_router)
app.include_router(staff_router)
app.include_router(taxoffice_router)
app.include_router(loyalty_router)
app.include_router(customer_router)
app.include_router(marketing_router)
app.include_router(marketing_public_router)
app.include_router(ai_router)
app.include_router(reservation_config_router, prefix="/api")  # Sprint: Reservierung Live-Ready
# System Settings & Opening Hours Master Module
app.include_router(system_settings_router, prefix="/api")
app.include_router(opening_hours_router, prefix="/api")
# Reservation Slots Module (Sprint: Slots & Durchgänge)
app.include_router(slots_router, prefix="/api")
# Table Module (Sprint: Tischplan & Belegung)
app.include_router(table_router, prefix="/api")
app.include_router(combination_router, prefix="/api")
# Backup Module (Sprint: Admin Backup/Export)
app.include_router(backup_router)
# Table Import & Seed Router
app.include_router(import_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.CORS_ORIGINS.split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    """Initialize default settings, rules, and ensure admin exists on startup"""
    # ADMIN-BOOTSTRAP: Sicherstellen, dass immer ein Admin existiert
    admin_ready = await bootstrap_admin_on_startup()
    if not admin_ready:
        logger.warning("⚠ Admin-Bootstrap fehlgeschlagen - manueller Seed empfohlen")
    
    await init_default_settings()
    await init_default_reminder_rules()
    
    # WordPress Sync Scheduler starten
    import asyncio
    asyncio.create_task(wordpress_sync_scheduler())
    
    logger.info("GastroCore v7.0.0 started - Events + Payment + Staff + TaxOffice + Loyalty Module enabled")


# ============== WORDPRESS SYNC SCHEDULER ==============
async def wordpress_sync_scheduler():
    """
    Hintergrund-Scheduler für WordPress Event Sync.
    Läuft alle 60 Minuten automatisch.
    """
    import asyncio
    from pathlib import Path
    
    SYNC_INTERVAL_SECONDS = 3600  # 60 Minuten
    LOCK_FILE = Path("/tmp/wp_sync.lock")
    INITIAL_DELAY = 120  # 2 Minuten nach Start warten
    
    logger.info(f"[WP-SYNC] Scheduler gestartet (Intervall: {SYNC_INTERVAL_SECONDS}s)")
    
    # Initiale Verzögerung damit alle Services hochgefahren sind
    await asyncio.sleep(INITIAL_DELAY)
    logger.info("[WP-SYNC] Initiale Verzögerung abgeschlossen, starte Sync-Loop")
    
    while True:
        try:
            # Lock prüfen
            if LOCK_FILE.exists():
                try:
                    lock_age = (datetime.now(timezone.utc) - 
                               datetime.fromtimestamp(LOCK_FILE.stat().st_mtime, tz=timezone.utc)).total_seconds()
                    if lock_age > 3600:
                        logger.warning(f"[WP-SYNC] Veralteter Lock gefunden ({lock_age:.0f}s), entferne...")
                        LOCK_FILE.unlink()
                    else:
                        logger.info("[WP-SYNC] Sync übersprungen (Lock aktiv)")
                        await asyncio.sleep(SYNC_INTERVAL_SECONDS)
                        continue
                except Exception:
                    pass
            
            # Lock setzen
            LOCK_FILE.write_text(f"scheduler:{datetime.now(timezone.utc).isoformat()}")
            
            try:
                logger.info("[WP-SYNC] Starte automatischen Sync...")
                
                # Sync direkt ausführen (Funktion aus events_module)
                from events_module import (
                    fetch_wordpress_events, map_wordpress_event_to_gastrocore,
                    has_real_changes, SYNC_SOURCE, WORDPRESS_EVENTS_API
                )
                import time
                
                start_time = time.time()
                
                report = {
                    "fetched": 0, "created": 0, "updated": 0, 
                    "unchanged": 0, "archived": 0, "skipped": 0, "errors": []
                }
                
                # Events holen
                wp_events = await fetch_wordpress_events()
                report["fetched"] = len(wp_events)
                
                seen_external_ids = set()
                
                for wp_event in wp_events:
                    try:
                        mapped = map_wordpress_event_to_gastrocore(wp_event)
                        external_id = mapped["external_id"]
                        seen_external_ids.add(external_id)
                        
                        existing = await db.events.find_one({
                            "external_source": SYNC_SOURCE,
                            "external_id": external_id,
                            "archived": {"$ne": True}
                        })
                        
                        now_str = datetime.now(timezone.utc).isoformat()
                        
                        if existing:
                            if has_real_changes(existing, mapped):
                                await db.events.update_one(
                                    {"id": existing["id"]},
                                    {"$set": {
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
                                        "content_category": mapped.get("content_category", "VERANSTALTUNG"),
                                        "wp_categories": mapped["wp_categories"],
                                        # Aktionen-Felder (Sprint: Aktionen-Infrastruktur)
                                        "action_type": mapped.get("action_type"),
                                        "menu_only": mapped.get("menu_only"),
                                        "restriction_notice": mapped.get("restriction_notice"),
                                        "guest_notice": mapped.get("guest_notice"),
                                        "updated_at": now_str,
                                        "last_sync_at": now_str,
                                    }}
                                )
                                report["updated"] += 1
                            else:
                                await db.events.update_one(
                                    {"id": existing["id"]},
                                    {"$set": {"last_sync_at": now_str}}
                                )
                                report["unchanged"] += 1
                        else:
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
                                "content_category": mapped.get("content_category", "VERANSTALTUNG"),
                                "wp_categories": mapped["wp_categories"],
                                # Aktionen-Felder (Sprint: Aktionen-Infrastruktur)
                                "action_type": mapped.get("action_type"),
                                "menu_only": mapped.get("menu_only"),
                                "restriction_notice": mapped.get("restriction_notice"),
                                "guest_notice": mapped.get("guest_notice"),
                                "status": "published",
                                "capacity_total": 100,
                                "booking_mode": "ticket_only",
                                "pricing_mode": "free_config",
                                "requires_payment": False,
                                "is_public": True,
                                "archived": False,
                                "created_at": now_str,
                                "updated_at": now_str,
                                "last_sync_at": now_str,
                            }
                            await db.events.insert_one(new_event)
                            report["created"] += 1
                            
                    except Exception as e:
                        report["errors"].append(str(e))
                        report["skipped"] += 1
                
                # Archivieren
                cutoff_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
                all_wp_in_db = await db.events.find({
                    "external_source": SYNC_SOURCE,
                    "archived": {"$ne": True}
                }).to_list(1000)
                
                for db_event in all_wp_in_db:
                    ext_id = db_event.get("external_id")
                    end_dt = db_event.get("end_datetime")
                    should_archive = ext_id not in seen_external_ids or (end_dt and end_dt < cutoff_date)
                    
                    if should_archive:
                        await db.events.update_one(
                            {"id": db_event["id"]},
                            {"$set": {"archived": True, "status": "archived", "updated_at": datetime.now(timezone.utc).isoformat()}}
                        )
                        report["archived"] += 1
                
                # Import-Log
                duration_ms = int((time.time() - start_time) * 1000)
                await db.import_logs.insert_one({
                    "id": str(uuid.uuid4()),
                    "type": "wordpress_events_sync",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user": "scheduler",
                    "source": WORDPRESS_EVENTS_API,
                    "fetched": report["fetched"],
                    "created": report["created"],
                    "updated": report["updated"],
                    "unchanged": report["unchanged"],
                    "archived": report["archived"],
                    "skipped": report["skipped"],
                    "errors": report["errors"][:10],
                    "duration_ms": duration_ms,
                    "success": len(report["errors"]) == 0,
                    "result": "success" if len(report["errors"]) == 0 else "partial",
                })
                
                logger.info(f"[WP-SYNC] Abgeschlossen: {report['created']} neu, {report['updated']} geändert, {report['unchanged']} unverändert ({duration_ms}ms)")
                
            finally:
                # Lock freigeben
                if LOCK_FILE.exists():
                    LOCK_FILE.unlink()
                    
        except Exception as e:
            logger.error(f"[WP-SYNC] Fehler: {e}")
            # Lock freigeben bei Fehler
            try:
                if LOCK_FILE.exists():
                    LOCK_FILE.unlink()
            except:
                pass
        
        # Warten bis zum nächsten Lauf
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)

@app.on_event("shutdown")
async def shutdown():
    await close_db_connection()
