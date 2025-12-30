"""
POS PDF Mail-Automation V1
- IMAP-Ingestion für gastronovi Z-Berichte
- Scheduler (10-Minuten-Intervall)
- UID-basiertes Lesen (keine Duplikate)
- SHA256 Dupe-Schutz

V1 SCOPE:
- Daily Z-Berichte → pos_daily_metrics
- Monthly Z-Berichte → pos_documents (Crosscheck)
- NUR: net_total, food_net, beverage_net
"""

import os
import re
import ssl
import email
import hashlib
import logging
import asyncio
import imaplib
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import uuid
from email.header import decode_header

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field

# Logging
logger = logging.getLogger("pos_mail")
logging.basicConfig(level=logging.INFO)

# Router - /api/pos/* (admin-only)
pos_mail_router = APIRouter(prefix="/api/pos", tags=["POS Mail Automation"])

# MongoDB wird aus server.py importiert
db = None

def set_db(database):
    """Set database reference from server.py"""
    global db
    db = database


# ============== CONFIGURATION ==============

POS_IMAP_HOST = os.getenv("POS_IMAP_HOST", "imap.ionos.de")
POS_IMAP_PORT = int(os.getenv("POS_IMAP_PORT", "993"))
POS_IMAP_USER = os.getenv("POS_IMAP_USER", "berichte@carlsburg.de")
POS_IMAP_PASSWORD = os.getenv("POS_IMAP_PASSWORD", "")  # PLACEHOLDER - set in .env
POS_IMAP_FOLDER = os.getenv("POS_IMAP_FOLDER", "INBOX")
POS_IMAP_TLS = os.getenv("POS_IMAP_TLS", "true").lower() == "true"

STORAGE_DIR = "/app/storage/pos_pdfs"
PARSER_VERSION = "1.1.0"

# Mail Filter
ALLOWED_SENDERS = ["noreply@gastronovi.de"]
SUBJECT_PREFIXES = ["Tagesbericht", "Monatsbericht"]


# ============== ENUMS & MODELS ==============

class DocType(str, Enum):
    DAILY = "daily"
    MONTHLY = "monthly"

class ParseStatus(str, Enum):
    STORED = "stored"
    PARSED = "parsed"
    FAILED = "failed"

class PosDocument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_type: DocType
    source: str = "email"
    imap_uid: Optional[int] = None
    message_id: Optional[str] = None
    received_at: str
    from_email: Optional[str] = None
    subject: Optional[str] = None
    file_name: str
    file_hash_sha256: str
    file_path: str
    parse_status: ParseStatus = ParseStatus.STORED
    parse_error: Optional[str] = None
    parsed_meta: Optional[Dict[str, Any]] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class PosDailyMetrics(BaseModel):
    date: str  # YYYY-MM-DD (unique)
    net_total: float = 0.0
    food_net: float = 0.0
    beverage_net: float = 0.0
    source_doc_id: Optional[str] = None
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ============== HELPER FUNCTIONS ==============

def calculate_sha256(content: bytes) -> str:
    """Calculate SHA256 hash of content"""
    return hashlib.sha256(content).hexdigest()

def decode_email_header(header_value: str) -> str:
    """Decode email header (handles encoded subjects)"""
    if not header_value:
        return ""
    decoded_parts = decode_header(header_value)
    result = []
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(encoding or 'utf-8', errors='replace'))
        else:
            result.append(part)
    return ''.join(result)

def parse_german_currency(value: str) -> float:
    """Parse German currency format: 1.234,56 or 1234,56 → 1234.56"""
    if not value:
        return 0.0
    try:
        # Remove € symbol and whitespace
        cleaned = re.sub(r'[€\s]', '', str(value))
        # Handle negative with minus or parentheses
        is_negative = '-' in cleaned or cleaned.startswith('(')
        cleaned = re.sub(r'[()-]', '', cleaned)
        # German format: 1.234,56 → 1234.56
        # Also handle: 119.450,74 (thousands separator with dot)
        cleaned = cleaned.replace('.', '').replace(',', '.')
        result = float(cleaned) if cleaned else 0.0
        return -result if is_negative else result
    except (ValueError, TypeError) as e:
        logger.warning(f"Currency parse failed for '{value}': {e}")
        return 0.0

def determine_doc_type(subject: str) -> DocType:
    """Determine if daily or monthly report based on subject"""
    subject_lower = subject.lower()
    if "monatsbericht" in subject_lower:
        return DocType.MONTHLY
    return DocType.DAILY


# ============== PDF PARSER (V1 - gastronovi) ==============

def extract_pdf_text(pdf_path: str) -> Tuple[str, bool]:
    """Extract text from PDF using pdfplumber"""
    try:
        import pdfplumber
        full_text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        
        has_text = len(full_text.strip()) > 100
        return full_text, has_text
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return "", False

