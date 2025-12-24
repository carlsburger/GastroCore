#!/bin/bash
# WordPress Event Sync Scheduler
# Läuft in einer Endlosschleife mit 60-Minuten Intervall
# Wird von Supervisor verwaltet

SYNC_SCRIPT="/app/backend/scripts/run_wordpress_sync.py"
INTERVAL_SECONDS=3600  # 60 Minuten
LOG_PREFIX="[WP-SYNC-SCHEDULER]"

echo "$LOG_PREFIX Scheduler gestartet (Intervall: ${INTERVAL_SECONDS}s)"

# Warte 60 Sekunden nach Start (damit Backend sicher läuft)
echo "$LOG_PREFIX Initialer Wartezeit: 60s..."
sleep 60

while true; do
    echo "$LOG_PREFIX $(date '+%Y-%m-%d %H:%M:%S') - Starte WordPress Sync..."
    
    # Sync ausführen
    cd /app/backend && /root/.venv/bin/python "$SYNC_SCRIPT"
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "$LOG_PREFIX Sync erfolgreich"
    elif [ $EXIT_CODE -eq 2 ]; then
        echo "$LOG_PREFIX Sync übersprungen (bereits aktiv)"
    else
        echo "$LOG_PREFIX Sync fehlgeschlagen (Exit: $EXIT_CODE)"
    fi
    
    echo "$LOG_PREFIX Nächster Sync in ${INTERVAL_SECONDS}s ($(date -d "+${INTERVAL_SECONDS} seconds" '+%H:%M:%S'))"
    sleep $INTERVAL_SECONDS
done
