# 🔍 CARLSBURG COCKPIT / GASTROCORE – AUDIT & ROADMAP
**Datum:** 2025-12-22  
**Build-ID:** cc4b2f4d-20251222  
**Commit:** cc4b2f4d4b9376cc57b8ff7be22553153b5ffa6c  
**Branch:** main  
**Version:** 3.0.0  

---

## 1️⃣ SESSION INTEGRITY CHECK

### A) Git / Repo
| Prüfpunkt | Status |
|-----------|--------|
| Repo-Pfad | `/app` (origin: github.com/carlsburger/GastroCore) |
| Branch | `main` (up to date) |
| Commit Hash | `cc4b2f4d4b9376cc57b8ff7be22553153b5ffa6c` |
| git status | ✅ Clean (nur yarn.lock untracked) |

### /api/version Response:
```json
{
  "build_id": "cc4b2f4d-20251222",
  "commit_hash": "cc4b2f4d4b9376cc57b8ff7be22553153b5ffa6c",
  "health_version": "3.0.0",
  "modules": {
    "core": true, "reservations": true, "tables": true,
    "events": true, "payments": true, "staff": true,
    "schedules": true, "taxoffice": true, "loyalty": true,
    "marketing": true, "ai": true
  }
}
```

### /api/health Response:
```json
{"status": "healthy", "database": "connected", "version": "3.0.0"}
```

---

### B) Dateiliste (Backend)

| Datei | LOC | Beschreibung |
|-------|-----|--------------|
| `server.py` | 2.242 | Haupt-Backend, Auth, Reservierungen, Core |
| `staff_module.py` | 1.871 | Mitarbeiter + Dienstplan |
| `loyalty_module.py` | 1.106 | Kundenbindung |
| `reservation_config_module.py` | 1.081 | Reservierungsregeln |
| `table_module.py` | 1.021 | Tisch-Stammdaten + Kombinationen |
| `payment_module.py` | 962 | Stripe-Integration |
| `events_module.py` | 944 | Events + Buchungen |
| `ai_assistant.py` | 921 | KI-Assistent |
| `taxoffice_module.py` | 889 | Finanzamt-Exporte |
| `marketing_module.py` | 875 | Kampagnen |
| `import_module.py` | 830 | Datenimport |
| `opening_hours_module.py` | 786 | Öffnungszeiten + Sperrtage |
| `seed_system.py` | 684 | Test-Daten |
| `email_service.py` | 670 | SMTP-E-Mail |
| `system_settings_module.py` | 244 | Company Profile |
| `pdf_service.py` | 190 | PDF-Generierung |
| **TOTAL** | **15.889** | |

### Dateiliste (Frontend)

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
| `TaxOfficeExports.jsx` | 695 | Finanzamt |
| `TableAdmin.jsx` | 645 | Tisch-Stammdaten |
| `Settings.jsx` | 586 | Einstellungen |
| `Staff.jsx` | 570 | Mitarbeiter-Liste |
| ... (weitere 22 Seiten) | ~4.274 | |
| **TOTAL** | **18.365** | 36 Seiten gesamt |

---

### C) DB Check – Collection Counts

| Collection | Count | Status |
|------------|-------|--------|
| `users` | 1 | ✅ Admin vorhanden |
| `settings` | 6 | ✅ Grundkonfig |
| `reminder_rules` | 2 | ✅ Erinnerungen |
| `audit_logs` | 2 | ✅ Protokoll |
| `staff_members` | 0 | ⚠️ on-demand |
| `work_areas` | 0 | ⚠️ on-demand |
| `schedules` | 0 | ⚠️ on-demand |
| `shifts` | 0 | ⚠️ on-demand |
| `tables` | 0 | ⚠️ on-demand |
| `table_combinations` | 0 | ⚠️ on-demand |
| `reservations` | 0 | ⚠️ on-demand |
| `guests` | 0 | ⚠️ on-demand |
| `opening_hours_periods` | 0 | ⚠️ on-demand |
| `closures` | 0 | ⚠️ on-demand |
| `events` | 0 | ⚠️ on-demand |
| `payment_rules` | 0 | ⚠️ on-demand |

**Hinweis:** Collections werden automatisch bei erster Nutzung erstellt.

---

## 2️⃣ IST-STAND-REPORT (Detail)

### A) Module-Status

