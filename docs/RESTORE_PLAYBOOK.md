# RESTORE PLAYBOOK - Carlsburg Cockpit
**Version:** 1.0  
**Letzte Aktualisierung:** 2025-01-01

---

## Übersicht

Dieses Playbook beschreibt, wie das Carlsburg Cockpit System nach einem Neustart oder bei einem neuen Agenten in <5 Minuten in den identischen Arbeitszustand gebracht wird.

---

## PHASE 1: Repo & Branch Verifizieren

### Schritt 1.1: Git Status prüfen
```bash
cd /app
git rev-parse --abbrev-ref HEAD  # Sollte: main
git rev-parse --short HEAD       # Aktueller Commit
```

### Schritt 1.2: Remote prüfen
```bash
git remote -v
# Sollte: carlsburger/GastroCore (oder origin)
```

**✅ Erwartetes Ergebnis:** Branch `main`, Commit bekannt

---

## PHASE 2: Services Starten

### Schritt 2.1: Supervisor Status
```bash
sudo supervisorctl status
```

**Erwartetes Ergebnis:**
```
backend    RUNNING
frontend   RUNNING
mongodb    RUNNING
```

### Schritt 2.2: Bei gestoppten Services
```bash
sudo supervisorctl restart all
sleep 10
sudo supervisorctl status
```

### Schritt 2.3: Port-Verifizierung
```bash
netstat -tlnp | grep -E "3000|8001"
```
- Port 3000 → Frontend (node)
- Port 8001 → Backend (uvicorn/python)

---

## PHASE 3: ENV Keys Verifizieren

### Schritt 3.1: Backend ENV prüfen
```bash
cat /app/backend/.env | grep "=" | cut -d'=' -f1 | sort
```

**Erforderliche Keys:**
| Key | Typ | Erforderlich |
|-----|-----|--------------|
| MONGO_URL | Secret | ✅ Ja |
| JWT_SECRET | Secret | ✅ Ja |
| DB_NAME | Config | ✅ Ja |
| SMTP_HOST | Config | ✅ Ja |
| SMTP_PASSWORD | Secret | ⚠️ Platzhalter OK |
| POS_IMAP_HOST | Config | ✅ Ja |
| POS_IMAP_PASSWORD | Secret | ⚠️ Platzhalter OK |

### Schritt 3.2: Frontend ENV prüfen
```bash
cat /app/frontend/.env
```

**Erforderlich:**
```
REACT_APP_BACKEND_URL=https://gastro-widget-fix.preview.emergentagent.com
```

---

## PHASE 4: Boot-Checklist Ausführen

### PUBLIC Checks (ohne Auth)

#### Check 1: Health
```bash
curl -s http://localhost:8001/api/health
```
**Erwartete Antwort:**
```json
{"status":"healthy","database":"connected","version":"3.0.0"}
```

#### Check 2: Restaurant Info
```bash
curl -s http://localhost:8001/api/public/restaurant-info | head -c 200
```
**Erwartete Antwort:** JSON mit `name`, `opening_hours_weekly_text`

#### Check 3: Events
```bash
curl -s http://localhost:8001/api/public/events | head -c 100
```
**Erwartete Antwort:** JSON Array mit Events

#### Check 4: Email Status
```bash
curl -s http://localhost:8001/api/public/email-status
```
**Erwartete Antwort:**
```json
{"smtp_configured":true,"imap_configured":true,...}
```

### UI Checks (Browser oder curl)

#### Check 5: Booking Widget
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/book
```
**Erwartete Antwort:** `200`

#### Check 6: Login Page
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/login
```
**Erwartete Antwort:** `200`

---

## PHASE 5: Seed/Config Status

### Schritt 5.1: Seed Status prüfen
```bash
curl -s http://localhost:8001/internal/seed/status
```

**Erwartetes Ergebnis:**
```json
{
  "users": 10,
  "events": 40,
  "staff_members": 23,
  "opening_hours": 7,
  "recommendation": "DATA_EXISTS"
}
```

### Schritt 5.2: Bei fehlenden Daten
Falls `recommendation: "SEED_NEEDED"`:
```bash
# Als Admin einloggen und Seed ausführen
# Oder per API:
curl -X POST http://localhost:8001/internal/seed
```

---

## PHASE 6: Fehlerdiagnose

### Log-Locations

| Log | Pfad |
|-----|------|
| Backend Error | `/var/log/supervisor/backend.err.log` |
| Backend Output | `/var/log/supervisor/backend.out.log` |
| Frontend Error | `/var/log/supervisor/frontend.err.log` |
| Frontend Output | `/var/log/supervisor/frontend.out.log` |

### Häufige Probleme

#### Problem: "Not authenticated" bei API
**Ursache:** Admin-Endpoint ohne Token aufgerufen  
**Lösung:** Ist korrekt für geschützte Endpoints. Public Endpoints prüfen.

#### Problem: Database not connected
**Diagnose:**
```bash
tail -50 /var/log/supervisor/backend.err.log | grep -i mongo
```
**Lösung:** MONGO_URL in .env prüfen

#### Problem: Frontend 404
**Diagnose:**
```bash
tail -20 /var/log/supervisor/frontend.err.log
```
**Lösung:** `sudo supervisorctl restart frontend`

#### Problem: SMTP Test schlägt fehl
**Diagnose:**
```bash
tail -50 /var/log/supervisor/backend.err.log | grep -i smtp
```
**Lösung:** SMTP_PASSWORD im Emergent Dashboard prüfen

---

## Schnell-Referenz

### Ein-Zeiler Boot-Check
```bash
curl -s http://localhost:8001/api/health && \
curl -s http://localhost:8001/api/public/email-status && \
curl -s -o /dev/null -w "Frontend: %{http_code}\n" http://localhost:3000/book
```

### Kompletter Neustart
```bash
sudo supervisorctl restart all && sleep 15 && \
curl -s http://localhost:8001/api/health
```

---

## Checkliste zum Abhaken

- [ ] Git Branch = main
- [ ] Backend RUNNING
- [ ] Frontend RUNNING
- [ ] MongoDB RUNNING
- [ ] /api/health = healthy + db connected
- [ ] /api/public/restaurant-info = Name korrekt
- [ ] /api/public/events = Liste vorhanden
- [ ] /api/public/email-status = smtp+imap configured
- [ ] /book = HTTP 200
- [ ] /login = HTTP 200

**Wenn alle Checks bestanden: System ist betriebsbereit.**
