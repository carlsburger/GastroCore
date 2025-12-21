# Backup-Verzeichnis – Carlsburg Cockpit

## Namensschema

| Datei | Format |
|-------|--------|
| Patch | `patch_<commit>_<YYYYMMDD_HHMM>.patch` |
| ZIP | `release_<commit>_<YYYYMMDD_HHMM>.zip` |
| Report | `backup_report_<commit>_<YYYYMMDD_HHMM>.md` |

## Ausschlussliste (nicht im ZIP enthalten)

```
node_modules/
.venv/
venv/
__pycache__/
dist/
build/
.git/
.env
logs/
uploads/
*.log
*.pyc
.DS_Store
```

## Ablauf „Vor Tab schließen"

1. Terminal öffnen
2. Ins Projektverzeichnis wechseln: `cd /app`
3. Backup-Skript ausführen: `bash scripts/make_backup.sh`
4. **ZIP-Datei lokal herunterladen** (aus `/app/backups/`)
5. Tab kann geschlossen werden

## Wiederherstellung

1. ZIP entpacken
2. `yarn install` im frontend-Ordner
3. `pip install -r backend/requirements.txt`
4. `.env`-Dateien neu anlegen (nicht im Backup enthalten!)
5. Services starten

## Wichtig

- **Secrets (.env) sind NICHT im Backup!**
- Nach Wiederherstellung müssen Umgebungsvariablen neu gesetzt werden
- Backup regelmäßig lokal sichern
