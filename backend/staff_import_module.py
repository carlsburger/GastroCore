"""
Staff Import Module (Mode A – Strict Full Import + Merge)
==========================================================
CB Cockpit → Mitarbeiter → Import

Features:
- XLSX Import for staff_members
- Dry-Run (default ON)
- Deterministic merge (email → phone → personal_number)
- Schema normalization (role → roles[])
- Deactivation of missing staff (active=false)
- Idempotent execution

RULES:
- NO deletes, EVER
- NO seed data manipulation
- Audit logging for all imports
"""

import uuid
import hashlib
import logging
import io
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query, Header
from pydantic import BaseModel, Field

# Core imports
from core.database import db
from core.auth import require_admin

logger = logging.getLogger(__name__)

# Router
staff_import_router = APIRouter(prefix="/api/admin/staff/import", tags=["Staff Import"])


# ============== CONSTANTS ==============

# Canonical role keys (source of truth)
CANONICAL_ROLES = {
    "service",
    "bar",
    "kitchen",
    "reinigung",
    "eismacher",
    "kuechenhilfe",
    "aushilfe",
    "schichtleiter",
    "restaurantleiter",
    "kuechenchef",
    "souschef"
}

# Role normalization mapping
ROLE_NORMALIZATION_MAP = {
    # Kitchen variants
    "kueche": "kitchen",
    "küche": "kitchen",
    "koch": "kitchen",
    "köchin": "kitchen",
    "koechin": "kitchen",
    # Reinigung variants
    "reinigungskraft": "reinigung",
    "cleaning": "reinigung",
    "putzkraft": "reinigung",
    # Eismacher variants
    "ice_maker": "eismacher",
    "eis": "eismacher",
    "eisverkauf": "eismacher",
    # Kitchen help variants
    "kuechenhilfe": "kuechenhilfe",
    "küchenhilfe": "kuechenhilfe",
    "kitchen_help": "kuechenhilfe",
    # Service variants
    "kellner": "service",
    "kellnerin": "service",
    "servicekraft": "service",
    # Other
    "aushilfskraft": "aushilfe",
    "barkeeper": "bar",
    "barkraft": "bar",
}

# Excel column mappings (German → field)
EXCEL_COLUMN_MAP = {
    "vorname": "first_name",
    "nachname": "last_name",
    "first_name": "first_name",
    "last_name": "last_name",
    "email": "email",
    "e-mail": "email",
    "telefon": "phone",
    "phone": "phone",
    "mobil": "mobile_phone",
    "mobile": "mobile_phone",
    "mobile_phone": "mobile_phone",
    "personalnummer": "personal_number",
    "personal_number": "personal_number",
    "rolle": "role",
    "role": "role",
    "rollen": "roles",
    "roles": "roles",
    "abteilung": "department",
    "department": "department",
    "anstellungsart": "employment_type",
    "employment_type": "employment_type",
    "wochenstunden": "weekly_hours",
    "weekly_hours": "weekly_hours",
    "eintrittsdatum": "entry_date",
    "entry_date": "entry_date",
    "geburtsdatum": "date_of_birth",
    "date_of_birth": "date_of_birth",
    "strasse": "street",
    "street": "street",
    "straße": "street",
    "plz": "zip_code",
    "zip_code": "zip_code",
    "ort": "city",
    "city": "city",
    "steuer_id": "tax_id",
    "tax_id": "tax_id",
    "sv_nummer": "social_security_number",
    "social_security_number": "social_security_number",
    "krankenkasse": "health_insurance",
    "health_insurance": "health_insurance",
    "iban": "bank_iban",
    "bank_iban": "bank_iban",
    "notfallkontakt_name": "emergency_contact_name",
    "emergency_contact_name": "emergency_contact_name",
    "notfallkontakt_telefon": "emergency_contact_phone",
    "emergency_contact_phone": "emergency_contact_phone",
    "notizen": "notes",
    "notes": "notes",
    "aktiv": "active",
    "active": "active",
    "status": "status",
}


