"""
GastroCore API v1.1.0 - Production-Ready
Modular Gastro Management System

Architecture:
- Core: Auth, Audit, Config, Validators
- Modules: Reservations, Areas, Users, Settings

Security:
- RBAC on all endpoints
- Audit logging for all mutations
- Input validation
- Status transition enforcement
"""
from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, BackgroundTasks, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator
from typing import List, Optional, Any, Dict
import uuid
from datetime import datetime, timezone, timedelta
import logging
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Core imports
from core.config import settings
from core.database import db, client, close_db_connection
from core.auth import (
    get_current_user, require_roles, require_admin, require_manager,
    hash_password, verify_password, create_token, decode_token
)
from core.audit import create_audit_log, safe_dict_for_audit, SYSTEM_ACTOR
from core.models import UserRole, ReservationStatus, serialize_for_db
from core.validators import (
    validate_status_transition, validate_reservation_data,
    validate_area_data, validate_user_data, validate_password_strength
)
from core.exceptions import (
    GastroCoreException, UnauthorizedException, ForbiddenException,
    NotFoundException, ValidationException, ConflictException,
    InvalidStatusTransitionException
)
from email_service import (
    send_confirmation_email, send_reminder_email, send_cancellation_email,
    verify_cancel_token
)

# ============== APP SETUP ==============
app = FastAPI(
    title="GastroCore API",
    version="1.1.0",
    description="Production-Ready Restaurant Management System"
)

