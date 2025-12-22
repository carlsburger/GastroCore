# =============================================
# IST-STAND-REPORT – Carlsburg Cockpit / GastroCore
# Stand: 2025-12-22 12:17 UTC
# =============================================

## 1) SESSION INTEGRITY CHECK

### A) Git / Repository
| Parameter | Wert |
|-----------|------|
| Repo-Pfad | `/app` |
| Branch | `main` |
| Commit Hash | `98ea4b03dc9559ebb4ae6644b916d026de88bbcf` |
| Build-ID | `98ea4b03-20251222` |
| git status | ✅ clean (nur yarn.lock untracked) |

### B) API Status
```json
GET /api/health
{
  "status": "healthy",
  "database": "connected",
  "version": "3.0.0"
}

GET /api/version → Modules:
  core: true, reservations: true, tables: true, events: true,
  payments: true, staff: true, schedules: true, taxoffice: true,
  loyalty: true, marketing: true, ai: true
```

### C) Dateiliste (Backend)
| Modul-Datei | Größe (Bytes) | LOC |
|-------------|---------------|-----|
| server.py | 87.488 | 2.242 |
| staff_module.py | 69.682 | 1.871 |
| events_module.py | 36.190 | 944 |
| reservation_config_module.py | 36.721 | 1.081 |
| table_module.py | 34.486 | ~900 |
| payment_module.py | 34.736 | ~900 |
| loyalty_module.py | 37.041 | ~950 |
| marketing_module.py | 32.166 | ~850 |
| taxoffice_module.py | 32.103 | ~850 |
| opening_hours_module.py | 24.761 | ~650 |
| system_settings_module.py | 7.734 | ~200 |
| import_module.py | 34.262 | ~900 |
| ai_assistant.py | 31.715 | ~800 |

**Total Backend:** 17 Python-Dateien, ~15.000 LOC

### D) Dateiliste (Frontend)
| Seite | Größe (Bytes) | Funktion |
|-------|---------------|----------|
| ServiceTerminal.jsx | 50.929 | Tagesgeschäft Service |
| TablePlan.jsx | 45.056 | Tischplan-Ansicht |
| Dashboard.jsx | 42.311 | Übersicht/Statistiken |
| AIAssistant.jsx | 39.135 | KI-Chat |
| Marketing.jsx | 36.072 | Marketing-Tools |
| OpeningHoursAdmin.jsx | 35.166 | Öffnungszeiten/Sperrtage |
| Schedule.jsx | 27.151 | Dienstplan |
| ReservationConfig.jsx | 28.763 | Reservierungs-Einstellungen |
| Staff.jsx | 20.921 | Mitarbeiterliste |
| Events.jsx | 18.605 | Events/Aktionen |
| Settings.jsx | 23.517 | Einstellungen |

**Total Frontend:** 36 JSX-Seiten, ~600 KB

### E) Datenbank Collections
| Collection | Count | Status |
|------------|-------|--------|
| users | 1 | ✅ Admin vorhanden |
| staff_members | 12 | ✅ Importiert |
| schedules | 1 | ✅ KW vorhanden |
| shifts | 0 | ⚠️ Keine Schichten |
| work_areas | 0 | ⚠️ Keine Arbeitsbereiche |
| reservations | 0 | ⚠️ Keine Reservierungen |
| guests | 0 | ⚪ On-demand |
| events | 16 | ✅ 8 Veranstalt. + 8 Aktionen |
| opening_hours_master | 4 | ✅ Perioden vorhanden |
| closures | 5 | ✅ Sperrtage vorhanden |
| tables | 0 | ⚠️ Keine Tische |
| areas | 0 | ⚠️ Keine Bereiche |
| system_settings | 1 | ✅ Company Profile |
| audit_logs | 35 | ✅ Logging aktiv |

---

## 2) MODULE-STATUS

