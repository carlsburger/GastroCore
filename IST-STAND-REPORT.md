# 🔍 CARLSBURG COCKPIT / GASTROCORE – AUDIT & ROADMAP
**Datum:** 2025-12-22 13:34 UTC  
**Build-ID:** `1245f44b-20251222`  
**Commit:** `1245f44b587bcb198e10ed7681ed6c2f4a8999e9`  
**Branch:** `main`  
**Version:** 3.0.0  

---

## 1️⃣ SESSION INTEGRITY CHECK

### A) Git / Repo
| Prüfpunkt | Wert |
|-----------|------|
| Repo-Pfad | `/app` |
| Branch | `main` |
| Commit Hash | `1245f44b587bcb198e10ed7681ed6c2f4a8999e9` |
| git status | ✅ Clean (nur yarn.lock untracked) |

### /api/version
```json
{
  "build_id": "1245f44b-20251222",
  "health_version": "3.0.0",
  "modules": {
    "core": true, "reservations": true, "tables": true,
    "events": true, "payments": true, "staff": true,
    "schedules": true, "taxoffice": true, "loyalty": true,
    "marketing": true, "ai": true
  }
}
```

### /api/health
```json
{"status": "healthy", "database": "connected", "version": "3.0.0"}
```

---

### B) Dateiliste

#### Backend (12 Module + Core)
| Datei | LOC | Beschreibung |
|-------|-----|--------------|
| `server.py` | 2.247 | Core, Auth, Reservierungen |
| `staff_module.py` | 1.871 | Mitarbeiter + Dienstplan |
| `loyalty_module.py` | 1.106 | Kundenbindung |
| `reservation_config_module.py` | 1.081 | Reservierungsregeln |
| `table_module.py` | 1.021 | Tische + Kombinationen |
| `payment_module.py` | 962 | Stripe |
| `events_module.py` | 944 | Events |
| `ai_assistant.py` | 921 | KI |
| `taxoffice_module.py` | 889 | Exporte |
| `marketing_module.py` | 875 | Kampagnen |
| `opening_hours_module.py` | 786 | Öffnungszeiten |
| `backup_module.py` | 438 | **NEU** Backup/Export |
| **TOTAL** | **16.332** | |

#### Frontend (37 Seiten)
| Seite | LOC | Beschreibung |
|-------|-----|--------------|
| `TablePlan.jsx` | 1.182 | Grafischer Tischplan |
| `ServiceTerminal.jsx` | 1.134 | Service-Ansicht |
| `StaffDetail.jsx` | 1.076 | Mitarbeiter-Details |
| `Dashboard.jsx` | 1.063 | Haupt-Dashboard |
| `AIAssistant.jsx` | 1.034 | KI-Chat |
| `Marketing.jsx` | 973 | Kampagnen |
| `OpeningHoursAdmin.jsx` | 949 | Öffnungszeiten |
| `ReservationConfig.jsx` | 743 | Regeln |
| `Schedule.jsx` | 741 | Dienstplan |
| `BackupExport.jsx` | ~400 | **NEU** Backup |
| ... (27 weitere) | ~8.073 | |
| **TOTAL** | **~18.768** | |

---

### C) DB Check – Collection Counts

| Collection | Count | Status |
|------------|-------|--------|
| `users` | 1 | ✅ Admin vorhanden |
| `staff_members` | 12 | ✅ Importiert |
| `work_areas` | 3 | ✅ Service/Küche/Bar |
| `tables` | 46 | ✅ Vollständig |
| `events` | 11 | ✅ Von Website |
| `actions` | 13 | ✅ Von Website |
| `settings` | 6 | ✅ Grundkonfig |
| `reminder_rules` | 2 | ✅ |
| `audit_logs` | 9 | ✅ |
| `schedules` | 0 | ⚠️ on-demand |
| `shifts` | 0 | ⚠️ on-demand |
| `reservations` | 0 | ⚠️ on-demand |
| `guests` | 0 | ⚠️ on-demand |
| `opening_hours_periods` | 0 | ⚠️ on-demand |
| `closures` | 0 | ⚠️ on-demand |
| `table_combinations` | 0 | ⚠️ on-demand |
| `reservation_config` | 0 | ⚠️ on-demand |

---

## 2️⃣ IST-STAND-REPORT

### A) Module-Status

