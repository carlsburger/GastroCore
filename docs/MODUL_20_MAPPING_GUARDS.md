# MODUL 20: RESERVIERUNG – MAPPING-VERIFIZIERUNG & BACKEND-GUARDS
## GastroCore / Carlsburg Cockpit
**Stand: 29.12.2025**

---

# 📋 AUFGABENPAKET A: MAPPING-VERIFIZIERUNG

## A1) Modell- & Feldprüfung

### Reservierung (Collection: `reservations`)

| Soll-Feld | Ist-Feld | Datentyp | Default | Status |
|-----------|----------|----------|---------|--------|
| `guest_count` | `party_size` | Integer | - | ✅ Vorhanden |
| `start_at` | `time` | String "HH:MM" | - | ✅ Vorhanden |
| `end_at` | berechnet via `duration_minutes` | - | 115 Min | ✅ Implementiert |
| `status` | `status` | String (Enum) | "neu" | ✅ Vorhanden |
| `reservation_type` | `source` + `event_id` | String | "widget" | ✅ Vorhanden |
| `event_flag` | `event_id` | UUID (nullable) | null | ✅ Vorhanden |

### Zusätzliche Felder (existierend)
| Feld | Datentyp | Beschreibung |
|------|----------|--------------|
| `guest_name` | String | Gastname |
| `guest_phone` | String | Telefon |
| `guest_email` | String (opt) | E-Mail |
| `date` | String "YYYY-MM-DD" | Datum |
| `area_id` | UUID (opt) | Bereich |
| `table_number` | String (opt) | Tisch |
| `notes` | String (opt) | Notizen |
| `occasion` | String (opt) | Anlass |
| `event_pricing` | Object (opt) | Event-Preisinfo |
| `reminder_sent` | Boolean | Erinnerung gesendet |
| `archived` | Boolean | Archiviert |

---

## A2) Status-Workflow Abgleich

### Soll-Workflow (fachlich)
```
NEU → BESTAETIGT → ANGEKOMMEN → ABGESCHLOSSEN
                            └→ NO_SHOW
      └→ STORNIERT
```

### Ist-Workflow (Code: `ReservationStatus`)
```python
class ReservationStatus(str, Enum):
    NEU = "neu"
    BESTAETIGT = "bestaetigt"
    ANGEKOMMEN = "angekommen"
    ABGESCHLOSSEN = "abgeschlossen"
    NO_SHOW = "no_show"
    STORNIERT = "storniert"
```

### Erlaubte Übergänge (Code)
```python
ALLOWED_TRANSITIONS = {
    "neu": ["bestaetigt", "storniert"],
    "bestaetigt": ["angekommen", "storniert"],
    "angekommen": ["abgeschlossen", "no_show"],
    "abgeschlossen": [],  # Terminal
    "no_show": [],        # Terminal
    "storniert": []       # Terminal
}
```

### ✅ ERGEBNIS: WORKFLOW STIMMT ÜBEREIN
Keine neuen Status eingeführt. Mapping ist 1:1.

---

# 📋 AUFGABENPAKET B: IMPLEMENTIERTE BACKEND-GUARDS

## B1) Standarddauer erzwingen ✅

**Datei:** `/app/backend/reservation_guards.py`

```python
STANDARD_RESERVATION_DURATION_MINUTES = 115  # 1:55 für Gast

def enforce_standard_duration(data: dict, is_event: bool = False) -> dict:
    if is_event:
        return data  # Event-Buchungen behalten eigene Dauer
    data["duration_minutes"] = STANDARD_RESERVATION_DURATION_MINUTES
    return data
```

**Integration:**
- `POST /api/reservations` - Guard aktiv
- `POST /public/book` - Guard aktiv
- Keine manuelle Dauer für normale Reservierungen möglich

---

## B2) Event sperrt à la carte ✅

**Datei:** `/app/backend/reservation_guards.py`

