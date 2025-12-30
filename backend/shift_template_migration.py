"""
Shift Templates Migration & Normalization Module
- Kanonisches V2 Schema
- Department Normalisierung mit Aliases
- V1 -> V2 Migration
- Master Import Endpoint

CANONICAL DEPARTMENT KEYS (lowercase):
- service
- kitchen
- reinigung
- eismacher
- kuechenhilfe

ALIASES:
- "Küche" -> kitchen
- "kueche" -> kitchen
- "cleaning" -> reinigung
- "ice_maker" -> eismacher
- "kitchen_help" -> kuechenhilfe
- "Restaurant" -> service (from V1 station)
- "Eis" -> eismacher (from V1 station)
"""

import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, field_validator

# Logging
logger = logging.getLogger("shift_template_migration")

# Router
migration_router = APIRouter(prefix="/api/admin/shift-templates", tags=["Shift Templates Migration"])

# MongoDB reference
db = None

def set_db(database):
    global db
    db = database


# ============== CANONICAL SCHEMA ==============

class CanonicalDepartment(str, Enum):
    """Kanonische Department Keys (lowercase)"""
    SERVICE = "service"
    KITCHEN = "kitchen"
    REINIGUNG = "reinigung"
    EISMACHER = "eismacher"
    KUECHENHILFE = "kuechenhilfe"

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

class EventMode(str, Enum):
    NORMAL = "normal"
    KULTUR = "kultur"


# ============== DEPARTMENT NORMALIZATION ==============

# Alias mapping to canonical keys
DEPARTMENT_ALIASES = {
    # Canonical -> Canonical (identity)
    "service": "service",
    "kitchen": "kitchen",
    "reinigung": "reinigung",
    "eismacher": "eismacher",
    "kuechenhilfe": "kuechenhilfe",
    
    # German variants
    "küche": "kitchen",
    "kueche": "kitchen",
    "kuche": "kitchen",
    
    # English variants
    "cleaning": "reinigung",
    "ice_maker": "eismacher",
    "icemaker": "eismacher",
    "kitchen_help": "kuechenhilfe",
    "kitchenhelp": "kuechenhilfe",
    
    # V1 station mappings
    "restaurant": "service",
    "eis": "eismacher",
    
    # Legacy/mixed case
    "Service": "service",
    "Kitchen": "kitchen",
    "Küche": "kitchen",
    "Reinigung": "reinigung",
    "Eismacher": "eismacher",
    "Küchenhilfe": "kuechenhilfe",
}

# V1 role -> department mapping
ROLE_TO_DEPARTMENT = {
    "service": "service",
    "schichtleiter": "service",
    "bar": "service",
    "aushilfe": "service",
    "kitchen": "kitchen",
    "kueche": "kitchen",
    "cleaning": "reinigung",
    "ice_maker": "eismacher",
    "kitchen_help": "kuechenhilfe",
}

# V1 station -> department mapping
STATION_TO_DEPARTMENT = {
    "Restaurant": "service",
    "restaurant": "service",
    "Küche": "kitchen",
    "küche": "kitchen",
    "Reinigung": "reinigung",
    "reinigung": "reinigung",
    "Eis": "eismacher",
    "eis": "eismacher",
}


def normalize_department(value: Any) -> str:
    """
    Normalize any department value to canonical lowercase key.
    
    Args:
        value: Can be string, enum value, or None
        
    Returns:
        Canonical department key (service, kitchen, reinigung, eismacher, kuechenhilfe)
        
    Raises:
        ValueError: If value cannot be normalized
    """
    if value is None:
        raise ValueError("Department cannot be None")
    
    # Convert to string
    str_value = str(value).strip()
    
    # Check direct alias mapping (case-insensitive)
    lower_value = str_value.lower()
    
    if lower_value in DEPARTMENT_ALIASES:
        return DEPARTMENT_ALIASES[lower_value]
    
    # Check if it's already a canonical key
    canonical_keys = [e.value for e in CanonicalDepartment]
    if lower_value in canonical_keys:
        return lower_value
    
    # Try role mapping
    if lower_value in ROLE_TO_DEPARTMENT:
        return ROLE_TO_DEPARTMENT[lower_value]
    
    # Try station mapping
    if str_value in STATION_TO_DEPARTMENT:
        return STATION_TO_DEPARTMENT[str_value]
    
    raise ValueError(f"Unknown department value: {value}")