api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============== GLOBAL EXCEPTION HANDLER ==============
@app.exception_handler(GastroCoreException)
async def gastrocore_exception_handler(request: Request, exc: GastroCoreException):
    """Handle all custom exceptions with consistent format"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": exc.error_code,
            "success": False
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Ein unerwarteter Fehler ist aufgetreten",
            "error_code": "INTERNAL_ERROR",
            "success": False
        }
    )


# ============== PYDANTIC MODELS ==============
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

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class AreaCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    capacity: Optional[int] = Field(None, ge=1, le=500)

class AreaResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    capacity: Optional[int]
    created_at: str
    archived: bool

class ReservationCreate(BaseModel):
    guest_name: str = Field(..., min_length=2, max_length=100)
    guest_phone: str = Field(..., min_length=6, max_length=30)
    guest_email: Optional[EmailStr] = None
    party_size: int = Field(..., ge=1, le=20)
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    area_id: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=1000)
    
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
    notes: Optional[str] = Field(None, max_length=1000)

class StatusUpdate(BaseModel):
    status: ReservationStatus

class SettingCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    value: str
    description: Optional[str] = None


# ============== HELPER FUNCTIONS ==============
def create_user_entity(email: str, name: str, role: str, password_hash: str, must_change: bool = True) -> dict:
    """Create a new user document"""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": name,
        "role": role,
        "password_hash": password_hash,
        "is_active": True,
        "must_change_password": must_change,
        "created_at": now,
        "updated_at": now,
        "archived": False
    }

def create_reservation_entity(data: dict) -> dict:
    """Create a new reservation document"""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(uuid.uuid4()),
        "guest_name": data.get("guest_name"),
        "guest_phone": data.get("guest_phone"),
        "guest_email": data.get("guest_email"),
        "party_size": data.get("party_size"),
        "date": data.get("date"),
        "time": data.get("time"),
        "area_id": data.get("area_id"),
        "notes": data.get("notes"),
        "status": ReservationStatus.NEU.value,
        "created_at": now,
        "updated_at": now,
        "archived": False,
        "reminder_sent": False
    }

def create_area_entity(data: dict) -> dict:
    """Create a new area document"""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(uuid.uuid4()),
        "name": data.get("name"),
        "description": data.get("description"),
        "capacity": data.get("capacity"),
        "created_at": now,
        "updated_at": now,
        "archived": False
    }


# ============== AUTH ENDPOINTS ==============
@api_router.post("/auth/login", response_model=TokenResponse, tags=["Auth"])
async def login(data: UserLogin):
    """Authenticate user and return JWT token"""
    user = await db.users.find_one({"email": data.email, "archived": False}, {"_id": 0})
    
    if not user or not verify_password(data.password, user["password_hash"]):
        raise UnauthorizedException("Ungültige Anmeldedaten")
    
    if not user.get("is_active", True):
        raise UnauthorizedException("Konto deaktiviert")
    
    token = create_token(user["id"], user["email"], user["role"])
    
    # Audit login
    await create_audit_log(user, "user", user["id"], "login")
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            is_active=user["is_active"],
            must_change_password=user.get("must_change_password", False),
            created_at=user["created_at"]
        )
    )

@api_router.get("/auth/me", response_model=UserResponse, tags=["Auth"])
async def get_me(user: dict = Depends(get_current_user)):
    """Get current authenticated user"""
    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        role=user["role"],
        is_active=user["is_active"],
        must_change_password=user.get("must_change_password", False),
        created_at=user["created_at"]
    )

@api_router.post("/auth/change-password", tags=["Auth"])
async def change_password(data: PasswordChange, user: dict = Depends(get_current_user)):
    """Change user password"""
    if not verify_password(data.current_password, user["password_hash"]):
        raise ValidationException("Aktuelles Passwort ist falsch")
    
    validate_password_strength(data.new_password)
    
    before = safe_dict_for_audit(user)
    new_hash = hash_password(data.new_password)
    
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {
            "password_hash": new_hash,
            "must_change_password": False,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    await create_audit_log(user, "user", user["id"], "password_change", before, {**before, "must_change_password": False})
    
    return {"message": "Passwort erfolgreich geändert", "success": True}


# ============== USER ENDPOINTS (Admin only) ==============
@api_router.get("/users", response_model=List[UserResponse], tags=["Users"])
async def get_users(user: dict = Depends(require_admin)):
    """List all users (Admin only)"""
    users = await db.users.find({"archived": False}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return [UserResponse(**u) for u in users]

@api_router.post("/users", response_model=UserResponse, tags=["Users"])
async def create_user(data: UserCreate, user: dict = Depends(require_admin)):
    """Create a new user (Admin only)"""
    # Check for duplicate email
    existing = await db.users.find_one({"email": data.email, "archived": False})
    if existing:
        raise ConflictException("E-Mail bereits registriert")
    
    new_user = create_user_entity(
        email=data.email,
        name=data.name,
        role=data.role.value,
        password_hash=hash_password(data.password),
        must_change=True
    )
    
    await db.users.insert_one(new_user)
    await create_audit_log(user, "user", new_user["id"], "create", None, safe_dict_for_audit(new_user))
    
    return UserResponse(**{k: v for k, v in new_user.items() if k != "password_hash"})

@api_router.delete("/users/{user_id}", tags=["Users"])
async def archive_user(user_id: str, user: dict = Depends(require_admin)):
    """Archive a user (Admin only)"""
    if user_id == user["id"]:
        raise ValidationException("Eigenes Konto kann nicht archiviert werden")
    
    existing = await db.users.find_one({"id": user_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Benutzer")
    
    before = safe_dict_for_audit(existing)
    await db.users.update_one({"id": user_id}, {"$set": {"archived": True, "updated_at": datetime.now(timezone.utc).isoformat()}})
    
    await create_audit_log(user, "user", user_id, "archive", before, {**before, "archived": True})
    
    return {"message": "Benutzer archiviert", "success": True}


# ============== AREA ENDPOINTS ==============
@api_router.get("/areas", tags=["Areas"])
async def get_areas(user: dict = Depends(get_current_user)):
    """List all areas (requires authentication)"""
    areas = await db.areas.find({"archived": False}, {"_id": 0}).to_list(1000)
    return areas

@api_router.post("/areas", tags=["Areas"])
async def create_area(data: AreaCreate, user: dict = Depends(require_admin)):
    """Create a new area (Admin only)"""
    area = create_area_entity(data.model_dump(exclude_none=True))
    
    await db.areas.insert_one(area)
    await create_audit_log(user, "area", area["id"], "create", None, safe_dict_for_audit(area))
    
    return area

@api_router.put("/areas/{area_id}", tags=["Areas"])
async def update_area(area_id: str, data: AreaCreate, user: dict = Depends(require_admin)):
    """Update an area (Admin only)"""
    existing = await db.areas.find_one({"id": area_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Bereich")
    
    before = safe_dict_for_audit(existing)
    update_data = {**data.model_dump(exclude_none=True), "updated_at": datetime.now(timezone.utc).isoformat()}
    
    await db.areas.update_one({"id": area_id}, {"$set": update_data})
    
    updated = await db.areas.find_one({"id": area_id}, {"_id": 0})
    await create_audit_log(user, "area", area_id, "update", before, safe_dict_for_audit(updated))
    
    return updated

@api_router.delete("/areas/{area_id}", tags=["Areas"])
async def archive_area(area_id: str, user: dict = Depends(require_admin)):
    """Archive an area (Admin only)"""
    existing = await db.areas.find_one({"id": area_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Bereich")
    
    before = safe_dict_for_audit(existing)
    await db.areas.update_one({"id": area_id}, {"$set": {"archived": True, "updated_at": datetime.now(timezone.utc).isoformat()}})
    
    await create_audit_log(user, "area", area_id, "archive", before, {**before, "archived": True})
    
    return {"message": "Bereich archiviert", "success": True}


# ============== RESERVATION ENDPOINTS ==============
@api_router.get("/reservations", tags=["Reservations"])
async def get_reservations(
    date: Optional[str] = None,
    status: Optional[ReservationStatus] = None,
    area_id: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 200,
    user: dict = Depends(get_current_user)
):
    """
    List reservations with filters.
    - Admin/Schichtleiter: Full access
    - Mitarbeiter: Blocked (no terminal access)
    """
    # RBAC: Mitarbeiter cannot access reservations
    if user["role"] == UserRole.MITARBEITER.value:
        raise ForbiddenException("Kein Zugriff auf Reservierungen")
    
    query = {"archived": False}
    
    if date:
        query["date"] = date
    if status:
        query["status"] = status.value
    if area_id:
        query["area_id"] = area_id
    if search:
        query["$or"] = [
            {"guest_name": {"$regex": search, "$options": "i"}},
            {"guest_phone": {"$regex": search, "$options": "i"}}
        ]
    
    reservations = await db.reservations.find(query, {"_id": 0}).sort("time", 1).limit(limit).to_list(limit)
    return reservations

@api_router.get("/reservations/{reservation_id}", tags=["Reservations"])
async def get_reservation(reservation_id: str, user: dict = Depends(get_current_user)):
    """Get a single reservation"""
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
    """Create a new reservation (Admin/Schichtleiter only)"""
    # Validate reservation data
    validate_reservation_data(data.model_dump())
    
    # Verify area exists if specified
    if data.area_id:
        area = await db.areas.find_one({"id": data.area_id, "archived": False})
        if not area:
            raise ValidationException("Ungültiger Bereich")
    
    reservation = create_reservation_entity(data.model_dump(exclude_none=True))
    
    await db.reservations.insert_one(reservation)
    await create_audit_log(user, "reservation", reservation["id"], "create", None, safe_dict_for_audit(reservation))
    
    # Send confirmation email
    if data.guest_email:
        area_name = None
        if data.area_id:
            area_doc = await db.areas.find_one({"id": data.area_id}, {"_id": 0})
            area_name = area_doc.get("name") if area_doc else None
        background_tasks.add_task(send_confirmation_email, reservation, area_name)
    
    return reservation

@api_router.put("/reservations/{reservation_id}", tags=["Reservations"])
async def update_reservation(
    reservation_id: str,
    data: ReservationUpdate,
    user: dict = Depends(require_manager)
):
    """Update a reservation (Admin/Schichtleiter only)"""
    existing = await db.reservations.find_one({"id": reservation_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Reservierung")
    
    # Cannot update terminal status reservations
    if ReservationStatus.is_terminal(existing.get("status")):
        raise ValidationException("Abgeschlossene Reservierungen können nicht mehr bearbeitet werden")
    
    before = safe_dict_for_audit(existing)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.reservations.update_one({"id": reservation_id}, {"$set": update_data})
    
    updated = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    await create_audit_log(user, "reservation", reservation_id, "update", before, safe_dict_for_audit(updated))
    
    return updated

@api_router.patch("/reservations/{reservation_id}/status", tags=["Reservations"])
async def update_reservation_status(
    reservation_id: str,
    new_status: ReservationStatus,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_manager)
):
    """
    Change reservation status (Admin/Schichtleiter only).
    Enforces valid status transitions.
    """
    existing = await db.reservations.find_one({"id": reservation_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Reservierung")
    
    current_status = existing.get("status")
    
    # Validate status transition
    validate_status_transition(current_status, new_status.value)
    
    before = safe_dict_for_audit(existing)
    update_data = {
        "status": new_status.value,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.reservations.update_one({"id": reservation_id}, {"$set": update_data})
    
    updated = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    await create_audit_log(user, "reservation", reservation_id, "status_change", before, safe_dict_for_audit(updated))
    
    # Send confirmation email when confirmed
    if new_status == ReservationStatus.BESTAETIGT and current_status != "bestaetigt":
        if updated.get("guest_email"):
            area_name = None
            if updated.get("area_id"):
                area_doc = await db.areas.find_one({"id": updated["area_id"]}, {"_id": 0})
                area_name = area_doc.get("name") if area_doc else None
            background_tasks.add_task(send_confirmation_email, updated, area_name)
    
    return updated

@api_router.delete("/reservations/{reservation_id}", tags=["Reservations"])
async def archive_reservation(reservation_id: str, user: dict = Depends(require_manager)):
    """Archive a reservation (Admin/Schichtleiter only)"""
    existing = await db.reservations.find_one({"id": reservation_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Reservierung")
    
    before = safe_dict_for_audit(existing)
    await db.reservations.update_one({"id": reservation_id}, {"$set": {"archived": True, "updated_at": datetime.now(timezone.utc).isoformat()}})
    
    await create_audit_log(user, "reservation", reservation_id, "archive", before, {**before, "archived": True})
    
    return {"message": "Reservierung archiviert", "success": True}


# ============== PUBLIC CANCELLATION ==============
@api_router.post("/reservations/{reservation_id}/cancel", tags=["Public"])
async def cancel_reservation_public(
    reservation_id: str,
    token: str,
    background_tasks: BackgroundTasks
):
    """Public endpoint for guests to cancel via email link"""
    if not verify_cancel_token(reservation_id, token):
        raise ForbiddenException("Ungültiger Stornierungslink")
    
    existing = await db.reservations.find_one({"id": reservation_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Reservierung")
    
    current_status = existing.get("status")
    
    # Validate cancellation is allowed
    if not ReservationStatus.can_cancel(current_status):
        raise ValidationException("Diese Reservierung kann nicht mehr storniert werden")
    
    before = safe_dict_for_audit(existing)
    update_data = {
        "status": ReservationStatus.STORNIERT.value,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.reservations.update_one({"id": reservation_id}, {"$set": update_data})
    await create_audit_log(SYSTEM_ACTOR, "reservation", reservation_id, "cancel_by_guest", before, {**before, "status": "storniert"})
    
    if existing.get("guest_email"):
        background_tasks.add_task(send_cancellation_email, existing)
    
    return {"message": "Reservierung erfolgreich storniert", "success": True}


# ============== REMINDER ENDPOINT ==============
@api_router.post("/reservations/send-reminders", tags=["Admin"])
async def send_reservation_reminders(background_tasks: BackgroundTasks, user: dict = Depends(require_admin)):
    """Send reminder emails for tomorrow's reservations (Admin only)"""
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
            
            background_tasks.add_task(send_reminder_email, res, area_name)
            await db.reservations.update_one({"id": res["id"]}, {"$set": {"reminder_sent": True}})
            sent_count += 1
    
    return {"message": f"Erinnerungen gesendet: {sent_count}", "count": sent_count, "success": True}


