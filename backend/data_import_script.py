"""
GastroCore Data Import Script
========================================
Importiert:
1. Mitarbeiter aus XLSX-Daten
2. Events & Aktionen von carlsburg.de
"""

import asyncio
import sys
sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import uuid
import os
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'carlsburg_db')

# Connect to MongoDB
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

def now_iso():
    return datetime.now(timezone.utc).isoformat()

# =========================================================
# TEIL A: MITARBEITER-IMPORT AUS XLSX-DATEN
# =========================================================

XLSX_DATA = [
    {"nachname": "Caban", "vorname": "Alicja", "zeit_pin": "4468", "rufname": "Alicja", "adresse": "Kolonia 23/2", "stadt": "Cedynia", "plz": "74520", "pers_nr": "1016", "email": "alicjacaban@onet.pl", "telefon": "+48512359612", "geburtstag": "27.04.1993"},
    {"nachname": "Fenske", "vorname": "Nicole", "zeit_pin": "1906", "rufname": "Nicole", "adresse": "Oderbruchstraße 16", "stadt": "Eberswalde", "plz": "16227", "pers_nr": "1012", "email": "deinenummer1@outlook.de", "telefon": "01729420499", "geburtstag": "19.06.1976"},
    {"nachname": "Gebel", "vorname": "Jacqueline", "zeit_pin": "9999", "rufname": "Jacqueline", "adresse": "Lindenstraße 37", "stadt": "Berlin", "plz": "12621", "pers_nr": "1020", "email": "jacquelinegebel@web.de", "telefon": "01782106650", "geburtstag": ""},
    {"nachname": "Graef", "vorname": "Sascha", "zeit_pin": "0806", "rufname": "Sascha", "adresse": "Schubertstraße 14", "stadt": "Brakel", "plz": "33034", "pers_nr": "1037", "email": "graef87@web.de", "telefon": "017677853856", "geburtstag": "08.06.1987"},
    {"nachname": "Jaskolla", "vorname": "Simon", "zeit_pin": "2512", "rufname": "Simon", "adresse": "Danckelmannstr. 23", "stadt": "Eberswalde", "plz": "16225", "pers_nr": "1032", "email": "simon.jasko1@gmail.com", "telefon": "017632295378", "geburtstag": "25.12.2000"},
    {"nachname": "Listowska", "vorname": "Justina", "zeit_pin": "3009", "rufname": "Justina", "adresse": "Ul. Mieszka 16", "stadt": "Cedynia", "plz": "74520", "pers_nr": "1011", "email": "jlistowska@gmail.com", "telefon": "+48695379216", "geburtstag": "30.09.1987"},
    {"nachname": "Senst", "vorname": "Annett", "zeit_pin": "2604", "rufname": "Annett", "adresse": "Wriezner Straße 87", "stadt": "Bad Freienwalde", "plz": "16259", "pers_nr": "1038", "email": "frettchen80@web.de", "telefon": "01723920630", "geburtstag": "26.04.1980"},
    {"nachname": "Steinert", "vorname": "Thomas", "zeit_pin": "2112", "rufname": "Tom", "adresse": "Alt-Friedrichsfelde 39", "stadt": "Berlin", "plz": "10315", "pers_nr": "1001", "email": "t.steinert@carlsburg.de", "telefon": "01749422589", "geburtstag": "21.12.1968"},
    {"nachname": "Taebling", "vorname": "Julia", "zeit_pin": "1505", "rufname": "Julia", "adresse": "Linsingenstraße 3", "stadt": "Bad Freienwalde", "plz": "16259", "pers_nr": "1006", "email": "taeblingjulia@gmail.com", "telefon": "01628873843", "geburtstag": "15.05.1979"},
    {"nachname": "Wolf", "vorname": "Luisa", "zeit_pin": "1912", "rufname": "Luisa", "adresse": "Herrmann-Seidel-Straße 6", "stadt": "Oderberg", "plz": "16248", "pers_nr": "1023", "email": "wolf-luisa2@web.de", "telefon": "017683293269", "geburtstag": "19.12.2007"},
    {"nachname": "Wolgast", "vorname": "Leonie", "zeit_pin": "2804", "rufname": "", "adresse": "Höhenweg 2a", "stadt": "Eberswalde", "plz": "16225", "pers_nr": "1021", "email": "leonie.wolgast@outlook.com", "telefon": "01793249566", "geburtstag": "28.04.2007"},
    {"nachname": "Ziegler", "vorname": "Fiete", "zeit_pin": "2412", "rufname": "Fiete", "adresse": "Am Grund 10", "stadt": "Britz", "plz": "16230", "pers_nr": "1013", "email": "fiete.ziegler@gmx.de", "telefon": "01709793839", "geburtstag": "24.12.1995"},
]

