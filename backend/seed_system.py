"""
============================================================
CARLSBURG COCKPIT - FIRST-RUN SEED SYSTEM
Sprint 11: Idempotentes Seed für frischen Clone/Deployment
============================================================
"""

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from core.database import db
from core.auth import hash_password

logger = logging.getLogger(__name__)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def create_entity(data: dict, extra_fields: dict = None) -> dict:
    """Create entity with standard fields"""
    entity = {
        "id": str(uuid.uuid4()),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "archived": False,
        **data
    }
    if extra_fields:
        entity.update(extra_fields)
    return entity

# ============================================================
# SEED: ADMIN USER
# ============================================================

async def seed_admin_user() -> Dict[str, Any]:
    """Seed admin user - IDEMPOTENT"""
    log = []
    
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@carlsburg.de")
    admin_password = os.environ.get("ADMIN_PASSWORD", "Carlsburg2025!")
    
    existing = await db.users.find_one({"email": admin_email, "archived": False})
    if existing:
        log.append(f"✓ Admin-User '{admin_email}' existiert bereits – übersprungen")
        return {"seeded": False, "log": log, "user": {"email": admin_email}}
    
    user_doc = {
        "id": str(uuid.uuid4()),
        "email": admin_email,
        "name": "Administrator",
        "role": "admin",
        "password_hash": hash_password(admin_password),
        "is_active": True,
        "must_change_password": True,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "archived": False
    }
    await db.users.insert_one(user_doc)
    log.append(f"✓ Admin-User '{admin_email}' neu angelegt (Passwort ändern erforderlich)")
    
    return {
        "seeded": True,
        "log": log,
        "user": {"email": admin_email, "password": admin_password, "must_change_password": True}
    }


# ============================================================
# ADMIN-BOOTSTRAP BEIM START (Sprint: Live-Ready)
# ============================================================

async def bootstrap_admin_on_startup() -> bool:
    """
    Stellt sicher, dass IMMER mindestens ein Admin existiert.
    Wird beim App-Start aufgerufen - IDEMPOTENT, KEINE bestehenden User überschrieben.
    
    Prüft:
    1. Existiert IRGENDEIN aktiver Admin? → Falls ja: nichts tun
    2. Falls nein: Admin aus ENV-Variablen oder Default erstellen
    
    Returns:
        True wenn Bootstrap erfolgreich (ob neu erstellt oder existierend)
    """
    try:
        # Prüfe ob IRGENDEIN Admin existiert (nicht nur der aus ENV)
        any_admin = await db.users.find_one({
            "role": "admin",
            "archived": False,
            "is_active": True
        })
        
        if any_admin:
            logger.info(f"✓ Admin-Bootstrap: Admin '{any_admin.get('email')}' existiert bereits")
            return True
        
        # Kein Admin gefunden - erstelle einen
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@carlsburg.de")
        admin_password = os.environ.get("ADMIN_PASSWORD", "Carlsburg2025!")
        
        # Prüfe nochmal spezifisch auf diese Email (könnte archiviert sein)
        existing_archived = await db.users.find_one({"email": admin_email, "archived": True})
        if existing_archived:
            # Reaktiviere archivierten Admin
            await db.users.update_one(
                {"email": admin_email},
                {"$set": {
                    "archived": False,
                    "is_active": True,
                    "updated_at": now_iso()
                }}
            )
            logger.info(f"✓ Admin-Bootstrap: Admin '{admin_email}' reaktiviert")
            return True
        
        # Komplett neuen Admin erstellen
        user_doc = {
            "id": str(uuid.uuid4()),
            "email": admin_email,
            "name": "Administrator",
            "role": "admin",
            "password_hash": hash_password(admin_password),
            "is_active": True,
            "must_change_password": True,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "archived": False
        }
        await db.users.insert_one(user_doc)
        logger.info(f"✓ Admin-Bootstrap: Admin '{admin_email}' neu erstellt (Passwort aus ENV oder Default)")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Admin-Bootstrap fehlgeschlagen: {e}")
        return False

