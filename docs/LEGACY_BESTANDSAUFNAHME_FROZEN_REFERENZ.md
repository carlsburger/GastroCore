# LEGACY SYSTEM – BESTANDSAUFNAHME & FROZEN-REFERENZ

**System:** Carlsburg Cockpit (GastroCore)  
**Erstellt:** 01.01.2026  
**Zweck:** Clean Rebuild Vorbereitung (Variante C: Legacy-Freeze)  
**Analyst:** Emergent AI (Senior Software/Data Architect)

---

## 1. Nachweislich funktionierende Komponenten

### 1.1 RESERVIERUNGSSYSTEM (Modul 20) – VOLLSTÄNDIG FUNKTIONAL ✅

| Komponente | Route | Status | Nachweis |
|------------|-------|--------|----------|
| Booking Widget | `/book` | ✅ Live | 3-Schritt-Wizard, Slot-Prüfung, E-Mail-Bestätigung |
| Service-Terminal | `/service-terminal` | ✅ Live | Status-Workflow, Walk-Ins, Tischzuweisung |
| Reservierungs-Kalender | `/reservation-calendar` | ✅ Live | Wochen-/Tagesansicht |
| Tischplan | `/table-plan` | ✅ Live | Visuelle Belegung |
| Warteliste | `/waitlist` | ✅ Live | CRUD, Konvertierung in Reservierung |
| Öffentliche APIs | `/api/public/*` | ✅ Live | restaurant-info, availability, book |

**Bestätigte Flows:**
1. **Widget → Reservierung → Bestätigungs-E-Mail** ✅
2. **Walk-in Erfassung → Tischzuweisung → Abschluss** ✅
3. **Warteliste → Benachrichtigung → Konvertierung** ✅
4. **Online-Stornierung via Token** ✅

### 1.2 EVENT-SYSTEM (Modul 40) – FUNKTIONAL ✅

| Komponente | Route | Status | Nachweis |
|------------|-------|--------|----------|
| Event-Verwaltung | `/events` | ✅ Live | CRUD, Kategorien, Pricing |
| Event-Buchungen | `/event-bookings` | ✅ Live | Reservierung mit Anzahlung |
| WordPress-Sync | Backend | ✅ Live | Automatischer Import (WP → GastroCore) |
| Dashboard-Widget | `/dashboard` | ✅ Live | Events-Summary mit 3 Kategorien |

**Bestätigte Flows:**
1. **WordPress Sync → Events in DB** ✅
2. **Event-Buchung mit Varianten-Auswahl → Anzahlung → Bestätigung** ✅
3. **Pricing-Kalkulation (Single + Varianten)** ✅

### 1.3 MITARBEITER-SYSTEM (Modul 30) – TEILWEISE FUNKTIONAL ⚠️

| Komponente | Route | Status | Nachweis |
|------------|-------|--------|----------|
| Mitarbeiter-CRUD | `/staff` | ✅ Live | 23 Mitarbeiter in DB |
| Zeiterfassung (Timeclock) | `/api/timeclock/*` | ✅ Live | State-Machine (WORKING/BREAK/CLOSED) |
| Schichten V2 | `/api/staff/shifts/v2` | ✅ Live | assigned_staff_ids[], Status-Workflow |
| Abwesenheiten | `/api/staff/absences/*` | ✅ Live | Request/Approve/Reject |
| Dokumente | `/api/staff/documents/*` | ✅ Live | Upload, Acknowledge |
| Employee-PWA | `/employee` | ✅ Live | 5 Tabs (Status, Schichten, Zeiten, Abwesenheit, Unterlagen) |

**ABER:** 
- V1/V2 Parallelität bei Schichten (noch nicht vollständig migriert)
- Department-Inkonsistenz (`kueche` vs `kitchen`)

### 1.4 COCKPIT-INFRASTRUKTUR (Modul 10) – FUNKTIONAL ✅

| Komponente | Route | Status | Nachweis |
|------------|-------|--------|----------|
| Dashboard | `/dashboard` | ✅ Live | Reservierungen, Events, POS |
| Öffnungszeiten-Admin | `/opening-hours` | ✅ Live | Perioden-basiert (Sommer/Winter) |
| Seeds Backup/Export | `/api/admin/seeds/*` | ✅ Live | ZIP-Export von Konfigdaten |
| System-Settings | Backend | ✅ Live | Key-Value Store |
| POS Mail Import | `/api/pos/*` | ✅ Live | IMAP Ingest, Daily Metrics |

