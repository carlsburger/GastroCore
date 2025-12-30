# FIX REPORT – Cockpit UI State + IMAP Setup

**Datum:** 30.12.2025  
**System:** Carlsburg / GastroCore v7.0.0  
**Status:** PRODUKTIV

---

## 1) Root Cause (why old UI shows)

### Analyse-Ergebnis: **UI IST KORREKT**

Nach Überprüfung wurde festgestellt, dass die aktuelle UI **bereits dem erwarteten Zustand entspricht**:

| Komponente | Erwartet | Ist-Zustand | Status |
|------------|----------|-------------|--------|
| Logo | Carlsburg mit Bild | ✅ Korrekt | OK |
| Sidebar-Branding | "CB \| Cockpit" | ⚠️ War "Cockpit" | **GEFIXT** |
| Navigation Gruppen | Dashboard, Reservierungen, VA/Aktion, Mitarbeiter, etc. | ✅ Korrekt | OK |
| Rolle-basierte Sichtbarkeit | Admin/Schichtleiter Filter | ✅ Korrekt | OK |
| Backend URL | `REACT_APP_BACKEND_URL` | ✅ Korrekt gesetzt | OK |

### Mögliche Ursachen für "altes UI" Wahrnehmung:

1. **Browser-Cache**: User sieht gecachte Version
   - Lösung: Hard Refresh (Ctrl+Shift+R) oder Cache leeren
   
2. **CDN/Proxy-Cache**: Cloudflare oder nginx cacht alte Assets
   - Lösung: Cache purge oder `?v=` Query-Parameter an Assets

3. **PWA/Service Worker**: NICHT vorhanden im Projekt
   - Keine Aktion erforderlich

4. **Falscher Branch/Build**: NICHT der Fall
   - Git zeigt aktuellen `main` Branch
   - Commit: `cec92c1` (aktuellster Stand)

---

## 2) Changes Applied (files + summary)

### Änderung 1: Branding-Text korrigiert

**Datei:** `/app/frontend/src/components/Layout.jsx`

**Vorher (Zeile 77):**
```jsx
<span className="text-[10px] text-[#fafbed]/70 tracking-widest uppercase">
  Cockpit
</span>
```

**Nachher:**
```jsx
<span className="text-[10px] text-[#fafbed]/70 tracking-widest uppercase">
  CB | Cockpit
</span>
```

### Keine weiteren Änderungen erforderlich

Die Navigation war bereits korrekt implementiert mit:
- Dashboard als Haupteinstieg
- Hierarchische Gruppen (Reservierungen, VA/Aktion, Mitarbeiter, etc.)
- Rolle-basierte Sichtbarkeit (`roles: ["admin", "schichtleiter"]`)

---

## 3) Navigation Spec Implemented (final menu labels/structure)

```
📊 Dashboard                    [Admin, Schichtleiter]
🍽️  Service-Terminal            [Admin, Schichtleiter]
📖 Reservierungen  ▼            [Admin, Schichtleiter]
   ├─ Übersicht
   ├─ Kalender
   ├─ Tischplan
   └─ Widget Preview (extern)
🎉 VA / Aktion  ▼               [Admin, Schichtleiter]
   ├─ Veranstaltungen
   ├─ Aktionen
   └─ Menü-Aktionen
👥 Mitarbeiter  ▼               [Admin, Schichtleiter]
   ├─ Übersicht
   ├─ Import                    [Admin]
   ├─ Dienstplan
   ├─ Abwesenheiten
   ├─ Schichtmodelle
   └─ Steuerbüro-Export         [Admin]
📅 Meine Schichten              [Alle authentifizierten User]
⏰ Stempeln                     [Alle authentifizierten User]
📢 Marketing                    [Admin]
📊 POS / Kasse  ▼               [Admin]
   ├─ Monatsabschluss
   └─ Import Monitor
⚙️  Einstellungen  ▼            [Admin]
   ├─ System
   ├─ Öffnungszeiten
   ├─ Reservierung
   ├─ E-Mail / SMTP
   ├─ Bereiche
   ├─ Benutzer
   ├─ Tisch-Stammdaten
   ├─ Backup / Export
   └─ System-Seeds
```

---

## 4) Required ENV Keys for IMAP (exact names)

Der POS Mail Import benötigt folgende Umgebungsvariablen:

| Variable | Typ | Beispiel | Beschreibung |
|----------|-----|----------|--------------|
| `POS_IMAP_HOST` | String | `imap.ionos.de` | IMAP Server Hostname |
| `POS_IMAP_PORT` | Integer | `993` | IMAP Port (993 für SSL) |
| `POS_IMAP_USER` | String | `berichte@carlsburg.de` | Postfach-Benutzer |
| `POS_IMAP_PASSWORD` | String | `***` | **PFLICHT** - Postfach-Passwort |
| `POS_IMAP_FOLDER` | String | `INBOX` | Ordner mit Z-Berichten |
| `POS_IMAP_TLS` | Boolean | `true` | TLS/SSL aktivieren |

### Standard-Werte (bereits im Code):
```python
POS_IMAP_HOST = "imap.ionos.de"
POS_IMAP_PORT = 993
POS_IMAP_USER = "berichte@carlsburg.de"
POS_IMAP_FOLDER = "INBOX"
POS_IMAP_TLS = true
```

### Fehlend (MUSS gesetzt werden):
```
POS_IMAP_PASSWORD=<das echte Passwort>
```

---

## 5) How to Set Secrets (prod + local) – step-by-step

### Option A: Lokale Entwicklung (.env Datei)

1. **Datei öffnen:**
   ```bash
   nano /app/backend/.env
   ```