async def import_staff(dry_run=True):
    """Import staff members from XLSX data"""
    results = {
        "would_create": [],
        "would_update": [],
        "would_skip": [],
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": []
    }
    
    for row in XLSX_DATA:
        first_name = row["vorname"].strip()
        last_name = row["nachname"].strip()
        email = row.get("email", "").strip().lower() or None
        phone = row.get("telefon", "").strip() or None
        
        if not first_name or not last_name:
            results["would_skip"].append({"reason": "Missing name", "data": row})
            results["skipped"] += 1
            continue
        
        # Skip the duplicate "Inh. Thomas" row
        if "Inh." in last_name or "Inh." in first_name:
            results["would_skip"].append({"reason": "Inhaber-Duplikat", "data": row})
            results["skipped"] += 1
            continue
        
        # Check for existing by email or name
        existing = None
        if email:
            existing = await db.staff_members.find_one({"email": email, "archived": {"$ne": True}})
        if not existing:
            existing = await db.staff_members.find_one({
                "first_name": first_name, 
                "last_name": last_name, 
                "archived": {"$ne": True}
            })
        
        # Parse birthday
        birthday = None
        if row.get("geburtstag"):
            try:
                parts = row["geburtstag"].split(".")
                if len(parts) == 3:
                    birthday = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
            except:
                pass
        
        staff_data = {
            "first_name": first_name,
            "last_name": last_name,
            "nickname": row.get("rufname", "").strip() or None,
            "email": email,
            "phone": phone,
            "address_street": row.get("adresse", "").strip() or None,
            "address_city": row.get("stadt", "").strip() or None,
            "address_zip": row.get("plz", "").strip() or None,
            "employee_number": row.get("pers_nr", "").strip() or None,
            "time_clock_pin": row.get("zeit_pin", "").strip() or None,
            "birth_date": birthday,
            "role": "service",  # Default role
            "employment_type": "teilzeit",  # Default
            "status": "aktiv",
            "updated_at": now_iso(),
        }
        
        if existing:
            # Update only empty fields
            update_fields = {}
            for key, value in staff_data.items():
                if value and not existing.get(key):
                    update_fields[key] = value
            
            if update_fields:
                record = {
                    "action": "update",
                    "id": existing["id"],
                    "name": f"{first_name} {last_name}",
                    "fields": list(update_fields.keys()),
                    "data": staff_data
                }
                results["would_update"].append(record)
                
                if not dry_run:
                    update_fields["updated_at"] = now_iso()
                    await db.staff_members.update_one(
                        {"id": existing["id"]},
                        {"$set": update_fields}
                    )
                    results["updated"] += 1
            else:
                results["would_skip"].append({
                    "action": "skip",
                    "id": existing["id"],
                    "name": f"{first_name} {last_name}",
                    "reason": "Already exists with all data"
                })
                results["skipped"] += 1
        else:
            # Create new
            staff_data["id"] = str(uuid.uuid4())
            staff_data["created_at"] = now_iso()
            staff_data["archived"] = False
            staff_data["work_area_ids"] = []
            
            results["would_create"].append({
                "action": "create",
                "name": f"{first_name} {last_name}",
                "email": email,
                "data": staff_data
            })
            
            if not dry_run:
                await db.staff_members.insert_one(staff_data)
                results["created"] += 1
    
    return results

