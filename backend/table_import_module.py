"""
GastroCore Table Import & Seed Module
=====================================
Persistente Tisch-Stammdaten + Kombinationen

ENDPOINTS:
- GET  /api/data-status              - System-Status mit Counts
- POST /api/admin/import/tables      - Excel Upload für Tische
- POST /api/admin/import/table-combinations - Excel Upload für Kombinationen
- POST /api/admin/seed/from-repo     - Seed aus /seed/ Ordner

ADDITIV - Keine Breaking Changes
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pathlib import Path
import uuid
import os
import io
import logging

# Core imports
from core.database import db
from core.auth import require_admin
from core.audit import create_audit_log

logger = logging.getLogger(__name__)

# Router
import_router = APIRouter(tags=["Import & Seed"])

# Paths
SEED_FOLDER = Path("/app/seed")
SEED_FOLDER.mkdir(parents=True, exist_ok=True)


# ============== MODELS ==============
class DataStatusResponse(BaseModel):
    build_id: str
    version: str
    database_type: str  # "external" or "local"
    database_warning: Optional[str]
    counts: Dict[str, int]
    last_import: Optional[Dict[str, Any]]


class ImportResult(BaseModel):
    success: bool
    created: int
    updated: int
    errors: int
    message: str


# ============== HELPERS ==============
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_mongo_type() -> tuple:
    """Check if using external or local MongoDB"""
    mongo_url = os.environ.get('MONGO_URL', '')
    if 'localhost' in mongo_url or '127.0.0.1' in mongo_url or not mongo_url:
        return "local", "⚠️ Lokale MongoDB - Daten gehen bei Container-Neustart verloren!"
    return "external", None


async def log_import(user_email: str, filename: str, collection: str, created: int, updated: int, errors: int):
    """Log import operation"""
    await db.import_logs.insert_one({
        "id": str(uuid.uuid4()),
        "timestamp": now_iso(),
        "user": user_email,
        "filename": filename,
        "collection": collection,
        "created": created,
        "updated": updated,
        "errors": errors
    })


# ============== ENDPOINTS ==============

@import_router.get("/api/data-status", response_model=DataStatusResponse)
async def get_data_status():
    """
    GET /api/data-status
    System health with collection counts
    """
    db_type, warning = get_mongo_type()
    
    # Get counts
    counts = {
        "tables": await db.tables.count_documents({"archived": {"$ne": True}}),
        "table_combinations": await db.table_combinations.count_documents({"archived": {"$ne": True}}),
        "reservations": await db.reservations.count_documents({"archived": {"$ne": True}}),
        "staff_members": await db.staff_members.count_documents({"archived": {"$ne": True}}),
        "events": await db.events.count_documents({"archived": {"$ne": True}}),
        "actions": await db.actions.count_documents({"archived": {"$ne": True}}),
        "users": await db.users.count_documents({"archived": {"$ne": True}}),
    }
    
    # Get last import
    last_import = await db.import_logs.find_one(sort=[("timestamp", -1)])
    last_import_data = None
    if last_import:
        last_import_data = {
            "timestamp": last_import.get("timestamp"),
            "collection": last_import.get("collection"),
            "user": last_import.get("user"),
            "created": last_import.get("created"),
            "updated": last_import.get("updated")
        }
    
    # Get build info
    import subprocess
    try:
        commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd='/app').decode().strip()
    except:
        commit = "unknown"
    
    return {
        "build_id": f"{commit}-{datetime.now().strftime('%Y%m%d')}",
        "version": "3.0.0",
        "database_type": db_type,
        "database_warning": warning,
        "counts": counts,
        "last_import": last_import_data
    }


@import_router.post("/api/admin/import/tables", response_model=ImportResult)
async def import_tables(file: UploadFile = File(...), user: dict = Depends(require_admin)):
    """
    POST /api/admin/import/tables
    Import tables from Excel file (Sheet: tables)
    Upsert by (table_number, area, subarea)
    """
    try:
        import openpyxl
    except ImportError:
        raise HTTPException(500, "openpyxl not installed")
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "Nur Excel-Dateien (.xlsx) erlaubt")
    
    content = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(content))
    
    # Find tables sheet
    sheet_name = 'tables' if 'tables' in wb.sheetnames else wb.sheetnames[0]
    ws = wb[sheet_name]
    
    # Get headers
    headers = [str(c.value).lower() if c.value else f"col{i}" for i, c in enumerate(ws[1])]
    
    created = 0
    updated = 0
    errors = 0
    
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        
        try:
            # Map columns
            data = dict(zip(headers, row))
            
            table_number = str(data.get('table_number', '')).strip()
            area = str(data.get('area', 'restaurant')).strip()
            subarea = data.get('subarea') or data.get('sub_area')
            if subarea:
                subarea = str(subarea).strip()
                if subarea == 'terrasse':
                    subarea = None
            
            seats = int(data.get('seats', 4))
            max_seats = int(data.get('max_seats', seats))
            combinable = str(data.get('combinable', 'true')).lower() == 'true'
            notes = data.get('notes')
            
            # Find existing
            existing = await db.tables.find_one({
                "table_number": table_number,
                "area": area
            })
            
            now = now_iso()
            
            if existing:
                await db.tables.update_one(
                    {"id": existing['id']},
                    {"$set": {
                        "sub_area": subarea,
                        "seats_default": seats,
                        "seats_max": max_seats,
                        "combinable": combinable,
                        "notes": notes,
                        "updated_at": now
                    }}
                )
                updated += 1
            else:
                await db.tables.insert_one({
                    "id": str(uuid.uuid4()),
                    "table_number": table_number,
                    "area": area,
                    "sub_area": subarea,
                    "seats_default": seats,
                    "seats_max": max_seats,
                    "combinable": combinable,
                    "combinable_with": [],
                    "notes": notes,
                    "active": True,
                    "fixed": False,
                    "position_x": None,
                    "position_y": None,
                    "created_at": now,
                    "updated_at": now,
                    "archived": False
                })
                created += 1
        except Exception as e:
            logger.error(f"Error importing table row: {e}")
            errors += 1
    
    # Log import
    await log_import(user.get('email', 'unknown'), file.filename, 'tables', created, updated, errors)
    
    # Audit
    await create_audit_log(
        actor={"id": user['id'], "email": user['email']},
        entity="tables",
        entity_id="bulk_import",
        action="import",
        after={"filename": file.filename, "created": created, "updated": updated}
    )
    
    return {
        "success": errors == 0,
        "created": created,
        "updated": updated,
        "errors": errors,
        "message": f"Import abgeschlossen: {created} neu, {updated} aktualisiert, {errors} Fehler"
    }


@import_router.post("/api/admin/import/table-combinations", response_model=ImportResult)
async def import_table_combinations(file: UploadFile = File(...), user: dict = Depends(require_admin)):
    """
    POST /api/admin/import/table-combinations
    Import table combinations from Excel file
    Upsert by combo_id
    """
    try:
        import openpyxl
    except ImportError:
        raise HTTPException(500, "openpyxl not installed")
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "Nur Excel-Dateien (.xlsx) erlaubt")
    
    content = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(content))
    
    # Find combinations sheet
    sheet_name = 'combinations' if 'combinations' in wb.sheetnames else wb.sheetnames[0]
    ws = wb[sheet_name]
    
    # Get headers
    headers = [str(c.value).lower() if c.value else f"col{i}" for i, c in enumerate(ws[1])]
    
    created = 0
    updated = 0
    errors = 0
    
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        
        try:
            data = dict(zip(headers, row))
            
            combo_id = str(data.get('combo_id', '')).strip()
            subarea = str(data.get('subarea', '')).strip()
            tables_str = str(data.get('tables', '')).strip()
            target_capacity = int(data.get('target_capacity', 0)) if data.get('target_capacity') else 0
            notes = data.get('notes')
            
            # Parse tables list
            tables_list = [t.strip() for t in tables_str.split('+') if t.strip()]
            
            # Determine area from subarea
            if subarea in ['saal', 'wintergarten']:
                area = 'restaurant'
            else:
                area = subarea  # terrasse
            
            # Find existing
            existing = await db.table_combinations.find_one({"combo_id": combo_id})
            
            now = now_iso()
            
            combo_data = {
                "combo_id": combo_id,
                "area": area,
                "subarea": subarea,
                "tables": tables_list,
                "target_capacity": target_capacity,
                "notes": notes,
                "updated_at": now
            }
            
            if existing:
                await db.table_combinations.update_one(
                    {"id": existing['id']},
                    {"$set": combo_data}
                )
                updated += 1
            else:
                combo_data["id"] = str(uuid.uuid4())
                combo_data["created_at"] = now
                combo_data["archived"] = False
                combo_data["active"] = True
                await db.table_combinations.insert_one(combo_data)
                created += 1
        except Exception as e:
            logger.error(f"Error importing combination row: {e}")
            errors += 1
    
    # Log import
    await log_import(user.get('email', 'unknown'), file.filename, 'table_combinations', created, updated, errors)
    
    # Audit
    await create_audit_log(
        actor={"id": user['id'], "email": user['email']},
        entity="table_combinations",
        entity_id="bulk_import",
        action="import",
        after={"filename": file.filename, "created": created, "updated": updated}
    )
    
    return {
        "success": errors == 0,
        "created": created,
        "updated": updated,
        "errors": errors,
        "message": f"Import abgeschlossen: {created} neu, {updated} aktualisiert, {errors} Fehler"
    }


@import_router.post("/api/admin/seed/from-repo", response_model=ImportResult)
async def seed_from_repo(user: dict = Depends(require_admin)):
    """
    POST /api/admin/seed/from-repo
    Load tables and combinations from /seed/ folder
    """
    try:
        import openpyxl
    except ImportError:
        raise HTTPException(500, "openpyxl not installed")
    
    tables_file = SEED_FOLDER / "tables.xlsx"
    combos_file = SEED_FOLDER / "table_combinations.xlsx"
    
    if not tables_file.exists() and not combos_file.exists():
        raise HTTPException(404, "Keine Seed-Dateien gefunden in /seed/")
    
    total_created = 0
    total_updated = 0
    total_errors = 0
    
    # Import tables
    if tables_file.exists():
        wb = openpyxl.load_workbook(tables_file)
        sheet_name = 'tables' if 'tables' in wb.sheetnames else wb.sheetnames[0]
        ws = wb[sheet_name]
        headers = [str(c.value).lower() if c.value else f"col{i}" for i, c in enumerate(ws[1])]
        
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[0]:
                continue
            try:
                data = dict(zip(headers, row))
                table_number = str(data.get('table_number', '')).strip()
                area = str(data.get('area', 'restaurant')).strip()
                subarea = data.get('subarea') or data.get('sub_area')
                if subarea:
                    subarea = str(subarea).strip()
                    if subarea == 'terrasse':
                        subarea = None
                
                existing = await db.tables.find_one({"table_number": table_number, "area": area})
                now = now_iso()
                
                if existing:
                    await db.tables.update_one(
                        {"id": existing['id']},
                        {"$set": {
                            "sub_area": subarea,
                            "seats_default": int(data.get('seats', 4)),
                            "seats_max": int(data.get('max_seats', data.get('seats', 4))),
                            "combinable": str(data.get('combinable', 'true')).lower() == 'true',
                            "notes": data.get('notes'),
                            "updated_at": now
                        }}
                    )
                    total_updated += 1
                else:
                    await db.tables.insert_one({
                        "id": str(uuid.uuid4()),
                        "table_number": table_number,
                        "area": area,
                        "sub_area": subarea,
                        "seats_default": int(data.get('seats', 4)),
                        "seats_max": int(data.get('max_seats', data.get('seats', 4))),
                        "combinable": str(data.get('combinable', 'true')).lower() == 'true',
                        "combinable_with": [],
                        "notes": data.get('notes'),
                        "active": True,
                        "fixed": False,
                        "created_at": now,
                        "updated_at": now,
                        "archived": False
                    })
                    total_created += 1
            except Exception as e:
                total_errors += 1
    
    # Import combinations
    if combos_file.exists():
        wb = openpyxl.load_workbook(combos_file)
        sheet_name = 'combinations' if 'combinations' in wb.sheetnames else wb.sheetnames[0]
        ws = wb[sheet_name]
        headers = [str(c.value).lower() if c.value else f"col{i}" for i, c in enumerate(ws[1])]
        
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[0]:
                continue
            try:
                data = dict(zip(headers, row))
                combo_id = str(data.get('combo_id', '')).strip()
                subarea = str(data.get('subarea', '')).strip()
                tables_str = str(data.get('tables', '')).strip()
                tables_list = [t.strip() for t in tables_str.split('+') if t.strip()]
                
                area = 'restaurant' if subarea in ['saal', 'wintergarten'] else subarea
                
                existing = await db.table_combinations.find_one({"combo_id": combo_id})
                now = now_iso()
                
                if existing:
                    await db.table_combinations.update_one(
                        {"id": existing['id']},
                        {"$set": {
                            "area": area,
                            "subarea": subarea,
                            "tables": tables_list,
                            "target_capacity": int(data.get('target_capacity', 0)) if data.get('target_capacity') else 0,
                            "notes": data.get('notes'),
                            "updated_at": now
                        }}
                    )
                    total_updated += 1
                else:
                    await db.table_combinations.insert_one({
                        "id": str(uuid.uuid4()),
                        "combo_id": combo_id,
                        "area": area,
                        "subarea": subarea,
                        "tables": tables_list,
                        "target_capacity": int(data.get('target_capacity', 0)) if data.get('target_capacity') else 0,
                        "notes": data.get('notes'),
                        "active": True,
                        "created_at": now,
                        "updated_at": now,
                        "archived": False
                    })
                    total_created += 1
            except Exception as e:
                total_errors += 1
    
    # Log
    await log_import(user.get('email', 'unknown'), "seed/from-repo", "tables+combinations", total_created, total_updated, total_errors)
    
    return {
        "success": total_errors == 0,
        "created": total_created,
        "updated": total_updated,
        "errors": total_errors,
        "message": f"Seed abgeschlossen: {total_created} neu, {total_updated} aktualisiert"
    }


@import_router.get("/api/admin/import/logs")
async def get_import_logs(limit: int = 20, user: dict = Depends(require_admin)):
    """Get recent import logs"""
    logs = await db.import_logs.find().sort("timestamp", -1).limit(limit).to_list(limit)
    for log in logs:
        log.pop('_id', None)
    return logs