def extract_date_range(text: str) -> Dict[str, Any]:
    """
    Extract date range from Z-Report text.
    Patterns:
    - "Von DD.MM.YYYY, HH:MM"
    - "Bis DD.MM.YYYY, HH:MM"
    """
    result = {
        "from_date": None,
        "to_date": None,
        "date": None,  # Business date (Von-Datum)
        "month": None,  # YYYY-MM for monthly reports
        "is_monthly": False
    }
    
    # Pattern: Von DD.MM.YYYY or Von DD.MM.YYYY, HH:MM
    von_pattern = r'Von[:\s]+(\d{2}\.\d{2}\.\d{4})(?:[,\s]+(\d{2}:\d{2}))?'
    bis_pattern = r'Bis[:\s]+(\d{2}\.\d{2}\.\d{4})(?:[,\s]+(\d{2}:\d{2}))?'
    
    von_match = re.search(von_pattern, text)
    bis_match = re.search(bis_pattern, text)
    
    if von_match:
        date_str = von_match.group(1)
        try:
            dt = datetime.strptime(date_str, "%d.%m.%Y")
            result["from_date"] = dt.strftime("%Y-%m-%d")
            result["date"] = result["from_date"]
            result["month"] = dt.strftime("%Y-%m")
        except ValueError:
            pass
    
    if bis_match:
        date_str = bis_match.group(1)
        try:
            dt = datetime.strptime(date_str, "%d.%m.%Y")
            result["to_date"] = dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    
    # Check if monthly (different Von/Bis dates)
    if result["from_date"] and result["to_date"] and result["from_date"] != result["to_date"]:
        result["is_monthly"] = True
    
    return result

def extract_net_total(text: str) -> float:
    """
    Extract Netto Gesamt from Steuerbericht section.
    Pattern: Total € <NETTO> € <STEUER> € <BRUTTO>
    Or: Total <NETTO> <STEUER> <BRUTTO>
    """
    # Find Steuerbericht section
    steuerbericht_match = re.search(r'Steuerbericht.*?(?=\n[A-Z][a-z]+\s*\n|\Z)', text, re.DOTALL | re.IGNORECASE)
    if not steuerbericht_match:
        logger.warning("Steuerbericht section not found")
        return 0.0
    
    section = steuerbericht_match.group(0)
    
    # Pattern: Total with three currency values (NETTO, STEUER, BRUTTO)
    # Examples:
    # "Total € 10.189,80 € 1.089,21 € 11.279,01"
    # "Total 10189.80 1089.21 11279.01"
    total_patterns = [
        r'Total\s+[€]?\s*([\d.,]+)\s+[€]?\s*([\d.,]+)\s+[€]?\s*([\d.,]+)',
        r'Gesamt\s+[€]?\s*([\d.,]+)\s+[€]?\s*([\d.,]+)\s+[€]?\s*([\d.,]+)',
    ]
    
    for pattern in total_patterns:
        match = re.search(pattern, section, re.IGNORECASE)
        if match:
            netto = parse_german_currency(match.group(1))
            if netto > 0:
                return netto
    
    # Fallback: Sum all tax line netto values
    # Pattern: <Rate> €<Netto> €<Steuer> €<Brutto>
    tax_pattern = r'(\d+)\s+[€]?\s*([\d.,]+)\s+[€]?\s*([\d.,]+)\s+[€]?\s*([\d.,]+)'
    total_netto = 0.0
    for match in re.finditer(tax_pattern, section):
        rate = int(match.group(1))
        if rate in [0, 7, 19]:  # Valid German tax rates
            netto = parse_german_currency(match.group(2))
            total_netto += netto
    
    return total_netto

def extract_hauptwarengruppen(text: str) -> Dict[str, float]:
    """
    Extract Food/Beverage NETTO from Hauptwarengruppen section.
    
    WICHTIG: gastronovi Format in Hauptwarengruppen:
    - Format: "Name Anzahl (€ NETTO) € BRUTTO"
    - Beispiel: "Beverage (Getränke) 6645 (€ 28659.80) € 28477.64"
    - Die Zahl in KLAMMERN ist NETTO!
    - Die rechte Zahl ohne Klammern ist BRUTTO!
    """
    result = {"food_net": 0.0, "beverage_net": 0.0}
    
    # Find Hauptwarengruppen section
    hwg_match = re.search(r'Hauptwarengruppen.*?(?=\n[A-Z][a-z]+(?:\s+\n|\s*$)|\nZeitabschnitte|\nKellner|\nTrinkgeld|\Z)', 
                          text, re.DOTALL | re.IGNORECASE)
    if not hwg_match:
        logger.warning("Hauptwarengruppen section not found")
        return result
    
    section = hwg_match.group(0)
    lines = section.split('\n')
    
    for line in lines:
        line_lower = line.lower()
        
        # Pattern: Look for value in parentheses (€ NETTO) - this is the NETTO value!
        # Format: "Beverage (Getränke) 6645 (€ 28659.80) € 28477.64"
        netto_match = re.search(r'\(€?\s*([\d.,]+)\)', line)
        
        netto = 0.0
        if netto_match:
            # Value in parentheses is NETTO
            netto = parse_german_currency(netto_match.group(1))
        else:
            # Fallback: If no parentheses, try to find currency values
            # Take the first one as it's more likely to be the relevant value
            amounts = re.findall(r'€\s*([\d.,]+)', line)
            if amounts:
                netto = parse_german_currency(amounts[0])
        
        if netto > 0:
            if 'beverage' in line_lower or 'getränke' in line_lower:
                result["beverage_net"] = netto
                logger.info(f"Beverage NETTO found: {netto}")
            elif 'food' in line_lower or 'speisen' in line_lower:
                result["food_net"] = netto
                logger.info(f"Food NETTO found: {netto}")
    
    return result