# =========================================================
# TEIL B: EVENTS & AKTIONEN VON WEBSITE
# =========================================================

VERANSTALTUNGEN = [
    {
        "title": "Bob Lehmann - Neues Programm",
        "description": "Er ist wieder da – mit neuem Programm und ein bischen verrückt wie immer. Du blühst und lebst, egal ob du dich verwegen durch die Erde wühlst oder einladend irgendwo herunterhangelst. Lass uns deine Wurzeln begießen und deine Knospen besingen, bis die Schneeglöckchen die Mitternacht bebimmeln.",
        "dates": ["2026-02-25", "2026-02-26"],
        "price": 29.00,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2022/02/bob-lehmann-1800.jpg",
        "default_start_time": "18:00",
    },
    {
        "title": "Die Kaktusblüte - Dresdner Kabarett",
        "description": "Wenn im neuen Programm des Dresdner Kabaretts Die Kaktusblüte Friedemann Heinrich und Uwe Hänchen mit ihrer Pianistin Janka Scheudeck wieder dem Zeitgeist auf der Spur sind, dann treffen die große Politik und der alltägliche Schwachsinn aufeinander.",
        "dates": ["2026-02-27"],
        "price": 29.00,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2024/05/Die-Kaktusbluete-serioes.jpg",
        "default_start_time": "18:00",
    },
    {
        "title": "UNIKAT - Die Zugabe",
        "description": "Nach dem durchschlagenden Erfolg der UNIKAT Xmas Tour 2024 kehren sie zurück – und zwar mit einer Zugabe! Sarah Barelly und Jordan Smart bringen noch einmal das Beste aus Travestie, Live-Gesang, Cabaret und Comedy auf die Bühne.",
        "dates": ["2026-02-28"],
        "price": 39.00,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2023/11/UNIKAT-die-Zugabe-Quadrat.png",
        "default_start_time": "18:00",
    },
    {
        "title": "Trudchen und Irmchen - Dagmar Gelbke & Margit Meller",
        "description": "Wir sind nicht alt! Aber Sexxy! – Trudchen und Irmchen – zwei Rentnerinnen packen an. Die aus dem Osten übrig gebliebenen Rentnerinnen Trudchen und Irmchen werden trotzig verkünden.",
        "dates": ["2026-03-04"],
        "price": 29.00,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2023/11/Dagmar-Gelbke-Trudchen-und-Irmchen-scaled.jpg",
        "default_start_time": "18:00",
    },
    {
        "title": "Elke Winter - Solo-Programm zum Frauentag",
        "description": "Zum Frauentag 2026 kommt Elke Winter in diesem Jahr wieder einmal Solo zu uns. Sie ist die erste Künstlerin in der Weltgeschichte der Travestie, die ihr wahres Alter nicht verschweigt.",
        "dates": ["2026-03-05", "2026-03-06"],
        "price": 29.00,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2025/05/elke-winter-teaser-1.webp",
        "default_start_time": "18:00",
    },
    {
        "title": "Big Helga - Helga Hahnemann Programm",
        "description": "Big Helga – Een kleenet Menschenkind - das Helga Hahnemann Programm mit Dagmar Gelbke und Wolfgang Flieder. Programm zum 34. Todestag der DDR-Showbiz Legende.",
        "dates": ["2026-03-07", "2026-03-08"],
        "price": 29.00,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2023/08/dagmar-gelbke-wolfgang-flieder-1800.jpg",
        "default_start_time": "18:00",
    },
    {
        "title": "Schwarze Grütze - Dünnes Eis",
        "description": "In ihrem zehnten Bühnenprogramm begeben sich Stefan Klucke und Dirk Pursche mit nagelneuen, bitterwitzigen Songs mal wieder auf ganz dünnes Eis.",
        "dates": ["2026-03-12"],
        "price": 29.00,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2025/05/Schwarze_Gruetze_Eis_quer_Goeran_Gnaudschun-1024x709-1.jpg",
        "default_start_time": "18:00",
    },
    {
        "title": "CLOVER - Irish Folk Party",
        "description": "Die Folk Formation CLOVER aus Berlin. Immer wieder ausverkauft, immer wieder bombige Stimmung! CLOVER ist eine Berliner Live-Band und spielt seit 1996 irischen & schottischen Folk.",
        "dates": ["2026-05-13"],
        "price": 29.00,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2023/04/CLOVER_Trio.jpg",
        "default_start_time": "18:00",
    },
]