---

## 2. Identifizierte Frozen-Stände

### 2.1 Frozen-Stand A: MODUL 20 RESERVIERUNG (29.12.2025)

**Dokumentiert in:** `/app/docs/MODUL_20_FREEZE.md`

| Aspekt | Details |
|--------|---------|
| **Freeze-Datum** | 29.12.2025 |
| **Version** | 1.0 FINAL |
| **Abgenommen von** | Emergent AI |

**Enthaltene Guards (B1-B5, C1-C2):**

| Guard | Funktion | Status |
|-------|----------|--------|
| B1 | Standarddauer 115 Minuten erzwingen | ✅ AKTIV |
| B2 | Event sperrt normale Reservierungen | ✅ AKTIV |
| B3 | Slots bei Event deaktivieren | ✅ AKTIV |
| B4 | Wartelisten-Trigger nur bei STORNIERT | ✅ AKTIV |
| B5 | 24h Bestätigungsfenster für Warteliste | ✅ AKTIV |
| C1 | Gäste pro Stunde aggregieren | ✅ AKTIV |
| C2 | Event-Flag prüfen (is_event_active_at) | ✅ AKTIV |

**Aktive Konfiguration:**
- `STANDARD_RESERVATION_DURATION_MINUTES = 115`
- `WAITLIST_OFFER_VALIDITY_HOURS = 24`

**Fachliche Regeln:**
- Status-Workflow: NEU → BESTÄTIGT → ANGEKOMMEN → ABGESCHLOSSEN/NO_SHOW/STORNIERT
- Wartelisten-Trigger NUR bei Status → `storniert` (nicht bei no_show oder abgeschlossen)
- Öffnungszeiten kommen Server-seitig aus `opening_hours_master`

**TABU-LISTE (Verbote):**
1. Keine zweite Reservierungs-API
2. Keine alternative Statuslogik
3. Keine parallele Availability-/Slot-Berechnung
4. Keine parallele Kapazitätsquelle
5. Keine Änderung der Guard-Triggerbedingungen
6. Keine Frontend-Berechnung von Öffnungszeiten

**Was bewusst NICHT Teil dieses Stands war:**
- Monatskalender-Ansicht
- Reservierungs-Reports/Statistiken
- Automatische SMS-Erinnerungen
- Online-Payment für Standard-Reservierungen (nur für Events)
- Customer Accounts (Gäste-Login)

### 2.2 Frozen-Stand B: ÖFFNUNGSZEITEN-ARCHITEKTUR (30.12.2025)

**Dokumentiert in:** `/app/docs/OPENING_HOURS_COLLECTIONS.md`

| Aspekt | Details |
|--------|---------|
| **Source of Truth** | `opening_hours_master` (MongoDB Collection) |
| **Schema** | Saisonale Perioden mit `rules_by_weekday` |
| **Aktueller Stand** | 6 Dokumente, 3 aktiv |

**Legacy-Collections (NICHT VERWENDEN):**
- `opening_hours_periods` → LEER (0 Dokumente)
- `opening_hours` → DEPRECATED (alte Struktur)

**Fachliche Regeln:**
- Perioden haben `start_date`, `end_date`, `priority`
- Bei Überlappung gewinnt höhere Priorität
- `active` + `archived` Flags beide prüfen

**Was bewusst NICHT Teil dieses Stands war:**
- Migration der Legacy-Referenzen in `reservation_config_module.py`
- Migration der Legacy-Referenzen in `staff_module.py`

### 2.3 Frozen-Stand C: TIMECLOCK STATE-MACHINE (29.12.2025)

| Aspekt | Details |
|--------|---------|
| **Collection** | `time_sessions`, `time_events` |
| **States** | OFF → WORKING ↔ BREAK → CLOSED |

**Fachliche Regeln (INVARIANTEN):**
- Max 1 Session pro Mitarbeiter & Tag
- Max 1 aktive Pause gleichzeitig
- **KRITISCH:** Clock-out während BREAK → 409 CONFLICT (blockiert!)
- Alle Events sind append-only mit Idempotency-Key

