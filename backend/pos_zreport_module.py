"""
Gastronovi Z-Bericht PDF Import Module
- Email-Ingestion (IMAP)
- PDF Parsing & Extraction
- KPI Normalization
- Dashboard API
"""

import os
import re
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from pydantic import BaseModel
import pdfplumber

# Logging
logger = logging.getLogger("pos_zreport")

# Router
pos_router = APIRouter(prefix="/api/admin/pos", tags=["POS Z-Reports"])

# MongoDB wird aus server.py importiert
db = None

def set_db(database):
    """Set database reference from server.py"""
    global db
    db = database

# ============== CONSTANTS ==============

PARSER_VERSION = "1.0.0"
UPLOAD_DIR = "/app/uploads/z_reports"

# ============== MODELS ==============

class ImportStatus(str, Enum):
    PENDING = "pending"
    IMPORTED = "imported"
    EXTRACTED = "extracted"
    NORMALIZED = "normalized"
    FAILED = "failed"
    NEEDS_OCR = "needs_ocr"
    DUPLICATE = "duplicate"

class ZReportRaw(BaseModel):
    report_key: str
    date_business: str
    received_at: str
    source_email: Optional[str] = None
    message_id: Optional[str] = None
    pdf_hash: str
    pdf_path: str
    status: str = ImportStatus.PENDING.value
    z_number: Optional[str] = None

class ZReportExtracted(BaseModel):
    report_key: str
    extracted_at: str
    parser_version: str
    sections: Dict[str, Any]

class DailyKPIs(BaseModel):
    date_business: str
    net_total: float
    gross_total: float
    net_food: float = 0
    net_beverage: float = 0
    net_nonfood: float = 0
    beverage_share: float = 0
    tax_7: float = 0
    tax_19: float = 0
    tax_0: float = 0
    top_hour: Optional[str] = None
    top_hour_amount: float = 0
    discount_amount: float = 0
    storno_amount: float = 0
    tips_amount: float = 0

# ============== PDF PARSING ==============

def calculate_pdf_hash(content: bytes) -> str:
    """Calculate SHA256 hash of PDF content"""
    return hashlib.sha256(content).hexdigest()

def parse_currency(value: str) -> float:
    """Parse German currency format: € 1.234,56 -> 1234.56"""
    if not value:
        return 0.0
    try:
        # Remove € symbol and whitespace
        cleaned = re.sub(r'[€\s]', '', str(value))
        # Handle negative with minus or parentheses
        is_negative = '-' in cleaned or cleaned.startswith('(')
        cleaned = re.sub(r'[()-]', '', cleaned)
        # German format: 1.234,56 -> 1234.56
        cleaned = cleaned.replace('.', '').replace(',', '.')
        result = float(cleaned) if cleaned else 0.0
        return -result if is_negative else result
    except (ValueError, TypeError):
        return 0.0

