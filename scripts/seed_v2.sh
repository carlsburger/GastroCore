#!/bin/bash
# ============================================================
# CARLSBURG COCKPIT - V2 SEEDS WRAPPER
# ============================================================

set -e

echo "============================================================"
echo "       V2 SEEDS IMPORT"
echo "============================================================"
echo ""

# Health Check
echo "📌 Health Check..."
HEALTH=$(curl -s http://localhost:8001/api/health)
if echo "$HEALTH" | grep -q '"database":"connected"'; then
    echo "   ✅ Backend healthy, DB connected"
else
    echo "   ❌ Backend nicht healthy oder DB disconnected"
    echo "   $HEALTH"
    exit 1
fi
echo ""

# Import ausführen
echo "📌 Import ausführen..."
python3 /app/scripts/import_v2_seeds.py
echo ""

# Post-Check
echo "📌 Post-Check..."
echo "   Health: $(curl -s http://localhost:8001/api/health | grep -o '"database":"[^"]*"')"
echo ""

echo "============================================================"
echo "       DONE"
echo "============================================================"
