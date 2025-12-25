# API Status Code & Error Code Guidelines
## GastroCore / Carlsburg Cockpit

**Version:** 1.0.0  
**Datum:** 2025-12-25  
**Status:** Live

---

## 1. HTTP Status Codes

| Situation | Status | Beispiel |
|-----------|--------|----------|
| Erfolgreiche Anfrage | `200 OK` | GET /api/staff/members |
| Fachlich leer, aber gültig | `200 OK` | GET /api/staff/my-shifts (keine Schichten) |
| Ressource erstellt | `201 Created` | POST /api/staff/members |
| Nicht authentifiziert | `401 Unauthorized` | Kein/ungültiger Token |
| Kein Zugriff | `403 Forbidden` | Mitarbeiter versucht Admin-Aktion |
| Objekt existiert nicht | `404 Not Found` | GET /api/staff/members/{id} - ID nicht gefunden |
| Validierungsfehler | `422 Unprocessable Entity` | Ungültige Email-Format |
| Konflikt | `409 Conflict` | Doppelte Schichtzuweisung |
| Technischer Fehler | `500 Internal Server Error` | DB nicht erreichbar |

### ⚠️ Wichtige Regel

Ein fachlicher Zustand wie:
- "Kein Mitarbeiterprofil verknüpft"
- "Keine Schichten vorhanden"
- "Keine Reservierungen für heute"

ist **KEIN Fehler**, sondern ein **gültiger Zustand** → `200 OK`

---

## 2. API Response Format

### Standard Response (v2)

```json
{
  "success": true,
  "data": {...} | [...] | null,
  "message": "Optional: Hinweistext",
  "error": null | "ERROR_CODE"
}
```

### Beispiele

**Erfolg mit Daten:**
```json
{
  "success": true,
  "data": [
    {"id": "abc-123", "name": "Max Mustermann"}
  ],
  "message": null,
  "error": null
}
```

**Fachlich leer (kein Staff-Link):**
```json
{
  "success": true,
  "data": [],
  "message": "Kein Mitarbeiterprofil verknüpft. Bitte wende dich an die Schichtleitung.",
  "error": "STAFF_NOT_LINKED"
}
```

**Fehler:**
```json
{
  "success": false,
  "data": null,
  "message": "Die E-Mail-Adresse ist bereits vergeben.",
  "error": "VALIDATION_ERROR"
}
```

---

## 3. Error Codes (Enum)

| Code | Bedeutung | HTTP Status |
|------|-----------|-------------|
| `STAFF_NOT_LINKED` | User hat kein Mitarbeiterprofil | 200 |
| `NO_SHIFTS_ASSIGNED` | Keine Schichten vorhanden | 200 |
| `INVALID_ROLE` | Ungültige Benutzerrolle | 403 |
| `NOT_AUTHENTICATED` | Nicht angemeldet | 401 |
| `FORBIDDEN` | Keine Berechtigung | 403 |
| `NOT_FOUND` | Ressource nicht gefunden | 404 |
| `VALIDATION_ERROR` | Ungültige Eingabedaten | 422 |
| `CONFLICT` | Konflikt mit bestehenden Daten | 409 |
| `INTERNAL_ERROR` | Technischer Fehler | 500 |

---

## 4. Frontend Handling

```javascript
import { ApiErrorCode, extractData, hasErrorCode } from '@/lib/api-types';

// API Call
const response = await api.get('/staff/my-shifts');

// Daten extrahieren (kompatibel mit altem und neuem Format)
const shifts = extractData(response);

// Error Code prüfen
if (hasErrorCode(response, ApiErrorCode.STAFF_NOT_LINKED)) {
  showInfoMessage("Kein Mitarbeiterprofil verknüpft");
}
```

---

## 5. Begründung (Partnerfähigkeit)

Diese API-Semantik ist Voraussetzung für:
- ✅ Mobile Apps (iOS/Android)
- ✅ Externe Clients / Partner-Integrationen
- ✅ SDK-Generierung (OpenAPI)
- ✅ Sauberes Error-Tracking
- ✅ Konsistente UX

---

## 6. Migration von altem Format

Das neue Format ist **additiv** und **rückwärtskompatibel**:

1. Alte Endpoints liefern weiterhin Arrays/Objects direkt
2. Neue/migrierte Endpoints nutzen das Standard-Format
3. Frontend prüft automatisch mit `isStandardResponse()`

---

**Autor:** GastroCore Team  
**Review:** 2025-12-25
