# Opening Hours Collections – Architektur & Source of Truth

**Stand:** 30.12.2025  
**System:** Carlsburg / GastroCore v7.0.0  
**Modul:** 20_RESERVIERUNG (FROZEN)

---

## 1. Zweck dieser Dokumentation

Diese Datei definiert **verbindlich**, welche MongoDB-Collection für Öffnungszeiten die Wahrheit ist.

**Problem (historisch):**
- 3 verschiedene Collections für ähnliche Daten entstanden
- Module verwendeten unterschiedliche Collections
- Seeds-Verify zeigte Warnungen wegen Collection-Inkonsistenz

**Diese Doku verhindert:**
- Nutzung falscher/veralteter Collections
- Doppelte Datenpflege
- Widget-Fehler durch inkonsistente Öffnungszeiten

---

## 2. Übersicht: Source of Truth

| Rang | Collection | Status | Beschreibung |
|------|------------|--------|--------------|
| **1** | `opening_hours_master` | **SOURCE OF TRUTH** | Saisonale Perioden (Sommer/Winter) mit `rules_by_weekday` |
| 2 | `opening_hours_periods` | ⚠️ LEGACY | Leer (0 Dokumente), wird von manchen Modulen noch referenziert |
| 3 | `opening_hours` | ❌ DEPRECATED | Alte Struktur für einzelne Wochentage |

### Eindeutige Regel

```
╔═══════════════════════════════════════════════════════════════════╗
║  Für alle Öffnungszeiten-Operationen:                             ║
║  → IMMER opening_hours_master verwenden                           ║
║  → NIEMALS opening_hours_periods oder opening_hours verwenden     ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

## 3. Collection-Details

### 3.1 `opening_hours_master` (SOURCE OF TRUTH)

| Aspekt | Details |
|--------|---------|
| **Zweck** | Saisonale Öffnungszeiten-Perioden (z.B. "Winter 2025/26", "Sommer 2026") |
| **Schema** | `id`, `name`, `start_date`, `end_date`, `priority`, `active`, `archived`, `rules_by_weekday` |
| **Aktueller Stand** | 6 Dokumente, 3 aktiv |
| **Schreibzugriff** | `opening_hours_module.py` |
| **Lesezugriff** | `opening_hours_module.py`, `server.py` (via Import) |
| **Public API** | `/api/public/restaurant-info`, `/api/public/availability` |

**Beispiel-Dokument:**
```json
{
  "id": "c2315720-xxxx-xxxx-xxxx",
  "name": "Winter 2025/26",
  "start_date": "2025-11-01",
  "end_date": "2026-03-31",
  "priority": 10,
  "active": true,
  "archived": false,
  "rules_by_weekday": {
    "monday": { "is_closed": true },
    "tuesday": { "is_closed": true },
    "wednesday": { "blocks": [{"start": "12:00", "end": "18:00"}] },
    ...
  }
}
```

### 3.2 `opening_hours_periods` (LEGACY)

| Aspekt | Details |
|--------|---------|
| **Zweck** | Sollte ursprünglich Perioden enthalten (redundant zu master) |
| **Aktueller Stand** | **0 Dokumente** (leer) |
| **Schreibzugriff** | `reservation_config_module.py` (schreibt, aber Collection bleibt leer) |
| **Lesezugriff** | `reservation_config_module.py`, `staff_module.py` |
| **Status** | ⚠️ Module referenzieren es, aber Daten kommen faktisch aus `opening_hours_master` |

**Migration erforderlich:** Siehe Abschnitt 7

### 3.3 `opening_hours` (DEPRECATED)

| Aspekt | Details |
|--------|---------|
| **Zweck** | Alte Struktur: 1 Dokument pro Wochentag |
| **Aktueller Stand** | Variabel (Legacy-Daten) |
| **Schreibzugriff** | `server.py`, `seed_system.py` (Legacy-Endpoints) |
| **Lesezugriff** | `server.py` (Legacy) |
| **Status** | ❌ Nicht mehr als Source verwenden |

---

## 4. Verbindliche Regeln

### ✅ DO (Pflicht)

| Regel | Begründung |
|-------|------------|
| Neue Features MÜSSEN `opening_hours_master` verwenden | Single Source of Truth |
| Resolver MUSS `get_active_period_for_date()` aus `opening_hours_module.py` nutzen | Korrekte Prioritäts-/Datumslogik |
| Perioden haben `active` UND `archived` Flags | Beide prüfen für aktive Perioden |
| Widget-Ausgabe MUSS aus `opening_hours_master` abgeleitet werden | Konsistenz |

### ❌ DON'T (Verboten)

| Regel | Konsequenz bei Verstoß |
|-------|------------------------|
| KEINE neuen Reads/Writes auf `opening_hours_periods` | Daten-Inkonsistenz |
| KEINE neuen Reads/Writes auf `opening_hours` | Legacy-Daten werden ignoriert |
| KEINE Hardcoded Öffnungszeiten im Frontend | Widget zeigt falsche Zeiten |
| KEINE direkte MongoDB-Abfrage ohne Resolver | Priorität/Datum-Logik wird umgangen |

---

## 5. Seeds/Verify-Logik

### 5.1 Aktuelle Checks (`seeds_backup_module.py`)

```python
# Check 1: opening_hours_master (enthält saisonale Perioden)
ohm_active_count = await db.opening_hours_master.count_documents({
    "active": True, 
    "archived": {"$ne": True}
})
# → Status OK wenn mindestens 1 aktive Periode existiert