| Modul | Status | Endpoints | UI | Bemerkung |
|-------|--------|-----------|-----|-----------|
| **Core/Auth** | ✅ Fertig | Login, Users, Roles | ✅ | 3-Rollen-System |
| **Reservierungen** | ⚠️ Teilweise | CRUD, Waitlist | ✅ | Tisch-Zuweisung fehlt noch |
| **Tischplan** | ⚠️ Teilweise | Tables, Combinations | ✅ | Backend OK, UX ungetestet |
| **Service-Terminal** | ✅ Fertig | - | ✅ | UI optimiert (Sprint 5) |
| **Events** | ⚠️ Teilweise | Events, Products, Bookings | ✅ | Keine Testdaten |
| **Payments** | ⚠️ Teilweise | Stripe-Integration | ✅ | Test-Key vorhanden |
| **Staff** | ✅ Fertig | Members, Documents | ✅ | HR-Felder, Upload |
| **Schedules/Dienstplan** | ⚠️ Teilweise | Schedules, Shifts | ⚠️ | UX-Probleme, Shift-Dialog |
| **TaxOffice** | ✅ Fertig | Exports | ✅ | PDF/CSV |
| **Loyalty** | ⚠️ Teilweise | Programs, Points | ✅ | Keine Testdaten |
| **Marketing** | ⚠️ Teilweise | Campaigns | ✅ | SMTP nicht konfiguriert |
| **AI** | ⚠️ Teilweise | Chat-Endpoint | ✅ | Kein API-Key |

---

### B) Was läuft gut? (Top 5)

1. **Auth & Rollen-System** ✅
   - 3-Rollen-Modell (Admin, Schichtleiter, Mitarbeiter)
   - Route-Protection funktioniert
   - Token-basierte Auth stabil

2. **Öffnungszeiten-Management** ✅
   - Perioden + Sperrtage CRUD komplett
   - Effective Hours Berechnung korrekt
   - Priority-Logik funktioniert

3. **Staff-Modul** ✅
   - Mitarbeiter-Stammdaten mit Verschlüsselung
   - Dokument-Upload mit Kategorien
   - Completeness-Tracking

4. **Service-Terminal UI** ✅
   - Touch-optimiert, Pastel-Farben
   - Quick-Navigation (Heute/Morgen, Slots)
   - Hint-Icons für Gäste-Infos

5. **TaxOffice-Exporte** ✅
   - PDF/CSV-Export funktional
   - GoBD-konforme Struktur vorbereitet

---

### C) Risiken & Probleme (Top 10, priorisiert)

| # | Problem | Impact | Ursache | Betrifft |
|---|---------|--------|---------|----------|
| 1 | **Dienstplan: Shift-Dialog öffnet nicht** | 🔴 Hoch | Click-Handler defekt | `Schedule.jsx` |
| 2 | **Keine Stammdaten (Tische, MA, Bereiche)** | 🔴 Hoch | Seed nicht ausgeführt | DB |
| 3 | **SMTP nicht konfiguriert** | 🟡 Mittel | Env-Vars fehlen | `email_service.py` |
| 4 | **KI ohne API-Key** | 🟡 Mittel | OpenAI-Key fehlt | `ai_assistant.py` |
| 5 | **Dienstplan: KW-Navigation statt Datum** | 🟡 Mittel | UX-Entscheidung | `Schedule.jsx` |
| 6 | **Keine Schichtarten-Konfiguration** | 🟡 Mittel | Fehlendes Feature | Backend + UI |
| 7 | **Export-Buttons nicht sichtbar** | 🟡 Mittel | Conditional Rendering | `Schedule.jsx` |
| 8 | **Tischplan ohne Tische** | 🟡 Mittel | Keine Stammdaten | DB + `TablePlan.jsx` |
| 9 | **Reservierung ohne Tisch-Zuweisung-Logik** | 🟡 Mittel | Kein Auto-Assign | `server.py` |
| 10 | **MyShifts zeigt immer KW 52** | 🟢 Niedrig | Week-Calc Bug | `MyShifts.jsx` |

---

### D) Nacharbeit erforderlich

1. **Shift-Dialog fixen** – `Schedule.jsx` Click-Handler für Plus-Button reparieren
2. **Schichtarten-Collection** – Backend-Endpoint + Admin-UI für konfigurierbare Schichtarten
3. **Kalender-Navigation** – Datum-Picker statt KW-Buttons, heute markieren
4. **Stammdaten-Setup** – Tische, Bereiche, Mitarbeiter initial anlegen
5. **SMTP konfigurieren** – Env-Vars in Backend-Deployment setzen
6. **Tischplan testen** – Mit echten Tischen durchspielen
7. **Export-Visibility** – Buttons auch ohne Schichten anzeigen

---

## 3️⃣ ROADMAP – Praktische Reihenfolge

