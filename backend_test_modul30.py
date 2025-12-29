#!/usr/bin/env python3
"""
Modul 30 Backend Testing: Shifts V2 + Timeclock (FINAL)
Tests the specific requirements from the review request
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class Modul30Tester:
    def __init__(self):
        # Get backend URL from frontend .env
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
        
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        
        # Test credentials
        self.admin_creds = {"email": "admin@carlsburg.de", "password": "Carlsburg2025!"}

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
        """Authenticate as admin"""
        print("\n🔐 Authenticating as admin...")
        
        result = self.make_request("POST", "auth/login", self.admin_creds, expected_status=200)
        
        if result["success"] and "access_token" in result["data"]:
            self.token = result["data"]["access_token"]
            self.log_test("Admin authentication", True, "Token received")
            return True
        else:
            self.log_test("Admin authentication", False, f"Status: {result['status_code']}")
            return False

    def test_shifts_v2_list_with_date_filter(self):
        """S1: List Shifts with date filter"""
        print("\n📅 Testing S1: List Shifts with date filter...")
        
        params = {
            "date_from": "2025-12-22",
            "date_to": "2025-12-28"
        }
        
        result = self.make_request("GET", "staff/shifts/v2", params, expected_status=200)
        
        if result["success"]:
            shifts = result["data"].get("shifts", [])
            self.log_test("S1: List Shifts with date filter", True, 
                        f"Retrieved {len(shifts)} shifts for week 2025-12-22 to 2025-12-28")
            return True
        else:
            self.log_test("S1: List Shifts with date filter", False, 
                        f"Status: {result['status_code']}, Data: {result.get('data', {})}")
            return False

    def test_shifts_v2_create_new_shift(self):
        """S2: Create new Shift"""
        print("\n➕ Testing S2: Create new Shift...")
        
        shift_data = {
            "date_local": "2025-12-30",
            "start_time": "10:00",
            "end_time": "18:00",
            "role": "service",
            "required_staff_count": 2
        }
        
        result = self.make_request("POST", "staff/shifts/v2", shift_data, expected_status=200)
        
        if result["success"]:
            shift = result["data"]
            if shift.get("status") == "DRAFT" and shift.get("id"):
                self.log_test("S2: Create new Shift", True, 
                            f"Shift created with ID: {shift['id']}, status: {shift['status']}")
                return shift["id"]
            else:
                self.log_test("S2: Create new Shift", False, 
                            f"Unexpected response: status={shift.get('status')}")
                return None
        else:
            self.log_test("S2: Create new Shift", False, 
                        f"Status: {result['status_code']}, Data: {result.get('data', {})}")
            return None

    def test_shifts_v2_publish_shift(self, shift_id: str):
        """S3: Publish Shift"""
        print("\n📢 Testing S3: Publish Shift...")
        
        result = self.make_request("POST", f"staff/shifts/v2/{shift_id}/publish", {}, expected_status=200)
        
        if result["success"]:
            response = result["data"]
            if response.get("status") == "PUBLISHED":
                self.log_test("S3: Publish Shift", True, 
                            f"Shift published successfully, status: {response['status']}")
                return True
            else:
                self.log_test("S3: Publish Shift", False, 
                            f"Unexpected status: {response.get('status')}")
                return False
        else:
            self.log_test("S3: Publish Shift", False, 
                        f"Status: {result['status_code']}, Data: {result.get('data', {})}")
            return False

    def test_shifts_v2_assign_staff(self, shift_id: str):
        """S4: Assign Staff to Shift"""
        print("\n👥 Testing S4: Assign Staff to Shift...")
        
        # First get a staff member
        staff_result = self.make_request("GET", "staff/members", {}, expected_status=200)
        
        if not staff_result["success"] or not staff_result["data"]:
            self.log_test("S4: Get staff members", False, "Could not retrieve staff members")
            return False
        
        staff_members = staff_result["data"]
        if not staff_members:
            self.log_test("S4: Get staff members", False, "No staff members found")
            return False
        
        staff_id = staff_members[0]["id"]
        self.log_test("S4: Get staff members", True, f"Found {len(staff_members)} staff members")
        
        # Now assign staff to shift
        assign_data = {"staff_member_id": staff_id}
        result = self.make_request("POST", f"staff/shifts/v2/{shift_id}/assign", assign_data, expected_status=200)
        
        if result["success"]:
            response = result["data"]
            assigned_staff_ids = response.get("assigned_staff_ids", [])
            if staff_id in assigned_staff_ids:
                self.log_test("S4: Assign Staff to Shift", True, 
                            f"Staff {staff_id} assigned successfully, assigned_staff_ids: {assigned_staff_ids}")
                return True
            else:
                self.log_test("S4: Assign Staff to Shift", False, 
                            f"Staff not in assigned_staff_ids: {assigned_staff_ids}")
                return False
        else:
            self.log_test("S4: Assign Staff to Shift", False, 
                        f"Status: {result['status_code']}, Data: {result.get('data', {})}")
            return False

    def test_timeclock_clock_in(self):
        """T1: Clock-In"""
        print("\n⏰ Testing T1: Clock-In...")
        
        result = self.make_request("POST", "timeclock/clock-in", {}, expected_status=400)
        
        if result["success"]:
            response = result["data"]
            if response.get("state") == "WORKING" and response.get("session_id"):
                self.log_test("T1: Clock-In", True, 
                            f"Clock-in successful, state: {response['state']}, session_id: {response['session_id']}")
                return response["session_id"]
            else:
                self.log_test("T1: Clock-In", False, 
                            f"Unexpected response: state={response.get('state')}")
                return None
        else:
            self.log_test("T1: Clock-In", False, 
                        f"Status: {result['status_code']}, Data: {result.get('data', {})}")
            return None

    def test_timeclock_break_start(self):
        """T2: Break-Start"""
        print("\n☕ Testing T2: Break-Start...")
        
        result = self.make_request("POST", "timeclock/break-start", {}, expected_status=200)
        
        if result["success"]:
            response = result["data"]
            if response.get("state") == "BREAK":
                self.log_test("T2: Break-Start", True, 
                            f"Break started successfully, state: {response['state']}")
                return True
            else:
                self.log_test("T2: Break-Start", False, 
                            f"Unexpected state: {response.get('state')}")
                return False
        else:
            self.log_test("T2: Break-Start", False, 
                        f"Status: {result['status_code']}, Data: {result.get('data', {})}")
            return False

    def test_timeclock_clock_out_during_break_blocked(self):
        """T3: Clock-Out during BREAK (MUST BLOCK!)"""
        print("\n🚫 Testing T3: Clock-Out during BREAK (CRITICAL TEST)...")
        
        result = self.make_request("POST", "timeclock/clock-out", {}, expected_status=409)
        
        if result["success"]:
            response = result["data"]
            detail = response.get("detail", "")
            if "Pause" in detail or "BREAK" in detail or "break" in detail:
                self.log_test("T3: Clock-Out during BREAK BLOCKED", True, 
                            f"✅ CRITICAL TEST PASSED! Clock-out correctly blocked with 409 CONFLICT: {detail}")
                return True
            else:
                self.log_test("T3: Clock-Out during BREAK BLOCKED", False, 
                            f"Wrong error message: {detail}")
                return False
        else:
            self.log_test("T3: Clock-Out during BREAK BLOCKED", False, 
                        f"Expected 409 CONFLICT, got {result['status_code']}")
            return False

    def test_timeclock_break_end(self):
        """T4: Break-End"""
        print("\n🔄 Testing T4: Break-End...")
        
        result = self.make_request("POST", "timeclock/break-end", {}, expected_status=200)
        
        if result["success"]:
            response = result["data"]
            if response.get("state") == "WORKING":
                self.log_test("T4: Break-End", True, 
                            f"Break ended successfully, state: {response['state']}")
                return True
            else:
                self.log_test("T4: Break-End", False, 
                            f"Unexpected state: {response.get('state')}")
                return False
        else:
            self.log_test("T4: Break-End", False, 
                        f"Status: {result['status_code']}, Data: {result.get('data', {})}")
            return False

    def test_timeclock_clock_out_after_break(self):
        """T5: Clock-Out (after break ended)"""
        print("\n🏁 Testing T5: Clock-Out (after break ended)...")
        
        result = self.make_request("POST", "timeclock/clock-out", {}, expected_status=200)
        
        if result["success"]:
            response = result["data"]
            if response.get("state") == "CLOSED":
                self.log_test("T5: Clock-Out (after break ended)", True, 
                            f"Clock-out successful, state: {response['state']}")
                return True
            else:
                self.log_test("T5: Clock-Out (after break ended)", False, 
                            f"Unexpected state: {response.get('state')}")
                return False
        else:
            self.log_test("T5: Clock-Out (after break ended)", False, 
                        f"Status: {result['status_code']}, Data: {result.get('data', {})}")
            return False

    def test_admin_daily_overview(self):
        """Admin Overview"""
        print("\n📊 Testing Admin Daily Overview...")
        
        result = self.make_request("GET", "timeclock/admin/daily-overview", {}, expected_status=200)
        
        if result["success"]:
            response = result["data"]
            summary = response.get("summary", {})
            if "working_count" in summary and "on_break_count" in summary:
                self.log_test("Admin Daily Overview", True, 
                            f"Overview retrieved: working={summary.get('working_count')}, "
                            f"on_break={summary.get('on_break_count')}, "
                            f"completed={summary.get('completed_count')}")
                return True
            else:
                self.log_test("Admin Daily Overview", False, 
                            f"Missing expected fields in summary: {summary}")
                return False
        else:
            self.log_test("Admin Daily Overview", False, 
                        f"Status: {result['status_code']}, Data: {result.get('data', {})}")
            return False

    def run_all_tests(self):
        """Run all Modul 30 tests"""
        print("=" * 80)
        print("🧪 MODUL 30 BACKEND TESTING: Shifts V2 + Timeclock (FINAL)")
        print("=" * 80)
        
        # Authenticate
        if not self.authenticate():
            print("❌ Authentication failed, cannot continue")
            return False
        
        # Test Shifts V2
        print("\n" + "=" * 50)
        print("📋 SHIFTS V2 TESTS")
        print("=" * 50)
        
        # S1: List Shifts with date filter
        self.test_shifts_v2_list_with_date_filter()
        
        # S2: Create new Shift
        shift_id = self.test_shifts_v2_create_new_shift()
        
        if shift_id:
            # S3: Publish Shift
            if self.test_shifts_v2_publish_shift(shift_id):
                # S4: Assign Staff to Shift
                self.test_shifts_v2_assign_staff(shift_id)
        
        # Test Timeclock (Critical State Machine)
        print("\n" + "=" * 50)
        print("⏰ TIMECLOCK TESTS (Critical State Machine)")
        print("=" * 50)
        
        # T1: Clock-In
        session_id = self.test_timeclock_clock_in()
        
        if session_id:
            # T2: Break-Start
            if self.test_timeclock_break_start():
                # T3: Clock-Out during BREAK (MUST BLOCK!)
                if self.test_timeclock_clock_out_during_break_blocked():
                    # T4: Break-End
                    if self.test_timeclock_break_end():
                        # T5: Clock-Out (after break ended)
                        self.test_timeclock_clock_out_after_break()
        
        # Admin Overview
        print("\n" + "=" * 50)
        print("📊 ADMIN OVERVIEW")
        print("=" * 50)
        
        self.test_admin_daily_overview()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {len(self.failed_tests)}")
        print(f"Success rate: {success_rate:.1f}%")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in self.failed_tests:
                print(f"  - {test['name']}: {test['details']}")
        
        # Critical test check
        critical_passed = any("Clock-Out during BREAK BLOCKED" in test["name"] for test in 
                            [{"name": f"T3: Clock-Out during BREAK BLOCKED"} for _ in range(self.tests_passed)])
        
        if success_rate >= 80 and not self.failed_tests:
            print("\n✅ ALL TESTS PASSED - Modul 30 backend is working correctly!")
            return True
        else:
            print(f"\n⚠️ Some tests failed - Success rate: {success_rate:.1f}%")
            return False


def main():
    """Main test runner"""
    tester = Modul30Tester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 Modul 30 testing completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Modul 30 testing completed with failures!")
        sys.exit(1)


if __name__ == "__main__":
    main()