# GastroCore - Sprint 1 Requirements & Documentation

## Original Problem Statement
Modulare Gastro-App Sprint 1 für ein produktionsreifes Core-System + Service-Terminal-Grundlage.

## Architecture Review Complete ✓

### 1. Architektur-Eichung ✓
- **Modularer Monolith** implementiert:
  - `/app/backend/core/` - Auth, Audit, Config, Validators, Exceptions, Models
  - `/app/backend/server.py` - API Endpoints (Reservations, Areas, Users, Settings)
- **Klare Modulgrenzen** und Zuständigkeiten
- **Keine Duplikate** oder Hardcodierungen

### 2. RBAC Hart Gemacht ✓
- **Admin**: Vollzugriff auf alle Endpoints
- **Schichtleiter**: Service-Terminal + Reservierungen (kein Zugriff auf /users, /settings, /audit-logs)
- **Mitarbeiter**: KEIN Backoffice-Zugriff (403 auf /reservations)
- **Serverseitige Prüfung** in ALLEN Endpoints
- **Saubere Fehlermeldungen** mit error_code

### 3. Audit-Log Vollständigkeit ✓
- **JEDE mutierende Aktion** erzeugt Audit-Eintrag
- Felder: actor_id, actor_email, entity, entity_id, action, before, after, timestamp
- Aktionen: create, update, archive, status_change, password_change, login, cancel_by_guest

### 4. Status-Konsistenz ✓
- **Strenger Workflow** definiert in `core/config.py`:
  - neu → bestaetigt, storniert, no_show
  - bestaetigt → angekommen, storniert, no_show
  - angekommen → abgeschlossen, no_show
  - Terminal-Status: abgeschlossen, no_show, storniert
- **Serverseitige Validierung** in `core/validators.py`
- **Keine inkonsistenten Zustände** möglich

### 5. Konfiguration statt Code ✓
- **Settings in `core/config.py`**:
  - Status-Übergänge (STATUS_TRANSITIONS)
  - Schwellwerte (MAX_PARTY_SIZE, MIN_PARTY_SIZE)
  - Reservierungsvoraus (RESERVATION_ADVANCE_DAYS)
- **Runtime-Config** via Settings-API änderbar

### 6. Service-Terminal Realitäts-Check ✓
- **1-Klick Aktionen**: Quick-Action Buttons direkt in der Liste
- **Große Klickflächen**: h-12, min-w-[140px]
- **Klare Statusfarben**: Gelb (Neu), Blau (Bestätigt), Grün (Angekommen), Grau (Storniert), Rot (No-Show)
- **Mobile-optimiert**: Responsive Layout, große Touch-Targets

### 7. Fehlerhandling & Robustheit ✓
- **Zentrale Exception-Klassen** in `core/exceptions.py`
- **Globaler Exception-Handler** für konsistente Fehlermeldungen
- **Strukturierte Error-Response**: `{detail, error_code, success: false}`
- **Keine Silent Failures**

### 8. Performance-Basics ✓
- **Pagination**: `limit` Parameter auf allen Listen-Endpoints
- **Indexed Queries**: Optimierte MongoDB-Abfragen
- **Background Tasks**: E-Mail-Versand nicht blockierend

### Test Users
| Rolle | E-Mail | Passwort |
|-------|--------|----------|
| Admin | admin@gastrocore.de | Admin123! |
| Schichtleiter | schichtleiter@gastrocore.de | Schicht123! |
| Mitarbeiter | mitarbeiter@gastrocore.de | Mitarbeiter123! |

**Hinweis**: Beim ersten Login muss das Passwort geändert werden!

---

## API Endpoints

### Auth
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Current User
- `POST /api/auth/change-password` - Password Change

### Users (Admin only)
- `GET /api/users` - List Users
- `POST /api/users` - Create User
- `DELETE /api/users/{id}` - Archive User

### Areas
- `GET /api/areas` - List Areas (all authenticated)
- `POST /api/areas` - Create Area (Admin)
- `PUT /api/areas/{id}` - Update Area (Admin)
- `DELETE /api/areas/{id}` - Archive Area (Admin)

### Reservations
- `GET /api/reservations` - List (with filters)
- `GET /api/reservations/{id}` - Get One
- `POST /api/reservations` - Create (Admin/Schichtleiter) - **sendet Bestätigungs-E-Mail**
- `PUT /api/reservations/{id}` - Update (Admin/Schichtleiter)
- `PATCH /api/reservations/{id}/status` - Status Change (Admin/Schichtleiter) - **sendet E-Mail bei Bestätigung**
- `DELETE /api/reservations/{id}` - Archive (Admin/Schichtleiter)
- `POST /api/reservations/{id}/cancel?token=...` - **Öffentliche Stornierung** (via E-Mail-Link)
- `POST /api/reservations/send-reminders` - Erinnerungen senden (Admin, für Cron)

### Audit Log (Admin only)
- `GET /api/audit-logs` - List with filters

### Settings (Admin only)
- `GET /api/settings` - List Settings
- `POST /api/settings` - Create/Update Setting

---

## SMTP Konfiguration

Die SMTP-Zugangsdaten sind in `/app/backend/.env` konfiguriert:

```
SMTP_HOST=smtp.ionos.de
SMTP_PORT=465
SMTP_USER=reservierung@carlsburg.de
SMTP_PASSWORD=<ihr-passwort>
SMTP_FROM_EMAIL=reservierung@carlsburg.de
SMTP_FROM_NAME=Carlsburg Restaurant
```

**Hinweis**: Bei IONOS muss ggf. die E-Mail-Adresse erst im Webmail aktiviert werden und das korrekte Passwort verwendet werden.

---

## Cron-Job für Erinnerungen

Um tägliche Erinnerungs-E-Mails zu versenden, kann ein Cron-Job eingerichtet werden:

```bash
# Täglich um 10:00 Uhr Erinnerungen für morgige Reservierungen senden
0 10 * * * curl -X POST "https://ihre-domain.de/api/reservations/send-reminders" -H "Authorization: Bearer <admin-token>"
```

---

## Next Tasks (Sprint 2+)

### High Priority
- [ ] SMTP-Credentials korrigieren (aktuell: "Authentication credentials invalid")
- [ ] Einstellungen-Page für Key/Value Settings (Admin)
- [ ] Reservierung bearbeiten (Edit Dialog)

### Medium Priority
- [ ] Datumsbereich-Filter für Reservierungen
- [ ] Export-Funktion (CSV/PDF)
- [ ] Druckansicht für Reservierungsliste
- [ ] Gäste-Datenbank (wiederkehrende Gäste)

### Low Priority
- [ ] Tischplan-Visualisierung
- [ ] Multi-Language Support (EN, FR)
- [ ] Dark Mode
- [ ] Mobile App (PWA)
- [ ] Analytics Dashboard

---

## Tech Stack
- **Backend**: FastAPI, Motor (async MongoDB), PyJWT, bcrypt, smtplib
- **Frontend**: React 19, React Router, Shadcn/UI, Tailwind CSS, Axios
- **Database**: MongoDB
- **Auth**: JWT Tokens (24h expiry)
- **E-Mail**: SMTP (IONOS)