---

## 3. Konfiguration (migrierbar)

### 3.1 Definitive Konfigurationsdaten

| Collection | Dokumente | Seed-Datei | Migration |
|------------|-----------|------------|-----------|
| `opening_hours_master` | 6 (3 aktiv) | — | ✅ Übernehmen |
| `shift_templates` | 9 | `shift_templates_master.json` | ✅ Übernehmen |
| `tables` | 46 | `tables.xlsx` | ✅ Übernehmen |
| `table_combinations` | 17 | `table_combinations.xlsx` | ✅ Übernehmen |
| `reservation_slot_rules` | variabel | — | ✅ Übernehmen |
| `reservation_slot_exceptions` | variabel | — | ✅ Übernehmen |
| `system_settings` | variabel | — | ✅ Übernehmen |
| `users` (Admin) | 10 | seed_system.py | ✅ Übernehmen (ohne Passwörter) |

### 3.2 Semi-Konfiguration (prüfen)

| Collection | Dokumente | Anmerkung |
|------------|-----------|-----------|
| `staff_members` | 23 | Stammdaten, KEINE operativen Daten |
| `work_areas` | variabel | Arbeitsbereiche |
| `areas` | 0 (leer) | Bereiche (Restaurant/Terrasse) |
| `payment_rules` | 0 | Zahlungsregeln |
| `reminder_rules` | variabel | Erinnerungsregeln |

### 3.3 Seed-Dateien (versioniert in `/app/seed/`)

| Datei | Inhalt | Zeilen/Docs |
|-------|--------|-------------|
| `shift_templates_master.json` | 9 Schicht-Templates (V2 Schema) | 146 Zeilen |
| `tables.xlsx` | 46 Tische mit Bereichen | Excel |
| `table_combinations.xlsx` | 17 Tischkombinationen | Excel |
| `staff.xlsx` | 18 Mitarbeiter-Stammdaten | Excel |

### 3.4 Tischplan-Konfiguration (GOLD)

**Bereiche:**
| Bereich | Subarea | Tische | Plätze |
|---------|---------|--------|--------|
| Restaurant | Saal | 13 | 59 |
| Restaurant | Wintergarten | 11 | 43 |
| Terrasse | Terrasse | 22 | 84 |
| **GESAMT** | | **46** | **186** |

**Kombinationsregeln (aus README):**
- Kombinationen NUR innerhalb gleicher Subarea erlaubt
- Tisch 3 (Exot, oval) → NIE kombinierbar
- Saal 2er rund (Tisch 2, 11, 12) → NIE kombinierbar
- Wintergarten (Tisch 19, 20, 21) → NIE kombinierbar
- Kombi S4 (13+114+1) → blockiert Tisch 2 automatisch

### 3.5 Schicht-Templates (Source of Truth)

**Kanonische Departments:** `service`, `kitchen`, `reinigung`, `eismacher`, `kuechenhilfe`

| Template-ID | Name | Zeiten | Event-Mode |
|-------------|------|--------|------------|
| tpl-service-frueh | Service Früh | 10:00-15:00 (fixed) | normal |
| tpl-service-spaet | Service Spät | 17:00-Close+30 | normal |
| tpl-service-schichtleiter | Schichtleiter | 11:00-Close | normal |
| tpl-kitchen-frueh | Küche Früh | 09:00-15:00 (fixed) | normal |
| tpl-kitchen-spaet | Küche Spät | 16:00-Close+30 | normal |
| tpl-reinigung | Reinigung | 06:00-10:00 (fixed) | normal |
| tpl-service-kultur | Service Spät Kultur | 17:00-00:00 (fixed) | kultur |
| tpl-kitchen-kultur | Küche Spät Kultur | 16:00-00:00 (fixed) | kultur |
| tpl-schichtleiter-kultur | Schichtleiter Kultur | 11:00-00:00 (fixed) | kultur |

---

## 4. Operative Daten (NICHT migrieren)

### 4.1 Transaktionale Daten

