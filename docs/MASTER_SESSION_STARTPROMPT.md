# MASTER SESSION STARTPROMPT
## Carlsburg Cockpit - Stabiler Arbeitszustand

---

## SYSTEM IDENTIFIKATION

```
PROJEKT:        Carlsburg Cockpit
APP-NAME:       gastro-widget-fix (in Emergent)
REPOSITORY:     carlsburger/GastroCore
BRANCH:         main
PREVIEW-URL:    https://gastro-widget-fix.preview.emergentagent.com
```

---

## ABSOLUTE REGELN

1. **KEINE neuen Features** – Nur Stabilität, Diagnose, Bugfixes
2. **KEINE Änderungen an Fachlogik** – Bestehendes darf nicht brechen
3. **Secrets NIEMALS in Git** – Passwörter nur als ENV in Emergent Dashboard
4. **Deterministische Konfig** – Alle Konfigurationsdaten als Source-of-Truth versioniert
5. **MongoDB Atlas ist extern** – Operative Daten bleiben dort, nur Config wird geseeded

---

## BOOT-CHECKLIST (ohne Login ausführbar)

Nach jedem Neustart diese Checks durchführen:

### 1. Services prüfen
```bash
sudo supervisorctl status
# Erwartung: backend, frontend, mongodb = RUNNING
```

### 2. API Health
```bash
curl -s http://localhost:8001/api/health
```
**Erwartete Antwort:**
```json
{"status":"healthy","database":"connected","version":"3.0.0"}
```

### 3. Restaurant Info
```bash
curl -s http://localhost:8001/api/public/restaurant-info
```
**Erwartete Antwort:** JSON mit `name: "Carlsburg..."`

### 4. Events Liste
```bash
curl -s http://localhost:8001/api/public/events | head -c 100
```
**Erwartete Antwort:** JSON Array

### 5. E-Mail Status
```bash
curl -s http://localhost:8001/api/public/email-status
```
**Erwartete Antwort:**
```json
{"smtp_configured":true,"imap_configured":true,"message":"Beide Dienste konfiguriert"}
```

### 6. Frontend erreichbar
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/book
# Erwartung: 200
```

---

## EIN-ZEILER BOOT-CHECK

```bash
curl -s http://localhost:8001/api/health && echo " ✓" && \
curl -s http://localhost:8001/api/public/email-status | grep -q "true" && echo "Email ✓" && \
curl -s -o /dev/null -w "Frontend: %{http_code}\n" http://localhost:3000/book
```

---

## RESTORE BEI PROBLEMEN

### Services neu starten
```bash
sudo supervisorctl restart all
sleep 15
sudo supervisorctl status
```

### Logs prüfen
```bash
# Backend Fehler
tail -50 /var/log/supervisor/backend.err.log

# Frontend Fehler
tail -50 /var/log/supervisor/frontend.err.log
```

### Seed Status prüfen
```bash
curl -s http://localhost:8001/internal/seed/status
```

---

## STOP CONDITIONS

**Abbrechen und eskalieren wenn:**

1. ❌ MongoDB `database: "disconnected"` nach 3 Restart-Versuchen
2. ❌ MONGO_URL fehlt komplett in .env
3. ❌ Frontend-Build schlägt dauerhaft fehl (yarn build Errors)
4. ❌ Git Repo ist in detached HEAD oder anderem Branch als `main`
5. ❌ Unbekannter/fremder Code in `/app/` der nicht zu GastroCore gehört

---

## WICHTIGE DATEIEN

| Datei | Zweck |
|-------|-------|
| `/app/docs/MASTER_SNAPSHOT.md` | System-Fingerprint (Git, Build, ENV Keys) |
| `/app/docs/RESTORE_PLAYBOOK.md` | Schritt-für-Schritt Wiederherstellung |
| `/app/backend/.env` | Backend Konfiguration |
| `/app/backend/.env.example` | Vorlage für ENV |
| `/app/seed/` | Deterministische Seed-Daten |
| `/app/scripts/seed_data.sh` | Seed-Script |

---

## ENV KEYS (OHNE SECRETS)

### Backend (22 Keys)
```
APP_URL, AUTO_RESTORE_ENABLED, DB_NAME, JWT_SECRET*, MONGO_URL*,
POS_CROSSCHECK_THRESHOLD_ABS, POS_CROSSCHECK_THRESHOLD_PCT,
POS_IMAP_FOLDER, POS_IMAP_HOST, POS_IMAP_PASSWORD*, POS_IMAP_PORT,
POS_IMAP_TLS, POS_IMAP_USER, REQUIRE_ATLAS,
SMTP_FROM, SMTP_FROM_NAME, SMTP_HOST, SMTP_PASSWORD*, SMTP_PORT,
SMTP_USER, SMTP_USE_TLS
```
*`*` = Secret, nicht loggen*

### Frontend (1 Key)
```
REACT_APP_BACKEND_URL=https://gastro-widget-fix.preview.emergentagent.com
```

---

## DATENBANK-STATUS REFERENZ

| Collection | Erwarteter Count | Typ |
|------------|------------------|-----|
| users | 10 | Config |
| events | 40+ | Operativ |
| staff_members | 23 | Config |
| tables | 49 | Config |
| opening_hours | 7 | Config |
| reservations | variabel | Operativ |
| areas | 0 (OK) | Config |

---

## SCHNELL-REFERENZ ENDPUNKTE

| Endpoint | Auth | Zweck |
|----------|------|-------|
| `GET /api/health` | ⚪ Public | System-Status |
| `GET /api/public/restaurant-info` | ⚪ Public | Restaurant-Daten |
| `GET /api/public/events` | ⚪ Public | Event-Liste |
| `GET /api/public/email-status` | ⚪ Public | E-Mail Config |
| `GET /api/public/availability` | ⚪ Public | Slot-Verfügbarkeit |
| `GET /internal/seed/status` | ⚪ Internal | Seed-Status |
| `GET /api/smtp/status` | 🔒 Admin | SMTP Details |
| `POST /api/imap/test` | 🔒 Admin | IMAP Test |

---

## DIESER PROMPT GILT FÜR

- Projekt: **gastro-widget-fix** (Carlsburg Cockpit)
- Repository: **carlsburger/GastroCore**
- Branch: **main**
- Umgebung: **Emergent Preview/Deploy**

**Keine anderen Projekte. Keine Umbenennungen. Keine Feature-Entwicklung.**

---

*Dokument erstellt: 2025-01-01 | Version: 1.0*
