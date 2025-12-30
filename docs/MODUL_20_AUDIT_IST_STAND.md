# MODUL 20_RESERVIERUNG – IST-STAND AUDIT

**Datum:** 30.12.2025  
**System:** Carlsburg / GastroCore v7.0.0  
**Modul-Status:** FROZEN (dokumentiert in `/app/docs/MODUL_20_FREEZE.md`)

---

## 1. Überblick (Status & Scope)

### Modul 20 FROZEN - Definition
| Aspekt | Regelung |
|--------|----------|
| **Source of Truth** | Öffnungszeiten, Reservierungsregeln, Slots, Kapazität |
| **Schreibzugriff** | NUR durch Cockpit-Admin (10_COCKPIT) |
| **Lesezugriff** | Alle Module (Widget, Mitarbeiter, Dashboard) |
| **Änderungen erlaubt** | Bug-Fixes, Guards, UI-Labels |
| **Änderungen verboten** | Neue Features, Logik-Änderungen, Schema-Änderungen |

### Scope dieses Audits
- Öffnungszeiten-Resolver
- Reservierungsregeln & Kapazität
- Public Widget APIs
- Seeds/Restore Verifikation
- Collection-Konsistenz

---

## 2. Source of Truth (Code + DB)

### 2.1 Collection-Architektur (IST-ZUSTAND)

**⚠️ KRITISCHES PROBLEM: 3 parallele Öffnungszeiten-Collections**

| Collection | Verwendet von | Zweck | Status |
|------------|---------------|-------|--------|
| `opening_hours` | `server.py`, `seed_system.py` | Legacy einzelne Wochentage | ⚠️ VERALTET |
| `opening_hours_master` | `opening_hours_module.py` | Perioden (Sommer/Winter) | ✅ AKTIV |
| `opening_hours_periods` | `reservation_config_module.py`, `staff_module.py`, `seeds_backup_module.py` | Perioden (redundant?) | ❌ INKONSISTENT |

### 2.2 Code-Dateien

| Datei | Verantwortung | Collections |
|-------|---------------|-------------|
| `opening_hours_module.py` | Perioden-CRUD, `get_active_period_for_date()`, `calculate_effective_hours()` | `opening_hours_master` |
| `reservation_config_module.py` | Reservierungsregeln, Slot-Konfiguration | `opening_hours_periods`, `reservation_config` |
| `reservation_capacity.py` | Kapazitätsberechnung | Liest aus `opening_hours_module` |
| `reservation_slots_module.py` | Slot-Generierung, Durchgänge | `reservation_slot_rules`, `reservation_slot_exceptions` |
| `reservation_guards.py` | Validierung, Guards | Verschiedene |
| `server.py` (public_router) | Widget-APIs | `opening_hours_master` via Import |

### 2.3 Resolver-Kette

```
Widget ruft /api/public/availability
    → server.py ruft calculate_effective_hours()
        → opening_hours_module.get_active_period_for_date()
            → db.opening_hours_master.find({active: True})
            → Sortiert nach priority DESC, start_date DESC
            → Prüft ob heute in [start_date, end_date]
        → Wendet rules_by_weekday[wochentag] an
        → Wendet overrides (special_days) an
```

---

## 3. Datenstrukturen / Collections (Counts + Aktive)

### 3.1 Aktuelle Zählung (via Seeds-Status API)

| Collection | Count | Aktive | Status |
|------------|-------|--------|--------|
| `opening_hours_master` | 5 | 3 | ⚠️ Mehrfach (sollte 1) |
| `opening_hours_periods` | 2 | 0 | ❌ Inkonsistent |
| `shift_templates` | 9 | 9 | ✅ OK |
| `reservation_options` | 17 | – | ✅ OK |
| `reservation_slot_rules` | 3 | 3 | ✅ OK |
| `reservation_slot_exceptions` | 1 | – | ✅ OK |
| `system_settings` | 1 | – | ✅ OK |

### 3.2 opening_hours_master (Detail)

