# Modul 30: MITARBEITER & DIENSTPLAN V1
## GastroCore / Carlsburg Cockpit

**Version:** 1.0.0  
**Datum:** 2025-12-29  
**Status:** In Implementierung

---

## 1. Schema-Diff (Alt vs. Neu)

### 1.1 shift_templates (Erweitert)

| Feld | Alt | Neu | Typ | Pflicht | Beschreibung |
|------|-----|-----|-----|---------|--------------|
| id | ✅ | ✅ | string (UUID) | ✅ | Primary Key |
| code | ❌ | ✅ | string | ✅ | **NEU** Unique identifier (z.B. "SVC_EARLY") |
| name | ✅ | ✅ | string | ✅ | Anzeigename |
| department | ✅ | → role | - | - | **Umbenannt** |
| role | ❌ | ✅ | string | ✅ | **NEU** service, kitchen, bar, cleaning, etc. |
| station | ❌ | ✅ | string? | ❌ | **NEU** Optionale Station (z.B. "Terrasse") |
| start_time | ✅ | → start_time_local | string | ✅ | HH:MM |
| start_time_local | ❌ | ✅ | string | ✅ | **NEU** HH:MM Format |
| end_time_local | ❌ | ✅ | string | ✅ | **NEU** HH:MM Format (ersetzt end_time_type Logik) |
| end_time_type | ✅ | ✅ | enum | ❌ | Bleibt für dynamische Endzeiten |
| end_time_fixed | ✅ | ✅ | string? | ❌ | HH:MM wenn fixed |
| close_plus_minutes | ✅ | ✅ | int? | ❌ | Minuten nach Schließung |
| event_mode | ✅ | ✅ | boolean | ✅ | false=Normal, true=Kulturabend |
| active | ✅ | ✅ | boolean | ✅ | Template aktiv? |
| archived | ✅ | ✅ | boolean | ✅ | Soft-delete |

**Index:** `unique { code }`

---

### 1.2 shifts (SOURCE OF TRUTH - Umgebaut)

| Feld | Alt | Neu | Typ | Pflicht | Beschreibung |
|------|-----|-----|-----|---------|--------------|
| id | ✅ | ✅ | string (UUID) | ✅ | Primary Key |
| schedule_id | ✅ | ✅ | string | ❌ | Referenz zu Wochenplan (optional) |
| **staff_member_id** | ✅ | ❌ | string | - | **LEGACY - wird migriert** |
| **assigned_staff_ids** | ❌ | ✅ | string[] | ✅ | **NEU** Array von Staff-IDs |
| shift_date | ✅ | → date_local | - | - | **Umbenannt** |
| **date_local** | ❌ | ✅ | string | ✅ | **NEU** YYYY-MM-DD (Europe/Berlin) |
| start_time | ✅ | ❌ | string | - | **LEGACY** |
| end_time | ✅ | ❌ | string | - | **LEGACY** |
| **start_at_utc** | ❌ | ✅ | datetime | ✅ | **NEU** ISO 8601 UTC |
| **end_at_utc** | ❌ | ✅ | datetime | ✅ | **NEU** ISO 8601 UTC |
| role | ✅ | ✅ | string | ✅ | Rolle für diese Schicht |
| **station** | ❌ | ✅ | string? | ❌ | **NEU** Optionale Station |
| **event_id** | ❌ | ✅ | string? | ❌ | **NEU** Verknüpftes Event |
| **required_staff_count** | ❌ | ✅ | int | ✅ | **NEU** Soll-Besetzung (default: 1) |
| **status** | ❌ | ✅ | enum | ✅ | **NEU** DRAFT, PUBLISHED, CANCELLED |
| notes | ✅ | → notes_staff | - | - | **Umbenannt** |
| **notes_staff** | ❌ | ✅ | string? | ❌ | **NEU** Notizen für Mitarbeiter |
| **notes_internal** | ❌ | ✅ | string? | ❌ | **NEU** Interne Notizen (Admin) |
| work_area_id | ✅ | ✅ | string? | ❌ | Arbeitsbereich |
| hours | ✅ | ✅ | float | ❌ | Berechnete Stunden |
| template_id | ❌ | ✅ | string? | ❌ | **NEU** Referenz zur Vorlage |
| archived | ✅ | ✅ | boolean | ✅ | Soft-delete |

**Indizes:**
- `{ date_local: 1, start_at_utc: 1 }`
- `{ assigned_staff_ids: 1, start_at_utc: 1 }`
- `{ event_id: 1, start_at_utc: 1 }`

---

### 1.3 time_sessions (NEU)

| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|--------------|
| id | string (UUID) | ✅ | Primary Key |
| staff_member_id | string | ✅ | Mitarbeiter-ID |
| day_key | string | ✅ | YYYY-MM-DD (Europe/Berlin) |
| state | enum | ✅ | WORKING, BREAK, CLOSED |
| shift_id | string? | ❌ | Verknüpfte Schicht (wenn Auto-Link) |
| link_method | enum | ✅ | AUTO, MANUAL, NONE |
| clock_in_at | datetime | ✅ | Stempel-Ein (UTC) |
| clock_out_at | datetime? | ❌ | Stempel-Aus (UTC) |
| total_work_seconds | int | ❌ | Arbeitszeit in Sekunden |
| total_break_seconds | int | ❌ | Pausenzeit in Sekunden |
| breaks | array | ✅ | Array von Break-Objekten |
| created_at | datetime | ✅ | Erstellungszeitpunkt |
| updated_at | datetime | ✅ | Letztes Update |

**Break-Objekt:**
```json
{
  "start_at": "2025-12-29T12:00:00Z",
  "end_at": "2025-12-29T12:30:00Z",  // null wenn aktiv
  "duration_seconds": 1800
}
```

**Index:** `unique { staff_member_id: 1, day_key: 1 }`

---

### 1.4 time_events (NEU - Append-only)

| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|--------------|
| id | string (UUID) | ✅ | Primary Key |
| session_id | string | ✅ | Referenz zu time_session |
| staff_member_id | string | ✅ | Mitarbeiter-ID |
| event_type | enum | ✅ | CLOCK_IN, BREAK_START, BREAK_END, CLOCK_OUT |
| timestamp_utc | datetime | ✅ | Zeitpunkt (UTC) |
| timestamp_local | string | ✅ | Zeitpunkt (Europe/Berlin) |
| source | enum | ✅ | APP, TERMINAL, ADMIN_CORRECTION |
| idempotency_key | string | ✅ | Für Duplikat-Erkennung |
| metadata | object? | ❌ | Zusätzliche Daten |

**Indizes:**
- `{ session_id: 1, timestamp_utc: 1 }`
- `unique { idempotency_key: 1 }`

---

## 2. API-Endpunkte

### 2.1 Shift Management (Admin/Manager)

| Method | Endpoint | Beschreibung | Auth |
|--------|----------|--------------|------|
| GET | `/api/staff/shifts/v2` | Liste aller Schichten (V2) | Manager+ |
| GET | `/api/staff/shifts/v2/{shift_id}` | Einzelne Schicht | Manager+ |
| POST | `/api/staff/shifts/v2` | Neue Schicht erstellen | Manager+ |
| PATCH | `/api/staff/shifts/v2/{shift_id}` | Schicht bearbeiten | Manager+ |
| DELETE | `/api/staff/shifts/v2/{shift_id}` | Schicht archivieren | Manager+ |
| POST | `/api/staff/shifts/v2/{shift_id}/publish` | Status → PUBLISHED | Manager+ |
| POST | `/api/staff/shifts/v2/{shift_id}/cancel` | Status → CANCELLED | Manager+ |
| POST | `/api/staff/shifts/v2/{shift_id}/assign` | Mitarbeiter zuweisen | Manager+ |
| POST | `/api/staff/shifts/v2/{shift_id}/unassign` | Mitarbeiter entfernen | Manager+ |
| POST | `/api/staff/shifts/v2/generate-from-templates` | Aus Vorlagen generieren | Manager+ |

### 2.2 Shift Swap (Admin/Manager)

| Method | Endpoint | Beschreibung | Auth |
|--------|----------|--------------|------|
| POST | `/api/staff/shifts/v2/{shift_id}/swap` | Schichttausch (atomar) | Manager+ |

### 2.3 Timeclock (Alle Auth-User)

| Method | Endpoint | Beschreibung | Auth |
|--------|----------|--------------|------|
| GET | `/api/timeclock/status` | Aktueller Status | User |
| POST | `/api/timeclock/clock-in` | Einstempeln | User |
| POST | `/api/timeclock/clock-out` | Ausstempeln | User |
| POST | `/api/timeclock/break-start` | Pause beginnen | User |
| POST | `/api/timeclock/break-end` | Pause beenden | User |
| GET | `/api/timeclock/today` | Heute's Session | User |
| GET | `/api/timeclock/history` | Historische Sessions | User |

### 2.4 Admin Timeclock Management

| Method | Endpoint | Beschreibung | Auth |
|--------|----------|--------------|------|
| GET | `/api/staff/time-sessions` | Alle Sessions (gefiltert) | Manager+ |
| GET | `/api/staff/time-sessions/{session_id}` | Einzelne Session | Manager+ |
| PATCH | `/api/staff/time-sessions/{session_id}` | Korrektur | Admin |
| GET | `/api/staff/time-events` | Event-Log | Admin |

### 2.5 Mitarbeiter-App (PWA) Reads

