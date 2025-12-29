# MODUL 30: MITARBEITER & DIENSTPLAN – IST-STAND ANALYSE
## GastroCore / Carlsburg Cockpit
**Stand: 29.12.2025 | Version: V1.1**

---

# 📋 KURZÜBERBLICK (Executive Summary)

## System-Status
- **Version**: V1.1 (Abwesenheit & Personalakte LIGHT)
- **Status**: LIVE-TESTBEREIT
- **Abnahme**: 29.12.2025

## Architektur
- **Backend**: FastAPI mit MongoDB (Atlas)
- **Frontend**: React SPA + Mitarbeiter-PWA
- **Module**: 4 Backend-Module, 8 Frontend-Seiten

## Hauptfunktionsbereiche
| Bereich | Admin-Cockpit | Mitarbeiter-PWA | Status |
|---------|---------------|-----------------|--------|
| Mitarbeiter-Stammdaten | ✅ CRUD | ❌ Read-only | 🟢 |
| Dienstplan V2 | ✅ Vollzugriff | ✅ Nur eigene | 🟢 |
| Zeiterfassung (Timeclock) | ✅ Admin-Übersicht | ✅ Stempeln | 🟢 |
| Abwesenheiten | ✅ Approve/Reject | ✅ Beantragen | 🟢 |
| Personalakte | ✅ Upload | ✅ Lesen/Bestätigen | 🟢 |
| Schichtmodelle | ✅ CRUD | ❌ | 🟢 |

---

# 🧑‍💼 1. MITARBEITER-MODUL

## 1.1 Backend: staff_module.py (143KB)

### Collections
| Collection | Beschreibung | Felder |
|------------|--------------|--------|
| `staff_members` | Mitarbeiter-Stammdaten | id, first_name, last_name, full_name, email, phone, role, employment_type, active, archived |
| `staff_documents` (Legacy) | Alte Dokumente | id, staff_member_id, category, file_path, notes |
| `work_areas` | Arbeitsbereiche | id, name, description |

### API-Endpunkte (staff_router: /api/staff)
| Endpunkt | Methode | Funktion | Auth |
|----------|---------|----------|------|
| `/members` | GET | Alle Mitarbeiter | Manager |
| `/members` | POST | MA erstellen | Manager |
| `/members/{id}` | GET | Einzelner MA | User |
| `/members/{id}` | PATCH | MA bearbeiten | Manager |
| `/members/{id}` | DELETE | MA archivieren | Admin |
| `/members/{id}/hr-fields` | PATCH | HR-Felder | Admin |
| `/members/{id}/reveal-field` | POST | Feld entschlüsseln | Admin |
| `/members/{id}/completeness` | GET | Vollständigkeit | Manager |
| `/members/{id}/documents` | GET/POST | Dokumente (Legacy) | Manager |
| `/members/{id}/send-welcome` | POST | Willkommens-Email | Admin |
| `/work-areas` | GET/POST/PATCH/DELETE | Arbeitsbereiche | Manager |

### Rollen-System
| Rolle | Code | Berechtigungen |
|-------|------|----------------|
| Admin | `admin` | Vollzugriff |
| Schichtleiter | `schichtleiter` | MA + Schichten verwalten |
| Service | `service` | Nur eigene Daten |
| Mitarbeiter | `mitarbeiter` | Nur eigene Daten |

---

## 1.2 Frontend: Staff.jsx + StaffDetail.jsx

### Staff.jsx (/staff)
**Funktion**: Mitarbeiter-Übersicht mit Liste
**Interaktiv**: Ja (Admin/Schichtleiter)
**Features**:
- Mitarbeiter-Liste mit Filterfunktion
- Status-Badges (aktiv/inaktiv)
- Vollständigkeitsanzeige
- Link zu Detail-Seite
- Neuen MA erstellen

### StaffDetail.jsx (/staff/:id)
**Funktion**: Mitarbeiter-Detailansicht mit 6 Tabs
**Interaktiv**: Ja (rollenbasiert)

