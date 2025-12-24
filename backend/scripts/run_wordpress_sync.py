#!/usr/bin/env python3
"""
WordPress Event Sync Runner
===========================
Führt den WordPress Event Sync aus.
Kann manuell oder per Cron/Supervisor aufgerufen werden.

Features:
- Lock-Mechanismus verhindert parallele Ausführung
- Direkter Aufruf der Sync-Logik (kein HTTP)
- Sauberes Logging nach stdout/stderr
- Exit-Codes: 0=OK, 1=Fehler, 2=bereits laufend

Usage:
  python run_wordpress_sync.py
  python run_wordpress_sync.py --force  # Lock ignorieren
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Lock-Datei
LOCK_FILE = Path("/tmp/wp_sync.lock")
LOCK_TIMEOUT_SECONDS = 3600  # 1 Stunde - danach gilt Lock als veraltet

# Backend-Pfad hinzufügen
BACKEND_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_PATH))


def acquire_lock() -> bool:
    """
    Versucht Lock zu setzen.
    Returns True wenn Lock erworben, False wenn bereits gelockt.
    """
    if LOCK_FILE.exists():
        # Prüfe ob Lock veraltet ist
        try:
            lock_time = datetime.fromtimestamp(LOCK_FILE.stat().st_mtime, tz=timezone.utc)
            age_seconds = (datetime.now(timezone.utc) - lock_time).total_seconds()
            
            if age_seconds > LOCK_TIMEOUT_SECONDS:
                logger.warning(f"Veralteter Lock gefunden ({age_seconds:.0f}s alt), entferne...")
                LOCK_FILE.unlink()
            else:
                return False
        except Exception as e:
            logger.error(f"Fehler beim Lock-Check: {e}")
            return False
    
    # Lock setzen
    try:
        LOCK_FILE.write_text(f"PID: {os.getpid()}\nStarted: {datetime.now(timezone.utc).isoformat()}")
        return True
    except Exception as e:
        logger.error(f"Fehler beim Lock-Setzen: {e}")
        return False


def release_lock():
    """Entfernt den Lock."""
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except Exception as e:
        logger.warning(f"Fehler beim Lock-Entfernen: {e}")


async def run_sync():
    """Führt den WordPress Sync aus."""
    # Imports innerhalb der Funktion um zirkuläre Imports zu vermeiden
    from dotenv import load_dotenv
    load_dotenv(BACKEND_PATH / ".env")
    
    # MongoDB initialisieren
    from motor.motor_asyncio import AsyncIOMotorClient
    
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "gastrocore")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Sync-Logik importieren und ausführen
    from events_module import (
        fetch_wordpress_events,
        map_wordpress_event_to_gastrocore,
        has_real_changes,
        decode_html_entities,
        SYNC_SOURCE,
        WORDPRESS_EVENTS_API
    )
    import uuid
    from datetime import timedelta
    import time
    
    def now_iso():
        return datetime.now(timezone.utc).isoformat()
    
    start_time = time.time()
    
    report = {
        "fetched": 0,
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "archived": 0,
        "skipped": 0,
        "errors": [],
    }
    
    try:
        # 1. Events von WordPress holen
        logger.info("Hole Events von WordPress...")
        wp_events = await fetch_wordpress_events()
        report["fetched"] = len(wp_events)
        logger.info(f"  → {len(wp_events)} Events gefunden")
        
        # Track welche external_ids wir gesehen haben
        seen_external_ids = set()
        
        # 2. Für jedes Event: Create oder Update
        for wp_event in wp_events:
            try:
                mapped = map_wordpress_event_to_gastrocore(wp_event)
                external_id = mapped["external_id"]
                seen_external_ids.add(external_id)
                
                # Prüfe ob Event bereits existiert
                existing = await db.events.find_one({
                    "external_source": SYNC_SOURCE,
                    "external_id": external_id,
                    "archived": {"$ne": True}
                })
                
                if existing:
                    # Prüfe ob sich wirklich etwas geändert hat
                    if has_real_changes(existing, mapped):
                        update_fields = {
                            "title": mapped["title"],
                            "description": mapped["description"],
                            "short_description": mapped["short_description"],
                            "image_url": mapped["image_url"],
                            "start_datetime": mapped["start_datetime"],
                            "end_datetime": mapped["end_datetime"],
                            "entry_price": mapped["entry_price"],
                            "website_url": mapped["website_url"],
                            "slug": mapped["slug"],
                            "event_type": mapped["event_type"],
                            "wp_categories": mapped["wp_categories"],
                            "updated_at": now_iso(),
                            "last_sync_at": now_iso(),
                        }
                        
                        await db.events.update_one(
                            {"id": existing["id"]},
                            {"$set": update_fields}
                        )
                        report["updated"] += 1
                    else:
                        # Keine echten Änderungen
                        await db.events.update_one(
                            {"id": existing["id"]},
                            {"$set": {"last_sync_at": now_iso()}}
                        )
                        report["unchanged"] += 1
                        
                else:
                    # CREATE
                    new_event = {
                        "id": str(uuid.uuid4()),
                        "external_source": mapped["external_source"],
                        "external_id": mapped["external_id"],
                        "title": mapped["title"],
                        "description": mapped["description"],
                        "short_description": mapped["short_description"],
                        "image_url": mapped["image_url"],
                        "start_datetime": mapped["start_datetime"],
                        "end_datetime": mapped["end_datetime"],
                        "entry_price": mapped["entry_price"],
                        "website_url": mapped["website_url"],
                        "slug": mapped["slug"],
                        "event_type": mapped["event_type"],
                        "content_category": "VERANSTALTUNG",
                        "wp_categories": mapped["wp_categories"],
                        "status": "published",
                        "capacity_total": 100,
                        "booking_mode": "ticket_only",
                        "pricing_mode": "free_config",
                        "requires_payment": False,
                        "is_public": True,
                        "archived": False,
                        "created_at": now_iso(),
                        "updated_at": now_iso(),
                        "last_sync_at": now_iso(),
                    }
                    
                    await db.events.insert_one(new_event)
                    report["created"] += 1
                    
            except Exception as e:
                report["errors"].append(f"Event {wp_event.get('id')}: {str(e)}")
                report["skipped"] += 1
        
        # 3. Archivieren
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        
        all_wp_events_in_db = await db.events.find({
            "external_source": SYNC_SOURCE,
            "archived": {"$ne": True}
        }).to_list(1000)
        
        for db_event in all_wp_events_in_db:
            ext_id = db_event.get("external_id")
            end_dt = db_event.get("end_datetime")
            
            should_archive = False
            if ext_id not in seen_external_ids:
                should_archive = True
            if end_dt and end_dt < cutoff_date:
                should_archive = True
            
            if should_archive:
                await db.events.update_one(
                    {"id": db_event["id"]},
                    {"$set": {"archived": True, "status": "archived", "updated_at": now_iso()}}
                )
                report["archived"] += 1
        
        # 4. Import-Log schreiben
        duration_ms = int((time.time() - start_time) * 1000)
        report["duration_ms"] = duration_ms
        
        result_status = "success" if len(report["errors"]) == 0 else "partial"
        
        import_log = {
            "id": str(uuid.uuid4()),
            "type": "wordpress_events_sync",
            "timestamp": now_iso(),
            "user": "scheduler",
            "source": WORDPRESS_EVENTS_API,
            "fetched": report["fetched"],
            "created": report["created"],
            "updated": report["updated"],
            "unchanged": report["unchanged"],
            "archived": report["archived"],
            "skipped": report["skipped"],
            "errors": report["errors"][:10],
            "duration_ms": duration_ms,
            "success": result_status == "success",
            "result": result_status,
        }
        
        await db.import_logs.insert_one(import_log)
        
        return report
        
    except Exception as e:
        logger.error(f"Sync-Fehler: {e}")
        report["errors"].append(str(e))
        
        # Fehler-Log schreiben
        error_log = {
            "id": str(uuid.uuid4()),
            "type": "wordpress_events_sync",
            "timestamp": now_iso(),
            "user": "scheduler",
            "source": WORDPRESS_EVENTS_API,
            "success": False,
            "result": "error",
            "error": str(e),
        }
        await db.import_logs.insert_one(error_log)
        
        raise
    
    finally:
        client.close()


def main():
    """Hauptfunktion."""
    import argparse
    
    parser = argparse.ArgumentParser(description="WordPress Event Sync Runner")
    parser.add_argument("--force", action="store_true", help="Lock ignorieren")
    args = parser.parse_args()
    
    logger.info("=" * 50)
    logger.info("WordPress Event Sync gestartet")
    logger.info("=" * 50)
    
    # Lock prüfen
    if not args.force:
        if not acquire_lock():
            logger.warning("Sync bereits aktiv (Lock existiert). Abbruch.")
            sys.exit(2)
    
    try:
        # Sync ausführen
        report = asyncio.run(run_sync())
        
        # Ergebnis ausgeben
        logger.info("-" * 50)
        logger.info("Sync abgeschlossen:")
        logger.info(f"  Geholt:      {report['fetched']}")
        logger.info(f"  Neu:         {report['created']}")
        logger.info(f"  Aktualisiert:{report['updated']}")
        logger.info(f"  Unverändert: {report['unchanged']}")
        logger.info(f"  Archiviert:  {report['archived']}")
        logger.info(f"  Übersprungen:{report['skipped']}")
        logger.info(f"  Dauer:       {report.get('duration_ms', 0)}ms")
        
        if report['errors']:
            logger.warning(f"  Fehler:      {len(report['errors'])}")
            for err in report['errors'][:5]:
                logger.warning(f"    - {err}")
        
        logger.info("=" * 50)
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Sync fehlgeschlagen: {e}")
        sys.exit(1)
        
    finally:
        release_lock()


if __name__ == "__main__":
    main()