| Collection | Typ | Aktion |
|------------|-----|--------|
| `reservations` | Operativ | ❌ Nicht migrieren |
| `waitlist` | Operativ | ❌ Nicht migrieren |
| `events` | Operativ | ⚠️ Teilweise (aktive Events prüfen) |
| `event_bookings` | Operativ | ❌ Nicht migrieren |
| `shifts` | Operativ | ❌ Nicht migrieren |
| `schedules` | Operativ | ❌ Nicht migrieren |
| `time_sessions` | Operativ | ❌ Nicht migrieren |
| `time_events` | Operativ | ❌ Nicht migrieren |
| `payment_transactions` | Operativ | ❌ Nicht migrieren |
| `customers` | Operativ | ❌ Nicht migrieren |
| `guests` | Operativ | ❌ Nicht migrieren |

### 4.2 Logging/Audit

| Collection | Typ | Aktion |
|------------|-----|--------|
| `audit_logs` | Audit | ❌ Nicht migrieren |
| `message_logs` | Audit | ❌ Nicht migrieren |
| `ai_logs` | Audit | ❌ Nicht migrieren |
| `import_logs` | Audit | ❌ Nicht migrieren |
| `staff_import_runs` | Audit | ❌ Nicht migrieren |

### 4.3 POS-Daten

| Collection | Typ | Aktion |
|------------|-----|--------|
| `pos_documents` | Operativ | ❌ Nicht migrieren |
| `pos_daily_metrics` | Operativ | ❌ Nicht migrieren |
| `pos_z_reports_raw` | Operativ | ❌ Nicht migrieren |
| `pos_daily_kpis` | Operativ | ❌ Nicht migrieren |
| `pos_monthly_confirmations` | Operativ | ❌ Nicht migrieren |

---

## 5. Mehrfach-Wahrheiten & Inkonsistenzen

### 5.1 KRITISCH: Role/Department Inkonsistenz

**Problem:** 3 verschiedene Enum-Definitionen für dieselbe Fachlichkeit

| Datei | Enum | Werte |
|-------|------|-------|
| `staff_module.py:137` | ShiftRole | SERVICE, SCHICHTLEITER, **KUECHE**, BAR, AUSHILFE |
| `shifts_v2_module.py:39` | ShiftRole | SERVICE, **KITCHEN**, REINIGUNG, EISMACHER, KUECHENHILFE |
| `shift_template_migration.py:53` | CanonicalDepartment | SERVICE, **KITCHEN**, REINIGUNG, EISMACHER, KUECHENHILFE |

**Frontend zusätzlich:**
- `Staff.jsx:90-96` → `kueche` (deutsch)
- `Schedule.jsx:80-83` → `kitchen` (englisch) + Alias `kueche`
- `constants.js:97-103` → `kitchen` (englisch)

**FOLGE:** Schicht-Zuweisungen können fehlschlagen wenn nicht beide Varianten geprüft werden.

### 5.2 KRITISCH: Öffnungszeiten-Collections

| Collection | Status | Dokumentenanzahl |
|------------|--------|------------------|
| `opening_hours_master` | ✅ Source of Truth | 6 (3 aktiv) |
| `opening_hours_periods` | ⚠️ LEGACY (referenziert) | 0 (LEER!) |
| `opening_hours` | ❌ DEPRECATED | variabel |

**FOLGE:** Module referenzieren noch `opening_hours_periods`, obwohl es leer ist. Funktioniert nur weil Fallback auf `opening_hours_master` existiert.

### 5.3 MITTEL: Schicht V1/V2 Parallelität

| System | Datei | Status |
|--------|-------|--------|
| V1 | `staff_module.py` | ⚠️ Aktiv (Legacy) |
| V2 | `shifts_v2_module.py` | ✅ Aktiv (neu) |

**Schema-Unterschiede:**
- V1: `staff_member_id` (einzeln)
- V2: `assigned_staff_ids[]` (Array)
- V1: `shift_date`, `start_time`, `end_time` (strings)
- V2: `date_local`, `start_at_utc`, `end_at_utc` (datetime)

**FOLGE:** Doppelte Datenpflege möglich, inkonsistente Schichtzustände.

### 5.4 MITTEL: Settings-Collections

| Collection | Zweck | Status |
|------------|-------|--------|
| `settings` | Legacy Key-Value | ⚠️ Aktiv |
| `system_settings` | Neuer Key-Value | ⚠️ Aktiv |
| `reservation_options` | Reservierungs-Konfig | ✅ Aktiv |

