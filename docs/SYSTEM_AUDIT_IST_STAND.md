# SYSTEM AUDIT – IST-STAND
## Carlsburg / GastroCore System
**Datum:** 30.12.2025  
**Version:** v7.0.0  
**Status:** PRODUKTIV (Atlas)

---

## 1. Gesamtüberblick

### 1.1 Systemarchitektur
| Schicht | Technologie | Status |
|---------|-------------|--------|
| Frontend | React 18 + Vite + Tailwind CSS | ✅ Aktiv |
| Backend | FastAPI (Python 3.11) | ✅ Aktiv |
| Datenbank | MongoDB Atlas | ✅ Produktiv |
| Auth | JWT (eigene Implementierung) | ✅ Aktiv |

### 1.2 Modulare Struktur (Backend)
```
├── CORE (Infrastruktur)
│   ├── server.py (Hauptrouter, Startup-Logik)
│   ├── core/auth.py (JWT, Rollen)
│   ├── core/database.py (MongoDB-Connection)
│   └── core/audit.py (Audit-Logging)
│
├── COCKPIT (10_COCKPIT)
│   ├── system_settings_module.py
│   ├── opening_hours_module.py
│   ├── seeds_backup_module.py
│   └── backup_module.py
│
├── RESERVIERUNG (20_RESERVIERUNG) - FREEZE
│   ├── reservation_capacity.py
│   ├── reservation_config_module.py
│   ├── reservation_slots_module.py
│   ├── reservation_guards.py
│   └── table_module.py
│
├── MITARBEITER (30_MITARBEITER) - AKTIV
│   ├── staff_module.py (143KB!)
│   ├── staff_import_module.py
│   ├── shifts_v2_module.py
│   ├── shift_template_migration.py
│   ├── timeclock_module.py
│   └── absences_module.py
│
├── EVENTS (40_EVENTS)
│   ├── events_module.py
│   └── (WordPress Sync in server.py)
│
├── KUNDEN-APP (50_KUNDEN)
│   └── loyalty_module.py
│
├── MARKETING (60_MARKETING)
│   └── marketing_module.py
│
├── TECHNIK (70_TECHNIK)
│   ├── pos_mail_module.py
│   ├── pos_zreport_module.py
│   ├── taxoffice_module.py
│   └── ai_assistant.py
│
└── IMPORT/SEED
    ├── seed_system.py
    ├── auto_restore.py
    ├── data_import_script.py
    ├── table_import_module.py
    └── import_module.py
```

### 1.3 Modul-Zählung
| Kategorie | Anzahl |
|-----------|--------|
| Backend-Module (*.py) | 32 |
| Frontend-Seiten (*.jsx) | 58 |
| MongoDB Collections | ~60 |
| Registrierte Router | 27 |

---

## 2. Backend-Analyse

### 2.1 Collection-Zugriffe (TOP 20)

| Collection | READ-Module | WRITE-Module | Typ |
|------------|-------------|--------------|-----|
| `staff_members` | staff, shifts_v2, timeclock, absences, taxoffice, ai_assistant | staff, staff_import, seed_system | Operativ |
| `events` | events, ai_assistant, backup, dashboard | events, data_import | Operativ |
| `reservations` | reservation_*, table, payment, ai_assistant | server.py, events | Operativ |
| `shifts` | staff, shifts_v2, timeclock, taxoffice | staff, shifts_v2 | Operativ |
| `shift_templates` | staff, shifts_v2, shift_migration, seeds_backup | staff, shift_migration | Konfiguration |
| `settings` | server.py, multiple | server.py, multiple | Konfiguration |
| `schedules` | staff | staff | Operativ |
| `users` | auth, staff, seed_system | auth, seed_system | Operativ |
| `opening_hours_periods` | opening_hours, reservation_*, seeds_backup | opening_hours | Konfiguration |
| `tables` | table, reservation_capacity | table, import | Konfiguration |
| `time_sessions` | timeclock, shifts_v2 | timeclock | Operativ |
| `customers` | loyalty, marketing | loyalty | Operativ |
| `marketing_content` | marketing | marketing | Operativ |
| `event_bookings` | events | events | Operativ |

### 2.2 Enum-Duplikate (KRITISCH)

