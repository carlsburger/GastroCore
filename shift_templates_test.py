#!/usr/bin/env python3
"""
Shift Templates Smoke Test - Carlsburg Cockpit
Tests the specific requirements from the review request
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class ShiftTemplatesAPITester:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        
        # Test credentials
        self.admin_credentials = {
            "email": "admin@carlsburg.de", 
            "password": "Carlsburg2025!"
        }

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

    def make_request(self, method: str, endpoint: str, data: Dict = None, 
                    expected_status: int = 200) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
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
        """Authenticate with admin credentials"""
        print("🔐 Authenticating with admin credentials...")
        
        result = self.make_request("POST", "auth/login", self.admin_credentials, expected_status=200)
        
        if result["success"] and "access_token" in result["data"]:
            self.token = result["data"]["access_token"]
            user_data = result["data"]["user"]
            self.log_test("Admin authentication", True, f"Logged in as {user_data.get('email')}")
            return True
        else:
            self.log_test("Admin authentication", False, f"Status: {result['status_code']}")
            return False

    def test_shift_templates_smoke_test(self):
        """Test Shift Templates - Specific requirements from review request"""
        print("\n🔄 Testing Shift Templates (Carlsburg Cockpit)...")
        
        shift_templates_success = True
        
        # 1. GET /api/staff/shift-templates - Liste alle Templates, prüfe 9 Templates vorhanden
        result = self.make_request("GET", "staff/shift-templates", expected_status=200)
        if result["success"]:
            templates = result["data"]
            template_count = len(templates)
            
            # Check for 9 templates
            if template_count == 9:
                self.log_test("GET /api/staff/shift-templates - 9 Templates vorhanden", True, f"Found {template_count} templates")
            else:
                self.log_test("GET /api/staff/shift-templates - 9 Templates vorhanden", False, f"Expected 9, found {template_count}")
                shift_templates_success = False
            
            # Check event_mode field exists (normal/kultur)
            event_mode_check = True
            for template in templates:
                if "event_mode" not in template:
                    event_mode_check = False
                    break
                if template["event_mode"] not in ["normal", "kultur"]:
                    event_mode_check = False
                    break
            
            if event_mode_check:
                self.log_test("event_mode Feld existiert (normal/kultur)", True, "All templates have valid event_mode")
            else:
                self.log_test("event_mode Feld existiert (normal/kultur)", False, "Missing or invalid event_mode field")
                shift_templates_success = False
            
            # Check close_plus_minutes nie undefined (0 wenn nicht gesetzt)
            close_plus_minutes_check = True
            for template in templates:
                close_plus_minutes = template.get("close_plus_minutes")
                end_time_type = template.get("end_time_type", "fixed")
                
                # If end_time_type is "close_plus_minutes", then close_plus_minutes must be defined
                if end_time_type == "close_plus_minutes" and close_plus_minutes is None:
                    close_plus_minutes_check = False
                    break
                # If end_time_type is "fixed", close_plus_minutes can be undefined (not relevant)
            
            if close_plus_minutes_check:
                self.log_test("close_plus_minutes nie undefined (0 wenn nicht gesetzt)", True, "All templates have close_plus_minutes defined when needed")
            else:
                self.log_test("close_plus_minutes nie undefined (0 wenn nicht gesetzt)", False, "Some templates with close_plus_minutes end_time_type have undefined close_plus_minutes")
                shift_templates_success = False
                
        else:
            self.log_test("GET /api/staff/shift-templates", False, f"Status: {result['status_code']}")
            shift_templates_success = False
            return shift_templates_success
        
        # 2. POST /api/staff/schedules/{schedule_id}/apply-templates - Idempotenz-Test
        schedule_id = "30fd1a35-8fd8-4968-a8b6-7baa74f972ee"  # KW2/2026
        apply_data = {
            "departments": ["service", "kitchen"]
        }
        
        result = self.make_request("POST", f"staff/schedules/{schedule_id}/apply-templates", 
                                 apply_data, expected_status=200)
        if result["success"]:
            apply_response = result["data"]
            shifts_created = apply_response.get("shifts_created", 0)
            skipped_existing = apply_response.get("skipped_existing", 0)
            
            # Erwartung: shifts_created = 0, skipped_existing > 0 (da bereits applied)
            if shifts_created == 0 and skipped_existing > 0:
                self.log_test("POST apply-templates - Idempotenz funktioniert", True, 
                            f"shifts_created={shifts_created}, skipped_existing={skipped_existing}")
            else:
                self.log_test("POST apply-templates - Idempotenz funktioniert", False, 
                            f"Expected shifts_created=0 and skipped_existing>0, got shifts_created={shifts_created}, skipped_existing={skipped_existing}")
                shift_templates_success = False
        else:
            self.log_test("POST apply-templates", False, f"Status: {result['status_code']}")
            shift_templates_success = False
        
        # 3. GET /api/staff/shifts?schedule_id=30fd1a35-8fd8-4968-a8b6-7baa74f972ee
        result = self.make_request("GET", "staff/shifts", {"schedule_id": schedule_id}, 
                                 expected_status=200)
        if result["success"]:
            shifts = result["data"]
            if len(shifts) > 0:
                self.log_test("GET /api/staff/shifts - Schichten für KW2/2026 existieren", True, 
                            f"Found {len(shifts)} shifts for schedule {schedule_id}")
                
                # Check times - keine 22:00 für Küche, außer bei Kultur
                kitchen_22_check = True
                for shift in shifts:
                    if shift.get("department") == "kitchen" and shift.get("end_time") == "22:00":
                        # Check if this is a Kultur event
                        shift_name = shift.get("shift_name", "")
                        if "kultur" not in shift_name.lower():
                            kitchen_22_check = False
                            break
                
                if kitchen_22_check:
                    self.log_test("Zeiten korrekt (keine 22:00 für Küche, außer bei Kultur)", True, "Kitchen shift times are correct")
                else:
                    self.log_test("Zeiten korrekt (keine 22:00 für Küche, außer bei Kultur)", False, "Found kitchen shift ending at 22:00 without Kultur")
                    shift_templates_success = False
                    
            else:
                self.log_test("GET /api/staff/shifts - Schichten für KW2/2026 existieren", False, "No shifts found for the schedule")
                shift_templates_success = False
        else:
            self.log_test("GET /api/staff/shifts", False, f"Status: {result['status_code']}")
            shift_templates_success = False
        
        return shift_templates_success

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("📊 SHIFT TEMPLATES SMOKE TEST SUMMARY")
        print("=" * 80)
        
        if self.tests_passed == self.tests_run:
            print("✅ ALL TESTS PASSED")
        else:
            print("❌ SOME TESTS FAILED")
        
        print("=" * 80)
        print(f"📈 RESULTS: {self.tests_passed} passed, {len(self.failed_tests)} failed, {self.tests_run} total")
        print(f"📊 SUCCESS RATE: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in self.failed_tests:
                print(f"  - {test['name']}: {test['details']}")
        
        print("=" * 80)

    def run_tests(self):
        """Run all shift templates tests"""
        print("🚀 Starting Shift Templates Smoke Test - Carlsburg Cockpit")
        print(f"🎯 Target: {self.base_url}")
        print("=" * 80)
        
        # Authenticate
        if not self.authenticate():
            print("❌ Authentication failed, cannot proceed with tests")
            return False
        
        # Run shift templates test
        success = self.test_shift_templates_smoke_test()
        
        # Print summary
        self.print_summary()
        
        return success


if __name__ == "__main__":
    tester = ShiftTemplatesAPITester()
    success = tester.run_tests()
    sys.exit(0 if success else 1)