| Tab | Inhalt | Admin | Schichtleiter |
|-----|--------|-------|---------------|
| Kontakt | Email, Telefon, Adresse | ✅ Edit | ✅ View |
| Personal/Steuer | SV-Nr, Steuer-ID, Bank | ✅ Edit | ❌ |
| Abwesenheiten | Legacy-Liste | ✅ View | ✅ View |
| Notfall | Notfallkontakt | ✅ Edit | ✅ View |
| Dokumente | Legacy-Uploads | ✅ Upload | ✅ View |
| Personalakte V2 | V1.1 Dokumente | ✅ Upload | ❌ |

---

# 📅 2. DIENSTPLAN-MODUL (Shifts V2)

## 2.1 Backend: shifts_v2_module.py (37KB)

### Collection: shifts
```json
{
  "id": "UUID",
  "date_local": "YYYY-MM-DD",
  "start_time": "HH:MM",
  "end_time": "HH:MM",
  "role": "Service | Küche | Bar | ...",
  "station": "String (optional)",
  "assigned_staff_ids": ["UUID", "UUID"],  // Multi-Assignment!
  "status": "DRAFT | PUBLISHED | CANCELLED",
  "event_mode": "normal | kultur",
  "template_id": "UUID (optional)",
  "notes_admin": "String",
  "notes_staff": "String",
  "archived": false,
  "created_at": "ISO",
  "updated_at": "ISO"
}
```

### Status-Machine
```
DRAFT ──publish──> PUBLISHED ──cancel──> CANCELLED
   │                    │
   └───────────────────────────────────── (delete nur bei DRAFT)
```

### API-Endpunkte (shifts_v2_router: /api/staff/shifts/v2)
| Endpunkt | Methode | Funktion | Auth |
|----------|---------|----------|------|
| `/` | GET | Alle Schichten (Filter) | Manager |
| `/{id}` | GET | Einzelne Schicht | User |
| `/` | POST | Schicht erstellen | Manager |
| `/{id}` | PATCH | Schicht bearbeiten | Manager |
| `/{id}` | DELETE | Schicht löschen (nur DRAFT) | Manager |
| `/{id}/publish` | POST | Veröffentlichen | Manager |
| `/{id}/cancel` | POST | Stornieren | Manager |
| `/{id}/assign` | POST | MA zuweisen | Manager |
| `/{id}/unassign` | POST | MA entfernen | Manager |
| `/{id}/swap` | POST | Tausch (atomar) | Manager |
| `/bulk/publish` | POST | Mehrere veröffentlichen | Manager |
| `/generate-from-templates` | POST | Aus Vorlage generieren | Manager |
| `/migrate-legacy` | POST | Legacy-Migration | Admin |
| `/my` | GET | Eigene Schichten | User |

### Schichtmodelle (shift_templates)
| Endpunkt | Methode | Funktion |
|----------|---------|----------|
| `/shift-templates` | GET/POST | Alle/Neu |
| `/shift-templates/{id}` | GET/PUT/DELETE | CRUD |
| `/shift-templates/apply` | POST | Auf Woche anwenden |

---

## 2.2 Frontend: ShiftsAdmin.jsx + MyShifts.jsx

### ShiftsAdmin.jsx (/shifts-admin)
**Funktion**: Dienstplan V2 - Wochenansicht
**Interaktiv**: Vollständig (Admin/Schichtleiter)
**Features**:
- 7-Tage Wochenansicht
- Schicht erstellen per "+ Hinzufügen"
- Multi-Assignment (mehrere MA pro Schicht)
- Publish/Cancel Buttons
- Tagesdetail-Ansicht
- Aus Vorlage generieren

### MyShifts.jsx (/my-shifts)
**Funktion**: Eigene Schichten (Listenansicht)
**Interaktiv**: Read-only
**Features**:
- Eigene Schichten für 14 Tage
- Status-Anzeige (Heute/Morgen Badge)
- Rolle + Station
- Notizen

### Schedule.jsx (/schedule) - LEGACY
**Funktion**: Alter Dienstplan (deprecated)
**Status**: 🟡 Noch vorhanden, aber Shifts V2 ist Source of Truth

---

# ⏱ 3. ZEITERFASSUNG (Timeclock)

## 3.1 Backend: timeclock_module.py (40KB)

### Collections
| Collection | Beschreibung |
|------------|--------------|
| `time_sessions` | Tages-Sessions pro MA |
| `time_events` | Append-only Audit-Log |

