#!/usr/bin/env python3
"""
============================================================
CARLSBURG COCKPIT - PHASE P1: TABLES SEED BUILDER
Clean Rebuild (Variante C) - Legacy strikt read-only
============================================================

Erzeugt V2-Seeds aus bestehenden Excel-Dateien.
Keine Migration, kein Merge, kein Legacy-Write.

INPUT:
  /app/seed/tables.xlsx
  /app/seed/table_combinations.xlsx

OUTPUT:
  /app/seeds/v2/tables_master_v2.json
  /app/seeds/v2/table_combinations_master_v2.json

ZIEL-DB (später): gastrocore_v2
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime, timezone
from typing import List, Dict, Any, Set, Tuple

# ============================================================
# CONFIGURATION
# ============================================================

INPUT_TABLES = "/app/seed/tables.xlsx"
INPUT_COMBINATIONS = "/app/seed/table_combinations.xlsx"

OUTPUT_DIR = "/app/seeds/v2"
OUTPUT_TABLES = f"{OUTPUT_DIR}/tables_master_v2.json"
OUTPUT_COMBINATIONS = f"{OUTPUT_DIR}/table_combinations_master_v2.json"

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def table_number_to_id(table_number: str) -> str:
    """
    Konvertiert Tischnummer zu ID.
    Punkt '.' → Unterstrich '_'
    
    Beispiele:
        1 → table_1
        38 → table_38
        38.1 → table_38_1
        114 → table_114
    """
    num_str = str(table_number).strip()
    # Punkt durch Unterstrich ersetzen
    safe_num = num_str.replace(".", "_")
    return f"table_{safe_num}"


def parse_tables_string(tables_str: str) -> List[str]:
    """
    Parst Kombinations-String zu Liste von Tischnummern.
    
    Beispiele:
        "9+10" → ["9", "10"]
        "8+9+10" → ["8", "9", "10"]
        "39+38.1" → ["39", "38.1"]
    """
    if pd.isna(tables_str):
        return []
    
    parts = str(tables_str).split("+")
    return [p.strip() for p in parts if p.strip()]


def now_iso() -> str:
    """ISO 8601 UTC timestamp"""
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# MAIN BUILD FUNCTIONS
# ============================================================

def build_tables_seed(df: pd.DataFrame) -> Tuple[List[Dict[str, Any]], Set[str]]:
    """
    Baut tables_master_v2.json aus DataFrame.
    
    Returns:
        (tables_list, valid_table_ids_set)
    """
    tables = []
    valid_ids = set()
    
    for _, row in df.iterrows():
        table_number = str(row["table_number"]).strip()
        table_id = table_number_to_id(table_number)
        
        # Bereich bestimmen
        area = str(row.get("area", "restaurant")).strip().lower()
        sub_area = str(row.get("subarea", "")).strip().lower() if pd.notna(row.get("subarea")) else ""
        
        # Plätze
        seats_default = int(row.get("seats", 4))
        seats_max = int(row.get("max_seats", seats_default)) if pd.notna(row.get("max_seats")) else seats_default
        
        # Active Flag
        active = bool(row.get("active", True)) if pd.notna(row.get("active")) else True
        
        # Combinable → fixed (umgekehrte Logik: nicht kombinierbar = fixed)
        combinable = bool(row.get("combinable", True)) if pd.notna(row.get("combinable")) else True
        fixed = not combinable
        
        # Notes
        notes = None
        if pd.notna(row.get("notes")):
            notes = str(row["notes"]).strip()
        elif pd.notna(row.get("reason_not_combinable")):
            notes = str(row["reason_not_combinable"]).strip()
        
        table_doc = {
            "id": table_id,
            "table_number": table_number,
            "area": area,
            "sub_area": sub_area,
            "seats_default": seats_default,
            "seats_max": seats_max,
            "active": active,
            "fixed": fixed
        }
        
        if notes:
            table_doc["notes"] = notes
        
        tables.append(table_doc)
        valid_ids.add(table_id)
    
    return tables, valid_ids


def add_missing_tables_from_combinations(
    tables: List[Dict[str, Any]], 
    valid_ids: Set[str],
    df_combinations: pd.DataFrame
) -> Tuple[List[Dict[str, Any]], Set[str], List[str]]:
    """
    Ergänzt fehlende Tische, die in Kombinationen referenziert werden.
    
    LEGACY DATA FIX: Die Excel enthält nicht alle Tische.
    Diese Funktion identifiziert und ergänzt fehlende Tische.
    
    Returns:
        (updated_tables, updated_valid_ids, added_table_numbers)
    """
    # Alle benötigten Tische aus Kombinationen sammeln
    needed_tables = set()
    combo_subareas = {}  # table_number -> subarea mapping
    
    for _, row in df_combinations.iterrows():
        tables_str = str(row.get("tables", ""))
        sub_area = str(row.get("subarea", "")).strip().lower() if pd.notna(row.get("subarea")) else ""
        
        for tn in parse_tables_string(tables_str):
            needed_tables.add(tn)
            combo_subareas[tn] = sub_area
    
    # Fehlende Tische identifizieren
    missing = []
    for tn in needed_tables:
        tid = table_number_to_id(tn)
        if tid not in valid_ids:
            missing.append(tn)
    
    if not missing:
        return tables, valid_ids, []
    
    # Fehlende Tische ergänzen
    added = []
    for tn in sorted(missing, key=lambda x: float(x.replace("_", ".")) if x.replace(".","").replace("_","").isdigit() else 0):
        tid = table_number_to_id(tn)
        sub_area = combo_subareas.get(tn, "")
        area = "terrasse" if sub_area == "terrasse" else "restaurant"
        
        # Standardwerte für fehlende Tische
        # Dezimaltische (38.1, 40.1) sind typisch Terassen-Nebentische
        is_decimal = "." in tn
        seats = 2 if is_decimal else 4  # Dezimaltische sind meist 2er
        
        table_doc = {
            "id": tid,
            "table_number": tn,
            "area": area,
            "sub_area": sub_area,
            "seats_default": seats,
            "seats_max": seats,
            "active": True,
            "fixed": False,
            "notes": "AUTO-ERGÄNZT: Fehlte in Legacy-Excel, aber in Kombinationen referenziert"
        }
        
        tables.append(table_doc)
        valid_ids.add(tid)
        added.append(tn)
    
    return tables, valid_ids, added


def build_combinations_seed(
    df: pd.DataFrame, 
    valid_table_ids: Set[str]
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Baut table_combinations_master_v2.json aus DataFrame.
    
    Validiert, dass alle referenzierten Tische existieren.
    
    Returns:
        (combinations_list, error_list)
    """
    combinations = []
    errors = []
    
    for _, row in df.iterrows():
        combo_id_raw = str(row["combo_id"]).strip()
        combo_id = f"combo_{combo_id_raw}"
        
        # Sub-Area (für Kombinationen ist das der relevante Bereich)
        sub_area = str(row.get("subarea", "")).strip().lower() if pd.notna(row.get("subarea")) else ""
        
        # Area aus Sub-Area ableiten
        area = "terrasse" if sub_area == "terrasse" else "restaurant"
        
        # Tische parsen
        tables_str = str(row.get("tables", ""))
        table_numbers = parse_tables_string(tables_str)
        table_ids = [table_number_to_id(tn) for tn in table_numbers]
        
        # Validierung: Alle Tische müssen existieren
        missing = [tid for tid in table_ids if tid not in valid_table_ids]
        if missing:
            errors.append(f"Kombination {combo_id_raw}: Fehlende Tische: {missing}")
            continue
        
        # Target Capacity
        target_capacity = int(row.get("target_capacity", 0)) if pd.notna(row.get("target_capacity")) else 0
        
        # Notes
        notes = str(row["notes"]).strip() if pd.notna(row.get("notes")) else None
        
        combo_doc = {
            "id": combo_id,
            "combo_id": combo_id_raw,
            "area": area,
            "sub_area": sub_area,
            "tables": table_ids,
            "target_capacity": target_capacity,
            "active": True
        }
        
        if notes:
            combo_doc["notes"] = notes
        
        combinations.append(combo_doc)
    
    return combinations, errors