### Sprint 6: Dienstplan Stabilisierung (1 Woche)
**Ziel:** Dienstplan produktionsreif machen
- [ ] Fix: Shift-Dialog Click-Handler
- [ ] Schichtarten-Konfiguration (Collection + UI)
- [ ] Kalender-Navigation (Datum statt nur KW)
- [ ] Export-Buttons immer sichtbar
- [ ] Test mit echten Mitarbeitern

### Sprint 7: Tischplan & Stammdaten (1-2 Wochen)
**Ziel:** Tische definieren, Plan nutzbar
- [ ] Tisch-Stammdaten anlegen (15-20 Tische)
- [ ] Bereiche definieren (Saal, Wintergarten, Terrasse)
- [ ] Tischplan grafisch testen
- [ ] Kombinationsregeln validieren

### Sprint 8: Reservierung + Tisch-Zuweisung (1-2 Wochen)
**Ziel:** Reservierungen an Tische binden
- [ ] Auto-Assign Logik implementieren
- [ ] Service-Terminal: Tisch-Anzeige
- [ ] Belegungsübersicht pro Zeitslot
- [ ] Konflikte visualisieren

### Sprint 9: E-Mail & Kommunikation (1 Woche)
**Ziel:** Gäste automatisch informieren
- [ ] SMTP konfigurieren + testen
- [ ] E-Mail-Templates anpassen
- [ ] Reminder-System aktivieren

### Sprint 10: KI-Integration (Optional, nach Stabilisierung)
**Ziel:** Assistenz-Funktionen
- [ ] OpenAI-Key einbinden
- [ ] Natürliche Sprache für Suche
- [ ] Empfehlungen für Tischplanung

**Begründung der Reihenfolge:**
1. Dienstplan zuerst → täglich im Einsatz
2. Tische vor Reservierungen → Grundlage für Zuweisung
3. E-Mail nach Kern-Features → Nice-to-have
4. KI ganz am Ende → nur sinnvoll wenn Daten vorhanden

---

## 4️⃣ DIENSTPLAN – DEEP DIVE

### A) Ist-Stand

**Backend-Endpoints (staff_module.py):**
```
GET    /api/staff/schedules          – Liste aller Pläne
GET    /api/staff/schedules/{id}     – Ein Plan
POST   /api/staff/schedules          – Plan erstellen
PATCH  /api/staff/schedules/{id}     – Plan aktualisieren
POST   /api/staff/schedules/{id}/publish  – Veröffentlichen
POST   /api/staff/schedules/{id}/copy     – Woche kopieren
GET    /api/staff/shifts             – Schichten filtern
POST   /api/staff/shifts             – Schicht erstellen
PATCH  /api/staff/shifts/{id}        – Schicht bearbeiten
DELETE /api/staff/shifts/{id}        – Schicht löschen
GET    /api/staff/my-shifts          – Eigene Schichten (MA-Ansicht)
```

**Collections:**
- `schedules` – Wochenpläne (year, week, status)
- `shifts` – Einzelne Schichten (staff_member_id, date, times, role)
- `work_areas` – Arbeitsbereiche (name, description)
- `staff_members` – Mitarbeiter (name, employment_type, areas)

**UI-Seiten:**
- `Schedule.jsx` (741 LOC) – Manager-Ansicht
- `MyShifts.jsx` (215 LOC) – Mitarbeiter-Ansicht

**Konflikt-Erkennung:**
- ✅ Doppelbelegung (gleicher MA, gleicher Tag, überlappende Zeit)
- ✅ Ruhezeit (11 Stunden zwischen Schichten)

---

### B) Fehlende Konfiguration

#### 1) Schichtarten (FEHLT KOMPLETT)

**Anforderung:**
- Konfigurierbare Schichttypen statt hardcodierter Rollen
- Pro Schichtart: Name, Farbe, Default-Zeiten, Bereich, Pausenregel

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

**Empfohlene Struktur:**
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

---

#### 2) Dienstplan-Ansicht (UX-Probleme)

**Aktuell:**
- Navigation nur über KW-Buttons (</>)
- Kein Datum-Picker
- "Heute" nicht markiert
- Keine Monats-Schnellwahl

**Anforderung:**
- Kalender-Widget oben
- Monat/Jahr schnell wählbar (Dropdown oder Scroll)
- Tagesleiste (Mo-So) klickbar
- "Heute" immer hervorgehoben
- 2 Jahre voraus mit wenigen Klicks erreichbar
- Wochenstart: Montag (✅ bereits so)