```python
async def guard_event_blocks_reservation(
    date_str: str,
    time_str: str,
    event_id: Optional[str] = None,
    duration_minutes: int = 115
) -> None:
    if event_id:
        return  # Event-Buchungen erlaubt
    
    is_blocked, event_info = await check_event_blocks_reservation(...)
    if is_blocked:
        raise ConflictException(event_info["message"])
```

**Integration:**
- `POST /api/reservations` - Guard aktiv
- `POST /public/book` - Guard aktiv

**Fehlermeldung:**
```json
{
  "detail": "Event 'Kulturabend' blockiert normale Reservierungen von 18:00 bis 23:00"
}
```

---

## B3) Events sind nicht slotbasiert ✅

**Datei:** `/app/backend/reservation_guards.py`

```python
async def get_event_blocked_slots(date_str: str) -> List[str]:
    # Gibt alle Slots zurück, die durch Events blockiert sind
    # z.B. ["18:00", "18:30", "19:00", ...]
```

**Integration:**
- `GET /public/availability` - Event-Slots werden als `disabled` markiert

**Response-Änderung:**
```json
{
  "slots": [
    {"time": "17:30", "available": true},
    {"time": "18:00", "available": false, "disabled": true, "reason": "Event zu dieser Zeit"},
    {"time": "18:30", "available": false, "disabled": true, "reason": "Event zu dieser Zeit"}
  ]
}
```

---

## B4) Wartelisten-Trigger absichern ✅

**Datei:** `/app/backend/reservation_guards.py`

```python
async def should_trigger_waitlist(old_status: str, new_status: str, reservation: dict) -> bool:
    # NUR bei Statuswechsel → STORNIERT triggern
    if new_status != "storniert":
        return False
    # Nur wenn vorher aktiv (neu, bestaetigt)
    if old_status not in ["neu", "bestaetigt"]:
        return False
    return True
```

**Integration:**
- `POST /public/reservations/{id}/cancel` - Trigger aktiv
- Bei NO_SHOW → KEIN Trigger
- Bei ABGESCHLOSSEN → KEIN Trigger

---

## B5) Wartelisten-Bestätigungsfenster ✅

**Datei:** `/app/backend/reservation_guards.py`

```python
WAITLIST_OFFER_VALIDITY_HOURS = 24

async def process_waitlist_on_cancellation(reservation: dict) -> Optional[dict]:
    # Setze Ablaufzeit für Angebot
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    
    await db.waitlist.update_one(
        {"id": waitlist_entry["id"]},
        {"$set": {
            "status": "informiert",
            "offer_expires_at": expires_at.isoformat(),
            ...
        }}
    )
```

**Wartelisten-Eintrag nach Trigger:**
```json
{
  "id": "...",
  "status": "informiert",
  "offer_expires_at": "2025-12-31T14:00:00+00:00",
  "offered_reservation_id": "...",
  "offered_time": "19:00"
}
```

---

# 📋 AUFGABENPAKET C: VORBEREITUNG MODUL 30

## C1) Gäste pro Stunde ✅

**Neuer Endpunkt:** `GET /api/reservations/hourly`

```python
@api_router.get("/reservations/hourly", tags=["Reservations"])
async def get_reservations_hourly(
    date: str = Query(..., description="Datum YYYY-MM-DD"),
    user: dict = Depends(require_manager)
):
    hourly_data = await get_hourly_overview(date)
    return {
        "date": date,
        "hours": hourly_data,
        "total_guests": sum(h["guests"] for h in hourly_data),
        "total_reservations": sum(h["reservations"] for h in hourly_data)
    }
```

**Response:**
```json
{
  "date": "2025-12-31",
  "hours": [
    {"hour": "11", "hour_display": "11:00", "guests": 45, "reservations": 12},
    {"hour": "12", "hour_display": "12:00", "guests": 78, "reservations": 20},
    ...
  ],
  "total_guests": 234,
  "total_reservations": 65
}
```

**Verwendung für Modul 30:**
- Schichtbelegung automatisch berechnen
- Dashboard-Integration
- Keine automatische Schichtbelegung implementiert (nur Daten bereitgestellt)

---

## C2) Event-Flag ✅

**Funktion:** `is_event_active_at(date_str, time_str)`