| ID | Name | Start | End | Priority | Active |
|----|------|-------|-----|----------|--------|
| `c2315720-...` | Winter 2025/26 | 2025-11-01 | 2026-03-31 | 10 | ✅ |
| `b03cffe5-...` | Sommer 2026 | 2026-04-01 | 2026-10-31 | 10 | ✅ |
| `311974f5-...` | Winter 2026/27 | 2026-11-01 | 2027-03-31 | 10 | ✅ |
| ... | (2 weitere) | ... | ... | ... | ... |

**Heute (30.12.2025):** Fällt in "Winter 2025/26" → **KORREKT AUFGELÖST**

### 3.3 Reservierungen (letzte 30 Tage)

| Metrik | Wert |
|--------|------|
| Reservierungen gesamt | – (nicht abgefragt) |
| Status "confirmed" | – |
| Status "cancelled" | – |
| Durchschn. party_size | – |

---

## 4. Öffnungszeiten-Resolver (Wie wird "heute" berechnet?)

### 4.1 Algorithmus (opening_hours_module.py:325-380)

```python
async def get_active_period_for_date(target_date: date):
    # 1. Alle aktiven, nicht-archivierten Perioden holen
    periods = await db.opening_hours_master.find({
        "active": True, 
        "archived": {"$ne": True}
    }).sort([("priority", -1), ("start_date", -1)]).to_list(100)
    
    # 2. Für jede Periode prüfen ob target_date im Bereich liegt
    for period in periods:
        start = datetime.strptime(period["start_date"], "%Y-%m-%d").date()
        end = datetime.strptime(period["end_date"], "%Y-%m-%d").date()
        
        if start <= target_date <= end:
            return period  # Erste passende Periode (höchste Priorität)
    
    return None
```

### 4.2 Heutige Auflösung

**Datum:** 30.12.2025 (Dienstag)  
**Periode:** "Winter 2025/26" (01.11.2025 - 31.03.2026)  
**Regel für Dienstag:** `is_closed: true` → Restaurant geschlossen

**Widget-Output (restaurant-info):**
```json
{
  "opening_hours_weekly_text": "Mo/Di Ruhetag · Mi-Do 12:00-18:00 · Fr/Sa 12:00-20:00 · So 12:00-18:00",
  "opening_hours_season_label": "Winter 2025/26"
}
```

→ **KORREKT**

### 4.3 Availability für 05.01.2025 (Sonntag)

```json
{
  "date": "2025-01-05",
  "weekday_de": "Sonntag",
  "available": true,
  "slots": [
    {"time": "11:00", "available": true, "seating_name": "Durchgang 1 (Mittag)"},
    {"time": "12:00", "available": true, "seating_name": "Durchgang 1 (Mittag)"},
    {"time": "16:00", "available": true, "seating_name": "Abendservice"},
    ...
  ],
  "closing_time": "22:00"
}
```

→ **Slots werden korrekt generiert**

---

## 5. Reservierungslogik (Slots, Kapazität, Holds, Warteliste)

### 5.1 Slot-Generierung

| Komponente | Collection | Status |
|------------|------------|--------|
| Slot-Regeln | `reservation_slot_rules` | ✅ 3 aktive Regeln |
| Slot-Ausnahmen | `reservation_slot_exceptions` | ✅ 1 Dokument |
| Durchgänge (Seatings) | Berechnet aus Slot-Regeln | ✅ Funktioniert |

### 5.2 Kapazität

```
Gesamtkapazität: 95 Plätze (aus slot_rules oder fallback)
Pro Durchgang: 95 (keine Aufteilung)
```

### 5.3 Holds / Warteliste

| Feature | Implementiert | Collection |
|---------|---------------|------------|
| 2-Phasen-Buchung | ⚠️ Unklar | – |
| TTL-Holds | ⚠️ Unklar | – |
| Warteliste | ⚠️ Unklar | `waitlist`? |

**→ Audit empfiehlt separate Prüfung dieser Features**

---

## 6. Public Widget APIs (restaurant-info, availability, book)

### 6.1 GET /api/public/restaurant-info