AKTIONEN = [
    {
        "title": "Valentinsabend",
        "description": "6-Gang-Valentinsmenü bei Kerzenschein. Fein, frisch, fokussiert auf Geschmack. Begrüßungscocktail, Pastinakensuppe, Avocado-Mango-Tatar, Schokoladenkuchen mit Vanilleeis. Beim Hauptgang haben Sie die Wahl – vegetarisch, mit Fleisch oder Fisch.",
        "dates": ["2026-02-14"],
        "price": 59.90,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2025/12/Valentinstag-Event-an-der-Carlsburg.png",
        "default_start_time": "17:00",
        "requires_menu_choice": True,
        "menu_options": [
            {"title": "Mit Fleisch", "description": "Hauptgang Fleisch", "price_delta": 0},
            {"title": "Mit Fisch", "description": "Hauptgang Fisch", "price_delta": 0},
            {"title": "Vegetarisch", "description": "Vegetarische Variante", "price_delta": -10.00},
        ],
        "content_category": "AKTION_MENUE",
    },
    {
        "title": "Spareribs Sattessen",
        "description": "Spareribs-Sattessen nach amerikanischer Art. Saftige Schweinerippchen mit Kartoffel Wedges und Cole Slaw, sowie würzige hausgemachte Barbecue-Sauce oder wahlweise einem milden Knoblauch-Dip. Schlemmen Sie so viel Sie mögen.",
        "dates": [
            "2026-01-09", "2026-02-06", "2026-03-11", "2026-03-12", "2026-03-18", "2026-03-19",
            "2026-03-25", "2026-03-26", "2026-04-01", "2026-04-02", "2026-04-08", "2026-04-09",
            "2026-04-15", "2026-04-16", "2026-04-22", "2026-04-23", "2026-04-29", "2026-04-30",
        ],
        "price": 25.90,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2022/01/carlsburg-spareribs-1800.jpg",
        "default_start_time": "17:00",
        "requires_menu_choice": False,
        "content_category": "AKTION",
    },
    {
        "title": "Großgarnelen Sattessen",
        "description": "Riesengarnelen essen, soviel Sie mögen! Wahlweise mit Aioli und unserem Asia Dip (natürlich alle hausgemacht!). Wählen Sie Ihre Lieblingssauce und schlemmen Sie nach Herzenslust.",
        "dates": [
            "2026-01-16", "2026-02-13", "2026-05-06", "2026-05-07", "2026-05-13",
            "2026-05-20", "2026-05-21", "2026-05-27", "2026-05-28",
        ],
        "price": 35.90,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2022/01/carlsburg-grossgarnelen-1800.jpg",
        "default_start_time": "17:00",
        "requires_menu_choice": False,
        "content_category": "AKTION",
    },
    {
        "title": "Schnitzel Sattessen",
        "description": "Zwei verschiedene Schnitzel-Varianten – so viel Sie mögen: Klassisches Schweineschnitzel nach Wiener Art und Hähnchenschnitzel aus der Keule in Panko-Chili-Panade. Dazu Barbecue-Lecho-Sauce oder Jägersauce.",
        "dates": [
            "2026-01-30", "2026-06-03", "2026-06-17", "2026-07-01", "2026-07-15",
            "2026-07-29", "2026-08-05", "2026-08-19",
        ],
        "price": 29.90,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2025/03/schnitzel-satt-3.jpg",
        "default_start_time": "17:00",
        "requires_menu_choice": False,
        "content_category": "AKTION",
    },
    {
        "title": "Mediterraner Tapas-Abend",
        "description": "Mediterranes Geschmacksparadies: Brotkorb, Dipvariationen, Serranoschinken, Manchego, Chorizo, Pimientos de Padrón, Hackbällchen, Datteln im Speckmantel, Scampis in Knoblauchbutter, Guacamole, Sardellen.",
        "dates": [
            "2026-01-23", "2026-02-20", "2026-06-05", "2026-06-19", "2026-07-03",
            "2026-07-17", "2026-07-31", "2026-08-21", "2026-09-04", "2026-09-25",
        ],
        "price": 0,  # À la carte pricing
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2025/03/tapas-1-2.jpg",
        "default_start_time": "17:00",
        "requires_menu_choice": False,
        "content_category": "AKTION",
        "notes": "Einzelne Tapas ab 3,00 Euro bis 9,00 Euro",
    },
    {
        "title": "Carlsburger Terrassen BBQ",
        "description": "Die feinsten Leckereien vom Grill auf unserer Terrasse: Lachs in Folie, Argentinisches Entrecôte, Lamm-Spieße mit wunderbarem Ausblick über das gesamte Oderbruch.",
        "dates": ["2026-07-24", "2026-07-25", "2026-08-07", "2026-08-08"],
        "price": 0,  # Variable pricing
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2022/01/carlsburg-bbg-1800.jpg",
        "default_start_time": "17:00",
        "requires_menu_choice": False,
        "content_category": "AKTION",
    },
    {
        "title": "Ente Sattessen",
        "description": "Carlsburger Ente Sattessen - Jeder kann vom Federvieh samt Rot- und Grünkohl sowie Kartoffelklößen, so viel essen wie er will.",
        "dates": [
            "2026-10-04", "2026-10-11", "2026-10-18", "2026-10-25",
            "2026-11-01", "2026-11-22", "2026-11-29",
            "2026-12-06", "2026-12-13", "2026-12-20", "2026-12-27",
        ],
        "price": 34.90,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2022/01/carlsburg-entenschmaus-1800.jpg",
        "default_start_time": "17:00",
        "requires_menu_choice": False,
        "content_category": "AKTION",
    },
    {
        "title": "Martinsgans Essen",
        "description": "Das große Carlsburger Martinsgansessen - 3-Gänge-Menü mit Bouillon vom Gänseklein, knusprigem Gänsebraten mit zweierlei Kohl und Kartoffelklößen, und hausgemachtem Wintereis.",
        "dates": ["2026-11-07", "2026-11-08", "2026-11-14", "2026-11-15", "2026-11-21", "2026-11-22"],
        "price": 49.90,
        "image_url": "https://www.carlsburg.de/wp-content/uploads/2022/01/carlsburg-martinsgans-1400.jpg",
        "default_start_time": "17:00",
        "requires_menu_choice": True,
        "menu_options": [
            {"title": "3-Gänge Menü", "description": "Suppe, Gänsebraten, Dessert", "price_delta": 0},
            {"title": "Nur Gänsebraten", "description": "Ohne Suppe und Dessert", "price_delta": -15.00},
        ],
        "content_category": "AKTION_MENUE",
    },
]