| Modul | Status | Endpoints | UI | Bemerkung |
|-------|--------|-----------|-----|-----------|
| **Core/Auth** | ✅ Fertig | Login, Users, Roles | ✅ | 3-Rollen-System |
| **Reservierungen** | ⚠️ Teilweise | CRUD vorhanden | ✅ | Tisch-Zuweisung manuell |
| **Tischplan** | ✅ Fertig | Tables, Combinations | ✅ | 46 Tische importiert |
| **Service-Terminal** | ✅ Fertig | - | ✅ | Touch-optimiert |
| **Events & Aktionen** | ✅ Fertig | CRUD | ✅ | 24 importiert |
| **Payments** | ⚠️ Teilweise | Stripe vorhanden | ✅ | Test-Key aktiv |
| **Staff** | ✅ Fertig | 34 Endpoints | ✅ | 12 MA importiert |
| **Schedules/Dienstplan** | ⚠️ Teilweise | CRUD vorhanden | ⚠️ | UX-Probleme |
| **TaxOffice** | ✅ Fertig | Exports | ✅ | PDF/CSV |
| **Backup/Export** | ✅ **NEU** | 4 Endpoints | ✅ | XLSX/JSON |
| **Loyalty** | ⚠️ Teilweise | Endpoints | ✅ | Keine Daten |
| **Marketing** | ⚠️ Teilweise | Endpoints | ✅ | SMTP fehlt |
| **AI** | ⚠️ Teilweise | Chat | ✅ | API-Key fehlt |

---

### B) Was läuft gut? (Top 5)

1. **Stammdaten vollständig** ✅
   - 12 Mitarbeiter importiert (aus Excel)
   - 46 Tische mit korrekten Bereichen/Subbereichen
   - 3 Arbeitsbereiche (Service, Küche, Bar)

2. **Events & Aktionen** ✅
   - 11 Veranstaltungen + 13 Aktionen von Website gescraped
   - Alle Termine 2026 erfasst
   - Menü-Aktionen mit Optionen

3. **Backup-System** ✅ (NEU)
   - XLSX-Export (Staff + Tables)
   - JSON-Export (Events/Actions)
   - Server-Backup in /app/backups/
   - Sensible Daten maskiert

4. **Auth & Rollen** ✅
   - Admin/Schichtleiter/Mitarbeiter
   - Route-Protection funktioniert
   - Token-basierte Auth stabil

5. **Tischplan-Backend** ✅
   - Alle 46 Tische mit Kombinierbarkeit
   - Saal/Wintergarten/Terrasse korrekt
   - API liefert vollständige Daten

---

### C) Risiken & Probleme (Top 10)

| # | Problem | Impact | Ursache |
|---|---------|--------|---------|
| 1 | **Dienstplan: Shift-Dialog öffnet nicht** | 🔴 Hoch | Click-Handler in Schedule.jsx |
| 2 | **Öffnungszeiten nicht konfiguriert** | 🔴 Hoch | Keine Perioden in DB |
| 3 | **Keine Schichtarten-Konfiguration** | 🟡 Mittel | Collection fehlt |
| 4 | **SMTP nicht konfiguriert** | 🟡 Mittel | Env-Vars fehlen |
| 5 | **KI ohne API-Key** | 🟡 Mittel | OpenAI-Key fehlt |
| 6 | **Dienstplan: Nur KW-Navigation** | 🟡 Mittel | UX-Entscheidung |
| 7 | **Export-Buttons nicht sichtbar** | 🟡 Mittel | Conditional Rendering |
| 8 | **Reservierungs-Slots fehlen** | 🟡 Mittel | reservation_config leer |
| 9 | **Tischkombinationen ungetestet** | 🟢 Niedrig | Keine Kombinationen angelegt |
| 10 | **MyShifts zeigt falsche KW** | 🟢 Niedrig | Week-Calc Bug |

---

### D) Nacharbeit erforderlich

1. **Shift-Dialog fixen** → `Schedule.jsx` Click-Handler debuggen
2. **Öffnungszeiten anlegen** → Mindestens 1 Periode in DB
3. **Schichtarten-Collection** → Backend-Endpoint + Admin-UI
4. **Kalender-Navigation** → Datum-Picker statt nur KW
5. **SMTP konfigurieren** → Env-Vars im Deployment
6. **Reservierungs-Slots** → Default-Config anlegen
7. **Export-Buttons** → Conditional entfernen

---

## 3️⃣ ROADMAP – Praktische Reihenfolge

