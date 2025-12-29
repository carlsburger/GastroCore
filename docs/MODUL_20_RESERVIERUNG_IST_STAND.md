# MODUL 20: RESERVIERUNG – IST-STAND ANALYSE
## GastroCore / Carlsburg Cockpit
**Stand: 29.12.2025**

---

# 📋 KURZÜBERBLICK (Executive Summary)

## System-Architektur
- **Backend**: FastAPI mit MongoDB (Atlas)
- **Frontend**: React SPA mit Tailwind CSS
- **Status**: Produktionsreif, vollständige CRUD-Funktionalität

## Hauptkomponenten
| Komponente | Route | Zustand | Bewertung |
|------------|-------|---------|-----------|
| Reservierungs-Kalender | `/reservation-calendar` | 🟢 Stabil | Wochen-/Tagesansicht |
| Service-Terminal | `/service-terminal` | 🟢 Stabil | Tagesgeschäft-UI |
| Öffentliches Buchungswidget | `/book` | 🟢 Stabil | Kunden-Self-Service |
| Tischplan | `/table-plan` | 🟢 Stabil | Visuelle Tischbelegung |
| Warteliste | `/waitlist` | 🟢 Stabil | Warteschlangen-Mgmt |
| Reservierungs-Konfig | `/reservation-config` | 🟢 Stabil | Admin-Einstellungen |

---

# 📊 DETAILLIERTE FUNKTIONSLISTE

## 1. BACKEND API-ENDPUNKTE

### Reservierungen (Core)
| Endpunkt | Methode | Funktion | Auth | Status |
|----------|---------|----------|------|--------|
| `/api/reservations` | GET | Liste aller Reservierungen | Manager | 🟢 |
| `/api/reservations` | POST | Neue Reservierung erstellen | Manager | 🟢 |
| `/api/reservations/summary` | GET | 7-Tage Dashboard-Übersicht | Manager | 🟢 |
| `/api/reservations/slots` | GET | Slot-Kapazitäten für Datum | User | 🟢 |
| `/api/reservations/{id}` | GET | Einzelne Reservierung | User | 🟢 |
| `/api/reservations/{id}` | PUT | Reservierung bearbeiten | Manager | 🟢 |
| `/api/reservations/{id}/status` | PATCH | Status ändern | Terminal | 🟢 |
| `/api/reservations/{id}/assign` | PATCH | Tisch zuweisen | Terminal | 🟢 |
| `/api/reservations/{id}` | DELETE | Archivieren | Manager | 🟢 |

### Walk-ins
| Endpunkt | Methode | Funktion | Auth | Status |
|----------|---------|----------|------|--------|
| `/api/walk-ins` | POST | Walk-in eintragen | Terminal | 🟢 |

### Warteliste
| Endpunkt | Methode | Funktion | Auth | Status |
|----------|---------|----------|------|--------|
| `/api/waitlist` | GET | Warteliste abrufen | Terminal | 🟢 |
| `/api/waitlist` | POST | Eintrag hinzufügen | Terminal | 🟢 |
| `/api/waitlist/{id}` | PATCH | Eintrag aktualisieren | Terminal | 🟢 |
| `/api/waitlist/{id}/convert` | POST | In Reservierung umwandeln | Terminal | 🟢 |
| `/api/waitlist/{id}` | DELETE | Archivieren | Manager | 🟢 |

### Öffentlich (Public Routes)
| Endpunkt | Methode | Funktion | Auth | Status |
|----------|---------|----------|------|--------|
| `/public/booking` | POST | Online-Buchung | - | 🟢 |
| `/public/reservations/{id}/cancel` | POST | Gast-Stornierung | Token | 🟢 |
| `/public/slots` | GET | Verfügbare Slots | - | 🟢 |

### Zusätzliche Features
| Endpunkt | Methode | Funktion | Auth | Status |
|----------|---------|----------|------|--------|
| `/api/reservations/send-reminders` | POST | Erinnerungen senden | Admin | 🟢 |
| `/api/reservations/{id}/whatsapp-reminder` | POST | WhatsApp-Link | Manager | 🟢 |

---

## 2. DATENMODELL

