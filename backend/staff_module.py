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
# Sensitive HR fields - Admin only
SENSITIVE_HR_FIELDS = {"tax_id", "social_security_number", "bank_iban", "health_insurance", "date_of_birth", "street", "zip_code", "city"}
# Fields requiring special audit logging
AUDIT_SENSITIVE_FIELDS = {"tax_id", "social_security_number", "bank_iban"}


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


def filter_member_for_role(member: dict, user_role: str) -> dict:
    """Filter staff member fields based on user role"""
    if user_role == "admin":
        # Admin sees everything
        return member
    
    # Schichtleiter sees only contact fields, not sensitive HR data
    filtered = {k: v for k, v in member.items() if k not in SENSITIVE_HR_FIELDS}
    return filtered


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
    if status:
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
            extra={"changed_fields": changed_sensitive, "note": "Sensitive HR data updated"}
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
    """Update HR fields for a staff member - Admin only with enhanced audit logging"""
    existing = await db.staff_members.find_one({"id": member_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Mitarbeiter")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        return existing
    
    update_data["updated_at"] = now_iso()
    
    # Track which sensitive fields are being changed
    changed_sensitive = []
    for field in AUDIT_SENSITIVE_FIELDS:
        if field in update_data and update_data[field] != existing.get(field):
            changed_sensitive.append(field)
    
    await db.staff_members.update_one({"id": member_id}, {"$set": update_data})
    updated = await db.staff_members.find_one({"id": member_id}, {"_id": 0})
    
    # Enhanced audit logging for sensitive HR fields
    if changed_sensitive:
        await create_audit_log(
            user, "staff_member_hr", member_id, "update_sensitive_hr_fields",
            {"fields": changed_sensitive, "values": "***MASKED***"},
            {"fields": changed_sensitive, "values": "***MASKED***"},
            extra={
                "changed_fields": changed_sensitive,
                "staff_name": updated.get("full_name"),
                "note": "Sensitive HR data updated - values masked for privacy"
            }
        )
    
    # Standard audit log
    await create_audit_log(
        user, "staff_member", member_id, "update_hr_fields",
        {k: existing.get(k) for k in update_data.keys()},
        update_data
    )
    
    result = {k: v for k, v in updated.items() if k != "_id"}
    result["completeness"] = calculate_completeness(updated)
    return result


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
