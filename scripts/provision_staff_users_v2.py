#!/usr/bin/env python3
"""
============================================================
CARLSBURG COCKPIT - STAFF USER PROVISIONING V2
============================================================

Erstellt User-Accounts für alle Staff Members.
- Verknüpft via staff_member_id
- Generiert zufällige Initial-Passwörter (nur Hash in DB)
- Schreibt Credentials in /app/tmp/initial_passwords.csv (NICHT committen!)
- Idempotent: keine Duplikate

KEINE neuen Endpoints. KEINE Auth-Flow Änderungen.
"""

import os
import sys
import uuid
import csv
import secrets
import string
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple
from dotenv import load_dotenv

# Load environment
load_dotenv('/app/backend/.env')

# Add backend to path for imports
sys.path.insert(0, '/app/backend')
from core.auth import hash_password

# ============================================================
# CONFIGURATION
# ============================================================

OUTPUT_CSV = "/app/tmp/initial_passwords.csv"
DEFAULT_ROLE = "mitarbeiter"
EXTERNAL_SOURCE = "staff_provisioning_v2"

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def now_iso() -> str:
    """ISO 8601 UTC timestamp"""
    return datetime.now(timezone.utc).isoformat()


def generate_password(length: int = 16) -> str:
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_email_for_staff(staff: dict) -> str:
    """
    Generate email for staff without email.
    Format: staff_<personnel_number>@local.invalid
    """
    personnel_number = staff.get("personnel_number", "")
    if personnel_number:
        return f"staff_{personnel_number}@local.invalid"
    
    # Fallback: use staff id
    staff_id = staff.get("id", "unknown")[:8]
    return f"staff_{staff_id}@local.invalid"


def get_display_name(staff: dict) -> str:
    """Get display name for user"""
    display = staff.get("display_name")
    if display:
        return display
    
    first = staff.get("first_name", "")
    last = staff.get("last_name", "")
    return f"{first} {last}".strip() or "Mitarbeiter"


# ============================================================
# MAIN PROVISIONING
# ============================================================

async def provision_staff_users():
    """
    Main provisioning function.
    
    Returns:
        (created_count, skipped_count, error_count, credentials_list)
    """
    from motor.motor_asyncio import AsyncIOMotorClient
    
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "gastrocore_v2")
    
    if not mongo_url:
        print("❌ MONGO_URL nicht gesetzt. ABBRUCH.")
        return 0, 0, 0, []
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Verify connection
    try:
        await db.command("ping")
    except Exception as e:
        print(f"❌ DB nicht erreichbar: {e}")
        client.close()
        return 0, 0, 0, []
    
    print(f"✅ Verbunden mit {db_name}")
    
    # Load all staff members
    staff_members = await db.staff_members.find(
        {"archived": {"$ne": True}},
        {"_id": 0}
    ).to_list(1000)
    
    print(f"📋 {len(staff_members)} Staff Members gefunden")
    
    created = 0
    skipped = 0
    errors = 0
    credentials = []
    
    for staff in staff_members:
        staff_id = staff.get("id")
        staff_email = staff.get("email")
        personnel_number = staff.get("personnel_number")
        
        if not staff_id:
            print(f"   ⚠️  Staff ohne ID übersprungen")
            errors += 1
            continue
        
        # Check if user already exists (by staff_member_id OR email)
        existing_by_link = await db.users.find_one({
            "staff_member_id": staff_id,
            "archived": {"$ne": True}
        })
        
        if existing_by_link:
            skipped += 1
            continue
        
        # Check by email if staff has email
        if staff_email:
            existing_by_email = await db.users.find_one({
                "email": staff_email,
                "archived": {"$ne": True}
            })
            
            if existing_by_email:
                # Link existing user to staff
                if not existing_by_email.get("staff_member_id"):
                    await db.users.update_one(
                        {"id": existing_by_email["id"]},
                        {"$set": {
                            "staff_member_id": staff_id,
                            "external_source": EXTERNAL_SOURCE,
                            "updated_at": now_iso()
                        }}
                    )
                    print(f"   🔗 User {existing_by_email['id'][:8]}... verknüpft mit Staff {staff_id[:8]}...")
                skipped += 1
                continue
        
        # Create new user
        try:
            # Determine email
            user_email = staff_email if staff_email else generate_email_for_staff(staff)
            
            # Generate password
            initial_password = generate_password(16)
            password_hash = hash_password(initial_password)
            
            # Create user document
            user_id = str(uuid.uuid4())
            user_doc = {
                "id": user_id,
                "email": user_email,
                "name": get_display_name(staff),
                "role": DEFAULT_ROLE,
                "password_hash": password_hash,
                "is_active": True,
                "must_change_password": True,
                "staff_member_id": staff_id,
                "external_source": EXTERNAL_SOURCE,
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "archived": False
            }
            
            await db.users.insert_one(user_doc)
            
            # Store credentials for CSV (password only in memory, then to file)
            credentials.append({
                "user_id": user_id,
                "email": user_email,
                "name": user_doc["name"],
                "staff_member_id": staff_id,
                "personnel_number": personnel_number or "",
                "initial_password": initial_password
            })
            
            created += 1
            
        except Exception as e:
            print(f"   ❌ Fehler bei Staff {staff_id[:8]}...: {e}")
            errors += 1
    
    # Create indexes
    await db.users.create_index("id", unique=True)
    await db.users.create_index("email", unique=True)
    await db.users.create_index("staff_member_id", sparse=True)
    
    client.close()
    
    return created, skipped, errors, credentials


def write_credentials_csv(credentials: List[Dict]) -> str:
    """
    Write credentials to CSV file.
    SECURITY: This file must NOT be committed to git!
    """
    if not credentials:
        return ""
    
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "user_id", "email", "name", "staff_member_id", 
            "personnel_number", "initial_password"
        ])
        writer.writeheader()
        writer.writerows(credentials)
    
    # Set restrictive permissions
    os.chmod(OUTPUT_CSV, 0o600)
    
    return OUTPUT_CSV


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("STAFF USER PROVISIONING V2")
    print("=" * 60)
    print("")
    
    # Run provisioning
    created, skipped, errors, credentials = asyncio.run(provision_staff_users())
    
    print("")
    print("=" * 60)
    print("ERGEBNIS")
    print("=" * 60)
    print(f"   Erstellt:    {created}")
    print(f"   Übersprungen: {skipped}")
    print(f"   Fehler:      {errors}")
    
    # Write credentials to CSV
    if credentials:
        csv_path = write_credentials_csv(credentials)
        print(f"\n📄 Credentials gespeichert: {csv_path}")
        print(f"   ⚠️  NICHT COMMITTEN! Nur für initiale Verteilung.")
    
    print("")
    print("=" * 60)
    print("✅ PROVISIONING ABGESCHLOSSEN")
    print("=" * 60)
    
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