### State-Machine
```
        ┌──────────────────────────────┐
        │            OFF               │
        └──────────────┬───────────────┘
                       │ clock-in
        ┌──────────────▼───────────────┐
        │          WORKING             │◄───┐
        └──────────────┬───────────────┘    │
                       │ break-start    break-end
        ┌──────────────▼───────────────┐    │
        │           BREAK              │────┘
        └──────────────────────────────┘
                       │
                       │ clock-out (NUR aus WORKING!)
        ┌──────────────▼───────────────┐
        │          CLOSED              │
        └──────────────────────────────┘

⚠️ PAUSE STRICT: clock-out während BREAK = 409 BLOCKED
```

### API-Endpunkte (timeclock_router: /api/timeclock)
| Endpunkt | Methode | Funktion | Auth |
|----------|---------|----------|------|
| `/status` | GET | Aktueller Status | User |
| `/today` | GET | Heutige Session | User |
| `/clock-in` | POST | Einstempeln | User |
| `/clock-out` | POST | Ausstempeln | User |
| `/break-start` | POST | Pause starten | User |
| `/break-end` | POST | Pause beenden | User |
| `/history` | GET | Historie | User |
| `/admin/sessions` | GET | Alle Sessions | Manager |
| `/admin/sessions/{id}` | GET/PATCH | Session bearbeiten | Manager |
| `/admin/events` | GET | Alle Events | Manager |
| `/admin/daily-overview` | GET | Tagesübersicht | Manager |

### Business-Logik
- **1 Session pro MA pro Tag** (Europe/Berlin)
- **Auto-Link zu Shift** bei eindeutigem Match
- **Idempotency Keys** für Netzwerk-Resilienz
- **Append-only Events** für Audit-Trail

---

## 3.2 Frontend: EmployeePWA.jsx (/employee)

**Funktion**: Mitarbeiter-App mit 5 Tabs
**Interaktiv**: Vollständig
**Viewport**: Mobile-optimiert (PWA)

| Tab | Icon | Funktion |
|-----|------|----------|
| Home/Status | ⏱ | Quick-Actions (Stempeln) |
| Schichten | 📅 | Eigene Schichten (14 Tage) |
| Zeiten | ⏲ | Tagesübersicht mit Timeline |
| Abwesenheit | 📴 | Antrag stellen/Liste |
| Unterlagen | 📄 | Dokumente + Badge |

### Timeclock UI-States
| State | Anzeige | Buttons |
|-------|---------|---------|
| OFF | "Nicht eingestempelt" | Einstempeln |
| WORKING | "Arbeitet" + Timer | Pause, Ausstempeln |
| BREAK | "In Pause" + Warnung | Pause beenden |
| CLOSED | "Feierabend" + Zeiten | — |

---

# 📴 4. ABWESENHEITEN (V1.1)

## 4.1 Backend: absences_module.py (31KB)

### Collection: staff_absences
```json
{
  "id": "UUID",
  "staff_member_id": "UUID",
  "type": "VACATION | SICK | SPECIAL | OTHER",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "status": "REQUESTED | APPROVED | REJECTED | CANCELLED",
  "notes_employee": "String",
  "notes_admin": "String",
  "created_at": "ISO",
  "updated_at": "ISO"
}
```

### API-Endpunkte
**Mitarbeiter** (absences_router: /api/staff/absences):
| Endpunkt | Methode | Funktion |
|----------|---------|----------|
| `/me` | GET | Eigene Abwesenheiten |
| `/` | POST | Antrag stellen |
| `/{id}/cancel` | POST | Stornieren |

**Admin** (admin_absences_router: /api/admin/absences):
| Endpunkt | Methode | Funktion |
|----------|---------|----------|
| `/` | GET | Alle Abwesenheiten (Filter) |
| `/pending` | GET | Offene Anträge |
| `/by-date/{date}` | GET | Für Tagesübersicht |
| `/{id}/approve` | POST | Genehmigen |
| `/{id}/reject` | POST | Ablehnen (Grund Pflicht) |
| `/{id}/cancel` | POST | Stornieren |

---

## 4.2 Frontend: AbsencesAdmin.jsx (/absences)

