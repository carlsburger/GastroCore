# IST-ANALYSE: CARLSBURG COCKPIT
**Datum:** 2025-01-01 | **Modus:** READ-ONLY

---

## A) ÖFFNUNGSZEITEN – QUELLEN

| Quelle | Collection | Count | Status |
|--------|------------|-------|--------|
| opening_hours_master | `opening_hours_master` | 6 | ⚠️ PROBLEM: start/end_month_day = NULL |
| opening_hours_periods | `opening_hours_periods` | 2 | Vorhanden |
| closures | `closures` | 7 | ⚠️ 5 ohne Datum |
| reservation_slot_rules | `reservation_slot_rules` | 3 | ✅ Aktiv |
| reservation_slot_exceptions | `reservation_slot_exceptions` | 1 | ✅ Aktiv |

### opening_hours_master (6 Einträge)
ALLE haben `start_month_day: null` und `end_month_day: null`:

| Name | Priority | Mo | Di | Mi | Do | Fr | Sa | So |
|------|----------|----|----|----|----|----|----|-----|
| Sommer | 10 | 12-18 | 12-18 | 12-18 | 12-18 | 12-20 | 12-20 | 12-18 |
| Winter | 10 | zu | zu | 12-18 | 12-18 | 12-20 | 12-20 | 12-18 |
| Ostern | 10 | 11:30-20 | 11:30-20 | 11:30-18 | ... | ... | ... | 11:30-20 |
| Advent | 10 | - | - | 17:30-22 | ... | 11:30-22 | 11:30-22 | 11:30-20 |
| Spargelwochen | 10 | - | - | - | ... | 17:30-22 | 11:30-22 | 11:30-20 |
| Neujahr | 10 | zu | 11:30-20 | 12-18 | 12-18 | 12-20 | 12-20 | 12-18 |

**⚠️ KRITISCH:** Ohne gültige Datumsangaben kann das System NICHT bestimmen, welche Periode aktuell ist!

### reservation_slot_rules (3 Regeln)

| Name | Tage | generate_between | Priority | Active |
|------|------|------------------|----------|--------|
| Wochenende mit Durchgängen | Sa/So (5,6) | 11:30-18:30 | 20 | ✅ |
| Wochentags Standard | Mi/Do/Fr (2,3,4) | 12:00-18:30 | 10 | ✅ |
| Feiertags-Slots (Mo/Di) | Mo/Di (0,1) | 12:00-18:30 | 5 | ✅ |

### closures (7 Einträge)

| Datum | Reason | Scope | Status |
|-------|--------|-------|--------|
| NULL | Heiligabend | full_day | ⚠️ Kein Datum! |
| NULL | Silvester | full_day | ⚠️ Kein Datum! |
| NULL | Neujahr | full_day | ⚠️ Kein Datum! |
| NULL | Heiligabend (Updated Test) | full_day | ⚠️ Kein Datum! |
| NULL | Betriebsausflug (Test) | full_day | ⚠️ Kein Datum! |
| 2026-01-02 | Betriebsferien | full_day | ✅ OK |
| 2026-01-01 | Neujahr | full_day | ✅ OK |

---

## B) SLOT-LOGIK

### Slot-Generierung Flow
```
1. /api/public/availability?date=X&party_size=Y
2. → get_availability_for_date()
3. → Lädt reservation_slot_rules für Wochentag
4. → Generiert Slots basierend auf generate_between
5. → Filtert blocked_windows
6. → Prüft closures
7. → Gibt verfügbare Slots zurück
```

### Testfall: 2026-01-04 (Sonntag)
- **Schließzeit:** 18:00 (korrekt für Sonntag)
- **Letzte Buchung:** 16:30 (korrekt: 18:00 - 90min Aufenthalt)
- **Slots:** 11:00, 11:30, 12:00, 13:00, 13:30, 14:00, 16:00, 16:30
- **Status:** ✅ KORREKT

### Testfall: 2026-01-03 (Samstag)
- **Schließzeit:** 20:00
- **Letzte Buchung:** 18:30 (korrekt: 20:00 - 90min Aufenthalt)
- **Slots:** 11:00-18:30
- **Status:** ✅ KORREKT

---

## C) EVENTS

### Event-Quellen

| Quelle | Collection | Count | Status |
|--------|------------|-------|--------|
| Interne Events | `events` | 40 | ✅ Aktiv |
| WordPress Sync | `import_logs` | 5 Einträge | ⚠️ Alle status=NULL, 0 items |