| Modul | Status | Backend | Frontend | Bemerkung |
|-------|--------|---------|----------|-----------|
| **Core/Auth** | ✅ | server.py | Login.jsx | JWT Auth funktioniert |
| **Reservierungen** | ⚠️ | server.py | ServiceTerminal.jsx | Endpoints OK, aber keine Testdaten |
| **Tischplan** | ⚠️ | table_module.py | TablePlan.jsx, TableAdmin.jsx | UI vorhanden, keine Tische angelegt |
| **Service-Terminal** | ✅ | server.py | ServiceTerminal.jsx | Optimiert für iPad |
| **Events & Aktionen** | ✅ | events_module.py | Events.jsx | 3 Kategorien, 16 Events |
| **Payments** | ⚠️ | payment_module.py | PaymentRules.jsx | Stripe-Integration, keine Config |
| **Staff/Mitarbeiter** | ✅ | staff_module.py | Staff.jsx | 12 MA importiert |
| **Schedules/Dienstplan** | ⚠️ | staff_module.py | Schedule.jsx | UI vorhanden, UX-Probleme |
| **TaxOffice/Exporte** | ✅ | taxoffice_module.py | TaxOfficeExports.jsx | DATEV-Export |
| **Loyalty/Kunden** | ⚠️ | loyalty_module.py | - | Backend vorhanden, kein Frontend |
| **Marketing** | ⚠️ | marketing_module.py | Marketing.jsx | UI vorhanden, SMTP fehlt |
| **KI-Assistent** | ✅ | ai_assistant.py | AIAssistant.jsx | GPT-Integration |
| **Opening Hours** | ✅ | opening_hours_module.py | OpeningHoursAdmin.jsx | Perioden + Closures |
| **System Settings** | ✅ | system_settings_module.py | SystemSettings.jsx | Company Profile |

---

## 3) WAS LÄUFT GUT? (Top 5)

1. **Backend-Architektur** ✅
   - Saubere Modul-Trennung, alle 11 Module aktiv
   - Audit-Logging funktioniert (35 Einträge)
   - REST-API vollständig dokumentiert

2. **Events & Aktionen** ✅
   - 3-Kategorien-System (Veranstaltung/Aktion/Menü-Aktion)
   - 16 Events von Website importiert
   - Menüauswahl-Logik implementiert

3. **Mitarbeiter-Import** ✅
   - 12 Mitarbeiter aus XLSX importiert
   - Idempotente Upsert-Logik
   - HR-Felder verschlüsselt

4. **Öffnungszeiten-System** ✅
   - Perioden mit Priority-Logik (Sommer/Winter)
   - Recurring + One-off Sperrtage
   - Effective Hours API für Reservierung & Dienstplan