**ShiftRole** – 3× definiert:
1. `staff_module.py:137` → `SERVICE, SCHICHTLEITER, KUECHE, BAR, AUSHILFE`
2. `shifts_v2_module.py:39` → `SERVICE, KITCHEN, REINIGUNG, EISMACHER, KUECHENHILFE`
3. `timeclock_module.py:64` (ShiftStatusV2 – Namenskonflikt)

**CanonicalDepartment** – 1× definiert (korrekt):
- `shift_template_migration.py:53` → `SERVICE, KITCHEN, REINIGUNG, EISMACHER, KUECHENHILFE`

**Inkonsistenz:**
- `staff_module.py` verwendet `KUECHE` (deutsch)
- `shifts_v2_module.py` verwendet `KITCHEN` (englisch)
- Alias-Mapping existiert, aber nicht überall verwendet

### 2.3 Doppelte Logik

| Logik | Dateien | Risiko |
|-------|---------|--------|
| Department/Role Normalisierung | `shift_template_migration.py`, `staff_import_module.py` | MITTEL |
| EndTimeType Enum | `staff_module.py:2145`, `shift_template_migration.py:61` | NIEDRIG |
| SeasonType/DayType Enum | `staff_module.py:2153-2158`, `shift_template_migration.py:65-73` | NIEDRIG |
| Schicht-Erstellung | `staff_module.py`, `shifts_v2_module.py` | HOCH |

### 2.4 Guards & Validatoren

| Guard | Datei | Zweck |
|-------|-------|-------|
| `require_admin` | `core/auth.py` | Admin-Only Endpoints |
| `require_manager` | `core/auth.py` | Admin + Schichtleiter |
| `reservation_guards.py` | Eigenes Modul | Reservierungsvalidierung |
| `SEED_COLLECTIONS` | `seeds_backup_module.py` | Seed-Scope Definition |
| `CRITICAL_COLLECTIONS` | `auto_restore.py` | Auto-Restore Scope |

---

## 3. Frontend-Analyse

### 3.1 Seiten-Übersicht (58 Seiten)

| Bereich | Seiten | Domänen |
|---------|--------|---------|
| Cockpit (Dashboard) | 15 | Reservierungen, Events, Einstellungen |
| Mitarbeiter | 10 | Staff, Shifts, Templates, Absences |
| Kunden-App | 8 | Login, Profile, Events, Rewards |
| Service-Terminal | 6 | Tischplan, Warteliste, Walk-In |
| System | 8 | Users, Backup, Import, Audit |
| Public | 6 | Booking Widget, Events, Confirm |
| Legacy | 5 | Schedule, MyShifts (teilweise redundant) |

### 3.2 Hardcoded Werte (KRITISCH)

**Staff.jsx (Zeile 90-96):**
```javascript
const ROLES = {
  service: { label: "Service", color: "bg-emerald-100..." },
  schichtleiter: { label: "Schichtleiter", color: "bg-amber-100..." },
  kueche: { label: "Küche", color: "bg-orange-100..." },  // ← KUECHE
  bar: { label: "Bar", color: "bg-violet-100..." },
  aushilfe: { label: "Aushilfe", color: "bg-gray-100..." },
};
```

**Schedule.jsx (Zeile 80-83):**
```javascript
const ROLE_CONFIG = {
  service: { label: "Service", color: "#10b981" },
  kueche: { label: "Küche", color: "#f97316" },
  kitchen: { label: "Küche", color: "#f97316" },  // Alias!
  ...
};
```

**EmployeePWA.jsx (Zeile 628, 805):**
```javascript
{todayShift.role || "Service"}  // Hardcoded Fallback
```

**constants.js (Zeile 97-103):**
```javascript
export const DEPARTMENT_LABELS = {
  service: "Service",
  kitchen: "Küche",  // ← KITCHEN (englisch)
  reinigung: "Reinigung",
  ...
};
```

### 3.3 Datenquellen