async def import_events(dry_run=True):
    """Import events and aktionen from website data"""
    results = {
        "veranstaltungen": {"would_create": [], "would_update": [], "created": 0, "updated": 0},
        "aktionen": {"would_create": [], "would_update": [], "created": 0, "updated": 0},
        "errors": []
    }
    
    # Import Veranstaltungen
    for v in VERANSTALTUNGEN:
        existing = await db.events.find_one({
            "title": v["title"],
            "source": "carlsburg_web",
            "archived": {"$ne": True}
        })
        
        event_data = {
            "title": v["title"],
            "description": v["description"],
            "image_url": v.get("image_url"),
            "price_per_person": v.get("price"),
            "content_category": "VERANSTALTUNG",
            "booking_mode": "ticket",
            "default_start_time": v.get("default_start_time", "18:00"),
            "requires_menu_choice": False,
            "requires_payment": True,
            "source": "carlsburg_web",
            "source_url": f"https://www.carlsburg.de/veranstaltungen/",
            "status": "published",
            "is_public": True,
            "event_type": "show",
            "updated_at": now_iso(),
        }
        
        # Set first date
        if v.get("dates") and len(v["dates"]) > 0:
            event_data["date"] = v["dates"][0]
            event_data["all_dates"] = v["dates"]
        
        if existing:
            results["veranstaltungen"]["would_update"].append({
                "id": existing["id"],
                "title": v["title"],
                "dates": v.get("dates", [])
            })
            if not dry_run:
                await db.events.update_one({"id": existing["id"]}, {"$set": event_data})
                results["veranstaltungen"]["updated"] += 1
        else:
            event_data["id"] = str(uuid.uuid4())
            event_data["created_at"] = now_iso()
            event_data["archived"] = False
            event_data["capacity"] = 60
            event_data["available_capacity"] = 60
            
            results["veranstaltungen"]["would_create"].append({
                "title": v["title"],
                "price": v.get("price"),
                "dates": v.get("dates", [])
            })
            if not dry_run:
                await db.events.insert_one(event_data)
                results["veranstaltungen"]["created"] += 1
    
    # Import Aktionen
    for a in AKTIONEN:
        existing = await db.events.find_one({
            "title": a["title"],
            "source": "carlsburg_web",
            "archived": {"$ne": True}
        })
        
        event_data = {
            "title": a["title"],
            "description": a["description"],
            "image_url": a.get("image_url"),
            "price_per_person": a.get("price") if a.get("price") else None,
            "content_category": a.get("content_category", "AKTION"),
            "booking_mode": "reservation_with_menu_choice" if a.get("requires_menu_choice") else "reservation",
            "default_start_time": a.get("default_start_time", "17:00"),
            "requires_menu_choice": a.get("requires_menu_choice", False),
            "requires_payment": False,
            "source": "carlsburg_web",
            "source_url": f"https://www.carlsburg.de/aktionen/",
            "status": "published",
            "is_public": True,
            "event_type": "dinner",
            "updated_at": now_iso(),
        }
        
        # Add menu options
        if a.get("menu_options"):
            event_data["menu_options"] = [
                {"option_id": str(uuid.uuid4()), **opt}
                for opt in a["menu_options"]
            ]
        
        # Set dates
        if a.get("dates"):
            event_data["all_dates"] = a["dates"]
            event_data["date"] = a["dates"][0] if a["dates"] else None
        
        if existing:
            results["aktionen"]["would_update"].append({
                "id": existing["id"],
                "title": a["title"],
                "dates_count": len(a.get("dates", []))
            })
            if not dry_run:
                await db.events.update_one({"id": existing["id"]}, {"$set": event_data})
                results["aktionen"]["updated"] += 1
        else:
            event_data["id"] = str(uuid.uuid4())
            event_data["created_at"] = now_iso()
            event_data["archived"] = False
            event_data["capacity"] = None  # Needs manual configuration
            event_data["available_capacity"] = None
            event_data["needs_capacity_config"] = True
            
            results["aktionen"]["would_create"].append({
                "title": a["title"],
                "price": a.get("price"),
                "dates_count": len(a.get("dates", [])),
                "requires_menu_choice": a.get("requires_menu_choice", False)
            })
            if not dry_run:
                await db.events.insert_one(event_data)
                results["aktionen"]["created"] += 1
    
    return results


