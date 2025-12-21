#!/bin/bash
# ============================================================
# CARLSBURG COCKPIT – SAFEPOINT BACKUP SCRIPT
# ============================================================

set -e

# Farben für Ausgabe
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  CARLSBURG COCKPIT - BACKUP SYSTEM${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Projektverzeichnis
PROJECT_DIR="/app"
BACKUP_DIR="${PROJECT_DIR}/backups"

# In Projektverzeichnis wechseln
cd "$PROJECT_DIR"

# A) Build/Commit erfassen
echo -e "${YELLOW}[1/4] Erfasse Build-Informationen...${NC}"

COMMIT_SHORT=$(git rev-parse --short HEAD 2>/dev/null || echo "no-git")
COMMIT_FULL=$(git rev-parse HEAD 2>/dev/null || echo "no-git")
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
DATETIME=$(date +"%Y%m%d_%H%M")
DATE_READABLE=$(date +"%Y-%m-%d %H:%M:%S")

# Version von API holen (falls Backend läuft)
BUILD_ID="unknown"
VERSION="unknown"
if curl -s http://localhost:8001/api/version > /dev/null 2>&1; then
    API_RESPONSE=$(curl -s http://localhost:8001/api/version)
    BUILD_ID=$(echo "$API_RESPONSE" | grep -o '"build_id":"[^"]*' | cut -d'"' -f4 || echo "unknown")
    VERSION=$(echo "$API_RESPONSE" | grep -o '"health_version":"[^"]*' | cut -d'"' -f4 || echo "unknown")
fi

echo "  Commit: $COMMIT_SHORT"
echo "  Branch: $BRANCH"
echo "  Build-ID: $BUILD_ID"
echo "  Version: $VERSION"
echo ""

# Backup-Verzeichnis erstellen
mkdir -p "$BACKUP_DIR"

# Dateinamen
PATCH_FILE="${BACKUP_DIR}/patch_${COMMIT_SHORT}_${DATETIME}.patch"
ZIP_FILE="${BACKUP_DIR}/release_${COMMIT_SHORT}_${DATETIME}.zip"
REPORT_FILE="${BACKUP_DIR}/backup_report_${COMMIT_SHORT}_${DATETIME}.md"

# B) Patch exportieren
echo -e "${YELLOW}[2/4] Erstelle Patch-Datei...${NC}"
if git diff > "$PATCH_FILE" 2>/dev/null; then
    PATCH_SIZE=$(du -h "$PATCH_FILE" | cut -f1)
    if [ -s "$PATCH_FILE" ]; then
        echo -e "  ${GREEN}✓${NC} Patch erstellt: $(basename $PATCH_FILE) ($PATCH_SIZE)"
    else
        echo "  ℹ Keine uncommitted Änderungen (Patch leer)"
    fi
else
    echo "  ⚠ Kein Git-Repository, Patch übersprungen"
    touch "$PATCH_FILE"
fi
echo ""

# C) ZIP exportieren
echo -e "${YELLOW}[3/4] Erstelle ZIP-Archiv...${NC}"
echo "  Ausgeschlossen: node_modules, .venv, .git, .env, logs, uploads, __pycache__"

# ZIP erstellen mit Ausschlüssen
cd "$PROJECT_DIR"
zip -r "$ZIP_FILE" . \
    -x "node_modules/*" \
    -x "*/node_modules/*" \
    -x ".venv/*" \
    -x "venv/*" \
    -x "__pycache__/*" \
    -x "*/__pycache__/*" \
    -x "dist/*" \
    -x "build/*" \
    -x ".git/*" \
    -x ".env" \
    -x "*/.env" \
    -x "logs/*" \
    -x "uploads/*" \
    -x "*.log" \
    -x "*.pyc" \
    -x ".DS_Store" \
    -x "backups/*.zip" \
    -x "backups/*.patch" \
    > /dev/null 2>&1

ZIP_SIZE=$(du -h "$ZIP_FILE" | cut -f1)
echo -e "  ${GREEN}✓${NC} ZIP erstellt: $(basename $ZIP_FILE) ($ZIP_SIZE)"
echo ""

# D) Mini-Report schreiben
echo -e "${YELLOW}[4/4] Erstelle Backup-Report...${NC}"

cat > "$REPORT_FILE" << EOF
# Backup Report – Carlsburg Cockpit

**Erstellt:** ${DATE_READABLE}

## Build-Informationen

| Feld | Wert |
|------|------|
| Commit (kurz) | ${COMMIT_SHORT} |
| Commit (voll) | ${COMMIT_FULL} |
| Branch | ${BRANCH} |
| Build-ID | ${BUILD_ID} |
| Version | ${VERSION} |

## Erzeugte Dateien

| Datei | Größe |
|-------|-------|
| $(basename $PATCH_FILE) | ${PATCH_SIZE:-0} |
| $(basename $ZIP_FILE) | ${ZIP_SIZE} |
| $(basename $REPORT_FILE) | - |

## Nächste Schritte

1. **ZIP-Datei lokal herunterladen:**
   \`\`\`
   ${ZIP_FILE}
   \`\`\`

2. **Sicher aufbewahren** (Cloud-Speicher, lokale Festplatte)

3. **Tab kann geschlossen werden**

## Wiederherstellung

1. ZIP entpacken
2. \`yarn install\` im frontend-Ordner
3. \`pip install -r backend/requirements.txt\`
4. .env-Dateien neu anlegen
5. Services starten

---
*Automatisch generiert von make_backup.sh*
EOF

REPORT_SIZE=$(du -h "$REPORT_FILE" | cut -f1)
echo -e "  ${GREEN}✓${NC} Report erstellt: $(basename $REPORT_FILE) ($REPORT_SIZE)"
echo ""

# Zusammenfassung
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  BACKUP ABGESCHLOSSEN${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "Erzeugte Dateien:"
echo "  📄 $PATCH_FILE"
echo "  📦 $ZIP_FILE"
echo "  📋 $REPORT_FILE"
echo ""
echo -e "${YELLOW}⚠ WICHTIG: ZIP jetzt lokal herunterladen!${NC}"
echo "  Pfad: $ZIP_FILE"
echo ""
echo -e "${GREEN}SAFEPOINT READY ✓${NC}"