# ============================================================
# SEED: SCHICHTLEITER & MITARBEITER
# ============================================================

async def seed_staff_users() -> Dict[str, Any]:
    """Seed test staff users - IDEMPOTENT"""
    log = []
    created = []
    
    staff_users = [
        {"email": "schichtleiter@carlsburg.de", "name": "Schichtleiter Demo", "role": "schichtleiter", "password": "Schicht2025!"},
        {"email": "mitarbeiter@carlsburg.de", "name": "Mitarbeiter Demo", "role": "mitarbeiter", "password": "Mitarbeiter2025!"},
    ]
    
    for u in staff_users:
        existing = await db.users.find_one({"email": u["email"], "archived": False})
        if existing:
            log.append(f"✓ User '{u['email']}' existiert bereits – übersprungen")
            continue
        
        user_doc = {
            "id": str(uuid.uuid4()),
            "email": u["email"],
            "name": u["name"],
            "role": u["role"],
            "password_hash": hash_password(u["password"]),
            "is_active": True,
            "must_change_password": True,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "archived": False
        }
        await db.users.insert_one(user_doc)
        log.append(f"✓ User '{u['email']}' ({u['role']}) neu angelegt")
        created.append({"email": u["email"], "password": u["password"], "role": u["role"]})
    
    return {"seeded": len(created) > 0, "log": log, "created": created}

# ============================================================
# SEED: AREAS (BEREICHE)
# ============================================================

async def seed_areas() -> Dict[str, Any]:
    """Seed restaurant areas - IDEMPOTENT"""
    log = []
    area_ids = []
    
    areas = [
        {"name": "Restaurant", "description": "Hauptspeiseraum", "capacity": 60, "table_count": 15, "color": "#3B82F6", "sort_order": 1},
        {"name": "Wintergarten", "description": "Verglaster Anbau", "capacity": 30, "table_count": 8, "color": "#10B981", "sort_order": 2},
        {"name": "Terrasse", "description": "Außenbereich (saisonal)", "capacity": 40, "table_count": 10, "color": "#F59E0B", "sort_order": 3},
    ]
    
    for a in areas:
        existing = await db.areas.find_one({"name": a["name"], "archived": False})
        if existing:
            log.append(f"✓ Bereich '{a['name']}' existiert bereits – übersprungen")
            area_ids.append(existing["id"])
            continue
        
        area_doc = create_entity(a)
        await db.areas.insert_one(area_doc)
        area_ids.append(area_doc["id"])
        log.append(f"✓ Bereich '{a['name']}' neu angelegt (Kapazität: {a['capacity']})")
    
    return {"seeded": True, "log": log, "area_ids": area_ids}

# ============================================================
# SEED: OPENING HOURS
# ============================================================

async def seed_opening_hours() -> Dict[str, Any]:
    """Seed opening hours Mo-So - IDEMPOTENT"""
    log = []
    
    existing = await db.opening_hours.count_documents({})
    if existing >= 7:
        log.append("✓ Öffnungszeiten bereits vorhanden – übersprungen")
        return {"seeded": False, "log": log}
    
    # Delete incomplete data
    await db.opening_hours.delete_many({})
    
    # Day names for logging
    day_names = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    
    for day in range(7):
        is_closed = (day == 0)  # Montag Ruhetag
        
        if is_closed:
            slots = []
        else:
            slots = [
                {"start": "11:30", "end": "14:30"},  # Mittagsservice
                {"start": "17:30", "end": "22:00"},  # Abendservice
            ]
        
        hours_doc = {
            "id": str(uuid.uuid4()),
            "day_of_week": day,
            "is_closed": is_closed,
            "slots": slots,
            "created_at": now_iso(),
            "updated_at": now_iso()
        }
        await db.opening_hours.insert_one(hours_doc)
        
        if is_closed:
            log.append(f"✓ {day_names[day]}: Ruhetag")
        else:
            log.append(f"✓ {day_names[day]}: 11:30-14:30 & 17:30-22:00")
    
    return {"seeded": True, "log": log}

