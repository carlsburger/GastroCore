# MASTER SNAPSHOT - Carlsburg Cockpit
**Erstellt:** 2025-01-01 12:45 UTC  
**System:** gastro-widget-fix (Emergent)

---

## System Fingerprint

| Key | Value |
|-----|-------|
| **Git Branch** | `main` |
| **Git Commit** | `5b142e107993dd1de0f7d5c55b71fa838637db2e` |
| **Commit Short** | `5b142e1` |
| **Commit Date** | 2026-01-01 13:54:19 UTC |
| **Build Hash** | Kein Production Build (Dev Server) |
| **Snapshot Timestamp** | 2025-01-01T12:45:00Z |

---

## Service Status

| Service | Status | Port | PID |
|---------|--------|------|-----|
| Backend (FastAPI) | ✅ RUNNING | 8001 | 1143 |
| Frontend (React) | ✅ RUNNING | 3000 | 50 |
| MongoDB | ✅ RUNNING | 27017 | 52 |
| nginx-code-proxy | ✅ RUNNING | - | 47 |

---

## Aktive URLs

| Typ | URL |
|-----|-----|
| Preview | `https://gastro-widget-fix.preview.emergentagent.com` |
| API | `https://gastro-widget-fix.preview.emergentagent.com/api` |
| Booking Widget | `https://gastro-widget-fix.preview.emergentagent.com/book` |
| Login | `https://gastro-widget-fix.preview.emergentagent.com/login` |

---

## ENV Keys (Runtime)

### Backend (.env)
```
APP_URL
AUTO_RESTORE_ENABLED
DB_NAME
JWT_SECRET                    # SECRET
MONGO_URL                     # SECRET
POS_CROSSCHECK_THRESHOLD_ABS
POS_CROSSCHECK_THRESHOLD_PCT
POS_IMAP_FOLDER
POS_IMAP_HOST
POS_IMAP_PASSWORD             # SECRET - <SET_IN_EMERGENT>
POS_IMAP_PORT
POS_IMAP_TLS
POS_IMAP_USER
REQUIRE_ATLAS
SMTP_FROM
SMTP_FROM_NAME
SMTP_HOST
SMTP_PASSWORD                 # SECRET - <SET_IN_EMERGENT>
SMTP_PORT
SMTP_USER
SMTP_USE_TLS
```

### Frontend (.env)
```
REACT_APP_BACKEND_URL
```

---

## Datenbank Status

| Collection | Count | Status |
|------------|-------|--------|
| users | 10 | ✅ OK |
| areas | 0 | ⚠️ Leer |
| opening_hours | 7 | ✅ OK |
| events | 40 | ✅ OK |
| staff_members | 23 | ✅ OK |
| tables | 49 | ✅ OK |
| reservations | ? | ✅ Operativ |

---

## Seed System

| Komponente | Pfad | Status |
|------------|------|--------|
| Tables | `/app/seed/tables.xlsx` | ✅ Vorhanden |
| Combinations | `/app/seed/table_combinations.xlsx` | ✅ Vorhanden |
| Staff | `/app/seed/staff.xlsx` | ✅ Vorhanden |
| Shift Templates | `/app/seed/shift_templates_master.json` | ✅ Vorhanden |
| Seed Script | `/app/scripts/seed_data.sh` | ✅ Vorhanden |
| Backup Script | `/app/scripts/make_backup.sh` | ✅ Vorhanden |

---

## E-Mail Konfiguration

| Service | Host | Port | Configured |
|---------|------|------|------------|
| SMTP | smtp.ionos.de | 465 | ✅ true |
| IMAP | imap.ionos.de | 993 | ✅ true |

**⚠️ Passwörter:** Sind Platzhalter. Müssen im Emergent Dashboard gesetzt werden.

---

## Versionen

| Package | Version |
|---------|---------|
| FastAPI | 0.110.1 |
| Motor | 3.3.1 |
| Pydantic | 2.12.5 |
| React | 19.0.0 |
| GastroCore | 3.0.0 |

---

## Checksums (für Drift-Erkennung)

```
tables.xlsx:              MD5 siehe Datei
table_combinations.xlsx:  MD5 siehe Datei
.env (backend):           22 Keys
.env (frontend):          1 Key
```

---

**Dieser Snapshot repräsentiert den stabilen Referenzzustand.**