5. **UI/Corporate Design** ✅
   - Neue Farben (#002f02, #ffed00) implementiert
   - Klappbare Navigation
   - Touch-optimiert für iPad

---

## 4) WAS LÄUFT NICHT GUT / RISIKEN (Top 10)

| # | Problem | Impact | Ursache | Betroffene Datei |
|---|---------|--------|---------|------------------|
| 1 | **Keine Tische angelegt** | HOCH | Seed fehlt | table_module.py, TableAdmin.jsx |
| 2 | **Keine Arbeitsbereiche (Work Areas)** | HOCH | Seed fehlt → Dienstplan unbenutzbar | staff_module.py |
| 3 | **Keine Schichtarten konfigurierbar** | HOCH | Feature fehlt komplett | staff_module.py, Schedule.jsx |
| 4 | **Dienstplan UX: KW statt Datum** | MITTEL | Kalender-Navigation umständlich | Schedule.jsx |
| 5 | **SMTP nicht konfiguriert** | HOCH | Keine E-Mails möglich | Settings.jsx |
| 6 | **Keine Areas (Restaurant/Terrasse)** | HOCH | Seed fehlt | Areas.jsx |
| 7 | **Payment Rules leer** | MITTEL | Keine Anzahlungsregeln | payment_module.py |
| 8 | **Loyalty-Frontend fehlt** | NIEDRIG | Backend vorhanden, UI fehlt | - |
| 9 | **Reservierungs-Testdaten fehlen** | MITTEL | Kein Seed → Service-Terminal leer | server.py |
| 10 | **Route /events → Service-Terminal Bug** | NIEDRIG | Routing-Konflikt | App.js |

---

## 5) WAS MÜSSEN WIR NACHARBEITEN?

### KRITISCH (vor Go-Live)
1. **Tische anlegen** – Seed-Script oder Admin-UI in TableAdmin.jsx
2. **Areas anlegen** – Restaurant, Terrasse, Wintergarten in Areas.jsx
3. **Work Areas anlegen** – Service, Küche, Bar für Dienstplan
4. **SMTP konfigurieren** – .env Variablen + Settings.jsx
5. **Schichtarten-System** – Neue Collection + Config-UI

### WICHTIG (für Betrieb)
6. **Dienstplan-Kalender** – Monat/Jahr schnell wählbar machen
7. **Testdaten Reservierungen** – Seed für Service-Terminal-Tests
8. **Payment Rules** – Anzahlungsregeln definieren
9. **Reservation-Config** – Slot-Zeiten, Kapazitäten

### OPTIONAL (Verbesserungen)
10. **Loyalty-UI** – Punkte-System Frontend
11. **Newsletter-Integration** – Marketing-Modul vervollständigen
12. **KI-Assistent Prompts** – Feintuning für Carlsburg-Kontext

---

## 6) ROADMAP – Praktische Reihenfolge

### Sprint 1: SEED & STAMMDATEN (1-2 Tage)
**Ziel:** System betriebsbereit machen
- [ ] Areas anlegen (Restaurant, Terrasse, Wintergarten, Event)
- [ ] Tische anlegen (18 Tische lt. Carlsburg-Setup)
- [ ] Work Areas anlegen (Service, Küche, Bar, Event)
- [ ] Schichtarten-Config (Früh, Spät, Teildienst, Event)
- [ ] Test-Reservierungen für heute/morgen

**Begründung:** Ohne Stammdaten sind Service-Terminal und Dienstplan nicht nutzbar.

### Sprint 2: DIENSTPLAN OPTIMIERUNG (2-3 Tage)
**Ziel:** Dienstplan-UX deutlich verbessern
- [ ] Kalender-Navigation (Monat/Jahr schnell wählen)
- [ ] Wochenansicht mit "Heute" markiert
- [ ] Schichtarten-Farben in UI
- [ ] Schicht-Templates (Vorlagen)
- [ ] Mitarbeiter-Verfügbarkeiten

**Begründung:** Dienstplan ist täglich im Einsatz, UX-Probleme kosten Zeit.

### Sprint 3: KOMMUNIKATION (1-2 Tage)
**Ziel:** E-Mail/WhatsApp funktionsfähig
- [ ] SMTP-Konfiguration UI
- [ ] E-Mail-Templates prüfen
- [ ] Reminder-System testen
- [ ] WhatsApp-Integration (falls vorhanden)

**Begründung:** Gäste-Kommunikation ist geschäftskritisch.

### Sprint 4: RESERVIERUNG FEINSCHLIFF (2 Tage)
**Ziel:** Reservierungsflow optimieren
- [ ] Reservation-Config vollständig
- [ ] Payment Rules für Events
- [ ] Walk-in Flow testen
- [ ] Tischzuweisung automatisch

**Begründung:** Reservierungen sind Kerngeschäft.

### Sprint 5: KI & MARKETING (optional, später)
**Ziel:** Nur nach Stabilisierung
- [ ] KI-Assistent Feintuning
- [ ] Newsletter-Integration
- [ ] Loyalty-UI

**Begründung:** "Nice-to-have", keine Priorität vor Grundfunktionen.

---

## 7) DIENSTPLAN – DEEP DIVE

### A) Ist-Stand

**Collections:**
- `schedules` – Wochenpläne (year, week, status)
- `shifts` – Einzelne Schichten (schedule_id, member_id, date, start, end)
- `work_areas` – Arbeitsbereiche (AKTUELL LEER!)
- `staff_members` – 12 Mitarbeiter vorhanden

**Endpoints (staff_module.py):**
```
GET  /api/staff/schedules           - Liste
GET  /api/staff/schedules/{id}      - Detail mit Shifts
POST /api/staff/schedules           - Neuer Wochenplan
POST /api/staff/schedules/{id}/publish
POST /api/staff/schedules/{id}/archive
POST /api/staff/schedules/{id}/copy
GET  /api/staff/shifts              - Schichten filtern
POST /api/staff/shifts              - Schicht anlegen
PATCH/DELETE /api/staff/shifts/{id}
GET  /api/staff/my-shifts           - Eigene Schichten
GET  /api/staff/hours-overview      - Stundenübersicht
```

**UI (Schedule.jsx):**
- 741 LOC, funktionale Komponente
- Wochenansicht mit 7 Spalten (Mo-So)
- Schichten als Karten pro Tag
- Dialog zum Erstellen/Bearbeiten

### B) UX-Probleme

1. **Navigation nach KW statt Datum**
   - User muss KW-Nummer kennen
   - Kein visueller Kalender
   - "Heute" nicht sofort sichtbar

2. **Kein schneller Monats-/Jahreswechsel**
   - Nur +/- Woche möglich
   - 2 Jahre voraus = 104 Klicks

3. **Keine Schichtarten**
   - Nur Start/Ende, keine Kategorisierung
   - Keine Farben für Früh/Spät/etc.
   - Keine Default-Zeiten

4. **Work Areas fehlen**
   - Ohne Work Areas keine Bereichszuordnung
   - UI zeigt leere Bereiche

### C) Fehlende Konfiguration

**1) Schichtarten (NEU ANZULEGEN):**
```javascript
// Vorschlag: Collection "shift_types"
{
  id: uuid,
  name: "Frühdienst",
  short_name: "F",
  color: "#4CAF50",
  default_start: "06:00",
  default_end: "14:00",
  work_area_id: "service",
  break_minutes: 30,
  is_active: true
}

// Beispiel-Schichtarten:
- Frühdienst (F) 06:00-14:00 grün
- Spätdienst (S) 14:00-22:00 blau  
- Teildienst (T) 10:00-14:00 + 17:00-22:00 orange
- Event (E) flexibel lila
- Küche (K) 08:00-16:00 rot
```