def parse_gastronovi_pdf_v1(pdf_path: str) -> Dict[str, Any]:
    """
    V1 Parser für gastronovi Z-Berichte.
    Extrahiert NUR: net_total, food_net, beverage_net
    """
    result = {
        "success": False,
        "error": None,
        "date": None,
        "month": None,
        "is_monthly": False,
        "net_total": 0.0,
        "food_net": 0.0,
        "beverage_net": 0.0
    }
    
    # Extract text
    text, has_text = extract_pdf_text(pdf_path)
    
    if not has_text:
        result["error"] = "PDF enthält keinen extrahierbaren Text (OCR benötigt)"
        return result
    
    # Extract date range
    date_info = extract_date_range(text)
    result["date"] = date_info.get("date")
    result["month"] = date_info.get("month")
    result["is_monthly"] = date_info.get("is_monthly", False)
    
    if not result["date"]:
        result["error"] = "Datum konnte nicht extrahiert werden"
        return result
    
    # Extract net_total from Steuerbericht
    result["net_total"] = extract_net_total(text)
    
    if result["net_total"] == 0:
        result["error"] = "Netto-Gesamt konnte nicht extrahiert werden"
        return result
    
    # Extract Food/Beverage from Hauptwarengruppen
    hwg = extract_hauptwarengruppen(text)
    result["food_net"] = hwg.get("food_net", 0.0)
    result["beverage_net"] = hwg.get("beverage_net", 0.0)
    
    result["success"] = True
    return result


# ============== IMAP CLIENT ==============

class IMAPClient:
    """IMAP Client für IONOS Mailbox"""
    
    def __init__(self):
        self.connection = None
    
    def connect(self) -> bool:
        """Connect to IMAP server"""
        if not POS_IMAP_PASSWORD:
            logger.error("POS_IMAP_PASSWORD not set in environment")
            return False
        
        try:
            if POS_IMAP_TLS:
                context = ssl.create_default_context()
                self.connection = imaplib.IMAP4_SSL(
                    POS_IMAP_HOST, 
                    POS_IMAP_PORT, 
                    ssl_context=context
                )
            else:
                self.connection = imaplib.IMAP4(POS_IMAP_HOST, POS_IMAP_PORT)
            
            self.connection.login(POS_IMAP_USER, POS_IMAP_PASSWORD)
            logger.info(f"Connected to IMAP: {POS_IMAP_HOST}:{POS_IMAP_PORT}")
            return True
            
        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from IMAP server"""
        if self.connection:
            try:
                self.connection.logout()
            except:
                pass
            self.connection = None
    
    def select_folder(self, folder: str = "INBOX") -> bool:
        """Select mailbox folder"""
        try:
            status, data = self.connection.select(folder)
            return status == "OK"
        except Exception as e:
            logger.error(f"Folder selection failed: {e}")
            return False
    
    def search_mails(self, since_uid: int = 0) -> List[int]:
        """
        Search for mails matching our criteria.
        Returns list of UIDs.
        """
        try:
            # Search criteria: FROM noreply@gastronovi.de
            # Note: IMAP SEARCH doesn't support SUBJECT prefix easily,
            # so we filter subject in Python
            status, data = self.connection.uid('search', None, 
                f'(FROM "noreply@gastronovi.de" UID {since_uid + 1}:*)')
            
            if status != "OK":
                return []
            
            uid_list = data[0].split()
            return [int(uid) for uid in uid_list if int(uid) > since_uid]
            
        except Exception as e:
            logger.error(f"IMAP search failed: {e}")
            return []
    
    def fetch_mail(self, uid: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single mail by UID.
        Returns: {uid, message_id, from, subject, date, attachments: [{name, content}]}
        """
        try:
            status, data = self.connection.uid('fetch', str(uid), '(RFC822)')
            
            if status != "OK" or not data or not data[0]:
                return None
            
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Extract headers
            from_addr = decode_email_header(msg.get('From', ''))
            subject = decode_email_header(msg.get('Subject', ''))
            message_id = msg.get('Message-ID', '')
            date_str = msg.get('Date', '')
            
            # Filter: Subject must start with Tagesbericht or Monatsbericht
            subject_ok = any(subject.startswith(prefix) for prefix in SUBJECT_PREFIXES)
            if not subject_ok:
                logger.debug(f"Skipping mail UID {uid}: subject '{subject}' doesn't match filter")
                return None
            
            # Extract PDF attachments
            attachments = []
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = part.get('Content-Disposition', '')
                
                if 'attachment' in content_disposition or content_type == 'application/pdf':
                    filename = part.get_filename()
                    if filename:
                        filename = decode_email_header(filename)
                        if filename.lower().endswith('.pdf'):
                            content = part.get_payload(decode=True)
                            if content:
                                attachments.append({
                                    "name": filename,
                                    "content": content
                                })
            
            return {
                "uid": uid,
                "message_id": message_id,
                "from": from_addr,
                "subject": subject,
                "date": date_str,
                "attachments": attachments
            }
            
        except Exception as e:
            logger.error(f"Fetch mail UID {uid} failed: {e}")
            return None