| Seite | API-Endpunkte | Lokale Daten |
|-------|---------------|--------------|
| Dashboard.jsx | `/api/events/dashboard/*`, `/api/reservations/*` | LOAD_THRESHOLDS |
| Staff.jsx | `/api/staff/members`, `/api/staff/work-areas` | ROLES, STATUS_CONFIG |
| Schedule.jsx | `/api/staff/*`, `/api/shifts/*` | ROLE_CONFIG, DEPARTMENT_GROUPS |
| Events.jsx | `/api/events/*` | CATEGORY_CONFIG |
| BookingWidget.jsx | `/api/public/restaurant-info`, `/api/public/book` | — |

### 3.4 Cross-Domain Zugriffe

| Seite | Primär-Domäne | Fremdzugriffe |
|-------|---------------|---------------|
| Dashboard.jsx | Reservierungen | Events (Summary), Guests |
| Staff.jsx | Mitarbeiter | Work Areas |
| ShiftsAdmin.jsx | Schichten | Staff Members, Templates, Events |
| Events.jsx | Events | Event Bookings, Customers |

---

## 4. Datenbank-Analyse

### 4.1 Collection-Klassifikation

#### Konfigurationsdaten (SEED-fähig)
| Collection | Writer | Reader | Seed? |
|------------|--------|--------|-------|
| `opening_hours_master` | opening_hours | opening_hours, reservation_* | ✅ |
| `opening_hours_periods` | opening_hours | opening_hours, reservation_* | ✅ |
| `shift_templates` | staff, shift_migration | staff, shifts_v2 | ✅ |
| `reservation_slot_rules` | reservation_slots | reservation_slots | ✅ |
| `reservation_options` | reservation_config | server.py | ✅ |
| `reservation_slot_exceptions` | reservation_slots | reservation_slots | ✅ |
| `system_settings` | system_settings | multiple | ✅ |
| `payment_rules` | payment | payment | ❌ |
| `work_areas` | staff | staff, shifts_v2 | ❌ |
| `areas` | server.py | server.py, reservation | ❌ |
| `tables` | table, import | table, reservation | ❌ |
| `table_combinations` | table, import | table | ❌ |

#### Operative Daten (NICHT seed-fähig)
| Collection | Writer | Reader | Volumen |
|------------|--------|--------|---------|
| `reservations` | server.py | multiple | HOCH |
| `events` | events, import | events, dashboard, ai | MITTEL |
| `staff_members` | staff, import | multiple | MITTEL |
| `shifts` | staff, shifts_v2 | multiple | HOCH |
| `schedules` | staff | staff | MITTEL |
| `time_sessions` | timeclock | timeclock, shifts_v2 | HOCH |
| `customers` | loyalty | loyalty, marketing | MITTEL |
| `event_bookings` | events | events | MITTEL |
| `payment_transactions` | payment | payment | MITTEL |

#### Audit/Logging
| Collection | Writer | Reader | Retention |
|------------|--------|--------|-----------|
| `audit_logs` | core/audit | audit UI | Unbegrenzt |
| `message_logs` | marketing | marketing | Unbegrenzt |
| `ai_logs` | ai_assistant | — | Unbegrenzt |
| `import_logs` | import | import | Unbegrenzt |
| `staff_import_runs` | staff_import | staff_import | Unbegrenzt |

### 4.2 Key-Inkonsistenzen

| Feld | Wert A | Wert B | Betroffene Collections |
|------|--------|--------|------------------------|
| Role/Department | `kueche` | `kitchen` | staff_members, shifts, shift_templates |
| Status | `aktiv`/`inaktiv` | `active: true/false` | staff_members, shift_templates |
| Archived | `archived: true` | `archived: false` | Alle |

### 4.3 Verwaiste/Überladene Collections

**Potentiell veraltet:**
- `opening_hours` (Legacy, ersetzt durch `opening_hours_periods`)
- `settings` (teilweise durch `system_settings` ersetzt)
- `schedules` (unklar ob noch aktiv genutzt)

**Überladen:**
- `staff_members` (95 Zugriffe, sehr viele Felder)
- `events` (87 Zugriffe, komplexe Struktur)

---

## 5. Modulgrenzen & Konflikte

### 5.1 Modul: 10_COCKPIT

**Verantwortung:**
- System-Einstellungen
- Öffnungszeiten-Verwaltung
- Seed Backup & Restore
- Dashboard-Widgets

