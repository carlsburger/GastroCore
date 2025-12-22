# GastroCore Seed-Dateien

Dieser Ordner enthält die Stammdaten für das Carlsburg Cockpit.

## Dateien

- `tables.xlsx` - Tisch-Stammdaten (49 Tische)
- `table_combinations.xlsx` - Tischkombinationen (17 Kombinationen)

## Import

### Automatisch (empfohlen)
```bash
# Per API (Admin-Login erforderlich)
POST /api/admin/seed/from-repo
```

### Manuell (UI)
1. Login als Admin
2. Navigation: Reservierung → Import
3. Button "Seed aus Repo laden" klicken

## Struktur

### tables.xlsx
| Spalte | Beschreibung |
|--------|--------------|
| table_number | Tischnummer (z.B. "1", "38.1") |
| area | Bereich: "restaurant" oder "terrasse" |
| subarea | Unterbereich: "saal", "wintergarten" oder leer |
| seats | Standard-Sitzplätze |
| max_seats | Maximale Sitzplätze |
| combinable | true/false - kombinierbar |
| notes | Notizen |

### table_combinations.xlsx
| Spalte | Beschreibung |
|--------|--------------|
| combo_id | Kombinations-ID (z.B. "S1", "W1", "T1") |
| subarea | Bereich: "saal", "wintergarten", "terrasse" |
| tables | Tische (z.B. "9+10") |
| target_capacity | Ziel-Kapazität |
| notes | Notizen |

## Regeln

- Kombinationen nur innerhalb gleicher Subarea erlaubt
- Tisch 3 (Exot, oval) nie kombinierbar
- Saal 2er rund (Tisch 2, 11, 12) nie kombinierbar
- Wintergarten (Tisch 19, 20, 21) nie kombinierbar
- Kombi S4 (13+114+1) blockiert Tisch 2 automatisch