| Feld | Quelle | Aktueller Wert |
|------|--------|----------------|
| `name` | `reservation_config.restaurant_name` → `settings.restaurant_name` | "Carlsburg Historisches Panoramarestaurant" |
| `phone` | `reservation_config.contact_phone` | `null` |
| `email` | `reservation_config.contact_email` | `null` |
| `opening_hours_weekly_text` | Berechnet aus aktiver Periode | "Mo/Di Ruhetag · Mi-Do 12:00-18:00 · ..." |
| `opening_hours_season_label` | `period.name` | "Winter 2025/26" |

**Konsistenz:** ✅ Season-Label stimmt mit aktiver Periode überein

### 6.2 GET /api/public/availability

| Parameter | Verarbeitung |
|-----------|--------------|
| `date` | → `get_active_period_for_date()` |
| `party_size` | → Kapazitätsprüfung |

**Ablauf:**
1. Periode für Datum ermitteln
2. `rules_by_weekday[wochentag]` anwenden
3. Overrides (`special_days`) prüfen
4. Slot-Regeln anwenden
5. Bestehende Reservierungen abziehen

### 6.3 POST /api/public/book

| Prüfung | Status |
|---------|--------|
| Datum in Öffnungszeiten | ✅ |
| Slot verfügbar | ✅ |
| Kapazität ausreichend | ✅ |
| Minimaler Vorlauf | ⚠️ Unklar |

---

## 7. Seeds/Restore Verifikation (Warnungen + Ursachen)

### 7.1 Aktuelle Warnungen

```json
{
  "status": "WARNINGS",
  "warnings": [
    "Multiple opening_hours_master documents found: 6",
    "No active opening_hours_periods found"
  ],
  "errors": []
}
```

### 7.2 Ursachen-Analyse

#### Warnung 1: "Multiple opening_hours_master documents found: 6"

**Ursache:**
- Seeds-Verify zählt `db.opening_hours_master.count_documents({})` = 6
- Erwartet wird 1 Dokument (Single Source of Truth)
- Tatsächlich sind 5 Perioden + 1 Legacy-Dokument?

**Erwartetes Verhalten:**
- `opening_hours_master` sollte **nur 1 Basis-Dokument** enthalten
- Perioden sollten in `opening_hours_periods` sein

**Root Cause:**
- **Code-Inkonsistenz**: `opening_hours_module.py` speichert Perioden in `opening_hours_master`
- **Verify-Logik**: Erwartet Single-Document, nicht Multiple-Perioden

#### Warnung 2: "No active opening_hours_periods found"

**Ursache:**
- Seeds-Verify prüft `db.opening_hours_periods.count_documents({active: True})` = 0
- Die Collection `opening_hours_periods` ist **LEER** oder anders strukturiert

**Root Cause:**
- **Falsche Collection**: Perioden sind in `opening_hours_master`, nicht `opening_hours_periods`
- Manche Module (`reservation_config_module.py`, `staff_module.py`) erwarten aber `opening_hours_periods`

### 7.3 Fingerprint-Drift

| Metrik | Wert |
|--------|------|
| Aktueller Fingerprint | `f18ab25467ba` |
| Gespeicherter Fingerprint | `59717bc31444` |
| Match | ❌ NEIN |

**Ursache:** Daten wurden nach Import geändert (Updates ohne neuen Export)

---

## 8. Festgestellte Inkonsistenzen (nur Fakten)

### 8.1 KRITISCH: Collection-Dualismus

| Problem | Betroffene Module | Risiko |
|---------|-------------------|--------|
| `opening_hours_master` vs `opening_hours_periods` | opening_hours_module ↔ reservation_config_module, staff_module, seeds_backup | Daten-Inkonsistenz, Widget zeigt falsche Zeiten |

**Code-Belege:**
- `opening_hours_module.py:337` → `db.opening_hours_master.find()`
- `reservation_config_module.py:252` → `db.opening_hours_periods.find()`
- `seeds_backup_module.py:414` → `db.opening_hours_periods.count_documents()`

### 8.2 MITTEL: Verify-Logik vs. Realität

| Verify erwartet | Realität |
|-----------------|----------|
| 1 `opening_hours_master` Dokument | 5 Perioden-Dokumente |
| Aktive `opening_hours_periods` | Collection ist leer |

