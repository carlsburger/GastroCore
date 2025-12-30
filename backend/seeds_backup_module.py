"""
Modul 10_COCKPIT – Backup & Restore (System-Seeds) V1

Sicheres, reproduzierbares Backup-&-Restore-Modul für systemrelevante
Konfigurationen (Seeds) des Carlsburg Cockpits.

SEED-SCOPE:
- opening_hours_master
- opening_hours_periods
- shift_templates (canonical V2 schema)
- reservation_slot_rules
- reservation_options
- reservation_slot_exceptions
- system_settings

NICHT enthalten: shifts, reservations, guests, logs, time tracking, POS
"""

import os
import io
import json
import zipfile
import logging
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Logging
logger = logging.getLogger("seeds_backup")

# Router
seeds_router = APIRouter(prefix="/api/admin/seeds", tags=["Seeds Backup & Restore"])

# MongoDB - import from core.database
try:
    from core.database import db
except ImportError:
    db = None

# Auth
try:
    from core.auth import require_admin
except ImportError:
    async def require_admin():
        return {"role": "admin", "email": "admin@carlsburg.de"}


# ============== CONFIGURATION ==============

# Seed collections and their export paths
SEED_COLLECTIONS = {
    "opening_hours_master": {
        "collection": "opening_hours_master",
        "export_path": "seed/opening_hours/opening_hours_master.json",
        "filter": {"active": True},  # active=true
        "order": 2
    },
    "opening_hours_periods": {
        "collection": "opening_hours_periods",
        "export_path": "seed/opening_hours/opening_hours_periods.json",
        "filter": {"archived": {"$ne": True}},  # archived=false (active egal)
        "order": 3
    },
    "shift_templates": {
        "collection": "shift_templates",
        "export_path": "seed/shift_templates/shift_templates_master.json",
        "filter": {"active": True, "archived": False},  # active=true, archived=false
        "order": 4
    },
    "reservation_slot_rules": {
        "collection": "reservation_slot_rules",
        "export_path": "seed/reservations/reservation_slot_rules.json",
        "filter": {"active": True},  # active=true
        "order": 6
    },
    "reservation_options": {
        "collection": "reservation_options",
        "export_path": "seed/reservations/reservation_options.json",
        "filter": {"active": True},  # active=true
        "order": 5
    },
    "reservation_slot_exceptions": {
        "collection": "reservation_slot_exceptions",
        "export_path": "seed/reservations/reservation_slot_exceptions.json",
        "filter": {"archived": {"$ne": True}},  # archived=false (active egal)
        "order": 7
    },
    "system_settings": {
        "collection": "system_settings",
        "export_path": "seed/system/system_settings.json",
        "filter": {},  # alle
        "order": 1
    }
}

# Import order (verbindlich)
IMPORT_ORDER = [
    "system_settings",
    "opening_hours_master",
    "opening_hours_periods",
    "shift_templates",
    "reservation_options",
    "reservation_slot_rules",
    "reservation_slot_exceptions"
]


# ============== MODELS ==============

class ImportOptions(BaseModel):
    dry_run: bool = Field(default=True, description="Preview only, no DB changes")
    archive_missing: bool = Field(default=False, description="Archive items not in seed")
    force_overwrite: bool = Field(default=False, description="Overwrite even if newer")

class ImportResult(BaseModel):
    status: str  # "success", "dry_run", "error"
    created: int = 0
    updated: int = 0
    archived: int = 0
    skipped: int = 0
    warnings: List[str] = []
    errors: List[str] = []
    details: Dict[str, Any] = {}

class VerifyResult(BaseModel):
    status: str  # "READY", "WARNINGS", "STOP"
    checks: Dict[str, Any] = {}
    warnings: List[str] = []
    errors: List[str] = []


# ============== HASH / FINGERPRINT ==============