### Reservierung (Collection: `reservations`)
```json
{
  "id": "UUID",
  "guest_name": "String",
  "guest_phone": "String",
  "guest_email": "String (optional)",
  "party_size": "Integer",
  "date": "YYYY-MM-DD",
  "time": "HH:MM",
  "duration_minutes": "Integer (default: 110)",
  "area_id": "UUID (optional)",
  "table_number": "String (optional)",
  "status": "neu|bestaetigt|angekommen|abgeschlossen|no_show|storniert",
  "source": "widget|intern|walk-in|waitlist|phone",
  "notes": "String (optional)",
  "occasion": "String (optional)",
  "event_id": "UUID (optional, für Event-Buchungen)",
  "variant_code": "String (optional, für Event-Varianten)",
  "event_pricing": {
    "total_price": "Float",
    "price_per_person": "Float",
    "payment_mode": "none|deposit|full",
    "payment_status": "pending|paid|failed",
    "amount_due": "Float"
  },
  "reminder_sent": "Boolean",
  "archived": "Boolean",
  "created_at": "ISO DateTime",
  "updated_at": "ISO DateTime"
}
```

### Warteliste (Collection: `waitlist`)
```json
{
  "id": "UUID",
  "guest_name": "String",
  "guest_phone": "String",
  "guest_email": "String (optional)",
  "party_size": "Integer",
  "date": "YYYY-MM-DD",
  "preferred_time": "String (optional)",
  "priority": "Integer (1-5)",
  "status": "offen|informiert|eingeloest|erledigt",
  "notes": "String (optional)",
  "archived": "Boolean"
}
```

---

## 3. STATUS-WORKFLOW

### Reservierung-Status (ReservationStatus)
```
                ┌─────────────────────┐
                │        NEU          │
                └──────────┬──────────┘
                           │
              ┌────────────▼────────────┐
              │      BESTAETIGT         │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │      ANGEKOMMEN         │
              └────────────┬────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
    ▼                      ▼                      ▼
┌──────────┐        ┌──────────┐          ┌──────────┐
│ABGESCHL. │        │ NO_SHOW  │          │STORNIERT │
└──────────┘        └──────────┘          └──────────┘
   (Terminal)          (Terminal)           (kann von NEU 
                                            oder BESTAETIGT)
```

### Wartelisten-Status (WaitlistStatus)
```
OFFEN → INFORMIERT → EINGELOEST / ERLEDIGT
```

---

## 4. FRONTEND-SCREENS

### 4.1 Reservierungs-Kalender (`/reservation-calendar`)
**Funktion**: Übersicht über Reservierungen in Wochen-/Tagesansicht

**Features**:
- Wochenansicht mit 7-Tage Übersicht
- Tagesansicht mit detaillierter Slot-Übersicht
- Öffnungszeiten-Integration
- Kapazitäts-Anzeige pro Slot
- Navigation (Vor/Zurück/Heute)
- Klick auf Tag → wechselt zu Tagesansicht

**Interaktiv**: READ-ONLY (Navigation + View-Wechsel)
**Modus**: Übersicht, keine Bearbeitung

**Bewertung**: 🟢 Stabil – nicht neu bauen

---

### 4.2 Service-Terminal (`/service-terminal`)
**Funktion**: Tagesgeschäft-Management für Service-Personal

**Features**:
- Reservierungsliste mit Echtzeit-Polling (20s)
- Status-Änderung per Klick/Dropdown
- Walk-in Schnellerfassung
- Tisch-Zuweisung
- Filter: Datum, Bereich, Zeitslot, Status
- Wochen-Übersicht (optional)
- Gast-Flag Anzeige (Blacklist/Greylist)
- Payment-Status bei Event-Buchungen
- WhatsApp-Reminder Link

**Interaktiv**: VOLLSTÄNDIG INTERAKTIV
- Status ändern
- Tisch zuweisen
- Walk-in erstellen
- Reservierung bearbeiten (Sheet)

**Bewertung**: 🟢 Stabil – nicht neu bauen

---

### 4.3 Öffentliches Buchungswidget (`/book`)
**Funktion**: Kunden-Self-Service Buchung