**FOLGE:** Unklar welche Collection für welche Settings verwendet wird.

### 5.5 NIEDRIG: Event-Kategorien in Frontend

**Backend (events_module.py):**
```python
class ContentCategory(str, Enum):
    VERANSTALTUNG = "VERANSTALTUNG"
    AKTION = "AKTION"
    AKTION_MENUE = "AKTION_MENUE"
```

**Frontend (Events.jsx):**
```javascript
const CATEGORY_CONFIG = { ... }  // Hardcoded Labels + Farben
```

**FOLGE:** Label-Änderungen erfordern Frontend-Deployment.

---

## 6. Implizite Fachlogik & Sonderregeln

### 6.1 Tischnummern-Logik

| Regel | Beispiel | Anmerkung |
|-------|----------|-----------|
| Integer = normaler Tisch | `1`, `38` | Standard |
| Dezimal = Nebentisch | `38.1`, `40.1` | Terrassenlogik |
| 3-stellig = Kombi-Tisch | `114` | Teil von Kombi S3/S4 |

**Sonderfall Kombi S4:** Tische `13+114+1` blockieren automatisch Tisch `2` (wegen Laufweg).

### 6.2 Bereichslogik

| Bereich | Subarea | Besonderheiten |
|---------|---------|----------------|
| Restaurant | Saal | Hauptbereich, 13 Tische |
| Restaurant | Wintergarten | Separat, 11 Tische, eigene Kombis |
| Terrasse | Terrasse | Saisonal, 22 Tische, Dezimal-Nummern |

**Regel:** Kombinationen NUR innerhalb gleicher Subarea erlaubt!

### 6.3 Kapazitäts-Regeln

| Konstante | Wert | Quelle |
|-----------|------|--------|
| `DEFAULT_EVENT_CAPACITY` | 95 | events_module.py (NICHT 100!) |
| `STANDARD_RESERVATION_DURATION_MINUTES` | 115 | reservation_guards.py |
| `WAITLIST_OFFER_VALIDITY_HOURS` | 24 | reservation_guards.py |

### 6.4 Event- und Sonderabend-Logik

**Kulturabend-Modus:**
- Event-Mode `kultur` aktiviert verlängerte Schichten (bis 00:00)
- Normale Reservierungen werden durch Events blockiert (Guard B2)
- Slots bei Event deaktiviert (Guard B3)

**Aktionen vs. Veranstaltungen:**
- `VERANSTALTUNG`: Kulturevents (blockiert normale Reservierungen)
- `AKTION`: Zeitlich begrenzte Aktionen (erlaubt parallele Reservierungen)
- `AKTION_MENUE`: Menü-Aktion mit eingeschränkter Karte

### 6.5 Zeit-Overrides & Sonderzeiten

| Collection | Zweck |
|------------|-------|
| `reservation_slot_exceptions` | Datum-spezifische Slot-Änderungen |
| `opening_overrides` | Einmalige Öffnungszeiten-Änderungen |
| `closures` | Geplante Schließtage |
| `special_days` | Feiertage, besondere Tage |

### 6.6 Gast-Flag-System

| Flag | Trigger | Auswirkung |
|------|---------|------------|
| Greylist | 2 No-Shows | Warnung bei Buchung |
| Blacklist | 3 No-Shows | Buchung blockiert |

### 6.7 Payment-Flow bei Events

```
Event hat payment_policy.mode = "deposit"
    → Reservierung entsteht mit status = "pending_payment"
    → Zahlungsfrist = payment_deadline_hours
    → Nach Fristablauf: status = "expired" (automatisch)
    → Nach Zahlung: status = "bestätigt"
```

---

## 7. Übernahme-Empfehlung für Clean Rebuild

### 7.1 Unbedingt übernehmen (GOLD) ⭐

