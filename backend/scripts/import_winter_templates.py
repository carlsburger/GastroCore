#!/usr/bin/env python3
"""
Shift Templates Winter Import Script
=====================================
Upsert by code - keine Duplikate

Usage: python import_winter_templates.py
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import os

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "gastrocore")

# Winter Templates Data
WINTER_TEMPLATES = [
    {
        "code": "SERVICE_WINTER_1100_1700",
        "name": "Service Winter 11:00-17:00",
        "role": "service",
        "station": "Restaurant",
        "start_time_local": "11:00",
        "end_time_local": "17:00",
        "event_mode": False,
        "active": True
    },
    {
        "code": "SERVICE_WINTER_1100_1800",
        "name": "Service Winter 11:00-18:00",
        "role": "service",
        "station": "Restaurant",
        "start_time_local": "11:00",
        "end_time_local": "18:00",
        "event_mode": False,
        "active": True
    },
    {
        "code": "SERVICE_WINTER_1130_1700",
        "name": "Service Winter 11:30-17:00",
        "role": "service",
        "station": "Restaurant",
        "start_time_local": "11:30",
        "end_time_local": "17:00",
        "event_mode": False,
        "active": True
    },
    {
        "code": "SERVICE_WINTER_1200_1800",
        "name": "Service Winter 12:00-18:00",
        "role": "service",
        "station": "Restaurant",
        "start_time_local": "12:00",
        "end_time_local": "18:00",
        "event_mode": False,
        "active": True
    },
    {
        "code": "SERVICE_WINTER_1200_2000",
        "name": "Service Winter 12:00-20:00",
        "role": "service",
        "station": "Restaurant",
        "start_time_local": "12:00",
        "end_time_local": "20:00",
        "event_mode": False,
        "active": True
    },
    {
        "code": "SERVICE_WINTER_1300_1800",
        "name": "Service Winter 13:00-18:00",
        "role": "service",
        "station": "Restaurant",
        "start_time_local": "13:00",
        "end_time_local": "18:00",
        "event_mode": False,
        "active": True
    },
    {
        "code": "SERVICE_WINTER_1300_2000",
        "name": "Service Winter 13:00-20:00",
        "role": "service",
        "station": "Restaurant",
        "start_time_local": "13:00",
        "end_time_local": "20:00",
        "event_mode": False,
        "active": True
    },
    {
        "code": "SERVICE_WINTER_1400_2000",
        "name": "Service Winter 14:00-20:00",
        "role": "service",
        "station": "Restaurant",
        "start_time_local": "14:00",
        "end_time_local": "20:00",
        "event_mode": False,
        "active": True
    },
    {
        "code": "KITCHEN_WINTER_0900_1700",
        "name": "Küche Winter 09:00-17:00",
        "role": "kitchen",
        "station": "Küche",
        "start_time_local": "09:00",
        "end_time_local": "17:00",
        "event_mode": False,
        "active": True
    },
    {
        "code": "KITCHEN_WINTER_0900_1800",
        "name": "Küche Winter 09:00-18:00",
        "role": "kitchen",
        "station": "Küche",
        "start_time_local": "09:00",
        "end_time_local": "18:00",
        "event_mode": False,
        "active": True
    },
    {
        "code": "KITCHEN_WINTER_1000_1900",
        "name": "Küche Winter 10:00-19:00",
        "role": "kitchen",
        "station": "Küche",
        "start_time_local": "10:00",
        "end_time_local": "19:00",
        "event_mode": False,
        "active": True
    },
    {
        "code": "KITCHEN_WINTER_1100_1800",
        "name": "Küche Winter 11:00-18:00",
        "role": "kitchen",
        "station": "Küche",
        "start_time_local": "11:00",
        "end_time_local": "18:00",
        "event_mode": False,
        "active": True
    },
    {
        "code": "KITCHEN_WINTER_1100_1900",
        "name": "Küche Winter 11:00-19:00",
        "role": "kitchen",
        "station": "Küche",
        "start_time_local": "11:00",
        "end_time_local": "19:00",
        "event_mode": False,
        "active": True
    },
    {
        "code": "KITCHEN_WINTER_1200_1800",
        "name": "Küche Winter 12:00-18:00",
        "role": "kitchen",
        "station": "Küche",
        "start_time_local": "12:00",
        "end_time_local": "18:00",
        "event_mode": False,
        "active": True
    },
    {
        "code": "KITCHEN_WINTER_1200_2000",
        "name": "Küche Winter 12:00-20:00",
        "role": "kitchen",
        "station": "Küche",
        "start_time_local": "12:00",
        "end_time_local": "20:00",
        "event_mode": False,
        "active": True
    },
    {
        "code": "KITCHEN_WINTER_1400_2000",
        "name": "Küche Winter 14:00-20:00",
        "role": "kitchen",
        "station": "Küche",
        "start_time_local": "14:00",
        "end_time_local": "20:00",
        "event_mode": False,
        "active": True
    },
    {
        "code": "KITCHEN_HELP_WINTER_1100_1300",
        "name": "Küchenhilfe Winter 11:00-13:00",
        "role": "kitchen_help",
        "station": "Küche",
        "start_time_local": "11:00",
        "end_time_local": "13:00",
        "event_mode": False,
        "active": True
    },
    {
        "code": "KITCHEN_HELP_WINTER_1100_1600",
        "name": "Küchenhilfe Winter 11:00-16:00",
        "role": "kitchen_help",
        "station": "Küche",
        "start_time_local": "11:00",
        "end_time_local": "16:00",
        "event_mode": False,
        "active": True
    },
    {
        "code": "CLEANING_WINTER_0900_1100",
        "name": "Reinigung Winter 09:00-11:00",
        "role": "cleaning",
        "station": "Reinigung",
        "start_time_local": "09:00",
        "end_time_local": "11:00",
        "event_mode": False,
        "active": True
    },
    {
        "code": "ICE_MAKER_WINTER_0900_1600",
        "name": "Eismacher Winter 09:00-16:00",
        "role": "ice_maker",
        "station": "Eis",
        "start_time_local": "09:00",
        "end_time_local": "16:00",
        "event_mode": False,
        "active": True
    }
]


async def import_templates():
    """Import Winter Templates via Upsert by code"""
    
    print("=" * 60)
    print("SHIFT TEMPLATES WINTER IMPORT")
    print("=" * 60)
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    collection = db.shift_templates
    
    print(f"\nConnected to: {DB_NAME}")
    
    # 1. IST-CHECK
    existing_count = await collection.count_documents({})
    existing_codes = await collection.distinct("code")
    existing_codes = [c for c in existing_codes if c is not None]
    
    print(f"\n--- IST-STAND ---")
    print(f"Dokumente gesamt: {existing_count}")
    print(f"Dokumente mit code: {len(existing_codes)}")
    print(f"Existierende Codes: {existing_codes}")
    
    # 2. Import Codes aus JSON
    import_codes = [t["code"] for t in WINTER_TEMPLATES]
    new_codes = [c for c in import_codes if c not in existing_codes]
    update_codes = [c for c in import_codes if c in existing_codes]
    
    print(f"\n--- IMPORT-PLAN ---")
    print(f"Templates im JSON: {len(WINTER_TEMPLATES)}")
    print(f"Neue Codes (INSERT): {len(new_codes)}")
    print(f"Bestehende Codes (UPDATE): {len(update_codes)}")
    
    # 3. UPSERT
    print(f"\n--- UPSERT AUSFÜHRUNG ---")
    
    inserted = 0
    modified = 0
    upserted = 0
    
    now = datetime.now(timezone.utc).isoformat()
    
    for template in WINTER_TEMPLATES:
        code = template["code"]
        
        # Prepare document
        doc = {
            "name": template["name"],
            "code": template["code"],
            "role": template["role"],
            "station": template["station"],
            "start_time": template["start_time_local"],  # Map to existing field
            "end_time": template["end_time_local"],      # Map to existing field
            "start_time_local": template["start_time_local"],
            "end_time_local": template["end_time_local"],
            "event_mode": template.get("event_mode", False),
            "active": template.get("active", True),
            "updated_at": now
        }
        
        # Upsert by code
        result = await collection.update_one(
            {"code": code},
            {
                "$set": doc,
                "$setOnInsert": {
                    "id": str(uuid.uuid4()),
                    "created_at": now
                }
            },
            upsert=True
        )
        
        if result.upserted_id:
            upserted += 1
            print(f"  ➕ INSERT: {code}")
        elif result.modified_count > 0:
            modified += 1
            print(f"  🔄 UPDATE: {code}")
        else:
            print(f"  ⏸️ UNCHANGED: {code}")
    
    # 4. Ergebnis
    print(f"\n--- ERGEBNIS ---")
    print(f"✅ Inserted (neue): {upserted}")
    print(f"🔄 Modified (updates): {modified}")
    print(f"📊 Gesamt verarbeitet: {len(WINTER_TEMPLATES)}")
    
    # 5. Verifizierung
    final_count = await collection.count_documents({})
    final_codes = await collection.distinct("code")
    final_codes = [c for c in final_codes if c is not None]
    
    print(f"\n--- NACH IMPORT ---")
    print(f"Dokumente gesamt: {final_count}")
    print(f"Dokumente mit code: {len(final_codes)}")
    
    # Check if all winter codes are present
    winter_codes_present = all(c in final_codes for c in import_codes)
    print(f"\n✅ Alle Winter-Codes vorhanden: {winter_codes_present}")
    
    client.close()
    print("\n" + "=" * 60)
    print("IMPORT ABGESCHLOSSEN")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(import_templates())
