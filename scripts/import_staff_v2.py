#!/usr/bin/env python3
"""
============================================================
CARLSBURG COCKPIT - STAFF IMPORT V2
Clean Rebuild - Deterministic Source-of-Truth Import
============================================================

INPUT:  /app/import/staff.xlsx
OUTPUT: /app/seed/staff_members_master.json
TARGET: gastrocore_v2.staff_members

Features:
- Deterministische UUID5-basierte IDs
- Stabiler Row-Hash für Change-Detection
- Upsert-Logik (kein Duplikat)
- Vollständige Feldtransformation
"""

import os
import sys
import json
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import pandas as pd
from dotenv import load_dotenv

# Load environment from backend .env
load_dotenv('/app/backend/.env')

# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = "/app/import/staff.xlsx"
OUTPUT_JSON = "/app/seed/staff_members_master.json"
NAMESPACE_UUID = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace

# Department Mapping
DEPARTMENT_MAP = {
    "service": "service",
    "küche": "kitchen",
    "kueche": "kitchen",
    "kitchen": "kitchen",
    "reinigung": "reinigung",
    "bar": "bar",
    "eismacher": "eismacher",
    "kuechenhilfe": "kuechenhilfe",
}

# Employment Type Mapping
EMPLOYMENT_TYPE_MAP = {
    "vz": "vollzeit",
    "vollzeit": "vollzeit",
    "tz": "teilzeit",
    "teilzeit": "teilzeit",
    "minijob": "minijob",
    "selbstständig": "selbststaendig",
    "selbständig": "selbststaendig",
    "selbststaendig": "selbststaendig",
    "freelance": "selbststaendig",
    "aushilfe": "aushilfe",
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def generate_deterministic_id(email: str = None, personnel_number: str = None, 
                               first_name: str = None, last_name: str = None, 
                               row_index: int = None) -> str:
    """
    Erzeugt deterministische UUID5-basierte ID.
    Priorität: email > personnel_number > name:row_index
    """
    if email and pd.notna(email):
        seed = f"email:{str(email).lower().strip()}"
    elif personnel_number and pd.notna(personnel_number):
        seed = f"personnel:{str(personnel_number).strip()}"
    else:
        fn = str(first_name or "").strip()
        ln = str(last_name or "").strip()
        seed = f"name:{fn}:{ln}:{row_index}"
    
    return str(uuid.uuid5(NAMESPACE_UUID, seed))


def generate_row_hash(row: pd.Series) -> str:
    """
    Erzeugt stabilen Hash für Change-Detection.
    """
    # Relevante Felder für Hash
    hash_fields = ['Nachname', 'Vorname', 'email', 'personal_number', 'phone', 
                   'Position', 'emplyment_type', 'Wochenstunden']
    
    hash_data = []
    for field in hash_fields:
        val = row.get(field, "")
        if pd.notna(val):
            hash_data.append(f"{field}:{val}")
    
    hash_str = "|".join(sorted(hash_data))
    return hashlib.sha256(hash_str.encode()).hexdigest()[:16]


def parse_date(date_val) -> Optional[str]:
    """
    Parst verschiedene Datumsformate zu ISO YYYY-MM-DD.
    """
    if pd.isna(date_val):
        return None
    
    date_str = str(date_val).strip()
    
    # Bereits datetime
    if isinstance(date_val, datetime):
        return date_val.strftime("%Y-%m-%d")
    
    # Pandas Timestamp
    if hasattr(date_val, 'strftime'):
        return date_val.strftime("%Y-%m-%d")
    
    # String-Formate probieren
    formats = [
        "%Y-%m-%d",           # 2025-12-01
        "%Y-%m-%d %H:%M:%S",  # 2025-12-01 00:00:00
        "%d.%m.%Y",           # 01.12.2025
        "%d/%m/%Y",           # 01/12/2025
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.split()[0], fmt.split()[0])
            return dt.strftime("%Y-%m-%d")
        except:
            continue
    
    return None


def normalize_phone(phone_val) -> Optional[str]:
    """
    Normalisiert Telefonnummer.
    """
    if pd.isna(phone_val):
        return None
    
    phone_str = str(phone_val).strip()
    
    # Entferne alles außer Zahlen und +
    cleaned = ''.join(c for c in phone_str if c.isdigit() or c == '+')
    
    if not cleaned:
        return None
    
    # Füge Ländervorwahl hinzu wenn nötig
    if cleaned.startswith("48") and len(cleaned) >= 11:
        # Polnische Nummer
        return f"+{cleaned}"
    elif cleaned.startswith("49") or cleaned.startswith("0049"):
        # Deutsche Nummer mit Vorwahl
        return f"+{cleaned.replace('0049', '49')}"
    elif cleaned.startswith("0"):
        # Deutsche Nummer ohne Ländervorwahl
        return f"+49{cleaned[1:]}"
    elif len(cleaned) >= 10:
        # Annahme: Deutsche Nummer
        return f"+49{cleaned}"
    
    return cleaned


def map_department(dept_val: str) -> str:
    """
    Mappt Department auf kanonischen Wert.
    """
    if pd.isna(dept_val):
        return "service"  # Default
    
    dept_lower = str(dept_val).lower().strip()
    
    return DEPARTMENT_MAP.get(dept_lower, "service")


def map_employment_type(emp_val: str) -> str:
    """
    Mappt Employment Type auf kanonischen Wert.
    """
    if pd.isna(emp_val):
        return "vollzeit"  # Default
    
    emp_lower = str(emp_val).lower().strip()
    
    return EMPLOYMENT_TYPE_MAP.get(emp_lower, "vollzeit")


def safe_float(val, default: float = 0.0) -> float:
    """Sichere Float-Konvertierung."""
    if pd.isna(val):
        return default
    try:
        return float(val)
    except:
        return default


def safe_int(val, default: int = 0) -> int:
    """Sichere Int-Konvertierung."""
    if pd.isna(val):
        return default
    try:
        return int(float(val))
    except:
        return default


def safe_str(val, default: str = "") -> str:
    """Sichere String-Konvertierung."""
    if pd.isna(val):
        return default
    return str(val).strip()


# ============================================================
# MAIN TRANSFORM
# ============================================================

def transform_row(row: pd.Series, row_index: int) -> Dict[str, Any]:
    """
    Transformiert eine Excel-Zeile in ein Staff-Member-Dokument.
    """
    # Basis-Felder extrahieren
    first_name = safe_str(row.get('Vorname'))
    last_name = safe_str(row.get('Nachname'))
    rufname = safe_str(row.get('Rufname'))
    email = safe_str(row.get('email')).lower() if pd.notna(row.get('email')) else None
    personnel_number = safe_str(row.get('personal_number'))
    
    # Deterministische ID
    staff_id = generate_deterministic_id(
        email=email,
        personnel_number=personnel_number,
        first_name=first_name,
        last_name=last_name,
        row_index=row_index
    )
    
    # Display Name: Rufname wenn vorhanden, sonst Vorname
    display_name = rufname if rufname else first_name
    
    # Adresse
    address = None
    street = safe_str(row.get('street'))
    city = safe_str(row.get('city'))
    zip_code = safe_str(row.get('zip_code'))
    
    if street or city or zip_code:
        address = {
            "street": street or None,
            "zip_code": zip_code or None,
            "city": city or None
        }
    
    # Department aus employment_fraction oder Position ableiten
    dept_source = row.get('employment_fraction') or row.get('Position') or 'service'
    department = map_department(dept_source)
    
    # Position
    position = safe_str(row.get('primary_position')) or safe_str(row.get('Position'))
    secondary_position = safe_str(row.get('secondary_position')) or None
    
    # Employment Type
    employment_type = map_employment_type(row.get('emplyment_type'))
    
    # Weekly Hours
    weekly_hours = safe_float(row.get('Wochenstunden'), 0.0)
    
    # Time PIN
    time_pin = safe_str(row.get('time_pin')) or None
    
    # Phones
    phone = normalize_phone(row.get('phone'))
    phone_secondary = normalize_phone(row.get('Telefon 2'))
    
    # Birthday
    birthday = parse_date(row.get('date_of_birth /YYYY-MM-DD'))
    
    # Notes/Besonderheiten
    notes = safe_str(row.get('Besonderheiten')) or None
    
    # Start Date
    start_date = parse_date(row.get('Startdatum'))
    
    # Row Hash für Change-Detection
    row_hash = generate_row_hash(row)
    
    # Dokument zusammenbauen
    doc = {
        "id": staff_id,
        "first_name": first_name,
        "last_name": last_name,
        "display_name": display_name,
        "email": email,
        "phone": phone,
        "phone_secondary": phone_secondary,
        "birthday": birthday,
        "personnel_number": personnel_number if personnel_number else None,
        "time_pin": time_pin,
        "address": address,
        "employment_type": employment_type,
        "weekly_hours": weekly_hours,
        "department": department,
        "position": position,
        "secondary_position": secondary_position,
        "start_date": start_date,
        "notes": notes,
        "status": "aktiv",
        "active": True,
        "archived": False,
        "external_source": "excel_import",
        "external_row_hash": row_hash
    }
    
    # None-Werte entfernen für sauberes JSON
    doc = {k: v for k, v in doc.items() if v is not None}
    
    return doc


def build_staff_json():
    """
    Liest Excel, transformiert alle Zeilen, schreibt JSON.
    """
    print("=" * 60)
    print("STAFF IMPORT V2 - JSON BUILD")
    print("=" * 60)
    
    # Excel einlesen
    print(f"\n📥 Lese {INPUT_FILE}...")
    df = pd.read_excel(INPUT_FILE)
    print(f"   ✅ {len(df)} Zeilen gelesen")
    
    # Transformieren
    print(f"\n🔧 Transformiere Daten...")
    staff_members = []
    
    for idx, row in df.iterrows():
        doc = transform_row(row, idx)
        staff_members.append(doc)
    
    print(f"   ✅ {len(staff_members)} Mitarbeiter transformiert")
    
    # Sortieren für Determinismus (nach ID)
    staff_members.sort(key=lambda x: x.get("id", ""))
    
    # JSON schreiben
    print(f"\n💾 Schreibe {OUTPUT_JSON}...")
    
    output_doc = {
        "_meta": {
            "version": "2.0.0",
            "description": "Carlsburg Staff Members Master V2 - Source of Truth",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_file": INPUT_FILE,
            "source_rows": len(df),
            "target_db": "gastrocore_v2",
            "count": len(staff_members)
        },
        "data": staff_members
    }
    
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output_doc, f, indent=2, ensure_ascii=False)
    
    file_size = os.path.getsize(OUTPUT_JSON)
    print(f"   ✅ {len(staff_members)} Einträge, {file_size} Bytes")
    
    return staff_members, len(df)