# ============== SETTINGS ENDPOINTS ==============
@api_router.get("/settings", tags=["Settings"])
async def get_settings_endpoint(user: dict = Depends(require_admin)):
    """Get all settings (Admin only)"""
    settings_list = await db.settings.find({}, {"_id": 0}).to_list(1000)
    return settings_list

@api_router.post("/settings", tags=["Settings"])
async def create_or_update_setting(data: SettingCreate, user: dict = Depends(require_admin)):
    """Create or update a setting (Admin only)"""
    existing = await db.settings.find_one({"key": data.key}, {"_id": 0})
    now = datetime.now(timezone.utc).isoformat()
    
    if existing:
        before = safe_dict_for_audit(existing)
        update_data = {"value": data.value, "description": data.description, "updated_at": now}
        await db.settings.update_one({"key": data.key}, {"$set": update_data})
        updated = await db.settings.find_one({"key": data.key}, {"_id": 0})
        await create_audit_log(user, "setting", data.key, "update", before, safe_dict_for_audit(updated))
        return updated
    else:
        setting = {
            "id": str(uuid.uuid4()),
            "key": data.key,
            "value": data.value,
            "description": data.description,
            "created_at": now,
            "updated_at": now
        }
        await db.settings.insert_one(setting)
        await create_audit_log(user, "setting", data.key, "create", None, safe_dict_for_audit(setting))
        return setting