**2) Dienstplan-Ansicht (VERBESSERUNG):**
```
+--------------------------------------------------+
| < Jan 2026 >  [Heute] [Woche] [Monat]            |
+--------------------------------------------------+
| Mo Di Mi Do Fr Sa So                              |
| 5  6  7  8  9  10 11  ← aktuelle Woche           |
+--------------------------------------------------+
|        | Mo 5. | Di 6. | Mi 7. | ...             |
+--------+-------+-------+-------+                  |
| Service| [F]   | [S]   | -     |                  |
|        | Tom   | Anna  |       |                  |
+--------+-------+-------+-------+                  |
| Küche  | [K]   | [K]   | [K]   |                  |
|        | Max   | Max   | Lisa  |                  |
+--------+-------+-------+-------+                  |
```

### D) Vorschlag: Minimal vs. Sauber

**Quick Win (ohne Backend-Änderung):**
- Kalender-Widget in Schedule.jsx hinzufügen
- Heute-Button + Datum-Picker
- Monat/Jahr Dropdown
- Work Areas als Seed anlegen

**Saubere Lösung (mit Backend):**
1. Neue Collection `shift_types` 
2. Neue Endpoints:
   - `GET/POST/PATCH/DELETE /api/staff/shift-types`
3. Shift-Model erweitern: `shift_type_id`
4. UI: Schichtarten-Admin + Farben in Kalender

### E) To-Do Liste Dienstplan (max 12 Punkte)

| # | Task | Typ | Priorität |
|---|------|-----|-----------|
| 1 | Work Areas anlegen (Service, Küche, Bar, Event) | SEED | KRITISCH |
| 2 | Kalender-Navigation in Schedule.jsx | UI | HOCH |
| 3 | "Heute" Button + Datum-Picker | UI | HOCH |
| 4 | Monat/Jahr Schnellwahl | UI | HOCH |
| 5 | Collection `shift_types` anlegen | BACKEND | HOCH |
| 6 | Endpoints für Schichtarten | BACKEND | HOCH |
| 7 | Schichtarten-Admin UI | UI | MITTEL |
| 8 | Farben in Schicht-Karten | UI | MITTEL |
| 9 | Default-Zeiten aus Schichtart | LOGIK | MITTEL |
| 10 | Closed-Days aus Opening Hours anzeigen | INTEGRATION | MITTEL |
| 11 | Schicht-Vorlagen/Templates | FEATURE | NIEDRIG |
| 12 | Mitarbeiter-Verfügbarkeiten | FEATURE | NIEDRIG |

### F) Testliste Dienstplan

1. [ ] Work Areas erscheinen in Dropdown
2. [ ] Neue Schicht kann angelegt werden
3. [ ] Schicht wird im Kalender angezeigt
4. [ ] Wochenwechsel funktioniert (+/-)
5. [ ] "Heute" springt zur aktuellen Woche
6. [ ] Monat/Jahr kann schnell gewechselt werden
7. [ ] Schichtarten werden mit Farbe angezeigt
8. [ ] Geschlossene Tage sind markiert
9. [ ] Mitarbeiter sieht eigene Schichten (/my-shifts)
10. [ ] Stundenübersicht zeigt korrekte Summen

---

## 8) NEXT STEP EMPFEHLUNG

```
SOFORT (heute):
1. Areas + Tische + Work Areas als Seed anlegen
2. Dienstplan: Kalender-Navigation implementieren

DIESE WOCHE:
3. Schichtarten-System (Backend + Frontend)
4. SMTP-Konfiguration

NÄCHSTE WOCHE:
5. Test-Reservierungen + Service-Terminal Durchlauf
6. Payment Rules für Events

NICHT ANFASSEN (vorerst):
- KI-Assistent Feintuning
- Marketing/Newsletter
- Loyalty-System
```

---

*Report erstellt: 2025-12-22 12:17 UTC*
*Nächstes Review: Nach Sprint 1 Abschluss*