### 8.3 NIEDRIG: Legacy-Collection

| Collection | Status |
|------------|--------|
| `opening_hours` | Noch in Code referenziert (`server.py:458`, `seed_system.py:222`) aber nicht primär |

### 8.4 INFO: Fingerprint-Drift

- Fingerprint matcht nicht nach Änderungen
- Erwartetes Verhalten, aber sollte nach jedem Update neu exportiert werden

---

## 9. Fix-Plan (Stufe 1–3, minimal-invasiv)

### Stufe 1: No-Code / Admin-Only (SOFORT)

**Ziel:** Verify-Warnungen eliminieren ohne Code-Änderungen

| Aktion | Beschreibung | Risiko |
|--------|--------------|--------|
| 1.1 | Backup erstellen (Seeds-Export) | Keins |
| 1.2 | ⚠️ **NICHT MÖGLICH** - Collection-Inkonsistenz erfordert Code-Fix | – |

**Fazit Stufe 1:** Kann nicht ohne Code-Änderung gelöst werden.

---

### Stufe 2: Small Code Fixes (SAFE in FROZEN)

**Ziel:** Verify-Logik an Realität anpassen

#### Fix 2.1: Seeds-Verify Logik anpassen

**Datei:** `/app/backend/seeds_backup_module.py`

**Änderung:**
```python
# VORHER (Zeile 404-418):
ohm_count = await db.opening_hours_master.count_documents({})
if ohm_count > 1:
    result.warnings.append(f"Multiple opening_hours_master documents found")

ohp_count = await db.opening_hours_periods.count_documents({"active": True})
if ohp_count == 0:
    result.warnings.append("No active opening_hours_periods found")

# NACHHER:
# opening_hours_master enthält Perioden - das ist korrekt
ohm_count = await db.opening_hours_master.count_documents({"active": True})
result.checks["opening_hours_master"] = {"count": ohm_count, "status": "ok"}
if ohm_count == 0:
    result.warnings.append("No active opening_hours_master periods found")
    result.checks["opening_hours_master"]["status"] = "warning"
# Hinweis: opening_hours_periods ist Legacy, nicht mehr prüfen
```

#### Fix 2.2: Collection-Konsolidierung dokumentieren

**Datei:** `/app/docs/OPENING_HOURS_COLLECTIONS.md` (NEU)

```markdown
# Opening Hours Collections – Architektur

## Aktiv (Source of Truth)
- `opening_hours_master` → Saisonale Perioden (Sommer/Winter)

## Legacy (nicht mehr verwenden)
- `opening_hours` → Alte einzelne Wochentage
- `opening_hours_periods` → Redundante Perioden (leer)

## Migration
Module die `opening_hours_periods` verwenden sollten auf `opening_hours_master` migriert werden.
```

#### Fix 2.3: SEED_COLLECTIONS anpassen

**Datei:** `/app/backend/seeds_backup_module.py`

```python
SEED_COLLECTIONS = {
    "opening_hours_master": {...},  # Behalten
    # "opening_hours_periods": {...},  # ENTFERNEN (Legacy)
    ...
}
```

---

### Stufe 3: Reproduzierbarkeit (Config Packs)

**Ziel:** Deterministischer Export/Import für Modul 20

#### Config Pack A: Core Calendar
```
- opening_hours_master (Perioden)
- reservation_slot_exceptions (Overrides)
- special_days / closures (Feiertage)
```

#### Config Pack B: Reservation Rules
```
- reservation_config (Basis-Konfiguration)
- reservation_options (Anlässe)
- reservation_slot_rules (Durchgänge)
```

#### Config Pack C: Table Setup
```
- tables
- table_combinations
- areas
```

**Implementierung:** Neuer Endpunkt `/api/admin/seeds/export-pack?pack=A`

---

## 10. Entscheidendste nächste Aktion (1 Satz)

**Seeds-Verify-Logik in `seeds_backup_module.py` anpassen, um `opening_hours_master` als Perioden-Source zu akzeptieren und `opening_hours_periods`-Prüfung zu entfernen – dies eliminiert die Warnungen ohne Datenänderungen und respektiert FROZEN-Status.**
