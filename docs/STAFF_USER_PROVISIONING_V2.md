# Staff User Provisioning V2

**Projekt:** Carlsburg Cockpit (GastroCore)  
**Branch:** main  
**Datum:** 2026-01-02  
**Ziel-DB:** gastrocore_v2  

---

## Übersicht

Dieses Dokument beschreibt das User-Provisioning für Staff Members in V2.

### Was wurde erstellt?

Für jeden `staff_member` wurde ein `user`-Account angelegt mit:
- `staff_member_id` Verknüpfung
- Zufälliges Initial-Passwort (nur Hash in DB)
- Role: `mitarbeiter` (Default)
- `must_change_password: true`

### Statistiken

| Metrik | Wert |
|--------|------|
| Staff Members | 18 |
| Users (gesamt) | 19 |
| Users (verlinkt) | 18 |
| Users (provisioniert) | 18 |

---

## Script

**Pfad:** `/app/scripts/provision_staff_users_v2.py`

### Ausführen

```bash
python3 /app/scripts/provision_staff_users_v2.py
```

### Verhalten

1. Lädt alle `staff_members` aus V2 DB
2. Prüft für jeden Staff ob User existiert (via `staff_member_id` oder `email`)
3. Wenn nicht: erstellt neuen User mit:
   - Email: `staff.email` oder `staff_<personnel_number>@local.invalid`
   - Name: `staff.display_name` oder `first_name last_name`
   - Role: `mitarbeiter`
   - Password: 16 Zeichen random, nur Hash gespeichert
   - `staff_member_id`: Verknüpfung zum Staff
   - `external_source`: `staff_provisioning_v2`
   - `must_change_password`: `true`
4. Schreibt Credentials nach `/app/tmp/initial_passwords.csv`

### Idempotenz

Das Script ist idempotent:
- Existierende User werden übersprungen
- Keine Duplikate
- Mehrfach ausführbar ohne Seiteneffekte

---

## Initial Passwords

**Pfad:** `/app/tmp/initial_passwords.csv`

⚠️ **SECURITY:**
- Diese Datei enthält Klartext-Passwörter
- NICHT in Git committen
- Nur für initiale Verteilung an Mitarbeiter
- Nach Verteilung löschen

### Format

```csv
user_id,email,name,staff_member_id,personnel_number,initial_password
```

### Verteilung

1. CSV-Datei exportieren (z.B. auf sicheren USB-Stick)
2. Passwörter persönlich oder via sicherem Kanal verteilen
3. Mitarbeiter müssen beim ersten Login Passwort ändern
4. CSV-Datei löschen: `rm /app/tmp/initial_passwords.csv`

---

## Rollback

Falls Rollback nötig:

```bash
# Provisionierte User löschen
python3 << 'EOF'
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv('/app/backend/.env')

async def rollback():
    client = AsyncIOMotorClient(os.environ.get("MONGO_URL"))
    db = client[os.environ.get("DB_NAME", "gastrocore_v2")]
    
    result = await db.users.delete_many({
        "external_source": "staff_provisioning_v2"
    })
    
    print(f"Gelöscht: {result.deleted_count} User")
    client.close()

asyncio.run(rollback())
EOF
```

---

## Smoke Tests

### Durchgeführte Tests

| Test | Ergebnis |
|------|----------|
| Login via `/api/auth/login` | ✅ Erfolgreich |
| `GET /api/timeclock/status` | ✅ Staff-Link funktioniert |
| `GET /api/staff/my-shifts` | ✅ Erreichbar |

### Test-Kommandos

```bash
# Login testen (ersetze EMAIL und PASSWORD)
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"EMAIL","password":"PASSWORD"}'

# Mit Token API aufrufen
curl http://localhost:8001/api/timeclock/status \
  -H "Authorization: Bearer TOKEN"
```

---

## Nächste Schritte

1. **Rollen anpassen:** Admin/Schichtleiter manuell hochstufen
2. **Passwörter verteilen:** CSV an Mitarbeiter (sicher!)
3. **CSV löschen:** Nach Verteilung `rm /app/tmp/initial_passwords.csv`
4. **Optional:** Welcome-Flow mit Passwort-Reset-Link (nicht in dieser Session)

---

## Technische Details

### User Schema

```json
{
  "id": "uuid",
  "email": "string",
  "name": "string",
  "role": "mitarbeiter",
  "password_hash": "bcrypt-hash",
  "is_active": true,
  "must_change_password": true,
  "staff_member_id": "uuid (Verknüpfung)",
  "external_source": "staff_provisioning_v2",
  "created_at": "ISO-timestamp",
  "updated_at": "ISO-timestamp",
  "archived": false
}
```

### Verknüpfung User → Staff

Die Verknüpfung erfolgt via `user.staff_member_id = staff_member.id`.

Der Timeclock und andere APIs finden den Staff Member via:
1. Direkter Link: `user.staff_member_id`
2. Fallback: Email-Matching

### PIN-Login

PIN-Login wurde **nicht** implementiert, da kein Endpoint existiert.
Die PIN bleibt in `staff_member.time_pin` für späteren Ausbau gespeichert.

---

**Status:** ✅ Provisioning erfolgreich  
**Keine Änderungen an Auth-Flow**  
**Keine neuen Endpoints**