**Features**:
- 3-Schritt Wizard (Datum/Zeit → Daten → Bestätigung)
- Slot-Verfügbarkeitsprüfung
- Mehrsprachig (DE/EN)
- Anlass-Auswahl
- Wartelisten-Option bei Ausgebuchtsein
- Bestätigungs-E-Mail

**Interaktiv**: VOLLSTÄNDIG INTERAKTIV (Public)
**URL-Parameter**: `?date=YYYY-MM-DD&time=HH:MM&party_size=N&lang=de|en`

**Bewertung**: 🟢 Stabil – nicht neu bauen

---

### 4.4 Tischplan (`/table-plan`)
**Funktion**: Visuelle Tischbelegungsübersicht

**Features**:
- Bereiche mit Tischen
- Belegungsstatus-Anzeige
- Kapazitäts-Übersicht
- Tisch-Zuweisung zu Reservierung
- Druckansicht (`/table-plan/print`)

**Interaktiv**: INTERAKTIV (Zuweisung)

**Bewertung**: 🟢 Stabil – nicht neu bauen

---

### 4.5 Warteliste (`/waitlist`)
**Funktion**: Wartelisten-Management

**Features**:
- Einträge auflisten
- Neuen Eintrag erstellen
- Status ändern
- In Reservierung umwandeln
- Prioritäts-Sortierung

**Interaktiv**: VOLLSTÄNDIG INTERAKTIV

**Bewertung**: 🟢 Stabil – nicht neu bauen

---

### 4.6 Reservierungs-Konfig (`/reservation-config`)
**Funktion**: Admin-Einstellungen für Reservierungen

**Features**:
- Standard-Dauer (default: 110 Min)
- Verlängerungs-Optionen
- Zeitslot-Konfiguration pro Wochentag
- Sperrzeiten
- Öffnungsperioden

**Interaktiv**: VOLLSTÄNDIG INTERAKTIV (Admin only)

**Bewertung**: 🟢 Stabil – nicht neu bauen

---

### 4.7 Stornierung (`/cancel/:reservationId`)
**Funktion**: Gast kann Reservierung stornieren

**Features**:
- Token-basierte Authentifizierung
- Stornierungsbestätigung
- E-Mail bei Stornierung

**Interaktiv**: PUBLIC
**URL-Parameter**: Token im Query-String

**Bewertung**: 🟢 Stabil – nicht neu bauen

---

### 4.8 Bestätigung (`/confirm/:reservationId`)
**Funktion**: Bestätigungsseite nach Buchung

**Features**:
- Reservierungsdetails anzeigen
- Storno-Link
- QR-Code (optional)

**Interaktiv**: READ-ONLY (Public)

**Bewertung**: 🟢 Stabil – nicht neu bauen

---

## 5. RESERVIERUNGSTYPEN

### Aktuelle Typen im System
| Typ | Field | Unterscheidung | UI-Darstellung |
|-----|-------|----------------|----------------|
| Normal | `source=widget/intern/phone` | Standard | Keine besondere Markierung |
| Walk-in | `source=walk-in` | Laufkundschaft | Badge "Walk-in" |
| Warteliste | `source=waitlist` | Konvertiert | Badge "Warteliste" |
| Event | `event_id` gesetzt | Event-Buchung | Event-Name + Pricing |
| Mit Anzahlung | `payment_mode=deposit/full` | Zahlungspflichtig | Payment-Badge |

### Event-Integration (bereits vorhanden)
- Events haben eigene Pricing-Konfiguration
- Reservierungen können mit Events verknüpft werden
- Payment-Flows sind implementiert (Stripe)
- Varianten-Auswahl bei Multi-Price Events

**Bewertung**: 🟢 Stabil – nur Erweiterung sinnvoll

---

## 6. BUSINESS-LOGIK (Backend)

### Kapazitätsprüfung
- `check_capacity()` - Prüft verfügbare Plätze
- `calculate_slot_capacity()` - Berechnet Kapazität pro Slot
- Berücksichtigt: Bereiche, Tische, Öffnungszeiten, bestehende Reservierungen

### Tisch-Konfliktprüfung
- `check_table_conflict()` - Verhindert Doppelbelegung
- Berücksichtigt: Datum, Zeit, Dauer, bestehende Reservierungen

