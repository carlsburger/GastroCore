#!/usr/bin/env python3
"""
GastroCore Backend API Testing Suite
Tests authentication, RBAC, CRUD operations, and audit logging
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class GastroCoreAPITester:
    def __init__(self, base_url: str = "https://table-master-17.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.test_data = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        
        # Test credentials from requirements
        self.credentials = {
            "admin": {"email": "admin@gastrocore.de", "password": "Admin123!"},
            "schichtleiter": {"email": "schichtleiter@gastrocore.de", "password": "Schicht123!"},
            "mitarbeiter": {"email": "mitarbeiter@gastrocore.de", "password": "Mitarbeiter123!"}
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
                    token: str = None, expected_status: int = 200) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
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

    def create_temp_admin(self):
        """Create a temporary admin user for testing"""
        print("\n👑 Creating temporary admin user...")
        
        # Use schichtleiter token to try creating admin (this should fail, but let's see)
        # Actually, let's try to reset the admin password directly in the database
        
        # For now, let's skip admin-specific tests and focus on what we can test
        return False
        """Test seeding initial data"""
        print("\n🌱 Testing seed data creation...")
        
        result = self.make_request("POST", "seed", expected_status=200)
        
        if result["success"]:
            self.log_test("Seed data creation", True, "Test users and data created successfully")
            return True
        else:
            # Check if data already exists
            if result["status_code"] == 200 and "bereits vorhanden" in str(result.get("data", {})):
                self.log_test("Seed data creation", True, "Data already exists - OK")
                return True
            else:
                self.log_test("Seed data creation", False, f"Status: {result['status_code']}")
                return False

    def test_authentication(self):
        """Test authentication for all user roles"""
        print("\n🔐 Testing authentication...")
        
        auth_success = True
        
        for role, creds in self.credentials.items():
            result = self.make_request("POST", "auth/login", creds, expected_status=200)
            
            if result["success"] and "access_token" in result["data"]:
                self.tokens[role] = result["data"]["access_token"]
                user_data = result["data"]["user"]
                
                # Check must_change_password flag
                must_change = user_data.get("must_change_password", False)
                self.log_test(f"Login {role}", True, 
                            f"Token received, must_change_password: {must_change}")
                
                # Store user data for later tests
                self.test_data[f"{role}_user"] = user_data
                
            else:
                self.log_test(f"Login {role}", False, 
                            f"Status: {result['status_code']}, Data: {result.get('data', {})}")
                auth_success = False
        
        return auth_success

    def test_password_change_requirement(self):
        """Test that admin must change password on first login"""
        print("\n🔑 Testing password change requirement...")
        
        if "admin" not in self.tokens:
            self.log_test("Password change test", False, "Admin token not available")
            return False
        
        admin_user = self.test_data.get("admin_user", {})
        must_change = admin_user.get("must_change_password", False)
        
        if must_change:
            # Test password change
            change_data = {
                "current_password": "Admin123!",
                "new_password": "NewAdmin123!"
            }
            
            result = self.make_request("POST", "auth/change-password", 
                                     change_data, self.tokens["admin"], expected_status=200)
            
            if result["success"]:
                self.log_test("Password change", True, "Password changed successfully")
                
                # Update credentials for future tests
                self.credentials["admin"]["password"] = "NewAdmin123!"
                
                # Re-login to get new token
                login_result = self.make_request("POST", "auth/login", 
                                               self.credentials["admin"], expected_status=200)
                if login_result["success"]:
                    self.tokens["admin"] = login_result["data"]["access_token"]
                    self.log_test("Re-login after password change", True)
                    return True
                else:
                    self.log_test("Re-login after password change", False)
                    return False
            else:
                self.log_test("Password change", False, f"Status: {result['status_code']}")
                return False
        else:
            self.log_test("Password change requirement", True, "User doesn't need to change password")
            return True

    def test_rbac_access_control(self):
        """Test Role-Based Access Control"""
        print("\n🛡️ Testing RBAC access control...")
        
        rbac_success = True
        
        # Test admin-only endpoints
        admin_endpoints = [
            ("GET", "users", 200),
            ("GET", "audit-logs", 200),
        ]
        
        for method, endpoint, expected_status in admin_endpoints:
            # Test with admin token (should work)
            result = self.make_request(method, endpoint, token=self.tokens.get("admin"), 
                                     expected_status=expected_status)
            if result["success"]:
                self.log_test(f"Admin access to {endpoint}", True)
            else:
                self.log_test(f"Admin access to {endpoint}", False, f"Status: {result['status_code']}")
                rbac_success = False
            
            # Test with mitarbeiter token (should fail with 403)
            result = self.make_request(method, endpoint, token=self.tokens.get("mitarbeiter"), 
                                     expected_status=403)
            if result["success"]:
                self.log_test(f"Mitarbeiter blocked from {endpoint}", True, "403 Forbidden as expected")
            else:
                self.log_test(f"Mitarbeiter blocked from {endpoint}", False, 
                            f"Expected 403, got {result['status_code']}")
                rbac_success = False
        
        # Test schichtleiter access to reservations (should work)
        result = self.make_request("GET", "reservations", token=self.tokens.get("schichtleiter"), 
                                 expected_status=200)
        if result["success"]:
            self.log_test("Schichtleiter access to reservations", True)
        else:
            self.log_test("Schichtleiter access to reservations", False, f"Status: {result['status_code']}")
            rbac_success = False
        
        return rbac_success

    def test_areas_management(self):
        """Test areas CRUD operations (Admin only)"""
        print("\n🏢 Testing areas management...")
        
        if "admin" not in self.tokens:
            self.log_test("Areas management", False, "Admin token not available")
            return False
        
        areas_success = True
        
        # Create area
        area_data = {
            "name": "Test Terrasse",
            "description": "Test area for automated testing",
            "capacity": 25
        }
        
        result = self.make_request("POST", "areas", area_data, self.tokens["admin"], expected_status=200)
        if result["success"] and "id" in result["data"]:
            area_id = result["data"]["id"]
            self.test_data["test_area_id"] = area_id
            self.log_test("Create area", True, f"Area created with ID: {area_id}")
        else:
            self.log_test("Create area", False, f"Status: {result['status_code']}")
            areas_success = False
            return areas_success
        
        # Get areas
        result = self.make_request("GET", "areas", token=self.tokens["admin"], expected_status=200)
        if result["success"] and isinstance(result["data"], list):
            self.log_test("Get areas", True, f"Retrieved {len(result['data'])} areas")
        else:
            self.log_test("Get areas", False, f"Status: {result['status_code']}")
            areas_success = False
        
        # Update area
        update_data = {
            "name": "Updated Test Terrasse",
            "description": "Updated description",
            "capacity": 30
        }
        
        result = self.make_request("PUT", f"areas/{area_id}", update_data, 
                                 self.tokens["admin"], expected_status=200)
        if result["success"]:
            self.log_test("Update area", True)
        else:
            self.log_test("Update area", False, f"Status: {result['status_code']}")
            areas_success = False
        
        return areas_success

    def test_users_management(self):
        """Test users CRUD operations (Admin only)"""
        print("\n👥 Testing users management...")
        
        if "admin" not in self.tokens:
            self.log_test("Users management", False, "Admin token not available")
            return False
        
        users_success = True
        
        # Get users
        result = self.make_request("GET", "users", token=self.tokens["admin"], expected_status=200)
        if result["success"] and isinstance(result["data"], list):
            self.log_test("Get users", True, f"Retrieved {len(result['data'])} users")
        else:
            self.log_test("Get users", False, f"Status: {result['status_code']}")
            users_success = False
        
        # Create user
        user_data = {
            "name": "Test User",
            "email": "test@gastrocore.de",
            "password": "TestPass123!",
            "role": "mitarbeiter"
        }
        
        result = self.make_request("POST", "users", user_data, self.tokens["admin"], expected_status=200)
        if result["success"] and "id" in result["data"]:
            user_id = result["data"]["id"]
            self.test_data["test_user_id"] = user_id
            self.log_test("Create user", True, f"User created with ID: {user_id}")
        else:
            self.log_test("Create user", False, f"Status: {result['status_code']}")
            users_success = False
        
        return users_success

    def test_reservations_workflow(self):
        """Test reservations CRUD and status transitions"""
        print("\n📅 Testing reservations workflow...")
        
        if "schichtleiter" not in self.tokens:
            self.log_test("Reservations workflow", False, "Schichtleiter token not available")
            return False
        
        reservations_success = True
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Create reservation
        reservation_data = {
            "guest_name": "Test Familie Schmidt",
            "guest_phone": "+49 170 9876543",
            "guest_email": "schmidt@example.de",
            "party_size": 4,
            "date": today,
            "time": "19:30",
            "area_id": self.test_data.get("test_area_id"),
            "notes": "Test reservation for automated testing"
        }
        
        result = self.make_request("POST", "reservations", reservation_data, 
                                 self.tokens["schichtleiter"], expected_status=200)
        if result["success"] and "id" in result["data"]:
            reservation_id = result["data"]["id"]
            self.test_data["test_reservation_id"] = reservation_id
            self.log_test("Create reservation", True, f"Reservation created with ID: {reservation_id}")
        else:
            self.log_test("Create reservation", False, f"Status: {result['status_code']}")
            reservations_success = False
            return reservations_success
        
        # Get reservations
        result = self.make_request("GET", "reservations", {"date": today}, 
                                 self.tokens["schichtleiter"], expected_status=200)
        if result["success"] and isinstance(result["data"], list):
            self.log_test("Get reservations", True, f"Retrieved {len(result['data'])} reservations")
        else:
            self.log_test("Get reservations", False, f"Status: {result['status_code']}")
            reservations_success = False
        
        # Test status transitions: neu -> bestaetigt -> angekommen -> abgeschlossen
        status_transitions = ["bestaetigt", "angekommen", "abgeschlossen"]
        
        for new_status in status_transitions:
            # The status change endpoint expects the status as a query parameter
            result = self.make_request("PATCH", f"reservations/{reservation_id}/status?new_status={new_status}", 
                                     {}, self.tokens["schichtleiter"], 
                                     expected_status=200)
            if result["success"]:
                self.log_test(f"Status change to {new_status}", True)
            else:
                self.log_test(f"Status change to {new_status}", False, f"Status: {result['status_code']}")
                reservations_success = False
        
        # Test search functionality
        result = self.make_request("GET", "reservations", {"search": "Schmidt"}, 
                                 self.tokens["schichtleiter"], expected_status=200)
        if result["success"] and isinstance(result["data"], list):
            found_reservation = any(r["guest_name"] == "Test Familie Schmidt" for r in result["data"])
            if found_reservation:
                self.log_test("Search by guest name", True, "Found reservation by name")
            else:
                self.log_test("Search by guest name", False, "Reservation not found in search")
                reservations_success = False
        else:
            self.log_test("Search by guest name", False, f"Status: {result['status_code']}")
            reservations_success = False
        
        return reservations_success

    def test_no_show_functionality(self):
        """Test marking reservation as no-show"""
        print("\n❌ Testing no-show functionality...")
        
        if "schichtleiter" not in self.tokens or "test_reservation_id" not in self.test_data:
            self.log_test("No-show functionality", False, "Prerequisites not met")
            return False
        
        # Create another reservation for no-show test
        today = datetime.now().strftime("%Y-%m-%d")
        reservation_data = {
            "guest_name": "No Show Test",
            "guest_phone": "+49 170 1111111",
            "party_size": 2,
            "date": today,
            "time": "20:00"
        }
        
        result = self.make_request("POST", "reservations", reservation_data, 
                                 self.tokens["schichtleiter"], expected_status=200)
        if not result["success"]:
            self.log_test("Create no-show test reservation", False)
            return False
        
        no_show_reservation_id = result["data"]["id"]
        
        # Mark as no-show
        result = self.make_request("PATCH", f"reservations/{no_show_reservation_id}/status?new_status=no_show", 
                                 {}, self.tokens["schichtleiter"], 
                                 expected_status=200)
        if result["success"]:
            self.log_test("Mark reservation as no-show", True)
            return True
        else:
            self.log_test("Mark reservation as no-show", False, f"Status: {result['status_code']}")
            return False

    def test_audit_logging(self):
        """Test audit log functionality"""
        print("\n📋 Testing audit logging...")
        
        if "admin" not in self.tokens:
            self.log_test("Audit logging", False, "Admin token not available")
            return False
        
        # Get audit logs
        result = self.make_request("GET", "audit-logs", {"limit": 50}, 
                                 self.tokens["admin"], expected_status=200)
        if result["success"] and isinstance(result["data"], list):
            logs = result["data"]
            self.log_test("Get audit logs", True, f"Retrieved {len(logs)} audit log entries")
            
            # Check if our test actions are logged
            test_actions = ["create", "update", "status_change"]
            logged_actions = [log["action"] for log in logs]
            
            for action in test_actions:
                if action in logged_actions:
                    self.log_test(f"Audit log contains {action}", True)
                else:
                    self.log_test(f"Audit log contains {action}", False, "Action not found in logs")
            
            return True
        else:
            self.log_test("Get audit logs", False, f"Status: {result['status_code']}")
            return False

    def test_filtering_functionality(self):
        """Test filtering reservations by status, area, and date"""
        print("\n🔍 Testing filtering functionality...")
        
        if "schichtleiter" not in self.tokens:
            self.log_test("Filtering functionality", False, "Schichtleiter token not available")
            return False
        
        filtering_success = True
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Test date filter
        result = self.make_request("GET", "reservations", {"date": today}, 
                                 self.tokens["schichtleiter"], expected_status=200)
        if result["success"]:
            self.log_test("Filter by date", True, f"Retrieved reservations for {today}")
        else:
            self.log_test("Filter by date", False, f"Status: {result['status_code']}")
            filtering_success = False
        
        # Test status filter
        result = self.make_request("GET", "reservations", {"status": "neu"}, 
                                 self.tokens["schichtleiter"], expected_status=200)
        if result["success"]:
            self.log_test("Filter by status", True, "Retrieved reservations with status 'neu'")
        else:
            self.log_test("Filter by status", False, f"Status: {result['status_code']}")
            filtering_success = False
        
        # Test area filter (if we have a test area)
        if "test_area_id" in self.test_data:
            result = self.make_request("GET", "reservations", {"area_id": self.test_data["test_area_id"]}, 
                                     self.tokens["schichtleiter"], expected_status=200)
            if result["success"]:
                self.log_test("Filter by area", True, "Retrieved reservations for test area")
            else:
                self.log_test("Filter by area", False, f"Status: {result['status_code']}")
                filtering_success = False
        
        return filtering_success

    def cleanup_test_data(self):
        """Clean up test data created during testing"""
        print("\n🧹 Cleaning up test data...")
        
        cleanup_success = True
        
        # Archive test area
        if "test_area_id" in self.test_data and "admin" in self.tokens:
            result = self.make_request("DELETE", f"areas/{self.test_data['test_area_id']}", 
                                     token=self.tokens["admin"], expected_status=200)
            if result["success"]:
                self.log_test("Archive test area", True)
            else:
                self.log_test("Archive test area", False, f"Status: {result['status_code']}")
                cleanup_success = False
        
        # Archive test user
        if "test_user_id" in self.test_data and "admin" in self.tokens:
            result = self.make_request("DELETE", f"users/{self.test_data['test_user_id']}", 
                                     token=self.tokens["admin"], expected_status=200)
            if result["success"]:
                self.log_test("Archive test user", True)
            else:
                self.log_test("Archive test user", False, f"Status: {result['status_code']}")
                cleanup_success = False
        
        return cleanup_success

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting GastroCore Backend API Tests")
        print("=" * 50)
        
        # Test sequence
        test_results = []
        
        test_results.append(self.test_seed_data())
        test_results.append(self.test_authentication())
        test_results.append(self.test_password_change_requirement())
        test_results.append(self.test_rbac_access_control())
        test_results.append(self.test_areas_management())
        test_results.append(self.test_users_management())
        test_results.append(self.test_reservations_workflow())
        test_results.append(self.test_no_show_functionality())
        test_results.append(self.test_filtering_functionality())
        test_results.append(self.test_audit_logging())
        test_results.append(self.cleanup_test_data())
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        print(f"Total tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {len(self.failed_tests)}")
        print(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in self.failed_tests:
                print(f"  - {test['name']}: {test['details']}")
        
        return len(self.failed_tests) == 0

def main():
    """Main test execution"""
    tester = GastroCoreAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())