def extract_date_from_text(text: str) -> Optional[str]:
    """Extract business date from Z-Report text"""
    # Pattern: "Von 01.02.2020 11:40" or "Von: 01.02.2020"
    patterns = [
        r'Von[:\s]+(\d{2}\.\d{2}\.\d{4})',
        r'Datum[:\s]+(\d{2}\.\d{2}\.\d{4})',
        r'(\d{2}\.\d{2}\.\d{4})\s+\d{2}:\d{2}',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            try:
                dt = datetime.strptime(date_str, "%d.%m.%Y")
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None

def extract_z_number(text: str) -> Optional[str]:
    """Extract Z-Zähler number"""
    match = re.search(r'Z-Zähler[:\s]+(\d+)', text)
    if match:
        return match.group(1)
    return None

def parse_tax_section(text: str) -> Dict[str, float]:
    """Parse Steuerbericht section"""
    taxes = {"tax_7": 0, "tax_19": 0, "tax_0": 0, "net_total": 0, "gross_total": 0}
    
    # Pattern for tax lines: "7 €X.XXX,XX €XXX,XX €X.XXX,XX"
    # or "19 €X.XXX,XX €X.XXX,XX €X.XXX,XX"
    tax_pattern = r'(\d+)\s+[€]?\s*([\d.,]+)\s+[€]?\s*([\d.,]+)\s+[€]?\s*([\d.,]+)'
    
    for match in re.finditer(tax_pattern, text):
        rate = int(match.group(1))
        netto = parse_currency(match.group(2))
        steuer = parse_currency(match.group(3))
        brutto = parse_currency(match.group(4))
        
        if rate == 7:
            taxes["tax_7"] = steuer
            taxes["net_total"] += netto
            taxes["gross_total"] += brutto
        elif rate == 19:
            taxes["tax_19"] = steuer
            taxes["net_total"] += netto
            taxes["gross_total"] += brutto
        elif rate == 0:
            taxes["tax_0"] = steuer
            taxes["net_total"] += netto
            taxes["gross_total"] += brutto
    
    return taxes

def parse_product_groups(text: str) -> Dict[str, float]:
    """Parse Hauptwarengruppen for Food/Beverage split"""
    groups = {"food": 0, "beverage": 0, "nonfood": 0}
    
    # Pattern: "Beverage (Getränke) 3142 (€ 10189.80) € 10103.02"
    # or "Food (Speisen) 1234 (€ 5000.00) € 5500.00"
    
    lines = text.split('\n')
    for line in lines:
        line_lower = line.lower()
        
        # Extract gross amount (last currency value in line)
        amounts = re.findall(r'[€]\s*([\d.,]+)', line)
        if not amounts:
            continue
        
        gross = parse_currency(amounts[-1])
        
        if 'beverage' in line_lower or 'getränke' in line_lower:
            groups["beverage"] += gross
        elif 'food' in line_lower or 'speisen' in line_lower:
            groups["food"] += gross
        elif 'non-food' in line_lower or 'nichtlebensmittel' in line_lower:
            groups["nonfood"] += gross
    
    return groups

def parse_hourly_sales(text: str) -> Dict[str, Any]:
    """Parse Zeitabschnitte for Top Hour"""
    hourly = []
    top_hour = None
    top_amount = 0
    
    # Pattern: "12:00 - 13:00 € 10582.85 28.52%"
    pattern = r'(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})\s+[€]?\s*([\d.,]+)'
    
    for match in re.finditer(pattern, text):
        start = match.group(1)
        end = match.group(2)
        amount = parse_currency(match.group(3))
        
        hourly.append({"hour": f"{start}-{end}", "amount": amount})
        
        if amount > top_amount:
            top_amount = amount
            top_hour = f"{start}-{end}"
    
    return {"hourly": hourly, "top_hour": top_hour, "top_hour_amount": top_amount}

def parse_waiters(text: str) -> List[Dict[str, Any]]:
    """Parse Kellner section"""
    waiters = []
    
    # Section starts after "Kellner" heading
    kellner_section = re.search(r'Kellner\s*\n(.*?)(?=\n[A-Z][a-z]+\s*\n|\nBezahlarten)', text, re.DOTALL)
    if not kellner_section:
        return waiters
    
    section_text = kellner_section.group(1)
    
    # Pattern: "Name Count € Amount"
    # Example: "Cathleen Albrecht 163 € 12125.36"
    pattern = r'([A-Za-zäöüÄÖÜß\s]+?)\s+(\d+)\s+[€]?\s*([\d.,]+)'
    
    for match in re.finditer(pattern, section_text):
        name = match.group(1).strip()
        count = int(match.group(2))
        amount = parse_currency(match.group(3))
        
        if name and amount > 0:
            waiters.append({
                "name": name,
                "transactions": count,
                "gross_amount": amount
            })
    
    return waiters

def parse_discounts_stornos(text: str) -> Dict[str, float]:
    """Parse Rabatte and Stornierte Artikel"""
    result = {"discount_amount": 0, "storno_amount": 0}
    
    # Rabatte section
    rabatt_match = re.search(r'Rabatte.*?Total.*?[€]\s*([-\d.,]+)', text, re.DOTALL)
    if rabatt_match:
        result["discount_amount"] = abs(parse_currency(rabatt_match.group(1)))
    
    # Positionsrabatte
    pos_rabatt_match = re.search(r'Positionsrabatte.*?Total.*?[€]\s*([-\d.,]+)', text, re.DOTALL)
    if pos_rabatt_match:
        result["discount_amount"] += abs(parse_currency(pos_rabatt_match.group(1)))
    
    # Stornierte Artikel
    storno_match = re.search(r'Stornierte Artikel.*?Total.*?[€]\s*([\d.,]+)', text, re.DOTALL)
    if storno_match:
        result["storno_amount"] = parse_currency(storno_match.group(1))
    
    return result

def parse_tips(text: str) -> float:
    """Parse Trinkgeld"""
    match = re.search(r'Trinkgeld.*?[€]\s*([\d.,]+)', text, re.DOTALL)
    if match:
        return parse_currency(match.group(1))
    return 0

def parse_top_items(text: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Parse Positionen for top/flop items"""
    items = []
    
    # Find Positionen section
    pos_section = re.search(r'Positionen\s*\n(.*)', text, re.DOTALL)
    if not pos_section:
        return items
    
    section_text = pos_section.group(1)
    
    # Pattern: "Item Name Qty € Amount"
    pattern = r'([A-Za-zäöüÄÖÜß\s\d.,*-]+?)\s+(\d+)\s+[€]?\s*([\d.,]+)'
    
    for match in re.finditer(pattern, section_text):
        name = match.group(1).strip()
        qty = int(match.group(2))
        amount = parse_currency(match.group(3))
        
        # Skip invalid entries
        if len(name) < 3 or amount == 0:
            continue
        
        items.append({
            "name": name[:50],  # Limit name length
            "quantity": qty,
            "gross_amount": amount
        })
    
    # Sort by amount descending
    items.sort(key=lambda x: x["gross_amount"], reverse=True)
    
    return items[:limit]

def extract_pdf_text(pdf_path: str) -> tuple[str, bool]:
    """Extract text from PDF using pdfplumber"""
    try:
        full_text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        
        # Check if we got meaningful text
        has_text = len(full_text.strip()) > 100
        return full_text, has_text
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return "", False

def parse_zreport_pdf(pdf_path: str) -> Dict[str, Any]:
    """Full parsing pipeline for Z-Report PDF"""
    result = {
        "success": False,
        "error": None,
        "date_business": None,
        "z_number": None,
        "sections": {},
        "kpis": {}
    }
    
    # Extract text
    text, has_text = extract_pdf_text(pdf_path)
    
    if not has_text:
        result["error"] = "needs_ocr"
        return result
    
    # Extract metadata
    result["date_business"] = extract_date_from_text(text)
    result["z_number"] = extract_z_number(text)
    
    if not result["date_business"]:
        result["error"] = "date_not_found"
        return result
    
    # Parse sections
    try:
        taxes = parse_tax_section(text)
        groups = parse_product_groups(text)
        hourly = parse_hourly_sales(text)
        waiters = parse_waiters(text)
        discounts = parse_discounts_stornos(text)
        tips = parse_tips(text)
        top_items = parse_top_items(text, 20)
        
        result["sections"] = {
            "taxes": taxes,
            "groups": groups,
            "hourly": hourly,
            "waiters": waiters,
            "discounts": discounts,
            "tips": tips,
            "items": top_items
        }
        
        # Calculate KPIs
        gross_total = taxes.get("gross_total", 0)
        if gross_total == 0:
            # Fallback: sum from groups
            gross_total = groups["food"] + groups["beverage"] + groups["nonfood"]
        
        net_total = taxes.get("net_total", 0)
        
        beverage_share = 0
        if gross_total > 0:
            beverage_share = round((groups["beverage"] / gross_total) * 100, 1)
        
        result["kpis"] = {
            "net_total": net_total,
            "gross_total": gross_total,
            "net_food": groups["food"],
            "net_beverage": groups["beverage"],
            "net_nonfood": groups["nonfood"],
            "beverage_share": beverage_share,
            "tax_7": taxes.get("tax_7", 0),
            "tax_19": taxes.get("tax_19", 0),
            "tax_0": taxes.get("tax_0", 0),
            "top_hour": hourly.get("top_hour"),
            "top_hour_amount": hourly.get("top_hour_amount", 0),
            "discount_amount": discounts.get("discount_amount", 0),
            "storno_amount": discounts.get("storno_amount", 0),
            "tips_amount": tips
        }
        
        result["success"] = True
        
    except Exception as e:
        logger.error(f"Parsing error: {e}")
        result["error"] = f"parse_error: {str(e)}"
    
    return result

# ============== IMPORT LOGIC ==============

async def import_pdf_file(
    pdf_content: bytes,
    filename: str,
    source_email: Optional[str] = None,
    message_id: Optional[str] = None
) -> Dict[str, Any]:
    """Import a single PDF file"""
    
    # Calculate hash for idempotency
    pdf_hash = calculate_pdf_hash(pdf_content)
    
    # Check for duplicate
    existing = await db.pos_z_reports_raw.find_one({"pdf_hash": pdf_hash})
    if existing:
        return {
            "status": "duplicate",
            "report_key": existing.get("report_key"),
            "message": "PDF already imported"
        }
    
    # Save PDF temporarily for parsing
    temp_path = f"/tmp/zreport_{uuid.uuid4().hex}.pdf"
    with open(temp_path, 'wb') as f:
        f.write(pdf_content)
    
    # Parse PDF
    parse_result = parse_zreport_pdf(temp_path)
    
    if not parse_result["success"]:
        os.remove(temp_path)
        return {
            "status": "failed",
            "error": parse_result.get("error", "unknown")
        }
    
    date_business = parse_result["date_business"]
    z_number = parse_result.get("z_number", "")
    
    # Generate report key
    report_key = f"{date_business}_{z_number}_{pdf_hash[:8]}"
    
    # Move PDF to archive
    dt = datetime.strptime(date_business, "%Y-%m-%d")
    archive_dir = f"{UPLOAD_DIR}/{dt.year}/{dt.month:02d}"
    os.makedirs(archive_dir, exist_ok=True)
    archive_path = f"{archive_dir}/{report_key}.pdf"
    
    os.rename(temp_path, archive_path)
    
    # Save raw entry
    raw_doc = {
        "id": str(uuid.uuid4()),
        "report_key": report_key,
        "date_business": date_business,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "source_email": source_email,
        "message_id": message_id,
        "pdf_hash": pdf_hash,
        "pdf_path": archive_path,
        "status": ImportStatus.IMPORTED.value,
        "z_number": z_number,
        "original_filename": filename
    }
    await db.pos_z_reports_raw.insert_one(raw_doc)
    
    # Save extracted data
    extracted_doc = {
        "id": str(uuid.uuid4()),
        "report_key": report_key,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "parser_version": PARSER_VERSION,
        "sections": parse_result["sections"]
    }
    await db.pos_z_reports_extracted.insert_one(extracted_doc)
    
    # Update raw status
    await db.pos_z_reports_raw.update_one(
        {"report_key": report_key},
        {"$set": {"status": ImportStatus.EXTRACTED.value}}
    )
    
    # Save/Update KPIs
    kpis = parse_result["kpis"]
    kpis["date_business"] = date_business
    kpis["report_key"] = report_key
    kpis["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.pos_daily_kpis.update_one(
        {"date_business": date_business},
        {"$set": kpis},
        upsert=True
    )
    
    # Update raw status to normalized
    await db.pos_z_reports_raw.update_one(
        {"report_key": report_key},
        {"$set": {"status": ImportStatus.NORMALIZED.value}}
    )
    
    # Save waiter data
    if parse_result["sections"].get("waiters"):
        for waiter in parse_result["sections"]["waiters"]:
            await db.pos_waiter_daily.update_one(
                {"date_business": date_business, "waiter_name": waiter["name"]},
                {"$set": {
                    "date_business": date_business,
                    "waiter_name": waiter["name"],
                    "transactions": waiter["transactions"],
                    "gross_amount": waiter["gross_amount"],
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }},
                upsert=True
            )
    
    # Save item data
    if parse_result["sections"].get("items"):
        for item in parse_result["sections"]["items"]:
            await db.pos_item_daily.update_one(
                {"date_business": date_business, "item_name": item["name"]},
                {"$set": {
                    "date_business": date_business,
                    "item_name": item["name"],
                    "quantity": item["quantity"],
                    "gross_amount": item["gross_amount"],
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }},
                upsert=True
            )
    
    return {
        "status": "success",
        "report_key": report_key,
        "date_business": date_business,
        "kpis": kpis
    }

# ============== API ENDPOINTS ==============

@pos_router.post("/upload")
async def upload_zreport(
    file: UploadFile = File(...)
):
    """
    Upload a Z-Report PDF manually.
    Idempotent: duplicate PDFs are rejected.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    
    content = await file.read()
    
    if len(content) < 1000:
        raise HTTPException(status_code=400, detail="File too small to be a valid PDF")
    
    result = await import_pdf_file(content, file.filename)
    
    if result["status"] == "duplicate":
        return {
            "success": False,
            "status": "duplicate",
            "message": result["message"],
            "report_key": result.get("report_key")
        }
    elif result["status"] == "failed":
        raise HTTPException(status_code=422, detail=f"Parse failed: {result.get('error')}")
    
    return {
        "success": True,
        "status": "imported",
        "report_key": result["report_key"],
        "date_business": result["date_business"],
        "kpis": result.get("kpis")
    }

@pos_router.get("/import-status")
async def get_import_status(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format")
):
    """Get import status for a specific date or all"""
    query = {}
    if date:
        query["date_business"] = date
    
    raw_reports = await db.pos_z_reports_raw.find(query, {"_id": 0}).to_list(100)
    extracted = await db.pos_z_reports_extracted.find(query, {"_id": 0}).to_list(100)
    kpis = await db.pos_daily_kpis.find(query, {"_id": 0}).to_list(100)
    
    return {
        "raw_count": len(raw_reports),
        "extracted_count": len(extracted),
        "kpis_count": len(kpis),
        "raw_reports": raw_reports,
        "kpis": kpis
    }

@pos_router.get("/kpis")
async def get_kpis(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    limit: int = Query(30, le=365)
):
    """Get daily KPIs for date range"""
    query = {}
    
    if from_date:
        query["date_business"] = {"$gte": from_date}
    if to_date:
        if "date_business" in query:
            query["date_business"]["$lte"] = to_date
        else:
            query["date_business"] = {"$lte": to_date}
    
    kpis = await db.pos_daily_kpis.find(
        query, 
        {"_id": 0}
    ).sort("date_business", -1).to_list(limit)
    
    # Calculate aggregates
    if kpis:
        total_gross = sum(k.get("gross_total", 0) for k in kpis)
        total_net = sum(k.get("net_total", 0) for k in kpis)
        avg_beverage_share = sum(k.get("beverage_share", 0) for k in kpis) / len(kpis)
        
        return {
            "kpis": kpis,
            "summary": {
                "days": len(kpis),
                "total_gross": round(total_gross, 2),
                "total_net": round(total_net, 2),
                "avg_daily_gross": round(total_gross / len(kpis), 2),
                "avg_beverage_share": round(avg_beverage_share, 1)
            }
        }
    
    return {"kpis": [], "summary": None}

@pos_router.get("/kpis/latest")
async def get_latest_kpis():
    """Get the most recent KPIs for dashboard"""
    latest = await db.pos_daily_kpis.find_one(
        {},
        {"_id": 0},
        sort=[("date_business", -1)]
    )
    
    if not latest:
        return {"status": "no_data", "kpis": None}
    
    # Get waiters for that day
    waiters = await db.pos_waiter_daily.find(
        {"date_business": latest["date_business"]},
        {"_id": 0}
    ).sort("gross_amount", -1).to_list(10)
    
    # Get top items (Renner)
    top_items = await db.pos_item_daily.find(
        {"date_business": latest["date_business"]},
        {"_id": 0}
    ).sort("gross_amount", -1).to_list(10)
    
    # Get flop items (Penner) - lowest non-zero
    flop_items = await db.pos_item_daily.find(
        {"date_business": latest["date_business"], "gross_amount": {"$gt": 0}},
        {"_id": 0}
    ).sort("gross_amount", 1).to_list(10)
    
    return {
        "status": "ok",
        "kpis": latest,
        "top_waiters": waiters,
        "top_items": top_items,
        "flop_items": flop_items
    }

@pos_router.get("/raw/{report_key}")
async def get_raw_report(report_key: str):
    """Get raw report metadata"""
    raw = await db.pos_z_reports_raw.find_one(
        {"report_key": report_key},
        {"_id": 0}
    )
    
    if not raw:
        raise HTTPException(status_code=404, detail="Report not found")
    
    extracted = await db.pos_z_reports_extracted.find_one(
        {"report_key": report_key},
        {"_id": 0}
    )
    
    return {
        "raw": raw,
        "extracted": extracted
    }

@pos_router.post("/reparse/{report_key}")
async def reparse_report(report_key: str):
    """Re-parse an existing raw PDF (admin only)"""
    raw = await db.pos_z_reports_raw.find_one({"report_key": report_key})
    
    if not raw:
        raise HTTPException(status_code=404, detail="Report not found")
    
    pdf_path = raw.get("pdf_path")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    # Re-parse
    parse_result = parse_zreport_pdf(pdf_path)
    
    if not parse_result["success"]:
        raise HTTPException(status_code=422, detail=f"Parse failed: {parse_result.get('error')}")
    
    # Update extracted
    await db.pos_z_reports_extracted.update_one(
        {"report_key": report_key},
        {"$set": {
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "parser_version": PARSER_VERSION,
            "sections": parse_result["sections"]
        }},
        upsert=True
    )
    
    # Update KPIs
    kpis = parse_result["kpis"]
    kpis["date_business"] = raw["date_business"]
    kpis["report_key"] = report_key
    kpis["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.pos_daily_kpis.update_one(
        {"date_business": raw["date_business"]},
        {"$set": kpis},
        upsert=True
    )
    
    return {
        "success": True,
        "message": "Report re-parsed successfully",
        "kpis": kpis
    }

@pos_router.get("/stats")
async def get_import_stats():
    """Get overall import statistics"""
    raw_count = await db.pos_z_reports_raw.count_documents({})
    extracted_count = await db.pos_z_reports_extracted.count_documents({})
    kpis_count = await db.pos_daily_kpis.count_documents({})
    
    # Status breakdown
    status_counts = {}
    for status in ImportStatus:
        count = await db.pos_z_reports_raw.count_documents({"status": status.value})
        status_counts[status.value] = count
    
    return {
        "raw_reports": raw_count,
        "extracted_reports": extracted_count,
        "daily_kpis": kpis_count,
        "status_breakdown": status_counts
    }