**Gehört NICHT dazu:**
- Operative Reservierungsdaten
- Mitarbeiterdaten
- Event-Daten

**Grenzüberschreitungen:**
- `server.py` enthält viel Cockpit-Logik direkt (Dashboard-Endpoints)
- `backup_module.py` exportiert ALLE Collections (nicht nur Konfig)

### 5.2 Modul: 20_RESERVIERUNG (FREEZE)

**Verantwortung:**
- Reservierungs-CRUD
- Kapazitätsberechnung
- Slot-Generierung
- Tischplan

**Gehört NICHT dazu:**
- Event-Buchungen (→ 40_EVENTS)
- Zahlungen (→ Payment)

**Grenzüberschreitungen:**
- `events_module.py` schreibt in `reservations` für Event-Reservierungen
- `table_module.py` liest Reservierungsstatus

**Status:** FREEZE dokumentiert in `/app/docs/MODUL_20_FREEZE.md`

### 5.3 Modul: 30_MITARBEITER

**Verantwortung:**
- Mitarbeiter-CRUD
- Schichtplanung
- Zeiterfassung
- Abwesenheiten/Dokumente

**Gehört NICHT dazu:**
- Öffnungszeiten (→ Cockpit)
- Event-Verknüpfung (→ Events)

**Grenzüberschreitungen:**
- `staff_module.py` ist überladen (143KB, 3800+ Zeilen)
- Schicht-Templates werden sowohl in `staff_module.py` als auch `shift_template_migration.py` verwaltet
- `shifts_v2_module.py` parallel zu Legacy-Logik in `staff_module.py`

### 5.4 Modul: 40_EVENTS

**Verantwortung:**
- Event-CRUD
- Event-Buchungen
- WordPress-Sync
- Pricing/Varianten

**Gehört NICHT dazu:**
- Reservierungen ohne Event
- Mitarbeiter-Schichten

**Grenzüberschreitungen:**
- Event-Buchungen erstellen Reservierungen (→ 20_RESERVIERUNG)
- Dashboard-Summary greift auf Events zu

### 5.5 Kopplungsmatrix

```
              COCKPIT  RESERV  MITARB  EVENTS  KUNDEN  MARKET  TECHNIK
COCKPIT         —       READ    READ    READ    —       —       READ
RESERVIERUNG   READ      —      —       READ    —       —       —
MITARBEITER    READ     —        —      READ    —       —       —
EVENTS         READ    WRITE    READ     —      READ    —       —
KUNDEN         READ     —       —       READ     —      READ    —
MARKETING      READ     —       —       READ    READ     —      —
TECHNIK        READ     —       READ    READ    —       —        —
```

---

## 6. Source-of-Truth Bewertung

### 6.1 Öffnungszeiten

| Frage | Antwort |
|-------|---------|
| **Single Source of Truth?** | ✅ JA: `opening_hours_periods` + `opening_hours_master` |
| **Resolver-Funktion?** | ✅ JA: `calculate_effective_hours()` in `opening_hours_module.py` |
| **Mehrfachdefinitionen?** | ⚠️ Legacy `opening_hours` Collection existiert noch |
| **Frontend-Logik?** | ✅ NEIN: Kommt alles aus API |

### 6.2 Rollen / Departments

| Frage | Antwort |
|-------|---------|
| **Single Source of Truth?** | ❌ NEIN: 3 Enum-Definitionen, Frontend-Hardcodings |
| **Kanonische Keys?** | ⚠️ TEILWEISE: `CanonicalDepartment` in `shift_template_migration.py` |
| **Mehrfachdefinitionen?** | ❌ JA: `kueche` vs `kitchen` inkonsistent |
| **Frontend-Logik?** | ❌ JA: ROLES in Staff.jsx, ROLE_CONFIG in Schedule.jsx |

**EMPFEHLUNG:** Zentrale `CANONICAL_ROLES` Konstante im Backend, Frontend lädt aus API

### 6.3 Events / Aktionen

| Frage | Antwort |
|-------|---------|
| **Single Source of Truth?** | ✅ JA: `events` Collection |
| **Kategorie-Enum?** | ✅ JA: `ContentCategory` in `events_module.py` |
| **Mehrfachdefinitionen?** | ⚠️ TEILWEISE: `CATEGORY_CONFIG` in Events.jsx |
| **Frontend-Logik?** | ⚠️ TEILWEISE: Label-Mappings hardcoded |

