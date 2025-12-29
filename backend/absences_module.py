"""
GastroCore Absences & Documents Module - V1.1
Modul 30: Abwesenheiten & Personalakte (LIGHT)

FEATURES:
- staff_absences: Urlaub, Krank, Sonderfrei
- staff_documents: Digitale Personalakte (read-only für MA)
- staff_document_acknowledgements: Bestätigungen

GRUNDSÄTZE:
- Abwesenheiten beeinflussen Dienstplan & Kontrolle
- Personalakte ist read-only für Mitarbeiter
- Keine Uploads durch Mitarbeiter in V1.1
- Backend ist Source of Truth
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, date, timedelta
from enum import Enum
import uuid
import os
import logging
import shutil
from pathlib import Path

from core.database import db
from core.auth import get_current_user, require_admin, require_manager
from core.audit import create_audit_log, safe_dict_for_audit
from core.exceptions import NotFoundException, ValidationException, ForbiddenException, ConflictException

logger = logging.getLogger(__name__)

# ============== FILE STORAGE CONFIG ==============
UPLOAD_DIR = Path("/app/uploads/staff_documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}


# ============== ENUMS ==============
class AbsenceType(str, Enum):
    VACATION = "VACATION"      # Urlaub
    SICK = "SICK"              # Krank
    SPECIAL = "SPECIAL"        # Sonderfrei (z.B. Hochzeit, Umzug)
    OTHER = "OTHER"            # Sonstiges


class AbsenceStatus(str, Enum):
    REQUESTED = "REQUESTED"    # Beantragt
    APPROVED = "APPROVED"      # Genehmigt
    REJECTED = "REJECTED"      # Abgelehnt
    CANCELLED = "CANCELLED"    # Storniert


class DocumentCategory(str, Enum):
    CONTRACT = "CONTRACT"       # Arbeitsvertrag
    POLICY = "POLICY"          # Belehrung / Richtlinie
    CERTIFICATE = "CERTIFICATE" # Zeugnis / Bescheinigung
    OTHER = "OTHER"            # Sonstiges


# ============== PYDANTIC MODELS ==============

# --- Absences ---
class AbsenceCreateRequest(BaseModel):
    """Mitarbeiter beantragt Abwesenheit"""
    type: AbsenceType
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD")
    notes_employee: Optional[str] = Field(None, max_length=500)


class AbsenceAdminAction(BaseModel):
    """Admin genehmigt/lehnt ab"""
    notes_admin: Optional[str] = Field(None, max_length=500)


class AbsenceResponse(BaseModel):
    id: str
    staff_member_id: str
    staff_name: Optional[str] = None
    type: AbsenceType
    start_date: str
    end_date: str
    days_count: int
    status: AbsenceStatus
    notes_employee: Optional[str] = None
    notes_admin: Optional[str] = None
    created_at: str
    updated_at: str


# --- Documents ---
class DocumentResponse(BaseModel):
    id: str
    staff_member_id: str
    title: str
    category: DocumentCategory
    file_url: str
    file_name: str
    version: int
    requires_acknowledgement: bool
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None
    created_at: str


class DocumentAcknowledgementRequest(BaseModel):
    """Bestätigung durch Mitarbeiter"""
    device_id: Optional[str] = None


# ============== HELPER FUNCTIONS ==============
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now_utc().isoformat()


def calculate_days(start_date: str, end_date: str) -> int:
    """Berechne Anzahl Tage (inklusiv)"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    return (end - start).days + 1


def validate_date_range(start_date: str, end_date: str):
    """Validiere Datumsbereich"""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        if end < start:
            raise ValidationException("Enddatum darf nicht vor Startdatum liegen")
    except ValueError:
        raise ValidationException("Ungültiges Datumsformat. Erwartet: YYYY-MM-DD")


async def get_staff_member_for_user(user: dict) -> dict:
    """Get staff member linked to user"""
    staff_member_id = user.get("staff_member_id")
    if staff_member_id:
        staff = await db.staff_members.find_one({"id": staff_member_id, "archived": False}, {"_id": 0})
        if staff:
            return staff
    
    # Fallback: Email matching
    staff = await db.staff_members.find_one({"email": user.get("email"), "archived": False}, {"_id": 0})
    return staff


