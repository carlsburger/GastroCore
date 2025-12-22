#!/usr/bin/env python3
"""
Dienstplan Live-Ready Backend Smoke Tests
Tests critical conflict detection, audit logs, and schedule management features
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class DienstplanTester:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.token = None
        self.test_data = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        
        # Test credentials from requirements
        self.credentials = [
            {"email": "admin@gastrocore.de", "password": "Admin123!"},
            {"email": "admin@carlsburg.de", "password": "Carlsburg2025!"}
        ]

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
        """Authenticate with available credentials"""
        print("\n🔐 Authenticating...")
        
        for creds in self.credentials:
            result = self.make_request("POST", "auth/login", creds, expected_status=200)
            
            if result["success"] and "access_token" in result["data"]:
                self.token = result["data"]["access_token"]
                user_data = result["data"]["user"]
                self.log_test(f"Login {creds['email']}", True, f"Role: {user_data.get('role')}")
                return True
            else:
                self.log_test(f"Login {creds['email']}", False, 
                            f"Status: {result['status_code']}, Data: {result.get('data', {})}")
        
        return False

    def setup_test_data(self):
        """Setup required test data (staff members, work areas, schedules)"""
        print("\n🏗️ Setting up test data...")
        
        # Seed staff data if needed
        result = self.make_request("POST", "seed-staff", {}, expected_status=200)
        if result["success"]:
            self.log_test("Seed staff data", True, "Staff data seeded successfully")
        else:
            # Check if data already exists
            if "bereits" in str(result.get("data", {})) or result["status_code"] == 200:
                self.log_test("Seed staff data", True, "Staff data already exists")
            else:
                self.log_test("Seed staff data", False, f"Status: {result['status_code']}")
                return False
        
        # Get staff members
        result = self.make_request("GET", "staff/members", expected_status=200)
        if result["success"] and result["data"]:
            self.test_data["staff_members"] = result["data"]
            self.test_data["staff_member_id"] = result["data"][0]["id"]
            self.log_test("Get staff members", True, f"Found {len(result['data'])} staff members")
        else:
            self.log_test("Get staff members", False, f"Status: {result['status_code']}")
            return False
        
        # Get work areas
        result = self.make_request("GET", "staff/work-areas", expected_status=200)
        if result["success"] and result["data"]:
            self.test_data["work_areas"] = result["data"]
            self.test_data["work_area_id"] = result["data"][0]["id"]
            self.log_test("Get work areas", True, f"Found {len(result['data'])} work areas")
        else:
            self.log_test("Get work areas", False, f"Status: {result['status_code']}")
            return False
        
        # Get or create schedule for KW 52/2025
        result = self.make_request("GET", "staff/schedules", {"year": 2025, "week": 52}, expected_status=200)
        if result["success"] and result["data"]:
            self.test_data["schedule_id"] = result["data"][0]["id"]
            self.log_test("Get existing schedule KW 52/2025", True, f"Schedule ID: {result['data'][0]['id']}")
        else:
            # Create schedule for KW 52/2025
            schedule_data = {"year": 2025, "week": 52}
            result = self.make_request("POST", "staff/schedules", schedule_data, expected_status=200)
            if result["success"] and "id" in result["data"]:
                self.test_data["schedule_id"] = result["data"]["id"]
                self.log_test("Create schedule KW 52/2025", True, f"Schedule ID: {result['data']['id']}")
            else:
                self.log_test("Create schedule KW 52/2025", False, f"Status: {result['status_code']}")
                return False
        
        return True

    def test_conflict_detection_double_booking(self):
        """TEST 1: KONFLIKTERKENNUNG DOPPELBELEGUNG (KRITISCH)"""
        print("\n🚨 TEST 1: Konflikterkennung Doppelbelegung...")
        
        if not all(key in self.test_data for key in ["schedule_id", "staff_member_id", "work_area_id"]):
            self.log_test("Conflict Detection - Double Booking", False, "Missing test data")
            return False
        
        # Create first shift
        shift_data = {
            "schedule_id": self.test_data["schedule_id"],
            "staff_member_id": self.test_data["staff_member_id"],
            "work_area_id": self.test_data["work_area_id"],
            "shift_date": "2025-12-22",
            "start_time": "10:00",
            "end_time": "18:00",
            "role": "service"
        }
        
        result = self.make_request("POST", "staff/shifts", shift_data, expected_status=200)
        if result["success"] and "id" in result["data"]:
            shift_id = result["data"]["id"]
            self.test_data["test_shift_id"] = shift_id
            self.log_test("Create first shift", True, f"Shift ID: {shift_id}")
        else:
            self.log_test("Create first shift", False, f"Status: {result['status_code']}, Data: {result.get('data', {})}")
            return False
        
        # Try to create SAME shift again (should fail with 409)
        result = self.make_request("POST", "staff/shifts", shift_data, expected_status=409)
        if result["success"]:
            error_message = result["data"].get("detail", "")
            if "Konflikt" in error_message or "bereits eingeplant" in error_message:
                self.log_test("Conflict Detection - Double Booking", True, 
                            f"✅ CRITICAL TEST PASSED: {error_message}")
                return True
            else:
                self.log_test("Conflict Detection - Double Booking", False, 
                            f"Wrong error message: {error_message}")
                return False
        else:
            self.log_test("Conflict Detection - Double Booking", False, 
                        f"Expected 409, got {result['status_code']}")
            return False

    def test_conflict_detection_rest_time(self):
        """TEST 2: KONFLIKTERKENNUNG RUHEZEIT 11h (KRITISCH)"""
        print("\n🚨 TEST 2: Konflikterkennung Ruhezeit 11h...")
        
        if not all(key in self.test_data for key in ["schedule_id", "staff_member_id", "work_area_id"]):
            self.log_test("Conflict Detection - Rest Time", False, "Missing test data")
            return False
        
        # Create evening shift
        evening_shift = {
            "schedule_id": self.test_data["schedule_id"],
            "staff_member_id": self.test_data["staff_member_id"],
            "work_area_id": self.test_data["work_area_id"],
            "shift_date": "2025-12-23",
            "start_time": "18:00",
            "end_time": "23:00",
            "role": "service"
        }
        
        result = self.make_request("POST", "staff/shifts", evening_shift, expected_status=200)
        if result["success"] and "id" in result["data"]:
            evening_shift_id = result["data"]["id"]
            self.log_test("Create evening shift", True, f"Evening shift ID: {evening_shift_id}")
        else:
            self.log_test("Create evening shift", False, f"Status: {result['status_code']}")
            return False
        
        # Try to create early morning shift next day (should fail with 409 - only 7h rest)
        morning_shift = {
            "schedule_id": self.test_data["schedule_id"],
            "staff_member_id": self.test_data["staff_member_id"],
            "work_area_id": self.test_data["work_area_id"],
            "shift_date": "2025-12-24",
            "start_time": "06:00",
            "end_time": "14:00",
            "role": "service"
        }
        
        result = self.make_request("POST", "staff/shifts", morning_shift, expected_status=409)
        if result["success"]:
            error_message = result["data"].get("detail", "")
            if "Ruhezeit" in error_message or "11h unterschritten" in error_message:
                self.log_test("Conflict Detection - Rest Time", True, 
                            f"✅ CRITICAL TEST PASSED: {error_message}")
                return True
            else:
                self.log_test("Conflict Detection - Rest Time", False, 
                            f"Wrong error message: {error_message}")
                return False
        else:
            self.log_test("Conflict Detection - Rest Time", False, 
                        f"Expected 409, got {result['status_code']}")
            return False

    def test_audit_logs_for_shifts(self):
        """TEST 3: AUDIT-LOGS FÜR SCHICHTEN"""
        print("\n📋 TEST 3: Audit-Logs für Schichten...")
        
        # Get audit logs for shift entity type
        result = self.make_request("GET", "audit-logs", {"entity_type": "shift", "limit": 5}, expected_status=200)
        if result["success"]:
            logs = result["data"]
            if logs:
                # Check for create action
                create_logs = [log for log in logs if log.get("action") == "create" and log.get("entity") == "shift"]
                if create_logs:
                    self.log_test("Audit-Logs für Schichten", True, 
                                f"Found {len(create_logs)} shift create audit entries")
                    return True
                else:
                    self.log_test("Audit-Logs für Schichten", False, 
                                "No shift create audit entries found")
                    return False
            else:
                self.log_test("Audit-Logs für Schichten", False, "No audit logs found")
                return False
        else:
            self.log_test("Audit-Logs für Schichten", False, f"Status: {result['status_code']}")
            return False

    def test_copy_week(self):
        """TEST 4: WOCHE KOPIEREN"""
        print("\n📅 TEST 4: Woche kopieren...")
        
        if "schedule_id" not in self.test_data:
            self.log_test("Copy Week", False, "Missing schedule ID")
            return False
        
        # Copy week
        result = self.make_request("POST", f"staff/schedules/{self.test_data['schedule_id']}/copy", 
                                 {}, expected_status=200)
        if result["success"]:
            response_data = result["data"]
            if ("new_schedule_id" in response_data and 
                response_data.get("success") and 
                "shifts_copied" in response_data):
                
                copied_count = response_data.get("shifts_copied", 0)
                new_schedule_id = response_data.get("new_schedule_id")
                
                self.log_test("Copy Week", True, 
                            f"New schedule: {new_schedule_id}, Shifts copied: {copied_count}")
                
                # Verify new schedule has status "entwurf"
                result = self.make_request("GET", f"staff/schedules/{new_schedule_id}", expected_status=200)
                if result["success"]:
                    new_schedule = result["data"]
                    if new_schedule.get("status") == "entwurf":
                        self.log_test("New schedule status", True, "Status is 'entwurf'")
                        return True
                    else:
                        self.log_test("New schedule status", False, 
                                    f"Expected 'entwurf', got {new_schedule.get('status')}")
                        return False
                else:
                    self.log_test("Verify new schedule", False, f"Status: {result['status_code']}")
                    return False
            else:
                self.log_test("Copy Week", False, f"Missing required fields in response: {response_data}")
                return False
        else:
            self.log_test("Copy Week", False, f"Status: {result['status_code']}")
            return False

    def test_my_shifts_endpoint(self):
        """TEST 5: MY-SHIFTS ENDPOINT"""
        print("\n👤 TEST 5: My-Shifts Endpoint...")
        
        # Test my-shifts endpoint
        result = self.make_request("GET", "staff/my-shifts", 
                                 {"date_from": "2025-01-01", "date_to": "2025-12-31"}, 
                                 expected_status=200)
        if result["success"]:
            shifts = result["data"]
            if isinstance(shifts, list):
                self.log_test("My-Shifts Endpoint", True, 
                            f"Retrieved {len(shifts)} shifts for logged-in user")
                return True
            else:
                self.log_test("My-Shifts Endpoint", False, "Response is not an array")
                return False
        else:
            self.log_test("My-Shifts Endpoint", False, f"Status: {result['status_code']}")
            return False

    def test_csv_export(self):
        """TEST 6: CSV-EXPORT"""
        print("\n📊 TEST 6: CSV-Export...")
        
        # Test CSV export
        url = f"{self.base_url}/api/staff/export/shifts/csv"
        headers = {'Authorization': f'Bearer {self.token}'}
        params = {"year": 2025, "week": 52}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'text/csv' in content_type or 'application/octet-stream' in content_type:
                    csv_size = len(response.content)
                    self.log_test("CSV-Export", True, 
                                f"CSV file downloaded successfully, size: {csv_size} bytes")
                    return True
                else:
                    self.log_test("CSV-Export", False, 
                                f"Expected CSV, got content-type: {content_type}")
                    return False
            else:
                self.log_test("CSV-Export", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("CSV-Export", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all Dienstplan tests"""
        print("🚀 Starting Dienstplan Live-Ready Backend Smoke Tests")
        print("=" * 60)
        
        # Authentication
        if not self.authenticate():
            print("\n❌ Authentication failed - cannot continue")
            return False
        
        # Setup test data
        if not self.setup_test_data():
            print("\n❌ Test data setup failed - cannot continue")
            return False
        
        # Run all tests
        tests = [
            self.test_conflict_detection_double_booking,
            self.test_conflict_detection_rest_time,
            self.test_audit_logs_for_shifts,
            self.test_copy_week,
            self.test_my_shifts_endpoint,
            self.test_csv_export
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                self.log_test(f"Exception in {test.__name__}", False, str(e))
        
        # Summary
        print("\n" + "=" * 60)
        print(f"📊 TEST SUMMARY")
        print(f"Total tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {len(self.failed_tests)}")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for failed in self.failed_tests:
                print(f"  - {failed['name']}: {failed['details']}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"\n✅ Success Rate: {success_rate:.1f}%")
        
        return len(self.failed_tests) == 0


if __name__ == "__main__":
    tester = DienstplanTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)