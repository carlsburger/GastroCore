#!/usr/bin/env python3
"""
POS Mail Import Status Test - Review Request
Test the POS Mail Import status and configuration
"""

import requests
import sys
import json

def test_pos_mail_import_status():
    """Test POS Mail Import status and configuration - Review Request"""
    print("📧 Testing POS Mail Import Status...")
    
    # Get backend URL from frontend .env
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    base_url = line.split('=', 1)[1].strip()
                    break
    except:
        base_url = "http://localhost:8001"
    
    print(f"🌐 Testing against: {base_url}")
    
    # 1. Login as admin@carlsburg.de with password Carlsburg2025!
    print("\n1. Logging in as admin@carlsburg.de...")
    login_data = {
        "email": "admin@carlsburg.de",
        "password": "Carlsburg2025!"
    }
    
    try:
        response = requests.post(f"{base_url}/api/auth/login", json=login_data)
        if response.status_code == 200:
            token_data = response.json()
            if "access_token" in token_data:
                token = token_data["access_token"]
                print("✅ Login successful - Token received")
            else:
                print("❌ Login failed - No access token in response")
                return False
        else:
            print(f"❌ Login failed - Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return False
    
    # 2. Call GET /api/pos/ingest/status
    print("\n2. Calling GET /api/pos/ingest/status...")
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        response = requests.get(f"{base_url}/api/pos/ingest/status", headers=headers)
        if response.status_code == 200:
            status_data = response.json()
            print("✅ POS status API call successful")
            print(f"Response data: {json.dumps(status_data, indent=2)}")
            
            # 3. Verify the response
            print("\n3. Verifying response data...")
            
            # Check imap_configured: should be false (password not set yet)
            imap_configured = status_data.get("imap_configured")
            if imap_configured == False:
                print("✅ imap_configured: false (password not set yet)")
            else:
                print(f"❌ imap_configured: Expected false, got {imap_configured}")
                return False
            
            # Check imap_host: should be "imap.ionos.de"
            imap_host = status_data.get("imap_host")
            if imap_host == "imap.ionos.de":
                print(f"✅ imap_host: {imap_host}")
            else:
                print(f"❌ imap_host: Expected 'imap.ionos.de', got {imap_host}")
                return False
            
            # Check imap_user: should be "berichte@carlsburg.de"
            imap_user = status_data.get("imap_user")
            if imap_user == "berichte@carlsburg.de":
                print(f"✅ imap_user: {imap_user}")
            else:
                print(f"❌ imap_user: Expected 'berichte@carlsburg.de', got {imap_user}")
                return False
            
            # Log additional fields for information
            additional_fields = ["scheduler_running", "documents_total", "metrics_total", "imap_folder"]
            print("\n📋 Additional status information:")
            for field in additional_fields:
                if field in status_data:
                    print(f"   {field}: {status_data.get(field)}")
            
            print("\n✅ ALL VERIFICATION TESTS PASSED!")
            return True
            
        else:
            print(f"❌ POS status API call failed - Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ POS status API error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting POS Mail Import Status Test...")
    print("=" * 60)
    
    success = test_pos_mail_import_status()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 POS MAIL IMPORT STATUS TEST: PASSED")
        sys.exit(0)
    else:
        print("💥 POS MAIL IMPORT STATUS TEST: FAILED")
        sys.exit(1)