async def get_staff_name(staff_member_id: str) -> str:
    """Get staff member's full name"""
    staff = await db.staff_members.find_one({"id": staff_member_id}, {"_id": 0})
    if staff:
        return staff.get("full_name") or f"{staff.get('first_name', '')} {staff.get('last_name', '')}".strip()
    return "Unbekannt"


def generate_file_path(staff_member_id: str, filename: str) -> Path:
    """Generate unique file path for document"""
    ext = Path(filename).suffix.lower()
    unique_name = f"{uuid.uuid4()}{ext}"
    staff_dir = UPLOAD_DIR / staff_member_id
    staff_dir.mkdir(parents=True, exist_ok=True)
    return staff_dir / unique_name


# ============== ROUTERS ==============
absences_router = APIRouter(prefix="/api/staff/absences", tags=["Absences"])
documents_router = APIRouter(prefix="/api/staff/documents", tags=["Documents"])
admin_absences_router = APIRouter(prefix="/api/admin/absences", tags=["Admin Absences"])
admin_documents_router = APIRouter(prefix="/api/admin/staff", tags=["Admin Documents"])


# ============================================================
# MITARBEITER ABSENCES ENDPOINTS
# ============================================================

@absences_router.get("/me")
async def get_my_absences(
    status: Optional[AbsenceStatus] = None,
    year: Optional[int] = None,
    user: dict = Depends(get_current_user)
):
    """
    Mitarbeiter: Eigene Abwesenheiten abrufen.
    Optional gefiltert nach Status und Jahr.
    """
    staff = await get_staff_member_for_user(user)
    if not staff:
        return {
            "success": True,
            "data": [],
            "message": "Kein Mitarbeiterprofil verknüpft"
        }
    
    query = {"staff_member_id": staff["id"]}
    
    if status:
        query["status"] = status.value
    
    if year:
        query["start_date"] = {"$regex": f"^{year}-"}
    
    absences = await db.staff_absences.find(query, {"_id": 0}).sort("start_date", -1).to_list(500)
    
    # Enrich with calculated days
    for absence in absences:
        absence["days_count"] = calculate_days(absence["start_date"], absence["end_date"])
    
    return {
        "success": True,
        "data": absences,
        "count": len(absences)
    }


