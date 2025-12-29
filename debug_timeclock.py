#!/usr/bin/env python3
"""
Debug timeclock test - check user linking
"""

import sys
sys.path.append('/app')

from backend_test import GastroCoreAPITester

def main():
    tester = GastroCoreAPITester()
    
    print("🚀 Debug Timeclock Test")
    print("=" * 80)
    
    # First authenticate
    print("🔐 Authenticating...")
    auth_success = tester.test_authentication()
    if not auth_success:
        print("❌ Authentication failed")
        return False
    
    # Create a test user and link to staff member
    import time
    timestamp = int(time.time())
    user_data = {
        'name': 'Timeclock Test User',
        'email': f'timeclock{timestamp}@test.de',
        'password': 'TestPass123!',
        'role': 'schichtleiter'
    }
    
    print(f"\n👤 Creating test user: {user_data['email']}")
    create_result = tester.make_request('POST', 'users', user_data, tester.tokens['admin'], expected_status=200)
    if not create_result['success']:
        print(f"❌ Failed to create user: {create_result['status_code']}")
        print(f"Response: {create_result.get('data', {})}")
        return False
    
    new_user = create_result['data']
    user_id = new_user['id']
    print(f"✅ User created with ID: {user_id}")
    
    # Get first staff member and link
    print("\n👥 Getting staff members...")
    staff_result = tester.make_request('GET', 'staff/members', {}, tester.tokens['admin'], expected_status=200)
    if not staff_result['success']:
        print(f"❌ Failed to get staff members: {staff_result['status_code']}")
        return False
    
    staff = staff_result['data']
    if not staff:
        print("❌ No staff members found")
        return False
    
    first_staff = staff[0]
    staff_id = first_staff['id']
    staff_name = f"{first_staff.get('first_name', '')} {first_staff.get('last_name', '')}".strip()
    print(f"✅ Using staff member: {staff_name} (ID: {staff_id})")
    
    # Link user to staff member
    print(f"\n🔗 Linking user to staff member...")
    link_result = tester.make_request('POST', f'users/{user_id}/link-staff?staff_member_id={staff_id}', {}, tester.tokens['admin'], expected_status=200)
    if not link_result['success']:
        print(f"❌ Failed to link user to staff member: {link_result['status_code']}")
        print(f"Response: {link_result.get('data', {})}")
        return False
    
    print(f"✅ Link successful: {link_result['data']}")
    
    # Login as the test user
    print(f"\n🔑 Logging in as test user...")
    login_data = {'email': f'timeclock{timestamp}@test.de', 'password': 'TestPass123!'}
    login_result = tester.make_request('POST', 'auth/login', login_data, expected_status=200)
    if not login_result['success']:
        print(f"❌ Failed to login as test user: {login_result['status_code']}")
        print(f"Response: {login_result.get('data', {})}")
        return False
    
    test_token = login_result['data']['access_token']
    test_user = login_result['data']['user']
    print(f"✅ Login successful")
    print(f"User data: {test_user}")
    
    # Check if staff_member_id is in the user profile
    print(f"\n🔍 Checking user profile...")
    profile_result = tester.make_request('GET', 'auth/me', token=test_token, expected_status=200)
    if not profile_result['success']:
        print(f"❌ Failed to get user profile: {profile_result['status_code']}")
        return False
    
    profile = profile_result['data']
    print(f"Profile: {profile}")
    
    if profile.get('staff_member_id'):
        print(f"✅ User has staff_member_id: {profile['staff_member_id']}")
    else:
        print(f"❌ User missing staff_member_id")
        return False
    
    # Try clock-in
    print(f"\n⏰ Attempting clock-in...")
    clock_in_result = tester.make_request('POST', 'timeclock/clock-in', {}, test_token, expected_status=200)
    if clock_in_result['success']:
        print(f"✅ Clock-in successful: {clock_in_result['data']}")
        return True
    else:
        print(f"❌ Clock-in failed: {clock_in_result['status_code']}")
        print(f"Response: {clock_in_result.get('data', {})}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)