async def import_to_mongodb(staff_members: List[Dict]) -> int:
    """
    Importiert Staff Members in MongoDB V2 via Upsert.
    """
    from motor.motor_asyncio import AsyncIOMotorClient
    
    mongo_url = os.environ.get("MONGO_URL")
    if not mongo_url:
        print("❌ MONGO_URL nicht gesetzt!")
        return 0
    
    # DB-Namen aus URL extrahieren oder verwenden
    db_name = os.environ.get("DB_NAME", "gastrocore_v2")
    
    print(f"\n🔄 Verbinde mit MongoDB ({db_name})...")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    collection = db.staff_members
    
    # Upsert für jeden Mitarbeiter
    imported = 0
    updated = 0
    
    for member in staff_members:
        staff_id = member.get("id")
        email = member.get("email")
        personnel_number = member.get("personnel_number")
        
        # Upsert-Filter: Primär ID, sekundär email oder personnel_number
        filter_query = {"id": staff_id}
        
        # Update mit $set
        update_doc = {"$set": member}
        
        result = await collection.update_one(
            filter_query,
            update_doc,
            upsert=True
        )
        
        if result.upserted_id:
            imported += 1
        elif result.modified_count > 0:
            updated += 1
    
    # Index auf id erstellen
    await collection.create_index("id", unique=True)
    await collection.create_index("email", sparse=True)
    await collection.create_index("personnel_number", sparse=True)
    
    total_in_db = await collection.count_documents({})
    
    client.close()
    
    print(f"   ✅ Neu: {imported}, Aktualisiert: {updated}")
    print(f"   📊 Gesamt in DB: {total_in_db}")
    
    return total_in_db


