# 🔍 GASTROCORE SYSTEM-AUDIT & STATUSBERICHT

**Datum:** 2025-07-24  
**Auditor:** System-Prüfung (Read-Only)  
**Datenbank:** MongoDB Atlas (cluster0.qguoo0u.mongodb.net)  
**System:** Carlsburg Cockpit / GastroCore

---

## 1️⃣ ZUSAMMENFASSUNG (EXECUTIVE SUMMARY)

### ⚠️ KRITISCHER STATUS

| Komponente | Status | Beschreibung |
|------------|--------|--------------|
| **Backend** | ❌ **OFFLINE** | Import-Fehler in `payment_module.py` |
| **Frontend** | ✅ Läuft | Port 3000 erreichbar |
| **Datenbank** | ⚠️ **NICHT ERREICHBAR** | SSL-Handshake-Fehler zu Atlas |
| **Quelldaten** | ✅ Vorhanden | Excel/JSON-Backups vollständig |

### Sofortmaßnahmen erforderlich:
1. **Backend-Import-Fehler beheben** (emergentintegrations Paket)
2. **MongoDB Atlas IP-Whitelist prüfen**
3. **SSL-Zertifikate aktualisieren**

---

## 2️⃣ DATENBANK-INVENTUR

### A) Verbindungsstatus

```
❌ MongoDB Atlas nicht erreichbar
   Cluster: cluster0.qguoo0u.mongodb.net
   Fehler: SSL handshake failed (TLSV1_ALERT_INTERNAL_ERROR)
   
   Mögliche Ursachen:
   - IP nicht in Atlas-Whitelist
   - Cluster pausiert/inaktiv
   - SSL-Zertifikatsprobleme
```

### B) Lokale Datenquellen (Backup-Analyse)

Da keine direkte DB-Verbindung möglich ist, wurde die Analyse auf Basis der **Backup-Dateien** durchgeführt:

| Datenquelle | Datei | Einträge | Status |
|-------------|-------|----------|--------|
| **Tische** | `Carlsburg_Tables.xlsx` | 46 | ✅ Vollständig |
| **Kombinationen** | `Carlsburg_Combinations.xlsx` | 17 | ✅ Vollständig |
| **Mitarbeiter** | `Mitarbeiterliste_2025.xlsx` | 13 | ✅ Vollständig |
| **Veranstaltungen** | `Carlsburg_EventsActions_*.json` | 11 | ✅ Vollständig |
| **Aktionen** | `Carlsburg_EventsActions_*.json` | 13 | ⚠️ Unvollständig (keine Zeiträume) |

### C) Letzter bekannter DB-Stand (aus IST-STAND-REPORT)

| Collection | Count | Bemerkung |
|------------|-------|-----------|
| `users` | 1 | Admin vorhanden |
| `staff_members` | 12 | Aus Excel importiert |
| `work_areas` | 3 | Service/Küche/Bar |
| `tables` | 46 | Vollständig |
| `events` | 11 | Von Website gescraped |
| `actions` | 13 | Von Website gescraped |
| `settings` | 6 | Grundkonfiguration |
| `opening_hours_periods` | 0 | ⚠️ Nicht konfiguriert |
| `closures` | 0 | ⚠️ Nicht konfiguriert |
| `table_combinations` | 0 | ⚠️ Nicht importiert |
| `reservation_config` | 0 | ⚠️ Nicht konfiguriert |
| `schedules` | 0 | On-demand |
| `shifts` | 0 | On-demand |
| `reservations` | 0 | On-demand |

---

## 3️⃣ FACHLICHE VALIDIERUNG DER INHALTE

### 🔹 Tische & Tischlogik

#### Tische nach Bereich:

| Bereich | Subbereich | Anzahl | Plätze (Std) | Plätze (Max) |
|---------|------------|--------|--------------|--------------|
| Restaurant | Saal | 13 | 59 | 63 |
| Restaurant | Wintergarten | 11 | 43 | 43 |
| Terrasse | Terrasse | 22 | 84 | 84 |
| **GESAMT** | - | **46** | **186** | **190** |