# Check 2: opening_hours_periods (Legacy - nur Info)
ohp_count = await db.opening_hours_periods.count_documents({"active": True})
# → Status OK auch wenn 0 (Legacy-Collection wird ausgelaufen)
```

### 5.2 Warum mehrere `opening_hours_master` Dokumente OK sind

| Anzahl | Bedeutung | Status |
|--------|-----------|--------|
| 0 | Keine Perioden definiert | ⚠️ Warnung |
| 1 | Eine Periode (z.B. nur Sommer) | ✅ OK |
| 3+ | Mehrere Perioden (Sommer, Winter, Feiertage) | ✅ OK (empfohlen) |

**Architektur:** Jede Periode ist ein eigenes Dokument mit:
- `start_date` / `end_date` → Gültigkeitszeitraum
- `priority` → Bei Überlappung gewinnt höhere Priorität
- `active` → Nur aktive Perioden werden evaluiert

### 5.3 Was „active" bedeutet

```
active = true  → Periode wird bei Datumsabfrage berücksichtigt
active = false → Periode wird ignoriert (z.B. Entwurf)
archived = true → Periode ist archiviert und wird IMMER ignoriert
```

**Auflösungslogik:**
```python
periods = db.opening_hours_master.find({
    "active": True, 
    "archived": {"$ne": True}
}).sort([("priority", -1), ("start_date", -1)])