| Element | Begründung | Dateien/Collections |
|---------|------------|---------------------|
| **Tischplan-Struktur** | Fachlich komplex, bewährt | `tables.xlsx`, `table_combinations.xlsx` |
| **Öffnungszeiten-Perioden** | Source of Truth geklärt | `opening_hours_master` |
| **Schicht-Templates V2** | Aktuelles Schema, kanonische Departments | `shift_templates_master.json` |
| **Reservierungs-Guards** | Fachlich abgenommen, getestet | `reservation_guards.py` (Logik, nicht Code) |
| **Status-Workflow** | Etabliert im Live-Betrieb | Enum-Definition |
| **Event-Kategorien** | VERANSTALTUNG/AKTION/AKTION_MENUE | Enum-Definition |
| **Timeclock State-Machine** | Invarianten bewährt | Logik, nicht Code |
| **Admin-User Seed** | Bootstrap-Logik | `seed_system.py` (Konzept) |

### 7.2 Optional (übernehmen wenn sinnvoll)

| Element | Begründung | Empfehlung |
|---------|------------|------------|
| Staff-Stammdaten | 23 Mitarbeiter | Excel-Export als Basis |
| Event-Pricing-Logik | Varianten, Anzahlung | Konzept übernehmen, Code neu |
| POS-Ingest-Logik | IMAP + PDF Parser | Konzept übernehmen, Code neu |
| WordPress-Sync | Event-Import | Nur wenn WP bleibt |
| Wartelisten-Logik | Konvertierung, Trigger | Konzept übernehmen |
| E-Mail-Templates | Bestätigung, Storno | Texte extrahieren |

### 7.3 Explizit verwerfen (NICHT übernehmen) ❌

| Element | Begründung |
|---------|------------|
| **V1 Schicht-Code** | Parallelität zu V2, deprecated |
| **`opening_hours_periods`** | Leere Legacy-Collection |
| **`opening_hours`** | Deprecated Struktur |
| **`staff_module.py` komplett** | 143KB, 3800+ Zeilen, überladen |
| **Department-Hardcodings** | `kueche` vs `kitchen` Inkonsistenz |
| **Frontend Label-Hardcodings** | Sollten aus API kommen |
| **`schedules` Collection** | Unklar ob noch genutzt |
| **Alle operativen Daten** | Reservierungen, Events, Shifts etc. |
| **Backups in `/app/backups/`** | Historische Zustände, nicht relevant |
| **`areas` Collection** | 0 Dokumente, nicht implementiert |

---

## 8. Zusammenfassung für Clean Rebuild

### 8.1 Source-of-Truth Tabelle

| Domäne | Quelle | Status |
|--------|--------|--------|
| Öffnungszeiten | `opening_hours_master` | ✅ Eindeutig |
| Tische | `tables.xlsx` / `tables` Collection | ✅ Eindeutig |
| Tischkombinationen | `table_combinations.xlsx` | ✅ Eindeutig |
| Schicht-Templates | `shift_templates_master.json` | ✅ Eindeutig |
| Rollen/Departments | ❌ KONFLIKT | 3 Enum-Definitionen |
| Reservierungs-Status | `ReservationStatus` Enum | ✅ Eindeutig |
| Event-Kategorien | `ContentCategory` Enum | ✅ Eindeutig |
| Settings | ❌ KONFLIKT | 3 Collections |

### 8.2 Migrations-Prioritäten

1. **P1 (Sofort):** Tischplan + Kombinationen exportieren
2. **P2 (Sofort):** Öffnungszeiten-Perioden exportieren
3. **P3 (Sofort):** Schicht-Templates exportieren
4. **P4 (Kurzfristig):** Kanonische Departments definieren (EINMAL)
5. **P5 (Kurzfristig):** Status-Enums als Referenz dokumentieren
6. **P6 (Mittelfristig):** Staff-Stammdaten bereinigen

### 8.3 Was im Neubau NICHT wiederholen

1. ❌ Mehrere Enum-Definitionen für dieselbe Fachlichkeit
2. ❌ Legacy-Collections parallel zu neuen Collections
3. ❌ Frontend-Hardcodings für Labels/Farben
4. ❌ Module > 500 Zeilen (staff_module.py hat 3800+)
5. ❌ V1/V2 Parallelität ohne klare Deprecation
6. ❌ Implizite Fachlogik ohne Dokumentation

---

**Ende der Bestandsaufnahme**

*Erstellt: 01.01.2026*
*Analyst: Emergent AI*
*Zweck: Clean Rebuild Vorbereitung (Variante C: Legacy-Freeze)*
