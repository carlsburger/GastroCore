#!/usr/bin/env python3
"""
Setup admin user with staff member link for timeclock testing
"""

import sys
sys.path.append('/app')

from backend_test import GastroCoreAPITester

def main():
    tester = GastroCoreAPITester()
    
    print("🚀 Setting up admin user for timeclock testing")
    print("=" * 80)
    
    # First authenticate
    print("🔐 Authenticating...")
    auth_success = tester.test_authentication()
    if not auth_success:
        print("❌ Authentication failed")
        return False
    
    # Get staff members
    print("\n👥 Getting staff members...")
    result = tester.make_request("GET", "staff/members", {}, tester.tokens["admin"], expected_status=200)
    if not result["success"]:
        print(f"❌ Failed to get staff members: {result['status_code']}")
        return False
    
    staff_members = result["data"]
    print(f"✅ Found {len(staff_members)} staff members")
    
    if not staff_members:
        print("❌ No staff members found")
        return False
    
    # Use first staff member
    first_staff = staff_members[0]
    staff_id = first_staff["id"]
    staff_name = f"{first_staff.get('first_name', '')} {first_staff.get('last_name', '')}".strip()
    
    print(f"📋 Using staff member: {staff_name} (ID: {staff_id})")
    
    # Get admin user ID
    result = tester.make_request("GET", "auth/me", token=tester.tokens["admin"], expected_status=200)
    if not result["success"]:
        print(f"❌ Failed to get admin user info: {result['status_code']}")
        return False
    
    admin_user = result["data"]
    admin_id = admin_user["id"]
    
    # Link admin to staff member
    print(f"\n🔗 Linking admin user to staff member...")
    result = tester.make_request("POST", f"users/{admin_id}/link-staff", {"staff_member_id": staff_id}, 
                               tester.tokens["admin"], expected_status=200)
    if result["success"]:
        print(f"✅ Successfully linked admin to staff member: {staff_name}")
        
        # Verify the link
        result = tester.make_request("GET", "auth/me", token=tester.tokens["admin"], expected_status=200)
        if result["success"]:
            updated_user = result["data"]
            if updated_user.get("staff_member_id") == staff_id:
                print(f"✅ Link verified: admin now has staff_member_id = {staff_id}")
                return True
            else:
                print(f"❌ Link verification failed: expected {staff_id}, got {updated_user.get('staff_member_id')}")
                return False
        else:
            print(f"❌ Failed to verify link: {result['status_code']}")
            return False
    else:
        print(f"❌ Failed to link admin to staff member: {result['status_code']}")
        print(f"Response: {result.get('data', {})}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)