def print_samples(staff_members: List[Dict]):
    """
    Gibt 2 Stichproben aus (ohne sensible Daten).
    """
    print("\n📋 STICHPROBEN (2 Mitarbeiter):")
    
    for i, member in enumerate(staff_members[:2]):
        print(f"\n   Mitarbeiter {i+1}:")
        print(f"   - Name: {member.get('first_name')} {member.get('last_name')}")
        print(f"   - Personnel #: {member.get('personnel_number', 'N/A')}")
        print(f"   - Department: {member.get('department')}")
        print(f"   - Position: {member.get('position')}")
        print(f"   - Employment: {member.get('employment_type')}")
        print(f"   - ID: {member.get('id')[:8]}...")


# ============================================================
# MAIN
# ============================================================

def main():
    import asyncio
    
    print("\n" + "=" * 60)
    print("CARLSBURG COCKPIT - STAFF IMPORT V2")
    print("=" * 60)
    
    # 1. JSON bauen
    staff_members, excel_rows = build_staff_json()
    
    # 2. Stichproben anzeigen
    print_samples(staff_members)
    
    # 3. MongoDB Import
    print("\n" + "=" * 60)
    print("MONGODB IMPORT")
    print("=" * 60)
    
    db_count = asyncio.run(import_to_mongodb(staff_members))
    
    # 4. Zusammenfassung
    print("\n" + "=" * 60)
    print("VERIFIKATION")
    print("=" * 60)
    print(f"\n📊 ERGEBNIS:")
    print(f"   Excel-Zeilen:     {excel_rows}")
    print(f"   JSON-Einträge:    {len(staff_members)}")
    print(f"   DB-Dokumente:     {db_count}")
    
    if excel_rows == len(staff_members) == db_count:
        print(f"\n   ✅ KONSISTENT: Alle {excel_rows} Mitarbeiter importiert")
    else:
        print(f"\n   ⚠️  INKONSISTENT: Bitte prüfen!")
    
    print("\n" + "=" * 60)
    print("✅ STAFF IMPORT V2 ABGESCHLOSSEN")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