```python
async def is_event_active_at(date_str: str, time_str: str) -> Tuple[bool, Optional[dict]]:
    is_blocked, event_info = await check_event_blocks_reservation(date_str, time_str, 0)
    return is_blocked, event_info
```

**Verwendung:**
```python
event_active, event_info = await is_event_active_at("2025-12-31", "19:00")
# event_active = True/False
# event_info = {"event_id": "...", "event_title": "Silvesterparty", ...}
```

---

# ✅ NICHT VERÄNDERTE BEREICHE

| Bereich | Begründung |
|---------|------------|
| Reservierungs-API Struktur | Keine neue API - Guards auf bestehende integriert |
| Datenmodell | Keine neuen Felder - nur Enforcement |
| Status-Logik | Keine neuen Status - nur Trigger-Logik |
| Slot-System | Keine neue Slot-Logik - nur Filtering |
| Kapazitätsberechnung | `reservation_capacity.py` unverändert |
| Event-Modul | Liest nur Events - verändert nichts |

---

# ⚠️ TECHNISCHE RISIKEN & HINWEISE

## Risiken
1. **Performance bei vielen Events**: Event-Check bei jeder Buchung → Caching erwägen für V2
2. **Wartelisten-Ablauf**: Scheduler für `check_expired_waitlist_offers()` empfohlen
3. **Event-Konfiguration**: Feld `blocks_normal_reservations` muss bei Events gepflegt werden

## Empfehlungen
1. **Scheduler** für Wartelisten-Ablauf alle 5 Minuten
2. **Monitoring** für Event-Blocking-Konflikte
3. **Admin-UI** für Event-Block-Einstellung verbessern

---

# 📌 ZUSAMMENFASSUNG

## Implementiert
- ✅ B1: Standarddauer 115 Min erzwungen
- ✅ B2: Event sperrt normale Reservierungen
- ✅ B3: Slots bei Event als disabled
- ✅ B4: Wartelisten-Trigger nur bei Stornierung
- ✅ B5: 24h Bestätigungsfenster
- ✅ C1: Gäste pro Stunde Aggregation
- ✅ C2: Event-Flag Abfrage

## Erfolgskriterium erfüllt
> Nach Umsetzung ist Modul 20 fachlich und technisch widerspruchsfrei.
> Event- und Normalbetrieb sind eindeutig getrennt.
> Wartelisten-Logik ist deterministisch.
> Modul 30 kann ohne Parallelentwicklung andocken.

**Status: ✅ ALLE GUARDS IMPLEMENTIERT**

---

## Booking Widget (/book) - UI Elemente

### Header (Logo)
- Booking Widget nutzt exakt dasselbe Logo wie Login-Seite
- Asset: `CARLSBURG_LOGO_URL` (Carlsburg Historisches Panoramarestaurant)
- Responsive: Desktop h-20, Mobile h-16
- Fallback: Text "Carlsburg Historisches Panoramarestaurant"

### Öffnungszeiten-Anzeige
Das Widget zeigt eine kompakte, periodenbasierte Wochenübersicht:

**Endpoint:** `GET /api/public/restaurant-info`

**Response-Felder:**
```json
{
  "name": "Carlsburg Historisches Panoramarestaurant",
  "opening_hours_weekly_text": "Mo/Di Ruhetag · Mi/Do 12:00-18:00 · Fr/Sa 12:00-20:00 · So 12:00-18:00",
  "opening_hours_season_label": "Winter"
}
```

**Darstellung im Widget:**
`Öffnungszeiten (Winter): Mo/Di Ruhetag · Mi/Do 12:00-18:00 · Fr/Sa 12:00-20:00 · So 12:00-18:00`

**Generierung:**
- Serverseitig aus aktiver Öffnungszeiten-Periode (Winter/Sommer)
- Gruppierung von Wochentagen mit identischen Zeiten
- Ruhetage explizit als "Ruhetag" markiert
- Keine Frontend-Berechnung

---

*Dokumentiert am 29.12.2025*
*Implementiert von: Emergent AI*