# ============================================================
# SEED: WORK AREAS (für Staff)
# ============================================================

async def seed_work_areas() -> Dict[str, Any]:
    """Seed work areas for staff scheduling - IDEMPOTENT"""
    log = []
    
    work_areas = [
        {"name": "Service", "description": "Kellner, Servicekräfte", "color": "#3B82F6", "sort_order": 1},
        {"name": "Küche", "description": "Köche, Küchenhilfen", "color": "#EF4444", "sort_order": 2},
        {"name": "Bar", "description": "Barkeeper, Getränkeservice", "color": "#8B5CF6", "sort_order": 3},
        {"name": "Event", "description": "Veranstaltungsbetreuung", "color": "#F59E0B", "sort_order": 4},
    ]
    
    for wa in work_areas:
        existing = await db.work_areas.find_one({"name": wa["name"], "archived": False})
        if existing:
            log.append(f"✓ Arbeitsbereich '{wa['name']}' existiert bereits – übersprungen")
            continue
        
        wa_doc = create_entity(wa)
        await db.work_areas.insert_one(wa_doc)
        log.append(f"✓ Arbeitsbereich '{wa['name']}' neu angelegt")
    
    return {"seeded": True, "log": log}

# ============================================================
# SEED: STAFF MEMBERS (Demo)
# ============================================================

async def seed_staff_members() -> Dict[str, Any]:
    """Seed demo staff members - IDEMPOTENT"""
    log = []
    
    # Get work area IDs
    service_area = await db.work_areas.find_one({"name": "Service"})
    kitchen_area = await db.work_areas.find_one({"name": "Küche"})
    
    service_id = service_area["id"] if service_area else None
    kitchen_id = kitchen_area["id"] if kitchen_area else None
    
    staff_members = [
        {
            "first_name": "Max",
            "last_name": "Mustermann",
            "email": "max.mustermann@carlsburg.de",
            "phone": "+49 170 1234567",
            "role": "service",
            "employment_type": "vollzeit",
            "weekly_hours": 40.0,
            "status": "aktiv",
            "work_area_ids": [service_id] if service_id else [],
            "entry_date": "2023-01-15",
        },
        {
            "first_name": "Anna",
            "last_name": "Koch",
            "email": "anna.koch@carlsburg.de",
            "phone": "+49 171 2345678",
            "role": "kitchen",
            "employment_type": "vollzeit",
            "weekly_hours": 40.0,
            "status": "aktiv",
            "work_area_ids": [kitchen_id] if kitchen_id else [],
            "entry_date": "2022-06-01",
        },
    ]
    
    for s in staff_members:
        existing = await db.staff_members.find_one({"email": s["email"], "archived": False})
        if existing:
            log.append(f"✓ Mitarbeiter '{s['first_name']} {s['last_name']}' existiert bereits – übersprungen")
            continue
        
        staff_doc = create_entity(s)
        await db.staff_members.insert_one(staff_doc)
        log.append(f"✓ Mitarbeiter '{s['first_name']} {s['last_name']}' neu angelegt ({s['role']})")
    
    return {"seeded": True, "log": log}

# ============================================================
# SEED: EVENTS (Demo)
# ============================================================

