# GastroCore - Sprint 1 Requirements & Documentation

## Original Problem Statement
Modulare Gastro-App Sprint 1 für ein produktionsreifes Core-System + Service-Terminal-Grundlage.

### Anforderungen
1. **Auth & Rollen**
   - Rollen: Admin, Schichtleiter, Mitarbeiter
   - RBAC auf API-Ebene
   - Admin: Vollzugriff
   - Schichtleiter: Zugriff auf Service-Terminal + Reservierungen
   - Mitarbeiter: kein Backoffice-Zugriff

2. **Audit-Log (Pflicht)**
   - Jede mutierende Aktion erzeugt Audit-Eintrag
   - Felder: actor, entity, entity_id, before/after diff, timestamp

3. **Stammdaten**
   - Bereiche anlegen (z.B. Terrasse, Saal, Wintergarten)
   - Einstellungen als Key/Value (vorbereitet)

4. **Service-Terminal (UI)**
   - Tagesliste Reservierungen (Filter: Status, Bereich)
   - Statuswechsel: neu → bestätigt → angekommen → abgeschlossen → no-show
   - Suche nach Name/Telefon
   - Nur Schichtleiter/Admin darf bearbeiten

5. **E-Mail-Benachrichtigungen** (neu)
   - Bestätigung bei neuer Reservierung
   - Erinnerung 24h vorher (Cron-Endpoint)
   - Stornierungslink in jeder E-Mail
   - Stornierungsbestätigung

### User Choices
- **Auth**: JWT-basierte Custom Auth
- **Design**: Hell/Beige Theme mit Tokens:
  - Primary: #00280b
  - Footer: #002f02
  - Accent: #ffed00
  - Background: #fafbed
  - Container: #f3f6de
  - Fonts: Lato (Body+H4), Playfair Display (H1–H3, H5–H6)
- **Initiale Benutzer**: Test-User pro Rolle mit Passwortwechsel beim ersten Login
- **Sprache**: i18n vorbereitet, Default Deutsch
- **Echtzeit**: Kein WebSocket, Polling/Refresh reicht
- **E-Mail**: IONOS SMTP (reservierung@carlsburg.de)

---

## Architecture Tasks Done (Sprint 1 + E-Mail)

### Backend (FastAPI + MongoDB)
- [x] JWT Authentication mit Rollen
- [x] RBAC Middleware für alle Endpoints
- [x] User Model mit must_change_password Flag
- [x] Reservation Model mit Status-Workflow
- [x] Area Model für Bereiche
- [x] Setting Model für Key/Value-Einstellungen
- [x] AuditLog für alle Mutationen
- [x] Seed-Endpoint für Test-Daten
- [x] Archivierung statt Löschen
- [x] E-Mail Service mit SMTP (IONOS)
- [x] HTML E-Mail Templates (Carlsburg Branding)
- [x] Bestätigungs-E-Mail bei Reservierung
- [x] Erinnerungs-Endpoint für Cron-Jobs
- [x] Stornierungslink mit Token-Verifizierung
- [x] Öffentlicher Stornierungsendpoint

### Frontend (React + Shadcn/UI)
- [x] Login Page mit Split-Screen Design
- [x] Password Change Page
- [x] Dashboard/Service-Terminal
- [x] Areas Management (Admin)
- [x] Users Management (Admin)
- [x] Audit-Log Viewer (Admin)
- [x] Protected Routes mit Role-Check
- [x] i18n Setup (Deutsch)
- [x] Custom Theme (Beige/Grün)
- [x] Stornierungsseite (öffentlich)
- [x] Status "Storniert" Support

### E-Mail Templates
- Bestätigung: Elegantes Design mit Reservierungsdetails + Stornierungslink
- Erinnerung: "Bis morgen!" mit Reservierungsdetails + Stornierungslink
- Stornierung: Bestätigung der erfolgreichen Stornierung

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