**Funktion**: Abwesenheiten verwalten
**Interaktiv**: Vollständig (Admin/Schichtleiter)
**Features**:
- Summary-Karten (Gesamt/Beantragt/Genehmigt/Abgelehnt/Storniert)
- Filter (Status, Typ, Mitarbeiter, Zeitraum)
- Aktionen: Genehmigen, Ablehnen (mit Grund), Stornieren
- Bestätigungsdialoge

---

# 📄 5. PERSONALAKTE (V1.1)

## 5.1 Backend: absences_module.py

### Collections
| Collection | Beschreibung |
|------------|--------------|
| `staff_documents` | Dokumente (V1.1) |
| `staff_document_acknowledgements` | Bestätigungen |

### API-Endpunkte
**Mitarbeiter** (documents_router: /api/staff/documents):
| Endpunkt | Methode | Funktion |
|----------|---------|----------|
| `/me` | GET | Eigene Dokumente |
| `/me/unacknowledged-count` | GET | Für Badge |
| `/{id}/acknowledge` | POST | Bestätigen |
| `/{id}/download` | GET | Herunterladen |

**Admin** (admin_documents_router: /api/admin/staff):
| Endpunkt | Methode | Funktion |
|----------|---------|----------|
| `/{staff_id}/documents` | GET | Liste |
| `/{staff_id}/documents` | POST | Upload (multipart) |
| `/{staff_id}/documents/{id}/download` | GET | Download |
| `/{staff_id}/documents/{id}` | DELETE | Löschen |

### Dokument-Kategorien (fix)
- CONTRACT (Arbeitsvertrag)
- POLICY (Belehrung)
- CERTIFICATE (Bescheinigung)
- OTHER (Sonstiges)

---

## 5.2 Frontend: PersonalakteTab.jsx

**Eingebettet in**: StaffDetail.jsx (Tab "Personalakte V2")
**Interaktiv**: Admin only
**Features**:
- Dokument-Upload mit File-Dialog
- Versionierung automatisch
- Kategorie-Auswahl
- Pflichtdokument-Checkbox
- Acknowledgement-Status Anzeige
- Download + Löschen

---

# 🔐 6. ROLLEN & BERECHTIGUNGEN

## Rollen-Matrix
| Funktion | Admin | Schichtleiter | Service | Mitarbeiter |
|----------|-------|---------------|---------|-------------|
| MA-Liste sehen | ✅ | ✅ | ❌ | ❌ |
| MA erstellen | ✅ | ✅ | ❌ | ❌ |
| MA HR-Felder | ✅ | ❌ | ❌ | ❌ |
| Dienstplan V2 | ✅ | ✅ | ❌ | ❌ |
| Schicht zuweisen | ✅ | ✅ | ❌ | ❌ |
| Eigene Schichten | ✅ | ✅ | ✅ | ✅ |
| Stempeln | ✅ | ✅ | ✅ | ✅ |
| Abwesenheit beantragen | ✅ | ✅ | ✅ | ✅ |
| Abwesenheit genehmigen | ✅ | ✅ | ❌ | ❌ |
| Dokumente hochladen | ✅ | ❌ | ❌ | ❌ |
| Dokumente bestätigen | ✅ | ✅ | ✅ | ✅ |

## Auth-Guards (Backend)
- `get_current_user` - Authentifizierter User
- `require_manager` - Admin oder Schichtleiter
- `require_admin` - Nur Admin

## Protected Routes (Frontend)
```jsx
<ProtectedRoute roles={["admin", "schichtleiter"]}>
  <Staff />
  <ShiftsAdmin />
  <AbsencesAdmin />
</ProtectedRoute>
```

---

# 🟢🟡🔴 BEWERTUNG JE FUNKTIONSBLOCK

## 🟢 EXISTIERT STABIL – NICHT NEU BAUEN
| Bereich | Komponenten |
|---------|-------------|
| Mitarbeiter-CRUD | staff_module.py, Staff.jsx, StaffDetail.jsx |
| Shifts V2 Engine | shifts_v2_module.py, Multi-Assignment |
| Timeclock State Machine | timeclock_module.py, Pause Strict |
| Abwesenheiten-Workflow | absences_module.py, Status-Machine |
| Personalakte V1.1 | staff_documents, Acknowledgements |
| Rollen-System | Auth-Guards, ProtectedRoute |