### Gast-Flag Management
- `update_guest_no_show()` - Aktualisiert No-Show Counter
- Greylist nach 2 No-Shows
- Blacklist nach 3 No-Shows (blockiert Buchung)

### E-Mail Service
- Bestätigungs-E-Mails
- Stornierungsbestätigungen
- Erinnerungen (manuell auslösbar)

### Status-Validierung
- `validate_status_transition()` - Erlaubte Status-Übergänge
- Terminal-Status (abgeschlossen, no_show, storniert) sind final

---

# 🔍 BEWERTUNG & RISIKOANALYSE

## ✅ NICHT NEU BAUEN (🟢)

| Komponente | Begründung |
|------------|------------|
| Reservierungs-CRUD APIs | Vollständig, getestet, produktiv |
| Service-Terminal UI | Feature-complete, täglich im Einsatz |
| Buchungswidget | Funktioniert, mehrsprachig |
| Tischplan | Visuell + funktional komplett |
| Wartelisten-System | Vollständiger Workflow |
| Status-Workflow | Business-Logik etabliert |
| Kapazitätsprüfung | Komplex, funktioniert |
| E-Mail-Service | Integriert, getestet |

## 🟡 ERWEITERUNG SINNVOLL

| Komponente | Erweiterungsvorschlag |
|------------|----------------------|
| Reservierungs-Kalender | Monatsansicht hinzufügen |
| Reservierungstypen | "Aktion" und "Menü" als explizite Typen |
| Dashboard | Erweiterte Statistiken |
| Mobile PWA | Reservierungs-Management für MA |

## 🔴 KANN NEU ENTWICKELT WERDEN

| Komponente | Grund |
|------------|-------|
| Monatskalender-Ansicht | Existiert nicht |
| Reservierungs-Reports | Keine Auswertungen vorhanden |
| SMS-Erinnerungen | Nur WhatsApp-Link vorhanden |
| Online-Payment für Standard-Reservierungen | Nur für Events implementiert |

---

# ⚠️ WARNUNG: PARALLELENTWICKLUNGS-RISIKEN

## NICHT PARALLEL BAUEN:
1. **Keine zweite Reservierungs-API** - `server.py` Endpunkte nutzen
2. **Keine alternative Status-Logik** - `ReservationStatus` Enum ist Source of Truth
3. **Keine separate Kapazitätsprüfung** - `reservation_capacity.py` nutzen
4. **Kein zweites Buchungswidget** - `/book` erweitern, nicht ersetzen
5. **Keine separate Tischverwaltung** - `table_module.py` + `/table-plan` nutzen

## KOORDINATION ERFORDERLICH BEI:
1. Neue Reservierungstypen → `ReservationSource` Enum erweitern
2. Neue Status → `ReservationStatus` Enum erweitern
3. UI-Änderungen → Bestehende Komponenten modifizieren
4. API-Erweiterungen → Neue Endpunkte in `server.py` hinzufügen

---

# 📝 OFFENE LÜCKEN

1. **Monatskalender-Ansicht** - Nicht implementiert
2. **Reservierungs-Statistiken/Reports** - Keine dedizierte Auswertung
3. **Automatische Erinnerungen** - Nur manueller Trigger
4. **SMS-Integration** - Nicht vorhanden (nur WhatsApp-Link)
5. **Recurring Reservations** - Keine Wiederholungs-Funktion
6. **Deposit für Standard-Reservierungen** - Nur für Events
7. **Customer Account** - Gäste haben keine Login-Möglichkeit
8. **Reservierungs-Historie für Gäste** - Nicht vorhanden

---

# 📌 FAZIT

**Das Reservierungsmodul ist vollständig und produktionsreif.**

- Alle Core-Funktionen sind implementiert
- UI ist konsistent und benutzerfreundlich
- Backend ist robust mit Validierung
- Event-Integration funktioniert

**Empfehlung**: Erweiterungen auf Basis des bestehenden Systems durchführen.
Keine Parallelentwicklung starten.

---

*Dokumentiert am 29.12.2025*
*Analyst: Emergent AI*