# ============== ENUMS ==============

class ImportMode(str, Enum):
    MODE_A = "A"  # Strict Full Import + Merge


class ImportAction(str, Enum):
    INSERT = "insert"
    UPDATE = "update"
    DEACTIVATE = "deactivate"
    SKIP = "skip"
    UNCHANGED = "unchanged"


class MatchMethod(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    PERSONAL_NUMBER = "personal_number"
    NAME_DOB = "name_dob"
    NONE = "none"


# ============== MODELS ==============

class ImportPlanItem(BaseModel):
    row: int
    action: ImportAction
    match_by: MatchMethod
    staff_id: Optional[str] = None
    excel_data: Dict[str, Any] = {}
    changes: Dict[str, Any] = {}
    reason: Optional[str] = None


class DuplicateCandidate(BaseModel):
    row: int
    reason: str
    candidates: List[str] = []
    match_field: Optional[str] = None


class ImportWarning(BaseModel):
    row: int
    field: str
    issue: str


class ImportCounts(BaseModel):
    insert: int = 0
    update: int = 0
    deactivate: int = 0
    unchanged: int = 0
    skipped: int = 0


class AnalyzeResponse(BaseModel):
    mode: str
    dry_run: bool
    strict_full_import: bool
    file_hash: str
    total_rows: int
    counts: ImportCounts
    plan: List[ImportPlanItem] = []
    duplicates: List[DuplicateCandidate] = []
    warnings: List[ImportWarning] = []


class ExecuteResponse(BaseModel):
    mode: str
    dry_run: bool
    strict_full_import: bool
    run_id: str
    file_hash: str
    total_rows: int
    counts: ImportCounts
    applied: List[Dict[str, Any]] = []
    errors: List[str] = []


# ============== HELPER FUNCTIONS ==============

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_phone(phone: str) -> str:
    """Normalize phone number to digits only, handle +49"""
    if not phone:
        return ""
    # Remove all non-digit characters except leading +
    cleaned = re.sub(r'[^\d+]', '', str(phone).strip())
    # Handle German country code
    if cleaned.startswith('+49'):
        cleaned = '0' + cleaned[3:]
    elif cleaned.startswith('0049'):
        cleaned = '0' + cleaned[4:]
    elif cleaned.startswith('49') and len(cleaned) > 10:
        cleaned = '0' + cleaned[2:]
    # Remove leading zeros for comparison (keep one)
    cleaned = re.sub(r'^0+', '0', cleaned)
    return cleaned


def normalize_email(email: str) -> str:
    """Normalize email to lowercase, stripped"""
    if not email:
        return ""
    return str(email).strip().lower()


def normalize_role(role_value: str) -> str:
    """Normalize a single role to canonical key"""
    if not role_value:
        return ""
    role_lower = str(role_value).strip().lower()
    # Check normalization map first
    if role_lower in ROLE_NORMALIZATION_MAP:
        return ROLE_NORMALIZATION_MAP[role_lower]
    # Check if already canonical
    if role_lower in CANONICAL_ROLES:
        return role_lower
    # Return as-is but log warning
    logger.warning(f"Unknown role value: {role_value}")
    return role_lower


def normalize_roles(role_input: Any) -> List[str]:
    """
    Normalize role(s) to roles[] array.
    Handles: string, comma-separated string, list
    """
    if not role_input:
        return []
    
    roles = []
    
    if isinstance(role_input, list):
        for r in role_input:
            normalized = normalize_role(str(r))
            if normalized and normalized not in roles:
                roles.append(normalized)
    elif isinstance(role_input, str):
        # Handle comma-separated
        parts = [p.strip() for p in role_input.split(',')]
        for part in parts:
            normalized = normalize_role(part)
            if normalized and normalized not in roles:
                roles.append(normalized)
    else:
        normalized = normalize_role(str(role_input))
        if normalized:
            roles.append(normalized)
    
    return roles


def calculate_file_hash(content: bytes) -> str:
    """Calculate SHA256 hash of file content"""
    return hashlib.sha256(content).hexdigest()[:16]


def map_excel_columns(headers: List[str]) -> Dict[int, str]:
    """Map Excel column indices to field names"""
    column_map = {}
    for idx, header in enumerate(headers):
        if header:
            header_lower = str(header).strip().lower().replace(' ', '_')
            if header_lower in EXCEL_COLUMN_MAP:
                column_map[idx] = EXCEL_COLUMN_MAP[header_lower]
            else:
                # Try direct match
                column_map[idx] = header_lower
    return column_map


def parse_xlsx(content: bytes) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parse XLSX file and return list of row dicts + list of headers.
    Uses openpyxl for XLSX parsing.
    """
    import openpyxl
    from openpyxl.utils.exceptions import InvalidFileException
    
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        
        rows_data = []
        headers = []
        column_map = {}
        
        for row_idx, row in enumerate(sheet.iter_rows(values_only=True)):
            if row_idx == 0:
                # Header row
                headers = [str(cell).strip() if cell else "" for cell in row]
                column_map = map_excel_columns(headers)
                continue
            
            # Data row
            row_dict = {"_row_number": row_idx + 1}  # 1-based row number
            has_data = False
            
            for col_idx, cell_value in enumerate(row):
                if col_idx in column_map:
                    field_name = column_map[col_idx]
                    if cell_value is not None and str(cell_value).strip():
                        row_dict[field_name] = cell_value
                        has_data = True
            
            if has_data:
                rows_data.append(row_dict)
        
        workbook.close()
        return rows_data, headers
        
    except InvalidFileException as e:
        raise ValueError(f"Invalid XLSX file: {e}")
    except Exception as e:
        raise ValueError(f"Error parsing XLSX: {e}")


def parse_employment_type(value: Any) -> str:
    """Parse employment type to canonical value"""
    if not value:
        return "teilzeit"
    val_lower = str(value).strip().lower()
    if val_lower in ["vollzeit", "full_time", "fulltime", "full-time", "voll"]:
        return "vollzeit"
    if val_lower in ["teilzeit", "part_time", "parttime", "part-time", "teil"]:
        return "teilzeit"
    if val_lower in ["minijob", "mini", "geringfügig", "450", "520"]:
        return "minijob"
    if val_lower in ["praktikum", "intern", "praktikant"]:
        return "praktikum"
    return "teilzeit"


def parse_date(value: Any) -> Optional[str]:
    """Parse date to YYYY-MM-DD format"""
    if not value:
        return None
    
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    
    val_str = str(value).strip()
    
    # Try common formats
    formats = [
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d-%m-%Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(val_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return None


def parse_bool(value: Any) -> bool:
    """Parse boolean value"""
    if isinstance(value, bool):
        return value
    if not value:
        return True  # Default active
    val_lower = str(value).strip().lower()
    return val_lower in ["true", "1", "ja", "yes", "aktiv", "active", "x"]


def row_to_staff_data(row: Dict[str, Any]) -> Dict[str, Any]:
    """Convert parsed Excel row to staff_member fields"""
    data = {}
    
    # Required fields
    if "first_name" in row:
        data["first_name"] = str(row["first_name"]).strip()
    if "last_name" in row:
        data["last_name"] = str(row["last_name"]).strip()
    
    # Identifiers
    if "email" in row:
        data["email"] = normalize_email(row["email"])
    if "phone" in row:
        data["phone"] = str(row["phone"]).strip()
        data["_phone_normalized"] = normalize_phone(row["phone"])
    if "mobile_phone" in row:
        data["mobile_phone"] = str(row["mobile_phone"]).strip()
    if "personal_number" in row:
        data["personal_number"] = str(row["personal_number"]).strip()
    
    # Role(s) - normalize to roles[]
    roles = []
    if "roles" in row:
        roles = normalize_roles(row["roles"])
    elif "role" in row:
        roles = normalize_roles(row["role"])
    elif "department" in row:
        roles = normalize_roles(row["department"])
    
    if roles:
        data["roles"] = roles
    
    # Employment
    if "employment_type" in row:
        data["employment_type"] = parse_employment_type(row["employment_type"])
    if "weekly_hours" in row:
        try:
            data["weekly_hours"] = float(row["weekly_hours"])
        except (ValueError, TypeError):
            pass
    
    # Dates
    if "entry_date" in row:
        parsed = parse_date(row["entry_date"])
        if parsed:
            data["entry_date"] = parsed
    if "date_of_birth" in row:
        parsed = parse_date(row["date_of_birth"])
        if parsed:
            data["date_of_birth"] = parsed
    
    # Address
    if "street" in row:
        data["street"] = str(row["street"]).strip()
    if "zip_code" in row:
        data["zip_code"] = str(row["zip_code"]).strip()
    if "city" in row:
        data["city"] = str(row["city"]).strip()
    
    # HR fields
    if "tax_id" in row:
        data["tax_id"] = str(row["tax_id"]).strip()
    if "social_security_number" in row:
        data["social_security_number"] = str(row["social_security_number"]).strip()
    if "health_insurance" in row:
        data["health_insurance"] = str(row["health_insurance"]).strip()
    if "bank_iban" in row:
        data["bank_iban"] = str(row["bank_iban"]).strip()
    
    # Emergency contact
    if "emergency_contact_name" in row:
        data["emergency_contact_name"] = str(row["emergency_contact_name"]).strip()
    if "emergency_contact_phone" in row:
        data["emergency_contact_phone"] = str(row["emergency_contact_phone"]).strip()
    
    # Notes
    if "notes" in row:
        data["notes"] = str(row["notes"]).strip()
    
    # Status
    if "active" in row:
        data["active"] = parse_bool(row["active"])
    if "status" in row:
        status_val = str(row["status"]).strip().lower()
        if status_val in ["aktiv", "active"]:
            data["status"] = "aktiv"
        elif status_val in ["inaktiv", "inactive"]:
            data["status"] = "inaktiv"
    
    return data


# ============== MATCHING LOGIC ==============

async def find_staff_matches(
    email: Optional[str],
    phone: Optional[str],
    personal_number: Optional[str],
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    date_of_birth: Optional[str] = None,
    enable_name_fallback: bool = False
) -> Tuple[List[Dict[str, Any]], MatchMethod]:
    """
    Find matching staff members in strict order:
    1. email (case-insensitive)
    2. phone (normalized)
    3. personal_number
    4. (optional) first_name + last_name + date_of_birth
    
    Returns: (list of matches, match method used)
    """
    
    # 1. Match by email
    if email:
        email_normalized = normalize_email(email)
        matches = await db.staff_members.find({
            "email": {"$regex": f"^{re.escape(email_normalized)}$", "$options": "i"},
            "archived": {"$ne": True}
        }, {"_id": 0}).to_list(10)
        
        if matches:
            return matches, MatchMethod.EMAIL
    
    # 2. Match by phone
    if phone:
        phone_normalized = normalize_phone(phone)
        if phone_normalized:
            # Get all staff and compare normalized phones
            all_staff = await db.staff_members.find({
                "phone": {"$exists": True, "$ne": None, "$ne": ""},
                "archived": {"$ne": True}
            }, {"_id": 0}).to_list(1000)
            
            matches = [
                s for s in all_staff
                if normalize_phone(s.get("phone", "")) == phone_normalized
            ]
            
            if matches:
                return matches, MatchMethod.PHONE
    
    # 3. Match by personal_number
    if personal_number:
        matches = await db.staff_members.find({
            "personal_number": str(personal_number).strip(),
            "archived": {"$ne": True}
        }, {"_id": 0}).to_list(10)
        
        if matches:
            return matches, MatchMethod.PERSONAL_NUMBER
    
    # 4. Fallback: name + date_of_birth
    if enable_name_fallback and first_name and last_name and date_of_birth:
        matches = await db.staff_members.find({
            "first_name": {"$regex": f"^{re.escape(first_name)}$", "$options": "i"},
            "last_name": {"$regex": f"^{re.escape(last_name)}$", "$options": "i"},
            "date_of_birth": date_of_birth,
            "archived": {"$ne": True}
        }, {"_id": 0}).to_list(10)
        
        if matches:
            return matches, MatchMethod.NAME_DOB
    
    return [], MatchMethod.NONE


def compute_changes(existing: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute what fields would change between existing and new data.
    Returns dict of {field: {"old": ..., "new": ...}}
    """
    changes = {}
    
    # Fields to compare
    compare_fields = [
        "first_name", "last_name", "email", "phone", "mobile_phone",
        "personal_number", "roles", "employment_type", "weekly_hours",
        "entry_date", "date_of_birth", "street", "zip_code", "city",
        "tax_id", "social_security_number", "health_insurance", "bank_iban",
        "emergency_contact_name", "emergency_contact_phone", "notes"
    ]
    
    for field in compare_fields:
        old_val = existing.get(field)
        new_val = new_data.get(field)
        
        # Skip if new value not provided
        if field not in new_data:
            continue
        
        # Handle roles[] specially (compare as sets)
        if field == "roles":
            old_roles = set(existing.get("roles", []))
            # Also check legacy 'role' field
            if not old_roles and existing.get("role"):
                old_roles = {normalize_role(existing["role"])}
            new_roles = set(new_val) if new_val else set()
            
            if old_roles != new_roles:
                changes[field] = {"old": list(old_roles), "new": list(new_roles)}
            continue
        
        # Compare values (handle None vs empty string)
        old_comparable = old_val if old_val else None
        new_comparable = new_val if new_val else None
        
        if old_comparable != new_comparable:
            changes[field] = {"old": old_val, "new": new_val}
    
    return changes


# ============== IMPORT LOGIC ==============

async def analyze_import(
    rows: List[Dict[str, Any]],
    mode: ImportMode,
    strict_full_import: bool,
    enable_name_fallback: bool = False
) -> AnalyzeResponse:
    """
    Analyze import file and create execution plan.
    This is the dry-run logic.
    """
    counts = ImportCounts()
    plan = []
    duplicates = []
    warnings = []
    
    # Track which staff IDs are in the import
    imported_staff_ids = set()
    
    for row in rows:
        row_num = row.get("_row_number", 0)
        staff_data = row_to_staff_data(row)
        
        # Validate minimum required fields
        if not staff_data.get("first_name") or not staff_data.get("last_name"):
            warnings.append(ImportWarning(
                row=row_num,
                field="first_name/last_name",
                issue="missing"
            ))
            plan.append(ImportPlanItem(
                row=row_num,
                action=ImportAction.SKIP,
                match_by=MatchMethod.NONE,
                excel_data=staff_data,
                reason="Missing required fields (first_name, last_name)"
            ))
            counts.skipped += 1
            continue
        
        # Check for identifiers
        has_identifier = any([
            staff_data.get("email"),
            staff_data.get("phone"),
            staff_data.get("personal_number")
        ])
        
        if not has_identifier:
            warnings.append(ImportWarning(
                row=row_num,
                field="email|phone|personal_number",
                issue="missing"
            ))
        
        # Find matches
        matches, match_method = await find_staff_matches(
            email=staff_data.get("email"),
            phone=staff_data.get("_phone_normalized") or staff_data.get("phone"),
            personal_number=staff_data.get("personal_number"),
            first_name=staff_data.get("first_name"),
            last_name=staff_data.get("last_name"),
            date_of_birth=staff_data.get("date_of_birth"),
            enable_name_fallback=enable_name_fallback
        )
        
        # Remove internal field
        staff_data.pop("_phone_normalized", None)
        
        if len(matches) > 1:
            # Multiple matches = ambiguous, report as duplicate
            duplicates.append(DuplicateCandidate(
                row=row_num,
                reason="multiple_matches",
                candidates=[m.get("id") for m in matches],
                match_field=match_method.value
            ))
            plan.append(ImportPlanItem(
                row=row_num,
                action=ImportAction.SKIP,
                match_by=match_method,
                excel_data=staff_data,
                reason=f"Multiple matches found ({len(matches)})"
            ))
            counts.skipped += 1
            continue
        
        if len(matches) == 1:
            # Single match = update candidate
            existing = matches[0]
            staff_id = existing.get("id")
            imported_staff_ids.add(staff_id)
            
            changes = compute_changes(existing, staff_data)
            
            if changes:
                plan.append(ImportPlanItem(
                    row=row_num,
                    action=ImportAction.UPDATE,
                    match_by=match_method,
                    staff_id=staff_id,
                    excel_data=staff_data,
                    changes=changes
                ))
                counts.update += 1
            else:
                plan.append(ImportPlanItem(
                    row=row_num,
                    action=ImportAction.UNCHANGED,
                    match_by=match_method,
                    staff_id=staff_id,
                    excel_data=staff_data
                ))
                counts.unchanged += 1
        else:
            # No match = insert
            plan.append(ImportPlanItem(
                row=row_num,
                action=ImportAction.INSERT,
                match_by=MatchMethod.NONE,
                excel_data=staff_data
            ))
            counts.insert += 1
    
    # MODE A: Deactivate missing staff
    if strict_full_import:
        # Get all active staff not in import
        all_active = await db.staff_members.find({
            "archived": {"$ne": True},
            "$or": [
                {"active": True},
                {"status": "aktiv"},
                {"active": {"$exists": False}}  # Default active
            ]
        }, {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "is_system": 1, "is_test": 1}).to_list(1000)
        
        for staff in all_active:
            staff_id = staff.get("id")
            if staff_id and staff_id not in imported_staff_ids:
                # Check exclusions
                if staff.get("is_system") or staff.get("is_test"):
                    continue
                
                plan.append(ImportPlanItem(
                    row=0,  # Not from Excel
                    action=ImportAction.DEACTIVATE,
                    match_by=MatchMethod.NONE,
                    staff_id=staff_id,
                    reason=f"Not in import file: {staff.get('first_name')} {staff.get('last_name')}"
                ))
                counts.deactivate += 1
    
    return AnalyzeResponse(
        mode=mode.value,
        dry_run=True,
        strict_full_import=strict_full_import,
        file_hash="",  # Will be set by caller
        total_rows=len(rows),
        counts=counts,
        plan=plan,
        duplicates=duplicates,
        warnings=warnings
    )


async def execute_import(
    plan: List[ImportPlanItem],
    run_id: str,
    user_id: str,
    file_hash: str
) -> ExecuteResponse:
    """
    Execute the import plan.
    This applies the actual changes to the database.
    """
    counts = ImportCounts()
    applied = []
    errors = []
    
    for item in plan:
        try:
            if item.action == ImportAction.INSERT:
                # Create new staff member
                new_staff = {
                    "id": str(uuid.uuid4()),
                    **item.excel_data,
                    "active": True,
                    "status": "aktiv",
                    "archived": False,
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                    "imported_at": now_iso(),
                    "imported_by": user_id,
                    "import_run_id": run_id
                }
                
                # Ensure roles[] exists
                if "roles" not in new_staff:
                    new_staff["roles"] = ["service"]  # Default
                
                await db.staff_members.insert_one(new_staff)
                
                applied.append({
                    "action": "insert",
                    "staff_id": new_staff["id"],
                    "row": item.row
                })
                counts.insert += 1
                
            elif item.action == ImportAction.UPDATE:
                # Update existing staff member
                update_data = {
                    **item.excel_data,
                    "updated_at": now_iso(),
                    "last_import_at": now_iso(),
                    "last_import_by": user_id,
                    "last_import_run_id": run_id
                }
                
                # Ensure roles[] migration
                if "roles" in update_data:
                    update_data["$unset"] = {"role": ""}  # Remove legacy field
                
                # Separate $unset from $set
                unset_data = update_data.pop("$unset", None)
                
                update_ops = {"$set": update_data}
                if unset_data:
                    update_ops["$unset"] = unset_data
                
                await db.staff_members.update_one(
                    {"id": item.staff_id},
                    update_ops
                )
                
                applied.append({
                    "action": "update",
                    "staff_id": item.staff_id,
                    "row": item.row,
                    "changes": item.changes
                })
                counts.update += 1
                
            elif item.action == ImportAction.DEACTIVATE:
                # Deactivate staff member
                await db.staff_members.update_one(
                    {"id": item.staff_id},
                    {"$set": {
                        "active": False,
                        "status": "inaktiv",
                        "deactivated_at": now_iso(),
                        "deactivated_by": user_id,
                        "deactivated_reason": "Not in import file (Mode A)",
                        "deactivation_import_run_id": run_id
                    }}
                )
                
                applied.append({
                    "action": "deactivate",
                    "staff_id": item.staff_id,
                    "reason": item.reason
                })
                counts.deactivate += 1
                
            elif item.action == ImportAction.UNCHANGED:
                counts.unchanged += 1
                
            elif item.action == ImportAction.SKIP:
                counts.skipped += 1
                
        except Exception as e:
            logger.error(f"Error executing import action for row {item.row}: {e}")
            errors.append(f"Row {item.row}: {str(e)}")
    
    return ExecuteResponse(
        mode="A",
        dry_run=False,
        strict_full_import=True,
        run_id=run_id,
        file_hash=file_hash,
        total_rows=len([p for p in plan if p.row > 0]),
        counts=counts,
        applied=applied,
        errors=errors
    )


# ============== API ENDPOINTS ==============

@staff_import_router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_staff_import(
    file: UploadFile = File(...),
    mode: str = Query("A", description="Import mode (A = Strict Full Import)"),
    strict_full_import: bool = Query(True, description="Deactivate staff not in file"),
    enable_name_fallback: bool = Query(False, description="Enable name+DOB matching as fallback"),
    user: dict = Depends(require_admin)
):
    """
    Analyze XLSX file for staff import (Dry-Run).
    
    Returns:
    - counts: How many inserts/updates/deactivations would happen
    - plan: Detailed action plan for each row
    - duplicates: Rows with ambiguous matches
    - warnings: Missing identifiers etc.
    """
    
    # Validate file type
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Only XLSX files are supported")
    
    # Read file content
    content = await file.read()
    file_hash = calculate_file_hash(content)
    
    # Parse XLSX
    try:
        rows, headers = parse_xlsx(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not rows:
        raise HTTPException(status_code=400, detail="No data rows found in file")
    
    # Analyze
    result = await analyze_import(
        rows=rows,
        mode=ImportMode.MODE_A,
        strict_full_import=strict_full_import,
        enable_name_fallback=enable_name_fallback
    )
    
    result.file_hash = file_hash
    
    logger.info(f"Staff import analyzed by {user.get('email')}: "
                f"insert={result.counts.insert}, update={result.counts.update}, "
                f"deactivate={result.counts.deactivate}, unchanged={result.counts.unchanged}")
    
    return result


@staff_import_router.post("/execute", response_model=ExecuteResponse)
async def execute_staff_import(
    file: UploadFile = File(...),
    mode: str = Query("A", description="Import mode (A = Strict Full Import)"),
    strict_full_import: bool = Query(True, description="Deactivate staff not in file"),
    enable_name_fallback: bool = Query(False, description="Enable name+DOB matching as fallback"),
    idempotency_key: str = Header(..., alias="Idempotency-Key", description="Unique key to prevent duplicate executions"),
    user: dict = Depends(require_admin)
):
    """
    Execute staff import from XLSX file.
    
    REQUIRES: Idempotency-Key header to prevent duplicate executions.
    
    Process:
    1. Parse and analyze file
    2. Check idempotency (same key = return previous result)
    3. Execute plan
    4. Log to staff_import_runs
    """
    
    # Validate file type
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Only XLSX files are supported")
    
    # Read file content
    content = await file.read()
    file_hash = calculate_file_hash(content)
    
    # Check idempotency
    existing_run = await db.staff_import_runs.find_one({
        "idempotency_key": idempotency_key
    })
    
    if existing_run:
        # Return previous result
        logger.info(f"Staff import idempotency hit: {idempotency_key}")
        return ExecuteResponse(
            mode=existing_run.get("mode", "A"),
            dry_run=False,
            strict_full_import=existing_run.get("strict_full_import", True),
            run_id=existing_run.get("run_id"),
            file_hash=existing_run.get("file_hash"),
            total_rows=existing_run.get("total_rows", 0),
            counts=ImportCounts(**existing_run.get("counts", {})),
            applied=existing_run.get("applied", []),
            errors=existing_run.get("errors", [])
        )
    
    # Parse XLSX
    try:
        rows, headers = parse_xlsx(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not rows:
        raise HTTPException(status_code=400, detail="No data rows found in file")
    
    # Analyze first (to get plan)
    analysis = await analyze_import(
        rows=rows,
        mode=ImportMode.MODE_A,
        strict_full_import=strict_full_import,
        enable_name_fallback=enable_name_fallback
    )
    
    # Generate run ID
    run_id = str(uuid.uuid4())
    user_id = user.get("id") or user.get("email")
    
    # Execute
    result = await execute_import(
        plan=analysis.plan,
        run_id=run_id,
        user_id=user_id,
        file_hash=file_hash
    )
    
    # Log to audit collection
    audit_log = {
        "id": str(uuid.uuid4()),
        "run_id": run_id,
        "idempotency_key": idempotency_key,
        "user_id": user_id,
        "user_email": user.get("email"),
        "timestamp": now_iso(),
        "file_name": file.filename,
        "file_hash": file_hash,
        "total_rows": len(rows),
        "mode": mode,
        "strict_full_import": strict_full_import,
        "counts": result.counts.model_dump(),
        "applied": result.applied,
        "errors": result.errors,
        "duplicates": [d.model_dump() for d in analysis.duplicates],
        "warnings": [w.model_dump() for w in analysis.warnings]
    }
    
    await db.staff_import_runs.insert_one(audit_log)
    
    logger.info(f"Staff import executed by {user.get('email')} (run_id={run_id}): "
                f"insert={result.counts.insert}, update={result.counts.update}, "
                f"deactivate={result.counts.deactivate}")
    
    return result


@staff_import_router.get("/history")
async def get_import_history(
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_admin)
):
    """
    Get history of staff import runs.
    """
    runs = await db.staff_import_runs.find(
        {},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {
        "runs": runs,
        "total": len(runs)
    }


@staff_import_router.get("/template")
async def get_import_template(user: dict = Depends(require_admin)):
    """
    Get column mapping info for import template.
    """
    return {
        "required_columns": ["Vorname", "Nachname"],
        "identifier_columns": ["Email", "Telefon", "Personalnummer"],
        "optional_columns": [
            "Rollen", "Anstellungsart", "Wochenstunden", "Eintrittsdatum",
            "Geburtsdatum", "Straße", "PLZ", "Ort",
            "Steuer_ID", "SV_Nummer", "Krankenkasse", "IBAN",
            "Notfallkontakt_Name", "Notfallkontakt_Telefon", "Notizen", "Aktiv"
        ],
        "role_values": list(CANONICAL_ROLES),
        "employment_type_values": ["vollzeit", "teilzeit", "minijob", "praktikum"],
        "notes": [
            "At least one identifier (Email, Telefon, or Personalnummer) recommended",
            "Rollen can be comma-separated for multiple roles",
            "Dates should be in format YYYY-MM-DD or DD.MM.YYYY"
        ]
    }