### Event-Struktur
Events haben `dates: [...]` Array statt einzelnem `date` Feld:
- "Spareribs Sattessen" hat 37 Termine in einem Event-Objekt
- Das Frontend MUSS das `dates` Array verarbeiten, nicht ein einzelnes `date` Feld

### "Rippchen satt" Duplikat (09.01.2026)
- **Ursache:** KEIN Duplikat in DB - ein Event mit `dates: ["2026-01-09", ...]`
- **Wenn Duplikat in UI:** Frontend rendert möglicherweise mehrfach

### WordPress Sync Status
- 5 Einträge in `import_logs`
- Alle: `status: null`, `items_imported: 0`
- **Fazit:** WP Sync ist konfiguriert aber NICHT aktiv

---

## D) BILDER & ASSETS

### BookingWidget Bilder (Hardcoded)

| Typ | URL | Quelle |
|-----|-----|--------|
| Hero Background | customer-assets.emergentagent.com/.../K7A3951.jpg | Emergent CDN |
| Galerie 1 | images.unsplash.com/...terrace... | Unsplash |
| Galerie 2 | images.unsplash.com/...glasses... | Unsplash |
| Galerie 3 | images.unsplash.com/...potato... | Unsplash |
| Galerie 4 | images.unsplash.com/...mansion... | Unsplash |

### Event-Bilder (DB)
- 21 Bilder von `www.carlsburg.de`
- Werden von Events geladen, nicht vom Widget

---

## E) PRIORITÄTEN & ABHÄNGIGKEITEN

```
┌─────────────────────────────────────┐
│        /api/public/availability     │
└─────────────────┬───────────────────┘
                  │
    ┌─────────────┼─────────────┐
    ▼             ▼             ▼
┌────────┐  ┌──────────┐  ┌──────────┐
│closures│  │slot_rules│  │ events   │
│(7)     │  │(3)       │  │(40)      │
└────┬───┘  └────┬─────┘  └────┬─────┘
     │           │              │
     ▼           ▼              ▼
┌────────────────────────────────────┐
│        opening_hours_master        │
│   ⚠️ ALLE 6 OHNE DATUMSFILTER!     │
└────────────────────────────────────┘
```

### Auswertungsreihenfolge
1. `closures` prüfen (Tag gesperrt?)
2. `reservation_slot_rules` für Wochentag laden
3. `opening_hours_master` für Schließzeit (⚠️ nicht deterministisch ohne Daten!)
4. Slots generieren basierend auf Regeln

---

## F) ZUSAMMENFASSUNG

### WAS IST AKTIV?

| Komponente | Status | Details |
|------------|--------|---------|
| reservation_slot_rules | ✅ AKTIV | 3 Regeln für Mo-So |
| events | ✅ AKTIV | 40 Events mit dates Array |
| closures | ⚠️ TEILWEISE | 2 mit Datum, 5 ohne |
| opening_hours_master | ⚠️ BROKEN | 6 Perioden ohne Datumsfilter |
| WordPress Sync | ❌ INAKTIV | 0 importierte Items |

### WAS IST VORHANDEN ABER LEER/BROKEN?

| Komponente | Problem |
|------------|---------|
| opening_hours_master.start_month_day | NULL bei ALLEN 6 |
| opening_hours_master.end_month_day | NULL bei ALLEN 6 |
| closures.date | NULL bei 5 von 7 |
| import_logs.status | NULL bei allen |

### WAS BEEINFLUSST RESERVIERUNGEN WIRKLICH?

1. **reservation_slot_rules** - Bestimmt verfügbare Zeitfenster ✅
2. **closures (mit Datum)** - Blockiert 2 Tage ✅
3. **events** - Blockiert Slots während Events (wenn konfiguriert)
4. **opening_hours_master** - Bestimmt Schließzeit ⚠️ (nicht deterministisch)

---

## KRITISCHE BEFUNDE (P0)

1. **opening_hours_master ohne Datumsgrenzen**
   - ALLE 6 Perioden haben `start_month_day: null`
   - System kann nicht wissen ob "Sommer" oder "Winter" aktiv ist
   - → Erste passende Periode wird genommen (nicht deterministisch)

2. **5 Closures ohne Datum**
   - Heiligabend, Silvester, etc. ohne `date` Feld
   - Diese Sperren funktionieren NICHT

3. **SMTP_PASSWORD ist Platzhalter**
   - E-Mail-Versand funktioniert nicht
   - → Unabhängig von dieser Analyse

---

**ANALYSE ABGESCHLOSSEN. WARTE AUF FREIGABE FÜR ÄNDERUNGEN.**
