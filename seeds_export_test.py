#!/usr/bin/env python3
"""
Seeds Backup Export Test - Review Request
Tests the Seeds Backup Export functionality specifically
"""

import requests
import sys
import json
from datetime import datetime

class SeedsExportTester:
    def __init__(self, base_url: str = None):
        # Use the backend URL from frontend .env if not provided
        if base_url is None:
            try:
                with open('/app/frontend/.env', 'r') as f:
                    for line in f:
                        if line.startswith('REACT_APP_BACKEND_URL='):
                            base_url = line.split('=', 1)[1].strip()
                            break
                if base_url is None:
                    base_url = "http://localhost:8001"
            except:
                base_url = "http://localhost:8001"
        
        self.base_url = base_url
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    {details}")
        
        if success:
            self.tests_passed += 1
        else:
            self.failed_tests.append({"name": name, "details": details})

    def login_admin(self):
        """Login as admin to get token"""
        print("🔐 Logging in as admin...")
        
        url = f"{self.base_url}/api/auth/login"
        credentials = {"email": "admin@carlsburg.de", "password": "Carlsburg2025!"}
        
        try:
            response = requests.post(url, json=credentials)
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    self.admin_token = data["access_token"]
                    self.log_test("Admin login", True, f"Token received")
                    return True
                else:
                    self.log_test("Admin login", False, "No access token in response")
                    return False
            else:
                self.log_test("Admin login", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Admin login", False, f"Error: {str(e)}")
            return False

    def test_seeds_export(self):
        """Test Seeds Backup Export functionality"""
        print("\n🗂️ Testing Seeds Backup Export...")
        
        if not self.admin_token:
            self.log_test("Seeds Export", False, "Admin token not available")
            return False
        
        # Test GET /api/admin/seeds/export
        url = f"{self.base_url}/api/admin/seeds/export"
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = requests.get(url, headers=headers)
            
            # Test 1: HTTP 200 status
            if response.status_code == 200:
                self.log_test("HTTP Status 200", True, "Received HTTP 200 OK")
            else:
                self.log_test("HTTP Status 200", False, f"Expected 200, got {response.status_code}")
                return False
            
            # Test 2: Content-Type should be application/zip
            content_type = response.headers.get('content-type', '')
            if 'application/zip' in content_type:
                self.log_test("Content-Type: application/zip", True, f"Content-Type: {content_type}")
            else:
                self.log_test("Content-Type: application/zip", False, f"Expected application/zip, got: {content_type}")
            
            # Test 3: Content-Disposition header should have filename
            content_disposition = response.headers.get('content-disposition', '')
            if 'filename' in content_disposition:
                self.log_test("Content-Disposition with filename", True, f"Content-Disposition: {content_disposition}")
            else:
                self.log_test("Content-Disposition with filename", False, f"Missing filename in Content-Disposition: {content_disposition}")
            
            # Test 4: Response body should be binary ZIP data
            if len(response.content) > 0:
                # Check for ZIP file signature (PK)
                if response.content[:2] == b'PK':
                    zip_size = len(response.content)
                    self.log_test("Valid ZIP file", True, f"Valid ZIP file, size: {zip_size} bytes")
                else:
                    self.log_test("Valid ZIP file", False, "Response body is not a valid ZIP file")
            else:
                self.log_test("Valid ZIP file", False, "Empty response body")
            
            # Test 5: Check that ZIP file can be downloaded without "responseText" errors
            if b'responseText' not in response.content:
                self.log_test("No responseText errors", True, "No responseText errors found in binary data")
            else:
                self.log_test("No responseText errors", False, "responseText found in binary response - indicates error")
            
            # Test 6: Verify ZIP structure (bonus test)
            try:
                import zipfile
                import io
                zip_buffer = io.BytesIO(response.content)
                with zipfile.ZipFile(zip_buffer, 'r') as zf:
                    file_list = zf.namelist()
                    seed_files = [f for f in file_list if f.startswith("seed/") and f.endswith(".json")]
                    
                    if len(seed_files) > 0:
                        self.log_test("ZIP structure verification", True, f"Contains {len(seed_files)} seed files")
                    else:
                        self.log_test("ZIP structure verification", False, "No seed files found in ZIP")
                        
            except Exception as e:
                self.log_test("ZIP structure verification", False, f"Error reading ZIP: {str(e)}")
                
        except Exception as e:
            self.log_test("Seeds Export Request", False, f"Error: {str(e)}")
            return False
        
        return True

    def run_test(self):
        """Run the Seeds Export test"""
        print("🚀 Starting Seeds Backup Export Test")
        print(f"📍 Backend URL: {self.base_url}")
        print("=" * 80)
        
        # Login first
        if not self.login_admin():
            print("❌ Cannot proceed without admin login")
            return False
        
        # Run the export test
        self.test_seeds_export()
        
        # Summary
        print("\n" + "=" * 80)
        print(f"🏁 SEEDS EXPORT TEST COMPLETE")
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            print(f"\n❌ FAILED TESTS ({len(self.failed_tests)}):")
            for test in self.failed_tests:
                print(f"  • {test['name']}: {test['details']}")
        else:
            print("\n✅ ALL TESTS PASSED!")
        
        return self.tests_passed == self.tests_run

if __name__ == "__main__":
    tester = SeedsExportTester()
    success = tester.run_test()
    sys.exit(0 if success else 1)