def calculate_content_hash(content: str) -> str:
    """Calculate SHA256 hash of content, return first 12 chars"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:12]

def calculate_seeds_fingerprint(seed_data: Dict[str, List[dict]]) -> str:
    """
    Calculate a deterministic fingerprint for seed data.
    Sorts keys and values for consistent hashing.
    """
    # Create sorted, deterministic JSON representation
    sorted_data = {}
    for key in sorted(seed_data.keys()):
        docs = seed_data[key]
        # Sort documents by id for consistency
        sorted_docs = sorted(docs, key=lambda x: x.get('id', ''))
        sorted_data[key] = sorted_docs
    
    canonical_json = json.dumps(sorted_data, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()[:12]

async def get_current_seeds_fingerprint() -> Dict[str, Any]:
    """
    Calculate fingerprint of current DB seed state.
    Returns hash and metadata.
    """
    seed_data = {}
    
    for name, config in SEED_COLLECTIONS.items():
        collection = db[config["collection"]]
        filter_query = config.get("filter", {})
        docs = await collection.find(filter_query, {"_id": 0}).to_list(1000)
        
        # Clean documents
        cleaned_docs = []
        for doc in docs:
            cleaned = clean_document(doc)
            if name == "shift_templates" and "department" in cleaned:
                cleaned["department"] = normalize_department(cleaned["department"])
            cleaned_docs.append(cleaned)
        
        seed_data[name] = cleaned_docs
    
    fingerprint = calculate_seeds_fingerprint(seed_data)
    
    return {
        "fingerprint": fingerprint,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
        "collections": {name: len(docs) for name, docs in seed_data.items()}
    }


# ============== EXPORT FUNCTIONS ==============

def clean_document(doc: dict) -> dict:
    """Remove MongoDB _id and normalize for export"""
    cleaned = {k: v for k, v in doc.items() if k != "_id"}
    return cleaned

def normalize_department(value: str) -> str:
    """Normalize department to canonical key"""
    if not value:
        return value
    aliases = {
        "küche": "kitchen",
        "kueche": "kitchen",
        "cleaning": "reinigung",
        "ice_maker": "eismacher",
        "kitchen_help": "kuechenhilfe",
    }
    return aliases.get(value.lower(), value.lower())

async def export_collection(name: str) -> Tuple[List[dict], int]:
    """Export a single collection, returns (documents, count)"""
    config = SEED_COLLECTIONS.get(name)
    if not config:
        return [], 0
    
    collection = db[config["collection"]]
    filter_query = config.get("filter", {})
    
    docs = await collection.find(filter_query, {"_id": 0}).to_list(1000)
    
    # Clean and normalize
    cleaned_docs = []
    for doc in docs:
        cleaned = clean_document(doc)
        
        # Normalize shift_templates departments
        if name == "shift_templates" and "department" in cleaned:
            cleaned["department"] = normalize_department(cleaned["department"])
        
        cleaned_docs.append(cleaned)
    
    return cleaned_docs, len(cleaned_docs)

async def create_backup_zip() -> Tuple[io.BytesIO, Dict[str, int], str]:
    """Create ZIP backup of all seed collections. Returns (buffer, counts, fingerprint)"""
    buffer = io.BytesIO()
    counts = {}
    seed_data = {}
    
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name, config in SEED_COLLECTIONS.items():
            docs, count = await export_collection(name)
            counts[name] = count
            seed_data[name] = docs
            
            # Create JSON content
            json_content = json.dumps(docs, indent=2, ensure_ascii=False, default=str)
            
            # Add to ZIP
            zf.writestr(config["export_path"], json_content)
        
        # Calculate fingerprint
        fingerprint = calculate_seeds_fingerprint(seed_data)
        
        # Add manifest with fingerprint
        manifest = {
            "version": "1.0",
            "fingerprint": fingerprint,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "counts": counts
        }
        zf.writestr("seed/manifest.json", json.dumps(manifest, indent=2))
    
    buffer.seek(0)
    return buffer, counts, fingerprint


# ============== IMPORT FUNCTIONS ==============

def validate_zip_structure(zf: zipfile.ZipFile) -> Tuple[bool, List[str]]:
    """Validate ZIP file structure"""
    errors = []
    expected_files = [config["export_path"] for config in SEED_COLLECTIONS.values()]
    
    actual_files = zf.namelist()
    
    for expected in expected_files:
        if expected not in actual_files:
            # Warning, not error - file might be optional
            pass
    
    # Check for unexpected files
    seed_files = [f for f in actual_files if f.startswith("seed/") and f.endswith(".json")]
    
    return len(errors) == 0, errors

def parse_seed_file(zf: zipfile.ZipFile, path: str) -> Tuple[List[dict], List[str]]:
    """Parse a single seed JSON file from ZIP"""
    errors = []
    docs = []
    
    try:
        content = zf.read(path).decode('utf-8')
        data = json.loads(content)
        
        if isinstance(data, list):
            docs = data
        elif isinstance(data, dict) and "templates" in data:
            # Handle wrapped format
            docs = data.get("templates", [])
        elif isinstance(data, dict) and "items" in data:
            docs = data.get("items", [])
        else:
            # Single document
            docs = [data] if data else []
            
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in {path}: {e}")
    except Exception as e:
        errors.append(f"Error reading {path}: {e}")
    
    return docs, errors

async def import_collection(
    name: str, 
    docs: List[dict], 
    options: ImportOptions
) -> Dict[str, Any]:
    """Import documents into a collection"""
    result = {
        "created": 0,
        "updated": 0,
        "archived": 0,
        "skipped": 0,
        "warnings": [],
        "errors": []
    }
    
    config = SEED_COLLECTIONS.get(name)
    if not config:
        result["errors"].append(f"Unknown collection: {name}")
        return result
    
    collection = db[config["collection"]]
    now = datetime.now(timezone.utc).isoformat()
    
    imported_ids = set()
    
    for doc in docs:
        try:
            doc_id = doc.get("id")
            if not doc_id:
                # Generate ID if missing
                doc_id = str(uuid.uuid4())
                doc["id"] = doc_id
            
            imported_ids.add(doc_id)
            
            # Normalize department for shift_templates
            if name == "shift_templates" and "department" in doc:
                doc["department"] = normalize_department(doc["department"])
            
            # Check existing
            existing = await collection.find_one({"id": doc_id})
            
            if existing:
                # Update
                if not options.dry_run:
                    doc["updated_at"] = now
                    doc["_seed_imported"] = True
                    await collection.update_one(
                        {"id": doc_id},
                        {"$set": doc}
                    )
                result["updated"] += 1
            else:
                # Create
                if not options.dry_run:
                    doc["created_at"] = now
                    doc["updated_at"] = now
                    doc["_seed_imported"] = True
                    await collection.insert_one(doc)
                result["created"] += 1
                
        except Exception as e:
            result["errors"].append(f"Error importing {doc.get('id', 'unknown')}: {e}")
    
    # Archive missing (if requested)
    if options.archive_missing and not options.dry_run:
        # Find documents not in import
        existing_docs = await collection.find(
            {"id": {"$nin": list(imported_ids)}, "archived": {"$ne": True}},
            {"id": 1}
        ).to_list(1000)
        
        for doc in existing_docs:
            await collection.update_one(
                {"id": doc["id"]},
                {"$set": {"archived": True, "updated_at": now}}
            )
            result["archived"] += 1
    
    return result


# ============== VERIFY FUNCTIONS ==============

async def verify_seeds() -> VerifyResult:
    """Verify seed data integrity"""
    result = VerifyResult(status="READY", checks={}, warnings=[], errors=[])
    
    # Check 1: Opening hours master (contains seasonal periods)
    # NOTE: opening_hours_master stores multiple period documents (Sommer/Winter)
    # This is the CORRECT architecture - we check for at least 1 active period
    ohm_active_count = await db.opening_hours_master.count_documents({"active": True, "archived": {"$ne": True}})
    ohm_total_count = await db.opening_hours_master.count_documents({})
    result.checks["opening_hours_master"] = {
        "count": ohm_total_count, 
        "active": ohm_active_count,
        "status": "ok"
    }
    if ohm_active_count == 0:
        result.warnings.append("No active opening_hours_master periods found - widget may show default hours")
        result.checks["opening_hours_master"]["status"] = "warning"
    
    # Check 2: Opening hours periods (LEGACY - may be empty)
    # NOTE: Some modules still use opening_hours_periods, but opening_hours_master is Source of Truth
    # We only log info, not warning, as this collection is being phased out
    ohp_count = await db.opening_hours_periods.count_documents({"active": True})
    result.checks["opening_hours_periods"] = {
        "count": ohp_count, 
        "status": "ok",
        "note": "Legacy collection - opening_hours_master is Source of Truth"
    }
    
    # Check 3: Shift templates (at least 1 active)
    st_count = await db.shift_templates.count_documents({"active": True, "archived": {"$ne": True}})
    result.checks["shift_templates"] = {"count": st_count, "status": "ok"}
    if st_count == 0:
        result.errors.append("No active shift_templates found")
        result.checks["shift_templates"]["status"] = "error"
    
    # Check 4: Shift template departments (enum consistency)
    valid_departments = ["service", "kitchen", "reinigung", "eismacher", "kuechenhilfe"]
    invalid_depts = await db.shift_templates.find(
        {
            "active": True,
            "archived": {"$ne": True},
            "department": {"$nin": valid_departments}
        },
        {"id": 1, "department": 1}
    ).to_list(100)
    
    if invalid_depts:
        result.warnings.append(f"Found {len(invalid_depts)} shift_templates with non-canonical departments")
        result.checks["shift_template_departments"] = {
            "invalid_count": len(invalid_depts),
            "status": "warning"
        }
    else:
        result.checks["shift_template_departments"] = {"status": "ok"}
    
    # Check 5: Reservation options
    ro_count = await db.reservation_options.count_documents({})
    result.checks["reservation_options"] = {"count": ro_count, "status": "ok"}
    
    # Check 6: Reservation slot rules
    rsr_count = await db.reservation_slot_rules.count_documents({})
    result.checks["reservation_slot_rules"] = {"count": rsr_count, "status": "ok"}
    
    # Check 7: System settings
    ss_count = await db.system_settings.count_documents({})
    result.checks["system_settings"] = {"count": ss_count, "status": "ok"}
    if ss_count == 0:
        result.warnings.append("No system_settings document found")
        result.checks["system_settings"]["status"] = "warning"
    
    # Determine overall status
    if result.errors:
        result.status = "STOP"
    elif result.warnings:
        result.status = "WARNINGS"
    else:
        result.status = "READY"
    
    return result


# ============== API ENDPOINTS ==============

@seeds_router.get("/export")
async def export_seeds(user: dict = Depends(require_admin)):
    """
    Export all seed collections as ZIP file.
    READ-ONLY operation, never destructive.
    """
    try:
        # Create backup with fingerprint
        zip_buffer, counts, fingerprint = await create_backup_zip()
        
        # Generate filename with fingerprint
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        filename = f"carlsburg_system_seeds_{timestamp}_{fingerprint}.zip"
        
        # Audit log
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "type": "seeds_backup",
            "action": "export",
            "user": user.get("email", user.get("sub", "unknown")),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "result": {
                "status": "success",
                "filename": filename,
                "fingerprint": fingerprint,
                "counts": counts
            }
        })
        
        logger.info(f"Seeds exported by {user.get('email')}: fingerprint={fingerprint}, counts={counts}")
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@seeds_router.post("/import")
async def import_seeds(
    file: UploadFile = File(...),
    dry_run: bool = Query(True, description="Preview only, no DB changes"),
    archive_missing: bool = Query(False, description="Archive items not in seed"),
    force_overwrite: bool = Query(False, description="Overwrite even if newer"),
    user: dict = Depends(require_admin)
):
    """
    Import seeds from ZIP file.
    
    - dry_run=true (default): Preview only, no changes
    - archive_missing: Archive documents not in the import
    - force_overwrite: Overwrite even if DB version is newer
    """
    options = ImportOptions(
        dry_run=dry_run,
        archive_missing=archive_missing,
        force_overwrite=force_overwrite
    )
    
    result = ImportResult(
        status="dry_run" if dry_run else "success",
        details={}
    )
    
    try:
        # Read and validate ZIP
        content = await file.read()
        
        try:
            zf = zipfile.ZipFile(io.BytesIO(content))
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid ZIP file")
        
        # Validate structure
        is_valid, validation_errors = validate_zip_structure(zf)
        if validation_errors:
            result.warnings.extend(validation_errors)
        
        # Import in order
        for collection_name in IMPORT_ORDER:
            config = SEED_COLLECTIONS.get(collection_name)
            if not config:
                continue
            
            export_path = config["export_path"]
            
            if export_path not in zf.namelist():
                result.warnings.append(f"Missing file: {export_path}")
                continue
            
            # Parse file
            docs, parse_errors = parse_seed_file(zf, export_path)
            if parse_errors:
                result.errors.extend(parse_errors)
                continue
            
            if not docs:
                result.details[collection_name] = {"skipped": True, "reason": "empty"}
                continue
            
            # Import
            import_result = await import_collection(collection_name, docs, options)
            
            result.created += import_result["created"]
            result.updated += import_result["updated"]
            result.archived += import_result["archived"]
            result.warnings.extend(import_result["warnings"])
            result.errors.extend(import_result["errors"])
            
            result.details[collection_name] = {
                "created": import_result["created"],
                "updated": import_result["updated"],
                "archived": import_result["archived"],
                "total": len(docs)
            }
        
        zf.close()
        
        # Set status
        if result.errors:
            result.status = "error"
        elif dry_run:
            result.status = "dry_run"
        else:
            result.status = "success"
        
        # Calculate and store fingerprint after successful import
        imported_fingerprint = None
        if not dry_run and result.status == "success":
            fp_data = await get_current_seeds_fingerprint()
            imported_fingerprint = fp_data["fingerprint"]
            
            # Store seed version info
            await db.seed_version.update_one(
                {"type": "current"},
                {"$set": {
                    "type": "current",
                    "fingerprint": imported_fingerprint,
                    "imported_at": datetime.now(timezone.utc).isoformat(),
                    "imported_by": user.get("email", user.get("sub", "unknown")),
                    "source": "import"
                }},
                upsert=True
            )
        
        # Audit log
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "type": "seeds_backup",
            "action": "import",
            "user": user.get("email", user.get("sub", "unknown")),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "options": options.model_dump(),
            "result": {
                "status": result.status,
                "fingerprint": imported_fingerprint,
                "created": result.created,
                "updated": result.updated,
                "archived": result.archived,
                "errors": len(result.errors)
            }
        })
        
        logger.info(f"Seeds import by {user.get('email')}: {result.status}, fingerprint={imported_fingerprint}, created={result.created}, updated={result.updated}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@seeds_router.get("/verify")
async def verify_seeds_endpoint(user: dict = Depends(require_admin)):
    """
    Verify seed data integrity.
    
    Checks:
    - Exactly 1 active opening_hours_master
    - At least 1 active shift_template
    - Enum consistency
    - Reference integrity
    """
    result = await verify_seeds()
    return result


@seeds_router.get("/status")
async def get_seeds_status(user: dict = Depends(require_admin)):
    """
    Get current seeds status overview including fingerprint.
    """
    counts = {}
    
    for name, config in SEED_COLLECTIONS.items():
        collection = db[config["collection"]]
        filter_query = config.get("filter", {})
        count = await collection.count_documents(filter_query)
        counts[name] = count
    
    # Get current fingerprint
    fingerprint_data = await get_current_seeds_fingerprint()
    
    # Get stored seed version (from last import)
    seed_version = await db.seed_version.find_one(
        {"type": "current"},
        {"_id": 0}
    )
    
    # Get last backup info
    last_backup = await db.audit_logs.find_one(
        {"type": "seeds_backup", "action": "export"},
        {"_id": 0, "timestamp": 1, "result": 1, "user": 1},
        sort=[("timestamp", -1)]
    )
    
    # Get last import info
    last_import = await db.audit_logs.find_one(
        {"type": "seeds_backup", "action": "import", "result.status": "success"},
        {"_id": 0, "timestamp": 1, "result": 1, "user": 1, "options": 1},
        sort=[("timestamp", -1)]
    )
    
    # Run verification
    verify_result = await verify_seeds()
    
    return {
        "counts": counts,
        "total_documents": sum(counts.values()),
        "fingerprint": {
            "current": fingerprint_data["fingerprint"],
            "calculated_at": fingerprint_data["calculated_at"],
            "stored": seed_version.get("fingerprint") if seed_version else None,
            "imported_at": seed_version.get("imported_at") if seed_version else None,
            "imported_by": seed_version.get("imported_by") if seed_version else None,
            "matches": fingerprint_data["fingerprint"] == seed_version.get("fingerprint") if seed_version else None
        },
        "last_backup": last_backup,
        "last_import": last_import,
        "verification": {
            "status": verify_result.status,
            "warnings": verify_result.warnings,
            "errors": verify_result.errors
        }
    }


@seeds_router.get("/fingerprint")
async def get_fingerprint(user: dict = Depends(require_admin)):
    """
    Get current seed data fingerprint.
    
    Returns:
    - Current calculated fingerprint
    - Stored fingerprint from last import
    - Whether they match
    """
    # Get current fingerprint
    fingerprint_data = await get_current_seeds_fingerprint()
    
    # Get stored seed version
    seed_version = await db.seed_version.find_one(
        {"type": "current"},
        {"_id": 0}
    )
    
    return {
        "current_fingerprint": fingerprint_data["fingerprint"],
        "calculated_at": fingerprint_data["calculated_at"],
        "collections": fingerprint_data["collections"],
        "stored_version": {
            "fingerprint": seed_version.get("fingerprint") if seed_version else None,
            "imported_at": seed_version.get("imported_at") if seed_version else None,
            "imported_by": seed_version.get("imported_by") if seed_version else None,
        } if seed_version else None,
        "matches": fingerprint_data["fingerprint"] == seed_version.get("fingerprint") if seed_version else None,
        "drift_detected": seed_version and fingerprint_data["fingerprint"] != seed_version.get("fingerprint")
    }
