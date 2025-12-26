#!/usr/bin/env python3
"""
ROLLBACK-SKRIPT: Setzt alle Shift-Zuweisungen zurück auf null
Backup-Datei: /app/backups/shifts_backup_20251226_015349.json

Verwendung:
  cd /app/backend
  export $(grep -v '^#' .env | xargs)
  python3 /app/backups/rollback_shifts.py

ACHTUNG: Dies setzt staff_member_id auf null zurück!
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
from datetime import datetime, timezone

BACKUP_FILE = "/app/backups/shifts_backup_20251226_015349.json"

async def rollback():
    # Backup laden
    with open(BACKUP_FILE, 'r') as f:
        backup = json.load(f)
    
    print(f"Rollback aus: {BACKUP_FILE}")
    print(f"Enthält: {backup['total_shifts']} Shifts")
    print(f"Schedule: KW {backup['week']}/{backup['year']}")
    print("")
    
    confirm = input("Wirklich zurücksetzen? (ja/nein): ")
    if confirm.lower() != 'ja':
        print("Abgebrochen.")
        return
    
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    db = client['gastrocore']
    
    reset_count = 0
    for shift in backup['shifts']:
        # NUR staff_member_id zurücksetzen (war null im Backup)
        original_staff_id = shift.get('staff_member_id')  # sollte null sein
        
        result = await db.shifts.update_one(
            {"id": shift['id']},
            {"$set": {
                "staff_member_id": original_staff_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        if result.modified_count == 1:
            reset_count += 1
    
    print(f"\n✅ {reset_count} Shifts zurückgesetzt auf staff_member_id: null")
    client.close()

if __name__ == "__main__":
    asyncio.run(rollback())
