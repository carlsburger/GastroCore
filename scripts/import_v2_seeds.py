#!/usr/bin/env python3
"""
============================================================
CARLSBURG COCKPIT - V2 SEEDS IMPORT (IDEMPOTENT)
============================================================

Lädt work_areas_master.json und shift_templates_master.json
und schreibt sie idempotent in MongoDB gastrocore_v2.

KEINE Secrets loggen. KEINE ENV Values ausgeben.
NUR Counts: inserted/updated.
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment
load_dotenv('/app/backend/.env')

# ============================================================
# CONFIGURATION
# ============================================================

SEED_DIR = "/app/seed"
WORK_AREAS_FILE = f"{SEED_DIR}/work_areas_master.json"
SHIFT_TEMPLATES_FILE = f"{SEED_DIR}/shift_templates_master.json"

# ============================================================
# IMPORT FUNCTIONS
# ============================================================

async def import_work_areas(db) -> dict:
    """
    Importiert work_areas idempotent (upsert by id).
    """
    if not os.path.exists(WORK_AREAS_FILE):
        return {"error": f"Datei nicht gefunden: {WORK_AREAS_FILE}"}
    
    with open(WORK_AREAS_FILE, "r", encoding="utf-8") as f:
        seed_data = json.load(f)
    
    items = seed_data.get("data", [])
    collection = db.work_areas
    
    inserted = 0
    updated = 0
    
    for item in items:
        item_id = item.get("id")
        if not item_id:
            continue
        
        # Upsert by id
        result = await collection.update_one(
            {"id": item_id},
            {"$set": item},
            upsert=True
        )
        
        if result.upserted_id:
            inserted += 1
        elif result.modified_count > 0:
            updated += 1
    
    # Index erstellen
    await collection.create_index("id", unique=True)
    await collection.create_index("code", sparse=True)
    
    total = await collection.count_documents({"archived": {"$ne": True}})
    
    return {
        "file": WORK_AREAS_FILE,
        "inserted": inserted,
        "updated": updated,
        "total_active": total
    }


async def import_shift_templates(db) -> dict:
    """
    Importiert shift_templates idempotent (upsert by id).
    """
    if not os.path.exists(SHIFT_TEMPLATES_FILE):
        return {"error": f"Datei nicht gefunden: {SHIFT_TEMPLATES_FILE}"}
    
    with open(SHIFT_TEMPLATES_FILE, "r", encoding="utf-8") as f:
        seed_data = json.load(f)
    
    items = seed_data.get("data", [])
    collection = db.shift_templates
    
    inserted = 0
    updated = 0
    
    for item in items:
        item_id = item.get("id")
        if not item_id:
            continue
        
        # Upsert by id
        result = await collection.update_one(
            {"id": item_id},
            {"$set": item},
            upsert=True
        )
        
        if result.upserted_id:
            inserted += 1
        elif result.modified_count > 0:
            updated += 1
    
    # Index erstellen
    await collection.create_index("id", unique=True)
    await collection.create_index("code", sparse=True)
    await collection.create_index("department")
    
    total = await collection.count_documents({"archived": {"$ne": True}, "active": True})
    
    return {
        "file": SHIFT_TEMPLATES_FILE,
        "inserted": inserted,
        "updated": updated,
        "total_active": total
    }


async def check_db_connection(db) -> bool:
    """
    Prüft DB-Verbindung.
    """
    try:
        await db.command("ping")
        return True
    except Exception:
        return False


async def main():
    """
    Hauptfunktion - führt Import aus.
    """
    from motor.motor_asyncio import AsyncIOMotorClient
    
    print("=" * 60)
    print("V2 SEEDS IMPORT")
    print("=" * 60)
    
    # DB-Verbindung
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "gastrocore_v2")
    
    if not mongo_url:
        print("❌ MONGO_URL nicht gesetzt. ABBRUCH.")
        return 1
    
    print(f"\n📌 Target DB: {db_name}")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Connection Check
    if not await check_db_connection(db):
        print("❌ DB nicht erreichbar. ABBRUCH.")
        client.close()
        return 1
    
    print("✅ DB verbunden")
    
    # Import Work Areas
    print("\n--- Work Areas ---")
    wa_result = await import_work_areas(db)
    if "error" in wa_result:
        print(f"⚠️  {wa_result['error']}")
    else:
        print(f"   Inserted: {wa_result['inserted']}")
        print(f"   Updated:  {wa_result['updated']}")
        print(f"   Total:    {wa_result['total_active']}")
    
    # Import Shift Templates
    print("\n--- Shift Templates ---")
    st_result = await import_shift_templates(db)
    if "error" in st_result:
        print(f"⚠️  {st_result['error']}")
    else:
        print(f"   Inserted: {st_result['inserted']}")
        print(f"   Updated:  {st_result['updated']}")
        print(f"   Total:    {st_result['total_active']}")
    
    client.close()
    
    print("\n" + "=" * 60)
    print("✅ V2 SEEDS IMPORT ABGESCHLOSSEN")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
