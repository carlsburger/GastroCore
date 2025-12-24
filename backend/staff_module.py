"""
GastroCore Staff & Schedule Module - Sprint 5
Mitarbeiter- und Dienstplanverwaltung

ADDITIV - Keine Breaking Changes
"""

from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
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
    """Get start and end date of a calendar week"""
    first_day = date(year, 1, 1)
    first_monday = first_day + timedelta(days=(7 - first_day.weekday()) % 7)
    if first_day.weekday() <= 3:  # Thursday or earlier
        first_monday -= timedelta(days=7)
    week_start = first_monday + timedelta(weeks=week - 1)
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
    if user_role != "admin":
        # Non-admin: Remove ALL sensitive HR fields completely
        filtered = {}
        for k, v in member.items():
            if k not in SENSITIVE_HR_FIELDS and k not in HIGH_SECURITY_FIELDS:
                filtered[k] = v
        return filtered
    
    # Admin: Apply masking to high-security fields by default
    if masked:
        return mask_sensitive_fields(member)
    else:
        # Decrypt fields for admin when explicitly requested
        result = member.copy()
        for field in HIGH_SECURITY_FIELDS:
            if field in result and result[field]:
                result[field] = decrypt_field(result[field])
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
    
    # Status-Filter: Mappe "aktiv"/"inaktiv" auf active=true/false
    # Unterstützt sowohl "status" als auch "active" Feld in DB
    if status:
        if status.lower() == "aktiv":
            # Entweder status="aktiv" ODER active=true (für Kompatibilität)
            query["$or"] = [{"status": "aktiv"}, {"active": True, "status": {"$exists": False}}]
        elif status.lower() == "inaktiv":
            query["$or"] = [{"status": "inaktiv"}, {"active": False}]
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
    
    Returns 404 wenn kein Mitarbeiterprofil verknüpft.
    Returns leere Liste wenn keine Schichten vorhanden.
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
        # Kein Mitarbeiter-Profil gefunden - 404 mit klarer Meldung
        raise HTTPException(
            status_code=404,
            detail="Kein Mitarbeiterprofil verknüpft. Bitte wende dich an die Schichtleitung."
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
    
    return shifts


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
    
    # Get all active staff members
    staff_members = await db.staff_members.find({"archived": False, "status": "aktiv"}, {"_id": 0}).to_list(500)
    
    # Get all shifts for this week
    shifts = await db.shifts.find({
        "shift_date": {"$gte": week_start.isoformat(), "$lte": week_end.isoformat()},
        "archived": False
    }, {"_id": 0}).to_list(1000)
    
    # Calculate hours per staff member
    overview = []
    for member in staff_members:
        member_shifts = [s for s in shifts if s.get("staff_member_id") == member.get("id")]
        planned_hours = sum(s.get("hours", 0) for s in member_shifts)
        weekly_hours = member.get("weekly_hours", 0)
        
        overview.append({
            "staff_member_id": member.get("id"),
            "name": member.get("full_name"),
            "employment_type": member.get("employment_type"),
            "weekly_hours_target": weekly_hours,
            "planned_hours": round(planned_hours, 2),
            "difference": round(planned_hours - weekly_hours, 2),
            "shift_count": len(member_shifts)
        })
    
    return {
        "year": year,
        "week": week,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "overview": overview,
        "total_planned": round(sum(o["planned_hours"] for o in overview), 2),
        "total_target": round(sum(o["weekly_hours_target"] for o in overview), 2)
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


class ShiftTemplateCreate(BaseModel):
    department: DepartmentType
    name: str = Field(..., min_length=2, max_length=50)
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")  # HH:MM
    end_time_type: EndTimeType
    end_time_fixed: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")  # HH:MM if fixed
    close_plus_minutes: Optional[int] = Field(None, ge=0, le=120)  # if close_plus_minutes
    season: SeasonType = SeasonType.ALL
    day_type: DayType = DayType.ALL
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
    headcount_default: Optional[int] = None
    active: Optional[bool] = None
    sort_order: Optional[int] = None


class ApplyTemplatesRequest(BaseModel):
    schedule_id: str
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
        query["active"] = True
    
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
    """Seed default Carlsburg shift templates"""
    # Check if templates already exist
    existing = await db.shift_templates.count_documents({"archived": False})
    if existing > 0:
        return {"message": "Vorlagen existieren bereits", "seeded": False, "count": existing}
    
    default_templates = [
        # Sommer - Wochentag
        {"department": "service", "name": "S10 Vorbereitung", "start_time": "10:00", "end_time_type": "fixed", "end_time_fixed": "18:00", "season": "summer", "day_type": "weekday", "headcount_default": 1, "sort_order": 10},
        {"department": "service", "name": "S11 Früh", "start_time": "11:00", "end_time_type": "fixed", "end_time_fixed": "18:00", "season": "summer", "day_type": "weekday", "headcount_default": 1, "sort_order": 11},
        {"department": "service", "name": "S12 Schluss", "start_time": "12:00", "end_time_type": "close_plus_minutes", "close_plus_minutes": 30, "season": "summer", "day_type": "weekday", "headcount_default": 2, "sort_order": 12},
        
        # Sommer - Wochenende
        {"department": "service", "name": "S10 Vorbereitung WE", "start_time": "10:00", "end_time_type": "fixed", "end_time_fixed": "18:00", "season": "summer", "day_type": "weekend", "headcount_default": 1, "sort_order": 20},
        {"department": "service", "name": "S11 Früh WE", "start_time": "11:00", "end_time_type": "fixed", "end_time_fixed": "18:00", "season": "summer", "day_type": "weekend", "headcount_default": 2, "sort_order": 21},
        {"department": "service", "name": "S12 Schluss WE", "start_time": "12:00", "end_time_type": "close_plus_minutes", "close_plus_minutes": 30, "season": "summer", "day_type": "weekend", "headcount_default": 2, "sort_order": 22},
        {"department": "service", "name": "S13 Patisserie WE", "start_time": "13:00", "end_time_type": "close_plus_minutes", "close_plus_minutes": 30, "season": "summer", "day_type": "weekend", "headcount_default": 1, "sort_order": 23},
        
        # Winter - Standard
        {"department": "service", "name": "W11 Service", "start_time": "11:00", "end_time_type": "close_plus_minutes", "close_plus_minutes": 30, "season": "winter", "day_type": "all", "headcount_default": 1, "sort_order": 30},
        {"department": "service", "name": "W12 Service", "start_time": "12:00", "end_time_type": "close_plus_minutes", "close_plus_minutes": 30, "season": "winter", "day_type": "all", "headcount_default": 1, "sort_order": 31},
        
        # Küche (generisch)
        {"department": "kitchen", "name": "K10 Küche Früh", "start_time": "10:00", "end_time_type": "fixed", "end_time_fixed": "18:00", "season": "all", "day_type": "all", "headcount_default": 1, "sort_order": 50},
        {"department": "kitchen", "name": "K12 Küche Schluss", "start_time": "12:00", "end_time_type": "close_plus_minutes", "close_plus_minutes": 30, "season": "all", "day_type": "all", "headcount_default": 1, "sort_order": 51},
    ]
    
    for tpl_data in default_templates:
        tpl = create_entity({**tpl_data, "active": True})
        await db.shift_templates.insert_one(tpl)
    
    await create_audit_log(user, "shift_template", "seed", "seed_defaults", None, {"count": len(default_templates)})
    return {"message": "Standard-Vorlagen erstellt", "seeded": True, "count": len(default_templates)}


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
    data: ApplyTemplatesRequest,
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
    templates = await db.shift_templates.find({
        "department": {"$in": dept_values},
        "$or": [
            {"season": {"$in": [season, "all"]}},
            {"season": {"$exists": False}},  # Templates ohne season-Feld
        ],
        "$or": [
            {"active": True},
            {"is_active": True},  # Alternative Feldname
        ],
        "archived": False
    }, {"_id": 0}).to_list(100)
    
    # Fallback: Wenn keine Templates gefunden, versuche ohne season-Filter
    if not templates:
        templates = await db.shift_templates.find({
            "department": {"$in": dept_values},
            "$or": [
                {"active": True},
                {"is_active": True},
            ],
            "archived": False
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
    week_start = datetime.fromisoformat(week_start_str).date()
    created_shifts = []
    
    for day_offset in range(7):
        current_date = week_start + timedelta(days=day_offset)
        date_str = current_date.isoformat()
        is_wknd = current_date.weekday() >= 5
        
        # Get closing time for this day
        closing_time = await get_closing_time_for_date(date_str)
        if closing_time is None:
            continue  # Day is closed, skip
        
        for template in templates:
            # Check day_type filter
            tpl_day_type = template.get("day_type", "all")
            if tpl_day_type == "weekday" and is_wknd:
                continue
            if tpl_day_type == "weekend" and not is_wknd:
                continue
            
            # Calculate end time
            end_time = calculate_end_time(template, closing_time)
            
            # Create N shifts based on headcount_default
            headcount = template.get("headcount_default", 1)
            for i in range(headcount):
                shift = create_entity({
                    "schedule_id": schedule_id,
                    "staff_member_id": None,  # Unassigned
                    "work_area_id": get_area_id(template.get("department", "service")),
                    "date": date_str,  # Konsistent mit bestehenden Shifts
                    "shift_date": date_str,  # Legacy-Feld für Kompatibilität
                    "start_time": template.get("start_time"),
                    "end_time": end_time or template.get("end_time"),
                    "shift_name": template.get("name"),
                    "role": template.get("role", "service"),
                    "department": template.get("department"),
                    "notes": f"Aus Vorlage: {template.get('name')}",
                    "template_id": template.get("id"),
                    "status": "offen"
                })
                await db.shifts.insert_one(shift)
                created_shifts.append(shift["id"])
    
    await create_audit_log(
        user, "schedule", schedule_id, "apply_templates",
        None,
        {"templates_applied": len(templates), "shifts_created": len(created_shifts), "season": season}
    )
    
    return {
        "message": f"{len(created_shifts)} Schichten aus Vorlagen erstellt",
        "created": len(created_shifts),
        "season": season,
        "templates_used": len(templates)
    }


# ----- EVENT WARNING ENDPOINT -----

@staff_router.get("/schedules/{schedule_id}/event-warnings")
async def get_schedule_event_warnings(schedule_id: str, user: dict = Depends(require_manager)):
    """
    Check for events in the schedule week and return staffing warnings.
    Rule: 
    - Event with >=40 expected guests → min 3 service
    - Event with >=70 expected guests → min 4 service
    """
    schedule = await db.schedules.find_one({"id": schedule_id, "archived": False}, {"_id": 0})
    if not schedule:
        raise NotFoundException("Dienstplan")
    
    warnings = []
    
    # Get events for this week
    week_start = schedule.get("week_start")
    week_end = schedule.get("week_end")
    
    events = await db.events.find({
        "event_date": {"$gte": week_start, "$lte": week_end},
        "status": {"$in": ["published", "sold_out"]},
        "archived": False
    }, {"_id": 0}).to_list(50)
    
    if not events:
        return {"warnings": [], "has_events": False}
    
    # Get shifts for the schedule
    shifts = await db.shifts.find({
        "schedule_id": schedule_id,
        "archived": False
    }, {"_id": 0}).to_list(500)
    
    for event in events:
        event_date = event.get("event_date")
        expected_guests = event.get("max_capacity", 0)
        
        # Check bookings for this event
        bookings = await db.event_bookings.find({
            "event_id": event.get("id"),
            "status": {"$in": ["confirmed", "pending"]}
        }, {"_id": 0}).to_list(200)
        
        actual_guests = sum(b.get("total_quantity", 0) for b in bookings)
        
        # Determine required service staff
        required_service = 2  # Default
        if actual_guests >= 70 or expected_guests >= 70:
            required_service = 4
        elif actual_guests >= 40 or expected_guests >= 40:
            required_service = 3
        
        # Count planned service staff for this day
        day_shifts = [s for s in shifts if s.get("shift_date") == event_date]
        service_shifts = [s for s in day_shifts if s.get("role") in ["service", "schichtleiter"]]
        assigned_service = len([s for s in service_shifts if s.get("staff_member_id")])
        
        if assigned_service < required_service:
            warnings.append({
                "date": event_date,
                "event_name": event.get("title"),
                "event_id": event.get("id"),
                "expected_guests": max(actual_guests, expected_guests),
                "required_service": required_service,
                "planned_service": assigned_service,
                "shortage": required_service - assigned_service,
                "message": f"Event '{event.get('title')}': benötigt {required_service} Service – aktuell geplant {assigned_service}"
            })
    
    return {
        "warnings": warnings,
        "has_events": len(events) > 0,
        "events_count": len(events)
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

