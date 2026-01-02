#!/usr/bin/env python3
"""
============================================================
CARLSBURG COCKPIT - PHASE P2: OPENING HOURS SEED BUILDER
Clean Rebuild (Variante C) - Legacy strikt read-only
============================================================

Erzeugt V2-Seeds für Öffnungszeiten deterministisch.
Keine DB-Reads, keine Legacy-Collections.

OUTPUT:
  /app/seeds/v2/opening_periods_master_v2.json
  /app/seeds/v2/opening_overrides_master_v2.json

FACHLOGIK:
  - Sommerzeit: 04-01 bis 10-31, täglich 11:30-20:00
  - Winterzeit: 11-01 bis 03-31, Mo/Di geschlossen, Mi-So variabel
  - Overrides: Silvester/Neujahr, Heiligabend (höhere Priorität)
"""

import os
import sys
import json
from datetime import datetime, timezone
from typing import List, Dict, Any

# ============================================================
# CONFIGURATION
# ============================================================

OUTPUT_DIR = "/app/seeds/v2"
OUTPUT_PERIODS = f"{OUTPUT_DIR}/opening_periods_master_v2.json"
OUTPUT_OVERRIDES = f"{OUTPUT_DIR}/opening_overrides_master_v2.json"

# Wochentage: 0=Montag, 1=Dienstag, ..., 6=Sonntag
MONDAY = 0
TUESDAY = 1
WEDNESDAY = 2
THURSDAY = 3
FRIDAY = 4
SATURDAY = 5
SUNDAY = 6