def write_seed_file(data: List[Dict[str, Any]], output_path: str, description: str):
    """Schreibt Seed-Datei als JSON mit Metadaten."""
    
    seed_doc = {
        "_meta": {
            "version": "2.0.0",
            "description": description,
            "created_at": now_iso(),
            "source": "build_p1_tables.py",
            "target_db": "gastrocore_v2",
            "count": len(data)
        },
        "data": data
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(seed_doc, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Geschrieben: {output_path} ({len(data)} Einträge)")


def print_summary(tables: List[Dict], combinations: List[Dict]):
    """Gibt Summary aus."""
    
    print("\n" + "=" * 60)
    print("PHASE P1 SEEDS - SUMMARY")
    print("=" * 60)
    
    # Tische
    total_tables = len(tables)
    total_seats_default = sum(t["seats_default"] for t in tables)
    total_seats_max = sum(t["seats_max"] for t in tables)
    
    areas = {}
    for t in tables:
        key = f"{t['area']}/{t['sub_area']}" if t['sub_area'] else t['area']
        if key not in areas:
            areas[key] = {"count": 0, "seats": 0, "max": 0}
        areas[key]["count"] += 1
        areas[key]["seats"] += t["seats_default"]
        areas[key]["max"] += t["seats_max"]
    
    print(f"\n📋 TISCHE: {total_tables}")
    print(f"   Plätze (default): {total_seats_default}")
    print(f"   Plätze (max):     {total_seats_max}")
    print("\n   Nach Bereich:")
    for area, stats in sorted(areas.items()):
        print(f"   - {area}: {stats['count']} Tische, {stats['seats']}/{stats['max']} Plätze")
    
    # Kombinationen
    print(f"\n🔗 KOMBINATIONEN: {len(combinations)}")
    combo_by_area = {}
    for c in combinations:
        area = c["sub_area"] or c["area"]
        combo_by_area[area] = combo_by_area.get(area, 0) + 1
    for area, count in sorted(combo_by_area.items()):
        print(f"   - {area}: {count} Kombinationen")
    
    # Kapazitäten
    total_combo_capacity = sum(c["target_capacity"] for c in combinations)
    print(f"\n   Kombinierte Kapazität: {total_combo_capacity} Plätze")
    
    print("\n" + "=" * 60)
    print("✅ PHASE P1 SEEDS ERFOLGREICH ERSTELLT")
    print("=" * 60)
    
    print(f"\nDateien:")
    print(f"  - {OUTPUT_TABLES}")
    print(f"  - {OUTPUT_COMBINATIONS}")
    
    print(f"\nNächster Schritt:")
    print(f"  → Import in gastrocore_v2 (wenn MONGO_V2_URI gesetzt)")
    print()


# ============================================================
# OPTIONAL: IMPORT INTO MONGODB
# ============================================================

async def import_to_mongodb():
    """
    Importiert Seeds in MongoDB, NUR wenn MONGO_V2_URI existiert.
    """
    mongo_uri = os.environ.get("MONGO_V2_URI")
    
    if not mongo_uri:
        print("\n⚠️  MONGO_V2_URI nicht gesetzt - Import übersprungen")
        print("    Seeds wurden nur als JSON erstellt.")
        return False
    
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        
        print(f"\n🔄 Importiere in MongoDB (gastrocore_v2)...")
        
        client = AsyncIOMotorClient(mongo_uri)
        db = client.gastrocore_v2
        
        # Tables importieren
        with open(OUTPUT_TABLES, "r") as f:
            tables_data = json.load(f)["data"]
        
        await db.tables.delete_many({})  # Clear existing
        if tables_data:
            await db.tables.insert_many(tables_data)
            print(f"   ✅ {len(tables_data)} Tische importiert")
        
        # Combinations importieren
        with open(OUTPUT_COMBINATIONS, "r") as f:
            combos_data = json.load(f)["data"]
        
        await db.table_combinations.delete_many({})  # Clear existing
        if combos_data:
            await db.table_combinations.insert_many(combos_data)
            print(f"   ✅ {len(combos_data)} Kombinationen importiert")
        
        client.close()
        return True
        
    except ImportError:
        print("⚠️  motor nicht installiert - Import übersprungen")
        return False
    except Exception as e:
        print(f"❌ Import-Fehler: {e}")
        return False


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("CARLSBURG COCKPIT - PHASE P1: TABLES SEED BUILDER")
    print("Clean Rebuild (Variante C)")
    print("=" * 60)
    
    # 1. Input lesen
    print(f"\n📥 Lese Input-Dateien...")
    
    if not os.path.exists(INPUT_TABLES):
        print(f"❌ FEHLER: {INPUT_TABLES} nicht gefunden!")
        sys.exit(1)
    
    if not os.path.exists(INPUT_COMBINATIONS):
        print(f"❌ FEHLER: {INPUT_COMBINATIONS} nicht gefunden!")
        sys.exit(1)
    
    df_tables = pd.read_excel(INPUT_TABLES)
    df_combinations = pd.read_excel(INPUT_COMBINATIONS)
    
    print(f"   ✅ tables.xlsx: {len(df_tables)} Zeilen")
    print(f"   ✅ table_combinations.xlsx: {len(df_combinations)} Zeilen")
    
    # 2. Output-Verzeichnis erstellen
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 3. Tische bauen
    print(f"\n🔧 Baue Tische-Seed...")
    tables, valid_ids = build_tables_seed(df_tables)
    print(f"   ✅ {len(tables)} Tische aus Excel verarbeitet")
    
    # 3b. Fehlende Tische aus Kombinationen ergänzen (Legacy-Fix)
    tables, valid_ids, added_tables = add_missing_tables_from_combinations(
        tables, valid_ids, df_combinations
    )
    if added_tables:
        print(f"   ⚠️  {len(added_tables)} fehlende Tische ergänzt: {added_tables}")
        print(f"      (Legacy-Dateninkonsistenz - Tische waren in Kombinationen aber nicht in Tischliste)")
    
    # 4. Kombinationen bauen (mit Validierung)
    print(f"\n🔧 Baue Kombinationen-Seed...")
    combinations, errors = build_combinations_seed(df_combinations, valid_ids)
    
    if errors:
        print(f"\n❌ VALIDIERUNGSFEHLER ({len(errors)}):")
        for err in errors:
            print(f"   - {err}")
        print("\n⛔ ABBRUCH: Bitte Fehler korrigieren!")
        sys.exit(1)
    
    print(f"   ✅ {len(combinations)} Kombinationen verarbeitet (alle Tische validiert)")
    
    # 5. Seeds schreiben
    print(f"\n💾 Schreibe Seed-Dateien...")
    write_seed_file(
        tables, 
        OUTPUT_TABLES, 
        "Carlsburg Tische Master V2 - Source of Truth für Clean Rebuild"
    )
    write_seed_file(
        combinations, 
        OUTPUT_COMBINATIONS, 
        "Carlsburg Tischkombinationen Master V2 - Source of Truth für Clean Rebuild"
    )
    
    # 6. Summary
    print_summary(tables, combinations)
    
    # 7. Optional: MongoDB Import
    import asyncio
    asyncio.run(import_to_mongodb())
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
