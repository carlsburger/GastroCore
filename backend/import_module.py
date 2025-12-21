"""
============================================================
CARLSBURG COCKPIT - DATA IMPORT MODULE
Sprint: Data Onboarding - Staff & Website Import
============================================================
"""

import os
import re
import csv
import io
import json
import uuid
import logging
import httpx
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

from core.database import db

logger = logging.getLogger(__name__)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def generate_slug(title: str) -> str:
    """Generate URL-friendly slug from title"""
    slug = title.lower()
    slug = re.sub(r'[äÄ]', 'ae', slug)
    slug = re.sub(r'[öÖ]', 'oe', slug)
    slug = re.sub(r'[üÜ]', 'ue', slug)
    slug = re.sub(r'[ß]', 'ss', slug)
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug[:50]

def parse_price(price_str: str) -> Optional[float]:
    """Parse price string to float"""
    if not price_str:
        return None
    # Remove currency symbols and clean up
    cleaned = re.sub(r'[€EUR\s]', '', price_str)
    cleaned = cleaned.replace(',', '.').strip()
    try:
        return float(cleaned)
    except ValueError:
        return None

def parse_date_from_text(text: str, year: int = None) -> Optional[str]:
    """Parse German date from text like 'Mi. 25' or 'Fr, 09.01.2026'"""
    if not year:
        year = datetime.now().year
    
    # Pattern: DD.MM.YYYY
    match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    
    # Pattern: DD.MM.
    match = re.search(r'(\d{1,2})\.(\d{1,2})\.', text)
    if match:
        day, month = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    
    return None


# ============================================================
# PART 1: STAFF IMPORT
# ============================================================

async def import_staff_from_json(data: List[Dict], override: bool = False) -> Dict[str, Any]:
    """Import staff members from JSON array"""
    results = {
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
        "details": []
    }
    
    for idx, row in enumerate(data):
        try:
            result = await import_single_staff(row, override)
            results["details"].append(result)
            if result["action"] == "created":
                results["created"] += 1
            elif result["action"] == "updated":
                results["updated"] += 1
            else:
                results["skipped"] += 1
        except Exception as e:
            results["errors"].append({"row": idx, "data": row, "error": str(e)})
    
    return results


async def import_staff_from_csv(csv_text: str, override: bool = False) -> Dict[str, Any]:
    """Import staff members from CSV text"""
    results = {
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
        "details": []
    }
    
    try:
        reader = csv.DictReader(io.StringIO(csv_text), delimiter=';')
        for idx, row in enumerate(reader):
            try:
                # Normalize keys (lowercase, strip)
                normalized = {k.strip().lower().replace(' ', '_'): v.strip() for k, v in row.items() if v}
                result = await import_single_staff(normalized, override)
                results["details"].append(result)
                if result["action"] == "created":
                    results["created"] += 1
                elif result["action"] == "updated":
                    results["updated"] += 1
                else:
                    results["skipped"] += 1
            except Exception as e:
                results["errors"].append({"row": idx + 1, "data": row, "error": str(e)})
    except Exception as e:
        results["errors"].append({"row": 0, "error": f"CSV Parse Error: {str(e)}"})
    
    return results


