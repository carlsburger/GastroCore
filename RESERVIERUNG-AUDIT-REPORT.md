# 📋 RESERVIERUNG – KONFIGURATIONSAUDIT

**Datum:** 2025-12-23  
**Status:** READ-ONLY Analyse  
**Keine Änderungen vorgenommen**

---

## 1️⃣ IST-STAND ÜBERSICHT

### A) Datenbank-Collections

| Collection | Status | Daten | Fundstelle |
|------------|--------|-------|------------|
| `reservations` | ❌ FEHLT | - | Collection nicht angelegt |
| `guests` | ❌ FEHLT | - | Collection nicht angelegt |
| `reservation_config` | ❌ FEHLT | - | Config nur in-memory/fallback |
| `opening_hours_periods` | ❌ LEER | 0 | Collection existiert nicht |
| `closures` | ❌ LEER | 0 | Collection existiert nicht |
| `time_slot_configs` | ❌ FEHLT | - | Für Durchgänge/Sperrzeiten |
| `reminder_rules` | ✅ OK | 2 | 24h Email + 3h WhatsApp |
| `settings` | ✅ OK | 7 | No-Show Thresholds vorhanden |
| `tables` | ✅ OK | 49 | Mit seats_default/max |
| `table_combinations` | ✅ OK | 17 | Vollständig |
| `events` | ✅ OK | 21 | Mit dates, category, booking_hint |
| `waitlist` | ❌ FEHLT | - | Nicht implementiert |
| `payment_rules` | ❌ FEHLT | - | Stripe disabled |

### B) API-Endpoints

| Endpoint | Status | Beschreibung |
|----------|--------|--------------|
| `GET /api/reservation-config` | ✅ OK | Liefert Defaults |
| `PUT /api/reservation-config` | ✅ OK | Zum Konfigurieren |
| `GET /api/reservation-config/time-slots` | ✅ OK | Pro Wochentag |
| `POST /api/reservation-config/time-slots` | ✅ OK | Slots anlegen |
| `GET /api/reservation-config/available-slots/{date}` | ✅ OK | Verfügbare Slots |
| `GET /api/public/availability` | ✅ OK | Widget-Endpoint |
| `POST /api/public/book` | ✅ OK | Buchung anlegen |
| `GET /api/opening-hours/periods` | ✅ OK | Leere Liste (0 Perioden) |
| `POST /api/opening-hours/periods` | ✅ OK | Periode anlegen |
| `GET /api/closures` | ✅ OK | Leere Liste (0 Sperrtage) |
| `POST /api/closures` | ✅ OK | Sperrtag anlegen |
| `GET /api/guests` | ✅ OK | Leere Liste |
| `GET /api/guests/autocomplete` | ✅ OK | Suche implementiert |
| `GET /api/reservations` | ✅ OK | CRUD vorhanden |

### C) UI-Seiten

| Seite | Datei | LOC | Status |
|-------|-------|-----|--------|
| ReservationConfig | `ReservationConfig.jsx` | 743 | ✅ Vorhanden |
| OpeningHoursAdmin | `OpeningHoursAdmin.jsx` | ~1000 | ✅ Vorhanden |
| ServiceTerminal | `ServiceTerminal.jsx` | ~1100 | ✅ Vorhanden |
| BookingWidget | `BookingWidget.jsx` | ~500 | ✅ Vorhanden |
| Guests (CRM) | `Guests.jsx` | ~350 | ✅ Vorhanden |
| CancelReservation | `CancelReservation.jsx` | ~200 | ✅ Vorhanden |
| ConfirmReservation | `ConfirmReservation.jsx` | ~300 | ✅ Vorhanden |

---

## 2️⃣ CHECKLISTE: KONFIGURATION

### 2.1 Betriebslogik / Grundwerte

| Parameter | Soll | Ist | Status |
|-----------|------|-----|--------|
| Standard-Aufenthaltsdauer | 110 min | 110 min | ✅ OK |
| Buffer zwischen Slots | 10 min | 10 min | ✅ OK |
| min_advance_hours | konfigurierbar | 2 h | ✅ OK |
| max_advance_days | konfigurierbar | 90 Tage | ✅ OK |
| max_party_size | 20 | 20 | ✅ OK |
| max_total_capacity | variabel | 150 | ⚠️ Hardcoded, nicht Tisch-basiert |
| Kapazitätsmodell | Tisch-basiert | Bereichs-Cap | 🔴 **FALSCH** |

**Problem:** Kapazität ist auf 150 fixiert statt aus Tischen berechnet.  
**Ist:** `available_seats: 100` (Fallback-Wert)  
**Soll:** Summe aller `seats_default` der verfügbaren Tische