def normalize_season(value: Any) -> str:
    """Normalize season value to canonical lowercase"""
    if value is None:
        return "all"
    
    str_value = str(value).lower().strip()
    
    if str_value in ["summer", "sommer"]:
        return "summer"
    elif str_value in ["winter"]:
        return "winter"
    else:
        return "all"


# ============== V2 TEMPLATE MODEL ==============

class ShiftTemplateV2(BaseModel):
    """Canonical V2 Shift Template Schema"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    department: str
    name: str = Field(..., min_length=2, max_length=100)
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end_time_type: EndTimeType
    end_time_fixed: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    close_plus_minutes: Optional[int] = Field(None, ge=0, le=180)
    season: SeasonType = SeasonType.ALL
    day_type: DayType = DayType.ALL
    event_mode: EventMode = EventMode.NORMAL
    headcount_default: int = Field(default=1, ge=1, le=20)
    sort_order: int = Field(default=0)
    active: bool = True
    archived: bool = False
    legacy: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    @field_validator('department', mode='before')
    @classmethod
    def normalize_dept(cls, v):
        return normalize_department(v)


# ============== V1 -> V2 MIGRATION ==============

def migrate_v1_to_v2(v1_template: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate a V1 template (role/station schema) to V2 (department schema).
    
    V1 Fields: code, role, station, start_time, end_time, season, event_mode (bool), is_default, active
    V2 Fields: department, name, start_time, end_time_type, end_time_fixed, season, day_type, event_mode (str), headcount_default, sort_order, active, archived, legacy
    """
    # Determine department from role or station
    department = None
    
    if v1_template.get("station"):
        try:
            department = normalize_department(v1_template["station"])
        except ValueError:
            pass
    
    if not department and v1_template.get("role"):
        try:
            department = normalize_department(v1_template["role"])
        except ValueError:
            pass
    
    if not department:
        department = "service"  # Default fallback
    
    # Build name
    name = v1_template.get("name", "")
    if not name:
        # Generate from code or times
        code = v1_template.get("code", "")
        start = v1_template.get("start_time", "00:00")
        end = v1_template.get("end_time", "00:00")
        name = f"{department.title()} {start}-{end}"
    
    # Normalize season
    season = normalize_season(v1_template.get("season"))
    
    # Event mode (V1 has bool, V2 has string)
    event_mode_v1 = v1_template.get("event_mode", False)
    event_mode = "kultur" if event_mode_v1 else "normal"
    
    # Build V2 template
    v2_template = {
        "id": v1_template.get("id", str(uuid.uuid4())),
        "department": department,
        "name": name,
        "start_time": v1_template.get("start_time", v1_template.get("start_time_local", "00:00")),
        "end_time_type": "fixed",
        "end_time_fixed": v1_template.get("end_time", v1_template.get("end_time_local")),
        "close_plus_minutes": None,
        "season": season,
        "day_type": "all",
        "event_mode": event_mode,
        "headcount_default": v1_template.get("headcount_default", 1),
        "sort_order": v1_template.get("sort_order", 0),
        "active": False,  # IMPORTANT: migrated templates are inactive
        "archived": True,
        "legacy": True,
        "legacy_code": v1_template.get("code"),
        "legacy_role": v1_template.get("role"),
        "legacy_station": v1_template.get("station"),
        "migrated_at": datetime.now(timezone.utc).isoformat(),
        "created_at": v1_template.get("created_at", datetime.now(timezone.utc).isoformat()),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    return v2_template


async def run_migration() -> Dict[str, Any]:
    """
    Run the V1 -> V2 migration.
    
    Steps:
    1. Find all V1 templates (have role/station, no department)
    2. Migrate each to V2 schema
    3. Update original V1 templates to archived=true, legacy=true
    4. Return migration report
    """
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "v1_found": 0,
        "migrated": 0,
        "updated": 0,
        "errors": [],
        "details": []
    }
    
    # Create audit log
    audit_entry = {
        "id": str(uuid.uuid4()),
        "type": "shift_templates_migration",
        "action": "v1_to_v2_migration",
        "started_at": report["started_at"],
        "actor": "system",
        "status": "running"
    }
    await db.audit_logs.insert_one(audit_entry)
    
    try:
        # Find V1 templates (have role OR station, but no department field OR have role/station pattern)
        # V1 pattern: has 'role' field and 'station' field, but 'department' is missing or has old format
        v1_query = {
            "$or": [
                {"role": {"$exists": True}, "department": {"$exists": False}},
                {"station": {"$exists": True}, "department": {"$exists": False}},
                {"role": {"$exists": True}, "end_time_type": {"$exists": False}},
            ]
        }
        
        v1_templates = await db.shift_templates.find(v1_query, {"_id": 0}).to_list(200)
        report["v1_found"] = len(v1_templates)
        
        logger.info(f"Found {len(v1_templates)} V1 templates to migrate")
        
        for v1_tpl in v1_templates:
            try:
                # Migrate to V2
                v2_tpl = migrate_v1_to_v2(v1_tpl)
                
                # Update the existing template with V2 fields
                update_data = {
                    "department": v2_tpl["department"],
                    "end_time_type": v2_tpl["end_time_type"],
                    "end_time_fixed": v2_tpl["end_time_fixed"],
                    "close_plus_minutes": v2_tpl["close_plus_minutes"],
                    "day_type": v2_tpl["day_type"],
                    "event_mode": v2_tpl["event_mode"],
                    "headcount_default": v2_tpl["headcount_default"],
                    "sort_order": v2_tpl["sort_order"],
                    "active": False,  # Deactivate migrated templates
                    "archived": True,
                    "legacy": True,
                    "legacy_code": v2_tpl.get("legacy_code"),
                    "legacy_role": v2_tpl.get("legacy_role"),
                    "legacy_station": v2_tpl.get("legacy_station"),
                    "migrated_at": v2_tpl["migrated_at"],
                    "updated_at": v2_tpl["updated_at"]
                }
                
                # Normalize season if present
                if v1_tpl.get("season"):
                    update_data["season"] = normalize_season(v1_tpl["season"])
                
                await db.shift_templates.update_one(
                    {"id": v1_tpl["id"]},
                    {"$set": update_data}
                )
                
                report["migrated"] += 1
                report["details"].append({
                    "id": v1_tpl["id"],
                    "name": v1_tpl.get("name", v1_tpl.get("code")),
                    "from_role": v1_tpl.get("role"),
                    "from_station": v1_tpl.get("station"),
                    "to_department": v2_tpl["department"],
                    "status": "migrated"
                })
                
            except Exception as e:
                report["errors"].append({
                    "id": v1_tpl.get("id"),
                    "error": str(e)
                })
                logger.error(f"Migration error for {v1_tpl.get('id')}: {e}")
        
        # Also update any existing V2 templates that are not using canonical department keys
        v2_non_canonical = await db.shift_templates.find({
            "department": {"$exists": True},
            "department": {"$nin": ["service", "kitchen", "reinigung", "eismacher", "kuechenhilfe"]}
        }, {"_id": 0}).to_list(100)
        
        for tpl in v2_non_canonical:
            try:
                old_dept = tpl.get("department")
                new_dept = normalize_department(old_dept)
                
                await db.shift_templates.update_one(
                    {"id": tpl["id"]},
                    {"$set": {
                        "department": new_dept,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                report["updated"] += 1
                
            except Exception as e:
                report["errors"].append({
                    "id": tpl.get("id"),
                    "error": f"Department normalization failed: {e}"
                })
        
        report["status"] = "success" if not report["errors"] else "partial"
        
    except Exception as e:
        report["status"] = "failed"
        report["error"] = str(e)
        logger.error(f"Migration failed: {e}")
    
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    
    # Update audit log
    await db.audit_logs.update_one(
        {"id": audit_entry["id"]},
        {"$set": {
            "status": report["status"],
            "finished_at": report["finished_at"],
            "result": {
                "v1_found": report["v1_found"],
                "migrated": report["migrated"],
                "updated": report["updated"],
                "errors": len(report["errors"])
            }
        }}
    )
    
    return report


# ============== MASTER IMPORT ==============

SEED_FILE_PATH = Path("/app/seed/shift_templates_master.json")

async def import_master_templates(
    archive_missing: bool = False
) -> Dict[str, Any]:
    """
    Import shift templates from master seed file.
    
    Args:
        archive_missing: If True, archive templates not in master file
        
    Returns:
        Import report with counts
    """
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "created": 0,
        "updated": 0,
        "archived": 0,
        "errors": [],
        "templates": []
    }
    
    # Check seed file exists
    if not SEED_FILE_PATH.exists():
        report["status"] = "error"
        report["error"] = f"Seed file not found: {SEED_FILE_PATH}"
        return report
    
    # Load master templates
    try:
        with open(SEED_FILE_PATH, 'r', encoding='utf-8') as f:
            master_data = json.load(f)
    except Exception as e:
        report["status"] = "error"
        report["error"] = f"Failed to load seed file: {e}"
        return report
    
    master_templates = master_data if isinstance(master_data, list) else master_data.get("templates", [])
    master_ids = set()
    
    for tpl_data in master_templates:
        try:
            # Normalize department
            if "department" in tpl_data:
                tpl_data["department"] = normalize_department(tpl_data["department"])
            
            # Ensure required fields
            tpl_id = tpl_data.get("id", str(uuid.uuid4()))
            tpl_data["id"] = tpl_id
            master_ids.add(tpl_id)
            
            tpl_data["active"] = tpl_data.get("active", True)
            tpl_data["archived"] = False
            tpl_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # Upsert
            existing = await db.shift_templates.find_one({"id": tpl_id})
            
            if existing:
                await db.shift_templates.update_one(
                    {"id": tpl_id},
                    {"$set": tpl_data}
                )
                report["updated"] += 1
            else:
                tpl_data["created_at"] = datetime.now(timezone.utc).isoformat()
                await db.shift_templates.insert_one(tpl_data)
                report["created"] += 1
            
            report["templates"].append({
                "id": tpl_id,
                "name": tpl_data.get("name"),
                "department": tpl_data.get("department"),
                "action": "updated" if existing else "created"
            })
            
        except Exception as e:
            report["errors"].append({
                "template": tpl_data.get("name", tpl_data.get("id")),
                "error": str(e)
            })
    
    # Archive templates not in master (if requested)
    if archive_missing:
        # Find active templates not in master
        non_master = await db.shift_templates.find({
            "id": {"$nin": list(master_ids)},
            "active": True,
            "archived": {"$ne": True}
        }, {"_id": 0}).to_list(200)
        
        for tpl in non_master:
            await db.shift_templates.update_one(
                {"id": tpl["id"]},
                {"$set": {
                    "active": False,
                    "archived": True,
                    "archived_reason": "not_in_master",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            report["archived"] += 1
    
    report["status"] = "success" if not report["errors"] else "partial"
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    
    # Audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "type": "shift_templates_import",
        "action": "master_import",
        "timestamp": report["finished_at"],
        "actor": "admin",
        "result": {
            "created": report["created"],
            "updated": report["updated"],
            "archived": report["archived"],
            "errors": len(report["errors"])
        }
    })
    
    return report


# ============== VERIFICATION ==============

async def verify_templates() -> Dict[str, Any]:
    """
    Verify shift templates state.
    
    Returns:
        Verification report
    """
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "READY",
        "issues": []
    }
    
    # Total count
    total = await db.shift_templates.count_documents({})
    active_count = await db.shift_templates.count_documents({"active": True, "archived": {"$ne": True}})
    archived_count = await db.shift_templates.count_documents({"archived": True})
    legacy_count = await db.shift_templates.count_documents({"legacy": True})
    
    report["counts"] = {
        "total": total,
        "active": active_count,
        "archived": archived_count,
        "legacy": legacy_count
    }
    
    # Check for V1 active templates (should be 0)
    v1_active = await db.shift_templates.count_documents({
        "active": True,
        "archived": {"$ne": True},
        "$or": [
            {"department": {"$exists": False}},
            {"end_time_type": {"$exists": False}}
        ]
    })
    
    if v1_active > 0:
        report["status"] = "ISSUES"
        report["issues"].append(f"Found {v1_active} active V1 templates (should be 0)")
    
    # Department counts (active only)
    pipeline = [
        {"$match": {"active": True, "archived": {"$ne": True}}},
        {"$group": {"_id": "$department", "count": {"$sum": 1}}}
    ]
    dept_counts = await db.shift_templates.aggregate(pipeline).to_list(20)
    report["departments"] = {d["_id"]: d["count"] for d in dept_counts}
    
    # Check for non-canonical departments
    canonical = ["service", "kitchen", "reinigung", "eismacher", "kuechenhilfe"]
    for dept in report["departments"].keys():
        if dept and dept not in canonical:
            report["status"] = "ISSUES"
            report["issues"].append(f"Non-canonical department found: {dept}")
    
    # Sample templates per department
    report["samples"] = {}
    for dept in canonical:
        samples = await db.shift_templates.find(
            {"department": dept, "active": True, "archived": {"$ne": True}},
            {"_id": 0, "id": 1, "name": 1, "start_time": 1, "end_time_fixed": 1}
        ).limit(3).to_list(3)
        report["samples"][dept] = samples
    
    # Final status
    if not report["issues"]:
        report["status"] = "READY"
    
    return report


# ============== API ENDPOINTS ==============

try:
    from core.auth import require_admin
except ImportError:
    async def require_admin():
        return {"role": "admin"}


@migration_router.post("/migrate-v1-to-v2")
async def api_migrate_v1_to_v2(user: dict = Depends(require_admin)):
    """
    Run V1 -> V2 migration (admin-only).
    Idempotent: can be run multiple times safely.
    """
    result = await run_migration()
    return result


@migration_router.post("/import-master")
async def api_import_master(
    archive_missing: bool = Query(False, description="Archive templates not in master file"),
    user: dict = Depends(require_admin)
):
    """
    Import shift templates from master seed file (admin-only).
    Source: /app/seed/shift_templates_master.json
    """
    result = await import_master_templates(archive_missing=archive_missing)
    return result


@migration_router.get("/verify")
async def api_verify(user: dict = Depends(require_admin)):
    """
    Verify shift templates state (admin-only).
    Returns READY if all checks pass.
    """
    result = await verify_templates()
    return result


@migration_router.get("/normalize-department")
async def api_normalize_department(
    value: str = Query(..., description="Department value to normalize"),
    user: dict = Depends(require_admin)
):
    """
    Test department normalization (admin-only).
    """
    try:
        canonical = normalize_department(value)
        return {
            "input": value,
            "canonical": canonical,
            "valid": True
        }
    except ValueError as e:
        return {
            "input": value,
            "canonical": None,
            "valid": False,
            "error": str(e)
        }