async def main():
    print("=" * 60)
    print("GASTROCORE DATA IMPORT")
    print("=" * 60)
    
    # =====================================
    # TEIL A: MITARBEITER-IMPORT (DRY-RUN)
    # =====================================
    print("\n📋 TEIL A: MITARBEITER-IMPORT (DRY-RUN)")
    print("-" * 40)
    
    staff_results = await import_staff(dry_run=True)
    
    print(f"\n✅ Würde anlegen: {len(staff_results['would_create'])}")
    for s in staff_results['would_create'][:5]:
        print(f"   - {s['name']} ({s['email']})")
    
    print(f"\n🔄 Würde aktualisieren: {len(staff_results['would_update'])}")
    for s in staff_results['would_update'][:3]:
        print(f"   - {s['name']} (Felder: {', '.join(s.get('fields', [])[:3])})")
    
    print(f"\n⏭️  Würde überspringen: {len(staff_results['would_skip'])}")
    
    # =====================================
    # TEIL B: EVENTS-IMPORT (DRY-RUN)
    # =====================================
    print("\n\n🎭 TEIL B: EVENTS & AKTIONEN-IMPORT (DRY-RUN)")
    print("-" * 40)
    
    events_results = await import_events(dry_run=True)
    
    print(f"\n🎤 VERANSTALTUNGEN:")
    print(f"   Würde anlegen: {len(events_results['veranstaltungen']['would_create'])}")
    for e in events_results['veranstaltungen']['would_create'][:3]:
        print(f"   - {e['title']} ({e['price']}€, Termine: {len(e.get('dates', []))})")
    print(f"   Würde aktualisieren: {len(events_results['veranstaltungen']['would_update'])}")
    
    print(f"\n🍽️  AKTIONEN:")
    print(f"   Würde anlegen: {len(events_results['aktionen']['would_create'])}")
    for a in events_results['aktionen']['would_create'][:3]:
        menu = "🍴 Menüwahl" if a.get('requires_menu_choice') else ""
        print(f"   - {a['title']} ({a['price'] or 'variabel'}€, {a.get('dates_count', 0)} Termine) {menu}")
    print(f"   Würde aktualisieren: {len(events_results['aktionen']['would_update'])}")
    
    # =====================================
    # APPLY IMPORTS
    # =====================================
    print("\n\n" + "=" * 60)
    print("🚀 IMPORT AUSFÜHREN")
    print("=" * 60)
    
    # Staff Import
    print("\n📋 Mitarbeiter importieren...")
    staff_results = await import_staff(dry_run=False)
    print(f"   ✅ Erstellt: {staff_results['created']}")
    print(f"   🔄 Aktualisiert: {staff_results['updated']}")
    print(f"   ⏭️  Übersprungen: {staff_results['skipped']}")
    
    # Events Import
    print("\n🎭 Events & Aktionen importieren...")
    events_results = await import_events(dry_run=False)
    print(f"   Veranstaltungen - Erstellt: {events_results['veranstaltungen']['created']}, Aktualisiert: {events_results['veranstaltungen']['updated']}")
    print(f"   Aktionen - Erstellt: {events_results['aktionen']['created']}, Aktualisiert: {events_results['aktionen']['updated']}")
    
    # =====================================
    # SUMMARY
    # =====================================
    print("\n\n" + "=" * 60)
    print("📊 ZUSAMMENFASSUNG")
    print("=" * 60)
    
    # Count totals in DB
    staff_count = await db.staff_members.count_documents({"archived": {"$ne": True}})
    events_count = await db.events.count_documents({"archived": {"$ne": True}})
    
    print(f"\n📋 Mitarbeiter in DB: {staff_count}")
    print(f"🎭 Events/Aktionen in DB: {events_count}")
    
    # Items needing review
    needs_capacity = await db.events.count_documents({"needs_capacity_config": True, "archived": {"$ne": True}})
    menu_events = await db.events.count_documents({"requires_menu_choice": True, "archived": {"$ne": True}})
    
    print(f"\n⚠️  Aktionen ohne Kapazität (muss manuell gepflegt): {needs_capacity}")
    print(f"🍴 Aktionen mit Menüauswahl: {menu_events}")
    
    print("\n✅ IMPORT ABGESCHLOSSEN")


if __name__ == "__main__":
    asyncio.run(main())