async def seed_demo_event() -> Dict[str, Any]:
    """Seed one demo event - IDEMPOTENT"""
    log = []
    
    existing = await db.events.find_one({"title": "Testevent Silvestermenü", "archived": False})
    if existing:
        log.append("✓ Demo-Event 'Testevent Silvestermenü' existiert bereits – übersprungen")
        return {"seeded": False, "log": log}
    
    event_date = (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%d")
    
    event_doc = create_entity({
        "title": "Testevent Silvestermenü",
        "description": "Ein festliches 5-Gänge-Menü zum Jahreswechsel mit Live-Musik und Mitternachts-Champagner.",
        "event_type": "dinner",
        "date": event_date,
        "time_start": "19:00",
        "time_end": "02:00",
        "capacity": 40,
        "available_capacity": 40,
        "price_per_person": 89.00,
        "deposit_required": True,
        "deposit_amount": 30.00,
        "status": "published",
        "booking_deadline": (datetime.now(timezone.utc) + timedelta(days=12)).strftime("%Y-%m-%d"),
        "image_url": None,
        "is_public": True,
    })
    
    await db.events.insert_one(event_doc)
    log.append(f"✓ Demo-Event 'Testevent Silvestermenü' neu angelegt (Datum: {event_date}, 40 Plätze)")
    
    # Add demo products for the event
    products = [
        {"name": "Menü Standard", "description": "5-Gänge inkl. Aperitif", "price": 89.00, "sort_order": 1},
        {"name": "Menü Vegetarisch", "description": "5-Gänge vegetarisch", "price": 79.00, "sort_order": 2},
        {"name": "Getränkepaket", "description": "Weinbegleitung + Softdrinks", "price": 35.00, "sort_order": 3},
    ]
    
    for p in products:
        product_doc = create_entity({
            "event_id": event_doc["id"],
            **p
        })
        await db.event_products.insert_one(product_doc)
        log.append(f"  → Produkt '{p['name']}' hinzugefügt")
    
    return {"seeded": True, "log": log, "event_id": event_doc["id"]}

# ============================================================
# SEED: LOYALTY SETTINGS & REWARDS
# ============================================================

async def seed_loyalty() -> Dict[str, Any]:
    """Seed loyalty settings and demo rewards - IDEMPOTENT"""
    log = []
    
    # Loyalty Settings
    existing_settings = await db.loyalty_settings.find_one({})
    if not existing_settings:
        settings_doc = {
            "id": str(uuid.uuid4()),
            "points_per_euro": 0.1,  # 10 Punkte pro 100€
            "max_points_per_transaction": 500,
            "qr_validity_seconds": 90,
            "rounding": "floor",
            "created_at": now_iso(),
            "updated_at": now_iso()
        }
        await db.loyalty_settings.insert_one(settings_doc)
        log.append("✓ Loyalty-Einstellungen angelegt (10 Punkte pro 100€)")
    else:
        log.append("✓ Loyalty-Einstellungen existieren bereits – übersprungen")
    
    # Demo Rewards
    rewards = [
        {"name": "Kaffeespezialität gratis", "description": "Ein Heißgetränk nach Wahl", "reward_type": "free_item", "points_cost": 20},
        {"name": "Dessert gratis", "description": "Ein Dessert aus der Karte", "reward_type": "free_item", "points_cost": 50},
        {"name": "10% Rabatt", "description": "Auf die gesamte Rechnung", "reward_type": "discount", "points_cost": 100},
        {"name": "Flasche Hauswein", "description": "0,75l Hauswein rot oder weiß", "reward_type": "free_item", "points_cost": 150},
    ]
    
    for r in rewards:
        existing = await db.rewards.find_one({"name": r["name"], "archived": False})
        if existing:
            log.append(f"✓ Reward '{r['name']}' existiert bereits – übersprungen")
            continue
        
        reward_doc = create_entity({**r, "is_active": True})
        await db.rewards.insert_one(reward_doc)
        log.append(f"✓ Reward '{r['name']}' neu angelegt ({r['points_cost']} Punkte)")
    
    return {"seeded": True, "log": log}

# ============================================================
# SEED: PAYMENT RULES
# ============================================================

async def seed_payment_rules() -> Dict[str, Any]:
    """Seed default payment rules - IDEMPOTENT"""
    log = []
    
    rules = [
        {
            "name": "Gruppenbuchung ab 8 Personen",
            "description": "Anzahlung bei Gruppen ab 8 Personen",
            "trigger": "group_size",
            "trigger_value": 8,
            "payment_type": "deposit_per_person",
            "amount": 15.00,
            "is_active": True,
        },
        {
            "name": "Greylist-Gast",
            "description": "Vorauszahlung für Gäste mit No-Show-Historie",
            "trigger": "greylist",
            "trigger_value": 1,
            "payment_type": "full_prepayment",
            "amount": 0,  # Full amount
            "is_active": True,
        },
    ]
    
    for r in rules:
        existing = await db.payment_rules.find_one({"name": r["name"], "archived": False})
        if existing:
            log.append(f"✓ Zahlungsregel '{r['name']}' existiert bereits – übersprungen")
            continue
        
        rule_doc = create_entity(r)
        await db.payment_rules.insert_one(rule_doc)
        log.append(f"✓ Zahlungsregel '{r['name']}' neu angelegt")
    
    return {"seeded": True, "log": log}

# ============================================================
# SEED: DEFAULT SETTINGS
# ============================================================

async def seed_settings() -> Dict[str, Any]:
    """Seed default app settings - IDEMPOTENT"""
    log = []
    
    settings = [
        {"key": "restaurant_name", "value": "Carlsburg Restaurant", "description": "Restaurant-Name"},
        {"key": "max_total_capacity", "value": "130", "description": "Maximale Gesamtkapazität"},
        {"key": "no_show_greylist_threshold", "value": "2", "description": "No-Shows bis Greylist"},
        {"key": "no_show_blacklist_threshold", "value": "4", "description": "No-Shows bis Blacklist"},
        {"key": "default_reservation_duration", "value": "90", "description": "Standard-Aufenthaltsdauer (Minuten)"},
        {"key": "booking_advance_days", "value": "60", "description": "Maximale Vorausbuchung (Tage)"},
    ]
    
    for s in settings:
        existing = await db.settings.find_one({"key": s["key"]})
        if existing:
            log.append(f"✓ Setting '{s['key']}' existiert bereits – übersprungen")
            continue
        
        setting_doc = create_entity(s)
        setting_doc["key"] = s["key"]
        await db.settings.insert_one(setting_doc)
        log.append(f"✓ Setting '{s['key']}' = '{s['value']}' angelegt")
    
    return {"seeded": True, "log": log}

# ============================================================
# MAIN SEED ORCHESTRATOR
# ============================================================

async def run_full_seed(force: bool = False) -> Dict[str, Any]:
    """
    Run complete seed process - IDEMPOTENT
    
    Args:
        force: If True, run even if data exists (still idempotent per item)
    
    Returns:
        Complete seed report
    """
    logger.info("=== SEED-PROZESS GESTARTET ===")
    
    results = {
        "success": True,
        "timestamp": now_iso(),
        "force": force,
        "modules": {},
        "summary": {
            "total_steps": 0,
            "new_items": 0,
            "skipped_items": 0,
        },
        "credentials": {},
        "full_log": []
    }
    
    # Safety check
    if not force:
        user_count = await db.users.count_documents({"archived": False})
        if user_count >= 3:
            results["success"] = False
            results["message"] = "Datenbank enthält bereits Produktivdaten. Seed abgebrochen. Nutze FORCE_SEED=true um trotzdem zu seeden."
            results["full_log"].append("⚠ Seed abgebrochen: Existierende Daten gefunden")
            return results
    
    try:
        # 1. Admin User
        results["full_log"].append("\n📌 PHASE 1: Admin-User")
        admin_result = await seed_admin_user()
        results["modules"]["admin_user"] = admin_result
        results["full_log"].extend(admin_result["log"])
        if admin_result.get("seeded") and admin_result.get("user", {}).get("password"):
            results["credentials"]["admin"] = admin_result["user"]
        
        # 2. Staff Users
        results["full_log"].append("\n📌 PHASE 2: Staff-User")
        staff_result = await seed_staff_users()
        results["modules"]["staff_users"] = staff_result
        results["full_log"].extend(staff_result["log"])
        if staff_result.get("created"):
            results["credentials"]["staff"] = staff_result["created"]
        
        # 3. Areas
        results["full_log"].append("\n📌 PHASE 3: Bereiche")
        areas_result = await seed_areas()
        results["modules"]["areas"] = areas_result
        results["full_log"].extend(areas_result["log"])
        
        # 4. Opening Hours
        results["full_log"].append("\n📌 PHASE 4: Öffnungszeiten")
        hours_result = await seed_opening_hours()
        results["modules"]["opening_hours"] = hours_result
        results["full_log"].extend(hours_result["log"])
        
        # 5. Work Areas
        results["full_log"].append("\n📌 PHASE 5: Arbeitsbereiche")
        work_areas_result = await seed_work_areas()
        results["modules"]["work_areas"] = work_areas_result
        results["full_log"].extend(work_areas_result["log"])
        
        # 6. Staff Members
        results["full_log"].append("\n📌 PHASE 6: Mitarbeiter")
        staff_members_result = await seed_staff_members()
        results["modules"]["staff_members"] = staff_members_result
        results["full_log"].extend(staff_members_result["log"])
        
        # 7. Demo Event
        results["full_log"].append("\n📌 PHASE 7: Demo-Event")
        event_result = await seed_demo_event()
        results["modules"]["demo_event"] = event_result
        results["full_log"].extend(event_result["log"])
        
        # 8. Loyalty
        results["full_log"].append("\n📌 PHASE 8: Loyalty & Rewards")
        loyalty_result = await seed_loyalty()
        results["modules"]["loyalty"] = loyalty_result
        results["full_log"].extend(loyalty_result["log"])
        
        # 9. Payment Rules
        results["full_log"].append("\n📌 PHASE 9: Zahlungsregeln")
        payment_result = await seed_payment_rules()
        results["modules"]["payment_rules"] = payment_result
        results["full_log"].extend(payment_result["log"])
        
        # 10. Settings
        results["full_log"].append("\n📌 PHASE 10: App-Einstellungen")
        settings_result = await seed_settings()
        results["modules"]["settings"] = settings_result
        results["full_log"].extend(settings_result["log"])
        
        # Summary
        for log_line in results["full_log"]:
            results["summary"]["total_steps"] += 1
            if "neu angelegt" in log_line:
                results["summary"]["new_items"] += 1
            elif "übersprungen" in log_line:
                results["summary"]["skipped_items"] += 1
        
        results["full_log"].append("\n" + "=" * 50)
        results["full_log"].append("✅ SEED-PROZESS ABGESCHLOSSEN")
        results["full_log"].append(f"   Neu angelegt: {results['summary']['new_items']}")
        results["full_log"].append(f"   Übersprungen: {results['summary']['skipped_items']}")
        
        logger.info("=== SEED-PROZESS ERFOLGREICH ===")
        
    except Exception as e:
        logger.error(f"Seed-Fehler: {str(e)}")
        results["success"] = False
        results["error"] = str(e)
        results["full_log"].append(f"\n❌ FEHLER: {str(e)}")
    
    return results

# ============================================================
# VERIFICATION
# ============================================================

async def verify_seed() -> Dict[str, Any]:
    """Verify seed was successful"""
    checks = {}
    
    # Check users
    admin = await db.users.find_one({"role": "admin", "archived": False})
    checks["admin_exists"] = admin is not None
    
    # Check areas
    area_count = await db.areas.count_documents({"archived": False})
    checks["areas_exist"] = area_count >= 3
    checks["area_count"] = area_count
    
    # Check opening hours
    hours_count = await db.opening_hours.count_documents({})
    checks["opening_hours_exist"] = hours_count == 7
    
    # Check events
    event = await db.events.find_one({"status": "published", "archived": False})
    checks["published_event_exists"] = event is not None
    
    # Check rewards
    reward_count = await db.rewards.count_documents({"is_active": True, "archived": False})
    checks["rewards_exist"] = reward_count >= 1
    checks["reward_count"] = reward_count
    
    # Check payment rules
    rule_count = await db.payment_rules.count_documents({"is_active": True, "archived": False})
    checks["payment_rules_exist"] = rule_count >= 1
    
    # Overall status
    all_passed = all([
        checks["admin_exists"],
        checks["areas_exist"],
        checks["opening_hours_exist"],
        checks["published_event_exists"],
        checks["rewards_exist"],
        checks["payment_rules_exist"]
    ])
    
    checks["all_passed"] = all_passed
    checks["status"] = "READY" if all_passed else "INCOMPLETE"
    
    return checks