### Sprint 6: Dienstplan Stabilisierung (1 Woche)
**Ziel:** Dienstplan produktionsreif
- [ ] Fix: Shift-Dialog Click-Handler
- [ ] Export-Buttons immer sichtbar
- [ ] Schichtarten-Collection + UI
- [ ] Kalender-Navigation verbessern
- [ ] Test mit echten Mitarbeitern

### Sprint 7: Öffnungszeiten & Reservierung (1 Woche)
**Ziel:** Reservierungssystem aktivieren
- [ ] Öffnungszeiten-Perioden anlegen
- [ ] Reservierungs-Slots konfigurieren
- [ ] Sperrtage (Feiertage) eintragen
- [ ] Booking-Widget testen

### Sprint 8: Tischzuweisung & Service-Flow (1-2 Wochen)
**Ziel:** End-to-End Reservierung → Tisch
- [ ] Auto-Assign Logik implementieren
- [ ] Service-Terminal: Tisch-Anzeige
- [ ] Belegungsübersicht pro Slot
- [ ] Walk-in Flow testen

### Sprint 9: E-Mail & Kommunikation (1 Woche)
**Ziel:** Gäste automatisch informieren
- [ ] SMTP konfigurieren
- [ ] E-Mail-Templates anpassen
- [ ] Reminder-System aktivieren
- [ ] Bestätigungs-Mails testen

### Sprint 10: KI-Integration (Optional)
**Ziel:** Assistenz-Funktionen (nur nach Stabilisierung)
- [ ] OpenAI-Key einbinden
- [ ] Natürliche Sprache für Suche
- [ ] Empfehlungen für Tischplanung

**Begründung:**
1. Dienstplan zuerst → täglich im Einsatz
2. Öffnungszeiten vor Reservierung → Grundlage
3. Tischzuweisung → Kern-Feature
4. E-Mail danach → Nice-to-have
5. KI ganz am Ende → nur sinnvoll mit Daten

---

## 4️⃣ DIENSTPLAN – DEEP DIVE

### A) Ist-Stand

**Backend-Endpoints (staff_module.py):**
```
GET    /api/staff/schedules          – Liste
POST   /api/staff/schedules          – Erstellen
PATCH  /api/staff/schedules/{id}     – Aktualisieren
POST   /api/staff/schedules/{id}/publish  – Veröffentlichen
POST   /api/staff/schedules/{id}/copy     – Kopieren
GET    /api/staff/shifts             – Schichten filtern
POST   /api/staff/shifts             – Schicht erstellen
PATCH  /api/staff/shifts/{id}        – Bearbeiten
DELETE /api/staff/shifts/{id}        – Löschen
GET    /api/staff/my-shifts          – MA-Ansicht
GET    /api/staff/export/schedule/{id}/pdf
GET    /api/staff/export/shifts/csv
```

**Collections:**
- `schedules` – Wochenpläne (year, week, status) → **0 Einträge**
- `shifts` – Schichten → **0 Einträge**
- `work_areas` – Bereiche → **3 Einträge**
- `staff_members` – Mitarbeiter → **12 Einträge**

**UI-Seiten:**
- `Schedule.jsx` (741 LOC) – Manager-Ansicht
- `MyShifts.jsx` (215 LOC) – MA-Ansicht

**Konflikt-Erkennung:** ✅ Implementiert
- Doppelbelegung (gleicher MA, gleicher Tag)
- Ruhezeit (11h zwischen Schichten)

---

### B) Fehlende Konfiguration

#### 1) Schichtarten (FEHLT)

**Aktuell hardcoded:**
```javascript
const SHIFT_ROLES = {
  service: { label: "Service", color: "#10b981" },
  schichtleiter: { label: "Schichtleiter", color: "#f59e0b" },
  kueche: { label: "Küche", color: "#f97316" },
  bar: { label: "Bar", color: "#8b5cf6" },
  aushilfe: { label: "Aushilfe", color: "#6b7280" },
};
```

**Benötigt:** Collection `shift_types`
```json
{
  "id": "uuid",
  "name": "Frühdienst Service",
  "short_name": "FD-S",
  "color": "#10b981",
  "default_start": "10:00",
  "default_end": "16:00",
  "area": "service",
  "break_minutes": 30,
  "active": true
}
```

#### 2) Dienstplan-Ansicht (UX-Probleme)

