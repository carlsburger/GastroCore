"""
GastroCore Staff & Schedule Module - Sprint 5
Mitarbeiter- und Dienstplanverwaltung

ADDITIV - Keine Breaking Changes
"""

from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any, Generic, TypeVar
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from enum import Enum
import uuid
import os
import io
import csv
import logging
import shutil
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# Core imports
from core.database import db
from core.auth import require_admin, require_manager, get_current_user
from core.audit import create_audit_log, safe_dict_for_audit, SYSTEM_ACTOR
from core.exceptions import NotFoundException, ValidationException, ForbiddenException

logger = logging.getLogger(__name__)

# ============== FILE STORAGE CONFIG ==============
UPLOAD_DIR = Path("/app/uploads/staff_documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}


# ============== API RESPONSE TYPES ==============
class ApiErrorCode(str, Enum):
    """Zentrale Error-Codes für konsistente API-Semantik"""
    STAFF_NOT_LINKED = "STAFF_NOT_LINKED"
    NO_SHIFTS_ASSIGNED = "NO_SHIFTS_ASSIGNED"
    INVALID_ROLE = "INVALID_ROLE"
    NOT_AUTHENTICATED = "NOT_AUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFLICT = "CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    """
    Einheitlicher API Response Type für alle Endpoints.
    
    Regeln:
    - success=True: Anfrage erfolgreich verarbeitet (auch bei leeren Daten)
    - success=False: Technischer Fehler oder Validierungsfehler
    - HTTP 200: Auch für fachlich leere Zustände (z.B. keine Schichten)
    - HTTP 4xx/5xx: Nur für echte Fehler
    """
    success: bool = True
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[ApiErrorCode] = None
    
    class Config:
        use_enum_values = True


def api_success(data: Any = None, message: str = None) -> dict:
    """Helper für erfolgreiche API-Responses"""
    return {
        "success": True,
        "data": data,
        "message": message,
        "error": None
    }


def api_info(data: Any = None, message: str = None, error_code: ApiErrorCode = None) -> dict:
    """Helper für fachliche Zustände (z.B. keine Daten, nicht verknüpft)"""
    return {
        "success": True,
        "data": data,
        "message": message,
        "error": error_code.value if error_code else None
    }


def api_error(message: str, error_code: ApiErrorCode, data: Any = None) -> dict:
    """Helper für Fehlerfälle"""
    return {
        "success": False,
        "data": data,
        "message": message,
        "error": error_code.value
    }


# ============== ENUMS ==============
class EmploymentType(str, Enum):
    MINI = "mini"  # Minijob
    TEILZEIT = "teilzeit"  # Teilzeit
    VOLLZEIT = "vollzeit"  # Vollzeit


class StaffStatus(str, Enum):
    AKTIV = "aktiv"
    INAKTIV = "inaktiv"


class ScheduleStatus(str, Enum):
    ENTWURF = "entwurf"  # Draft
    VEROEFFENTLICHT = "veroeffentlicht"  # Published
    ARCHIVIERT = "archiviert"  # Archived


class DocumentCategory(str, Enum):
    ARBEITSVERTRAG = "arbeitsvertrag"
    BELEHRUNG = "belehrung"
    ZEUGNIS = "zeugnis"
    SONSTIGES = "sonstiges"


class DocumentVisibility(str, Enum):
    HR_ONLY = "hr_only"  # Only Admin
    MANAGER = "manager"  # Admin + Schichtleiter
    SELF = "self"  # Employee can see own


class ShiftRole(str, Enum):
    SERVICE = "service"
    SCHICHTLEITER = "schichtleiter"
    KUECHE = "kueche"
    BAR = "bar"
    AUSHILFE = "aushilfe"


# ============== HELPER FUNCTIONS ==============
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_entity(data: dict) -> dict:
    return {
        "id": str(uuid.uuid4()),
        **data,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "archived": False
    }


# ============== KONFLIKT-ERKENNUNG (Sprint: Dienstplan Live-Ready) ==============

async def check_shift_conflicts(
    staff_member_id: str,
    shift_date: str,
    start_time: str,
    end_time: str,
    exclude_shift_id: str = None
) -> dict:
    """
    Prüft auf Konflikte bei Schichtzuweisung:
    A) Doppelbelegung (überlappende Zeiten am gleichen Tag)
    B) Ruhezeit (min. 11 Stunden zwischen Schichten)
    
    Returns: {"has_conflict": bool, "conflict_type": str, "message": str}
    """
    from datetime import datetime, timedelta
    
    # A) Prüfe Doppelbelegung am gleichen Tag
    query = {
        "staff_member_id": staff_member_id,
        "shift_date": shift_date,
        "archived": False
    }
    if exclude_shift_id:
        query["id"] = {"$ne": exclude_shift_id}
    
    same_day_shifts = await db.shifts.find(query, {"_id": 0}).to_list(100)
    
    # Parse times
    new_start = datetime.strptime(start_time, "%H:%M")
    new_end = datetime.strptime(end_time, "%H:%M")
    if new_end < new_start:
        new_end += timedelta(days=1)
    
    for existing in same_day_shifts:
        ex_start = datetime.strptime(existing["start_time"], "%H:%M")
        ex_end = datetime.strptime(existing["end_time"], "%H:%M")
        if ex_end < ex_start:
            ex_end += timedelta(days=1)
        
        # Check overlap
        if not (new_end <= ex_start or new_start >= ex_end):
            return {
                "has_conflict": True,
                "conflict_type": "overlap",
                "message": f"Konflikt: Mitarbeiter ist bereits eingeplant ({existing['start_time']}-{existing['end_time']})"
            }
    
    # B) Prüfe Ruhezeit (11 Stunden)
    shift_datetime = datetime.fromisoformat(shift_date)
    prev_day = (shift_datetime - timedelta(days=1)).strftime("%Y-%m-%d")
    next_day = (shift_datetime + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Schichten am Vortag (für Ruhezeit nach Schichtende)
    prev_query = {
        "staff_member_id": staff_member_id,
        "shift_date": prev_day,
        "archived": False
    }
    prev_shifts = await db.shifts.find(prev_query, {"_id": 0}).to_list(100)
    
    for prev in prev_shifts:
        prev_end = datetime.strptime(prev["end_time"], "%H:%M")
        # Wenn Schicht nach Mitternacht endet
        if prev_end < datetime.strptime(prev["start_time"], "%H:%M"):
            prev_end_full = shift_datetime.replace(hour=prev_end.hour, minute=prev_end.minute)
        else:
            prev_end_full = (shift_datetime - timedelta(days=1)).replace(hour=prev_end.hour, minute=prev_end.minute)
        
        new_start_full = shift_datetime.replace(hour=new_start.hour, minute=new_start.minute)
        
        rest_hours = (new_start_full - prev_end_full).total_seconds() / 3600
        if 0 < rest_hours < 11:
            return {
                "has_conflict": True,
                "conflict_type": "rest_time",
                "message": f"Ruhezeit von 11h unterschritten (nur {rest_hours:.1f}h seit Schichtende am Vortag)"
            }
    
    # Schichten am Folgetag (für Ruhezeit vor Schichtbeginn)
    next_query = {
        "staff_member_id": staff_member_id,
        "shift_date": next_day,
        "archived": False
    }
    next_shifts = await db.shifts.find(next_query, {"_id": 0}).to_list(100)
    
    for nxt in next_shifts:
        nxt_start = datetime.strptime(nxt["start_time"], "%H:%M")
        nxt_start_full = (shift_datetime + timedelta(days=1)).replace(hour=nxt_start.hour, minute=nxt_start.minute)
        
        new_end_full = shift_datetime.replace(hour=new_end.hour, minute=new_end.minute)
        if new_end < new_start:
            new_end_full += timedelta(days=1)
        
        rest_hours = (nxt_start_full - new_end_full).total_seconds() / 3600
        if 0 < rest_hours < 11:
            return {
                "has_conflict": True,
                "conflict_type": "rest_time",
                "message": f"Ruhezeit von 11h unterschritten (nur {rest_hours:.1f}h bis Schichtbeginn am Folgetag)"
            }
    
    return {"has_conflict": False, "conflict_type": None, "message": None}


def get_week_dates(year: int, week: int) -> tuple:
    """
    Get start and end date of an ISO calendar week.
    Uses ISO 8601 standard: Week 1 is the first week with at least 4 days in the new year.
    The 4th of January is ALWAYS in week 1.
    """
    # ISO 8601: Der 4. Januar ist immer in Woche 1
    jan_4 = date(year, 1, 4)
    # Finde den Montag der Woche 1
    week_1_monday = jan_4 - timedelta(days=jan_4.weekday())
    # Berechne den Montag der gewünschten Woche
    week_start = week_1_monday + timedelta(weeks=week - 1)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def calculate_shift_hours(start_time: str, end_time: str) -> float:
    """Calculate hours from start and end time strings (HH:MM)"""
    start = datetime.strptime(start_time, "%H:%M")
    end = datetime.strptime(end_time, "%H:%M")
    if end < start:  # Overnight shift
        end += timedelta(days=1)
    diff = end - start
    return diff.total_seconds() / 3600


# ============== PYDANTIC MODELS ==============

# Work Areas
class WorkAreaCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    color: str = Field(default="#10b981")  # Tailwind green-500
    sort_order: int = Field(default=0)


class WorkAreaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


# Staff Members
class StaffMemberCreate(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: ShiftRole = ShiftRole.SERVICE
    employment_type: EmploymentType = EmploymentType.TEILZEIT
    weekly_hours: float = Field(default=20.0, ge=0, le=48)
    entry_date: str  # YYYY-MM-DD
    work_area_ids: List[str] = []  # Can work in multiple areas
    notes: Optional[str] = None  # HR internal notes
    user_id: Optional[str] = None  # Link to users collection (nullable)
    # NEW HR Fields (Sprint 7.1 - Additive)
    mobile_phone: Optional[str] = None
    street: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    date_of_birth: Optional[str] = None  # YYYY-MM-DD
    tax_id: Optional[str] = None  # Steuer-ID
    social_security_number: Optional[str] = None  # SV-Nummer
    health_insurance: Optional[str] = None  # Krankenkasse
    bank_iban: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


class StaffMemberUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[ShiftRole] = None
    employment_type: Optional[EmploymentType] = None
    weekly_hours: Optional[float] = None
    entry_date: Optional[str] = None
    work_area_ids: Optional[List[str]] = None
    notes: Optional[str] = None
    status: Optional[StaffStatus] = None
    user_id: Optional[str] = None
    # NEW HR Fields (Sprint 7.1 - Additive)
    mobile_phone: Optional[str] = None
    street: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    date_of_birth: Optional[str] = None
    tax_id: Optional[str] = None
    social_security_number: Optional[str] = None
    health_insurance: Optional[str] = None
    bank_iban: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


# NEW: HR Fields Update Model (Sprint 7.1)
class StaffHRFieldsUpdate(BaseModel):
    """Update sensitive HR fields - Admin only with audit logging"""
    email: Optional[EmailStr] = None
    mobile_phone: Optional[str] = None
    street: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    date_of_birth: Optional[str] = None
    tax_id: Optional[str] = None
    social_security_number: Optional[str] = None
    health_insurance: Optional[str] = None
    bank_iban: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


# NEW: Contact Fields visible to Manager (Sprint 7.1)
CONTACT_FIELDS = {"email", "phone", "mobile_phone", "emergency_contact_name", "emergency_contact_phone"}
# Sensitive HR fields - Admin only (NEVER exposed to non-admins)
SENSITIVE_HR_FIELDS = {"tax_id", "social_security_number", "bank_iban", "health_insurance", "date_of_birth", "street", "zip_code", "city"}
# HIGH SECURITY fields - encrypted at rest, masked in responses
HIGH_SECURITY_FIELDS = {"tax_id", "social_security_number", "bank_iban"}
# Fields requiring special audit logging
AUDIT_SENSITIVE_FIELDS = {"tax_id", "social_security_number", "bank_iban"}

# ============== ENCRYPTION MODULE (Sprint 7.2 - Security Enhancement) ==============
from cryptography.fernet import Fernet
import base64
import hashlib

# Get or generate encryption key from environment
def get_encryption_key() -> bytes:
    """Get encryption key from environment or generate deterministic one"""
    key_env = os.environ.get("HR_ENCRYPTION_KEY")
    if key_env:
        # Use provided key
        return base64.urlsafe_b64decode(key_env)
    else:
        # Generate deterministic key from JWT_SECRET for consistency
        jwt_secret = os.environ.get("JWT_SECRET", "default-secret-key-for-dev")
        # Create a proper Fernet key from the secret
        key_hash = hashlib.sha256(jwt_secret.encode()).digest()
        return base64.urlsafe_b64encode(key_hash)

ENCRYPTION_KEY = get_encryption_key()
cipher_suite = Fernet(ENCRYPTION_KEY)


def encrypt_field(value: str) -> str:
    """Encrypt a sensitive field value"""
    if not value:
        return value
    try:
        encrypted = cipher_suite.encrypt(value.encode('utf-8'))
        return f"ENC:{encrypted.decode('utf-8')}"
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        return value


def decrypt_field(value: str) -> str:
    """Decrypt a sensitive field value"""
    if not value or not value.startswith("ENC:"):
        return value
    try:
        encrypted_data = value[4:].encode('utf-8')
        decrypted = cipher_suite.decrypt(encrypted_data)
        return decrypted.decode('utf-8')
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return value


def mask_tax_id(value: str) -> str:
    """Mask Steuer-ID: show only last 2 digits"""
    if not value:
        return None
    decrypted = decrypt_field(value)
    clean = decrypted.replace(" ", "").replace("-", "")
    if len(clean) >= 2:
        return "*" * (len(clean) - 2) + clean[-2:]
    return "*" * len(clean)


def mask_social_security(value: str) -> str:
    """Mask SV-Nummer: show only last 3 characters"""
    if not value:
        return None
    decrypted = decrypt_field(value)
    clean = decrypted.replace(" ", "").replace("-", "")
    if len(clean) >= 3:
        return "*" * (len(clean) - 3) + clean[-3:]
    return "*" * len(clean)


def mask_iban(value: str) -> str:
    """Mask IBAN: show only last 4 digits"""
    if not value:
        return None
    decrypted = decrypt_field(value)
    clean = decrypted.replace(" ", "")
    if len(clean) >= 4:
        # Format: **** **** **** 1234
        masked = "*" * (len(clean) - 4) + clean[-4:]
        # Add spaces for readability
        return " ".join([masked[i:i+4] for i in range(0, len(masked), 4)])
    return "*" * len(clean)


def mask_sensitive_fields(member: dict, include_has_value: bool = True) -> dict:
    """Mask sensitive fields for display, optionally include has_value indicators"""
    result = member.copy()
    
    # Mask high security fields
    if "tax_id" in result and result["tax_id"]:
        result["tax_id_masked"] = mask_tax_id(result["tax_id"])
        result["tax_id_has_value"] = True
        del result["tax_id"]
    elif include_has_value:
        result["tax_id_masked"] = None
        result["tax_id_has_value"] = False
    
    if "social_security_number" in result and result["social_security_number"]:
        result["social_security_number_masked"] = mask_social_security(result["social_security_number"])
        result["social_security_number_has_value"] = True
        del result["social_security_number"]
    elif include_has_value:
        result["social_security_number_masked"] = None
        result["social_security_number_has_value"] = False
    
    if "bank_iban" in result and result["bank_iban"]:
        result["bank_iban_masked"] = mask_iban(result["bank_iban"])
        result["bank_iban_has_value"] = True
        del result["bank_iban"]
    elif include_has_value:
        result["bank_iban_masked"] = None
        result["bank_iban_has_value"] = False
    
    return result


def validate_tax_id(tax_id: str) -> bool:
    """Validate German Steuer-ID (11 digits)"""
    if not tax_id:
        return True  # Optional field
    # Remove spaces and check if 11 digits
    clean = tax_id.replace(" ", "").replace("-", "")
    return clean.isdigit() and len(clean) == 11


def validate_iban(iban: str) -> bool:
    """Basic IBAN validation (DE = 22 characters)"""
    if not iban:
        return True  # Optional field
    clean = iban.replace(" ", "").upper()
    if clean.startswith("DE"):
        return len(clean) == 22 and clean[2:].replace("X", "0").isalnum()
    return len(clean) >= 15 and len(clean) <= 34


def validate_social_security(ssn: str) -> bool:
    """Basic German SV-Nummer validation (12 characters)"""
    if not ssn:
        return True
    clean = ssn.replace(" ", "").replace("-", "")
    return len(clean) >= 10 and len(clean) <= 12


def calculate_completeness(member: dict) -> dict:
    """Calculate onboarding completeness score and checklist"""
    checklist = {
        "email": bool(member.get("email")),
        "mobile_phone": bool(member.get("mobile_phone") or member.get("phone")),
        "address": bool(member.get("street") and member.get("zip_code") and member.get("city")),
        "tax_id": bool(member.get("tax_id")),
        "social_security_number": bool(member.get("social_security_number")),
        "bank_iban": bool(member.get("bank_iban")),
        "health_insurance": bool(member.get("health_insurance")),
        "emergency_contact": bool(member.get("emergency_contact_name") and member.get("emergency_contact_phone")),
    }
    
    # Calculate score (weighted)
    weights = {
        "email": 10,
        "mobile_phone": 10,
        "address": 15,
        "tax_id": 20,
        "social_security_number": 20,
        "bank_iban": 15,
        "health_insurance": 5,
        "emergency_contact": 5
    }
    
    total_weight = sum(weights.values())
    achieved = sum(weights[k] for k, v in checklist.items() if v)
    score = int((achieved / total_weight) * 100)
    
    # Pflichtfelder für "aktiv" Status
    required_for_active = ["email", "mobile_phone", "tax_id", "social_security_number", "bank_iban"]
    missing_for_active = [k for k in required_for_active if not checklist.get(k)]
    
    return {
        "score": score,
        "checklist": checklist,
        "missing_for_active": missing_for_active,
        "is_complete": score == 100
    }


def filter_member_for_role(member: dict, user_role: str, masked: bool = True) -> dict:
    """
    Filter staff member fields based on user role.
    
    Args:
        member: The staff member dict
        user_role: The role of the requesting user
        masked: If True (default), mask sensitive fields even for admin
    
    Security: Non-admins NEVER see sensitive HR fields
    """
    # IMMER display_name und full_name generieren (für Anzeige in Listen)
    display_name = member.get("display_name")
    full_name = member.get("full_name")
    first_name = member.get("first_name")
    last_name = member.get("last_name")
    
    # Wenn name vorhanden aber first/last fehlen, splitte
    if member.get("name") and not (first_name and last_name):
        name_parts = member.get("name", "").split()
        if len(name_parts) >= 2:
            first_name = first_name or name_parts[0]
            last_name = last_name or " ".join(name_parts[1:])
        elif len(name_parts) == 1:
            first_name = first_name or name_parts[0]
            last_name = last_name or ""
    
    # full_name zusammenbauen
    if not full_name:
        if first_name and last_name:
            full_name = f"{first_name} {last_name}"
        elif member.get("name"):
            full_name = member.get("name")
        elif first_name:
            full_name = first_name
        else:
            full_name = member.get("email", "Unbekannt").split("@")[0].title()
    
    # display_name (gleich wie full_name, wenn nicht vorhanden)
    if not display_name:
        display_name = full_name
    
    # Kurzname für Initialen etc.
    short_name = member.get("short_name")
    if not short_name:
        parts = full_name.split() if full_name else []
        if len(parts) >= 2:
            short_name = f"{parts[0][0]}. {parts[-1]}"
        else:
            short_name = full_name[:15] if full_name else "?"
    
    if user_role != "admin":
        # Non-admin: Remove ALL sensitive HR fields completely
        filtered = {}
        for k, v in member.items():
            if k not in SENSITIVE_HR_FIELDS and k not in HIGH_SECURITY_FIELDS:
                filtered[k] = v
        filtered["display_name"] = display_name
        filtered["short_name"] = short_name
        filtered["full_name"] = full_name
        filtered["first_name"] = first_name or ""
        filtered["last_name"] = last_name or ""
        return filtered
    
    # Admin: Apply masking to high-security fields by default
    if masked:
        result = mask_sensitive_fields(member)
    else:
        # Decrypt fields for admin when explicitly requested
        result = member.copy()
        for field in HIGH_SECURITY_FIELDS:
            if field in result and result[field]:
                result[field] = decrypt_field(result[field])
    
    result["display_name"] = display_name
    result["short_name"] = short_name
    result["full_name"] = full_name
    result["first_name"] = first_name or ""
    result["last_name"] = last_name or ""
    return result


# Schedules (Weekly)
class ScheduleCreate(BaseModel):
    year: int = Field(..., ge=2024, le=2030)
    week: int = Field(..., ge=1, le=53)
    notes: Optional[str] = None


class ScheduleUpdate(BaseModel):
    notes: Optional[str] = None
    status: Optional[ScheduleStatus] = None


# Shifts
class ShiftCreate(BaseModel):
    schedule_id: str
    staff_member_id: str
    work_area_id: str
    shift_date: str  # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    role: ShiftRole = ShiftRole.SERVICE
    notes: Optional[str] = None


class ShiftUpdate(BaseModel):
    staff_member_id: Optional[str] = None
    work_area_id: Optional[str] = None
    shift_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    role: Optional[ShiftRole] = None
    notes: Optional[str] = None


# Documents
class DocumentMetadata(BaseModel):
    category: DocumentCategory
    visibility: DocumentVisibility = DocumentVisibility.HR_ONLY
    description: Optional[str] = None


# Welcome Email
class WelcomeEmailRequest(BaseModel):
    language: str = Field(default="de", pattern="^(de|en|pl)$")


# ============== ROUTERS ==============
staff_router = APIRouter(prefix="/api/staff", tags=["Staff"])


# ============== WORK AREAS ENDPOINTS ==============
@staff_router.get("/work-areas")
async def list_work_areas(user: dict = Depends(require_manager)):
    """List all work areas"""
    areas = await db.work_areas.find({"archived": False}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    return areas


@staff_router.post("/work-areas")
async def create_work_area(data: WorkAreaCreate, user: dict = Depends(require_admin)):
    """Create a new work area"""
    area = create_entity({
        **data.model_dump(),
        "is_active": True
    })
    await db.work_areas.insert_one(area)
    await create_audit_log(user, "work_area", area["id"], "create", None, safe_dict_for_audit(area))
    return {k: v for k, v in area.items() if k != "_id"}


@staff_router.patch("/work-areas/{area_id}")
async def update_work_area(area_id: str, data: WorkAreaUpdate, user: dict = Depends(require_admin)):
    """Update a work area"""
    existing = await db.work_areas.find_one({"id": area_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Arbeitsbereich")
    
    before = safe_dict_for_audit(existing)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now_iso()
    
    await db.work_areas.update_one({"id": area_id}, {"$set": update_data})
    updated = await db.work_areas.find_one({"id": area_id}, {"_id": 0})
    await create_audit_log(user, "work_area", area_id, "update", before, safe_dict_for_audit(updated))
    return updated


@staff_router.delete("/work-areas/{area_id}")
async def archive_work_area(area_id: str, user: dict = Depends(require_admin)):
    """Archive a work area"""
    existing = await db.work_areas.find_one({"id": area_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Arbeitsbereich")
    
    await db.work_areas.update_one({"id": area_id}, {"$set": {"archived": True, "updated_at": now_iso()}})
    await create_audit_log(user, "work_area", area_id, "archive", safe_dict_for_audit(existing), {"archived": True})
    return {"message": "Arbeitsbereich archiviert", "success": True}


# ============== STAFF MEMBERS ENDPOINTS ==============
@staff_router.get("/members")
async def list_staff_members(
    status: Optional[str] = None,
    work_area_id: Optional[str] = None,
    user: dict = Depends(require_manager)
):
    """List all staff members (filtered by user role)"""
    query = {"archived": False}
    
    # Status-Filter: Mappe "aktiv"/"inaktiv" auf is_active/active Felder
    # Unterstützt: status, active, is_active (für Kompatibilität mit verschiedenen Imports)
    if status:
        if status.lower() == "aktiv":
            # Aktive Mitarbeiter: is_active=true ODER active=true ODER status="aktiv"
            query["$or"] = [
                {"is_active": True},
                {"active": True},
                {"status": "aktiv"}
            ]
        elif status.lower() == "inaktiv":
            query["$or"] = [
                {"is_active": False},
                {"active": False},
                {"status": "inaktiv"}
            ]
        elif status.lower() != "all":
            query["status"] = status
    
    if work_area_id:
        query["work_area_ids"] = work_area_id
    
    members = await db.staff_members.find(query, {"_id": 0}).sort("last_name", 1).to_list(500)
    
    # Filter based on user role
    user_role = user.get("role", "")
    filtered_members = [filter_member_for_role(m, user_role) for m in members]
    
    # Add completeness score for Admin
    if user_role == "admin":
        for member in filtered_members:
            member["completeness"] = calculate_completeness(member)
    
    return filtered_members


@staff_router.get("/members/{member_id}")
async def get_staff_member(member_id: str, user: dict = Depends(require_manager)):
    """Get a single staff member (filtered by user role)"""
    member = await db.staff_members.find_one({"id": member_id, "archived": False}, {"_id": 0})
    if not member:
        raise NotFoundException("Mitarbeiter")
    
    user_role = user.get("role", "")
    filtered = filter_member_for_role(member, user_role)
    
    # Add completeness for Admin
    if user_role == "admin":
        filtered["completeness"] = calculate_completeness(member)
    
    return filtered


@staff_router.post("/members")
async def create_staff_member(
    data: StaffMemberCreate,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_admin)
):
    """Create a new staff member"""
    member = create_entity({
        **data.model_dump(),
        "status": StaffStatus.AKTIV.value,
        "full_name": f"{data.first_name} {data.last_name}"
    })
    await db.staff_members.insert_one(member)
    await create_audit_log(user, "staff_member", member["id"], "create", None, safe_dict_for_audit(member))
    
    return {k: v for k, v in member.items() if k != "_id"}


@staff_router.patch("/members/{member_id}")
async def update_staff_member(member_id: str, data: StaffMemberUpdate, user: dict = Depends(require_admin)):
    """Update a staff member (Admin only for all fields)"""
    existing = await db.staff_members.find_one({"id": member_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Mitarbeiter")
    
    before = safe_dict_for_audit(existing)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now_iso()
    
    # Update full_name if first or last name changed
    first = update_data.get("first_name", existing.get("first_name"))
    last = update_data.get("last_name", existing.get("last_name"))
    update_data["full_name"] = f"{first} {last}"
    
    # Check for status change to "aktiv" with missing required fields
    warnings = []
    if update_data.get("status") == "aktiv" and existing.get("status") != "aktiv":
        merged = {**existing, **update_data}
        completeness = calculate_completeness(merged)
        if completeness["missing_for_active"]:
            warnings.append({
                "type": "incomplete_profile",
                "message": f"Mitarbeiter wird aktiviert, aber folgende Pflichtfelder fehlen: {', '.join(completeness['missing_for_active'])}",
                "missing_fields": completeness["missing_for_active"]
            })
    
    await db.staff_members.update_one({"id": member_id}, {"$set": update_data})
    updated = await db.staff_members.find_one({"id": member_id}, {"_id": 0})
    
    # Special audit logging for sensitive fields
    changed_sensitive = [k for k in AUDIT_SENSITIVE_FIELDS if k in update_data and update_data[k] != existing.get(k)]
    if changed_sensitive:
        await create_audit_log(
            user, "staff_member_hr", member_id, "update_sensitive_fields",
            {k: "***" for k in changed_sensitive},  # Mask old values
            {k: "***" for k in changed_sensitive},  # Mask new values
            metadata={"changed_fields": changed_sensitive, "note": "Sensitive HR data updated"}
        )
    
    await create_audit_log(user, "staff_member", member_id, "update", before, safe_dict_for_audit(updated))
    
    result = {k: v for k, v in updated.items() if k != "_id"}
    result["completeness"] = calculate_completeness(updated)
    if warnings:
        result["warnings"] = warnings
    
    return result


@staff_router.delete("/members/{member_id}")
async def archive_staff_member(member_id: str, user: dict = Depends(require_admin)):
    """Archive a staff member (soft delete)"""
    existing = await db.staff_members.find_one({"id": member_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Mitarbeiter")
    
    await db.staff_members.update_one(
        {"id": member_id}, 
        {"$set": {"archived": True, "status": StaffStatus.INAKTIV.value, "updated_at": now_iso()}}
    )
    await create_audit_log(user, "staff_member", member_id, "archive", safe_dict_for_audit(existing), {"archived": True})
    return {"message": "Mitarbeiter archiviert", "success": True}


# ============== HR FIELDS ENDPOINTS (Sprint 7.1 - Additive) ==============
@staff_router.patch("/members/{member_id}/hr-fields")
async def update_hr_fields(
    member_id: str, 
    data: StaffHRFieldsUpdate, 
    user: dict = Depends(require_admin)
):
    """Update HR fields for a staff member - Admin only with encryption and audit logging"""
    existing = await db.staff_members.find_one({"id": member_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Mitarbeiter")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        return filter_member_for_role(existing, "admin", masked=True)
    
    # Validate fields before encryption
    validation_errors = []
    
    if "tax_id" in update_data and update_data["tax_id"]:
        if not validate_tax_id(update_data["tax_id"]):
            validation_errors.append("Steuer-ID muss 11 Ziffern haben")
    
    if "bank_iban" in update_data and update_data["bank_iban"]:
        if not validate_iban(update_data["bank_iban"]):
            validation_errors.append("Ungültiges IBAN-Format")
    
    if "social_security_number" in update_data and update_data["social_security_number"]:
        if not validate_social_security(update_data["social_security_number"]):
            validation_errors.append("SV-Nummer muss 10-12 Zeichen haben")
    
    if validation_errors:
        raise ValidationException("; ".join(validation_errors))
    
    # Track which sensitive fields are being changed (before encryption)
    changed_sensitive = []
    for field in AUDIT_SENSITIVE_FIELDS:
        if field in update_data:
            existing_decrypted = decrypt_field(existing.get(field, ""))
            if update_data[field] != existing_decrypted:
                changed_sensitive.append(field)
    
    # ENCRYPT high-security fields before storing
    for field in HIGH_SECURITY_FIELDS:
        if field in update_data and update_data[field]:
            update_data[field] = encrypt_field(update_data[field])
    
    update_data["updated_at"] = now_iso()
    
    await db.staff_members.update_one({"id": member_id}, {"$set": update_data})
    updated = await db.staff_members.find_one({"id": member_id}, {"_id": 0})
    
    # Enhanced audit logging for sensitive HR fields (NO cleartext values!)
    if changed_sensitive:
        await create_audit_log(
            user, "staff_member_hr", member_id, "update_sensitive_hr_fields",
            {"fields": changed_sensitive, "values": "[ENCRYPTED]"},
            {"fields": changed_sensitive, "values": "[ENCRYPTED]"},
            metadata={
                "changed_fields": changed_sensitive,
                "staff_name": updated.get("full_name"),
                "note": "Encrypted HR data updated - values not logged",
                "security_level": "HIGH"
            }
        )
    
    # Standard audit log (with sensitive fields masked)
    audit_before = {k: "***MASKED***" if k in HIGH_SECURITY_FIELDS else existing.get(k) for k in update_data.keys()}
    audit_after = {k: "***MASKED***" if k in HIGH_SECURITY_FIELDS else v for k, v in update_data.items()}
    await create_audit_log(user, "staff_member", member_id, "update_hr_fields", audit_before, audit_after)
    
    # Return masked response
    result = filter_member_for_role(updated, "admin", masked=True)
    result["completeness"] = calculate_completeness(updated)
    return result


# NEW: Endpoint to reveal encrypted field (Admin only, with audit)
class RevealFieldRequest(BaseModel):
    field: str = Field(..., description="Field to reveal: tax_id, social_security_number, or bank_iban")
    password: Optional[str] = None  # Optional re-authentication


@staff_router.post("/members/{member_id}/reveal-field")
async def reveal_sensitive_field(
    member_id: str,
    data: RevealFieldRequest,
    user: dict = Depends(require_admin)
):
    """
    Reveal a single encrypted field for Admin view.
    Logged for security audit trail.
    """
    if data.field not in HIGH_SECURITY_FIELDS:
        raise ValidationException(f"Feld '{data.field}' ist kein geschütztes Feld")
    
    member = await db.staff_members.find_one({"id": member_id, "archived": False}, {"_id": 0})
    if not member:
        raise NotFoundException("Mitarbeiter")
    
    encrypted_value = member.get(data.field)
    if not encrypted_value:
        return {"field": data.field, "value": None, "revealed": False}
    
    # Decrypt the field
    decrypted_value = decrypt_field(encrypted_value)
    
    # Audit log this reveal action (IMPORTANT for security compliance)
    await create_audit_log(
        user, "staff_member_hr", member_id, "reveal_sensitive_field",
        {"field": data.field},
        {"field": data.field, "revealed": True},
        metadata={
            "revealed_field": data.field,
            "staff_name": member.get("full_name"),
            "note": "Admin viewed encrypted field in cleartext",
            "security_level": "HIGH"
        }
    )
    
    return {
        "field": data.field,
        "value": decrypted_value,
        "revealed": True,
        "audit_logged": True
    }


@staff_router.get("/members/{member_id}/completeness")
async def get_member_completeness(member_id: str, user: dict = Depends(require_admin)):
    """Get completeness status for a staff member - Admin only"""
    member = await db.staff_members.find_one({"id": member_id, "archived": False}, {"_id": 0})
    if not member:
        raise NotFoundException("Mitarbeiter")
    
    completeness = calculate_completeness(member)
    return {
        "member_id": member_id,
        "member_name": member.get("full_name"),
        "status": member.get("status"),
        **completeness
    }


@staff_router.get("/completeness-overview")
async def get_completeness_overview(user: dict = Depends(require_admin)):
    """Get completeness overview for all active staff members - Admin only"""
    members = await db.staff_members.find(
        {"archived": False, "status": "aktiv"}, 
        {"_id": 0, "id": 1, "full_name": 1, "email": 1, "mobile_phone": 1, "phone": 1, 
         "tax_id": 1, "social_security_number": 1, "bank_iban": 1, "health_insurance": 1,
         "emergency_contact_name": 1, "emergency_contact_phone": 1, "street": 1, "zip_code": 1, "city": 1}
    ).to_list(500)
    
    overview = []
    incomplete_count = 0
    total_score = 0
    
    for member in members:
        completeness = calculate_completeness(member)
        total_score += completeness["score"]
        if completeness["missing_for_active"]:
            incomplete_count += 1
        
        overview.append({
            "id": member["id"],
            "name": member.get("full_name", ""),
            "score": completeness["score"],
            "missing_for_active": completeness["missing_for_active"],
            "is_complete": completeness["is_complete"]
        })
    
    avg_score = total_score / len(members) if members else 0
    
    return {
        "total_active": len(members),
        "incomplete_count": incomplete_count,
        "complete_count": len(members) - incomplete_count,
        "average_score": round(avg_score, 1),
        "members": sorted(overview, key=lambda x: x["score"])
    }


# ============== STAFF DOCUMENTS ENDPOINTS ==============
@staff_router.get("/members/{member_id}/documents")
async def list_staff_documents(member_id: str, user: dict = Depends(require_manager)):
    """List documents for a staff member"""
    # Check member exists
    member = await db.staff_members.find_one({"id": member_id, "archived": False})
    if not member:
        raise NotFoundException("Mitarbeiter")
    
    query = {"staff_member_id": member_id, "archived": False}
    
    # Schichtleiter can only see non-HR-only documents
    if user.get("role") == "schichtleiter":
        query["visibility"] = {"$ne": DocumentVisibility.HR_ONLY.value}
    
    docs = await db.staff_documents.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return docs


@staff_router.post("/members/{member_id}/documents")
async def upload_staff_document(
    member_id: str,
    file: UploadFile = File(...),
    category: str = Form(...),
    visibility: str = Form(default="hr_only"),
    description: str = Form(default=""),
    user: dict = Depends(require_admin)
):
    """Upload a document for a staff member"""
    # Check member exists
    member = await db.staff_members.find_one({"id": member_id, "archived": False})
    if not member:
        raise NotFoundException("Mitarbeiter")
    
    # Validate file
    if not file.filename:
        raise ValidationException("Dateiname fehlt")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationException(f"Dateityp nicht erlaubt. Erlaubt: {', '.join(ALLOWED_EXTENSIONS)}")
    
    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise ValidationException(f"Datei zu groß. Maximum: {MAX_FILE_SIZE // (1024*1024)}MB")
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    storage_filename = f"{file_id}{ext}"
    storage_path = UPLOAD_DIR / member_id
    storage_path.mkdir(parents=True, exist_ok=True)
    file_path = storage_path / storage_filename
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Create document record
    doc = create_entity({
        "staff_member_id": member_id,
        "file_id": file_id,
        "storage_path": str(file_path),
        "original_filename": file.filename,
        "file_size": len(content),
        "mime_type": file.content_type,
        "category": category,
        "visibility": visibility,
        "description": description,
        "uploaded_by": user.get("email")
    })
    
    await db.staff_documents.insert_one(doc)
    await create_audit_log(
        user, "staff_document", doc["id"], "create",
        None, {"staff_member_id": member_id, "filename": file.filename, "category": category}
    )
    
    return {k: v for k, v in doc.items() if k not in ["_id", "storage_path"]}


@staff_router.get("/documents/{doc_id}/download")
async def download_document(doc_id: str, user: dict = Depends(require_manager)):
    """Download a staff document"""
    doc = await db.staff_documents.find_one({"id": doc_id, "archived": False})
    if not doc:
        raise NotFoundException("Dokument")
    
    # Check visibility permissions
    if doc.get("visibility") == DocumentVisibility.HR_ONLY.value and user.get("role") != "admin":
        raise ForbiddenException("Kein Zugriff auf dieses Dokument")
    
    file_path = Path(doc.get("storage_path", ""))
    if not file_path.exists():
        raise NotFoundException("Datei nicht gefunden")
    
    def file_generator():
        with open(file_path, "rb") as f:
            yield from f
    
    return StreamingResponse(
        file_generator(),
        media_type=doc.get("mime_type", "application/octet-stream"),
        headers={"Content-Disposition": f"attachment; filename=\"{doc.get('original_filename', 'document')}\""}
    )


@staff_router.delete("/documents/{doc_id}")
async def archive_document(doc_id: str, user: dict = Depends(require_admin)):
    """Archive a document (soft delete)"""
    doc = await db.staff_documents.find_one({"id": doc_id, "archived": False}, {"_id": 0})
    if not doc:
        raise NotFoundException("Dokument")
    
    await db.staff_documents.update_one(
        {"id": doc_id},
        {"$set": {"archived": True, "archived_at": now_iso(), "updated_at": now_iso()}}
    )
    await create_audit_log(
        user, "staff_document", doc_id, "archive",
        {"filename": doc.get("original_filename")}, {"archived": True}
    )
    return {"message": "Dokument archiviert", "success": True}


# ============== SCHEDULES ENDPOINTS ==============
@staff_router.get("/schedules")
async def list_schedules(
    year: Optional[int] = None,
    status: Optional[str] = None,
    user: dict = Depends(require_manager)
):
    """List schedules"""
    query = {"archived": False}
    if year:
        query["year"] = year
    if status:
        query["status"] = status
    
    schedules = await db.schedules.find(query, {"_id": 0}).sort([("year", -1), ("week", -1)]).to_list(100)
    return schedules


@staff_router.get("/schedules/{schedule_id}")
async def get_schedule(schedule_id: str, user: dict = Depends(require_manager)):
    """Get a schedule with shifts"""
    schedule = await db.schedules.find_one({"id": schedule_id, "archived": False}, {"_id": 0})
    if not schedule:
        raise NotFoundException("Dienstplan")
    
    # Get shifts for this schedule
    shifts = await db.shifts.find({"schedule_id": schedule_id, "archived": False}, {"_id": 0}).to_list(500)
    
    # Get staff members and work areas for enrichment
    staff_ids = list(set(s.get("staff_member_id") for s in shifts if s.get("staff_member_id")))
    area_ids = list(set(s.get("work_area_id") for s in shifts if s.get("work_area_id")))
    
    staff = {s["id"]: s for s in await db.staff_members.find({"id": {"$in": staff_ids}}, {"_id": 0}).to_list(100)}
    areas = {a["id"]: a for a in await db.work_areas.find({"id": {"$in": area_ids}}, {"_id": 0}).to_list(100)}
    
    # Enrich shifts
    for shift in shifts:
        shift["staff_member"] = staff.get(shift.get("staff_member_id"), {})
        shift["work_area"] = areas.get(shift.get("work_area_id"), {})
        shift["hours"] = calculate_shift_hours(shift.get("start_time", "00:00"), shift.get("end_time", "00:00"))
    
    schedule["shifts"] = shifts
    return schedule


@staff_router.post("/schedules")
async def create_schedule(data: ScheduleCreate, user: dict = Depends(require_manager)):
    """Create a new schedule"""
    # Check if schedule for this week already exists
    existing = await db.schedules.find_one({
        "year": data.year,
        "week": data.week,
        "archived": False
    })
    if existing:
        raise ValidationException(f"Dienstplan für KW {data.week}/{data.year} existiert bereits")
    
    week_start, week_end = get_week_dates(data.year, data.week)
    
    schedule = create_entity({
        **data.model_dump(),
        "status": ScheduleStatus.ENTWURF.value,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat()
    })
    
    await db.schedules.insert_one(schedule)
    await create_audit_log(user, "schedule", schedule["id"], "create", None, safe_dict_for_audit(schedule))
    return {k: v for k, v in schedule.items() if k != "_id"}


@staff_router.patch("/schedules/{schedule_id}")
async def update_schedule(schedule_id: str, data: ScheduleUpdate, user: dict = Depends(require_manager)):
    """Update a schedule"""
    existing = await db.schedules.find_one({"id": schedule_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Dienstplan")
    
    # Can't modify archived schedules
    if existing.get("status") == ScheduleStatus.ARCHIVIERT.value:
        raise ValidationException("Archivierte Dienstpläne können nicht bearbeitet werden")
    
    before = safe_dict_for_audit(existing)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now_iso()
    
    await db.schedules.update_one({"id": schedule_id}, {"$set": update_data})
    updated = await db.schedules.find_one({"id": schedule_id}, {"_id": 0})
    await create_audit_log(user, "schedule", schedule_id, "update", before, safe_dict_for_audit(updated))
    return updated


@staff_router.post("/schedules/{schedule_id}/publish")
async def publish_schedule(schedule_id: str, user: dict = Depends(require_manager)):
    """Publish a schedule (make visible to employees)"""
    existing = await db.schedules.find_one({"id": schedule_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Dienstplan")
    
    if existing.get("status") == ScheduleStatus.VEROEFFENTLICHT.value:
        raise ValidationException("Dienstplan ist bereits veröffentlicht")
    
    before = safe_dict_for_audit(existing)
    await db.schedules.update_one(
        {"id": schedule_id},
        {"$set": {
            "status": ScheduleStatus.VEROEFFENTLICHT.value,
            "published_at": now_iso(),
            "published_by": user.get("email"),
            "updated_at": now_iso()
        }}
    )
    
    updated = await db.schedules.find_one({"id": schedule_id}, {"_id": 0})
    await create_audit_log(user, "schedule", schedule_id, "publish", before, safe_dict_for_audit(updated))
    return {"message": "Dienstplan veröffentlicht", "success": True}


@staff_router.post("/schedules/{schedule_id}/archive")
async def archive_schedule(schedule_id: str, user: dict = Depends(require_admin)):
    """Archive a schedule"""
    existing = await db.schedules.find_one({"id": schedule_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Dienstplan")
    
    before = safe_dict_for_audit(existing)
    await db.schedules.update_one(
        {"id": schedule_id},
        {"$set": {
            "status": ScheduleStatus.ARCHIVIERT.value,
            "archived": True,
            "updated_at": now_iso()
        }}
    )
    
    await create_audit_log(user, "schedule", schedule_id, "archive", before, {"status": "archiviert"})
    return {"message": "Dienstplan archiviert", "success": True}


# ============== WOCHE KOPIEREN (Sprint: Dienstplan Live-Ready) ==============
@staff_router.post("/schedules/{schedule_id}/copy")
async def copy_schedule_to_next_week(schedule_id: str, user: dict = Depends(require_manager)):
    """
    Kopiert einen Dienstplan in die nächste Woche.
    Alle Schichten werden mitkopiert, Status ist 'entwurf'.
    """
    # Quell-Schedule laden
    source = await db.schedules.find_one({"id": schedule_id, "archived": False}, {"_id": 0})
    if not source:
        raise NotFoundException("Dienstplan")
    
    # Nächste Woche berechnen
    source_year = source["year"]
    source_week = source["week"]
    
    if source_week >= 52:
        target_year = source_year + 1
        target_week = 1
    else:
        target_year = source_year
        target_week = source_week + 1
    
    target_start, target_end = get_week_dates(target_year, target_week)
    
    # Prüfen ob Ziel-Schedule bereits existiert
    existing_target = await db.schedules.find_one({
        "year": target_year,
        "week": target_week,
        "archived": False
    })
    if existing_target:
        raise ValidationException(f"Dienstplan für KW {target_week}/{target_year} existiert bereits")
    
    # Neuen Schedule erstellen
    new_schedule = create_entity({
        "year": target_year,
        "week": target_week,
        "week_start": target_start.isoformat(),
        "week_end": target_end.isoformat(),
        "status": ScheduleStatus.ENTWURF.value,
        "notes": f"Kopiert von KW {source_week}/{source_year}"
    })
    
    await db.schedules.insert_one(new_schedule)
    
    # Schichten kopieren
    source_shifts = await db.shifts.find({
        "schedule_id": schedule_id,
        "archived": False
    }, {"_id": 0}).to_list(500)
    
    # Tages-Offset berechnen (Differenz zwischen Wochenstart)
    source_start = date.fromisoformat(source["week_start"])
    days_offset = (target_start - source_start).days
    
    copied_count = 0
    for shift in source_shifts:
        # Neues Datum berechnen
        old_date = date.fromisoformat(shift["shift_date"])
        new_date = old_date + timedelta(days=days_offset)
        
        new_shift = create_entity({
            "schedule_id": new_schedule["id"],
            "staff_member_id": shift["staff_member_id"],
            "work_area_id": shift["work_area_id"],
            "shift_date": new_date.isoformat(),
            "start_time": shift["start_time"],
            "end_time": shift["end_time"],
            "hours": shift["hours"],
            "role": shift.get("role"),
            "notes": shift.get("notes")
        })
        
        await db.shifts.insert_one(new_shift)
        copied_count += 1
    
    await create_audit_log(
        user, "schedule", new_schedule["id"], "copy",
        {"source_id": schedule_id, "source_week": f"KW {source_week}/{source_year}"},
        {"target_week": f"KW {target_week}/{target_year}", "shifts_copied": copied_count}
    )
    
    return {
        "message": f"Dienstplan nach KW {target_week}/{target_year} kopiert",
        "success": True,
        "new_schedule_id": new_schedule["id"],
        "shifts_copied": copied_count
    }


# ============== SHIFTS ENDPOINTS ==============
@staff_router.get("/shifts")
async def list_shifts(
    schedule_id: Optional[str] = None,
    staff_member_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: dict = Depends(require_manager)
):
    """List shifts with filters"""
    query = {"archived": False}
    if schedule_id:
        query["schedule_id"] = schedule_id
    if staff_member_id:
        query["staff_member_id"] = staff_member_id
    if date_from:
        query["shift_date"] = {"$gte": date_from}
    if date_to:
        if "shift_date" in query:
            query["shift_date"]["$lte"] = date_to
        else:
            query["shift_date"] = {"$lte": date_to}
    
    shifts = await db.shifts.find(query, {"_id": 0}).sort("shift_date", 1).to_list(500)
    return shifts


# ============== MEINE SCHICHTEN (Sprint: Dienstplan Live-Ready) ==============
@staff_router.get("/my-shifts")
async def get_my_shifts(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Zeigt nur die eigenen Schichten des eingeloggten Mitarbeiters.
    Für alle Rollen verfügbar.
    
    Verknüpfung wird geprüft:
    1. Zuerst über staff_member_id im User-Dokument (explizite Verknüpfung)
    2. Fallback: über Email-Matching (für Kompatibilität)
    
    API SEMANTIK (v2):
    - Returns 200 OK auch wenn kein Mitarbeiterprofil verknüpft
    - Returns 200 OK mit leerer Liste wenn keine Schichten vorhanden
    - Fachliche Zustände sind KEINE HTTP-Fehler
    """
    staff_member = None
    
    # Methode 1: Explizite Verknüpfung über staff_member_id
    staff_member_id = user.get("staff_member_id")
    if staff_member_id:
        staff_member = await db.staff_members.find_one({
            "id": staff_member_id,
            "archived": False
        })
    
    # Methode 2: Fallback - Email-Matching (für Kompatibilität)
    if not staff_member:
        staff_member = await db.staff_members.find_one({
            "email": user.get("email"),
            "archived": False
        })
    
    if not staff_member:
        # Kein Mitarbeiter-Profil gefunden - 200 OK mit Info-Response
        return api_info(
            data=[],
            message="Kein Mitarbeiterprofil verknüpft. Bitte wende dich an die Schichtleitung.",
            error_code=ApiErrorCode.STAFF_NOT_LINKED
        )
    
    query = {
        "staff_member_id": staff_member["id"],
        "archived": False
    }
    
    # Datum-Filter auf korrektem Feld (date statt shift_date)
    if date_from:
        query["date"] = {"$gte": date_from}
    if date_to:
        if "date" in query:
            query["date"]["$lte"] = date_to
        else:
            query["date"] = {"$lte": date_to}
    
    shifts = await db.shifts.find(query, {"_id": 0}).sort("date", 1).to_list(100)
    
    # Bereichsnamen hinzufügen
    work_areas = await db.work_areas.find({"archived": False}, {"_id": 0}).to_list(100)
    area_map = {a["id"]: a for a in work_areas}
    
    for shift in shifts:
        area = area_map.get(shift.get("work_area_id"), {})
        shift["work_area_name"] = area.get("name", shift.get("department", "Unbekannt"))
        shift["work_area_color"] = area.get("color", "#3B82F6")
        # Berechne Stunden wenn nicht vorhanden
        if not shift.get("hours") and shift.get("start_time") and shift.get("end_time"):
            try:
                start = datetime.strptime(shift["start_time"], "%H:%M")
                end = datetime.strptime(shift["end_time"], "%H:%M")
                diff = (end - start).seconds / 3600
                shift["hours"] = round(diff, 1)
            except:
                shift["hours"] = 0
        # shift_date für Frontend-Kompatibilität
        shift["shift_date"] = shift.get("date")
    
    # Return mit einheitlichem API Response Format
    if not shifts:
        return api_info(
            data=[],
            message="Keine Schichten für diesen Zeitraum vorhanden.",
            error_code=ApiErrorCode.NO_SHIFTS_ASSIGNED
        )
    
    return api_success(data=shifts)


@staff_router.post("/shifts")
async def create_shift(data: ShiftCreate, user: dict = Depends(require_manager)):
    """Create a new shift"""
    # Validate schedule exists and is editable
    schedule = await db.schedules.find_one({"id": data.schedule_id, "archived": False})
    if not schedule:
        raise NotFoundException("Dienstplan")
    if schedule.get("status") == ScheduleStatus.ARCHIVIERT.value:
        raise ValidationException("Archivierte Dienstpläne können nicht bearbeitet werden")
    
    # Validate staff member exists
    staff = await db.staff_members.find_one({"id": data.staff_member_id, "archived": False})
    if not staff:
        raise NotFoundException("Mitarbeiter")
    
    # Validate work area exists
    area = await db.work_areas.find_one({"id": data.work_area_id, "archived": False})
    if not area:
        raise NotFoundException("Arbeitsbereich")
    
    # KONFLIKT-PRÜFUNG (Sprint: Dienstplan Live-Ready)
    conflict = await check_shift_conflicts(
        staff_member_id=data.staff_member_id,
        shift_date=data.shift_date,
        start_time=data.start_time,
        end_time=data.end_time
    )
    if conflict["has_conflict"]:
        raise HTTPException(status_code=409, detail=conflict["message"])
    
    # Calculate hours
    hours = calculate_shift_hours(data.start_time, data.end_time)
    
    shift = create_entity({
        **data.model_dump(),
        "hours": hours
    })
    
    await db.shifts.insert_one(shift)
    await create_audit_log(user, "shift", shift["id"], "create", None, safe_dict_for_audit(shift))
    return {k: v for k, v in shift.items() if k != "_id"}


@staff_router.patch("/shifts/{shift_id}")
async def update_shift(shift_id: str, data: ShiftUpdate, user: dict = Depends(require_manager)):
    """Update a shift"""
    existing = await db.shifts.find_one({"id": shift_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Schicht")
    
    # Check schedule is editable
    schedule = await db.schedules.find_one({"id": existing.get("schedule_id"), "archived": False})
    if schedule and schedule.get("status") == ScheduleStatus.ARCHIVIERT.value:
        raise ValidationException("Archivierte Dienstpläne können nicht bearbeitet werden")
    
    before = safe_dict_for_audit(existing)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    # Recalculate hours if times changed
    start = update_data.get("start_time", existing.get("start_time"))
    end = update_data.get("end_time", existing.get("end_time"))
    shift_date = update_data.get("shift_date", existing.get("shift_date"))
    staff_member_id = update_data.get("staff_member_id", existing.get("staff_member_id"))
    
    # KONFLIKT-PRÜFUNG bei Änderung von MA, Datum oder Zeiten (Sprint: Dienstplan Live-Ready)
    if any(k in update_data for k in ["staff_member_id", "shift_date", "start_time", "end_time"]):
        conflict = await check_shift_conflicts(
            staff_member_id=staff_member_id,
            shift_date=shift_date,
            start_time=start,
            end_time=end,
            exclude_shift_id=shift_id
        )
        if conflict["has_conflict"]:
            raise HTTPException(status_code=409, detail=conflict["message"])
    
    update_data["hours"] = calculate_shift_hours(start, end)
    update_data["updated_at"] = now_iso()
    
    await db.shifts.update_one({"id": shift_id}, {"$set": update_data})
    updated = await db.shifts.find_one({"id": shift_id}, {"_id": 0})
    await create_audit_log(user, "shift", shift_id, "update", before, safe_dict_for_audit(updated))
    return updated


@staff_router.delete("/shifts/{shift_id}")
async def delete_shift(shift_id: str, user: dict = Depends(require_manager)):
    """Delete a shift"""
    existing = await db.shifts.find_one({"id": shift_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Schicht")
    
    # Check schedule is editable
    schedule = await db.schedules.find_one({"id": existing.get("schedule_id"), "archived": False})
    if schedule and schedule.get("status") == ScheduleStatus.ARCHIVIERT.value:
        raise ValidationException("Schichten in archivierten Dienstplänen können nicht gelöscht werden")
    
    await db.shifts.update_one({"id": shift_id}, {"$set": {"archived": True, "updated_at": now_iso()}})
    await create_audit_log(user, "shift", shift_id, "archive", safe_dict_for_audit(existing), {"archived": True})
    return {"message": "Schicht gelöscht", "success": True}


# ============== HOURS OVERVIEW ==============
@staff_router.get("/hours-overview")
async def get_hours_overview(
    year: int,
    week: int,
    user: dict = Depends(require_manager)
):
    """Get Soll/Ist hours overview for a week"""
    week_start, week_end = get_week_dates(year, week)
    
    # Get all active staff members - Support both status AND is_active fields
    staff_members = await db.staff_members.find({
        "archived": False, 
        "$or": [
            {"status": "aktiv"},
            {"is_active": True},
            {"status": {"$exists": False}, "is_active": {"$exists": False}}  # Fallback
        ]
    }, {"_id": 0}).to_list(500)
    
    # Get all work areas for name resolution
    work_areas = await db.work_areas.find({"archived": {"$ne": True}}, {"_id": 0}).to_list(100)
    work_area_map = {a["id"]: a["name"] for a in work_areas}
    
    # Helper: Calculate hours from start_time and end_time strings
    def calc_hours_from_times(start_time: str, end_time: str) -> float:
        """Calculate hours between two time strings (HH:MM format)"""
        try:
            if not start_time or not end_time:
                return 0
            start_h, start_m = map(int, start_time.split(":"))
            end_h, end_m = map(int, end_time.split(":"))
            return (end_h * 60 + end_m - start_h * 60 - start_m) / 60
        except:
            return 0
    
    # Get all shifts for this week
    shifts = await db.shifts.find({
        "shift_date": {"$gte": week_start.isoformat(), "$lte": week_end.isoformat()},
        "archived": False
    }, {"_id": 0}).to_list(1000)
    
    # Calculate hours per staff member
    overview = []
    for member in staff_members:
        member_shifts = [s for s in shifts if s.get("staff_member_id") == member.get("id")]
        
        # Calculate planned hours: use hours field OR calculate from times
        planned_hours = 0
        for s in member_shifts:
            if s.get("hours"):
                planned_hours += s.get("hours", 0)
            else:
                planned_hours += calc_hours_from_times(s.get("start_time"), s.get("end_time"))
        
        weekly_hours = member.get("weekly_hours", 0) or 0
        
        # Resolve work area name from work_area_id or work_area_ids
        work_area_id = member.get("work_area_id")
        work_area_ids = member.get("work_area_ids", [])
        work_area_name = "—"
        
        # Prioritize single work_area_id, fall back to work_area_ids array
        if work_area_id:
            work_area_name = work_area_map.get(work_area_id, "—")
        elif work_area_ids and len(work_area_ids) > 0:
            work_area_name = work_area_map.get(work_area_ids[0], "—")
        
        # Use work_area_id for KPI (single value)
        effective_work_area_id = work_area_id or (work_area_ids[0] if work_area_ids else None)
        
        # Resolve display name: name > full_name > first_name + last_name
        display_name = member.get("name") or member.get("full_name")
        if not display_name:
            fn = member.get("first_name", "")
            ln = member.get("last_name", "")
            display_name = f"{fn} {ln}".strip() if fn or ln else "N.N."
        
        # KPI-Vorbereitung: work_area_id für spätere Bereichs-Auswertungen
        # TODO: Hier können später Bereichs-KPIs aggregiert werden
        overview.append({
            "staff_member_id": member.get("id"),
            "name": display_name,
            "first_name": member.get("first_name", ""),
            "last_name": member.get("last_name", ""),
            "work_area": work_area_name,  # NEU: Bereich für Anzeige
            "work_area_id": effective_work_area_id,  # NEU: ID für KPI
            "employment_type": member.get("employment_type"),
            "weekly_hours_target": weekly_hours,
            "planned_hours": round(planned_hours, 2),
            "difference": round(planned_hours - weekly_hours, 2),
            "shift_count": len(member_shifts)
        })
    
    # Bereichs-Aggregation (Service / Küche / Sonstige)
    area_summary = {}
    for o in overview:
        area = o.get("work_area", "Sonstige")
        if area not in area_summary:
            area_summary[area] = {
                "area": area,
                "target_hours": 0,
                "planned_hours": 0,
                "difference": 0,
                "staff_count": 0,
                "shift_count": 0
            }
        area_summary[area]["target_hours"] += o["weekly_hours_target"]
        area_summary[area]["planned_hours"] += o["planned_hours"]
        area_summary[area]["difference"] += o["difference"]
        area_summary[area]["staff_count"] += 1
        area_summary[area]["shift_count"] += o["shift_count"]
    
    # Runden der Bereichs-Summen
    for area in area_summary:
        area_summary[area]["target_hours"] = round(area_summary[area]["target_hours"], 2)
        area_summary[area]["planned_hours"] = round(area_summary[area]["planned_hours"], 2)
        area_summary[area]["difference"] = round(area_summary[area]["difference"], 2)
    
    return {
        "year": year,
        "week": week,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "overview": overview,
        "total_planned": round(sum(o["planned_hours"] for o in overview), 2),
        "total_target": round(sum(o["weekly_hours_target"] for o in overview), 2),
        "area_summary": list(area_summary.values())  # NEU: Bereichs-Summen
    }


# ============== EXPORTS ==============
@staff_router.get("/export/schedule/{schedule_id}/pdf")
async def export_schedule_pdf(schedule_id: str, user: dict = Depends(require_manager)):
    """Export schedule as PDF"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    
    schedule = await db.schedules.find_one({"id": schedule_id, "archived": False}, {"_id": 0})
    if not schedule:
        raise NotFoundException("Dienstplan")
    
    shifts = await db.shifts.find({"schedule_id": schedule_id, "archived": False}, {"_id": 0}).to_list(500)
    
    # Get staff and areas
    staff_ids = list(set(s.get("staff_member_id") for s in shifts))
    area_ids = list(set(s.get("work_area_id") for s in shifts))
    staff = {s["id"]: s for s in await db.staff_members.find({"id": {"$in": staff_ids}}, {"_id": 0}).to_list(100)}
    areas = {a["id"]: a for a in await db.work_areas.find({"id": {"$in": area_ids}}, {"_id": 0}).to_list(100)}
    
    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=1*cm, bottomMargin=1*cm)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, alignment=1)
    elements.append(Paragraph(f"Dienstplan KW {schedule.get('week')}/{schedule.get('year')}", title_style))
    elements.append(Paragraph(f"{schedule.get('week_start')} - {schedule.get('week_end')}", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Group shifts by date
    days = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    week_start = datetime.fromisoformat(schedule.get("week_start"))
    
    # Table header
    header = ["Mitarbeiter"] + [f"{days[i]}\n{(week_start + timedelta(days=i)).strftime('%d.%m.')}" for i in range(7)]
    
    # Build table data
    table_data = [header]
    for staff_id, staff_info in staff.items():
        row = [staff_info.get("full_name", "")]
        for i in range(7):
            day_date = (week_start + timedelta(days=i)).strftime("%Y-%m-%d")
            day_shifts = [s for s in shifts if s.get("staff_member_id") == staff_id and s.get("shift_date") == day_date]
            if day_shifts:
                shift_texts = []
                for s in day_shifts:
                    area_name = areas.get(s.get("work_area_id"), {}).get("name", "")
                    shift_texts.append(f"{s.get('start_time')}-{s.get('end_time')}\n{area_name}")
                row.append("\n".join(shift_texts))
            else:
                row.append("-")
        table_data.append(row)
    
    # Create table
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0, 0.18, 0.01)),  # GastroCore green
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=dienstplan_kw{schedule.get('week')}_{schedule.get('year')}.pdf"}
    )


@staff_router.get("/export/staff/csv")
async def export_staff_csv(user: dict = Depends(require_admin)):
    """Export staff members as CSV"""
    staff = await db.staff_members.find({"archived": False}, {"_id": 0}).to_list(500)
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["ID", "Vorname", "Nachname", "E-Mail", "Telefon", "Rolle", "Beschäftigungsart", "Sollstunden", "Eintrittsdatum", "Status"])
    
    for s in staff:
        writer.writerow([
            s.get("id"),
            s.get("first_name"),
            s.get("last_name"),
            s.get("email", ""),
            s.get("phone", ""),
            s.get("role"),
            s.get("employment_type"),
            s.get("weekly_hours"),
            s.get("entry_date"),
            s.get("status")
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=mitarbeiter.csv"}
    )


@staff_router.get("/export/shifts/csv")
async def export_shifts_csv(
    year: int,
    week: int,
    user: dict = Depends(require_manager)
):
    """Export shifts as CSV"""
    week_start, week_end = get_week_dates(year, week)
    
    shifts = await db.shifts.find({
        "shift_date": {"$gte": week_start.isoformat(), "$lte": week_end.isoformat()},
        "archived": False
    }, {"_id": 0}).to_list(1000)
    
    # Get staff and areas
    staff_ids = list(set(s.get("staff_member_id") for s in shifts))
    area_ids = list(set(s.get("work_area_id") for s in shifts))
    staff = {s["id"]: s for s in await db.staff_members.find({"id": {"$in": staff_ids}}, {"_id": 0}).to_list(100)}
    areas = {a["id"]: a for a in await db.work_areas.find({"id": {"$in": area_ids}}, {"_id": 0}).to_list(100)}
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["Datum", "Mitarbeiter", "Bereich", "Von", "Bis", "Stunden", "Rolle"])
    
    for s in sorted(shifts, key=lambda x: (x.get("shift_date"), x.get("start_time"))):
        staff_name = staff.get(s.get("staff_member_id"), {}).get("full_name", "")
        area_name = areas.get(s.get("work_area_id"), {}).get("name", "")
        writer.writerow([
            s.get("shift_date"),
            staff_name,
            area_name,
            s.get("start_time"),
            s.get("end_time"),
            s.get("hours"),
            s.get("role")
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=schichten_kw{week}_{year}.csv"}
    )


# ============== WELCOME EMAIL ==============
@staff_router.post("/members/{member_id}/send-welcome")
async def send_welcome_email(
    member_id: str,
    data: WelcomeEmailRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_admin)
):
    """Send welcome email to staff member"""
    member = await db.staff_members.find_one({"id": member_id, "archived": False}, {"_id": 0})
    if not member:
        raise NotFoundException("Mitarbeiter")
    
    if not member.get("email"):
        raise ValidationException("Mitarbeiter hat keine E-Mail-Adresse")
    
    # Import email service
    from email_service import send_email_template
    
    # Prepare template data
    templates = {
        "de": {
            "subject": "Willkommen bei GastroCore!",
            "greeting": f"Hallo {member.get('first_name')}",
            "body": """
Herzlich willkommen im Team!

Ihr Account wurde angelegt. Sie können sich ab sofort im System anmelden.

Bei Fragen wenden Sie sich bitte an Ihren Schichtleiter.

Mit freundlichen Grüßen,
Ihr GastroCore Team
"""
        },
        "en": {
            "subject": "Welcome to GastroCore!",
            "greeting": f"Hello {member.get('first_name')}",
            "body": """
Welcome to the team!

Your account has been created. You can now log in to the system.

If you have any questions, please contact your shift manager.

Best regards,
Your GastroCore Team
"""
        },
        "pl": {
            "subject": "Witamy w GastroCore!",
            "greeting": f"Cześć {member.get('first_name')}",
            "body": """
Witamy w zespole!

Twoje konto zostało utworzone. Możesz teraz zalogować się do systemu.

W razie pytań skontaktuj się z kierownikiem zmiany.

Z poważaniem,
Zespół GastroCore
"""
        }
    }
    
    lang = data.language
    template = templates.get(lang, templates["de"])
    
    # Log the attempt
    email_log = create_entity({
        "type": "welcome_email",
        "recipient": member.get("email"),
        "staff_member_id": member_id,
        "language": lang,
        "status": "pending"
    })
    await db.message_logs.insert_one(email_log)
    
    try:
        # Send email (using existing email service)
        await send_email_template(
            to_email=member.get("email"),
            subject=template["subject"],
            body=f"{template['greeting']}\n{template['body']}"
        )
        
        # Update log
        await db.message_logs.update_one(
            {"id": email_log["id"]},
            {"$set": {"status": "sent", "sent_at": now_iso()}}
        )
        
        await create_audit_log(
            user, "staff_member", member_id, "welcome_email_sent",
            None, {"email": member.get("email"), "language": lang}
        )
        
        return {"message": "Begrüßungs-E-Mail gesendet", "success": True}
        
    except Exception as e:
        logger.error(f"Failed to send welcome email: {e}")
        await db.message_logs.update_one(
            {"id": email_log["id"]},
            {"$set": {"status": "failed", "error": str(e)}}
        )
        raise HTTPException(status_code=500, detail=f"E-Mail-Versand fehlgeschlagen: {str(e)}")


# ============== SEED DEFAULT DATA ==============
async def seed_work_areas():
    """Seed default work areas"""
    existing = await db.work_areas.count_documents({"archived": False})
    if existing > 0:
        return {"message": "Arbeitsbereiche bereits vorhanden", "seeded": False}
    
    defaults = [
        {"name": "Service", "color": "#10b981", "sort_order": 1, "description": "Servicebereich Restaurant"},
        {"name": "Küche", "color": "#f59e0b", "sort_order": 2, "description": "Küche und Zubereitung"},
        {"name": "Bar", "color": "#8b5cf6", "sort_order": 3, "description": "Bar und Getränke"},
        {"name": "Event", "color": "#ec4899", "sort_order": 4, "description": "Veranstaltungen und Events"},
    ]
    
    for area_data in defaults:
        area = create_entity({**area_data, "is_active": True})
        await db.work_areas.insert_one(area)
    
    return {"message": "Standard-Arbeitsbereiche erstellt", "seeded": True, "count": len(defaults)}


async def seed_sample_staff():
    """Seed sample staff members"""
    existing = await db.staff_members.count_documents({"archived": False})
    if existing > 0:
        return {"message": "Mitarbeiter bereits vorhanden", "seeded": False}
    
    # Get work areas
    areas = await db.work_areas.find({"archived": False}, {"_id": 0}).to_list(10)
    service_area = next((a for a in areas if a.get("name") == "Service"), None)
    kitchen_area = next((a for a in areas if a.get("name") == "Küche"), None)
    
    defaults = [
        {
            "first_name": "Max",
            "last_name": "Mustermann",
            "email": "max@example.de",
            "phone": "+49 170 1234567",
            "role": "schichtleiter",
            "employment_type": "vollzeit",
            "weekly_hours": 40.0,
            "entry_date": "2023-01-15",
            "work_area_ids": [service_area["id"]] if service_area else [],
            "status": "aktiv"
        },
        {
            "first_name": "Anna",
            "last_name": "Schmidt",
            "email": "anna@example.de",
            "phone": "+49 171 2345678",
            "role": "service",
            "employment_type": "teilzeit",
            "weekly_hours": 25.0,
            "entry_date": "2023-06-01",
            "work_area_ids": [service_area["id"]] if service_area else [],
            "status": "aktiv"
        },
        {
            "first_name": "Thomas",
            "last_name": "Koch",
            "email": "thomas@example.de",
            "phone": "+49 172 3456789",
            "role": "kueche",
            "employment_type": "vollzeit",
            "weekly_hours": 40.0,
            "entry_date": "2022-03-01",
            "work_area_ids": [kitchen_area["id"]] if kitchen_area else [],
            "status": "aktiv"
        },
    ]
    
    for staff_data in defaults:
        staff = create_entity({
            **staff_data,
            "full_name": f"{staff_data['first_name']} {staff_data['last_name']}"
        })
        await db.staff_members.insert_one(staff)
    
    return {"message": "Beispiel-Mitarbeiter erstellt", "seeded": True, "count": len(defaults)}



# ============== SHIFT TEMPLATES MODULE (Sprint: Dienstplan Service live-tauglich) ==============

class EndTimeType(str, Enum):
    FIXED = "fixed"
    CLOSE_PLUS_MINUTES = "close_plus_minutes"

class EventMode(str, Enum):
    NORMAL = "normal"
    KULTUR = "kultur"

class SeasonType(str, Enum):
    SUMMER = "summer"
    WINTER = "winter"
    ALL = "all"

class DayType(str, Enum):
    WEEKDAY = "weekday"
    WEEKEND = "weekend"
    ALL = "all"

class DepartmentType(str, Enum):
    SERVICE = "service"
    KITCHEN = "kitchen"
    REINIGUNG = "reinigung"
    KUECHE = "Küche"  # Alias für Kompatibilität


class ShiftTemplateCreate(BaseModel):
    department: DepartmentType
    name: str = Field(..., min_length=2, max_length=50)
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")  # HH:MM
    end_time_type: EndTimeType
    end_time_fixed: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")  # HH:MM if fixed
    close_plus_minutes: Optional[int] = Field(None, ge=0, le=120)  # if close_plus_minutes
    season: SeasonType = SeasonType.ALL
    day_type: DayType = DayType.ALL
    event_mode: EventMode = EventMode.NORMAL  # Normal oder Kulturabend
    headcount_default: int = Field(default=1, ge=1, le=10)
    active: bool = True
    sort_order: int = Field(default=0)


class ShiftTemplateUpdate(BaseModel):
    department: Optional[DepartmentType] = None
    name: Optional[str] = None
    start_time: Optional[str] = None
    end_time_type: Optional[EndTimeType] = None
    end_time_fixed: Optional[str] = None
    close_plus_minutes: Optional[int] = None
    season: Optional[SeasonType] = None
    day_type: Optional[DayType] = None
    event_mode: Optional[EventMode] = None
    headcount_default: Optional[int] = None
    active: Optional[bool] = None
    sort_order: Optional[int] = None


class ApplyTemplatesRequest(BaseModel):
    schedule_id: str
    departments: List[DepartmentType] = [DepartmentType.SERVICE]
    season: Optional[SeasonType] = None  # None = auto-detect from opening hours

class ApplyTemplatesBody(BaseModel):
    """Request body für /schedules/{schedule_id}/apply-templates (schedule_id kommt aus URL)"""
    departments: List[DepartmentType] = [DepartmentType.SERVICE]
    season: Optional[SeasonType] = None  # None = auto-detect from opening hours
    

# ----- SHIFT TEMPLATES ENDPOINTS -----

@staff_router.get("/shift-templates")
async def list_shift_templates(
    department: Optional[DepartmentType] = None,
    season: Optional[SeasonType] = None,
    active_only: bool = True,
    user: dict = Depends(require_manager)
):
    """List all shift templates"""
    query = {"archived": False}
    if department:
        query["department"] = department.value
    if season:
        query["season"] = {"$in": [season.value, "all"]}
    if active_only:
        # Support both "active" and "is_active" fields
        query["$or"] = [{"active": True}, {"is_active": True}]
    
    templates = await db.shift_templates.find(query, {"_id": 0}).sort("sort_order", 1).to_list(100)
    return templates


@staff_router.get("/shift-templates/{template_id}")
async def get_shift_template(template_id: str, user: dict = Depends(require_manager)):
    """Get a single shift template"""
    template = await db.shift_templates.find_one({"id": template_id, "archived": False}, {"_id": 0})
    if not template:
        raise NotFoundException("Schicht-Vorlage")
    return template


@staff_router.post("/shift-templates")
async def create_shift_template(data: ShiftTemplateCreate, user: dict = Depends(require_admin)):
    """Create a new shift template"""
    # Validate end_time config
    if data.end_time_type == EndTimeType.FIXED and not data.end_time_fixed:
        raise ValidationException("end_time_fixed ist erforderlich wenn end_time_type = fixed")
    if data.end_time_type == EndTimeType.CLOSE_PLUS_MINUTES and data.close_plus_minutes is None:
        raise ValidationException("close_plus_minutes ist erforderlich wenn end_time_type = close_plus_minutes")
    
    template = create_entity(data.model_dump())
    await db.shift_templates.insert_one(template)
    await create_audit_log(user, "shift_template", template["id"], "create", None, safe_dict_for_audit(template))
    return {k: v for k, v in template.items() if k != "_id"}


@staff_router.put("/shift-templates/{template_id}")
async def update_shift_template(template_id: str, data: ShiftTemplateUpdate, user: dict = Depends(require_admin)):
    """Update a shift template"""
    existing = await db.shift_templates.find_one({"id": template_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Schicht-Vorlage")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        return existing
    
    update_data["updated_at"] = now_iso()
    
    # Validate if changing end_time_type
    merged = {**existing, **update_data}
    if merged.get("end_time_type") == "fixed" and not merged.get("end_time_fixed"):
        raise ValidationException("end_time_fixed ist erforderlich wenn end_time_type = fixed")
    if merged.get("end_time_type") == "close_plus_minutes" and merged.get("close_plus_minutes") is None:
        raise ValidationException("close_plus_minutes ist erforderlich wenn end_time_type = close_plus_minutes")
    
    before = safe_dict_for_audit(existing)
    await db.shift_templates.update_one({"id": template_id}, {"$set": update_data})
    updated = await db.shift_templates.find_one({"id": template_id}, {"_id": 0})
    await create_audit_log(user, "shift_template", template_id, "update", before, safe_dict_for_audit(updated))
    return updated


@staff_router.delete("/shift-templates/{template_id}")
async def delete_shift_template(template_id: str, user: dict = Depends(require_admin)):
    """Archive a shift template"""
    existing = await db.shift_templates.find_one({"id": template_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Schicht-Vorlage")
    
    await db.shift_templates.update_one({"id": template_id}, {"$set": {"archived": True, "updated_at": now_iso()}})
    await create_audit_log(user, "shift_template", template_id, "archive", safe_dict_for_audit(existing), {"archived": True})
    return {"message": "Vorlage gelöscht", "success": True}


@staff_router.post("/shift-templates/apply")
async def apply_templates_to_current_week(user: dict = Depends(require_manager)):
    """
    Apply all active shift templates to the current week.
    Creates a new schedule if none exists, then applies templates.
    """
    # Get current ISO week
    today = date.today()
    iso_year, iso_week, _ = today.isocalendar()
    
    # Find or create schedule for current week
    schedule = await db.schedules.find_one({
        "year": iso_year,
        "week": iso_week,
        "archived": {"$ne": True}
    })
    
    if not schedule:
        # Calculate week dates
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        schedule = {
            "id": str(uuid.uuid4()),
            "year": iso_year,
            "week": iso_week,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "status": "draft",
            "notes": "Auto-generiert durch Vorlagen-Anwendung",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "archived": False
        }
        await db.schedules.insert_one(schedule)
    
    schedule_id = schedule["id"]
    
    # Apply templates using existing function
    from staff_module import ApplyTemplatesRequest, DepartmentType
    request = ApplyTemplatesRequest(
        schedule_id=schedule_id,
        departments=[DepartmentType.SERVICE, DepartmentType.KITCHEN]
    )
    
    result = await apply_templates_to_schedule(schedule_id, request, user)
    result["schedule_id"] = schedule_id
    result["week"] = iso_week
    result["year"] = iso_year
    
    return result


@staff_router.post("/shift-templates/seed-defaults")
async def seed_default_templates(user: dict = Depends(require_admin)):
    """Seed default Carlsburg shift templates - Normal + Kulturabend Varianten"""
    # Check if templates already exist
    existing = await db.shift_templates.count_documents({"archived": False})
    if existing > 0:
        return {"message": "Vorlagen existieren bereits", "seeded": False, "count": existing}
    
    default_templates = [
        # ============ NORMALBETRIEB ============
        # Service - Normal
        {"department": "service", "name": "Service Früh", "start_time": "10:00", "end_time_type": "fixed", "end_time_fixed": "15:00", "season": "all", "day_type": "all", "event_mode": "normal", "headcount_default": 1, "sort_order": 10},
        {"department": "service", "name": "Service Spät", "start_time": "17:00", "end_time_type": "close_plus_minutes", "close_plus_minutes": 30, "season": "all", "day_type": "all", "event_mode": "normal", "headcount_default": 2, "sort_order": 11},
        
        # Küche - Normal (KEIN fixes 22:00!)
        {"department": "kitchen", "name": "Küche Früh", "start_time": "09:00", "end_time_type": "fixed", "end_time_fixed": "15:00", "season": "all", "day_type": "all", "event_mode": "normal", "headcount_default": 1, "sort_order": 20},
        {"department": "kitchen", "name": "Küche Spät", "start_time": "16:00", "end_time_type": "close_plus_minutes", "close_plus_minutes": 30, "season": "all", "day_type": "all", "event_mode": "normal", "headcount_default": 1, "sort_order": 21},
        
        # Schichtleiter - Normal  
        {"department": "service", "name": "Schichtleiter", "start_time": "11:00", "end_time_type": "close_plus_minutes", "close_plus_minutes": 0, "season": "all", "day_type": "all", "event_mode": "normal", "headcount_default": 1, "sort_order": 30},
        
        # Reinigung - Normal
        {"department": "reinigung", "name": "Reinigung", "start_time": "06:00", "end_time_type": "fixed", "end_time_fixed": "10:00", "season": "all", "day_type": "all", "event_mode": "normal", "headcount_default": 1, "sort_order": 40},
        
        # ============ KULTURABEND (bis 00:00) ============
        # Service - Kulturabend
        {"department": "service", "name": "Service Spät Kultur", "start_time": "17:00", "end_time_type": "fixed", "end_time_fixed": "00:00", "season": "all", "day_type": "all", "event_mode": "kultur", "headcount_default": 3, "sort_order": 110},
        
        # Küche - Kulturabend
        {"department": "kitchen", "name": "Küche Spät Kultur", "start_time": "16:00", "end_time_type": "fixed", "end_time_fixed": "00:00", "season": "all", "day_type": "all", "event_mode": "kultur", "headcount_default": 2, "sort_order": 120},
        
        # Schichtleiter - Kulturabend
        {"department": "service", "name": "Schichtleiter Kultur", "start_time": "11:00", "end_time_type": "fixed", "end_time_fixed": "00:00", "season": "all", "day_type": "all", "event_mode": "kultur", "headcount_default": 1, "sort_order": 130},
    ]
    
    for tpl_data in default_templates:
        tpl = create_entity({**tpl_data, "active": True})
        await db.shift_templates.insert_one(tpl)
    
    await create_audit_log(user, "shift_template", "seed", "seed_defaults", None, {"count": len(default_templates)})
    return {"message": "Carlsburg-Vorlagen erstellt (Normal + Kulturabend)", "seeded": True, "count": len(default_templates)}


# ----- APPLY TEMPLATES TO SCHEDULE -----

async def get_closing_time_for_date(date_str: str) -> Optional[str]:
    """Get closing time for a specific date from opening hours"""
    try:
        # Try to get from opening-hours effective
        from datetime import datetime
        day = await db.opening_hours_periods.find_one({"archived": False}, {"_id": 0})
        if not day:
            return "20:00"  # Default fallback
        
        # Get effective hours for the date
        # This is a simplified version - in production, use the full opening-hours logic
        dt = datetime.fromisoformat(date_str)
        weekday = dt.weekday()
        
        # Check closures first
        closure = await db.closures.find_one({
            "date": date_str,
            "archived": False
        }, {"_id": 0})
        if closure and closure.get("full_day"):
            return None  # Closed
        
        # Get opening hours for this weekday
        hours = await db.opening_hours_periods.find_one({
            "archived": False,
            "is_active": True
        }, {"_id": 0})
        
        if hours and hours.get("days"):
            day_config = hours["days"].get(str(weekday))
            if day_config and day_config.get("blocks"):
                last_block = day_config["blocks"][-1]
                return last_block.get("end", "20:00")
        
        return "20:00"  # Default
    except Exception as e:
        logger.warning(f"Could not get closing time for {date_str}: {e}")
        return "20:00"


def calculate_end_time(template: dict, closing_time: str) -> str:
    """Calculate actual end time based on template config"""
    if template.get("end_time_type") == "fixed":
        return template.get("end_time_fixed", "18:00")
    else:
        # close_plus_minutes
        from datetime import datetime, timedelta
        close_dt = datetime.strptime(closing_time, "%H:%M")
        plus_mins = template.get("close_plus_minutes", 30)
        end_dt = close_dt + timedelta(minutes=plus_mins)
        return end_dt.strftime("%H:%M")


def is_weekend(date_str: str) -> bool:
    """Check if date is weekend (Sat/Sun)"""
    from datetime import datetime
    dt = datetime.fromisoformat(date_str)
    return dt.weekday() >= 5  # 5=Saturday, 6=Sunday


async def get_current_season() -> str:
    """Determine current season from opening hours periods"""
    try:
        period = await db.opening_hours_periods.find_one({
            "archived": False,
            "is_active": True
        }, {"_id": 0})
        if period:
            name = period.get("name", "").lower()
            if "winter" in name:
                return "winter"
            elif "sommer" in name or "summer" in name:
                return "summer"
        return "summer"  # Default
    except:
        return "summer"


@staff_router.post("/schedules/{schedule_id}/apply-templates")
async def apply_templates_to_schedule(
    schedule_id: str,
    data: ApplyTemplatesBody,
    user: dict = Depends(require_manager)
):
    """
    Apply shift templates to a schedule.
    Creates shifts based on templates for each day of the week.
    """
    # Get schedule
    schedule = await db.schedules.find_one({"id": schedule_id, "archived": False}, {"_id": 0})
    if not schedule:
        raise NotFoundException("Dienstplan")
    
    if schedule.get("status") == ScheduleStatus.ARCHIVIERT.value:
        raise ValidationException("Archivierte Dienstpläne können nicht bearbeitet werden")
    
    # Determine season
    season = data.season.value if data.season else await get_current_season()
    
    # Get matching templates
    dept_values = [d.value for d in data.departments]
    
    # Flexible Template-Query: Unterstützt sowohl alte als auch neue Feldnamen
    # Verwende $and um beide $or-Bedingungen zu kombinieren
    templates = await db.shift_templates.find({
        "department": {"$in": dept_values},
        "$and": [
            {"$or": [
                {"season": {"$in": [season, "all"]}},
                {"season": {"$exists": False}},  # Templates ohne season-Feld
            ]},
            {"$or": [
                {"active": True},
                {"is_active": True},  # Alternative Feldname
                {"active": {"$exists": False}},  # Kein active-Feld = aktiv
            ]}
        ],
        "archived": {"$ne": True}
    }, {"_id": 0}).to_list(100)
    
    # Fallback: Wenn keine Templates gefunden, versuche ohne Filter
    if not templates:
        templates = await db.shift_templates.find({
            "department": {"$in": dept_values},
            "archived": {"$ne": True}
        }, {"_id": 0}).to_list(100)
    
    # Weiterer Fallback: Alle aktiven Templates (unabhängig von department)
    if not templates:
        templates = await db.shift_templates.find({
            "archived": {"$ne": True},
            "$or": [
                {"active": True},
                {"is_active": True},
                {"active": {"$exists": False}}
            ]
        }, {"_id": 0}).to_list(100)
    
    if not templates:
        return {"message": "Keine passenden Vorlagen gefunden", "created": 0}
    
    # Get work areas for mapping department -> work_area_id
    areas = await db.work_areas.find({"archived": False}, {"_id": 0}).to_list(50)
    service_area = next((a for a in areas if "service" in a.get("name", "").lower()), None)
    kitchen_area = next((a for a in areas if "küche" in a.get("name", "").lower() or "kitchen" in a.get("name", "").lower()), None)
    
    def get_area_id(department: str) -> str:
        if department == "service" and service_area:
            return service_area["id"]
        elif department == "kitchen" and kitchen_area:
            return kitchen_area["id"]
        return service_area["id"] if service_area else ""
    
    # Get week dates - Support both start_date and week_start
    week_start_str = schedule.get("start_date") or schedule.get("week_start")
    
    # FALLBACK: Wenn start_date fehlt, berechne es aus year/week
    if not week_start_str:
        year = schedule.get("year")
        week = schedule.get("week")
        if year and week:
            week_start, _ = get_week_dates(year, week)
            week_start_str = week_start.isoformat()
            # Update schedule mit den berechneten Daten
            _, week_end = get_week_dates(year, week)
            await db.schedules.update_one(
                {"id": schedule.get("id")},
                {"$set": {
                    "start_date": week_start_str,
                    "end_date": week_end.isoformat(),
                    "week_start": week_start_str,
                    "week_end": week_end.isoformat()
                }}
            )
        else:
            raise ValidationException("Schedule hat weder start_date noch year/week")
    
    week_start = datetime.fromisoformat(week_start_str).date()
    created_shifts = []
    skipped_existing = 0
    
    for day_offset in range(7):
        current_date = week_start + timedelta(days=day_offset)
        date_str = current_date.isoformat()
        is_wknd = current_date.weekday() >= 5
        
        # Check if this day has a Kultur-Event
        has_kultur_event = await db.events.find_one({
            "start_datetime": {"$regex": f"^{date_str}"},
            "content_category": {"$in": ["VERANSTALTUNG", "veranstaltung", "kultur"]},
            "archived": False
        })
        
        # Get closing time for this day
        closing_time = await get_closing_time_for_date(date_str)
        if closing_time is None:
            continue  # Day is closed, skip
        
        for template in templates:
            # Check event_mode: Skip normal templates on Kultur days (for affected templates)
            event_mode = template.get("event_mode", "normal")
            template_name = template.get("name", "")
            
            # Logic: On Kultur days, use Kultur variants; on normal days, use normal variants
            if has_kultur_event:
                # Skip normal Spät/Schichtleiter if Kultur variant exists
                if event_mode == "normal" and any(x in template_name for x in ["Spät", "Schichtleiter"]) and not "Früh" in template_name:
                    # Check if we have a Kultur variant for this
                    kultur_variant_exists = any(
                        t.get("event_mode") == "kultur" and 
                        template.get("department") == t.get("department") and
                        "Spät" in t.get("name", "") or "Schichtleiter" in t.get("name", "")
                        for t in templates
                    )
                    if kultur_variant_exists:
                        continue  # Skip normal, Kultur variant will be used
            else:
                # Normal day: skip Kultur templates
                if event_mode == "kultur":
                    continue
            
            # Check days_of_week filter (wenn vorhanden)
            days_of_week = template.get("days_of_week")
            if days_of_week is not None and current_date.weekday() not in days_of_week:
                continue  # Dieser Tag ist nicht in den erlaubten Tagen
            
            # Check day_type filter (Legacy)
            tpl_day_type = template.get("day_type", "all")
            if tpl_day_type == "weekday" and is_wknd:
                continue
            if tpl_day_type == "weekend" and not is_wknd:
                continue
            
            # Calculate end time based on end_time_type
            end_time_type = template.get("end_time_type", "fixed")
            if end_time_type == "close_plus_minutes" and closing_time:
                close_offset = template.get("close_plus_minutes", 0) or 0
                # Parse closing time and add offset
                try:
                    close_dt = datetime.strptime(closing_time, "%H:%M")
                    close_dt = close_dt + timedelta(minutes=close_offset)
                    end_time = close_dt.strftime("%H:%M")
                except:
                    end_time = template.get("end_time") or template.get("end_time_fixed", "23:00")
            else:
                # Fixed end time
                end_time = template.get("end_time_fixed") or template.get("end_time", "23:00")
            
            start_time = template.get("start_time")
            department = template.get("department")
            template_id = template.get("id")
            
            # IDEMPOTENT CHECK: Skip if shift already exists
            existing_shift = await db.shifts.find_one({
                "schedule_id": schedule_id,
                "date": date_str,
                "start_time": start_time,
                "end_time": end_time,
                "department": department,
                "template_id": template_id,
                "archived": False
            })
            
            if existing_shift:
                skipped_existing += 1
                continue  # Shift already exists, skip
            
            # Create N shifts based on headcount_default
            headcount = template.get("headcount_default", 1)
            for i in range(headcount):
                shift = create_entity({
                    "schedule_id": schedule_id,
                    "staff_member_id": None,  # Unassigned
                    "work_area_id": get_area_id(template.get("department", "service")),
                    "date": date_str,
                    "shift_date": date_str,  # Legacy
                    "start_time": start_time,
                    "end_time": end_time,
                    "shift_name": template.get("name"),
                    "role": template.get("role", "service"),
                    "department": department,
                    "notes": f"Aus Vorlage: {template.get('name')}",
                    "template_id": template_id,
                    "status": "offen"
                })
                await db.shifts.insert_one(shift)
                created_shifts.append(shift["id"])
    
    await create_audit_log(
        user, "schedule", schedule_id, "apply_templates",
        None,
        {"templates_used": len(templates), "shifts_created": len(created_shifts), "skipped_existing": skipped_existing, "season": season}
    )
    
    return {
        "message": f"{len(created_shifts)} Schichten aus Vorlagen erzeugt" + (f", {skipped_existing} bereits vorhanden" if skipped_existing > 0 else ""),
        "templates_used": len(templates), 
        "shifts_created": len(created_shifts), 
        "skipped_existing": skipped_existing,
        "season": season
    }


# ----- EVENT WARNING ENDPOINT -----

@staff_router.get("/schedules/{schedule_id}/event-warnings")
async def get_schedule_event_warnings(schedule_id: str, user: dict = Depends(require_manager)):
    """
    Liefert Veranstaltungs-Informationen für eine Dienstplan-Woche.
    
    HINWEIS: Diese Daten sind KEINE Fehler/Warnungen, sondern reine INFORMATIONEN
    für die Dispositionsplanung. Das Frontend zeigt sie entsprechend neutral an.
    
    Staffing-Empfehlung (nicht Fehler):
    - Event mit >=40 Gästen → empfohlen 3 Service
    - Event mit >=70 Gästen → empfohlen 4 Service
    """
    schedule = await db.schedules.find_one({"id": schedule_id, "archived": False}, {"_id": 0})
    if not schedule:
        raise NotFoundException("Dienstplan")
    
    # Korrektur: Nutze start_date/end_date statt week_start/week_end
    week_start = schedule.get("start_date") or schedule.get("week_start")
    week_end = schedule.get("end_date") or schedule.get("week_end")
    
    if not week_start or not week_end:
        return {"events": [], "has_events": False, "events_count": 0}
    
    # Events laden: start_datetime beginnt mit YYYY-MM-DD (String-Vergleich)
    # Events haben start_datetime als ISO-String "2026-01-09T17:00:00"
    all_events = await db.events.find({
        "status": {"$in": ["published", "sold_out"]},
        "archived": False
    }, {"_id": 0}).to_list(200)
    
    # Filter Events für diese Woche (basierend auf start_datetime)
    events_in_week = []
    for event in all_events:
        start_dt = event.get("start_datetime", "")
        if start_dt:
            # Extrahiere Datum aus ISO-String "2026-01-09T17:00:00" → "2026-01-09"
            event_date = start_dt[:10] if "T" in start_dt else start_dt
            if week_start <= event_date <= week_end:
                event["_computed_date"] = event_date
                events_in_week.append(event)
    
    if not events_in_week:
        return {"events": [], "has_events": False, "events_count": 0}
    
    # Shifts für den Schedule laden
    shifts = await db.shifts.find({
        "schedule_id": schedule_id,
        "archived": False
    }, {"_id": 0}).to_list(500)
    
    # Events mit Tagesbezug und Staffing-Info aufbereiten
    events_info = []
    for event in events_in_week:
        event_date = event.get("_computed_date")
        expected_guests = event.get("capacity_total", 0) or event.get("max_capacity", 0)
        
        # Staffing-Empfehlung berechnen
        recommended_service = 2  # Default
        if expected_guests >= 70:
            recommended_service = 4
        elif expected_guests >= 40:
            recommended_service = 3
        
        # Geplante Service-Schichten für diesen Tag zählen
        day_shifts = [s for s in shifts if s.get("shift_date") == event_date or s.get("date") == event_date]
        service_shifts = [s for s in day_shifts if s.get("role") in ["service", "schichtleiter"]]
        planned_service = len([s for s in service_shifts if s.get("staff_member_id")])
        
        # Event-Zeit extrahieren
        start_dt = event.get("start_datetime", "")
        event_time = start_dt[11:16] if "T" in start_dt else ""  # "17:00"
        
        events_info.append({
            "date": event_date,
            "event_name": event.get("title"),
            "event_id": event.get("id"),
            "event_type": event.get("event_type", "kultur"),
            "content_category": event.get("content_category", "VERANSTALTUNG"),
            "start_time": event_time,
            "expected_guests": expected_guests,
            "recommended_service": recommended_service,
            "planned_service": planned_service,
            # Formatierte Anzeige für Frontend
            "display_text": f"{event.get('title')} ({event_time} Uhr)"
        })
    
    # Nach Datum sortieren
    events_info.sort(key=lambda x: (x.get("date", ""), x.get("start_time", "")))
    
    return {
        "events": events_info,
        "has_events": len(events_info) > 0,
        "events_count": len(events_info)
    }


# ----- PDF EXPORT FOR SCHEDULE -----

@staff_router.get("/schedules/{schedule_id}/export-pdf")
async def export_schedule_pdf(
    schedule_id: str,
    view: str = "week",  # week or month
    user: dict = Depends(require_manager)
):
    """
    Export schedule as A4 PDF (landscape).
    Minimal format: Name + Time per day.
    """
    schedule = await db.schedules.find_one({"id": schedule_id, "archived": False}, {"_id": 0})
    if not schedule:
        raise NotFoundException("Dienstplan")
    
    # Get shifts with staff names
    shifts = await db.shifts.find({"schedule_id": schedule_id, "archived": False}, {"_id": 0}).to_list(500)
    
    # Get staff members
    staff_ids = list(set(s.get("staff_member_id") for s in shifts if s.get("staff_member_id")))
    staff_list = await db.staff_members.find({"id": {"$in": staff_ids}}, {"_id": 0, "id": 1, "full_name": 1}).to_list(100)
    staff_map = {s["id"]: s.get("full_name", "N.N.") for s in staff_list}
    
    # Build HTML for PDF
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4 landscape; margin: 1cm; }}
            body {{ font-family: Arial, sans-serif; font-size: 10px; }}
            h1 {{ font-size: 16px; margin-bottom: 10px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ border: 1px solid #ccc; padding: 4px; text-align: left; vertical-align: top; }}
            th {{ background: #f0f0f0; font-weight: bold; }}
            .day-header {{ font-weight: bold; background: #e8e8e8; }}
            .shift {{ font-size: 9px; margin: 2px 0; }}
            .unassigned {{ color: #999; font-style: italic; }}
        </style>
    </head>
    <body>
        <h1>Dienstplan KW {schedule.get('week', '')} / {schedule.get('year', '')}</h1>
        <p>{schedule.get('week_start', '')} bis {schedule.get('week_end', '')}</p>
        <table>
            <tr>
                <th>Mo</th><th>Di</th><th>Mi</th><th>Do</th><th>Fr</th><th>Sa</th><th>So</th>
            </tr>
            <tr>
    """
    
    # Group shifts by date
    from collections import defaultdict
    shifts_by_date = defaultdict(list)
    for shift in shifts:
        shifts_by_date[shift.get("shift_date", "")].append(shift)
    
    # Generate week view
    week_start = datetime.fromisoformat(schedule["week_start"]).date()
    for day_offset in range(7):
        current_date = (week_start + timedelta(days=day_offset)).isoformat()
        day_shifts = sorted(shifts_by_date.get(current_date, []), key=lambda x: x.get("start_time", ""))
        
        html_content += "<td>"
        html_content += f"<div class='day-header'>{current_date[8:10]}.{current_date[5:7]}.</div>"
        
        for shift in day_shifts:
            staff_name = staff_map.get(shift.get("staff_member_id"), "")
            if not staff_name:
                staff_name = "<span class='unassigned'>N.N.</span>"
            html_content += f"<div class='shift'>{shift.get('start_time', '')}-{shift.get('end_time', '')} {staff_name}</div>"
        
        if not day_shifts:
            html_content += "<div class='shift unassigned'>-</div>"
        
        html_content += "</td>"
    
    html_content += """
            </tr>
        </table>
    </body>
    </html>
    """
    
    # Convert HTML to PDF using basic approach
    # For production, use weasyprint or similar
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=dienstplan_kw{schedule.get('week')}_{schedule.get('year')}.pdf"
            }
        )
    except ImportError:
        # Fallback: return HTML
        return StreamingResponse(
            io.BytesIO(html_content.encode()),
            media_type="text/html",
            headers={
                "Content-Disposition": f"attachment; filename=dienstplan_kw{schedule.get('week')}_{schedule.get('year')}.html"
            }
        )


# ============== REGELBASIERTE DIENSTPLAN-VORSCHLÄGE ==============
"""
Shift Suggestion Engine - Generiert Vorschläge für Schichtbesetzung
KEINE automatische Zuweisung, nur Empfehlungen mit Begründung
"""

class ShiftSuggestionReason(str, Enum):
    """Gründe für Vorschläge"""
    AVAILABLE = "verfügbar"
    MATCHING_AREA = "passender Bereich"
    LOW_HOURS = "wenige Stunden geplant"
    LOW_SHIFTS = "wenige Schichten diese Woche"
    MULTI_ROLE = "Multi-Role geeignet"
    PREFERRED_DAY = "bevorzugter Tag"
    
class ShiftSuggestionWarning(str, Enum):
    """Warnungen bei Vorschlägen"""
    NEAR_HOUR_LIMIT = "nahe Wochenstunden-Grenze"
    CONSTRAINT_LIMIT = "nahe Constraint-Limit"
    ALREADY_SHIFT_TODAY = "bereits Schicht heute"


def check_availability_block(staff: dict, shift_date: str) -> tuple[bool, str]:
    """
    Prüft ob Mitarbeiter an diesem Datum verfügbar ist.
    Returns: (is_available, reason)
    """
    blocks = staff.get("availability_blocks", [])
    
    for block in blocks:
        block_type = block.get("type", "")
        start_date = block.get("start_date")
        end_date = block.get("end_date")
        
        # Prüfe Datumsbereich
        if start_date and end_date:
            if start_date <= shift_date <= end_date:
                reason = block.get("reason", f"Abwesenheit ({block_type})")
                return False, reason
        
        # Schulphase (generell eingeschränkt, aber nicht blockiert)
        if block_type == "school":
            return True, "Schulphase - eingeschränkt verfügbar"
    
    return True, ""


def check_constraints(staff: dict, shift_date: str, shift_data: dict, existing_shifts: list) -> tuple[bool, list]:
    """
    Prüft Aushilfen-Constraints (z.B. nur Wochenende, max Tage/Monat)
    Returns: (is_valid, warnings)
    """
    constraints = staff.get("constraints", {})
    warnings = []
    
    if not constraints:
        return True, warnings
    
    # Parse Datum
    try:
        dt = datetime.fromisoformat(shift_date)
        weekday = dt.weekday()  # 0=Montag, 6=Sonntag
        month = dt.month
        year = dt.year
    except:
        return True, warnings
    
    # Nur Wochenende?
    if constraints.get("weekend_only"):
        if weekday not in [5, 6]:  # Samstag=5, Sonntag=6
            return False, ["nur Wochenende erlaubt"]
    
    # Max Samstage/Sonntage pro Monat
    max_sat = constraints.get("max_saturdays_per_month")
    max_sun = constraints.get("max_sundays_per_month")
    
    if max_sat or max_sun:
        # Zähle bereits geplante Samstage/Sonntage im Monat
        staff_id = staff.get("id")
        saturdays = 0
        sundays = 0
        
        for shift in existing_shifts:
            if shift.get("staff_member_id") != staff_id:
                continue
            try:
                s_date = datetime.fromisoformat(shift.get("date", ""))
                if s_date.month == month and s_date.year == year:
                    if s_date.weekday() == 5:
                        saturdays += 1
                    elif s_date.weekday() == 6:
                        sundays += 1
            except:
                continue
        
        if max_sat and weekday == 5 and saturdays >= max_sat:
            return False, [f"max. {max_sat} Samstage/Monat erreicht"]
        
        if max_sun and weekday == 6 and sundays >= max_sun:
            return False, [f"max. {max_sun} Sonntage/Monat erreicht"]
        
        # Warnung bei Nähe zum Limit
        if max_sat and weekday == 5 and saturdays == max_sat - 1:
            warnings.append(f"letzter erlaubter Samstag ({saturdays + 1}/{max_sat})")
        if max_sun and weekday == 6 and sundays == max_sun - 1:
            warnings.append(f"letzter erlaubter Sonntag ({sundays + 1}/{max_sun})")
    
    return True, warnings


def calculate_staff_hours_this_week(staff_id: str, schedule_id: str, all_shifts: list) -> float:
    """Berechnet bereits geplante Stunden für Mitarbeiter in dieser Woche"""
    total_hours = 0.0
    
    for shift in all_shifts:
        if shift.get("staff_member_id") != staff_id:
            continue
        if shift.get("schedule_id") != schedule_id:
            continue
        
        try:
            start = datetime.strptime(shift.get("start_time", "09:00"), "%H:%M")
            end = datetime.strptime(shift.get("end_time", "17:00"), "%H:%M")
            hours = (end - start).seconds / 3600
            total_hours += hours
        except:
            total_hours += 8  # Default
    
    return total_hours


# ============== ZEIT-OVERLAP-PRÜFUNG ==============
"""
Robuste Prüfung ob Schichten zeitlich überlappen.
Erlaubt mehrere Schichten am selben Tag NUR wenn keine Zeitüberlappung.
"""

def parse_shift_times(shift: dict) -> tuple:
    """
    Parst Start- und Endzeit einer Schicht.
    Returns: (start_minutes, end_minutes, is_valid)
    - Zeiten als Minuten ab Mitternacht für einfache Vergleiche
    - Über-Mitternacht-Schichten werden erkannt (end < start)
    """
    start_time = shift.get("start_time", "")
    end_time = shift.get("end_time", "")
    
    if not start_time or not end_time:
        return (None, None, False)
    
    try:
        # Parse HH:MM Format
        start_parts = start_time.split(":")
        end_parts = end_time.split(":")
        
        start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
        end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
        
        # Über Mitternacht: end < start -> end += 24h (in Minuten)
        if end_minutes <= start_minutes:
            end_minutes += 24 * 60
        
        return (start_minutes, end_minutes, True)
    except (ValueError, IndexError):
        return (None, None, False)


def shifts_overlap(
    a_start: int, a_end: int, 
    b_start: int, b_end: int, 
    buffer_minutes: int = 0
) -> bool:
    """
    Prüft ob zwei Zeiträume überlappen.
    
    Args:
        a_start, a_end: Erste Schicht (Minuten ab Mitternacht)
        b_start, b_end: Zweite Schicht (Minuten ab Mitternacht)
        buffer_minutes: Mindestabstand zwischen Schichten (Default: 0)
    
    Returns:
        True wenn Overlap, False wenn keine Überlappung
    
    Overlap-Definition:
        a_start < b_end - buffer AND b_start < a_end - buffer
    
    Beispiele (buffer=0):
        09:00-11:00 + 11:00-16:00 -> False (kein Overlap, direkt anschließend)
        09:00-12:00 + 11:00-16:00 -> True (Overlap 11-12)
        20:00-24:00 + 00:00-02:00 -> False (über Mitternacht, kein Overlap)
    """
    if a_start is None or b_start is None:
        return True  # Bei ungültigen Zeiten: sicherheitshalber als Overlap behandeln
    
    # Anpassung für Buffer
    a_end_adj = a_end - buffer_minutes
    b_end_adj = b_end - buffer_minutes
    
    # Overlap wenn: a beginnt vor b endet UND b beginnt vor a endet
    return a_start < b_end_adj and b_start < a_end_adj


def check_shift_overlap_for_staff(
    staff_id: str,
    new_shift: dict,
    all_shifts: list,
    buffer_minutes: int = 0
) -> tuple:
    """
    Prüft ob eine neue Schicht mit bestehenden Schichten des Mitarbeiters überlappt.
    
    Args:
        staff_id: ID des Mitarbeiters
        new_shift: Die neue Schicht (dict mit date, start_time, end_time)
        all_shifts: Alle Schichten im Schedule
        buffer_minutes: Mindestabstand zwischen Schichten
    
    Returns:
        (has_overlap: bool, overlapping_shift: dict or None, reason: str)
    """
    new_date = new_shift.get("date", "")
    new_start, new_end, new_valid = parse_shift_times(new_shift)
    
    if not new_valid:
        return (False, None, "cannot_validate_overlap")
    
    # Finde alle Schichten des Mitarbeiters am selben Tag
    for existing in all_shifts:
        if existing.get("staff_member_id") != staff_id:
            continue
        if existing.get("date") != new_date:
            continue
        if existing.get("id") == new_shift.get("id"):
            continue  # Nicht mit sich selbst vergleichen
        
        ex_start, ex_end, ex_valid = parse_shift_times(existing)
        
        if not ex_valid:
            # Bestehende Schicht hat ungültige Zeiten -> sicherheitshalber Overlap annehmen
            return (True, existing, "existing_shift_invalid_times")
        
        if shifts_overlap(new_start, new_end, ex_start, ex_end, buffer_minutes):
            return (True, existing, "overlapping_shift_same_day")
    
    return (False, None, "no_overlap")


def calculate_suggestion_score(
    staff: dict,
    shift: dict,
    hours_planned: float,
    shifts_today: int,
    shifts_this_week: int,
    is_primary_area: bool
) -> tuple[float, list, list]:
    """
    Berechnet Score für einen Mitarbeiter für eine Schicht.
    Returns: (score, reasons, warnings)
    """
    score = 50.0  # Basis-Score
    reasons = []
    warnings = []
    
    weekly_hours = staff.get("weekly_hours", 40)
    
    # 1. Bereichs-Match
    if is_primary_area:
        score += 20
        reasons.append(f"primärer Bereich")
    else:
        score += 10
        reasons.append(f"sekundärer Bereich (Multi-Role)")
    
    # 2. Stunden-Auslastung
    utilization = hours_planned / weekly_hours if weekly_hours > 0 else 1.0
    
    if utilization < 0.3:
        score += 25
        reasons.append(f"nur {hours_planned:.0f}h von {weekly_hours}h geplant")
    elif utilization < 0.6:
        score += 15
        reasons.append(f"{hours_planned:.0f}h von {weekly_hours}h geplant")
    elif utilization < 0.9:
        score += 5
    elif utilization >= 1.0:
        score -= 15
        warnings.append(f"Wochenstunden bereits erreicht ({hours_planned:.0f}/{weekly_hours}h)")
    
    # 3. Schichten heute
    if shifts_today == 0:
        score += 10
        reasons.append("keine Schicht heute")
    elif shifts_today == 1:
        score -= 5
        warnings.append("bereits 1 Schicht heute")
    else:
        score -= 20
        warnings.append(f"bereits {shifts_today} Schichten heute")
    
    # 4. Schichten diese Woche (Fairness)
    if shifts_this_week <= 2:
        score += 10
    elif shifts_this_week <= 4:
        score += 5
    elif shifts_this_week >= 6:
        score -= 10
        warnings.append(f"bereits {shifts_this_week} Schichten diese Woche")
    
    return score, reasons, warnings


def generate_shift_suggestions(schedule_id: str) -> dict:
    """
    Generiert Schichtvorschläge für alle offenen Schichten eines Schedules.
    KEINE Zuweisung, nur Empfehlungen.
    """
    # Synchrone Hilfsfunktion - wird von async Endpoint aufgerufen
    raise NotImplementedError("Use async version")


async def generate_shift_suggestions_async(schedule_id: str) -> dict:
    """
    Generiert Schichtvorschläge für alle offenen Schichten eines Schedules.
    KEINE Zuweisung, nur Empfehlungen. (Async Version)
    """
    # Lade Schedule
    schedule = await db.schedules.find_one({"id": schedule_id})
    if not schedule:
        raise NotFoundException(f"Schedule {schedule_id} nicht gefunden")
    
    # Lade alle Schichten für dieses Schedule
    all_shifts = await db.shifts.find({"schedule_id": schedule_id}).to_list(1000)
    
    # Lade alle aktiven Mitarbeiter
    all_staff = await db.staff_members.find({"is_active": {"$ne": False}}).to_list(500)
    
    # Lade Work Areas für Mapping
    work_area_list = await db.work_areas.find().to_list(100)
    work_areas = {wa["id"]: wa["name"] for wa in work_area_list}
    
    # Ergebnis-Struktur
    result = {
        "schedule_id": schedule_id,
        "schedule_name": schedule.get("name", f"KW{schedule.get('week')}/{schedule.get('year')}"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "shifts_with_suggestions": [],
        "stats": {
            "total_shifts": len(all_shifts),
            "open_shifts": 0,
            "shifts_with_suggestions": 0
        }
    }
    
    # Für jede Schicht ohne Zuweisung
    for shift in all_shifts:
        # Überspringe bereits zugewiesene Schichten
        if shift.get("staff_member_id"):
            continue
        
        result["stats"]["open_shifts"] += 1
        
        shift_date = shift.get("date", "")
        shift_work_area = shift.get("work_area_id", "")
        shift_name = shift.get("shift_name", "Schicht")
        
        suggestions = []
        
        # Prüfe jeden Mitarbeiter
        for staff in all_staff:
            staff_id = staff.get("id")
            staff_name = staff.get("name", "")
            
            # 1. Verfügbarkeits-Check
            is_available, avail_reason = check_availability_block(staff, shift_date)
            if not is_available:
                continue  # Nicht verfügbar, kein Vorschlag
            
            # 2. Bereichs-Kompatibilität
            primary_area = staff.get("work_area_id")
            secondary_areas = staff.get("work_area_ids", [])
            
            is_primary = (shift_work_area == primary_area)
            is_secondary = (shift_work_area in secondary_areas)
            
            if not is_primary and not is_secondary:
                continue  # Falscher Bereich
            
            # 3. Constraint-Check
            is_valid, constraint_warnings = check_constraints(staff, shift_date, shift, all_shifts)
            if not is_valid:
                continue  # Constraint verletzt
            
            # 4. Zeit-Overlap-Check (NEU: zeitbasiert statt harter Blockade)
            has_overlap, overlapping_shift, overlap_reason = check_shift_overlap_for_staff(
                staff_id, shift, all_shifts, buffer_minutes=0
            )
            if has_overlap:
                continue  # Zeitüberlappung mit bestehender Schicht
            
            # 5. Berechne Statistiken
            hours_planned = calculate_staff_hours_this_week(staff_id, schedule_id, all_shifts)
            
            # Schichten heute zählen (für Score-Berechnung)
            shifts_today = sum(1 for s in all_shifts 
                             if s.get("staff_member_id") == staff_id 
                             and s.get("date") == shift_date)
            
            # Schichten diese Woche zählen
            shifts_this_week = sum(1 for s in all_shifts 
                                  if s.get("staff_member_id") == staff_id 
                                  and s.get("schedule_id") == schedule_id)
            
            # 6. Score berechnen
            score, reasons, warnings = calculate_suggestion_score(
                staff, shift, hours_planned, shifts_today, shifts_this_week, is_primary
            )
            
            # Constraint-Warnungen hinzufügen
            warnings.extend(constraint_warnings)
            
            # Availability-Hinweis (z.B. Schulphase)
            if avail_reason:
                warnings.append(avail_reason)
            
            suggestions.append({
                "staff_member_id": staff_id,
                "staff_name": staff_name,
                "score": round(score, 1),
                "reasons": reasons,
                "warnings": warnings,
                "hours_planned": round(hours_planned, 1),
                "weekly_hours": staff.get("weekly_hours", 40)
            })
        
        # Sortiere nach Score (beste zuerst), max 3 Vorschläge
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        top_suggestions = suggestions[:3]
        
        if top_suggestions:
            result["stats"]["shifts_with_suggestions"] += 1
        
        result["shifts_with_suggestions"].append({
            "shift_id": shift.get("id"),
            "shift_name": shift_name,
            "date": shift_date,
            "start_time": shift.get("start_time"),
            "end_time": shift.get("end_time"),
            "work_area_id": shift_work_area,
            "work_area_name": work_areas.get(shift_work_area, "Unbekannt"),
            "suggestions": top_suggestions
        })
    
    return result


# API Endpoint für Vorschläge
@staff_router.get("/schedules/{schedule_id}/shift-suggestions")
async def get_shift_suggestions(
    schedule_id: str,
    current_user: dict = Depends(require_manager)
):
    """
    Generiert Schichtvorschläge für alle offenen Schichten eines Schedules.
    Nur Vorschläge, keine automatische Zuweisung.
    """
    try:
        suggestions = await generate_shift_suggestions_async(schedule_id)
        return suggestions
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Fehler bei Vorschlagsgenerierung: {e}")
        raise HTTPException(status_code=500, detail=f"Fehler: {str(e)}")


@staff_router.post("/shifts/{shift_id}/apply-suggestion")
async def apply_shift_suggestion(
    shift_id: str,
    staff_member_id: str,
    current_user: dict = Depends(require_manager)
):
    """
    Wendet einen Vorschlag an (weist Mitarbeiter der Schicht zu).
    Dies ist die bewusste Übernahme durch den Planer.
    """
    # Prüfe ob Schicht existiert
    shift = await db.shifts.find_one({"id": shift_id})
    if not shift:
        raise HTTPException(status_code=404, detail="Schicht nicht gefunden")
    
    # Prüfe ob bereits zugewiesen
    if shift.get("staff_member_id"):
        raise HTTPException(status_code=400, detail="Schicht bereits zugewiesen")
    
    # Prüfe ob Mitarbeiter existiert
    staff = await db.staff_members.find_one({"id": staff_member_id})
    if not staff:
        raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden")
    
    # Zuweisung durchführen
    await db.shifts.update_one(
        {"id": shift_id},
        {
            "$set": {
                "staff_member_id": staff_member_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "assigned_by": current_user.get("id"),
                "assignment_source": "suggestion"
            }
        }
    )
    
    # Audit Log
    await create_audit_log(
        action="shift_assigned",
        entity_type="shift",
        entity_id=shift_id,
        actor_id=current_user.get("id"),
        changes={"staff_member_id": staff_member_id, "source": "suggestion"}
    )
    
    return {
        "success": True,
        "message": f"{staff.get('name')} wurde der Schicht zugewiesen",
        "shift_id": shift_id,
        "staff_member_id": staff_member_id
    }



# ============== BATCH AUTO-BESETZUNG ==============
"""
Batch-Endpoint für automatische Schichtbesetzung
- Vorschau (dry_run=true) oder Ausführung (dry_run=false)
- Idempotent: bereits zugewiesene Schichten werden übersprungen
- Skip-Gründe werden dokumentiert
"""

class SkipReason(str, Enum):
    """Gründe warum eine Schicht übersprungen wird"""
    ALREADY_ASSIGNED = "already_assigned"
    NO_CANDIDATES = "no_candidates"
    BELOW_MIN_SCORE = "below_min_score"
    UNAVAILABLE_AVAILABILITY_BLOCK = "unavailable_availability_block"
    WORK_AREA_MISMATCH = "work_area_mismatch"
    OVERLAPPING_SHIFT_SAME_DAY = "overlapping_shift_same_day"  # NEU: Zeitüberlappung
    CANNOT_VALIDATE_OVERLAP = "cannot_validate_overlap"  # NEU: Zeiten fehlen
    CONSTRAINT_WEEKEND_ONLY = "constraint_weekend_only"
    CONSTRAINT_MONTHLY_LIMIT = "constraint_monthly_limit"


class ApplySuggestionsRequest(BaseModel):
    """Request Body für Batch-Apply"""
    strategy: str = "top1"  # nur bester Kandidat je Shift
    limit: int = 20  # max Schichten pro Run
    dry_run: bool = True  # Vorschau oder ausführen
    min_score: float = 0  # Mindest-Score
    respect_constraints: bool = True  # immer true
    skip_if_assigned: bool = True  # immer true
    work_area_filter: Optional[List[str]] = None  # Optional: nur bestimmte Bereiche


async def batch_apply_suggestions(
    schedule_id: str,
    request: ApplySuggestionsRequest,
    current_user: dict
) -> dict:
    """
    Batch-Anwendung von Schichtvorschlägen.
    dry_run=true: nur Vorschau
    dry_run=false: tatsächliche Anwendung
    """
    # Lade Schedule
    schedule = await db.schedules.find_one({"id": schedule_id})
    if not schedule:
        raise NotFoundException(f"Schedule {schedule_id} nicht gefunden")
    
    # Lade alle Daten
    all_shifts = await db.shifts.find({"schedule_id": schedule_id}).to_list(1000)
    all_staff = await db.staff_members.find({"is_active": {"$ne": False}}).to_list(500)
    work_area_list = await db.work_areas.find().to_list(100)
    work_areas = {wa["id"]: wa["name"] for wa in work_area_list}
    work_area_ids_by_name = {wa["name"].lower(): wa["id"] for wa in work_area_list}
    
    # Filter: nur offene Schichten
    open_shifts = [s for s in all_shifts if not s.get("staff_member_id")]
    
    # Optional: Work Area Filter
    if request.work_area_filter:
        filter_ids = set()
        for name in request.work_area_filter:
            wa_id = work_area_ids_by_name.get(name.lower())
            if wa_id:
                filter_ids.add(wa_id)
        if filter_ids:
            open_shifts = [s for s in open_shifts if s.get("work_area_id") in filter_ids]
    
    # Limit anwenden
    open_shifts = open_shifts[:request.limit]
    
    # Ergebnis-Struktur
    result = {
        "schedule_id": schedule_id,
        "schedule_name": schedule.get("name", f"KW{schedule.get('week')}/{schedule.get('year')}"),
        "open_shifts": len([s for s in all_shifts if not s.get("staff_member_id")]),
        "processed": len(open_shifts),
        "would_apply": [],
        "applied": [],
        "skipped": [],
        "failed": [],
        "stats": {
            "applied_count": 0,
            "skipped_count": 0,
            "failed_count": 0
        }
    }
    
    # Track welche Staff bereits heute eine Schicht haben (für Double-Shift-Check)
    staff_shifts_by_date = {}
    for shift in all_shifts:
        if shift.get("staff_member_id"):
            date = shift.get("date", "")
            staff_id = shift.get("staff_member_id")
            key = f"{date}_{staff_id}"
            staff_shifts_by_date[key] = staff_shifts_by_date.get(key, 0) + 1
    
    # Für jeden offenen Shift den besten Kandidaten finden
    for shift in open_shifts:
        shift_id = shift.get("id")
        shift_date = shift.get("date", "")
        shift_work_area = shift.get("work_area_id", "")
        shift_name = shift.get("shift_name", "Schicht")
        
        # Bereits zugewiesen? (Sicherheitscheck)
        if shift.get("staff_member_id"):
            result["skipped"].append({
                "shift_id": shift_id,
                "shift_name": shift_name,
                "reason": SkipReason.ALREADY_ASSIGNED.value
            })
            result["stats"]["skipped_count"] += 1
            continue
        
        # Kandidaten sammeln
        candidates = []
        
        for staff in all_staff:
            staff_id = staff.get("id")
            staff_name = staff.get("name", "")
            
            # 1. Verfügbarkeits-Check
            is_available, avail_reason = check_availability_block(staff, shift_date)
            if not is_available:
                continue
            
            # 2. Bereichs-Kompatibilität
            primary_area = staff.get("work_area_id")
            secondary_areas = staff.get("work_area_ids", [])
            
            is_primary = (shift_work_area == primary_area)
            is_secondary = (shift_work_area in secondary_areas)
            
            if not is_primary and not is_secondary:
                continue
            
            # 3. Constraint-Check
            is_valid, constraint_warnings = check_constraints(staff, shift_date, shift, all_shifts)
            if not is_valid:
                continue
            
            # 4. Double-Shift-Check
            key = f"{shift_date}_{staff_id}"
            if staff_shifts_by_date.get(key, 0) >= 1:
                # Bereits eine Schicht heute - überpringe für Auto-Besetzung
                continue
            
            # 5. Berechne Score
            hours_planned = calculate_staff_hours_this_week(staff_id, schedule_id, all_shifts)
            shifts_today = sum(1 for s in all_shifts 
                             if s.get("staff_member_id") == staff_id 
                             and s.get("date") == shift_date)
            shifts_this_week = sum(1 for s in all_shifts 
                                  if s.get("staff_member_id") == staff_id 
                                  and s.get("schedule_id") == schedule_id)
            
            score, reasons, warnings = calculate_suggestion_score(
                staff, shift, hours_planned, shifts_today, shifts_this_week, is_primary
            )
            
            if score >= request.min_score:
                candidates.append({
                    "staff_member_id": staff_id,
                    "staff_name": staff_name,
                    "score": round(score, 1),
                    "reasons": reasons,
                    "warnings": warnings
                })
        
        # Keine Kandidaten?
        if not candidates:
            result["skipped"].append({
                "shift_id": shift_id,
                "shift_name": shift_name,
                "date": shift_date,
                "work_area": work_areas.get(shift_work_area, "Unbekannt"),
                "reason": SkipReason.NO_CANDIDATES.value
            })
            result["stats"]["skipped_count"] += 1
            continue
        
        # Sortiere nach Score und nimm Top-1
        candidates.sort(key=lambda x: x["score"], reverse=True)
        best = candidates[0]
        
        # Min-Score Check
        if best["score"] < request.min_score:
            result["skipped"].append({
                "shift_id": shift_id,
                "shift_name": shift_name,
                "reason": SkipReason.BELOW_MIN_SCORE.value,
                "best_score": best["score"],
                "min_score": request.min_score
            })
            result["stats"]["skipped_count"] += 1
            continue
        
        # Zu would_apply hinzufügen
        apply_item = {
            "shift_id": shift_id,
            "shift_name": shift_name,
            "date": shift_date,
            "time": f"{shift.get('start_time', '?')}-{shift.get('end_time', '?')}",
            "work_area": work_areas.get(shift_work_area, "Unbekannt"),
            "staff_member_id": best["staff_member_id"],
            "staff_name": best["staff_name"],
            "score": best["score"],
            "reasons": best["reasons"]
        }
        result["would_apply"].append(apply_item)
        
        # Bei dry_run=false: tatsächlich anwenden
        if not request.dry_run:
            try:
                await db.shifts.update_one(
                    {"id": shift_id, "staff_member_id": None},  # Nur wenn noch nicht zugewiesen
                    {
                        "$set": {
                            "staff_member_id": best["staff_member_id"],
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                            "assigned_by": current_user.get("id"),
                            "assignment_source": "batch_auto"
                        }
                    }
                )
                
                # Track für Double-Shift
                key = f"{shift_date}_{best['staff_member_id']}"
                staff_shifts_by_date[key] = staff_shifts_by_date.get(key, 0) + 1
                
                result["applied"].append(apply_item)
                result["stats"]["applied_count"] += 1
                
            except Exception as e:
                result["failed"].append({
                    "shift_id": shift_id,
                    "shift_name": shift_name,
                    "error": str(e)
                })
                result["stats"]["failed_count"] += 1
        else:
            result["stats"]["applied_count"] += 1  # Für dry_run: zeigt was angewendet WÜRDE
    
    # Audit Log bei tatsächlicher Anwendung
    if not request.dry_run and result["stats"]["applied_count"] > 0:
        await create_audit_log(
            action="batch_shift_assignment",
            entity_type="schedule",
            entity_id=schedule_id,
            actor_id=current_user.get("id"),
            changes={
                "applied_count": result["stats"]["applied_count"],
                "skipped_count": result["stats"]["skipped_count"],
                "strategy": request.strategy,
                "limit": request.limit
            }
        )
    
    return result


@staff_router.post("/schedules/{schedule_id}/apply-suggestions")
async def apply_suggestions_batch(
    schedule_id: str,
    request: ApplySuggestionsRequest,
    current_user: dict = Depends(require_manager)
):
    """
    Batch-Anwendung von Schichtvorschlägen.
    
    dry_run=true: Nur Vorschau, was angewendet werden würde
    dry_run=false: Tatsächliche Anwendung
    
    Idempotent: Bereits zugewiesene Schichten werden übersprungen.
    """
    try:
        result = await batch_apply_suggestions(schedule_id, request, current_user)
        return result
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Batch-Apply Fehler: {e}")
        raise HTTPException(status_code=500, detail=f"Fehler: {str(e)}")