async def import_single_staff(data: Dict, override: bool = False) -> Dict[str, Any]:
    """Import or update a single staff member - IDEMPOTENT"""
    first_name = data.get("first_name", data.get("vorname", "")).strip()
    last_name = data.get("last_name", data.get("nachname", "")).strip()
    email = data.get("email", "").strip().lower() or None
    phone = data.get("phone", data.get("telefon", "")).strip() or None
    
    if not first_name or not last_name:
        return {"action": "skipped", "reason": "Missing first_name or last_name"}
    
    # Match by email (if exists) or first_name+last_name+phone
    existing = None
    if email:
        existing = await db.staff_members.find_one({"email": email, "archived": False})
    
    if not existing:
        query = {"first_name": first_name, "last_name": last_name, "archived": False}
        if phone:
            query["phone"] = phone
        existing = await db.staff_members.find_one(query)
    
    # Prepare staff data
    staff_data = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "role": data.get("role", data.get("rolle", "service")).lower(),
        "employment_type": data.get("employment_type", data.get("beschaeftigung", "teilzeit")).lower(),
        "status": "aktiv",
        "updated_at": now_iso()
    }
    
    # Optional fields
    if data.get("entry_date") or data.get("eintrittsdatum"):
        staff_data["entry_date"] = data.get("entry_date", data.get("eintrittsdatum"))
    if data.get("target_hours_week") or data.get("wochenstunden"):
        try:
            staff_data["weekly_hours"] = float(data.get("target_hours_week", data.get("wochenstunden", 0)))
        except:
            pass
    
    if existing:
        if override:
            # Update all fields
            await db.staff_members.update_one(
                {"id": existing["id"]},
                {"$set": staff_data}
            )
            return {"action": "updated", "id": existing["id"], "name": f"{first_name} {last_name}"}
        else:
            # Update only empty fields
            update_fields = {}
            for key, value in staff_data.items():
                if value and not existing.get(key):
                    update_fields[key] = value
            
            if update_fields:
                update_fields["updated_at"] = now_iso()
                await db.staff_members.update_one(
                    {"id": existing["id"]},
                    {"$set": update_fields}
                )
                return {"action": "updated", "id": existing["id"], "name": f"{first_name} {last_name}", "fields": list(update_fields.keys())}
            return {"action": "skipped", "id": existing["id"], "name": f"{first_name} {last_name}", "reason": "Already exists"}
    
    # Create new staff member
    staff_data["id"] = str(uuid.uuid4())
    staff_data["created_at"] = now_iso()
    staff_data["archived"] = False
    staff_data["work_area_ids"] = []
    
    await db.staff_members.insert_one(staff_data)
    return {"action": "created", "id": staff_data["id"], "name": f"{first_name} {last_name}"}


# ============================================================
# PART 2: WEBSITE IMPORT - VERANSTALTUNGEN & AKTIONEN
# ============================================================