**Aktuell:**
- Nur KW-Navigation (← →)
- Kein Datum-Picker
- "Heute" nicht markiert

**Anforderung:**
```
┌─────────────────────────────────────────────────┐
│  ← Dezember 2025 →   [Heute] [Monat wählen]     │
│  Mo  Di  Mi  Do  Fr  Sa  So                     │
│  22  23  24  25  26  27  28  ← aktuelle Woche   │
├─────────────────────────────────────────────────┤
│        Mo    Di    Mi    Do    Fr    Sa    So   │
│ Service │     │     │     │     │     │     │   │
│ Küche   │     │     │     │     │     │     │   │
│ Bar     │     │     │     │     │     │     │   │
└─────────────────────────────────────────────────┘
```

**Empfehlung Layout:** 
- Spalten = Tage (Mo-So)
- Zeilen = Bereiche
- Innerhalb: MA-Karten mit Zeiten

---

### C) Quick Win vs. Sauberer Umbau

#### Quick Win (nur Frontend):
1. Shift-Dialog Click-Handler fixen
2. "Heute" markieren (CSS-Klasse)
3. Datum (DD.MM.) neben KW anzeigen
4. Export-Buttons immer sichtbar

#### Sauberer Umbau (additive Endpoints):
1. `POST /api/staff/shift-types` – Schichtarten CRUD
2. `GET /api/staff/shift-types`
3. UI-Seite `/admin/settings/shift-types`
4. Schedule.jsx: Schichtarten aus API laden

---

### D) To-Do Liste (12 Punkte)

| # | Aufgabe | Typ | Priorität |
|---|---------|-----|-----------|
| 1 | Shift-Dialog Click-Handler fixen | Bug | 🔴 |
| 2 | Export-Buttons immer sichtbar | Bug | 🔴 |
| 3 | "Heute" im Kalender markieren | UX | 🟡 |
| 4 | Datum (DD.MM.) neben KW | UX | 🟡 |
| 5 | Collection `shift_types` anlegen | Backend | 🟡 |
| 6 | CRUD-Endpoints für Schichtarten | Backend | 🟡 |
| 7 | UI-Seite Schichtarten-Admin | Frontend | 🟡 |
| 8 | Shift-Dialog: Schichtart-Dropdown | Frontend | 🟡 |
| 9 | Kalender-Widget für Navigation | Frontend | 🟢 |
| 10 | Monat-Schnellwahl | Frontend | 🟢 |
| 11 | 2-Jahres-Navigation | Frontend | 🟢 |
| 12 | Test: Vollständiger Workflow | Test | 🔴 |

### Testliste

| Test | Beschreibung | Voraussetzung |
|------|--------------|---------------|
| T1 | Plan erstellen (neue Woche) | MA vorhanden ✅ |
| T2 | Shift hinzufügen (Dialog) | Plan existiert |
| T3 | Shift speichern | T2 |
| T4 | Konflikt: Doppelbelegung | 2 Shifts |
| T5 | Konflikt: Ruhezeit | Schicht 23:00 + 06:00 |
| T6 | Shift bearbeiten | Shift existiert |
| T7 | Shift löschen | Shift existiert |
| T8 | Plan veröffentlichen | Status = entwurf |
| T9 | Woche kopieren | Veröffentlichter Plan |
| T10 | PDF-Export | Plan mit Shifts |
| T11 | CSV-Export | Plan mit Shifts |
| T12 | MyShifts anzeigen | Als MA einloggen |

---

## 5️⃣ NEXT STEP EMPFEHLUNG

```
FOKUS: Sprint 6 – Dienstplan Stabilisierung

1. SOFORT: Shift-Dialog Bug fixen (Schedule.jsx)
   → Ohne Dialog kein Test möglich

2. DANN: Öffnungszeiten anlegen
   → Mindestens 1 Periode (Mo-So, 11-22 Uhr)
   → Sperrtage: Heiligabend, Silvester

3. PARALLEL: Schichtarten-Konzept finalisieren
   → Schema bestätigen lassen
   → UI-Mockup erstellen

4. TEST: Mit echten Mitarbeitern
   → 1 Woche planen
   → Konflikte provozieren

WARNUNG: 
- KEIN Code für Schichtarten bevor Schema bestätigt!
- Öffnungszeiten MÜSSEN vor Reservierungs-Test existieren
```

---

**STOP – Keine Implementierung gestartet. Warte auf Freigabe.**