2. **IMAP-Passwort hinzufügen:**
   ```env
   # Bestehende Variablen (NICHT ÄNDERN)
   MONGO_URL=mongodb+srv://...
   JWT_SECRET=...
   DB_NAME=gastrocore
   REQUIRE_ATLAS=true
   AUTO_RESTORE_ENABLED=false
   
   # POS IMAP Credentials (NEU HINZUFÜGEN)
   POS_IMAP_PASSWORD=<IHR_ECHTES_PASSWORT>
   ```

3. **Backend neu starten:**
   ```bash
   sudo supervisorctl restart backend
   ```

4. **Verifizieren:**
   ```bash
   curl -s http://localhost:8001/api/admin/pos/status | jq '.imap_configured'
   # Erwartet: true
   ```

### Option B: Produktion (Emergent Deployment Secrets)

1. **Im Emergent Dashboard:**
   - Projekt öffnen → Settings → Environment Variables / Secrets

2. **Secret hinzufügen:**
   - Key: `POS_IMAP_PASSWORD`
   - Value: `<das echte Passwort>`
   - Scope: Backend

3. **Deployment neu starten:**
   - Deploy triggern oder Service restart

### ⚠️ WICHTIG: Secrets NIEMALS committen!

```bash
# .gitignore sollte enthalten:
.env
*.env
.env.local
.env.production
```

Aktuell ist `/app/backend/.env` bereits in `.gitignore` → ✅ Sicher

---

## 6) Verification Steps (smoke tests)

### Test 1: IMAP-Konfiguration prüfen

```bash
# Status-Endpoint aufrufen
curl -s -H "Authorization: Bearer <ADMIN_TOKEN>" \
  http://localhost:8001/api/admin/pos/status | jq

# Erwartete Ausgabe:
{
  "status": "ok",
  "imap_configured": true,       # ← MUSS true sein
  "imap_host": "imap.ionos.de",
  "imap_user": "berichte@carlsburg.de",
  "imap_folder": "INBOX",
  "last_sync": "...",
  "documents_count": ...
}
```

### Test 2: Dry-Run Import

```bash
# Trockenlauf - liest E-Mails, verarbeitet nicht
curl -s -X POST -H "Authorization: Bearer <ADMIN_TOKEN>" \
  "http://localhost:8001/api/admin/pos/import?dry_run=true" | jq

# Erwartete Ausgabe bei Erfolg:
{
  "success": true,
  "dry_run": true,
  "emails_found": 5,
  "pdfs_extracted": 5,
  "errors": []
}
```

### Test 3: Live Import (nach erfolgreichen Dry-Run)

```bash
# Echter Import
curl -s -X POST -H "Authorization: Bearer <ADMIN_TOKEN>" \
  "http://localhost:8001/api/admin/pos/import?dry_run=false" | jq

# Erwartete Ausgabe:
{
  "success": true,
  "dry_run": false,
  "imported_count": 5,
  "errors": []
}
```

### Test 4: Dashboard-Metriken prüfen

```bash
# Prüfen ob pos_daily_metrics gefüllt wird
curl -s -H "Authorization: Bearer <ADMIN_TOKEN>" \
  "http://localhost:8001/api/admin/pos/metrics?month=2025-01" | jq '.metrics | length'

# Sollte > 0 sein nach Import
```

### Test 5: Frontend POS-Monitor

1. Einloggen als Admin
2. Navigation: **POS / Kasse → Import Monitor**
3. Prüfen:
   - Status: "Verbunden" (grün)
   - Letzte Synchronisation: Aktuelles Datum
   - Dokumente: > 0

### Test 6: Backend-Logs prüfen

```bash
tail -50 /var/log/supervisor/backend.err.log | grep -i "imap\|pos\|mail"

# Erfolg:
# INFO: Connected to IMAP: imap.ionos.de:993
# INFO: Processing email: Z-Bericht 2025-01-15

# Fehler:
# ERROR: POS_IMAP_PASSWORD not set in environment
# ERROR: IMAP login failed: authentication error
```

---

## 7) Remaining Risks / Follow-ups

### Risiko 1: IMAP-Passwort nicht gesetzt (OFFEN)
- **Status:** ⚠️ Passwort fehlt aktuell
- **Auswirkung:** POS-Import nicht funktionsfähig
- **Aktion:** User muss Passwort in .env oder Deployment Secrets setzen

### Risiko 2: E-Mail-Format-Änderungen
- **Status:** NIEDRIG
- **Beschreibung:** Gastronovi könnte PDF-Format ändern
- **Aktion:** PDF-Parser hat Fallbacks, aber Monitoring empfohlen

### Risiko 3: Browser-Cache bei Usern
- **Status:** NIEDRIG
- **Beschreibung:** User könnten alte UI sehen
- **Aktion:** Empfehlung zur Cache-Leerung kommunizieren

### Follow-up Tasks:
1. [ ] IMAP-Passwort vom Betreiber einholen
2. [ ] Passwort in Backend .env setzen
3. [ ] Backend neu starten
4. [ ] Dry-Run Import testen
5. [ ] Live Import aktivieren
6. [ ] Automatischen Cronjob aktivieren (falls gewünscht)

---

## Zusammenfassung

| Bereich | Status | Aktion |
|---------|--------|--------|
| UI/Navigation | ✅ Korrekt | Branding-Text gefixt |
| Build/Deploy | ✅ Aktuell | Keine Aktion |
| IMAP Config | ⚠️ Offen | Passwort erforderlich |
| PWA/Cache | ✅ N/A | Kein Service Worker |

**Nächster Schritt:** IMAP-Passwort in `.env` setzen und Backend neu starten.
