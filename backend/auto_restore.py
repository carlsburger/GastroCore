"""
Auto-Restore System für GastroCore
===================================
Wird beim Backend-Start ausgeführt und stellt Daten aus Backups wieder her,
falls die kritischen Collections leer sind.

WICHTIG: Nur READ + INSERT, kein DROP, kein DELETE
GUARD: Nur ausführen wenn AUTO_RESTORE_ENABLED=true
"""

import json
import os
import logging
from pathlib import Path
from pymongo import MongoClient
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auto_restore")

BACKUP_DIR = Path("/app/backups")
CRITICAL_COLLECTIONS = ["staff_members", "tables", "work_areas", "shift_templates"]


def is_auto_restore_enabled() -> bool:
    """Prüft ob Auto-Restore aktiviert ist (Default: false)"""
    return os.getenv("AUTO_RESTORE_ENABLED", "false").lower() == "true"


def get_db():
    """MongoDB Verbindung herstellen - KEIN LOCALHOST FALLBACK"""
    mongo_url = os.getenv("MONGO_URL")
    
    if not mongo_url:
        logger.error("❌ MONGO_URL nicht gesetzt!")
        raise ValueError("MONGO_URL environment variable is required")
    
    # ATLAS-GUARD: Wenn REQUIRE_ATLAS=true, nur Atlas-URIs erlauben
    require_atlas = os.getenv("REQUIRE_ATLAS", "false").lower() == "true"
    is_atlas = "mongodb+srv://" in mongo_url or ".mongodb.net" in mongo_url
    is_localhost = "localhost" in mongo_url or "127.0.0.1" in mongo_url
    
    if require_atlas and not is_atlas:
        logger.error("❌ REQUIRE_ATLAS=true aber keine Atlas-URI konfiguriert!")
        raise ValueError("Atlas connection required but localhost URI detected")
    
    if require_atlas and is_localhost:
        logger.error("❌ REQUIRE_ATLAS=true aber localhost-URI detected!")
        raise ValueError("Atlas connection required but localhost URI detected")
    
    client = MongoClient(mongo_url)
    db_name = os.getenv("DB_NAME") or mongo_url.split("/")[-1].split("?")[0]
    return client[db_name]

def check_and_restore():
    """Prüft ob kritische Collections leer sind und stellt ggf. wieder her
    
    GUARD: Nur ausführen wenn AUTO_RESTORE_ENABLED=true
    """
    # AUTO-RESTORE GUARD
    if not is_auto_restore_enabled():
        logger.info("ℹ️ Auto-Restore ist deaktiviert (AUTO_RESTORE_ENABLED != true)")
        return {"status": "disabled", "restored": False, "reason": "AUTO_RESTORE_ENABLED not set to true"}
    
    db = get_db()
    
    # Prüfe ob Restore nötig ist
    needs_restore = False
    for coll in CRITICAL_COLLECTIONS:
        count = db[coll].count_documents({})
        if count == 0:
            logger.warning(f"⚠️ Collection '{coll}' ist LEER!")
            needs_restore = True
        else:
            logger.info(f"✓ Collection '{coll}': {count} Dokumente")
    
    if not needs_restore:
        logger.info("✅ Alle kritischen Collections haben Daten - kein Restore nötig")
        return {"status": "ok", "restored": False}
    
    logger.warning("🔄 Starte Auto-Restore aus Backups...")
    
    # Finde das beste Backup
    backup_path = BACKUP_DIR / "post_import_20251226_152821"
    if not backup_path.exists():
        logger.error("❌ Backup-Verzeichnis nicht gefunden!")
        return {"status": "error", "message": "Backup not found"}
    
    restored = {}
    
    # Restore jede leere Collection
    for coll in CRITICAL_COLLECTIONS:
        if db[coll].count_documents({}) == 0:
            backup_file = backup_path / f"{coll}.json"
            if backup_file.exists():
                with open(backup_file, "r") as f:
                    docs = json.load(f)
                
                # Entferne _id falls vorhanden
                for doc in docs:
                    if "_id" in doc:
                        del doc["_id"]
                
                if docs:
                    db[coll].insert_many(docs)
                    restored[coll] = len(docs)
                    logger.info(f"✅ Restored {coll}: {len(docs)} Dokumente")
    
    # Log Restore
    db.restore_logs.insert_one({
        "timestamp": datetime.utcnow().isoformat(),
        "type": "auto_restore",
        "restored": restored,
        "trigger": "empty_collections_detected"
    })
    
    return {"status": "ok", "restored": True, "collections": restored}

if __name__ == "__main__":
    result = check_and_restore()
    print(json.dumps(result, indent=2))