@absences_router.post("")
async def create_absence_request(
    data: AbsenceCreateRequest,
    user: dict = Depends(get_current_user)
):
    """
    Mitarbeiter: Abwesenheit beantragen.
    Status wird auf REQUESTED gesetzt.
    """
    staff = await get_staff_member_for_user(user)
    if not staff:
        raise HTTPException(status_code=400, detail="Kein Mitarbeiterprofil verknüpft")
    
    # Validate date range
    validate_date_range(data.start_date, data.end_date)
    
    # Check for overlapping absences
    existing = await db.staff_absences.find_one({
        "staff_member_id": staff["id"],
        "status": {"$in": [AbsenceStatus.REQUESTED.value, AbsenceStatus.APPROVED.value]},
        "$or": [
            {"start_date": {"$lte": data.end_date}, "end_date": {"$gte": data.start_date}}
        ]
    })
    
    if existing:
        raise ConflictException(
            f"Überschneidung mit bestehender Abwesenheit vom {existing['start_date']} bis {existing['end_date']}"
        )
    
    absence_id = str(uuid.uuid4())
    now = now_iso()
    
    absence = {
        "id": absence_id,
        "staff_member_id": staff["id"],
        "type": data.type.value,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "status": AbsenceStatus.REQUESTED.value,
        "notes_employee": data.notes_employee,
        "notes_admin": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.staff_absences.insert_one(absence)
    
    # Audit log
    await create_audit_log(
        user, "staff_absence", absence_id, "create",
        None,
        {"type": data.type.value, "dates": f"{data.start_date} - {data.end_date}"}
    )
    
    absence["days_count"] = calculate_days(data.start_date, data.end_date)
    del absence["_id"] if "_id" in absence else None
    
    return {
        "success": True,
        "message": "Abwesenheitsantrag eingereicht",
        "data": absence
    }


@absences_router.post("/{absence_id}/cancel")
async def cancel_my_absence(
    absence_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Mitarbeiter: Eigene Abwesenheit stornieren.
    Nur möglich wenn Status = REQUESTED.
    """
    staff = await get_staff_member_for_user(user)
    if not staff:
        raise HTTPException(status_code=400, detail="Kein Mitarbeiterprofil verknüpft")
    
    absence = await db.staff_absences.find_one({
        "id": absence_id,
        "staff_member_id": staff["id"]
    }, {"_id": 0})
    
    if not absence:
        raise NotFoundException("Abwesenheit")
    
    if absence["status"] != AbsenceStatus.REQUESTED.value:
        raise HTTPException(
            status_code=409,
            detail="Nur offene Anträge können storniert werden"
        )
    
    now = now_iso()
    await db.staff_absences.update_one(
        {"id": absence_id},
        {"$set": {"status": AbsenceStatus.CANCELLED.value, "updated_at": now}}
    )
    
    # Audit log
    await create_audit_log(
        user, "staff_absence", absence_id, "cancel",
        {"status": absence["status"]},
        {"status": AbsenceStatus.CANCELLED.value}
    )
    
    return {
        "success": True,
        "message": "Abwesenheitsantrag storniert"
    }


# ============================================================
# MITARBEITER DOCUMENTS ENDPOINTS
# ============================================================

@documents_router.get("/me")
async def get_my_documents(
    category: Optional[DocumentCategory] = None,
    user: dict = Depends(get_current_user)
):
    """
    Mitarbeiter: Eigene Dokumente abrufen.
    Inkl. Acknowledgement-Status.
    """
    staff = await get_staff_member_for_user(user)
    if not staff:
        return {
            "success": True,
            "data": [],
            "unacknowledged_count": 0,
            "message": "Kein Mitarbeiterprofil verknüpft"
        }
    
    query = {"staff_member_id": staff["id"]}
    if category:
        query["category"] = category.value
    
    documents = await db.staff_documents.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    # Get acknowledgements for this staff member
    ack_query = {"staff_member_id": staff["id"]}
    acknowledgements = await db.staff_document_acknowledgements.find(ack_query, {"_id": 0}).to_list(500)
    ack_map = {a["staff_document_id"]: a for a in acknowledgements}
    
    # Enrich documents with acknowledgement status
    unacknowledged_count = 0
    for doc in documents:
        ack = ack_map.get(doc["id"])
        doc["acknowledged"] = ack is not None
        doc["acknowledged_at"] = ack["acknowledged_at"] if ack else None
        
        if doc.get("requires_acknowledgement") and not doc["acknowledged"]:
            unacknowledged_count += 1
    
    return {
        "success": True,
        "data": documents,
        "count": len(documents),
        "unacknowledged_count": unacknowledged_count
    }


@documents_router.get("/me/unacknowledged-count")
async def get_unacknowledged_count(user: dict = Depends(get_current_user)):
    """
    Mitarbeiter: Anzahl unbestätigter Pflichtdokumente.
    Für Badge in PWA.
    """
    staff = await get_staff_member_for_user(user)
    if not staff:
        return {"count": 0}
    
    # Get all documents that require acknowledgement
    required_docs = await db.staff_documents.find({
        "staff_member_id": staff["id"],
        "requires_acknowledgement": True
    }, {"id": 1}).to_list(500)
    
    required_doc_ids = [d["id"] for d in required_docs]
    
    if not required_doc_ids:
        return {"count": 0}
    
    # Get acknowledgements
    acknowledged = await db.staff_document_acknowledgements.find({
        "staff_member_id": staff["id"],
        "staff_document_id": {"$in": required_doc_ids}
    }, {"staff_document_id": 1}).to_list(500)
    
    acknowledged_ids = {a["staff_document_id"] for a in acknowledged}
    
    unacknowledged_count = sum(1 for doc_id in required_doc_ids if doc_id not in acknowledged_ids)
    
    return {"count": unacknowledged_count}


@documents_router.post("/{document_id}/acknowledge")
async def acknowledge_document(
    document_id: str,
    data: DocumentAcknowledgementRequest = DocumentAcknowledgementRequest(),
    user: dict = Depends(get_current_user)
):
    """
    Mitarbeiter: Dokument als gelesen bestätigen.
    Nur eigene Dokumente.
    """
    staff = await get_staff_member_for_user(user)
    if not staff:
        raise HTTPException(status_code=400, detail="Kein Mitarbeiterprofil verknüpft")
    
    # Check document exists and belongs to this staff member
    document = await db.staff_documents.find_one({
        "id": document_id,
        "staff_member_id": staff["id"]
    }, {"_id": 0})
    
    if not document:
        raise NotFoundException("Dokument")
    
    # Check if already acknowledged
    existing = await db.staff_document_acknowledgements.find_one({
        "staff_document_id": document_id,
        "staff_member_id": staff["id"]
    })
    
    if existing:
        return {
            "success": True,
            "message": "Dokument wurde bereits bestätigt",
            "acknowledged_at": existing["acknowledged_at"]
        }
    
    # Create acknowledgement
    ack_id = str(uuid.uuid4())
    now = now_iso()
    
    acknowledgement = {
        "id": ack_id,
        "staff_document_id": document_id,
        "staff_member_id": staff["id"],
        "acknowledged_at": now,
        "source": "PWA",
        "device_id": data.device_id,
        "user_id": user.get("id"),
        "user_email": user.get("email")
    }
    
    await db.staff_document_acknowledgements.insert_one(acknowledgement)
    
    # Audit log
    await create_audit_log(
        user, "staff_document_acknowledgement", ack_id, "create",
        None,
        {"document_id": document_id, "document_title": document.get("title")}
    )
    
    return {
        "success": True,
        "message": "Dokument als gelesen bestätigt",
        "acknowledged_at": now
    }


@documents_router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Mitarbeiter: Dokument herunterladen.
    Nur eigene Dokumente.
    """
    staff = await get_staff_member_for_user(user)
    if not staff:
        raise HTTPException(status_code=400, detail="Kein Mitarbeiterprofil verknüpft")
    
    document = await db.staff_documents.find_one({
        "id": document_id,
        "staff_member_id": staff["id"]
    }, {"_id": 0})
    
    if not document:
        raise NotFoundException("Dokument")
    
    file_path = Path(document["file_path"])
    if not file_path.exists():
        raise NotFoundException("Datei nicht gefunden")
    
    return FileResponse(
        path=str(file_path),
        filename=document.get("file_name", "dokument.pdf"),
        media_type="application/octet-stream"
    )


# ============================================================
# ADMIN ABSENCES ENDPOINTS
# ============================================================

@admin_absences_router.get("")
async def list_absences(
    status: Optional[AbsenceStatus] = None,
    type: Optional[AbsenceType] = None,
    staff_member_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: dict = Depends(require_manager)
):
    """
    Admin/Manager: Alle Abwesenheiten auflisten.
    Mit Filtern für Status, Typ, Mitarbeiter, Zeitraum.
    """
    query = {}
    
    if status:
        query["status"] = status.value
    
    if type:
        query["type"] = type.value
    
    if staff_member_id:
        query["staff_member_id"] = staff_member_id
    
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to
        if date_query:
            query["start_date"] = date_query
    
    absences = await db.staff_absences.find(query, {"_id": 0}).sort("start_date", -1).to_list(1000)
    
    # Enrich with staff names and days count
    staff_ids = list(set(a["staff_member_id"] for a in absences))
    staff_map = {}
    if staff_ids:
        staff_members = await db.staff_members.find({"id": {"$in": staff_ids}}, {"_id": 0}).to_list(len(staff_ids))
        staff_map = {s["id"]: s for s in staff_members}
    
    for absence in absences:
        staff = staff_map.get(absence["staff_member_id"], {})
        absence["staff_name"] = staff.get("full_name") or f"{staff.get('first_name', '')} {staff.get('last_name', '')}".strip()
        absence["days_count"] = calculate_days(absence["start_date"], absence["end_date"])
    
    # Summary by status
    summary = {
        "total": len(absences),
        "requested": sum(1 for a in absences if a["status"] == AbsenceStatus.REQUESTED.value),
        "approved": sum(1 for a in absences if a["status"] == AbsenceStatus.APPROVED.value),
        "rejected": sum(1 for a in absences if a["status"] == AbsenceStatus.REJECTED.value),
        "cancelled": sum(1 for a in absences if a["status"] == AbsenceStatus.CANCELLED.value)
    }
    
    return {
        "success": True,
        "data": absences,
        "summary": summary
    }


@admin_absences_router.get("/pending")
async def list_pending_absences(user: dict = Depends(require_manager)):
    """
    Admin/Manager: Nur offene Anträge (REQUESTED).
    Für schnelle Übersicht.
    """
    absences = await db.staff_absences.find(
        {"status": AbsenceStatus.REQUESTED.value},
        {"_id": 0}
    ).sort("created_at", 1).to_list(500)
    
    # Enrich
    for absence in absences:
        absence["staff_name"] = await get_staff_name(absence["staff_member_id"])
        absence["days_count"] = calculate_days(absence["start_date"], absence["end_date"])
    
    return {
        "success": True,
        "data": absences,
        "count": len(absences)
    }


@admin_absences_router.get("/by-date/{date}")
async def get_absences_by_date(
    date: str,
    user: dict = Depends(require_manager)
):
    """
    Admin/Manager: Abwesenheiten für ein bestimmtes Datum.
    Für Tagesübersicht / Dienstplan-Integration.
    """
    # Find absences that include this date
    absences = await db.staff_absences.find({
        "status": AbsenceStatus.APPROVED.value,
        "start_date": {"$lte": date},
        "end_date": {"$gte": date}
    }, {"_id": 0}).to_list(500)
    
    # Enrich
    for absence in absences:
        absence["staff_name"] = await get_staff_name(absence["staff_member_id"])
    
    return {
        "success": True,
        "data": absences,
        "date": date,
        "count": len(absences)
    }


@admin_absences_router.post("/{absence_id}/approve")
async def approve_absence(
    absence_id: str,
    data: AbsenceAdminAction = AbsenceAdminAction(),
    user: dict = Depends(require_manager)
):
    """Admin/Manager: Abwesenheit genehmigen."""
    absence = await db.staff_absences.find_one({"id": absence_id}, {"_id": 0})
    
    if not absence:
        raise NotFoundException("Abwesenheit")
    
    if absence["status"] != AbsenceStatus.REQUESTED.value:
        raise HTTPException(
            status_code=409,
            detail=f"Antrag kann nicht genehmigt werden. Aktueller Status: {absence['status']}"
        )
    
    now = now_iso()
    update_data = {
        "status": AbsenceStatus.APPROVED.value,
        "notes_admin": data.notes_admin,
        "approved_by": user.get("id"),
        "approved_at": now,
        "updated_at": now
    }
    
    await db.staff_absences.update_one({"id": absence_id}, {"$set": update_data})
    
    # Audit log
    await create_audit_log(
        user, "staff_absence", absence_id, "approve",
        {"status": absence["status"]},
        {"status": AbsenceStatus.APPROVED.value}
    )
    
    return {
        "success": True,
        "message": "Abwesenheit genehmigt"
    }


@admin_absences_router.post("/{absence_id}/reject")
async def reject_absence(
    absence_id: str,
    data: AbsenceAdminAction,
    user: dict = Depends(require_manager)
):
    """Admin/Manager: Abwesenheit ablehnen."""
    absence = await db.staff_absences.find_one({"id": absence_id}, {"_id": 0})
    
    if not absence:
        raise NotFoundException("Abwesenheit")
    
    if absence["status"] != AbsenceStatus.REQUESTED.value:
        raise HTTPException(
            status_code=409,
            detail=f"Antrag kann nicht abgelehnt werden. Aktueller Status: {absence['status']}"
        )
    
    if not data.notes_admin:
        raise ValidationException("Bitte geben Sie einen Ablehnungsgrund an")
    
    now = now_iso()
    update_data = {
        "status": AbsenceStatus.REJECTED.value,
        "notes_admin": data.notes_admin,
        "rejected_by": user.get("id"),
        "rejected_at": now,
        "updated_at": now
    }
    
    await db.staff_absences.update_one({"id": absence_id}, {"$set": update_data})
    
    # Audit log
    await create_audit_log(
        user, "staff_absence", absence_id, "reject",
        {"status": absence["status"]},
        {"status": AbsenceStatus.REJECTED.value, "reason": data.notes_admin}
    )
    
    return {
        "success": True,
        "message": "Abwesenheit abgelehnt"
    }


@admin_absences_router.post("/{absence_id}/cancel")
async def admin_cancel_absence(
    absence_id: str,
    data: AbsenceAdminAction = AbsenceAdminAction(),
    user: dict = Depends(require_manager)
):
    """Admin/Manager: Abwesenheit stornieren (auch genehmigte)."""
    absence = await db.staff_absences.find_one({"id": absence_id}, {"_id": 0})
    
    if not absence:
        raise NotFoundException("Abwesenheit")
    
    if absence["status"] == AbsenceStatus.CANCELLED.value:
        raise HTTPException(status_code=409, detail="Abwesenheit ist bereits storniert")
    
    now = now_iso()
    update_data = {
        "status": AbsenceStatus.CANCELLED.value,
        "notes_admin": data.notes_admin or absence.get("notes_admin"),
        "cancelled_by": user.get("id"),
        "cancelled_at": now,
        "updated_at": now
    }
    
    await db.staff_absences.update_one({"id": absence_id}, {"$set": update_data})
    
    # Audit log
    await create_audit_log(
        user, "staff_absence", absence_id, "admin_cancel",
        {"status": absence["status"]},
        {"status": AbsenceStatus.CANCELLED.value}
    )
    
    return {
        "success": True,
        "message": "Abwesenheit storniert"
    }


# ============================================================
# ADMIN DOCUMENTS ENDPOINTS
# ============================================================

@admin_documents_router.get("/{staff_member_id}/documents")
async def list_staff_documents(
    staff_member_id: str,
    user: dict = Depends(require_manager)
):
    """Admin/Manager: Dokumente eines Mitarbeiters auflisten."""
    # Verify staff exists
    staff = await db.staff_members.find_one({"id": staff_member_id}, {"_id": 0})
    if not staff:
        raise NotFoundException("Mitarbeiter")
    
    documents = await db.staff_documents.find(
        {"staff_member_id": staff_member_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    
    # Get acknowledgements
    doc_ids = [d["id"] for d in documents]
    acknowledgements = await db.staff_document_acknowledgements.find(
        {"staff_document_id": {"$in": doc_ids}, "staff_member_id": staff_member_id},
        {"_id": 0}
    ).to_list(500)
    ack_map = {a["staff_document_id"]: a for a in acknowledgements}
    
    for doc in documents:
        ack = ack_map.get(doc["id"])
        doc["acknowledged"] = ack is not None
        doc["acknowledged_at"] = ack["acknowledged_at"] if ack else None
    
    staff_name = staff.get("full_name") or f"{staff.get('first_name', '')} {staff.get('last_name', '')}".strip()
    
    return {
        "success": True,
        "data": documents,
        "staff_member_id": staff_member_id,
        "staff_name": staff_name,
        "count": len(documents)
    }


@admin_documents_router.post("/{staff_member_id}/documents")
async def upload_staff_document(
    staff_member_id: str,
    file: UploadFile = File(...),
    title: str = Form(...),
    category: DocumentCategory = Form(...),
    requires_acknowledgement: bool = Form(False),
    user: dict = Depends(require_admin)
):
    """
    Admin: Dokument für Mitarbeiter hochladen.
    Nur Admin kann Dokumente hochladen (nicht Manager).
    """
    # Verify staff exists
    staff = await db.staff_members.find_one({"id": staff_member_id}, {"_id": 0})
    if not staff:
        raise NotFoundException("Mitarbeiter")
    
    # Validate file
    if not file.filename:
        raise ValidationException("Keine Datei ausgewählt")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationException(f"Dateityp nicht erlaubt. Erlaubt: {', '.join(ALLOWED_EXTENSIONS)}")
    
    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise ValidationException(f"Datei zu groß. Maximum: {MAX_FILE_SIZE // (1024*1024)}MB")
    
    # Generate file path and save
    file_path = generate_file_path(staff_member_id, file.filename)
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Check for existing document with same title to determine version
    existing = await db.staff_documents.find_one({
        "staff_member_id": staff_member_id,
        "title": title
    }, {"version": 1}, sort=[("version", -1)])
    
    version = (existing["version"] + 1) if existing else 1
    
    # Create document record
    doc_id = str(uuid.uuid4())
    now = now_iso()
    
    document = {
        "id": doc_id,
        "staff_member_id": staff_member_id,
        "title": title,
        "category": category.value,
        "file_path": str(file_path),
        "file_url": f"/api/admin/staff/{staff_member_id}/documents/{doc_id}/download",
        "file_name": file.filename,
        "file_size": len(content),
        "version": version,
        "requires_acknowledgement": requires_acknowledgement,
        "uploaded_by": user.get("id"),
        "created_at": now
    }
    
    await db.staff_documents.insert_one(document)
    
    # Audit log
    await create_audit_log(
        user, "staff_document", doc_id, "upload",
        None,
        {"staff_member_id": staff_member_id, "title": title, "category": category.value}
    )
    
    del document["_id"] if "_id" in document else None
    
    return {
        "success": True,
        "message": f"Dokument hochgeladen (Version {version})",
        "data": document
    }


@admin_documents_router.get("/{staff_member_id}/documents/{document_id}/download")
async def admin_download_document(
    staff_member_id: str,
    document_id: str,
    user: dict = Depends(require_manager)
):
    """Admin/Manager: Dokument herunterladen."""
    document = await db.staff_documents.find_one({
        "id": document_id,
        "staff_member_id": staff_member_id
    }, {"_id": 0})
    
    if not document:
        raise NotFoundException("Dokument")
    
    file_path = Path(document["file_path"])
    if not file_path.exists():
        raise NotFoundException("Datei nicht gefunden")
    
    return FileResponse(
        path=str(file_path),
        filename=document.get("file_name", "dokument.pdf"),
        media_type="application/octet-stream"
    )


@admin_documents_router.delete("/{staff_member_id}/documents/{document_id}")
async def delete_staff_document(
    staff_member_id: str,
    document_id: str,
    user: dict = Depends(require_admin)
):
    """Admin: Dokument löschen."""
    document = await db.staff_documents.find_one({
        "id": document_id,
        "staff_member_id": staff_member_id
    }, {"_id": 0})
    
    if not document:
        raise NotFoundException("Dokument")
    
    # Delete file
    file_path = Path(document["file_path"])
    if file_path.exists():
        file_path.unlink()
    
    # Delete document record
    await db.staff_documents.delete_one({"id": document_id})
    
    # Delete acknowledgements
    await db.staff_document_acknowledgements.delete_many({"staff_document_id": document_id})
    
    # Audit log
    await create_audit_log(
        user, "staff_document", document_id, "delete",
        {"title": document.get("title")},
        None
    )
    
    return {
        "success": True,
        "message": "Dokument gelöscht"
    }


# ============================================================
# INTEGRATION: TAGESÜBERSICHT MIT ABWESENHEITEN
# ============================================================

async def get_absences_for_daily_overview(day_key: str) -> List[dict]:
    """
    Helper für Tagesübersicht Integration.
    Gibt genehmigte Abwesenheiten für ein Datum zurück.
    """
    absences = await db.staff_absences.find({
        "status": AbsenceStatus.APPROVED.value,
        "start_date": {"$lte": day_key},
        "end_date": {"$gte": day_key}
    }, {"_id": 0}).to_list(500)
    
    for absence in absences:
        absence["staff_name"] = await get_staff_name(absence["staff_member_id"])
    
    return absences


async def check_absence_shift_conflict(staff_member_id: str, shift_date: str) -> Optional[dict]:
    """
    Prüft ob ein Mitarbeiter an einem bestimmten Datum abwesend ist.
    Für Warnung bei Schichtzuweisung.
    """
    absence = await db.staff_absences.find_one({
        "staff_member_id": staff_member_id,
        "status": AbsenceStatus.APPROVED.value,
        "start_date": {"$lte": shift_date},
        "end_date": {"$gte": shift_date}
    }, {"_id": 0})
    
    return absence