### 2.2 Öffnungszeiten-Regeln

| Prüfpunkt | Status | Details |
|-----------|--------|---------|
| Perioden Sommer/Winter | ❌ FEHLT | 0 Perioden in DB |
| Ruhetage Winter Mo/Di | ❌ FEHLT | Nicht konfiguriert |
| Override Feiertag→offen | ❌ FEHLT | Logik vorhanden, keine Daten |
| Sperrtage (24.12, 31.12) | ❌ FEHLT | 0 Closures in DB |
| UI für Sperrtage | ✅ OK | OpeningHoursAdmin.jsx |

**Aktueller Fallback:** 11:00-22:00 für alle Tage (hardcoded)

### 2.3 Reservierungs-Slots / Buchungszeiten

| Feature | Status | Details |
|---------|--------|---------|
| Slots pro Wochentag | ✅ OK | Endpoint + Datenmodell vorhanden |
| Sperrzeiten innerhalb Tag | ✅ OK | `blocked_ranges` Feld vorhanden |
| Manuell vs. Auto-Slots | ✅ OK | `use_manual_slots` Flag |
| Slot-Intervall | ✅ OK | Default 30 min, konfigurierbar |
| **Konfigurierte Slots** | ❌ LEER | Keine Daten in DB |

**Aktuell:** Auto-generierte Slots 11:00-22:00 alle 30 min (Fallback)

### 2.4 Events/Aktionen – Einfluss auf Slots

| Feature | Status | Details |
|---------|--------|---------|
| Events mit eigenem Buchungsmodus | ⚠️ TEILWEISE | `booking_required`, `booking_hint` vorhanden |
| Letzte à la carte 120 min vorher | ❌ FEHLT | Feld `last_alacarte_minutes_before` nicht in Events |
| Event-Cutoff Logik | ❌ FEHLT | Nicht implementiert |
| Event-Buchungen | ✅ OK | `/api/events/{id}/bookings` vorhanden |

**Fehlende Felder in Events:**
- `last_alacarte_minutes_before`
- `capacity` (Plätze pro Event)
- `requires_reservation` (Boolean)

### 2.5 Gastdaten / CRM-Basics

| Feature | Status | Details |
|---------|--------|---------|
| Autocomplete (Name/Tel/Email) | ✅ OK | Endpoint implementiert |
| Besuchszähler | ✅ OK | `visit_count` in Guest-Schema |
| Newsletter Opt-in | ⚠️ UNKLAR | Feld nicht gefunden |
| No-Show Greylist Threshold | ✅ OK | 2 (in Settings) |
| No-Show Blacklist Threshold | ✅ OK | 4 (in Settings) |
| Entsperrung/Rücknahme | ⚠️ MANUELL | Nur via DB oder Admin-Flag |

### 2.6 Kommunikation

| Feature | Status | Details |
|---------|--------|---------|
| SMTP | ✅ OK | IONOS konfiguriert |
| Email Templates | ✅ OK | DE/EN/PL vorhanden |
| Reminder Rules | ✅ OK | 24h Email + 3h WhatsApp |
| Storno-Link in Email | ✅ OK | `generate_cancel_token()` |
| WhatsApp Integration | ⚠️ STUB | Endpoint vorhanden, kein Provider |

### 2.7 Service-Workflow

| Feature | Status | Details |
|---------|--------|---------|
| Neu/Unbestätigt Counter | ✅ OK | ServiceTerminal filtert |
| 1-Klick Bestätigen | ✅ OK | Status-Patch Endpoint |
| 1-Klick Einchecken | ✅ OK | `angekommen` Status |
| 1-Klick No-Show | ✅ OK | `nicht_erschienen` Status |
| Walk-ins | ✅ OK | ServiceTerminal Dialog |
| Warteliste | ❌ FEHLT | Collection existiert nicht |

### 2.8 Widget / Website

| Feature | Status | Details |
|---------|--------|---------|
| Widget responsive | ✅ OK | BookingWidget.jsx |
| Public API | ✅ OK | `/api/public/*` Endpoints |
| CORS | ✅ OK | `allow_origins: *` |
| WordPress Embedding | ✅ MÖGLICH | CORS erlaubt alle Origins |

---

## 3️⃣ PROBLEME / RISIKEN

### 🔴 BLOCKER (Reservierung nicht zuverlässig)

