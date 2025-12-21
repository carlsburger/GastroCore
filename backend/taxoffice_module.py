"""
GastroCore Tax Office Export Module - Sprint 6
Steuerbüro-Exporte, Versand und Mitarbeiter-Meldungen

ADDITIV - Keine Breaking Changes
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
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
import json
import logging
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# Core imports
from core.database import db
from core.auth import require_admin, require_manager, get_current_user
from core.audit import create_audit_log, safe_dict_for_audit, SYSTEM_ACTOR
from core.exceptions import NotFoundException, ValidationException

# Email service
from email_service import send_email_with_attachments

logger = logging.getLogger(__name__)


# ============== ENUMS ==============
class ExportJobStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    SENT = "sent"
    FAILED = "failed"


class ExportType(str, Enum):
    MONTHLY_HOURS = "monthly_hours"
    SHIFT_LIST = "shift_list"
    STAFF_REGISTRATION = "staff_registration"


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


def calculate_shift_hours(start_time: str, end_time: str) -> float:
    """Calculate hours from start and end time strings (HH:MM)"""
    try:
        start = datetime.strptime(start_time, "%H:%M")
        end = datetime.strptime(end_time, "%H:%M")
        if end < start:  # Overnight shift
            end += timedelta(days=1)
        diff = end - start
        return round(diff.total_seconds() / 3600, 2)
    except:
        return 0.0


def get_month_dates(year: int, month: int) -> tuple:
    """Get first and last day of a month"""
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    return first_day, last_day


def get_weeks_in_period(start_date: date, end_date: date) -> float:
    """Calculate number of weeks in a period"""
    days = (end_date - start_date).days + 1
    return days / 7.0


# ============== PYDANTIC MODELS ==============

class TaxOfficeSettings(BaseModel):
    recipient_emails: List[EmailStr] = []
    cc_emails: List[EmailStr] = []
    bcc_emails: List[EmailStr] = []
    sender_name: str = "GastroCore HR"
    subject_template: str = "{company} - Steuerbüro Export {period}"
    default_text_de: str = "Anbei finden Sie die Unterlagen für den Zeitraum {period}."
    default_text_en: str = "Please find attached the documents for the period {period}."
    default_text_pl: str = "W załączeniu dokumenty za okres {period}."
    filename_prefix: str = "carlsburg"
    auto_send_day: Optional[int] = None  # Day of month for auto-send
    is_active: bool = True


class TaxOfficeSettingsUpdate(BaseModel):
    recipient_emails: Optional[List[EmailStr]] = None
    cc_emails: Optional[List[EmailStr]] = None
    bcc_emails: Optional[List[EmailStr]] = None
    sender_name: Optional[str] = None
    subject_template: Optional[str] = None
    default_text_de: Optional[str] = None
    default_text_en: Optional[str] = None
    default_text_pl: Optional[str] = None
    filename_prefix: Optional[str] = None
    auto_send_day: Optional[int] = None
    is_active: Optional[bool] = None


class CreateExportJobRequest(BaseModel):
    export_type: ExportType
    year: int = Field(..., ge=2020, le=2030)
    month: int = Field(..., ge=1, le=12)
    include_pdf: bool = True
    include_csv: bool = True
    notes: Optional[str] = None


class SendExportRequest(BaseModel):
    language: str = Field(default="de", pattern="^(de|en|pl)$")
    custom_message: Optional[str] = None


class StaffRegistrationRequest(BaseModel):
    include_documents: List[str] = []  # Document IDs to include
    additional_notes: Optional[str] = None


# Extended Staff Fields for Tax Office
class StaffTaxFields(BaseModel):
    tax_id: Optional[str] = None  # Steuer-ID
    tax_class: Optional[str] = None  # Steuerklasse
    social_security_number: Optional[str] = None  # Sozialversicherungsnummer
    health_insurance: Optional[str] = None  # Krankenkasse
    bank_name: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    hourly_wage: Optional[float] = None
    monthly_salary: Optional[float] = None
    vacation_days: Optional[int] = None
    children_count: Optional[int] = None
    church_tax: Optional[bool] = None


# ============== ROUTER ==============
taxoffice_router = APIRouter(prefix="/api/taxoffice", tags=["Tax Office"])


# ============== SETTINGS ENDPOINTS ==============
@taxoffice_router.get("/settings")
async def get_taxoffice_settings(user: dict = Depends(require_admin)):
    """Get tax office settings"""
    settings = await db.taxoffice_settings.find_one({"type": "taxoffice"}, {"_id": 0})
    if not settings:
        # Return defaults
        return TaxOfficeSettings().model_dump()
    return settings


@taxoffice_router.patch("/settings")
async def update_taxoffice_settings(
    data: TaxOfficeSettingsUpdate,
    user: dict = Depends(require_admin)
):
    """Update tax office settings"""
    existing = await db.taxoffice_settings.find_one({"type": "taxoffice"})
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now_iso()
    update_data["type"] = "taxoffice"
    
    if existing:
        before = safe_dict_for_audit(existing)
        await db.taxoffice_settings.update_one({"type": "taxoffice"}, {"$set": update_data})
        await create_audit_log(user, "taxoffice_settings", "taxoffice", "update", before, update_data)
    else:
        update_data["created_at"] = now_iso()
        await db.taxoffice_settings.insert_one(update_data)
        await create_audit_log(user, "taxoffice_settings", "taxoffice", "create", None, update_data)
    
    return await db.taxoffice_settings.find_one({"type": "taxoffice"}, {"_id": 0})


# ============== EXPORT JOBS ==============
@taxoffice_router.get("/jobs")
async def list_export_jobs(
    year: Optional[int] = None,
    month: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(require_admin)
):
    """List export jobs"""
    query = {"archived": False}
    if year:
        query["year"] = year
    if month:
        query["month"] = month
    if status:
        query["status"] = status
    
    jobs = await db.export_jobs.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return jobs


@taxoffice_router.get("/jobs/{job_id}")
async def get_export_job(job_id: str, user: dict = Depends(require_admin)):
    """Get export job details"""
    job = await db.export_jobs.find_one({"id": job_id, "archived": False}, {"_id": 0})
    if not job:
        raise NotFoundException("Export-Job")
    return job


@taxoffice_router.post("/jobs")
async def create_export_job(
    data: CreateExportJobRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_admin)
):
    """Create a new export job"""
    
    # Check if job for this period already exists
    existing = await db.export_jobs.find_one({
        "export_type": data.export_type,
        "year": data.year,
        "month": data.month,
        "status": {"$in": ["ready", "sent"]},
        "archived": False
    })
    
    job = create_entity({
        "export_type": data.export_type,
        "year": data.year,
        "month": data.month,
        "status": ExportJobStatus.PENDING.value,
        "include_pdf": data.include_pdf,
        "include_csv": data.include_csv,
        "notes": data.notes,
        "created_by": user.get("email"),
        "files": [],
        "error": None
    })
    
    await db.export_jobs.insert_one(job)
    await create_audit_log(user, "export_job", job["id"], "create", None, safe_dict_for_audit(job))
    
    # Start generation in background
    background_tasks.add_task(generate_export_job, job["id"])
    
    return {k: v for k, v in job.items() if k != "_id"}


async def generate_export_job(job_id: str):
    """Background task to generate export files"""
    
    job = await db.export_jobs.find_one({"id": job_id})
    if not job:
        return
    
    try:
        await db.export_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": ExportJobStatus.GENERATING.value, "updated_at": now_iso()}}
        )
        
        year = job.get("year")
        month = job.get("month")
        export_type = job.get("export_type")
        
        start_date, end_date = get_month_dates(year, month)
        files = []
        
        # Get settings for filename prefix
        settings = await db.taxoffice_settings.find_one({"type": "taxoffice"}) or {}
        prefix = settings.get("filename_prefix", "export")
        period_str = f"{year}-{month:02d}"
        
        if export_type == ExportType.MONTHLY_HOURS.value:
            # Generate hours overview
            if job.get("include_csv"):
                csv_content = await generate_hours_csv(start_date, end_date)
                files.append({
                    "type": "csv",
                    "name": f"{prefix}_stunden_{period_str}.csv",
                    "content": csv_content,
                    "size": len(csv_content)
                })
            
            if job.get("include_pdf"):
                pdf_content = await generate_hours_pdf(start_date, end_date, year, month)
                files.append({
                    "type": "pdf",
                    "name": f"{prefix}_monatsbericht_{period_str}.pdf",
                    "content_base64": pdf_content,
                    "size": len(pdf_content)
                })
        
        elif export_type == ExportType.SHIFT_LIST.value:
            # Generate shift list
            if job.get("include_csv"):
                csv_content = await generate_shifts_csv(start_date, end_date)
                files.append({
                    "type": "csv",
                    "name": f"{prefix}_schichten_{period_str}.csv",
                    "content": csv_content,
                    "size": len(csv_content)
                })
        
        # Save file references
        await db.export_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": ExportJobStatus.READY.value,
                "files": files,
                "completed_at": now_iso(),
                "updated_at": now_iso()
            }}
        )
        
        logger.info(f"Export job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Export job {job_id} failed: {e}")
        await db.export_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": ExportJobStatus.FAILED.value,
                "error": str(e),
                "updated_at": now_iso()
            }}
        )


async def generate_hours_csv(start_date: date, end_date: date) -> str:
    """Generate hours overview CSV"""
    
    # Get all active staff members
    staff = await db.staff_members.find({"archived": False}, {"_id": 0}).to_list(500)
    
    # Get all shifts in period
    shifts = await db.shifts.find({
        "shift_date": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()},
        "archived": False
    }, {"_id": 0}).to_list(5000)
    
    # Calculate hours per staff member
    weeks_in_period = get_weeks_in_period(start_date, end_date)
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow([
        "Mitarbeiter-ID", "Name", "Beschäftigungsart", 
        "Zeitraum von", "Zeitraum bis",
        "Sollstunden (Periode)", "Geplante Stunden", "Ist-Stunden", "Differenz"
    ])
    
    for member in staff:
        member_shifts = [s for s in shifts if s.get("staff_member_id") == member.get("id")]
        planned_hours = sum(s.get("hours", 0) for s in member_shifts)
        
        # Calculate target hours for period
        weekly_hours = member.get("weekly_hours", 0)
        target_hours = round(weekly_hours * weeks_in_period, 2)
        
        # For now, ist = planned (no time entries yet)
        ist_hours = planned_hours
        
        writer.writerow([
            member.get("id"),
            member.get("full_name"),
            member.get("employment_type"),
            start_date.isoformat(),
            end_date.isoformat(),
            target_hours,
            round(planned_hours, 2),
            round(ist_hours, 2),
            round(ist_hours - target_hours, 2)
        ])
    
    return output.getvalue()


async def generate_shifts_csv(start_date: date, end_date: date) -> str:
    """Generate shift list CSV"""
    
    shifts = await db.shifts.find({
        "shift_date": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()},
        "archived": False
    }, {"_id": 0}).sort("shift_date", 1).to_list(5000)
    
    # Get staff and areas for enrichment
    staff_ids = list(set(s.get("staff_member_id") for s in shifts))
    area_ids = list(set(s.get("work_area_id") for s in shifts))
    
    staff = {s["id"]: s for s in await db.staff_members.find({"id": {"$in": staff_ids}}, {"_id": 0}).to_list(500)}
    areas = {a["id"]: a for a in await db.work_areas.find({"id": {"$in": area_ids}}, {"_id": 0}).to_list(100)}
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["Datum", "Start", "Ende", "Stunden", "Mitarbeiter", "Bereich", "Rolle"])
    
    for shift in shifts:
        staff_name = staff.get(shift.get("staff_member_id"), {}).get("full_name", "")
        area_name = areas.get(shift.get("work_area_id"), {}).get("name", "")
        hours = calculate_shift_hours(shift.get("start_time", "00:00"), shift.get("end_time", "00:00"))
        
        writer.writerow([
            shift.get("shift_date"),
            shift.get("start_time"),
            shift.get("end_time"),
            hours,
            staff_name,
            area_name,
            shift.get("role", "")
        ])
    
    return output.getvalue()


async def generate_hours_pdf(start_date: date, end_date: date, year: int, month: int) -> str:
    """Generate monthly report PDF"""
    import base64
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    
    # Get data
    staff = await db.staff_members.find({"archived": False}, {"_id": 0}).to_list(500)
    shifts = await db.shifts.find({
        "shift_date": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()},
        "archived": False
    }, {"_id": 0}).to_list(5000)
    
    weeks_in_period = get_weeks_in_period(start_date, end_date)
    
    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=20, alignment=1, spaceAfter=20)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=12, alignment=1, textColor=colors.grey)
    
    # Header
    elements.append(Paragraph("Monatsbericht Arbeitszeiten", title_style))
    
    month_names = ["", "Januar", "Februar", "März", "April", "Mai", "Juni", 
                   "Juli", "August", "September", "Oktober", "November", "Dezember"]
    elements.append(Paragraph(f"{month_names[month]} {year}", subtitle_style))
    elements.append(Paragraph(f"Zeitraum: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}", subtitle_style))
    elements.append(Paragraph(f"Erstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M')}", subtitle_style))
    elements.append(Spacer(1, 1*cm))
    
    # Summary table
    table_data = [["Mitarbeiter", "Beschäftigung", "Soll (h)", "Geplant (h)", "Ist (h)", "Differenz (h)"]]
    
    total_target = 0
    total_planned = 0
    total_ist = 0
    
    for member in staff:
        member_shifts = [s for s in shifts if s.get("staff_member_id") == member.get("id")]
        planned_hours = sum(s.get("hours", 0) for s in member_shifts)
        weekly_hours = member.get("weekly_hours", 0)
        target_hours = round(weekly_hours * weeks_in_period, 2)
        ist_hours = planned_hours  # For now
        diff = round(ist_hours - target_hours, 2)
        
        total_target += target_hours
        total_planned += planned_hours
        total_ist += ist_hours
        
        table_data.append([
            member.get("full_name"),
            member.get("employment_type", "-"),
            f"{target_hours:.1f}",
            f"{planned_hours:.1f}",
            f"{ist_hours:.1f}",
            f"{diff:+.1f}"
        ])
    
    # Totals row
    table_data.append([
        "GESAMT", "",
        f"{total_target:.1f}",
        f"{total_planned:.1f}",
        f"{total_ist:.1f}",
        f"{total_ist - total_target:+.1f}"
    ])
    
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0, 0.18, 0.01)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    
    # Return base64 encoded
    return base64.b64encode(buffer.read()).decode('utf-8')


# ============== DOWNLOAD EXPORT FILES ==============
@taxoffice_router.get("/jobs/{job_id}/download/{file_index}")
async def download_export_file(job_id: str, file_index: int, user: dict = Depends(require_admin)):
    """Download a file from an export job"""
    
    job = await db.export_jobs.find_one({"id": job_id, "archived": False})
    if not job:
        raise NotFoundException("Export-Job")
    
    files = job.get("files", [])
    if file_index >= len(files):
        raise NotFoundException("Datei")
    
    file_info = files[file_index]
    
    if file_info.get("type") == "csv":
        content = file_info.get("content", "")
        return StreamingResponse(
            iter([content]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=\"{file_info.get('name')}\""}
        )
    elif file_info.get("type") == "pdf":
        import base64
        content = base64.b64decode(file_info.get("content_base64", ""))
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=\"{file_info.get('name')}\""}
        )
    
    raise ValidationException("Unbekannter Dateityp")


# ============== SEND TO TAX OFFICE ==============
@taxoffice_router.post("/jobs/{job_id}/send")
async def send_to_taxoffice(
    job_id: str,
    data: SendExportRequest,
    user: dict = Depends(require_admin)
):
    """Send export to tax office via email"""
    
    job = await db.export_jobs.find_one({"id": job_id, "archived": False})
    if not job:
        raise NotFoundException("Export-Job")
    
    if job.get("status") != ExportJobStatus.READY.value:
        raise ValidationException("Export-Job ist nicht bereit zum Versand")
    
    settings = await db.taxoffice_settings.find_one({"type": "taxoffice"}) or {}
    
    recipients = settings.get("recipient_emails", [])
    if not recipients:
        raise ValidationException("Keine Empfänger-E-Mail konfiguriert")
    
    # Prepare email
    period_str = f"{job.get('month'):02d}/{job.get('year')}"
    subject = settings.get("subject_template", "Steuerbüro Export {period}").replace("{period}", period_str).replace("{company}", "GastroCore")
    
    # Get body text based on language
    body_templates = {
        "de": settings.get("default_text_de", "Anbei finden Sie die Unterlagen für den Zeitraum {period}."),
        "en": settings.get("default_text_en", "Please find attached the documents for the period {period}."),
        "pl": settings.get("default_text_pl", "W załączeniu dokumenty za okres {period}.")
    }
    body = data.custom_message or body_templates.get(data.language, body_templates["de"])
    body = body.replace("{period}", period_str)
    
    # Prepare attachments
    import base64
    attachments = []
    for file_info in job.get("files", []):
        if file_info.get("type") == "csv":
            attachments.append({
                "filename": file_info.get("name"),
                "content": file_info.get("content").encode('utf-8'),
                "content_type": "text/csv"
            })
        elif file_info.get("type") == "pdf":
            attachments.append({
                "filename": file_info.get("name"),
                "content": base64.b64decode(file_info.get("content_base64", "")),
                "content_type": "application/pdf"
            })
    
    # Send email
    try:
        await send_email_with_attachments(
            to_emails=recipients,
            cc_emails=settings.get("cc_emails", []),
            subject=subject,
            body=body,
            attachments=attachments
        )
        
        # Update job status
        await db.export_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": ExportJobStatus.SENT.value,
                "sent_at": now_iso(),
                "sent_to": recipients,
                "updated_at": now_iso()
            }}
        )
        
        # Create message log
        message_log = create_entity({
            "type": "taxoffice_export",
            "recipient": ", ".join(recipients),
            "subject": subject,
            "status": "sent",
            "job_id": job_id,
            "files": [f.get("name") for f in job.get("files", [])]
        })
        await db.message_logs.insert_one(message_log)
        
        # Audit log
        await create_audit_log(
            user, "export_job", job_id, "sent_to_taxoffice",
            {"status": "ready"}, {"status": "sent", "sent_to": recipients}
        )
        
        return {"message": "Export erfolgreich versendet", "success": True, "sent_to": recipients}
        
    except Exception as e:
        logger.error(f"Failed to send export {job_id}: {e}")
        
        # Log failed attempt
        message_log = create_entity({
            "type": "taxoffice_export",
            "recipient": ", ".join(recipients),
            "subject": subject,
            "status": "failed",
            "error": str(e),
            "job_id": job_id
        })
        await db.message_logs.insert_one(message_log)
        
        raise HTTPException(status_code=500, detail=f"Versand fehlgeschlagen: {str(e)}")


# ============== STAFF REGISTRATION PACKAGE ==============
@taxoffice_router.post("/staff-registration/{staff_id}")
async def create_staff_registration(
    staff_id: str,
    data: StaffRegistrationRequest,
    user: dict = Depends(require_admin)
):
    """Create staff registration package for tax office"""
    
    # Get staff member
    member = await db.staff_members.find_one({"id": staff_id, "archived": False}, {"_id": 0})
    if not member:
        raise NotFoundException("Mitarbeiter")
    
    # Get selected documents
    documents = []
    if data.include_documents:
        docs = await db.staff_documents.find({
            "id": {"$in": data.include_documents},
            "archived": False
        }, {"_id": 0}).to_list(100)
        documents = docs
    
    # Generate registration PDF
    pdf_content = await generate_staff_registration_pdf(member, documents, data.additional_notes)
    
    # Create export job
    job = create_entity({
        "export_type": ExportType.STAFF_REGISTRATION.value,
        "staff_member_id": staff_id,
        "staff_name": member.get("full_name"),
        "status": ExportJobStatus.READY.value,
        "include_pdf": True,
        "include_csv": False,
        "created_by": user.get("email"),
        "files": [{
            "type": "pdf",
            "name": f"mitarbeiter_anmeldung_{member.get('last_name', 'unknown').lower()}_{datetime.now().strftime('%Y%m%d')}.pdf",
            "content_base64": pdf_content,
            "size": len(pdf_content)
        }],
        "document_ids": data.include_documents
    })
    
    await db.export_jobs.insert_one(job)
    await create_audit_log(
        user, "export_job", job["id"], "create_staff_registration",
        None, {"staff_id": staff_id, "staff_name": member.get("full_name")}
    )
    
    return {k: v for k, v in job.items() if k != "_id"}


async def generate_staff_registration_pdf(member: dict, documents: list, notes: str = None) -> str:
    """Generate staff registration PDF"""
    import base64
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, alignment=1, spaceAfter=20)
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=14, spaceBefore=15, spaceAfter=10)
    
    # Header
    elements.append(Paragraph("Mitarbeiter-Anmeldung", title_style))
    elements.append(Paragraph(f"Erstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Personal Data
    elements.append(Paragraph("Personaldaten", section_style))
    
    personal_data = [
        ["Vorname:", member.get("first_name", "-")],
        ["Nachname:", member.get("last_name", "-")],
        ["E-Mail:", member.get("email", "-")],
        ["Telefon:", member.get("phone", "-")],
        ["Eintrittsdatum:", member.get("entry_date", "-")],
        ["Beschäftigungsart:", member.get("employment_type", "-")],
        ["Sollstunden/Woche:", f"{member.get('weekly_hours', 0)} h"],
        ["Rolle:", member.get("role", "-")],
    ]
    
    # Add tax fields if present
    tax_fields = member.get("tax_fields", {})
    if tax_fields:
        if tax_fields.get("tax_id"):
            personal_data.append(["Steuer-ID:", tax_fields.get("tax_id")])
        if tax_fields.get("tax_class"):
            personal_data.append(["Steuerklasse:", tax_fields.get("tax_class")])
        if tax_fields.get("social_security_number"):
            personal_data.append(["SV-Nummer:", tax_fields.get("social_security_number")])
        if tax_fields.get("health_insurance"):
            personal_data.append(["Krankenkasse:", tax_fields.get("health_insurance")])
        if tax_fields.get("iban"):
            personal_data.append(["IBAN:", tax_fields.get("iban")])
        if tax_fields.get("bic"):
            personal_data.append(["BIC:", tax_fields.get("bic")])
        if tax_fields.get("hourly_wage"):
            personal_data.append(["Stundenlohn:", f"{tax_fields.get('hourly_wage')} €"])
        if tax_fields.get("vacation_days"):
            personal_data.append(["Urlaubstage:", str(tax_fields.get("vacation_days"))])
    
    table = Table(personal_data, colWidths=[5*cm, 10*cm])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)
    
    # Documents
    if documents:
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("Beigefügte Dokumente", section_style))
        
        doc_data = [["Dokument", "Kategorie", "Hochgeladen"]]
        for doc in documents:
            doc_data.append([
                doc.get("original_filename", "-"),
                doc.get("category", "-"),
                doc.get("created_at", "-")[:10] if doc.get("created_at") else "-"
            ])
        
        doc_table = Table(doc_data, colWidths=[8*cm, 4*cm, 3*cm])
        doc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(doc_table)
    
    # Notes
    if notes:
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("Anmerkungen", section_style))
        elements.append(Paragraph(notes, styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')


# ============== STAFF TAX FIELDS UPDATE ==============
@taxoffice_router.patch("/staff/{staff_id}/tax-fields")
async def update_staff_tax_fields(
    staff_id: str,
    data: StaffTaxFields,
    user: dict = Depends(require_admin)
):
    """Update tax-related fields for a staff member (HR only)"""
    
    member = await db.staff_members.find_one({"id": staff_id, "archived": False}, {"_id": 0})
    if not member:
        raise NotFoundException("Mitarbeiter")
    
    before = safe_dict_for_audit(member)
    
    tax_fields = {k: v for k, v in data.model_dump().items() if v is not None}
    
    await db.staff_members.update_one(
        {"id": staff_id},
        {"$set": {"tax_fields": tax_fields, "updated_at": now_iso()}}
    )
    
    updated = await db.staff_members.find_one({"id": staff_id}, {"_id": 0})
    await create_audit_log(user, "staff_member", staff_id, "update_tax_fields", before, safe_dict_for_audit(updated))
    
    return {"message": "Steuerdaten aktualisiert", "success": True}


# ============== RETRY FAILED JOB ==============
@taxoffice_router.post("/jobs/{job_id}/retry")
async def retry_export_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_admin)
):
    """Retry a failed export job"""
    
    job = await db.export_jobs.find_one({"id": job_id, "archived": False})
    if not job:
        raise NotFoundException("Export-Job")
    
    if job.get("status") not in [ExportJobStatus.FAILED.value]:
        raise ValidationException("Nur fehlgeschlagene Jobs können wiederholt werden")
    
    await db.export_jobs.update_one(
        {"id": job_id},
        {"$set": {"status": ExportJobStatus.PENDING.value, "error": None, "updated_at": now_iso()}}
    )
    
    background_tasks.add_task(generate_export_job, job_id)
    
    await create_audit_log(user, "export_job", job_id, "retry", {"status": "failed"}, {"status": "pending"})
    
    return {"message": "Export-Job wird erneut ausgeführt", "success": True}