#### Kombinierbarkeit:
- ✅ Kombinierbar: **39 Tische** (84.8%)
- ❌ Nicht kombinierbar: **7 Tische**

#### Kombinationen (17 definiert):

| Bereich | ID | Tische | Kapazität |
|---------|-----|--------|-----------|
| Saal | S1 | 9+10 | 6 |
| Saal | S2 | 8+9+10 | 8 |
| Saal | S3 | 13+114 | 9 |
| Saal | S4 | 13+114+1 | 11 |
| Wintergarten | W1 | 22+23+24 | 16 |
| Wintergarten | W2 | 23+24 | 9 |
| Wintergarten | W3 | 15+14 | 7 |
| Wintergarten | W4 | 16+18 | 7 |
| Wintergarten | W5 | 14+15+16 | 9 |
| Wintergarten | W6 | 18+16+17+15 | 13 |
| Terrasse | T1 | 35+34+36+33 | 11 |
| Terrasse | T2 | 37+38 | 8 |
| Terrasse | T3 | 39+40 | 8 |
| Terrasse | T4 | 41+42 | 8 |
| Terrasse | T5 | 35+36 | 7 |
| Terrasse | T6 | 39+38.1 | 7 |
| Terrasse | T7 | 41+40.1 | 7 |

**Status:** ✅ Tischdaten korrekt, ⚠️ Kombinationen noch nicht in DB importiert

---

### 🔹 Mitarbeiter

#### Mitarbeiterliste (13 Personen):

| Name | Rufname | Zeit-PIN |
|------|---------|----------|
| Alicja Caban | Alicja | 4468 |
| Nicole Fenske | Nicole | 1906 |
| Jacqueline Gebel | - | 9999 |
| Sascha Graef | Sascha | 806 |
| Simon Jaskolla | Simon | 2512 |
| Justina Listowska | Justina | 3009 |
| Annett Senst | Annett | 2604 |
| Thomas Steinert | Tom | 2112 |
| Inh. Thomas Steinert | - | 1222 |
| Julia Taebling | Julia | 1505 |
| Luisa Wolf | Luisa | 1912 |
| Leonie Wolgast | - | 2804 |
| Fiete Ziegler | Fiete | 2412 |

**Status:** ✅ Vollständig, ⚠️ Rollen/Arbeitsbereiche nicht in Excel-Quelle definiert

---

### 🔹 Veranstaltungen

#### Kategorisierung:

**1. Kulturveranstaltungen (11 Events):**

| Datum | Titel | Preis | Status |
|-------|-------|-------|--------|
| 2026-02-25 | Bob Lehmann | 29€ | ✅ Aktiv |
| 2026-02-26 | Bob Lehmann | 29€ | ✅ Aktiv |
| 2026-02-27 | Die Kaktusblüte | 29€ | ✅ Aktiv |
| 2026-02-28 | UNIKAT – die Zugabe | 39€ | ✅ Aktiv |
| 2026-03-04 | Trudchen und Irmchen | 29€ | ✅ Aktiv |
| 2026-03-05 | Elke Winter Solo | 29€ | ✅ Aktiv |
| 2026-03-06 | Elke Winter Solo | 29€ | ✅ Aktiv |
| 2026-03-07 | Big Helga | 29€ | ✅ Aktiv |
| 2026-03-08 | Big Helga (Frauentag) | 29€ | ✅ Aktiv |
| 2026-03-12 | Schwarze Grütze | 29€ | ✅ Aktiv |
| 2026-05-13 | CLOVER - Irish Folk Party | 29€ | ✅ Aktiv |

**2. Menüaktionen (13 Aktionen):**