# Erste Periode deren [start_date, end_date] das Zieldatum enthält gewinnt
```

---

## 6. Public APIs & Output

### 6.1 GET /api/public/restaurant-info

**Endpoint:** `server.py:1556`

| Feld | Quelle | Beispiel |
|------|--------|----------|
| `name` | `reservation_config.restaurant_name` oder `settings.restaurant_name` | "Carlsburg Historisches Panoramarestaurant" |
| `opening_hours_weekly_text` | Berechnet aus aktiver Periode | "Mo/Di Ruhetag · Mi-Do 12:00-18:00 · Fr/Sa 12:00-20:00 · So 12:00-18:00" |
| `opening_hours_season_label` | `period.name` aus `opening_hours_master` | "Winter 2025/26" |

**Ablauf:**
```
1. get_active_period_for_date(heute) → Aktive Periode
2. period.rules_by_weekday → Wochentag-Regeln
3. Gruppierung gleicher Zeiten → Kompakter Text
```

### 6.2 GET /api/public/availability

**Endpoint:** `server.py` / `reservation_capacity.py`

| Parameter | Wirkung |
|-----------|---------|
| `date` | Bestimmt welche Periode und welcher Wochentag |
| `party_size` | Kapazitätsprüfung |

**Regeln die Verfügbarkeit beeinflussen:**
1. `opening_hours_master` → Ist der Tag geöffnet?
2. `reservation_slot_rules` → Welche Zeitslots gibt es?
3. `reservation_slot_exceptions` → Gibt es Overrides für dieses Datum?
4. `special_days` / `closures` → Ist es ein Feiertag/Schließtag?
5. Bestehende `reservations` → Restkapazität

---

## 7. Migrations-Plan (TODO)

### Phase 1: Audit (Erledigt ✅)
- [x] Alle `opening_hours_periods` Reads identifiziert
- [x] Seeds-Verify angepasst

### Phase 2: Code-Migration (Offen)

| Datei | Zeilen | Aktion |
|-------|--------|--------|
| `reservation_config_module.py` | 252, 271, 787, 801, 820, 833, 846, 863, 871, 886 | Auf `opening_hours_master` umstellen |
| `staff_module.py` | 2650, 2668, 2708 | Auf `opening_hours_master` umstellen |

**Migrationscode-Muster:**
```python
# VORHER (falsch)
period = await db.opening_hours_periods.find_one({"active": True})

# NACHHER (korrekt)
from opening_hours_module import get_active_period_for_date
from datetime import date
period = await get_active_period_for_date(date.today())
```

### Phase 3: Cleanup (Optional)
- [ ] Legacy-Collection `opening_hours_periods` leeren/löschen
- [ ] Legacy-Collection `opening_hours` deprecation-markieren
- [ ] SEED_COLLECTIONS bereinigen

---

## 8. FAQ / Typische Fehler

### ❓ Warum ist `opening_hours_periods` leer und trotzdem OK?

**Antwort:** Die Collection ist Legacy. Alle aktiven Perioden sind in `opening_hours_master`. Der Seeds-Verify akzeptiert 0 Dokumente in `opening_hours_periods` mit einem Info-Hinweis.

### ❓ Wie teste ich welche Öffnungszeiten „heute" gelten?

```bash
curl -s http://localhost:8001/api/public/restaurant-info | jq '{
  season: .opening_hours_season_label,
  hours: .opening_hours_weekly_text
}'
```

Oder im Code:
```python
from opening_hours_module import get_active_period_for_date
from datetime import date

period = await get_active_period_for_date(date.today())
print(f"Aktive Periode: {period['name']}")
print(f"Heute ({date.today().strftime('%A')}): {period['rules_by_weekday'].get('monday')}")
```

### ❓ Warum zeigt das Widget falsche Zeiten?

**Checkliste:**
1. Ist mindestens eine Periode in `opening_hours_master` aktiv?
2. Liegt heute im `start_date`–`end_date` Bereich einer aktiven Periode?
3. Ist `archived: false` für die Periode?
4. Hat die Periode `rules_by_weekday` für den aktuellen Wochentag?

### ❓ Wie lege ich eine neue Saison-Periode an?

**Via API:**
```bash
POST /api/opening-hours/periods
{
  "name": "Sommer 2027",
  "start_date": "2027-04-01",
  "end_date": "2027-10-31",
  "priority": 10,
  "active": true,
  "rules_by_weekday": { ... }
}
```

**Die Periode wird in `opening_hours_master` gespeichert.**

### ❓ Was passiert bei überlappenden Perioden?

Die Periode mit **höherer `priority`** gewinnt. Bei gleicher Priorität gewinnt die mit **neuerem `start_date`**.

---

## 9. Kontakt / Verantwortung

| Bereich | Verantwortlich |
|---------|----------------|
| `opening_hours_module.py` | Backend-Team |
| Seeds/Verify | Backend-Team |
| Widget-Integration | Frontend-Team |
| Diese Dokumentation | System-Architektur |

---

**Ende der Dokumentation**