async def fetch_carlsburg_page(url: str) -> str:
    """Fetch HTML content from carlsburg.de"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.text


def parse_veranstaltungen(html: str) -> List[Dict]:
    """Parse events from veranstaltungen page"""
    soup = BeautifulSoup(html, 'html.parser')
    events = []
    
    # Find event entries
    # Looking for list items with event data
    for item in soup.select('li'):
        text = item.get_text(separator=' ', strip=True)
        
        # Look for price pattern (XX.XX EUR or XX EUR)
        price_match = re.search(r'(\d+[,.]?\d*)\s*(EUR|Euro|€)', text, re.IGNORECASE)
        
        # Look for image
        img = item.find('img')
        image_url = img.get('src') if img else None
        
        # Extract title from h3 or strong or first significant text
        title_elem = item.find(['h3', 'h4', 'strong'])
        if not title_elem:
            continue
            
        title = title_elem.get_text(strip=True)
        if not title or len(title) < 5:
            continue
        
        # Skip navigation items
        if title.lower() in ['februar', 'märz', 'april', 'mai', 'juni', 'juli', 'august', 'september', 'oktober', 'november', 'dezember', 'januar']:
            continue
        
        # Get description
        description = text[:500] if text else ""
        
        # Parse date from the item
        date_str = None
        # Look for patterns like "Mi. 25" or date elements
        date_text = item.get_text()
        
        # Try to find year context from month headers
        month_match = re.search(r'(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s*(\d{4})?', date_text, re.IGNORECASE)
        
        event = {
            "title": title,
            "description": description[:500],
            "image_url": image_url,
            "price": parse_price(price_match.group(1)) if price_match else None,
            "source": "carlsburg_web",
            "source_url": "https://www.carlsburg.de/veranstaltungen/",
            "content_category": "VERANSTALTUNG",
            "booking_mode": "ticket" if price_match else "reservation",
            "default_start_time": "18:00",
            "needs_review": True  # All imported events need review for date
        }
        
        events.append(event)
    
    return events


def parse_aktionen(html: str) -> List[Dict]:
    """Parse actions from aktionen page"""
    soup = BeautifulSoup(html, 'html.parser')
    aktionen = []
    
    # Find sections with h2 headers (action titles)
    for h2 in soup.find_all('h2'):
        title = h2.get_text(strip=True)
        
        # Skip generic/navigation h2s
        if not title or len(title) < 5 or title.lower() in ['newsletter', 'reservieren']:
            continue
        
        # Get parent container
        container = h2.find_parent(['div', 'section', 'article'])
        if not container:
            container = h2.parent
        
        # Get all text content
        text = container.get_text(separator=' ', strip=True) if container else ""
        
        # Find image
        img = container.find('img') if container else None
        image_url = img.get('src') if img else None
        
        # Parse price
        price_match = re.search(r'(\d+[,.]?\d*)\s*(EUR|Euro|€)', text, re.IGNORECASE)
        price = parse_price(price_match.group(1)) if price_match else None
        
        # Determine category based on keywords
        title_lower = title.lower()
        text_lower = text.lower()
        
        # Check if menu choice is required
        requires_menu = False
        menu_options = []
        
        if any(kw in text_lower for kw in ['menüauswahl', 'wahl', 'vegetarisch', 'fleisch', 'fisch', 'hauptgang haben sie die wahl']):
            requires_menu = True
            # Try to extract menu options
            if 'vegetarisch' in text_lower:
                menu_options.append({"title": "Vegetarisch", "description": "Vegetarische Variante"})
            if 'fleisch' in text_lower:
                menu_options.append({"title": "Fleisch", "description": "Mit Fleisch"})
            if 'fisch' in text_lower:
                menu_options.append({"title": "Fisch", "description": "Mit Fisch"})
        
        content_category = "AKTION_MENUE" if requires_menu else "AKTION"
        booking_mode = "reservation_with_menu_choice" if requires_menu else "reservation"
        
        # Parse dates from text
        dates = []
        date_patterns = re.findall(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', text)
        for day, month, year in date_patterns:
            dates.append(f"{year}-{int(month):02d}-{int(day):02d}")
        
        # Extract description (first 500 chars, cleaned)
        description = text[:800]
        
        aktion = {
            "title": title,
            "description": description,
            "image_url": image_url,
            "price": price,
            "source": "carlsburg_web",
            "source_url": f"https://www.carlsburg.de/aktionen/#{generate_slug(title)}",
            "content_category": content_category,
            "booking_mode": booking_mode,
            "default_start_time": "17:00",
            "requires_menu_choice": requires_menu,
            "menu_options": menu_options if requires_menu else [],
            "dates": dates[:10] if dates else [],  # Max 10 dates
            "needs_review": len(dates) == 0  # Needs review if no dates found
        }
        
        aktionen.append(aktion)
    
    return aktionen


async def import_carlsburg_content(
    mode: str = "dry_run",
    sources: List[str] = None,
    default_event_time: str = "18:00"
) -> Dict[str, Any]:
    """
    Import content from carlsburg.de
    
    Args:
        mode: "dry_run" (preview only) or "apply" (actually import)
        sources: List of sources to import ["aktionen", "veranstaltungen"]
        default_event_time: Default start time for events
    
    Returns:
        Import report with statistics
    """
    if sources is None:
        sources = ["aktionen", "veranstaltungen"]
    
    results = {
        "mode": mode,
        "sources": sources,
        "timestamp": now_iso(),
        "found": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "needs_review": 0,
        "items": [],
        "errors": []
    }
    
    all_items = []
    
    # Fetch and parse Veranstaltungen
    if "veranstaltungen" in sources:
        try:
            html = await fetch_carlsburg_page("https://www.carlsburg.de/veranstaltungen/")
            veranstaltungen = parse_veranstaltungen(html)
            all_items.extend(veranstaltungen)
            logger.info(f"Parsed {len(veranstaltungen)} Veranstaltungen")
        except Exception as e:
            results["errors"].append({"source": "veranstaltungen", "error": str(e)})
            logger.error(f"Error fetching Veranstaltungen: {e}")
    
    # Fetch and parse Aktionen
    if "aktionen" in sources:
        try:
            html = await fetch_carlsburg_page("https://www.carlsburg.de/aktionen/")
            aktionen = parse_aktionen(html)
            all_items.extend(aktionen)
            logger.info(f"Parsed {len(aktionen)} Aktionen")
        except Exception as e:
            results["errors"].append({"source": "aktionen", "error": str(e)})
            logger.error(f"Error fetching Aktionen: {e}")
    
    results["found"] = len(all_items)
    
    # Process each item
    for item in all_items:
        item["default_start_time"] = item.get("default_start_time", default_event_time)
        
        # Check for existing by source_url
        source_url = item.get("source_url", "")
        title_slug = generate_slug(item["title"])
        
        existing = await db.events.find_one({
            "$or": [
                {"source_url": source_url},
                {"title": item["title"], "source": "carlsburg_web"}
            ],
            "archived": False
        })
        
        if existing:
            item["status"] = "update"
            item["existing_id"] = existing["id"]
        else:
            item["status"] = "new"
        
        if item.get("needs_review"):
            results["needs_review"] += 1
        
        # Apply changes if not dry_run
        if mode == "apply":
            try:
                if existing:
                    # Update existing
                    update_data = {
                        "title": item["title"],
                        "description": item["description"],
                        "image_url": item.get("image_url"),
                        "price_per_person": item.get("price"),
                        "content_category": item["content_category"],
                        "booking_mode": item["booking_mode"],
                        "needs_review": item.get("needs_review", False),
                        "updated_at": now_iso(),
                        "source": "carlsburg_web",
                        "source_url": source_url
                    }
                    
                    if item.get("requires_menu_choice"):
                        update_data["requires_menu_choice"] = True
                        if item.get("menu_options"):
                            update_data["menu_options"] = [
                                {"option_id": str(uuid.uuid4()), **opt}
                                for opt in item["menu_options"]
                            ]
                    
                    await db.events.update_one(
                        {"id": existing["id"]},
                        {"$set": update_data}
                    )
                    results["updated"] += 1
                    item["action"] = "updated"
                else:
                    # Create new event
                    event_data = {
                        "id": str(uuid.uuid4()),
                        "title": item["title"],
                        "description": item["description"],
                        "image_url": item.get("image_url"),
                        "price_per_person": item.get("price"),
                        "content_category": item["content_category"],
                        "booking_mode": item["booking_mode"],
                        "default_start_time": item["default_start_time"],
                        "needs_review": item.get("needs_review", True),
                        "requires_menu_choice": item.get("requires_menu_choice", False),
                        "menu_options": [
                            {"option_id": str(uuid.uuid4()), **opt}
                            for opt in item.get("menu_options", [])
                        ],
                        "source": "carlsburg_web",
                        "source_url": source_url,
                        "status": "draft",  # Imported as draft, needs review
                        "capacity": 40,
                        "available_capacity": 40,
                        "is_public": False,  # Not public until reviewed
                        "created_at": now_iso(),
                        "updated_at": now_iso(),
                        "archived": False
                    }
                    
                    await db.events.insert_one(event_data)
                    results["created"] += 1
                    item["action"] = "created"
                    item["new_id"] = event_data["id"]
                    
            except Exception as e:
                results["errors"].append({"item": item["title"], "error": str(e)})
                item["action"] = "error"
                item["error"] = str(e)
        else:
            item["action"] = "preview"
        
        results["items"].append({
            "title": item["title"],
            "category": item["content_category"],
            "status": item["status"],
            "action": item.get("action", "preview"),
            "price": item.get("price"),
            "needs_review": item.get("needs_review", False),
            "requires_menu_choice": item.get("requires_menu_choice", False),
            "source_url": source_url
        })
    
    results["skipped"] = results["found"] - results["created"] - results["updated"]
    
    return results


# ============================================================
# MANUAL EVENT DEFINITIONS (Based on actual website content)
# ============================================================

CARLSBURG_VERANSTALTUNGEN = [
    {
        "title": "Bob Lehmann - Neues Programm",
        "description": "Er ist wieder da – mit neuem Programm und ein bischen verrückt wie immer. Du blühst und lebst, egal ob du dich verwegen durch die Erde wühlst oder einladend irgendwo herunterhangelst.",
        "dates": ["2026-02-25", "2026-02-26"],
        "price": 29.00,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2022/02/bob-lehmann-1800.jpg",
        "content_category": "VERANSTALTUNG",
        "booking_mode": "ticket"
    },
    {
        "title": "Die Kaktusblüte - Dresdner Kabarett",
        "description": "Wenn im neuen Programm des Dresdner Kabaretts Die Kaktusblüte Friedemann Heinrich und Uwe Hänchen mit ihrer Pianistin Janka Scheudeck wieder dem Zeitgeist auf der Spur sind.",
        "dates": ["2026-02-27"],
        "price": 29.00,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2024/05/Die-Kaktusbluete-serioes.jpg",
        "content_category": "VERANSTALTUNG",
        "booking_mode": "ticket"
    },
    {
        "title": "UNIKAT - Die Zugabe",
        "description": "Sarah Barelly und Jordan Smart bringen das Beste aus Travestie, Live-Gesang, Cabaret und Comedy auf die Bühne.",
        "dates": ["2026-02-28"],
        "price": 39.00,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2023/11/UNIKAT-die-Zugabe-Quadrat.png",
        "content_category": "VERANSTALTUNG",
        "booking_mode": "ticket"
    },
    {
        "title": "Trudchen und Irmchen - Wir sind nicht alt!",
        "description": "Dagmar Gelbke und Margit Meller als die 75-jährigen unverwüstlichen Rentnerinnen Trudchen und Irmchen.",
        "dates": ["2026-03-04"],
        "price": 29.00,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2023/11/Dagmar-Gelbke-Trudchen-und-Irmchen-scaled.jpg",
        "content_category": "VERANSTALTUNG",
        "booking_mode": "ticket"
    },
    {
        "title": "Elke Winter - Frauentag Solo",
        "description": "Zum Frauentag 2026 kommt Elke Winter wieder einmal Solo. Sie ist die erste Künstlerin in der Weltgeschichte der Travestie, die ihr wahres Alter nicht verschweigt.",
        "dates": ["2026-03-05", "2026-03-06"],
        "price": 29.00,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2025/05/elke-winter-teaser-1.webp",
        "content_category": "VERANSTALTUNG",
        "booking_mode": "ticket"
    },
    {
        "title": "Big Helga - Helga Hahnemann Programm",
        "description": "Dagmar Gelbke und Wolfgang Flieder mit dem Programm zum 34. Todestag der DDR-Showbiz Legende.",
        "dates": ["2026-03-07", "2026-03-08"],
        "price": 29.00,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2023/08/dagmar-gelbke-wolfgang-flieder-1800.jpg",
        "content_category": "VERANSTALTUNG",
        "booking_mode": "ticket"
    },
    {
        "title": "Schwarze Grütze - Auf dünnem Eis",
        "description": "Stefan Klucke und Dirk Pursche mit nagelneuen, bitterwitzigen Songs auf ganz dünnem Eis.",
        "dates": ["2026-03-12"],
        "price": 29.00,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2025/05/Schwarze_Gruetze_Eis_quer_Goeran_Gnaudschun-1024x709-1.jpg",
        "content_category": "VERANSTALTUNG",
        "booking_mode": "ticket"
    },
    {
        "title": "CLOVER - Irish Folk Party",
        "description": "Die Folk Formation CLOVER aus Berlin. Immer wieder ausverkauft, immer wieder bombige Stimmung!",
        "dates": ["2026-05-13"],
        "price": 29.00,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2023/04/CLOVER_Trio.jpg",
        "content_category": "VERANSTALTUNG",
        "booking_mode": "ticket"
    }
]

CARLSBURG_AKTIONEN = [
    {
        "title": "Valentinsabend - Ein Abend für zwei",
        "description": "6-Gang-Valentinsmenü bei Kerzenschein. Beim Hauptgang haben Sie die Wahl – vegetarisch, mit Fleisch oder Fisch.",
        "dates": ["2026-02-14"],
        "price": 59.90,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2025/12/Valentinstag-Event-an-der-Carlsburg.png",
        "content_category": "AKTION_MENUE",
        "booking_mode": "reservation_with_menu_choice",
        "requires_menu_choice": True,
        "menu_options": [
            {"title": "Vegetarisch", "description": "Vegetarische Hauptgang-Variante", "price_delta": -10.00},
            {"title": "Fleisch", "description": "Hauptgang mit Fleisch", "price_delta": 0},
            {"title": "Fisch", "description": "Hauptgang mit Fisch", "price_delta": 0}
        ],
        "default_start_time": "17:00"
    },
    {
        "title": "Spareribs Sattessen",
        "description": "Spareribs-Sattessen nach amerikanischer Art. Saftige Schweinerippchen mit Kartoffel Wedges und Cole Slaw, sowie würzige hausgemachte Barbecue-Sauce.",
        "dates": ["2026-01-09", "2026-02-06", "2026-03-11", "2026-03-12"],
        "price": 25.90,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2022/01/carlsburg-spareribs-1800.jpg",
        "content_category": "AKTION",
        "booking_mode": "reservation",
        "default_start_time": "17:00"
    },
    {
        "title": "Großgarnelen Sattessen",
        "description": "Riesengarnelen essen, soviel Sie mögen! Wahlweise mit Aioli und unserem Asia Dip.",
        "dates": ["2026-01-16", "2026-02-13", "2026-05-06", "2026-05-07"],
        "price": 35.90,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2022/01/carlsburg-grossgarnelen-1800.jpg",
        "content_category": "AKTION",
        "booking_mode": "reservation",
        "default_start_time": "17:00"
    },
    {
        "title": "Schnitzel Sattessen",
        "description": "Zwei verschiedene Schnitzel-Varianten – Klassisches Schweineschnitzel nach Wiener Art und Hähnchenschnitzel in Panko-Chili-Panade.",
        "dates": ["2026-01-30", "2026-06-03", "2026-06-17"],
        "price": 29.90,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2025/03/schnitzel-satt-3.jpg",
        "content_category": "AKTION",
        "booking_mode": "reservation",
        "default_start_time": "17:00"
    },
    {
        "title": "Mediterraner Tapas-Abend",
        "description": "Mediterranes Geschmacksparadies mit liebevoll komponierter Tapas-Auswahl. Serranoschinken, Manchego, gebratene Chorizo, Pimientos de Padrón und mehr.",
        "dates": ["2026-01-23", "2026-02-20", "2026-06-05", "2026-06-19"],
        "price": None,  # Variable pricing per item
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2025/03/tapas-1-2.jpg",
        "content_category": "AKTION",
        "booking_mode": "reservation",
        "default_start_time": "17:00"
    },
    {
        "title": "Carlsburger Terrassen BBQ",
        "description": "Die feinsten Leckereien vom Grill: Lachs in Folie, Argentinisches Entrecôte, Lamm-Spieße auf der Terrasse mit Ausblick über das Oderbruch.",
        "dates": ["2026-07-24", "2026-07-25", "2026-08-07", "2026-08-08"],
        "price": None,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2022/01/carlsburg-bbg-1800.jpg",
        "content_category": "AKTION",
        "booking_mode": "reservation",
        "default_start_time": "17:00"
    },
    {
        "title": "Ente Sattessen",
        "description": "Zur vorweihnachtlichen Zeit: Federvieh samt Rot- und Grünkohl sowie Kartoffelklößen, so viel Sie mögen.",
        "dates": ["2026-10-04", "2026-10-11", "2026-10-18", "2026-10-25", "2026-11-01", "2026-11-22", "2026-11-29", "2026-12-06", "2026-12-13", "2026-12-20", "2026-12-27"],
        "price": 34.90,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2022/01/carlsburg-entenschmaus-1800.jpg",
        "content_category": "AKTION",
        "booking_mode": "reservation",
        "default_start_time": "17:00"
    },
    {
        "title": "Martinsgans Essen",
        "description": "3-Gänge Menü: Bouillon vom Gänseklein, knuspriger Gänsebraten mit zweierlei Kohl und Kartoffelklößen, hausgemachtes Wintereis.",
        "dates": ["2026-11-07", "2026-11-08", "2026-11-14", "2026-11-15", "2026-11-21", "2026-11-22"],
        "price": 49.90,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2022/01/carlsburg-martinsgans-1400.jpg",
        "content_category": "AKTION_MENUE",
        "booking_mode": "reservation_with_menu_choice",
        "requires_menu_choice": True,
        "menu_options": [
            {"title": "3-Gänge Menü", "description": "Suppe, Gänsebraten, Dessert", "price_delta": 0},
            {"title": "Nur Gänsebraten", "description": "Gänsebraten mit Beilagen (ohne Suppe/Dessert)", "price_delta": -15.00}
        ],
        "default_start_time": "17:00"
    }
]


async def import_predefined_carlsburg_data(mode: str = "dry_run") -> Dict[str, Any]:
    """
    Import predefined Carlsburg data (structured from website)
    This is more reliable than HTML parsing
    """
    results = {
        "mode": mode,
        "timestamp": now_iso(),
        "veranstaltungen": {"created": 0, "updated": 0, "skipped": 0},
        "aktionen": {"created": 0, "updated": 0, "skipped": 0},
        "items": [],
        "errors": []
    }
    
    all_items = []
    
    # Process Veranstaltungen
    for v in CARLSBURG_VERANSTALTUNGEN:
        v["source"] = "carlsburg_web"
        v["source_url"] = f"https://www.carlsburg.de/veranstaltungen/#{generate_slug(v['title'])}"
        v["default_start_time"] = "18:00"
        v["category_type"] = "veranstaltungen"
        all_items.append(v)
    
    # Process Aktionen
    for a in CARLSBURG_AKTIONEN:
        a["source"] = "carlsburg_web"
        a["source_url"] = f"https://www.carlsburg.de/aktionen/#{generate_slug(a['title'])}"
        a["category_type"] = "aktionen"
        all_items.append(a)
    
    for item in all_items:
        cat_type = item.pop("category_type")
        cat_key = "veranstaltungen" if cat_type == "veranstaltungen" else "aktionen"
        
        # Check for existing
        existing = await db.events.find_one({
            "title": item["title"],
            "source": "carlsburg_web",
            "archived": False
        })
        
        status = "update" if existing else "new"
        
        if mode == "apply":
            try:
                if existing:
                    # Update
                    update_data = {
                        "description": item["description"],
                        "image_url": item.get("image_url"),
                        "price_per_person": item.get("price"),
                        "content_category": item["content_category"],
                        "booking_mode": item["booking_mode"],
                        "default_start_time": item.get("default_start_time", "17:00"),
                        "requires_menu_choice": item.get("requires_menu_choice", False),
                        "updated_at": now_iso(),
                        "source_url": item["source_url"]
                    }
                    
                    if item.get("menu_options"):
                        update_data["menu_options"] = [
                            {"option_id": str(uuid.uuid4()), **opt}
                            for opt in item["menu_options"]
                        ]
                    
                    await db.events.update_one({"id": existing["id"]}, {"$set": update_data})
                    results[cat_key]["updated"] += 1
                    action = "updated"
                else:
                    # Create
                    event_data = {
                        "id": str(uuid.uuid4()),
                        "title": item["title"],
                        "description": item["description"],
                        "image_url": item.get("image_url"),
                        "price_per_person": item.get("price"),
                        "content_category": item["content_category"],
                        "booking_mode": item["booking_mode"],
                        "default_start_time": item.get("default_start_time", "17:00"),
                        "requires_menu_choice": item.get("requires_menu_choice", False),
                        "menu_options": [
                            {"option_id": str(uuid.uuid4()), **opt}
                            for opt in item.get("menu_options", [])
                        ],
                        "source": "carlsburg_web",
                        "source_url": item["source_url"],
                        "status": "published",
                        "is_public": True,
                        "capacity": 40,
                        "available_capacity": 40,
                        "event_type": "dinner" if cat_type == "aktionen" else "show",
                        "created_at": now_iso(),
                        "updated_at": now_iso(),
                        "archived": False
                    }
                    
                    # Set first date if available
                    if item.get("dates") and len(item["dates"]) > 0:
                        event_data["date"] = item["dates"][0]
                        event_data["time_start"] = item.get("default_start_time", "17:00")
                    
                    await db.events.insert_one(event_data)
                    results[cat_key]["created"] += 1
                    action = "created"
                    
            except Exception as e:
                results["errors"].append({"item": item["title"], "error": str(e)})
                action = "error"
        else:
            action = "preview"
        
        results["items"].append({
            "title": item["title"],
            "category": item["content_category"],
            "status": status,
            "action": action,
            "price": item.get("price"),
            "dates_count": len(item.get("dates", [])),
            "requires_menu_choice": item.get("requires_menu_choice", False)
        })
    
    return results