| Aktion | Typ | Zeitraum | Status |
|--------|-----|----------|--------|
| Valentinsabend | Spezial | ❌ Nicht definiert | ⚠️ Unvollständig |
| Spareribs Sattessen | Wiederkehrend | ❌ Nicht definiert | ⚠️ Unvollständig |
| Großgarnelen Sattessen | Wiederkehrend | ❌ Nicht definiert | ⚠️ Unvollständig |
| Schnitzel Sattessen | Wiederkehrend | ❌ Nicht definiert | ⚠️ Unvollständig |
| Mediterraner Tapas-Abend | Wiederkehrend | ❌ Nicht definiert | ⚠️ Unvollständig |
| Carlsburger Terrassen BBQ | Saisonal | ❌ Nicht definiert | ⚠️ Unvollständig |
| Ente Sattessen | Saisonal | ❌ Nicht definiert | ⚠️ Unvollständig |
| Martinsgans Essen | Saisonal | ❌ Nicht definiert | ⚠️ Unvollständig |
| Spargelwochen | Saisonal | ❌ Nicht definiert | ⚠️ Unvollständig |
| Matjeswochen | Saisonal | ❌ Nicht definiert | ⚠️ Unvollständig |
| Pfifferlings-Wochen | Saisonal | ❌ Nicht definiert | ⚠️ Unvollständig |
| Kürbiswochen | Saisonal | ❌ Nicht definiert | ⚠️ Unvollständig |
| Wildwochen | Saisonal | ❌ Nicht definiert | ⚠️ Unvollständig |

**Kritischer Befund:**
- ✅ Veranstaltungen: Vollständig mit Datum, Preis, Beschreibung
- ❌ Aktionen: **Fehlende Zeiträume** (valid_from, valid_to = null)
- ❌ Aktionen: **Keine Wochentage** definiert
- ❌ Aktionen: **Keine Buchungsregeln** definiert

---

## 4️⃣ IMPORT- & QUELLENPRÜFUNG

### Datenherkunft:

| Quelle | Typ | Datum | Status |
|--------|-----|-------|--------|
| `Carlsburg_Tables.xlsx` | Excel | Manuell | ✅ |
| `Carlsburg_Combinations.xlsx` | Excel | Manuell | ✅ |
| `Mitarbeiterliste_2025.xlsx` | Excel | Manuell | ✅ |
| `carlsburg.de/veranstaltungen/` | Web-Scraping | 2025-12-22 | ✅ |
| `carlsburg.de/aktionen/` | Web-Scraping | 2025-12-22 | ⚠️ Unvollständig |

### Import-Qualität:

| Prüfpunkt | Status | Ergebnis |
|-----------|--------|----------|
| **Idempotenz** | ⚠️ Unklar | Keine Import-Logs in Backup |
| **Dubletten** | ⚠️ Möglich | Bob Lehmann 2x (2 Tage = korrekt) |
| **Referenz-Integrität** | ❌ Nicht geprüft | DB nicht erreichbar |
| **Schema-Konsistenz** | ✅ OK | Excel-Struktur konsistent |

---

## 5️⃣ SYSTEMSTATUS-REPORT

### ✅ Was funktioniert aktuell

**Datenbank (Quelldaten):**
- ✅ Tisch-Stammdaten vollständig (46 Tische, 17 Kombinationen)
- ✅ Mitarbeiter-Stammdaten vollständig (13 MA)
- ✅ Veranstaltungsdaten importiert (11 Events)
- ✅ Backup-Mechanismus funktioniert (Excel/JSON)

**Module:**
- ✅ Core/Auth-Modul implementiert (3-Rollen-System)
- ✅ Tischplan-Backend implementiert
- ✅ Events-Modul implementiert
- ✅ Staff-Modul implementiert
- ✅ Service-Terminal UI optimiert

**Frontend:**
- ✅ React-App läuft (Port 3000)
- ✅ Service-Terminal mit Touch-Optimierung
- ✅ Dashboard, Tischplan, Mitarbeiterverwaltung

---

