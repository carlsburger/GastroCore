"""
GastroCore - Reservation Slots Seed Script
==========================================
Erstellt Standard-Slot-Regeln und Event-Cutoff-Konfiguration.

WICHTIG: Nur einmal ausführen! Bestehende Daten werden NICHT überschrieben.
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import uuid
import os
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')

MONGO_URL = os.environ.get('MONGO_URL')

def now_iso():
    return datetime.now(timezone.utc).isoformat()

async def seed_slot_rules():
    """Seed Slot-Regeln"""
    
    print("=" * 70)
    print("🎰 RESERVATION SLOTS SEED")
    print("=" * 70)
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.gastrocore
    
    # ========== SLOT-REGELN ==========
    
    existing_rules = await db.reservation_slot_rules.count_documents({"archived": {"$ne": True}})
    
    if existing_rules > 0:
        print(f"\n⚠️  Es existieren bereits {existing_rules} Slot-Regeln. Überspringe Seed.")
    else:
        print("\n📅 Erstelle Slot-Regeln...")
        
        rules = [
            # Wochenende mit Durchgängen (Sa/So)
            {
                "id": str(uuid.uuid4()),
                "name": "Wochenende mit Durchgängen",
                "valid_from": None,
                "valid_to": None,
                "applies_days": [5, 6],  # Sa, So
                "slot_interval_minutes": 30,
                "allowed_start_times": None,
                "generate_between": {
                    "start": "11:30",
                    "end": "19:30",
                    "interval": 30
                },
                "blocked_windows": [
                    {
                        "start": "12:05",
                        "end": "13:55",
                        "reason": "1. Durchgang voll / Küchenfenster"
                    },
                    {
                        "start": "15:35",
                        "end": "16:55",
                        "reason": "2. Durchgang voll / Küchenfenster"
                    }
                ],
                "active": True,
                "priority": 20,
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "archived": False
            },
            # Wochentags ohne Durchgänge (Mi-Fr)
            {
                "id": str(uuid.uuid4()),
                "name": "Wochentags Standard",
                "valid_from": None,
                "valid_to": None,
                "applies_days": [2, 3, 4],  # Mi, Do, Fr
                "slot_interval_minutes": 30,
                "allowed_start_times": None,
                "generate_between": {
                    "start": "12:00",
                    "end": "19:30",
                    "interval": 30
                },
                "blocked_windows": [],
                "active": True,
                "priority": 10,
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "archived": False
            },
            # Ruhetage (Mo/Di) - als Fallback falls doch offen (Feiertag)
            {
                "id": str(uuid.uuid4()),
                "name": "Feiertags-Slots (Mo/Di wenn offen)",
                "valid_from": None,
                "valid_to": None,
                "applies_days": [0, 1],  # Mo, Di
                "slot_interval_minutes": 30,
                "allowed_start_times": None,
                "generate_between": {
                    "start": "12:00",
                    "end": "19:30",
                    "interval": 30
                },
                "blocked_windows": [],
                "active": True,
                "priority": 5,  # Niedrige Priorität - nur wenn Feiertag
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "archived": False
            }
        ]
        
        await db.reservation_slot_rules.insert_many(rules)
        
        for r in rules:
            days = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
            day_str = ", ".join([days[d] for d in r["applies_days"]])
            blocked = len(r.get("blocked_windows", []))
            print(f"   ✅ {r['name']} ({day_str}) - {blocked} Sperrfenster, Prio {r['priority']}")
    
    # ========== EVENT-CUTOFF SETTING ==========
    
    existing_cutoff = await db.settings.find_one({"key": "event_cutoff_minutes_default"})
    
    if existing_cutoff:
        print(f"\n⚠️  Event-Cutoff bereits konfiguriert: {existing_cutoff.get('value')} Minuten")
    else:
        print("\n⚙️ Erstelle Event-Cutoff-Setting...")
        
        await db.settings.insert_one({
            "id": str(uuid.uuid4()),
            "key": "event_cutoff_minutes_default",
            "value": "120",
            "description": "Standard-Cutoff für letzte à la carte Reservierung vor Event (Minuten)",
            "created_at": now_iso(),
            "updated_at": now_iso()
        })
        
        print("   ✅ event_cutoff_minutes_default = 120 Minuten")
    
    # ========== ZUSAMMENFASSUNG ==========
    
    print("\n" + "=" * 70)
    print("📊 ZUSAMMENFASSUNG")
    print("=" * 70)
    
    total_rules = await db.reservation_slot_rules.count_documents({"archived": {"$ne": True}})
    
    print(f"\n   Slot-Regeln: {total_rules}")
    
    # Aktive Regeln anzeigen
    print("\n📅 Aktive Slot-Regeln:")
    active_rules = await db.reservation_slot_rules.find(
        {"active": True, "archived": {"$ne": True}},
        {"_id": 0, "name": 1, "applies_days": 1, "priority": 1, "blocked_windows": 1}
    ).sort("priority", -1).to_list(10)
    
    days = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    for r in active_rules:
        day_str = ", ".join([days[d] for d in r.get("applies_days", [])])
        blocked = len(r.get("blocked_windows", []))
        print(f"   • {r['name']} ({day_str}) - Prio {r.get('priority', 0)}, {blocked} Sperr.")
    
    # Blocked Windows Details
    print("\n🚫 Konfigurierte Sperrfenster:")
    for r in active_rules:
        if r.get("blocked_windows"):
            for bw in r["blocked_windows"]:
                print(f"   • {bw.get('start')}-{bw.get('end')}: {bw.get('reason')}")
    
    client.close()
    print("\n✅ Slot-Seed abgeschlossen!")


if __name__ == "__main__":
    asyncio.run(seed_slot_rules())