# ============== INGEST LOGIC ==============

async def get_last_processed_uid() -> int:
    """Get last processed IMAP UID from state collection"""
    state = await db.pos_ingest_state.find_one({"key": "imap_last_uid"})
    return state.get("value", 0) if state else 0

async def set_last_processed_uid(uid: int):
    """Save last processed IMAP UID to state collection"""
    await db.pos_ingest_state.update_one(
        {"key": "imap_last_uid"},
        {"$set": {"value": uid, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )

async def check_hash_exists(file_hash: str) -> bool:
    """Check if PDF hash already exists (dupe protection)"""
    existing = await db.pos_documents.find_one({"file_hash_sha256": file_hash})
    return existing is not None

async def process_pdf_attachment(
    pdf_content: bytes,
    filename: str,
    mail_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process a single PDF attachment.
    Returns result dict with status.
    """
    result = {
        "status": "error",
        "filename": filename,
        "doc_id": None,
        "date": None,
        "error": None
    }
    
    # Calculate hash
    file_hash = calculate_sha256(pdf_content)
    
    # Check for duplicate
    if await check_hash_exists(file_hash):
        result["status"] = "duplicate"
        result["error"] = f"PDF bereits importiert (Hash: {file_hash[:16]}...)"
        logger.info(f"Skipping duplicate PDF: {filename}")
        return result
    
    # Determine doc type from subject
    doc_type = determine_doc_type(mail_info.get("subject", ""))
    
    # Save PDF to storage
    now = datetime.now(timezone.utc)
    year_month = now.strftime("%Y/%m")
    storage_path = f"{STORAGE_DIR}/{year_month}"
    os.makedirs(storage_path, exist_ok=True)
    
    safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    file_path = f"{storage_path}/{file_hash[:16]}_{safe_filename}"
    
    with open(file_path, 'wb') as f:
        f.write(pdf_content)
    
    # Create pos_documents entry
    doc = PosDocument(
        doc_type=doc_type,
        source="email",
        imap_uid=mail_info.get("uid"),
        message_id=mail_info.get("message_id"),
        received_at=mail_info.get("date", now.isoformat()),
        from_email=mail_info.get("from"),
        subject=mail_info.get("subject"),
        file_name=filename,
        file_hash_sha256=file_hash,
        file_path=file_path,
        parse_status=ParseStatus.STORED
    )
    
    await db.pos_documents.insert_one(doc.model_dump())
    result["doc_id"] = doc.id
    
    # Parse PDF
    parse_result = parse_gastronovi_pdf_v1(file_path)
    
    if not parse_result["success"]:
        # Update document with error
        await db.pos_documents.update_one(
            {"id": doc.id},
            {"$set": {
                "parse_status": ParseStatus.FAILED.value,
                "parse_error": parse_result.get("error"),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        result["status"] = "parse_failed"
        result["error"] = parse_result.get("error")
        return result
    
    # Update document with parsed data
    parsed_meta = {
        "date": parse_result.get("date"),
        "month": parse_result.get("month"),
        "is_monthly": parse_result.get("is_monthly"),
        "net_total": parse_result.get("net_total"),
        "food_net": parse_result.get("food_net"),
        "beverage_net": parse_result.get("beverage_net")
    }
    
    await db.pos_documents.update_one(
        {"id": doc.id},
        {"$set": {
            "parse_status": ParseStatus.PARSED.value,
            "parsed_meta": parsed_meta,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    result["date"] = parse_result.get("date")
    
    # For daily reports: upsert pos_daily_metrics
    if doc_type == DocType.DAILY and parse_result.get("date"):
        metrics = PosDailyMetrics(
            date=parse_result["date"],
            net_total=parse_result["net_total"],
            food_net=parse_result["food_net"],
            beverage_net=parse_result["beverage_net"],
            source_doc_id=doc.id
        )
        
        await db.pos_daily_metrics.update_one(
            {"date": metrics.date},
            {"$set": metrics.model_dump()},
            upsert=True
        )
        
        result["status"] = "success"
        logger.info(f"Daily metrics saved for {metrics.date}: net={metrics.net_total}, food={metrics.food_net}, bev={metrics.beverage_net}")
    
    elif doc_type == DocType.MONTHLY:
        # Monthly: just store, no metrics update (crosscheck only)
        result["status"] = "success_monthly"
        logger.info(f"Monthly report stored: {parse_result.get('month')}")
        
        # Optional: Crosscheck with daily sum
        if parse_result.get("month"):
            month = parse_result["month"]
            daily_sum = await db.pos_daily_metrics.aggregate([
                {"$match": {"date": {"$regex": f"^{month}"}}},
                {"$group": {"_id": None, "total": {"$sum": "$net_total"}}}
            ]).to_list(1)
            
            if daily_sum:
                daily_total = daily_sum[0].get("total", 0)
                monthly_total = parse_result.get("net_total", 0)
                diff = abs(monthly_total - daily_total)
                diff_pct = (diff / monthly_total * 100) if monthly_total > 0 else 0
                
                if diff > 50 or diff_pct > 1:
                    logger.warning(
                        f"Monthly crosscheck mismatch for {month}: "
                        f"Monthly={monthly_total:.2f}, Daily Sum={daily_total:.2f}, "
                        f"Diff={diff:.2f} ({diff_pct:.1f}%)"
                    )
    
    return result

async def run_mail_ingest() -> Dict[str, Any]:
    """
    Main ingest function: Connect to IMAP, fetch new mails, process PDFs.
    Called by scheduler every 10 minutes.
    """
    result = {
        "status": "error",
        "processed": 0,
        "skipped": 0,
        "failed": 0,
        "duplicates": 0,
        "errors": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None
    }
    
    # Check if password is configured
    if not POS_IMAP_PASSWORD:
        result["status"] = "not_configured"
        result["errors"].append("POS_IMAP_PASSWORD not set")
        logger.warning("Mail ingest skipped: POS_IMAP_PASSWORD not configured")
        return result
    
    client = IMAPClient()
    
    try:
        # Connect
        if not client.connect():
            result["errors"].append("IMAP connection failed")
            return result
        
        # Select folder
        if not client.select_folder(POS_IMAP_FOLDER):
            result["errors"].append(f"Could not select folder: {POS_IMAP_FOLDER}")
            return result
        
        # Get last processed UID
        last_uid = await get_last_processed_uid()
        logger.info(f"Starting mail ingest from UID > {last_uid}")
        
        # Search for new mails
        uids = client.search_mails(since_uid=last_uid)
        logger.info(f"Found {len(uids)} potential new mails")
        
        max_uid = last_uid
        
        for uid in uids:
            try:
                # Fetch mail
                mail_info = client.fetch_mail(uid)
                
                if not mail_info:
                    result["skipped"] += 1
                    max_uid = max(max_uid, uid)
                    continue
                
                # Process attachments
                if not mail_info.get("attachments"):
                    logger.debug(f"Mail UID {uid} has no PDF attachments")
                    result["skipped"] += 1
                    max_uid = max(max_uid, uid)
                    continue
                
                for attachment in mail_info["attachments"]:
                    proc_result = await process_pdf_attachment(
                        attachment["content"],
                        attachment["name"],
                        mail_info
                    )
                    
                    if proc_result["status"] == "success":
                        result["processed"] += 1
                    elif proc_result["status"] == "success_monthly":
                        result["processed"] += 1
                    elif proc_result["status"] == "duplicate":
                        result["duplicates"] += 1
                    else:
                        result["failed"] += 1
                        result["errors"].append(f"{attachment['name']}: {proc_result.get('error')}")
                
                max_uid = max(max_uid, uid)
                
            except Exception as e:
                logger.error(f"Error processing mail UID {uid}: {e}")
                result["failed"] += 1
                result["errors"].append(f"UID {uid}: {str(e)}")
                max_uid = max(max_uid, uid)
        
        # Update last processed UID
        if max_uid > last_uid:
            await set_last_processed_uid(max_uid)
            logger.info(f"Updated last processed UID to {max_uid}")
        
        result["status"] = "success"
        
    except Exception as e:
        logger.error(f"Mail ingest error: {e}")
        result["errors"].append(str(e))
    
    finally:
        client.disconnect()
    
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    
    # Log summary
    logger.info(
        f"Mail ingest complete: {result['processed']} processed, "
        f"{result['duplicates']} duplicates, {result['failed']} failed"
    )
    
    return result


# ============== SCHEDULER ==============

_scheduler_running = False
_scheduler_task = None

async def scheduler_loop():
    """Background scheduler running every 10 minutes"""
    global _scheduler_running
    
    while _scheduler_running:
        try:
            logger.info("Scheduler: Starting mail ingest...")
            result = await run_mail_ingest()
            
            # Save ingest log
            await db.pos_ingest_logs.insert_one({
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "result": result
            })
            
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        
        # Wait 10 minutes
        await asyncio.sleep(600)

def start_scheduler():
    """Start the background scheduler"""
    global _scheduler_running, _scheduler_task
    
    if _scheduler_running:
        logger.info("Scheduler already running")
        return
    
    _scheduler_running = True
    _scheduler_task = asyncio.create_task(scheduler_loop())
    logger.info("POS mail scheduler started (10-minute interval)")

def stop_scheduler():
    """Stop the background scheduler"""
    global _scheduler_running, _scheduler_task
    
    _scheduler_running = False
    if _scheduler_task:
        _scheduler_task.cancel()
        _scheduler_task = None
    logger.info("POS mail scheduler stopped")


# ============== API ENDPOINTS ==============

# Import auth dependency
try:
    from core.auth import require_admin
except ImportError:
    # Fallback if not available
    async def require_admin():
        return {"role": "admin"}

@pos_mail_router.post("/ingest/trigger")
async def trigger_ingest(user: dict = Depends(require_admin)):
    """
    Manually trigger mail ingest (admin-only).
    Useful for testing or immediate import.
    """
    result = await run_mail_ingest()
    return result

@pos_mail_router.get("/documents")
async def list_documents(
    doc_type: Optional[DocType] = Query(None),
    status: Optional[ParseStatus] = Query(None),
    limit: int = Query(50, le=200),
    user: dict = Depends(require_admin)
):
    """List POS documents (admin-only)"""
    query = {}
    if doc_type:
        query["doc_type"] = doc_type.value
    if status:
        query["parse_status"] = status.value
    
    docs = await db.pos_documents.find(
        query, 
        {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    
    return {
        "count": len(docs),
        "documents": docs
    }

@pos_mail_router.get("/daily-metrics")
async def list_daily_metrics(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    limit: int = Query(60, le=365),
    user: dict = Depends(require_admin)
):
    """List daily metrics (admin-only)"""
    query = {}
    
    if from_date:
        query["date"] = {"$gte": from_date}
    if to_date:
        if "date" in query:
            query["date"]["$lte"] = to_date
        else:
            query["date"] = {"$lte": to_date}
    
    metrics = await db.pos_daily_metrics.find(
        query,
        {"_id": 0}
    ).sort("date", -1).to_list(limit)
    
    # Calculate summary
    summary = None
    if metrics:
        summary = {
            "days": len(metrics),
            "total_net": round(sum(m.get("net_total", 0) for m in metrics), 2),
            "total_food": round(sum(m.get("food_net", 0) for m in metrics), 2),
            "total_beverage": round(sum(m.get("beverage_net", 0) for m in metrics), 2),
            "avg_daily_net": round(sum(m.get("net_total", 0) for m in metrics) / len(metrics), 2)
        }
    
    return {
        "metrics": metrics,
        "summary": summary
    }

@pos_mail_router.get("/ingest/status")
async def get_ingest_status(user: dict = Depends(require_admin)):
    """Get current ingest status (admin-only)"""
    last_uid = await get_last_processed_uid()
    
    # Get latest log
    latest_log = await db.pos_ingest_logs.find_one(
        {},
        {"_id": 0},
        sort=[("timestamp", -1)]
    )
    
    # Get document counts
    doc_count = await db.pos_documents.count_documents({})
    metrics_count = await db.pos_daily_metrics.count_documents({})
    failed_count = await db.pos_documents.count_documents({"parse_status": ParseStatus.FAILED.value})
    
    return {
        "scheduler_running": _scheduler_running,
        "last_processed_uid": last_uid,
        "imap_configured": bool(POS_IMAP_PASSWORD),
        "imap_host": POS_IMAP_HOST,
        "imap_user": POS_IMAP_USER,
        "imap_folder": POS_IMAP_FOLDER,
        "documents_total": doc_count,
        "metrics_total": metrics_count,
        "failed_documents": failed_count,
        "latest_ingest": latest_log
    }

@pos_mail_router.post("/scheduler/start")
async def start_scheduler_endpoint(user: dict = Depends(require_admin)):
    """Start the mail scheduler (admin-only)"""
    start_scheduler()
    return {"status": "started", "interval_minutes": 10}

@pos_mail_router.post("/scheduler/stop")
async def stop_scheduler_endpoint(user: dict = Depends(require_admin)):
    """Stop the mail scheduler (admin-only)"""
    stop_scheduler()
    return {"status": "stopped"}


# ============== CROSSCHECK & MONTHLY CONFIRM ==============

# Crosscheck thresholds (configurable)
CROSSCHECK_THRESHOLD_ABS = float(os.getenv("POS_CROSSCHECK_THRESHOLD_ABS", "50.0"))  # EUR
CROSSCHECK_THRESHOLD_PCT = float(os.getenv("POS_CROSSCHECK_THRESHOLD_PCT", "1.0"))   # %

async def crosscheck_pos_month(month: str) -> Dict[str, Any]:
    """
    Crosscheck monthly POS data: daily sum vs monthly PDF report.
    
    Args:
        month: Format YYYY-MM
        
    Returns:
        Crosscheck result with daily_sum, monthly_pdf values, diffs, and warning status
    """
    result = {
        "month": month,
        "has_monthly_pdf": False,
        "has_daily_data": False,
        "daily_count": 0,
        # Daily sum values
        "daily_sum_net_total": 0.0,
        "daily_sum_food_net": 0.0,
        "daily_sum_beverage_net": 0.0,
        # Monthly PDF values
        "monthly_pdf_net_total": None,
        "monthly_pdf_food_net": None,
        "monthly_pdf_beverage_net": None,
        # Differences
        "diff_abs_net_total": None,
        "diff_abs_food_net": None,
        "diff_abs_beverage_net": None,
        "diff_pct_net_total": None,
        "diff_pct_food_net": None,
        "diff_pct_beverage_net": None,
        # Status
        "warning": False,
        "warning_reasons": [],
        "checked_at": datetime.now(timezone.utc).isoformat()
    }
    
    # 1. Get daily sum for month
    daily_pipeline = [
        {"$match": {"date": {"$regex": f"^{month}"}}},
        {"$group": {
            "_id": None,
            "count": {"$sum": 1},
            "net_total": {"$sum": "$net_total"},
            "food_net": {"$sum": "$food_net"},
            "beverage_net": {"$sum": "$beverage_net"}
        }}
    ]
    
    daily_agg = await db.pos_daily_metrics.aggregate(daily_pipeline).to_list(1)
    
    if daily_agg:
        result["has_daily_data"] = True
        result["daily_count"] = daily_agg[0].get("count", 0)
        result["daily_sum_net_total"] = round(daily_agg[0].get("net_total", 0), 2)
        result["daily_sum_food_net"] = round(daily_agg[0].get("food_net", 0), 2)
        result["daily_sum_beverage_net"] = round(daily_agg[0].get("beverage_net", 0), 2)
    
    # 2. Get monthly PDF (latest for this month)
    monthly_doc = await db.pos_documents.find_one(
        {
            "doc_type": DocType.MONTHLY.value,
            "parse_status": ParseStatus.PARSED.value,
            "parsed_meta.month": month
        },
        {"_id": 0},
        sort=[("created_at", -1)]
    )
    
    if monthly_doc and monthly_doc.get("parsed_meta"):
        result["has_monthly_pdf"] = True
        meta = monthly_doc["parsed_meta"]
        result["monthly_pdf_net_total"] = meta.get("net_total")
        result["monthly_pdf_food_net"] = meta.get("food_net")
        result["monthly_pdf_beverage_net"] = meta.get("beverage_net")
        result["monthly_pdf_doc_id"] = monthly_doc.get("id")
        result["monthly_pdf_file"] = monthly_doc.get("file_name")
    
    # 3. Calculate differences (only if monthly PDF exists)
    if result["has_monthly_pdf"] and result["monthly_pdf_net_total"] is not None:
        # Net total diff
        result["diff_abs_net_total"] = round(
            result["daily_sum_net_total"] - result["monthly_pdf_net_total"], 2
        )
        if result["monthly_pdf_net_total"] > 0:
            result["diff_pct_net_total"] = round(
                (result["diff_abs_net_total"] / result["monthly_pdf_net_total"]) * 100, 2
            )
        
        # Food diff
        if result["monthly_pdf_food_net"] is not None:
            result["diff_abs_food_net"] = round(
                result["daily_sum_food_net"] - result["monthly_pdf_food_net"], 2
            )
            if result["monthly_pdf_food_net"] > 0:
                result["diff_pct_food_net"] = round(
                    (result["diff_abs_food_net"] / result["monthly_pdf_food_net"]) * 100, 2
                )
        
        # Beverage diff
        if result["monthly_pdf_beverage_net"] is not None:
            result["diff_abs_beverage_net"] = round(
                result["daily_sum_beverage_net"] - result["monthly_pdf_beverage_net"], 2
            )
            if result["monthly_pdf_beverage_net"] > 0:
                result["diff_pct_beverage_net"] = round(
                    (result["diff_abs_beverage_net"] / result["monthly_pdf_beverage_net"]) * 100, 2
                )
        
        # Check thresholds
        if abs(result["diff_abs_net_total"]) > CROSSCHECK_THRESHOLD_ABS:
            result["warning"] = True
            result["warning_reasons"].append(
                f"Net total diff {result['diff_abs_net_total']:.2f}€ exceeds threshold {CROSSCHECK_THRESHOLD_ABS}€"
            )
        
        if result["diff_pct_net_total"] is not None and abs(result["diff_pct_net_total"]) > CROSSCHECK_THRESHOLD_PCT:
            result["warning"] = True
            result["warning_reasons"].append(
                f"Net total diff {result['diff_pct_net_total']:.1f}% exceeds threshold {CROSSCHECK_THRESHOLD_PCT}%"
            )
    
    return result


@pos_mail_router.get("/monthly-crosscheck")
async def get_monthly_crosscheck(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$", description="Month in YYYY-MM format"),
    user: dict = Depends(require_admin)
):
    """
    Get crosscheck data for a month: daily sum vs monthly PDF.
    Shows differences and warnings if thresholds exceeded.
    """
    result = await crosscheck_pos_month(month)
    return result


@pos_mail_router.get("/monthly-status")
async def get_monthly_status(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$", description="Month in YYYY-MM format"),
    user: dict = Depends(require_admin)
):
    """
    Get complete monthly POS status including crosscheck and confirm state.
    """
    # Get crosscheck data
    crosscheck = await crosscheck_pos_month(month)
    
    # Get confirm status from monthly_business_metrics (if exists)
    monthly_metrics = await db.monthly_business_metrics.find_one(
        {"month": month},
        {"_id": 0}
    )
    
    confirmed = False
    locked = False
    confirmed_by = None
    confirmed_at = None
    
    if monthly_metrics:
        confirmed = monthly_metrics.get("status") == "confirmed"
        locked = monthly_metrics.get("locked", False)
        confirmed_by = monthly_metrics.get("confirmed_by")
        confirmed_at = monthly_metrics.get("confirmed_at")
    
    return {
        "month": month,
        "crosscheck": crosscheck,
        "confirmed": confirmed,
        "locked": locked,
        "confirmed_by": confirmed_by,
        "confirmed_at": confirmed_at
    }


@pos_mail_router.post("/monthly/{month}/confirm")
async def confirm_month(
    month: str,
    user: dict = Depends(require_admin)
):
    """
    Confirm/lock a month's POS data (admin-only).
    
    - Sets status=confirmed, locked=true
    - Stores crosscheck snapshot
    - Prevents future recalculations from overwriting
    """
    # Validate month format
    if not re.match(r"^\d{4}-\d{2}$", month):
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")
    
    # Get current crosscheck data
    crosscheck = await crosscheck_pos_month(month)
    
    # Prepare update
    now = datetime.now(timezone.utc).isoformat()
    user_email = user.get("email", user.get("sub", "unknown"))
    
    update_data = {
        "month": month,
        "status": "confirmed",
        "locked": True,
        "confirmed_by": user_email,
        "confirmed_at": now,
        "pos_crosscheck_snapshot": crosscheck,
        "updated_at": now
    }
    
    # Also store the POS sums in the monthly metrics
    if crosscheck["has_daily_data"]:
        update_data["pos_net_total"] = crosscheck["daily_sum_net_total"]
        update_data["pos_food_net"] = crosscheck["daily_sum_food_net"]
        update_data["pos_beverage_net"] = crosscheck["daily_sum_beverage_net"]
    
    # Upsert monthly_business_metrics
    result = await db.monthly_business_metrics.update_one(
        {"month": month},
        {"$set": update_data},
        upsert=True
    )
    
    # Audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "type": "monthly_confirm",
        "action": "pos_month_confirmed",
        "month": month,
        "confirmed_by": user_email,
        "timestamp": now,
        "crosscheck_warning": crosscheck["warning"],
        "crosscheck_snapshot": crosscheck
    })
    
    logger.info(f"Month {month} confirmed by {user_email}")
    
    return {
        "status": "confirmed",
        "month": month,
        "confirmed_by": user_email,
        "confirmed_at": now,
        "crosscheck": crosscheck,
        "had_warning": crosscheck["warning"]
    }


@pos_mail_router.get("/ingest/status-extended")
async def get_ingest_status_extended(user: dict = Depends(require_admin)):
    """
    Extended ingest status with additional stats for monitoring UI.
    """
    basic_status = await get_ingest_status(user)
    
    # Get current month
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    
    # Additional stats
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    
    # Documents today
    docs_today = await db.pos_documents.count_documents({
        "created_at": {"$gte": today + "T00:00:00"}
    })
    
    # Documents last 7 days
    docs_week = await db.pos_documents.count_documents({
        "created_at": {"$gte": week_ago + "T00:00:00"}
    })
    
    # Failed documents today
    failed_today = await db.pos_documents.count_documents({
        "parse_status": ParseStatus.FAILED.value,
        "created_at": {"$gte": today + "T00:00:00"}
    })
    
    # Failed documents last 7 days
    failed_week = await db.pos_documents.count_documents({
        "parse_status": ParseStatus.FAILED.value,
        "created_at": {"$gte": week_ago + "T00:00:00"}
    })
    
    # Last 10 failed documents
    failed_docs = await db.pos_documents.find(
        {"parse_status": ParseStatus.FAILED.value},
        {"_id": 0, "id": 1, "received_at": 1, "subject": 1, "parse_error": 1, "file_name": 1}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    # Last successful ingest
    last_success = await db.pos_ingest_logs.find_one(
        {"result.status": "success"},
        {"_id": 0, "timestamp": 1},
        sort=[("timestamp", -1)]
    )
    
    # Current month crosscheck (quick check)
    current_crosscheck = await crosscheck_pos_month(current_month)
    
    return {
        **basic_status,
        "extended": {
            "docs_today": docs_today,
            "docs_week": docs_week,
            "failed_today": failed_today,
            "failed_week": failed_week,
            "last_successful_ingest": last_success.get("timestamp") if last_success else None,
            "failed_documents": failed_docs,
            "current_month_crosscheck": {
                "month": current_month,
                "warning": current_crosscheck["warning"],
                "has_monthly_pdf": current_crosscheck["has_monthly_pdf"],
                "daily_count": current_crosscheck["daily_count"]
            }
        }
    }