### ⚠️ Was funktioniert eingeschränkt

| Problem | Ursache | Auswirkung |
|---------|---------|------------|
| **Aktionen unvollständig** | Zeiträume fehlen | Keine Buchung möglich |
| **Kombinationen nicht in DB** | Import nicht durchgeführt | Auto-Assign fehlt |
| **Dienstplan** | Shift-Dialog öffnet nicht | Keine Schichtplanung |
| **Öffnungszeiten** | Keine Perioden angelegt | Reservierung blockiert |
| **MyShifts** | Zeigt falsche KW | Verwirrung für MA |

---

### ❌ Was funktioniert nicht

| Problem | Technische Ursache | Kritikalität |
|---------|-------------------|--------------|
| **Backend offline** | `ImportError: cannot import name 'StripeCheckout' from 'emergentintegrations.payments.stripe.checkout'` | 🔴 KRITISCH |
| **MongoDB nicht erreichbar** | SSL-Handshake-Fehler, IP-Whitelist | 🔴 KRITISCH |
| **E-Mail-Versand** | SMTP nicht konfiguriert | 🟡 MITTEL |
| **KI-Assistent** | OpenAI API-Key fehlt | 🟡 MITTEL |
| **Zahlungen** | Stripe nicht initialisiert | 🟢 NIEDRIG (deaktiviert) |

---

### 🧩 Offene Konfigurationen

| Konfiguration | Status | Erforderliche Aktion |
|---------------|--------|---------------------|
| **Öffnungszeiten** | ❌ Leer | Mindestens 1 Periode anlegen |
| **Reservierungslogik** | ❌ Leer | Slots + Regeln definieren |
| **SMTP/Mail** | ❌ Nicht konfiguriert | Env-Vars setzen |
| **Loyalty** | ❌ Keine Daten | Optional |
| **Schichtarten** | ❌ Hardcoded | Collection anlegen |
| **Sperrtage** | ❌ Leer | Feiertage eintragen |

---

## 6️⃣ HANDLUNGSEMPFEHLUNGEN (PRIORISIERT)

### 1. 🔴 SOFORT: Backend reparieren
```bash
# Option A: emergentintegrations installieren
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/

# Option B: payment_module.py temporär deaktivieren
# Import in server.py auskommentieren
```

### 2. 🔴 SOFORT: MongoDB-Verbindung prüfen
- IP-Whitelist in Atlas Console prüfen (0.0.0.0/0 für Test)
- Cluster-Status prüfen (aktiv/pausiert)
- SSL-Optionen testen (`tlsInsecure=true`)

### 3. 🟡 KURZFRISTIG: Aktionen vervollständigen
- Zeiträume (valid_from, valid_to) für alle 13 Aktionen definieren
- Wochentage zuweisen
- Buchungsregeln festlegen

### 4. 🟡 KURZFRISTIG: Öffnungszeiten anlegen
- Standard-Periode erstellen (Mo-Sa, 11-22 Uhr)
- Sperrtage: Heiligabend, Silvester, 1. Januar

### 5. 🟢 MITTELFRISTIG: Tischkombinationen importieren
- 17 Kombinationen aus Excel in DB übertragen
- Referenz-Integrität prüfen

---

## 7️⃣ ABSCHLUSS

**Gesamtbewertung:** ⚠️ **EINGESCHRÄNKT BETRIEBSBEREIT**

Das System ist auf Code-Ebene weitgehend implementiert, aber:
- Backend aktuell nicht lauffähig (Import-Fehler)
- Datenbank nicht erreichbar (SSL/IP)
- Kritische Konfigurationen fehlen (Öffnungszeiten, Reservierung)

**Empfehlung:** Fokus auf Infrastruktur-Stabilisierung vor weiterer Feature-Entwicklung.

---

*Report erstellt: 2025-07-24 | Auditor: System-Prüfung (Read-Only)*
*Keine Daten wurden verändert oder gelöscht.*
