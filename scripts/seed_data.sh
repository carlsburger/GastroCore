#!/bin/bash
# ============================================================
# CARLSBURG COCKPIT – FIRST-RUN SEED SCRIPT
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

BACKEND_URL="${BACKEND_URL:-http://localhost:8001}"

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  CARLSBURG COCKPIT - FIRST-RUN SEED${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# 1. Check status
echo -e "${YELLOW}[1/3] Prüfe Datenbank-Status...${NC}"
STATUS=$(curl -s "${BACKEND_URL}/internal/seed/status")
echo "$STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  Users: {d[\"users\"]}, Areas: {d[\"areas\"]}, Events: {d[\"events\"]}')"
echo ""

RECOMMENDATION=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['recommendation'])")

if [ "$RECOMMENDATION" == "DATA_EXISTS" ] && [ "$1" != "--force" ]; then
    echo -e "${YELLOW}⚠ Daten bereits vorhanden. Seed übersprungen.${NC}"
    echo "  Nutze --force um trotzdem zu seeden (idempotent)."
    exit 0
fi

# 2. Run seed
echo -e "${YELLOW}[2/3] Führe Seed aus...${NC}"
FORCE_PARAM=""
[ "$1" == "--force" ] && FORCE_PARAM="?force=true"

SEED_RESULT=$(curl -s -X POST "${BACKEND_URL}/internal/seed${FORCE_PARAM}")

# Extract summary
NEW_ITEMS=$(echo "$SEED_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['summary']['new_items'])")
SKIPPED=$(echo "$SEED_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['summary']['skipped_items'])")

echo -e "  ${GREEN}✓${NC} Neu angelegt: $NEW_ITEMS"
echo -e "  ${GREEN}✓${NC} Übersprungen: $SKIPPED"
echo ""

# 3. Verify
echo -e "${YELLOW}[3/3] Verifiziere Seed...${NC}"
VERIFY=$(curl -s "${BACKEND_URL}/internal/seed/verify")
STATUS_CHECK=$(echo "$VERIFY" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")

if [ "$STATUS_CHECK" == "READY" ]; then
    echo -e "  ${GREEN}✓ System ist READY${NC}"
else
    echo -e "  ${RED}✗ System ist INCOMPLETE${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  SEED ABGESCHLOSSEN${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Show credentials if new
if [ "$NEW_ITEMS" -gt "0" ]; then
    echo -e "${YELLOW}Login-Daten:${NC}"
    echo "  Admin:        admin@carlsburg.de / Carlsburg2025!"
    echo "  Schichtleiter: schichtleiter@carlsburg.de / Schicht2025!"
    echo "  Mitarbeiter:  mitarbeiter@carlsburg.de / Mitarbeiter2025!"
    echo ""
    echo -e "${YELLOW}⚠ Passwörter müssen beim ersten Login geändert werden!${NC}"
fi

echo ""
echo -e "${GREEN}FIRST-RUN READY ✓${NC}"