DAY_NAMES = {
    0: "Montag",
    1: "Dienstag",
    2: "Mittwoch",
    3: "Donnerstag",
    4: "Freitag",
    5: "Samstag",
    6: "Sonntag"
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def now_iso() -> str:
    """ISO 8601 UTC timestamp"""
    return datetime.now(timezone.utc).isoformat()


def make_day_entry(day_of_week: int, is_closed: bool, open_time: str = None, close_time: str = None) -> Dict:
    """Erstellt einen Wochentag-Eintrag für eine Periode."""
    return {
        "day_of_week": day_of_week,
        "is_closed": is_closed,
        "open_time": open_time if not is_closed else None,
        "close_time": close_time if not is_closed else None
    }


# ============================================================
# SEED DATA DEFINITIONS
# ============================================================

def build_periods() -> List[Dict[str, Any]]:
    """
    Erstellt die Öffnungszeiten-Perioden.
    
    SOMMERZEIT (April - Oktober):
    - Täglich: 11:30 - 20:00
    
    WINTERZEIT (November - März):
    - Mo: geschlossen
    - Di: geschlossen
    - Mi: 12:00 - 18:00
    - Do: 12:00 - 18:00
    - Fr: 12:00 - 20:00
    - Sa: 12:00 - 20:00
    - So: 12:00 - 18:00
    """
    
    periods = []
    
    # ============== SOMMERZEIT ==============
    summer_hours = []
    for day in range(7):  # Mo-So
        summer_hours.append(make_day_entry(
            day_of_week=day,
            is_closed=False,
            open_time="11:30",
            close_time="20:00"
        ))
    
    summer_period = {
        "id": "period_summer",
        "name": "Sommerzeit",
        "recurrence": {
            "type": "yearly",
            "from_mm_dd": "04-01",
            "to_mm_dd": "10-31",
            "timezone": "Europe/Berlin"
        },
        "priority": 10,
        "active": True,
        "hours": summer_hours
    }
    periods.append(summer_period)
    
    # ============== WINTERZEIT ==============
    winter_hours = [
        # Montag - geschlossen
        make_day_entry(MONDAY, is_closed=True),
        # Dienstag - geschlossen
        make_day_entry(TUESDAY, is_closed=True),
        # Mittwoch - 12:00-18:00
        make_day_entry(WEDNESDAY, is_closed=False, open_time="12:00", close_time="18:00"),
        # Donnerstag - 12:00-18:00
        make_day_entry(THURSDAY, is_closed=False, open_time="12:00", close_time="18:00"),
        # Freitag - 12:00-20:00
        make_day_entry(FRIDAY, is_closed=False, open_time="12:00", close_time="20:00"),
        # Samstag - 12:00-20:00
        make_day_entry(SATURDAY, is_closed=False, open_time="12:00", close_time="20:00"),
        # Sonntag - 12:00-18:00
        make_day_entry(SUNDAY, is_closed=False, open_time="12:00", close_time="18:00"),
    ]
    
    winter_period = {
        "id": "period_winter",
        "name": "Winterzeit",
        "recurrence": {
            "type": "yearly",
            "from_mm_dd": "11-01",
            "to_mm_dd": "03-31",
            "timezone": "Europe/Berlin"
        },
        "priority": 10,
        "active": True,
        "hours": winter_hours
    }
    periods.append(winter_period)
    
    return periods


def build_overrides() -> List[Dict[str, Any]]:
    """
    Erstellt die Öffnungszeiten-Overrides (Schließtage).
    
    Overrides haben höhere Priorität als Perioden.
    """
    
    overrides = []
    
    # ============== SILVESTER / NEUJAHR 2025/2026 ==============
    overrides.append({
        "id": "override_silvester_2025",
        "name": "Silvester / Neujahr 2025/2026",
        "date_from": "2025-12-31",
        "date_to": "2026-01-02",
        "status": "closed",
        "open_from": None,
        "open_to": None,
        "last_reservation_time": None,
        "priority": 100,
        "active": True
    })
    
    # ============== HEILIGABEND 2026 ==============
    overrides.append({
        "id": "override_heiligabend_2026",
        "name": "Heiligabend 2026",
        "date_from": "2026-12-24",
        "date_to": "2026-12-24",
        "status": "closed",
        "open_from": None,
        "open_to": None,
        "last_reservation_time": None,
        "priority": 100,
        "active": True
    })
    
    return overrides


# ============================================================
# VALIDATION
# ============================================================

def validate_periods(periods: List[Dict]) -> List[str]:
    """Validiert die Perioden-Daten."""
    errors = []
    
    for period in periods:
        pid = period.get("id", "UNKNOWN")
        
        # Check: Exakt 7 Wochentage
        hours = period.get("hours", [])
        if len(hours) != 7:
            errors.append(f"{pid}: Muss exakt 7 Wochentage haben, hat {len(hours)}")
        
        # Check: Alle day_of_week von 0-6 vorhanden
        days_present = {h.get("day_of_week") for h in hours}
        expected_days = {0, 1, 2, 3, 4, 5, 6}
        missing_days = expected_days - days_present
        if missing_days:
            errors.append(f"{pid}: Fehlende Wochentage: {missing_days}")
        
        # Check: Zeiten sind HH:MM Format oder None
        for h in hours:
            day = h.get("day_of_week")
            is_closed = h.get("is_closed", False)
            open_time = h.get("open_time")
            close_time = h.get("close_time")
            
            if is_closed:
                if open_time is not None or close_time is not None:
                    errors.append(f"{pid}: Tag {day} ist geschlossen, aber Zeiten sind gesetzt")
            else:
                if open_time is None or close_time is None:
                    errors.append(f"{pid}: Tag {day} ist offen, aber Zeiten fehlen")
                else:
                    # Format-Check HH:MM
                    for time_val, time_name in [(open_time, "open_time"), (close_time, "close_time")]:
                        if not _is_valid_time(time_val):
                            errors.append(f"{pid}: Tag {day} {time_name} '{time_val}' ist kein gültiges HH:MM Format")
        
        # Check: Recurrence vorhanden
        rec = period.get("recurrence", {})
        if not rec.get("type") or not rec.get("from_mm_dd") or not rec.get("to_mm_dd"):
            errors.append(f"{pid}: Unvollständige recurrence-Definition")
    
    return errors


def validate_overrides(overrides: List[Dict]) -> List[str]:
    """Validiert die Override-Daten."""
    errors = []
    
    for override in overrides:
        oid = override.get("id", "UNKNOWN")
        
        date_from = override.get("date_from")
        date_to = override.get("date_to")
        
        # Check: Datum-Format
        if not _is_valid_date(date_from):
            errors.append(f"{oid}: date_from '{date_from}' ist kein gültiges YYYY-MM-DD Format")
        
        if not _is_valid_date(date_to):
            errors.append(f"{oid}: date_to '{date_to}' ist kein gültiges YYYY-MM-DD Format")
        
        # Check: date_from <= date_to
        if _is_valid_date(date_from) and _is_valid_date(date_to):
            if date_from > date_to:
                errors.append(f"{oid}: date_from ({date_from}) > date_to ({date_to})")
        
        # Check: Status vorhanden
        if not override.get("status"):
            errors.append(f"{oid}: status fehlt")
    
    return errors


def _is_valid_time(time_str: str) -> bool:
    """Prüft HH:MM Format."""
    if not time_str or not isinstance(time_str, str):
        return False
    parts = time_str.split(":")
    if len(parts) != 2:
        return False
    try:
        h, m = int(parts[0]), int(parts[1])
        return 0 <= h <= 23 and 0 <= m <= 59
    except ValueError:
        return False


def _is_valid_date(date_str: str) -> bool:
    """Prüft YYYY-MM-DD Format."""
    if not date_str or not isinstance(date_str, str):
        return False
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


# ============================================================
# OUTPUT
# ============================================================

def write_seed_file(data: List[Dict[str, Any]], output_path: str, description: str):
    """Schreibt Seed-Datei als JSON mit Metadaten."""
    
    seed_doc = {
        "_meta": {
            "version": "2.0.0",
            "description": description,
            "created_at": now_iso(),
            "source": "build_p2_opening_hours.py",
            "target_db": "gastrocore_v2",
            "count": len(data)
        },
        "data": data
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(seed_doc, f, indent=2, ensure_ascii=False)
    
    file_size = os.path.getsize(output_path)
    print(f"✅ Geschrieben: {output_path}")
    print(f"   → {len(data)} Einträge, {file_size} Bytes")


def print_summary(periods: List[Dict], overrides: List[Dict]):
    """Gibt Summary aus."""
    
    print("\n" + "=" * 60)
    print("PHASE P2 SEEDS - SUMMARY")
    print("=" * 60)
    
    # Perioden
    print(f"\n📅 PERIODEN: {len(periods)}")
    for p in periods:
        rec = p.get("recurrence", {})
        from_date = rec.get("from_mm_dd", "?")
        to_date = rec.get("to_mm_dd", "?")
        
        # Zähle offene/geschlossene Tage
        hours = p.get("hours", [])
        open_days = sum(1 for h in hours if not h.get("is_closed", True))
        closed_days = 7 - open_days
        
        print(f"\n   📌 {p['name']} ({p['id']})")
        print(f"      Zeitraum: {from_date} bis {to_date} (jährlich)")
        print(f"      Priorität: {p.get('priority', 0)}, Active: {p.get('active', False)}")
        print(f"      {open_days} Tage offen, {closed_days} Tage geschlossen")
        
        # Details pro Tag
        for h in sorted(hours, key=lambda x: x.get("day_of_week", 0)):
            day_name = DAY_NAMES.get(h.get("day_of_week"), "?")
            if h.get("is_closed"):
                print(f"      - {day_name}: geschlossen")
            else:
                print(f"      - {day_name}: {h.get('open_time')} - {h.get('close_time')}")
    
    # Overrides
    print(f"\n🚫 OVERRIDES (Schließtage): {len(overrides)}")
    for o in overrides:
        date_from = o.get("date_from", "?")
        date_to = o.get("date_to", "?")
        days = 1
        if date_from != date_to:
            try:
                d1 = datetime.strptime(date_from, "%Y-%m-%d")
                d2 = datetime.strptime(date_to, "%Y-%m-%d")
                days = (d2 - d1).days + 1
            except:
                pass
        
        print(f"\n   📌 {o['name']} ({o['id']})")
        print(f"      Zeitraum: {date_from} bis {date_to} ({days} Tag{'e' if days > 1 else ''})")
        print(f"      Status: {o.get('status')}, Priorität: {o.get('priority', 0)}")
    
    print("\n" + "=" * 60)
    print("✅ PHASE P2 SEEDS ERFOLGREICH ERSTELLT")
    print("=" * 60)
    
    print(f"\nDateien:")
    print(f"  - {OUTPUT_PERIODS}")
    print(f"  - {OUTPUT_OVERRIDES}")
    print()


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("CARLSBURG COCKPIT - PHASE P2: OPENING HOURS SEED BUILDER")
    print("Clean Rebuild (Variante C)")
    print("=" * 60)
    
    # 1. Output-Verzeichnis sicherstellen
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 2. Perioden bauen
    print(f"\n🔧 Baue Öffnungszeiten-Perioden...")
    periods = build_periods()
    print(f"   ✅ {len(periods)} Perioden erstellt")
    
    # 3. Overrides bauen
    print(f"\n🔧 Baue Öffnungszeiten-Overrides...")
    overrides = build_overrides()
    print(f"   ✅ {len(overrides)} Overrides erstellt")
    
    # 4. Validierung
    print(f"\n🔍 Validiere Daten...")
    
    period_errors = validate_periods(periods)
    override_errors = validate_overrides(overrides)
    all_errors = period_errors + override_errors
    
    if all_errors:
        print(f"\n❌ VALIDIERUNGSFEHLER ({len(all_errors)}):")
        for err in all_errors:
            print(f"   - {err}")
        print("\n⛔ ABBRUCH: Bitte Fehler korrigieren!")
        sys.exit(1)
    
    print(f"   ✅ Perioden validiert ({len(periods)} × 7 Wochentage)")
    print(f"   ✅ Overrides validiert ({len(overrides)} Einträge)")
    
    # 5. Seeds schreiben
    print(f"\n💾 Schreibe Seed-Dateien...")
    
    write_seed_file(
        periods,
        OUTPUT_PERIODS,
        "Carlsburg Öffnungszeiten-Perioden V2 - Source of Truth für Clean Rebuild"
    )
    
    write_seed_file(
        overrides,
        OUTPUT_OVERRIDES,
        "Carlsburg Öffnungszeiten-Overrides V2 - Source of Truth für Clean Rebuild"
    )
    
    # 6. Summary
    print_summary(periods, overrides)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
