#!/bin/bash
# ============================================================
# CARLSBURG COCKPIT - DB SWITCH SCRIPT
# Wechselt zwischen Legacy (gastrocore) und V2 (gastrocore_v2)
# ============================================================

ENV_FILE="/app/backend/.env"
LEGACY_BACKUP="/app/backend/.env.legacy_backup"
V2_BACKUP="/app/backend/.env.v2_backup"

show_current() {
    echo "=== AKTUELLE KONFIGURATION ==="
    grep "DB_NAME" "$ENV_FILE" 2>/dev/null | head -1
    grep "^MONGO_URL=" "$ENV_FILE" 2>/dev/null | sed 's/:.*@/:***@/' | head -1
    echo ""
}

switch_to_legacy() {
    echo "🔄 Wechsle zu LEGACY (gastrocore)..."
    
    # Sichere aktuelle V2 config
    cp "$ENV_FILE" "$V2_BACKUP" 2>/dev/null
    
    # Stelle Legacy wieder her
    if [ -f "$LEGACY_BACKUP" ]; then
        cp "$LEGACY_BACKUP" "$ENV_FILE"
        echo "✅ Legacy-Konfiguration wiederhergestellt"
    else
        echo "❌ Kein Legacy-Backup gefunden: $LEGACY_BACKUP"
        exit 1
    fi
    
    # Restart Backend
    sudo supervisorctl restart backend
    sleep 5
    show_current
}

switch_to_v2() {
    echo "🔄 Wechsle zu V2 (gastrocore_v2)..."
    
    # Sichere aktuelle Legacy config (falls noch nicht vorhanden)
    if [ ! -f "$LEGACY_BACKUP" ]; then
        cp "$ENV_FILE" "$LEGACY_BACKUP" 2>/dev/null
    fi
    
    # Stelle V2 wieder her
    if [ -f "$V2_BACKUP" ]; then
        cp "$V2_BACKUP" "$ENV_FILE"
        echo "✅ V2-Konfiguration wiederhergestellt"
    else
        # Manuelle Umstellung auf V2
        sed -i 's|/gastrocore?|/gastrocore_v2?|g' "$ENV_FILE"
        sed -i 's|DB_NAME=gastrocore$|DB_NAME=gastrocore_v2|g' "$ENV_FILE"
        echo "✅ V2-Konfiguration erstellt"
    fi
    
    # Restart Backend
    sudo supervisorctl restart backend
    sleep 5
    show_current
}

case "$1" in
    legacy)
        switch_to_legacy
        ;;
    v2)
        switch_to_v2
        ;;
    status)
        show_current
        curl -s http://localhost:8001/api/health | python3 -m json.tool 2>/dev/null
        ;;
    *)
        echo "Usage: $0 {legacy|v2|status}"
        echo ""
        echo "Befehle:"
        echo "  legacy  - Wechselt zu gastrocore (Legacy-DB)"
        echo "  v2      - Wechselt zu gastrocore_v2 (Clean Rebuild)"
        echo "  status  - Zeigt aktuelle Konfiguration"
        echo ""
        show_current
        ;;
esac