| Method | Endpoint | Beschreibung | Auth |
|--------|----------|--------------|------|
| GET | `/api/staff/my-shifts` | Eigene Schichten (nur PUBLISHED) | User |
| GET | `/api/timeclock/status` | Stempel-Status | User |
| GET | `/api/timeclock/today` | Tagesübersicht | User |

---

## 3. Smoke-Test-Liste

### 3.1 Shift-Management Tests

| # | Test | Erwartung | Priorität |
|---|------|-----------|-----------|
| S1 | POST /shifts/v2 mit assigned_staff_ids=[] | 201, Schicht erstellt | Critical |
| S2 | POST /shifts/v2 mit assigned_staff_ids=[id1,id2] | 201, Beide zugewiesen | Critical |
| S3 | POST /shifts/v2/{id}/publish | Status → PUBLISHED | Critical |
| S4 | POST /shifts/v2/{id}/cancel | Status → CANCELLED | Critical |
| S5 | POST /shifts/v2/{id}/assign mit staff_id | assigned_staff_ids aktualisiert | High |
| S6 | POST /shifts/v2/{id}/unassign mit staff_id | staff_id entfernt aus Array | High |
| S7 | GET /staff/my-shifts (nur PUBLISHED) | Nur veröffentlichte Schichten | Critical |

### 3.2 Timeclock Tests

| # | Test | Erwartung | Priorität |
|---|------|-----------|-----------|
| T1 | POST /timeclock/clock-in (erste Session) | 201, State=WORKING | Critical |
| T2 | POST /timeclock/clock-in (zweite am selben Tag) | **409 CONFLICT** | Critical |
| T3 | POST /timeclock/break-start | State=BREAK | Critical |
| T4 | POST /timeclock/clock-out während BREAK | **409 BLOCKED** | Critical |
| T5 | POST /timeclock/break-end | State=WORKING | Critical |
| T6 | POST /timeclock/clock-out | State=CLOSED | Critical |
| T7 | GET /timeclock/today (nach clock-out) | Arbeitszeit, Pausenzeit summiert | High |

### 3.3 Auto-Link Tests

| # | Test | Erwartung | Priorität |
|---|------|-----------|-----------|
| A1 | clock-in mit eindeutiger Schicht | shift_id gesetzt, link_method=AUTO | High |
| A2 | clock-in ohne Schicht | shift_id=null, link_method=NONE | High |
| A3 | clock-in mit >1 möglichen Schichten | shift_id=null, link_method=NONE | High |

### 3.4 Swap Tests

| # | Test | Erwartung | Priorität |
|---|------|-----------|-----------|
| W1 | Swap auf DRAFT Schicht | **400 ERROR** (nur PUBLISHED) | High |
| W2 | Swap auf PUBLISHED Schicht | assigned_staff_ids aktualisiert | High |
| W3 | Swap mit nicht-zugewiesenem MA | **400 ERROR** | High |
| W4 | Swap atomar (Transaktion) | Audit-Log geschrieben | High |

---

## 4. Migration Script

```python
# Wird in staff_module.py implementiert als Admin-Endpoint
POST /api/staff/shifts/migrate-to-v2

# Logik:
1. Für jeden shift mit staff_member_id und ohne assigned_staff_ids:
   - assigned_staff_ids = [staff_member_id]
   - status = DRAFT (oder PUBLISHED wenn schedule published)
   - date_local = shift_date
   - start_at_utc = parse(shift_date + " " + start_time, "Europe/Berlin")
   - end_at_utc = parse(shift_date + " " + end_time, "Europe/Berlin")

2. Report zurückgeben:
   - migrated_count
   - skipped_count
   - errors[]
```

---

## 5. State Machine: Timeclock

```
        ┌─────────────┐
        │    OFF      │ (Keine Session / Session CLOSED)
        └──────┬──────┘
               │ clock_in
               ▼
        ┌─────────────┐
   ┌────│   WORKING   │────┐
   │    └──────┬──────┘    │
   │           │           │
   │ break_end │ break_start
   │           │           │
   │    ┌──────▼──────┐    │
   └────│    BREAK    │────┘
        └──────┬──────┘
               │ ❌ clock_out BLOCKED!
               │
               │ (Erst break_end, dann clock_out)
               ▼
        ┌─────────────┐
        │   CLOSED    │
        └─────────────┘
```

**Invarianten:**
- Max 1 Session pro Mitarbeiter & Tag
- Max 1 aktive Pause gleichzeitig
- Clock-out bei BREAK → 409 CONFLICT
- Alle Events sind append-only mit Idempotency-Key

---

## 6. Abhängigkeiten

- MongoDB Transaktionen (Replica Set) für Swap
- `pytz` für Europe/Berlin Timezone
- Bestehende Auth-Module (get_current_user, require_manager, etc.)
- Audit-Log System (create_audit_log)
