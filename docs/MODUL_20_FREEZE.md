# MODUL 20 RESERVIERUNG – FREEZE DOKUMENTATION

## Status: ✅ FROZEN

| Feld | Wert |
|------|------|
| **Status** | FROZEN ✅ |
| **Freeze-Datum** | 29.12.2025 |
| **Version** | 1.0 FINAL |
| **Abgenommen von** | Emergent AI |

---

## Enthaltene Bestandteile

### 1. Reservation Guards (B1–B5)

| Guard | Funktion | Status |
|-------|----------|--------|
| **B1** | Standarddauer 115 Minuten erzwingen | ✅ AKTIV |
| **B2** | Event sperrt normale Reservierungen | ✅ AKTIV |
| **B3** | Slots bei Event deaktivieren | ✅ AKTIV |
| **B4** | Wartelisten-Trigger nur bei STORNIERT | ✅ AKTIV |
| **B5** | 24h Bestätigungsfenster für Warteliste | ✅ AKTIV |

### 2. Capacity Guards (C1–C2)

| Guard | Funktion | Status |
|-------|----------|--------|
| **C1** | Gäste pro Stunde aggregieren | ✅ AKTIV |
| **C2** | Event-Flag prüfen (is_event_active_at) | ✅ AKTIV |

### 3. Wartelisten-Trigger

- ✅ Public Cancel (`/api/public/reservations/{id}/cancel`)
- ✅ Admin Storno (`PATCH /api/reservations/{id}/status?new_status=storniert`)
- ✅ Trigger NUR bei Status → `storniert`
- ✅ Kein Trigger bei `no_show` oder `abgeschlossen`

### 4. API Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/reservations` | POST | Reservierung erstellen |
| `/api/reservations/{id}` | GET/PATCH/DELETE | CRUD |
| `/api/reservations/{id}/status` | PATCH | Status ändern |
| `/api/reservations/hourly` | GET | Gäste pro Stunde |
| `/api/public/availability` | GET | Slot-Verfügbarkeit |
| `/api/public/book` | POST | Öffentliche Buchung |
| `/api/public/restaurant-info` | GET | Branding + Öffnungszeiten |
| `/api/waitlist` | GET/POST | Warteliste |

### 5. Booking Widget (/book)

- ✅ Logo wie Login-Seite (Carlsburg Historisches Panoramarestaurant)
- ✅ Öffnungszeiten-Zeile (periodenbasiert, serverseitig generiert)
- ✅ 3-Schritt-Wizard (Datum/Zeit → Kontaktdaten → Bestätigung)
- ✅ Wartelisten-Funktion bei Kapazitätsüberlastung

### 6. Public Restaurant Info Response

```json
{
  "name": "Carlsburg Historisches Panoramarestaurant",
  "phone": null,
  "email": null,
  "address": null,
  "opening_hours_weekly_text": "Mo/Di Ruhetag · Mi/Do 12:00-18:00 · Fr/Sa 12:00-20:00 · So 12:00-18:00",
  "opening_hours_season_label": "Winter"
}
```

---

## TABU-LISTE (Änderungsverbote)

Die folgenden Änderungen sind **VERBOTEN** ohne neuen Entscheidungsblock:

| Nr. | Verbot | Begründung |
|-----|--------|------------|
| T1 | Keine zweite Reservierungs-API | Einheitliche Datenquelle |
| T2 | Keine alternative Statuslogik | Guard-Integrität |
| T3 | Keine parallele Availability-/Slot-Berechnung | Keine Duplikation |
| T4 | Keine parallele Kapazitätsquelle | reservation_capacity.py ist Source of Truth |
| T5 | Keine Änderung der Guard-Triggerbedingungen | Fachliche Abnahme erfolgt |
| T6 | Keine Frontend-Berechnung von Öffnungszeiten | Server ist Source of Truth |

---

## Änderungsprotokoll

| Datum | Version | Änderung | Autor |
|-------|---------|----------|-------|
| 29.12.2025 | 1.0 | Initial Freeze | Emergent AI |

---

## Änderungen ab jetzt

Änderungen an Modul 20 sind **NUR** zulässig mit:

1. **Neuem Entscheidungsblock** (dokumentiert in `/app/docs/`)
2. **Expliziter Freigabe** durch Product Owner
3. **Dokumentation** der Abweichung vom Freeze

Bei Bugs:
- Hotfixes erlaubt, wenn Guard-Logik nicht verändert wird
- Dokumentation des Fixes erforderlich

---

## Verifizierung

Zuletzt verifiziert am: **29.12.2025**

| Check | Status |
|-------|--------|
| Guards B1-B5 funktional | ✅ |
| Admin-Wartelisten-Trigger | ✅ |
| Booking Widget Logo | ✅ |
| Öffnungszeiten-Anzeige | ✅ |
| API Response korrekt | ✅ |

---

**MODUL 20 IST OFFIZIELL EINGEFROREN.**

*Freeze dokumentiert am 29.12.2025*
*Verantwortlich: Emergent AI*