### 6.4 Mitarbeiter

| Frage | Antwort |
|-------|---------|
| **Single Source of Truth?** | ✅ JA: `staff_members` Collection |
| **Rollen-Feld?** | ⚠️ MIGRATION: `role` → `roles[]` |
| **Mehrfachdefinitionen?** | ❌ NEIN |
| **Frontend-Logik?** | ⚠️ JA: Status/Rollen-Labels hardcoded |

### 6.5 Schichten

| Frage | Antwort |
|-------|---------|
| **Single Source of Truth?** | ⚠️ KONFLIKT: `shifts` + `schedules` + V2-Logik |
| **Template-Source?** | ⚠️ TEILWEISE: `shift_templates` + Migration-Logik |
| **Mehrfachdefinitionen?** | ❌ JA: V1 in `staff_module.py`, V2 in `shifts_v2_module.py` |
| **Frontend-Logik?** | ❌ JA: Schicht-Erstellung lokal berechnet |

### 6.6 KPIs

| Frage | Antwort |
|-------|---------|
| **Single Source of Truth?** | ⚠️ FRAGMENTIERT: `pos_daily_metrics`, `pos_z_reports_raw`, `pos_daily_kpis` |
| **Aggregation?** | Backend (`pos_mail_module.py`, `pos_zreport_module.py`) |
| **Mehrfachdefinitionen?** | ⚠️ JA: Tägliche vs. monatliche Metriken getrennt |
| **Frontend-Logik?** | ✅ NEIN |

### 6.7 Opt-ins / Kommunikation

| Frage | Antwort |
|-------|---------|
| **Single Source of Truth?** | ✅ JA: `customers.marketing_opt_in`, `guests.opt_in_status` |
| **Mehrfachdefinitionen?** | ⚠️ JA: Kunden vs. Gäste getrennt |
| **Frontend-Logik?** | ✅ NEIN |

---

## 7. Kritische Risiken

### 7.1 HOCH: Role/Department Inkonsistenz

**Problem:** `kueche` vs `kitchen` in verschiedenen Modulen
**Auswirkung:** Schicht-Zuweisung kann fehlschlagen, Reports inkorrekt
**Betroffene Dateien:**
- `staff_module.py` (ShiftRole.KUECHE)
- `shifts_v2_module.py` (ShiftRole.KITCHEN)
- `Staff.jsx`, `Schedule.jsx` (beide Varianten)

**Lösung:** Migration auf `CANONICAL_ROLES` mit Alias-Layer

### 7.2 HOCH: staff_module.py Überlastung

**Problem:** 143KB, 3800+ Zeilen, 95 DB-Zugriffe
**Auswirkung:** Schwer wartbar, hohe Kopplung, Testbarkeit gering
**Risiko:** Änderungen können unbeabsichtigte Seiteneffekte haben

**Lösung:** Refactoring in Sub-Module (NICHT JETZT)

### 7.3 MITTEL: Schicht V1/V2 Parallelität

**Problem:** Beide Systeme aktiv, keine klare Migration
**Auswirkung:** Doppelte Datenpflege, inkonsistente Zustände möglich
**Betroffene Dateien:**
- `staff_module.py` (V1-Logik)
- `shifts_v2_module.py` (V2-Logik)

**Lösung:** V1 deprecaten, V2 als Source of Truth

### 7.4 MITTEL: Seed-System Unvollständig

**Problem:** SEED_COLLECTIONS deckt nicht alle Konfigdaten ab
**Fehlende Collections:**
- `tables`, `table_combinations`
- `work_areas`, `areas`
- `payment_rules`
- `reminder_rules`

**Lösung:** SEED_COLLECTIONS erweitern (nach Stabilisierung)

### 7.5 NIEDRIG: Frontend-Hardcodings

**Problem:** Labels, Farben, Status-Mappings in JSX hardcoded
**Auswirkung:** Änderungen erfordern Frontend-Deployment
**Lösung:** API-Endpunkt für UI-Konfiguration

---

