"""
GastroCore - Opening Hours Seed Script
=====================================
Erstellt die Sommer- und Winter-Perioden sowie Sperrtage.

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

async def seed_opening_hours():
    """Seed Opening Hours Periods und Closures"""
    
    print("=" * 70)
    print("🌱 OPENING HOURS SEED")
    print("=" * 70)
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.gastrocore
    
    # ========== PERIODEN ==========
    
    # Prüfe ob bereits Perioden existieren
    existing_periods = await db.opening_hours_master.count_documents({"archived": {"$ne": True}})
    
    if existing_periods > 0:
        print(f"\n⚠️  Es existieren bereits {existing_periods} Perioden. Überspringe Perioden-Seed.")
    else:
        print("\n📅 Erstelle Öffnungszeiten-Perioden...")
        
        # SOMMER-PERIODE (01.04. - 31.10.)
        sommer = {
            "id": str(uuid.uuid4()),
            "name": "Sommer",
            "start_date": "2025-04-01",
            "end_date": "2025-10-31",
            "rules_by_weekday": {
                "monday": {
                    "is_closed": False,
                    "blocks": [{"start": "12:00", "end": "20:00", "reservable": True, "label": "Tagesservice"}]
                },
                "tuesday": {
                    "is_closed": False,
                    "blocks": [{"start": "12:00", "end": "20:00", "reservable": True, "label": "Tagesservice"}]
                },
                "wednesday": {
                    "is_closed": False,
                    "blocks": [{"start": "12:00", "end": "20:00", "reservable": True, "label": "Tagesservice"}]
                },
                "thursday": {
                    "is_closed": False,
                    "blocks": [{"start": "12:00", "end": "20:00", "reservable": True, "label": "Tagesservice"}]
                },
                "friday": {
                    "is_closed": False,
                    "blocks": [{"start": "12:00", "end": "20:00", "reservable": True, "label": "Tagesservice"}]
                },
                "saturday": {
                    "is_closed": False,
                    "blocks": [{"start": "12:00", "end": "20:00", "reservable": True, "label": "Tagesservice"}]
                },
                "sunday": {
                    "is_closed": False,
                    "blocks": [{"start": "12:00", "end": "20:00", "reservable": True, "label": "Tagesservice"}]
                }
            },
            "active": True,
            "priority": 10,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "archived": False
        }
        
        # WINTER-PERIODE (01.11. - 31.03.)
        winter = {
            "id": str(uuid.uuid4()),
            "name": "Winter",
            "start_date": "2025-11-01",
            "end_date": "2026-03-31",
            "rules_by_weekday": {
                "monday": {
                    "is_closed": True,  # Ruhetag
                    "blocks": []
                },
                "tuesday": {
                    "is_closed": True,  # Ruhetag
                    "blocks": []
                },
                "wednesday": {
                    "is_closed": False,
                    "blocks": [{"start": "12:00", "end": "18:00", "reservable": True, "label": "Tagesservice"}]
                },
                "thursday": {
                    "is_closed": False,
                    "blocks": [{"start": "12:00", "end": "18:00", "reservable": True, "label": "Tagesservice"}]
                },
                "friday": {
                    "is_closed": False,
                    "blocks": [{"start": "12:00", "end": "20:00", "reservable": True, "label": "Tagesservice"}]
                },
                "saturday": {
                    "is_closed": False,
                    "blocks": [{"start": "12:00", "end": "20:00", "reservable": True, "label": "Tagesservice"}]
                },
                "sunday": {
                    "is_closed": False,
                    "blocks": [{"start": "12:00", "end": "18:00", "reservable": True, "label": "Tagesservice"}]
                }
            },
            "active": True,
            "priority": 10,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "archived": False
        }
        
        # Sommer 2026
        sommer_2026 = {
            "id": str(uuid.uuid4()),
            "name": "Sommer 2026",
            "start_date": "2026-04-01",
            "end_date": "2026-10-31",
            "rules_by_weekday": sommer["rules_by_weekday"].copy(),
            "active": True,
            "priority": 10,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "archived": False
        }
        
        # Winter 2026/27
        winter_2026 = {
            "id": str(uuid.uuid4()),
            "name": "Winter 2026/27",
            "start_date": "2026-11-01",
            "end_date": "2027-03-31",
            "rules_by_weekday": winter["rules_by_weekday"].copy(),
            "active": True,
            "priority": 10,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "archived": False
        }
        
        periods = [sommer, winter, sommer_2026, winter_2026]
        await db.opening_hours_master.insert_many(periods)
        
        for p in periods:
            print(f"   ✅ {p['name']}: {p['start_date']} bis {p['end_date']}")
    
    # ========== SPERRTAGE ==========
    
    existing_closures = await db.closures.count_documents({"archived": {"$ne": True}})
    
    if existing_closures > 0:
        print(f"\n⚠️  Es existieren bereits {existing_closures} Sperrtage. Überspringe Closure-Seed.")
    else:
        print("\n🚫 Erstelle Sperrtage...")
        
        closures = [
            # Heiligabend - ganztags geschlossen
            {
                "id": str(uuid.uuid4()),
                "type": "recurring",
                "recurring_rule": {"month": 12, "day": 24},
                "one_off_rule": None,
                "scope": "full_day",
                "start_time": None,
                "end_time": None,
                "reason": "Heiligabend",
                "active": True,
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "archived": False
            },
            # Silvester - ganztags geschlossen
            {
                "id": str(uuid.uuid4()),
                "type": "recurring",
                "recurring_rule": {"month": 12, "day": 31},
                "one_off_rule": None,
                "scope": "full_day",
                "start_time": None,
                "end_time": None,
                "reason": "Silvester",
                "active": True,
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "archived": False
            },
            # Neujahr - ganztags geschlossen
            {
                "id": str(uuid.uuid4()),
                "type": "recurring",
                "recurring_rule": {"month": 1, "day": 1},
                "one_off_rule": None,
                "scope": "full_day",
                "start_time": None,
                "end_time": None,
                "reason": "Neujahr",
                "active": True,
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "archived": False
            }
        ]
        
        await db.closures.insert_many(closures)
        
        for c in closures:
            rule = c.get("recurring_rule", {})
            print(f"   ✅ {c['reason']}: {rule.get('day')}.{rule.get('month')}. (jährlich)")
    
    # ========== ZUSAMMENFASSUNG ==========
    
    print("\n" + "=" * 70)
    print("📊 ZUSAMMENFASSUNG")
    print("=" * 70)
    
    total_periods = await db.opening_hours_master.count_documents({"archived": {"$ne": True}})
    total_closures = await db.closures.count_documents({"archived": {"$ne": True}})
    
    print(f"\n   Perioden: {total_periods}")
    print(f"   Sperrtage: {total_closures}")
    
    # Aktive Perioden anzeigen
    print("\n📅 Aktive Perioden:")
    active_periods = await db.opening_hours_master.find(
        {"active": True, "archived": {"$ne": True}},
        {"_id": 0, "name": 1, "start_date": 1, "end_date": 1}
    ).to_list(10)
    
    for p in active_periods:
        print(f"   • {p['name']}: {p['start_date']} bis {p['end_date']}")
    
    # Aktive Sperrtage anzeigen
    print("\n🚫 Aktive Sperrtage:")
    active_closures = await db.closures.find(
        {"active": True, "archived": {"$ne": True}},
        {"_id": 0, "reason": 1, "type": 1, "recurring_rule": 1}
    ).to_list(10)
    
    for c in active_closures:
        if c["type"] == "recurring":
            rule = c.get("recurring_rule", {})
            print(f"   • {c['reason']}: {rule.get('day')}.{rule.get('month')}. (jährlich wiederkehrend)")
        else:
            print(f"   • {c['reason']}: einmalig")
    
    client.close()
    print("\n✅ Seed abgeschlossen!")


if __name__ == "__main__":
    asyncio.run(seed_opening_hours())