# ============== AUDIT LOG ENDPOINTS ==============
@api_router.get("/audit-logs", tags=["Audit"])
async def get_audit_logs(
    entity: Optional[str] = None,
    entity_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(require_admin)
):
    """Get audit logs (Admin only)"""
    query = {}
    if entity:
        query["entity"] = entity
    if entity_id:
        query["entity_id"] = entity_id
    if actor_id:
        query["actor_id"] = actor_id
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    return logs


# ============== SEED DATA ==============
@api_router.post("/seed", tags=["Admin"])
async def seed_data():
    """Seed initial test data (only if no users exist)"""
    existing_users = await db.users.count_documents({"archived": False})
    if existing_users > 0:
        return {"message": "Daten bereits vorhanden", "seeded": False}
    
    test_users = [
        {"email": "admin@gastrocore.de", "name": "Admin User", "role": "admin", "password": "Admin123!"},
        {"email": "schichtleiter@gastrocore.de", "name": "Schicht Leiter", "role": "schichtleiter", "password": "Schicht123!"},
        {"email": "mitarbeiter@gastrocore.de", "name": "Mit Arbeiter", "role": "mitarbeiter", "password": "Mitarbeiter123!"},
    ]
    
    for u in test_users:
        user_doc = create_user_entity(u["email"], u["name"], u["role"], hash_password(u["password"]))
        await db.users.insert_one(user_doc)
    
    test_areas = [
        {"name": "Terrasse", "description": "Außenbereich mit Sonnenschirmen", "capacity": 40},
        {"name": "Saal", "description": "Hauptspeiseraum", "capacity": 80},
        {"name": "Wintergarten", "description": "Verglaster Bereich", "capacity": 30},
        {"name": "Bar", "description": "Barhocker und Stehtische", "capacity": 20},
    ]
    
    area_ids = []
    for a in test_areas:
        area_doc = create_area_entity(a)
        await db.areas.insert_one(area_doc)
        area_ids.append(area_doc["id"])
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    test_reservations = [
        {"guest_name": "Familie Müller", "guest_phone": "+49 170 1234567", "party_size": 4, "date": today, "time": "12:00", "area_id": area_ids[1]},
        {"guest_name": "Hans Schmidt", "guest_phone": "+49 171 2345678", "party_size": 2, "date": today, "time": "13:00", "area_id": area_ids[0]},
        {"guest_name": "Lisa Weber", "guest_phone": "+49 172 3456789", "party_size": 6, "date": today, "time": "18:30", "area_id": area_ids[2]},
        {"guest_name": "Peter Braun", "guest_phone": "+49 173 4567890", "party_size": 3, "date": today, "time": "19:00", "area_id": area_ids[1]},
        {"guest_name": "Maria Schwarz", "guest_phone": "+49 174 5678901", "party_size": 8, "date": today, "time": "20:00", "area_id": area_ids[1]},
    ]
    
    for r in test_reservations:
        res_doc = create_reservation_entity(r)
        await db.reservations.insert_one(res_doc)
    
    return {
        "message": "Testdaten erstellt",
        "seeded": True,
        "users": [{"email": u["email"], "password": u["password"], "role": u["role"]} for u in test_users]
    }


# ============== HEALTH CHECK ==============
@api_router.get("/", tags=["Health"])
async def root():
    """API health check"""
    return {"message": "GastroCore API v1.1.0", "status": "running", "success": True}

@api_router.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check"""
    try:
        await client.admin.command('ping')
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "version": "1.1.0"
    }


# ============== APP CONFIG ==============
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.CORS_ORIGINS.split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown():
    await close_db_connection()