## 8. Stabilisierungsempfehlung (Prioritäten)

### PRIORITÄT 1: Role/Department Normalisierung

**Scope:** Backend + Frontend
**Aufwand:** 2-3 Tage
**Ziel:** Single Source of Truth für Rollen

**Schritte:**
1. `CANONICAL_ROLES` Konstante in Backend definieren
2. API-Endpunkt `/api/config/roles` erstellen
3. Frontend: Alle Hardcodings durch API-Daten ersetzen
4. Migration: `role` → `roles[]` im Staff Import abschließen

### PRIORITÄT 2: Schicht-System Konsolidierung

**Scope:** Backend
**Aufwand:** 3-5 Tage
**Ziel:** Klare V2-Migration, V1-Deprecation

**Schritte:**
1. V1-Endpunkte als deprecated markieren
2. V2 als alleinige Schreibquelle
3. `schedules` Collection evaluieren (löschen oder migrieren)

### PRIORITÄT 3: staff_module.py Entflechtung

**Scope:** Backend
**Aufwand:** 5-7 Tage (kann warten)
**Ziel:** Kleinere, fokussierte Module

**Schritte:**
1. Schicht-Logik → `shifts_module.py` (separates Modul)
2. Template-Logik → `shift_template_module.py`
3. HR-Felder → `staff_hr_module.py`
4. staff_module.py auf CRUD reduzieren

### PRIORITÄT 4: Seed-System Vervollständigung

**Scope:** Backend
**Aufwand:** 1-2 Tage
**Ziel:** Alle Konfig-Daten exportierbar

**Schritte:**
1. `tables`, `table_combinations` zu SEED_COLLECTIONS
2. `work_areas`, `areas` zu SEED_COLLECTIONS
3. Restore-Validierung erweitern

---

## 9. Gesamturteil

### Ist das System grundsätzlich gesund?

**JA, mit Einschränkungen.**

Das System ist funktional, produktiv und hat eine klare modulare Struktur. Die Kernfunktionen (Reservierungen, Events, Mitarbeiter) arbeiten korrekt. Die Architektur ist nachvollziehbar und erweiterbar.

**Jedoch:**
- Historisch gewachsene Inkonsistenzen (kueche/kitchen)
- Überlastete Module (staff_module.py)
- Parallele Systeme (V1/V2 Schichten)

### Sind die Probleme reparabel ohne Neubau?

**JA.**

Alle identifizierten Probleme sind durch gezielte Refactorings lösbar:
- Enum-Konsolidierung: 1-2 Tage
- Frontend-Hardcodings: 1-2 Tage
- Module-Splitting: 5-7 Tage (kann inkrementell)
- Seed-Erweiterung: 1-2 Tage

Kein Neubau erforderlich. Das Fundament (FastAPI, MongoDB, React) ist solide.

### Welche Bereiche MÜSSEN stabilisiert werden?

1. **Role/Department Normalisierung** – PFLICHT vor neuen Features
2. **Schicht V1/V2 Klärung** – PFLICHT vor Dienstplan-Erweiterungen
3. **Seed-System** – EMPFOHLEN für sicheres Restore

### Welche Module gelten als „reif / eingefroren"?

| Modul | Status | Begründung |
|-------|--------|------------|
| 20_RESERVIERUNG | 🔒 FREEZE | Produktiv, dokumentiert, stabil |
| 40_EVENTS | ⚠️ SEMI-FREEZE | Funktional, WordPress-Sync aktiv |
| 50_KUNDEN (Loyalty) | ⚠️ SEMI-FREEZE | Grundfunktion stabil |
| 10_COCKPIT (Seeds) | ⏳ IN ARBEIT | Backup funktioniert, Restore WIP |
| 30_MITARBEITER | ⏳ AKTIV | V2-Migration läuft |
| 70_TECHNIK (POS) | ✅ STABIL | Automatisiert, läuft |

---

**FAZIT:** Das System ist produktionsreif und erweiterbar. Die identifizierten Schwächen sind technische Schulden, keine fundamentalen Architekturprobleme. Mit den empfohlenen Stabilisierungsmaßnahmen (Priorität 1-2) ist das System bereit für weitere Feature-Entwicklung.