**Empfohlene Ansicht:**
```
┌─────────────────────────────────────────────────────┐
│  ← Dezember 2025 →   [Heute] [Monat-Picker]         │
│  Mo  Di  Mi  Do  Fr  Sa  So                         │
│  22  23  24  25  26  27  28  ← Aktuelle Woche       │
├─────────────────────────────────────────────────────┤
│        Mo   Di   Mi   Do   Fr   Sa   So             │
│ Service  │    │    │    │    │    │    │            │
│ Küche    │    │    │    │    │    │    │            │
│ Bar      │    │    │    │    │    │    │            │
└─────────────────────────────────────────────────────┘
```

**Layout-Empfehlung:** 
- Spalten = Tage (Mo-So)
- Zeilen = Bereiche (Service, Küche, Bar, Event)
- Innerhalb: Mitarbeiter-Karten mit Zeiten

---

### C) Quick Win vs. Sauberer Umbau

#### Quick Win (ohne Backend-Änderung):
1. **Shift-Dialog fix** – nur Frontend, Click-Handler debuggen
2. **Heute markieren** – CSS-Klasse für aktuellen Tag
3. **Datum anzeigen** – Neben KW auch DD.MM. anzeigen
4. **Export-Buttons** – Conditional entfernen

#### Sauberer Umbau (additive Endpoints):

1. **Neue Collection: `shift_types`**
   ```
   POST   /api/staff/shift-types
   GET    /api/staff/shift-types
   PATCH  /api/staff/shift-types/{id}
   DELETE /api/staff/shift-types/{id}
   ```

2. **UI-Seite: `/admin/settings/shift-types`**
   - Liste aller Schichtarten
   - Dialog für Erstellen/Bearbeiten
   - Drag & Drop für Reihenfolge

3. **Schedule.jsx Refactoring:**
   - Kalender-Widget (DatePicker)
   - Schichtarten aus API laden
   - Shift-Dialog mit Schichtart-Dropdown

---

### D) To-Do Liste (max 12 Punkte)

| # | Aufgabe | Typ | Priorität |
|---|---------|-----|-----------|
| 1 | Fix: Shift-Dialog Click-Handler | Bug | 🔴 |
| 2 | Export-Buttons immer sichtbar | Bug | 🔴 |
| 3 | "Heute" im Kalender markieren | UX | 🟡 |
| 4 | Datum (DD.MM.) neben KW anzeigen | UX | 🟡 |
| 5 | Collection `shift_types` anlegen | Backend | 🟡 |
| 6 | CRUD-Endpoints für Schichtarten | Backend | 🟡 |
| 7 | UI-Seite für Schichtarten | Frontend | 🟡 |
| 8 | Shift-Dialog: Schichtart-Dropdown | Frontend | 🟡 |
| 9 | Kalender-Widget für Navigation | Frontend | 🟢 |
| 10 | Monat-Schnellwahl | Frontend | 🟢 |
| 11 | 2-Jahres-Navigation | Frontend | 🟢 |
| 12 | Test: Vollständiger Schicht-Workflow | Test | 🔴 |

---

### E) Testliste für Dienstplan

| Test | Beschreibung | Voraussetzung |
|------|--------------|---------------|
| T1 | Plan erstellen (neue Woche) | Mitarbeiter vorhanden |
| T2 | Shift hinzufügen (Dialog öffnet) | Plan existiert |
| T3 | Shift speichern (MA + Zeit + Bereich) | T2 erfolgreich |
| T4 | Konflikt: Doppelbelegung → Fehler | 2 Shifts gleicher MA |
| T5 | Konflikt: Ruhezeit → Fehler | Schicht 23:00, nächste 06:00 |
| T6 | Shift bearbeiten | Bestehender Shift |
| T7 | Shift löschen | Bestehender Shift |
| T8 | Plan veröffentlichen | Status = entwurf |
| T9 | Woche kopieren | Veröffentlichter Plan |
| T10 | PDF-Export | Plan mit Shifts |
| T11 | CSV-Export | Plan mit Shifts |
| T12 | MyShifts: Eigene Schichten sehen | Als Mitarbeiter |

---

## 5️⃣ NEXT STEP EMPFEHLUNG

```
FOKUS: Sprint 6 – Dienstplan Stabilisierung

1. SOFORT: Shift-Dialog Bug fixen (Schedule.jsx)
   → Ohne funktionierenden Dialog kein produktiver Test

2. DANN: Schichtarten-Konzept finalisieren
   → Collection-Schema abstimmen
   → UI-Mockup erstellen

3. DANACH: Stammdaten anlegen (2-3 Test-Mitarbeiter)
   → Echte Schichten planen
   → Konflikt-Tests durchführen

4. PARALLEL: SMTP konfigurieren (wenn Zugangsdaten vorliegen)

WARNUNG: KEIN Code schreiben bevor Schichtarten-Schema bestätigt!
```

---

**STOP – Warte auf Freigabe für Implementierung.**