## 🟡 EXISTIERT – ERWEITERUNG MÖGLICH
| Bereich | Vorschlag |
|---------|-----------|
| Dienstplan-Ansicht | Monatsansicht hinzufügen |
| Timeclock | Overtime-Warnung |
| Abwesenheiten | Urlaubskontingent-Tracking |
| Personalakte | Digitale Signatur (V1.2+) |
| Export | Lohn-Export erweitern |

## 🔴 EXISTIERT NICHT – KANN NEU ENTWICKELT WERDEN
| Bereich | Beschreibung |
|---------|--------------|
| Schicht-Anfragen | MA kann Schicht anfragen |
| Schicht-Bestätigung | MA muss Schicht bestätigen |
| Verfügbarkeits-Eingabe | MA gibt Verfügbarkeit an |
| Automatische Planung | KI-gestützte Schichtplanung |
| Payroll-Integration | Lohnabrechnung |
| Krankmeldungs-Upload | AU-Scan hochladen |

---

# ⚠️ PARALLELENTWICKLUNGS-WARNUNG

## 🚫 NICHT PARALLEL BAUEN
1. **Keine zweite Mitarbeiter-API** - staff_module.py nutzen
2. **Keine alternative Shift-Logik** - shifts_v2_module.py ist Source of Truth
3. **Keine zweite Timeclock** - State-Machine ist fix
4. **Keine separate Abwesenheits-Verwaltung** - absences_module.py nutzen
5. **Kein zweites Dokument-System** - staff_documents Collection nutzen

## ⚠️ ERWEITERN, NICHT ERSETZEN
1. **Shift-Status** → ShiftStatusV2 Enum erweitern, nicht ersetzen
2. **Timeclock States** → TimeSessionState Enum erweitern
3. **Abwesenheits-Typen** → AbsenceType Enum erweitern
4. **Dokument-Kategorien** → DocumentCategory Enum erweitern
5. **Rollen** → roles Array in User erweitern

## 📍 KOORDINATION ERFORDERLICH
| Änderung | Betroffene Files |
|----------|------------------|
| Neuer Shift-Status | shifts_v2_module.py, ShiftsAdmin.jsx |
| Neuer Abwesenheits-Typ | absences_module.py, EmployeePWA.jsx, AbsencesAdmin.jsx |
| Neue Rolle | server.py (auth), Layout.jsx (nav), App.js (routes) |
| Neues MA-Feld | staff_module.py, StaffDetail.jsx |

---

# 📊 IST-STAND MATRIX

| Bereich | Backend | Frontend Admin | Frontend PWA | API-Routen |
|---------|---------|----------------|--------------|------------|
| **Mitarbeiter** | staff_module.py | Staff.jsx, StaffDetail.jsx | — | /api/staff/* |
| **Shifts V2** | shifts_v2_module.py | ShiftsAdmin.jsx | EmployeePWA (Tab) | /api/staff/shifts/v2/* |
| **Timeclock** | timeclock_module.py | (daily-overview) | EmployeePWA (Home) | /api/timeclock/* |
| **Abwesenheit** | absences_module.py | AbsencesAdmin.jsx | EmployeePWA (Tab) | /api/staff/absences/*, /api/admin/absences/* |
| **Personalakte** | absences_module.py | PersonalakteTab.jsx | EmployeePWA (Tab) | /api/staff/documents/*, /api/admin/staff/*/documents/* |
| **Templates** | staff_module.py | ShiftTemplates.jsx | — | /api/staff/shift-templates/* |

---

# 📌 FAZIT

**Modul 30 ist vollständig und produktionsreif (V1.1).**

### Umgesetzte Features
- ✅ Mitarbeiter-Stammdaten mit HR-Feldern
- ✅ Dienstplan V2 mit Multi-Assignment
- ✅ Timeclock mit Pause Strict
- ✅ Abwesenheiten mit Genehmigungsworkflow
- ✅ Personalakte mit Acknowledgement
- ✅ Rollenbasierte Zugriffskontrolle

### Empfehlung
Erweiterungen nur auf Basis des bestehenden Systems.
Keine Parallelentwicklung starten.
Modul 30 V1.1 kann eingefroren werden.

---

*Dokumentiert am 29.12.2025*
*Analyst: Emergent AI*