| # | Problem | Ursache | Vorschlag |
|---|---------|---------|-----------|
| 1 | **Keine Öffnungszeiten** | `opening_hours_periods` leer | Mindestens 1 Default-Periode anlegen |
| 2 | **Keine Sperrtage** | `closures` leer | 24.12, 31.12 etc. konfigurieren |
| 3 | **Kapazität nicht Tisch-basiert** | Hardcoded 100/150 statt Tisch-Summe | Logik in `check_capacity_with_duration` anpassen |
| 4 | **Events ohne Cutoff-Logik** | `last_alacarte_minutes_before` fehlt | Feld zu Events hinzufügen + Slot-Filter |

### 🟡 WICHTIG (Betrieb möglich, aber problematisch)

| # | Problem | Ursache | Vorschlag |
|---|---------|---------|-----------|
| 5 | **Keine Slot-Konfiguration** | `time_slot_configs` leer | Durchgänge Sa/So definieren |
| 6 | **Warteliste fehlt** | Collection + UI nicht vorhanden | Additiv implementieren |
| 7 | **Newsletter Opt-in unklar** | Feld nicht im Guest-Schema | Prüfen/ergänzen |
| 8 | **WhatsApp nur Stub** | Kein Provider konfiguriert | Twilio/MessageBird integrieren |

### 🟢 NICE-TO-HAVE

| # | Problem | Ursache | Vorschlag |
|---|---------|---------|-----------|
| 9 | Event-Kapazität pro Event | Feld `capacity` fehlt | Schema erweitern |
| 10 | Automatische Tischzuweisung | Nur manuell möglich | Auto-Assign implementieren |
| 11 | Besuchs-Badge im UI | Logik vorhanden, UI unklar | Frontend prüfen |

---

## 4️⃣ ZUSAMMENFASSUNG FÜR TOM

### ✅ Was ist bereits korrekt konfiguriert?

1. **Grundwerte** (110 min Aufenthalt, 10 min Buffer, 90 Tage Vorlauf) ✅
2. **No-Show Thresholds** (Greylist: 2, Blacklist: 4) ✅
3. **Reminder Rules** (24h Email, 3h WhatsApp) ✅
4. **SMTP** (IONOS, funktioniert) ✅
5. **Tische & Kombinationen** (49 Tische, 17 Kombis) ✅
6. **Events mit Terminen** (21 Events mit dates-Array) ✅
7. **API-Endpoints** (alle CRUD-Operationen vorhanden) ✅
8. **UI-Seiten** (Admin + Widget + Terminal) ✅

### ❌ Was fehlt / ist leer / ist inkonsistent?

| Kategorie | Problem | Dringlichkeit |
|-----------|---------|---------------|
| **Öffnungszeiten** | 0 Perioden (Sommer/Winter) | 🔴 BLOCKER |
| **Sperrtage** | 0 Closures (Feiertage) | 🔴 BLOCKER |
| **Kapazität** | Nicht Tisch-basiert (150 hardcoded) | 🔴 BLOCKER |
| **Event-Cutoff** | Feld fehlt in Events | 🔴 BLOCKER |
| **Zeitslots** | Keine Durchgänge/Sperrzeiten definiert | 🟡 WICHTIG |
| **Warteliste** | Komplett nicht implementiert | 🟡 WICHTIG |
| **guests Collection** | Existiert nicht (erst bei 1. Buchung) | 🟢 OK (on-demand) |

### 📋 EMPFOHLENE NÄCHSTE 3 SCHRITTE

#### 1️⃣ Öffnungszeiten-Periode anlegen (SOFORT)
```
POST /api/opening-hours/periods
{
  "name": "Standard 2026",
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "rules_by_weekday": {
    "monday": {"is_closed": true},
    "tuesday": {"is_closed": true},
    "wednesday": {"blocks": [{"start": "17:00", "end": "22:00"}]},
    "thursday": {"blocks": [{"start": "17:00", "end": "22:00"}]},
    "friday": {"blocks": [{"start": "17:00", "end": "22:00"}]},
    "saturday": {"blocks": [{"start": "11:30", "end": "22:00"}]},
    "sunday": {"blocks": [{"start": "11:30", "end": "20:00"}]}
  },
  "active": true,
  "priority": 10
}
```

#### 2️⃣ Sperrtage anlegen (SOFORT)
```
POST /api/closures
- 24.12. (recurring, full_day)
- 31.12. (recurring, time_range: ab 15:00)
- 01.01. (recurring, full_day)
```

#### 3️⃣ Kapazitätslogik auf Tisch-basiert umstellen (KURZFRISTIG)
- `check_capacity_with_duration()` ändern
- Statt `max_capacity = 150` → Summe freier Tische berechnen
- Tischverfügbarkeit in Availability-Response einbauen

---

**STOPP – Keine Implementierung gestartet. Report abgeschlossen.**
