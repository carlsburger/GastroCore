#!/usr/bin/env python3
"""
POS Cockpit Monitoring & Monatsabschluss Backend Testing
Test script for Modul 10_COCKPIT endpoints
"""

import requests
import sys
import json
from datetime import datetime

class POSCockpitTester:
    def __init__(self):
        # Use the backend URL from frontend .env
        try:
            with open('/app/frontend/.env', 'r') as f:
                for line in f:
                    if line.startswith('REACT_APP_BACKEND_URL='):
                        self.base_url = line.split('=', 1)[1].strip()
                        break
                else:
                    self.base_url = "http://localhost:8001"
        except:
            self.base_url = "http://localhost:8001"
        
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

    def make_request(self, method: str, endpoint: str, data=None, expected_status: int = 200):
        """Make HTTP request with error handling"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.admin_token:
            headers['Authorization'] = f'Bearer {self.admin_token}'
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=data)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            
            return {
                "success": response.status_code == expected_status,
                "status_code": response.status_code,
                "data": response.json() if response.content else {},
                "response": response
            }
        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "data": {},
                "error": str(e)
            }

    def authenticate(self):
        """Authenticate as admin"""
        print("🔐 Authenticating as admin...")
        
        credentials = {
            "email": "admin@carlsburg.de",
            "password": "Carlsburg2025!"
        }
        
        result = self.make_request("POST", "auth/login", credentials, expected_status=200)
        
        if result["success"] and "access_token" in result["data"]:
            self.admin_token = result["data"]["access_token"]
            user_data = result["data"]["user"]
            self.log_test("Admin authentication", True, 
                        f"Logged in as {user_data.get('email')}, Role: {user_data.get('role')}")
            return True
        else:
            self.log_test("Admin authentication", False, 
                        f"Status: {result['status_code']}, Data: {result.get('data', {})}")
            return False

    def test_pos_cockpit_endpoints(self):
        """Test all POS Cockpit Monitoring endpoints"""
        print("\n📊 Testing POS Cockpit Monitoring & Monatsabschluss...")
        
        if not self.admin_token:
            self.log_test("POS Cockpit Testing", False, "Admin token not available")
            return False
        
        pos_success = True
        
        # 1. GET /api/pos/ingest/status-extended (admin-only)
        print("\n1. Testing GET /api/pos/ingest/status-extended...")
        result = self.make_request("GET", "pos/ingest/status-extended", expected_status=200)
        if result["success"]:
            status_data = result["data"]
            required_fields = ["scheduler_running", "imap_configured", "documents_total", "metrics_total", "extended"]
            missing_fields = [field for field in required_fields if field not in status_data]
            
            if not missing_fields:
                extended = status_data.get("extended", {})
                extended_fields = ["docs_today", "docs_week", "failed_today", "failed_week", "current_month_crosscheck"]
                missing_extended = [field for field in extended_fields if field not in extended]
                
                if not missing_extended:
                    self.log_test("GET /api/pos/ingest/status-extended", True, 
                                f"All required fields present. Extended stats: docs_today={extended.get('docs_today')}, "
                                f"current_month_crosscheck warning={extended.get('current_month_crosscheck', {}).get('warning')}")
                else:
                    self.log_test("GET /api/pos/ingest/status-extended", False, 
                                f"Missing extended fields: {missing_extended}")
                    pos_success = False
            else:
                self.log_test("GET /api/pos/ingest/status-extended", False, 
                            f"Missing required fields: {missing_fields}")
                pos_success = False
        else:
            self.log_test("GET /api/pos/ingest/status-extended", False, 
                        f"Status: {result['status_code']}, Data: {result.get('data', {})}")
            pos_success = False
        
        # 2. GET /api/pos/monthly-crosscheck?month=2025-12 (admin-only)
        print("\n2. Testing GET /api/pos/monthly-crosscheck...")
        test_month = "2025-12"
        result = self.make_request("GET", f"pos/monthly-crosscheck?month={test_month}", expected_status=200)
        if result["success"]:
            crosscheck_data = result["data"]
            required_fields = ["month", "has_monthly_pdf", "has_daily_data", "daily_count", 
                             "daily_sum_net_total", "daily_sum_food_net", "daily_sum_beverage_net", 
                             "warning", "warning_reasons"]
            missing_fields = [field for field in required_fields if field not in crosscheck_data]
            
            if not missing_fields:
                self.log_test("GET /api/pos/monthly-crosscheck", True, 
                            f"Month: {crosscheck_data.get('month')}, Daily count: {crosscheck_data.get('daily_count')}, "
                            f"Has monthly PDF: {crosscheck_data.get('has_monthly_pdf')}, Warning: {crosscheck_data.get('warning')}")
            else:
                self.log_test("GET /api/pos/monthly-crosscheck", False, 
                            f"Missing required fields: {missing_fields}")
                pos_success = False
        else:
            self.log_test("GET /api/pos/monthly-crosscheck", False, 
                        f"Status: {result['status_code']}, Data: {result.get('data', {})}")
            pos_success = False
        
        # 3. GET /api/pos/monthly-status?month=2025-12 (admin-only)
        print("\n3. Testing GET /api/pos/monthly-status...")
        result = self.make_request("GET", f"pos/monthly-status?month={test_month}", expected_status=200)
        if result["success"]:
            status_data = result["data"]
            required_fields = ["month", "crosscheck", "confirmed", "locked", "confirmed_by", "confirmed_at"]
            missing_fields = [field for field in required_fields if field not in status_data]
            
            if not missing_fields:
                crosscheck = status_data.get("crosscheck", {})
                self.log_test("GET /api/pos/monthly-status", True, 
                            f"Month: {status_data.get('month')}, Confirmed: {status_data.get('confirmed')}, "
                            f"Locked: {status_data.get('locked')}, Crosscheck warning: {crosscheck.get('warning')}")
            else:
                self.log_test("GET /api/pos/monthly-status", False, 
                            f"Missing required fields: {missing_fields}")
                pos_success = False
        else:
            self.log_test("GET /api/pos/monthly-status", False, 
                        f"Status: {result['status_code']}, Data: {result.get('data', {})}")
            pos_success = False
        
        # 4. POST /api/pos/monthly/{month}/confirm (admin-only)
        print("\n4. Testing POST /api/pos/monthly/{month}/confirm...")
        # Test with a month that's likely not confirmed yet (2025-10)
        confirm_month = "2025-10"
        result = self.make_request("POST", f"pos/monthly/{confirm_month}/confirm", {}, expected_status=200)
        if result["success"]:
            confirm_data = result["data"]
            required_fields = ["status", "month", "confirmed_by", "confirmed_at", "crosscheck"]
            missing_fields = [field for field in required_fields if field not in confirm_data]
            
            if not missing_fields and confirm_data.get("status") == "confirmed":
                self.log_test("POST /api/pos/monthly/{month}/confirm", True, 
                            f"Month {confirm_data.get('month')} confirmed by {confirm_data.get('confirmed_by')}, "
                            f"Had warning: {confirm_data.get('had_warning')}")
                
                # Verify the confirm worked by checking status again
                verify_result = self.make_request("GET", f"pos/monthly-status?month={confirm_month}", expected_status=200)
                if verify_result["success"]:
                    verify_data = verify_result["data"]
                    if verify_data.get("confirmed") and verify_data.get("locked"):
                        self.log_test("Verify monthly confirm status", True, 
                                    f"Month {confirm_month} now shows confirmed=true, locked=true")
                    else:
                        self.log_test("Verify monthly confirm status", False, 
                                    f"Month {confirm_month} not properly confirmed/locked")
                        pos_success = False
                else:
                    self.log_test("Verify monthly confirm status", False, 
                                f"Status: {verify_result['status_code']}")
                    pos_success = False
            else:
                self.log_test("POST /api/pos/monthly/{month}/confirm", False, 
                            f"Missing fields or wrong status: {missing_fields}, status={confirm_data.get('status')}")
                pos_success = False
        else:
            self.log_test("POST /api/pos/monthly/{month}/confirm", False, 
                        f"Status: {result['status_code']}, Data: {result.get('data', {})}")
            pos_success = False
        
        # 5. Test existing endpoints still work
        print("\n5. Testing existing POS endpoints...")
        existing_endpoints = [
            ("GET", "pos/ingest/status", "Basic ingest status"),
            ("GET", "pos/documents", "Documents list"),
            ("GET", "pos/daily-metrics", "Daily metrics"),
            ("POST", "pos/ingest/trigger", "Manual ingest trigger"),
            ("POST", "pos/scheduler/start", "Scheduler start"),
            ("POST", "pos/scheduler/stop", "Scheduler stop")
        ]
        
        for method, endpoint, description in existing_endpoints:
            result = self.make_request(method, endpoint, {}, expected_status=200)
            if result["success"]:
                self.log_test(f"{method} /api/{endpoint} ({description})", True)
            else:
                self.log_test(f"{method} /api/{endpoint} ({description})", False, 
                            f"Status: {result['status_code']}")
                pos_success = False
        
        # 6. Test unauthorized access (should return 401/403)
        print("\n6. Testing unauthorized access...")
        # Temporarily remove token
        temp_token = self.admin_token
        self.admin_token = None
        
        unauthorized_endpoints = [
            ("GET", "pos/ingest/status-extended"),
            ("GET", f"pos/monthly-crosscheck?month={test_month}"),
            ("GET", f"pos/monthly-status?month={test_month}"),
            ("POST", f"pos/monthly/{confirm_month}/confirm")
        ]
        
        for method, endpoint in unauthorized_endpoints:
            result = self.make_request(method, endpoint, {}, expected_status=403)
            if result["success"]:
                self.log_test(f"Unauthorized access blocked for {endpoint}", True, "403 Forbidden as expected")
            else:
                self.log_test(f"Unauthorized access blocked for {endpoint}", False, 
                            f"Expected 403, got {result['status_code']}")
                pos_success = False
        
        # Restore token
        self.admin_token = temp_token
        
        return pos_success

    def run_tests(self):
        """Run all POS Cockpit tests"""
        print("🚀 Starting POS Cockpit Monitoring & Monatsabschluss Backend Tests")
        print(f"Backend URL: {self.base_url}")
        print("=" * 80)
        
        # Authenticate
        if not self.authenticate():
            print("❌ Authentication failed. Cannot proceed with tests.")
            return False
        
        # Run POS tests
        pos_success = self.test_pos_cockpit_endpoints()
        
        # Summary
        print("\n" + "=" * 80)
        print(f"🏁 POS COCKPIT TESTING COMPLETE")
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {(self.tests_passed / self.tests_run * 100):.1f}%")
        
        if self.failed_tests:
            print(f"\n❌ Failed tests ({len(self.failed_tests)}):")
            for test in self.failed_tests:
                print(f"  - {test['name']}: {test['details']}")
        else:
            print("\n✅ ALL TESTS PASSED!")
        
        return pos_success

if __name__ == "__main__":
    tester = POSCockpitTester()
    success = tester.run_tests()
    sys.exit(0 if success else 1)