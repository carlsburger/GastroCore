#!/usr/bin/env python3
"""
Modul 30 V1.1 - Backend Testing: Abwesenheiten & Personalakte
Tests the new APIs for absences and documents as per review request.
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class Modul30V11Tester:
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
        
        self.tokens = {}
        self.test_data = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        
        # Credentials from review request
        self.credentials = {
            "admin": {"email": "admin@carlsburg.de", "password": "Carlsburg2025!"}
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

    def authenticate(self):
        """Authenticate admin user"""
        print(f"\n🔐 Authenticating admin user...")
        
        result = self.make_request("POST", "auth/login", self.credentials["admin"], expected_status=200)
        
        if result["success"] and "access_token" in result["data"]:
            self.tokens["admin"] = result["data"]["access_token"]
            user_data = result["data"]["user"]
            self.test_data["admin_user"] = user_data
            self.log_test("Admin authentication", True, f"User: {user_data.get('email')}")
            return True
        else:
            self.log_test("Admin authentication", False, f"Status: {result['status_code']}")
            return False

    def test_absences_employee_perspective(self):
        """TEST 1: ABWESENHEITEN (Mitarbeiter-Perspektive)"""
        print("\n📋 TEST 1: ABWESENHEITEN (Mitarbeiter-Perspektive)")
        
        if "admin" not in self.tokens:
            self.log_test("Employee Absences Tests", False, "Admin token not available")
            return False
        
        success = True
        
        # 1. Login als Admin (der ein staff_member_id hat)
        # Already done in authenticate()
        
        # 2. GET /api/staff/absences/me → Sollte leere Liste oder existierende Abwesenheiten zurückgeben
        result = self.make_request("GET", "staff/absences/me", token=self.tokens["admin"], expected_status=200)
        if result["success"]:
            absences_data = result["data"]
            if "data" in absences_data and isinstance(absences_data["data"], list):
                self.log_test("2. GET /api/staff/absences/me", True, 
                            f"Retrieved {len(absences_data['data'])} absences")
            else:
                self.log_test("2. GET /api/staff/absences/me", False, "Invalid response format")
                success = False
        else:
            self.log_test("2. GET /api/staff/absences/me", False, f"Status: {result['status_code']}")
            success = False
        
        # 3. POST /api/staff/absences mit Body
        vacation_data = {
            "type": "VACATION",
            "start_date": "2025-02-15",  # Changed to avoid conflicts
            "end_date": "2025-02-20",
            "notes_employee": "Familienurlaub"
        }
        
        result = self.make_request("POST", "staff/absences", vacation_data, 
                                 self.tokens["admin"], expected_status=200)
        if result["success"]:
            absence_response = result["data"]
            if (absence_response.get("data", {}).get("status") == "REQUESTED" and 
                absence_response.get("data", {}).get("days_count") == 6):
                self.log_test("3. POST /api/staff/absences", True, 
                            f"Status: {absence_response['data']['status']}, Days: {absence_response['data']['days_count']}")
                self.test_data["vacation_absence_id"] = absence_response["data"]["id"]
            else:
                self.log_test("3. POST /api/staff/absences", False, 
                            f"Expected status=REQUESTED, days_count=6. Got: {absence_response}")
                success = False
        else:
            self.log_test("3. POST /api/staff/absences", False, f"Status: {result['status_code']}")
            success = False
        
        # 4. GET /api/staff/absences/me → Sollte den neuen Antrag enthalten
        result = self.make_request("GET", "staff/absences/me", token=self.tokens["admin"], expected_status=200)
        if result["success"]:
            absences_data = result["data"]
            if "data" in absences_data and len(absences_data["data"]) > 0:
                found_vacation = any(a.get("type") == "VACATION" for a in absences_data["data"])
                if found_vacation:
                    self.log_test("4. GET /api/staff/absences/me (contains new request)", True)
                else:
                    self.log_test("4. GET /api/staff/absences/me (contains new request)", False, 
                                "New vacation request not found")
                    success = False
            else:
                self.log_test("4. GET /api/staff/absences/me (contains new request)", False, 
                            "No absences returned")
                success = False
        else:
            self.log_test("4. GET /api/staff/absences/me (contains new request)", False, 
                        f"Status: {result['status_code']}")
            success = False
        
        # 5. POST /api/staff/absences/{id}/cancel → Antrag stornieren
        if "vacation_absence_id" in self.test_data:
            result = self.make_request("POST", f"staff/absences/{self.test_data['vacation_absence_id']}/cancel", 
                                     {}, self.tokens["admin"], expected_status=200)
            if result["success"]:
                self.log_test("5. POST /api/staff/absences/{id}/cancel", True, "Status: CANCELLED")
            else:
                self.log_test("5. POST /api/staff/absences/{id}/cancel", False, 
                            f"Status: {result['status_code']}")
                success = False
        
        return success

    def test_absences_admin_perspective(self):
        """TEST 2: ABWESENHEITEN (Admin-Perspektive)"""
        print("\n👑 TEST 2: ABWESENHEITEN (Admin-Perspektive)")
        
        if "admin" not in self.tokens:
            self.log_test("Admin Absences Tests", False, "Admin token not available")
            return False
        
        success = True
        
        # 6. POST /api/staff/absences mit neuem Urlaubsantrag
        vacation_data = {
            "type": "VACATION",
            "start_date": "2025-01-15",
            "end_date": "2025-01-20",
            "notes_employee": "Test vacation for admin approval"
        }
        
        result = self.make_request("POST", "staff/absences", vacation_data, 
                                 self.tokens["admin"], expected_status=200)
        if result["success"]:
            self.test_data["admin_test_absence_id"] = result["data"]["data"]["id"]
            self.log_test("6. POST /api/staff/absences (new vacation request)", True)
        else:
            self.log_test("6. POST /api/staff/absences (new vacation request)", False, 
                        f"Status: {result['status_code']}")
            success = False
            return success
        
        # 7. GET /api/admin/absences → Liste aller Abwesenheiten
        result = self.make_request("GET", "admin/absences", token=self.tokens["admin"], expected_status=200)
        if result["success"]:
            absences_data = result["data"]
            if "data" in absences_data and isinstance(absences_data["data"], list):
                self.log_test("7. GET /api/admin/absences", True, 
                            f"Retrieved {len(absences_data['data'])} absences")
            else:
                self.log_test("7. GET /api/admin/absences", False, "Invalid response format")
                success = False
        else:
            self.log_test("7. GET /api/admin/absences", False, f"Status: {result['status_code']}")
            success = False
        
        # 8. GET /api/admin/absences/pending → Nur offene Anträge
        result = self.make_request("GET", "admin/absences/pending", token=self.tokens["admin"], expected_status=200)
        if result["success"]:
            pending_data = result["data"]
            if "data" in pending_data and isinstance(pending_data["data"], list):
                self.log_test("8. GET /api/admin/absences/pending", True, 
                            f"Retrieved {len(pending_data['data'])} pending absences")
            else:
                self.log_test("8. GET /api/admin/absences/pending", False, "Invalid response format")
                success = False
        else:
            self.log_test("8. GET /api/admin/absences/pending", False, f"Status: {result['status_code']}")
            success = False
        
        # 9. POST /api/admin/absences/{id}/approve → Genehmigen
        if "admin_test_absence_id" in self.test_data:
            result = self.make_request("POST", f"admin/absences/{self.test_data['admin_test_absence_id']}/approve", 
                                     {}, self.tokens["admin"], expected_status=200)
            if result["success"]:
                self.log_test("9. POST /api/admin/absences/{id}/approve", True, "Status: APPROVED")
            else:
                self.log_test("9. POST /api/admin/absences/{id}/approve", False, 
                            f"Status: {result['status_code']}")
                success = False
        
        # 10. GET /api/admin/absences/by-date/2025-01-15 → Sollte genehmigte Abwesenheit zeigen
        result = self.make_request("GET", "admin/absences/by-date/2025-01-15", 
                                 token=self.tokens["admin"], expected_status=200)
        if result["success"]:
            date_absences = result["data"]
            if "data" in date_absences:
                self.log_test("10. GET /api/admin/absences/by-date/2025-01-15", True, 
                            f"Found {len(date_absences['data'])} absences for date")
            else:
                self.log_test("10. GET /api/admin/absences/by-date/2025-01-15", False, 
                            "Invalid response format")
                success = False
        else:
            self.log_test("10. GET /api/admin/absences/by-date/2025-01-15", False, 
                        f"Status: {result['status_code']}")
            success = False
        
        return success

    def test_absences_rejection(self):
        """TEST 3: ABWESENHEITEN ABLEHNEN"""
        print("\n❌ TEST 3: ABWESENHEITEN ABLEHNEN")
        
        if "admin" not in self.tokens:
            self.log_test("Absence Rejection Tests", False, "Admin token not available")
            return False
        
        success = True
        
        # 11. POST /api/staff/absences mit neuem Antrag (type=SICK)
        sick_data = {
            "type": "SICK",
            "start_date": "2025-01-25",
            "end_date": "2025-01-25",
            "notes_employee": "Krank"
        }
        
        result = self.make_request("POST", "staff/absences", sick_data, 
                                 self.tokens["admin"], expected_status=200)
        if result["success"]:
            sick_absence_id = result["data"]["data"]["id"]
            self.log_test("11. POST /api/staff/absences (sick request)", True)
            
            # 12. POST /api/admin/absences/{id}/reject
            reject_data = {"notes_admin": "Nicht genehmigt - bitte AU einreichen"}
            result = self.make_request("POST", f"admin/absences/{sick_absence_id}/reject", 
                                     reject_data, self.tokens["admin"], expected_status=200)
            if result["success"]:
                self.log_test("12. POST /api/admin/absences/{id}/reject", True, "Status: REJECTED")
            else:
                self.log_test("12. POST /api/admin/absences/{id}/reject", False, 
                            f"Status: {result['status_code']}")
                success = False
        else:
            self.log_test("11. POST /api/staff/absences (sick request)", False, 
                        f"Status: {result['status_code']}")
            success = False
        
        return success

    def test_documents_admin_upload(self):
        """TEST 4: DOKUMENTE (Admin Upload)"""
        print("\n📄 TEST 4: DOKUMENTE (Admin Upload)")
        
        if "admin" not in self.tokens:
            self.log_test("Document Upload Tests", False, "Admin token not available")
            return False
        
        success = True
        
        # Get admin user's staff_member_id or use first available staff member
        admin_user = self.test_data.get("admin_user", {})
        staff_member_id = admin_user.get("staff_member_id")
        
        if not staff_member_id:
            # Try to get any staff member for testing
            result = self.make_request("GET", "staff/members", token=self.tokens["admin"], expected_status=200)
            if result["success"] and result["data"]:
                staff_member_id = result["data"][0]["id"]
                self.log_test("Using first staff member for document testing", True, f"ID: {staff_member_id}")
            else:
                self.log_test("Document Upload Tests", False, "No staff member available for testing")
                return False
        
        # 13. POST /api/admin/staff/{staff_member_id}/documents
        test_file_content = "Test document content for Arbeitsvertrag 2025"
        
        url = f"{self.base_url}/api/admin/staff/{staff_member_id}/documents"
        headers = {'Authorization': f'Bearer {self.tokens["admin"]}'}
        
        files = {
            'file': ('arbeitsvertrag.txt', test_file_content, 'text/plain')
        }
        data = {
            'title': 'Arbeitsvertrag 2025',
            'category': 'CONTRACT',
            'requires_acknowledgement': 'true'
        }
        
        try:
            response = requests.post(url, headers=headers, files=files, data=data)
            
            if response.status_code == 200:
                doc_response = response.json()
                if "data" in doc_response and doc_response["data"].get("version") == 1:
                    self.log_test("13. POST /api/admin/staff/{id}/documents", True, 
                                f"Document uploaded, version: {doc_response['data']['version']}")
                    self.test_data["test_document_id"] = doc_response["data"]["id"]
                    self.test_data["staff_member_id"] = staff_member_id
                else:
                    self.log_test("13. POST /api/admin/staff/{id}/documents", False, 
                                f"Unexpected response: {doc_response}")
                    success = False
            else:
                error_detail = ""
                try:
                    error_response = response.json()
                    error_detail = f" - {error_response.get('detail', 'Unknown error')}"
                except:
                    error_detail = f" - {response.text}"
                self.log_test("13. POST /api/admin/staff/{id}/documents", False, 
                            f"Status: {response.status_code}{error_detail}")
                success = False
        except Exception as e:
            self.log_test("13. POST /api/admin/staff/{id}/documents", False, f"Error: {str(e)}")
            success = False
        
        # 14. GET /api/admin/staff/{staff_member_id}/documents
        result = self.make_request("GET", f"admin/staff/{staff_member_id}/documents", 
                                 token=self.tokens["admin"], expected_status=200)
        if result["success"]:
            docs_data = result["data"]
            if "data" in docs_data and isinstance(docs_data["data"], list):
                self.log_test("14. GET /api/admin/staff/{id}/documents", True, 
                            f"Retrieved {len(docs_data['data'])} documents")
            else:
                self.log_test("14. GET /api/admin/staff/{id}/documents", False, "Invalid response format")
                success = False
        else:
            self.log_test("14. GET /api/admin/staff/{id}/documents", False, f"Status: {result['status_code']}")
            success = False
        
        return success

    def test_documents_employee_perspective(self):
        """TEST 5: DOKUMENTE (Mitarbeiter-Perspektive)"""
        print("\n👤 TEST 5: DOKUMENTE (Mitarbeiter-Perspektive)")
        
        if "admin" not in self.tokens:
            self.log_test("Employee Documents Tests", False, "Admin token not available")
            return False
        
        success = True
        
        # 15. GET /api/staff/documents/me → Eigene Dokumente
        result = self.make_request("GET", "staff/documents/me", token=self.tokens["admin"], expected_status=200)
        if result["success"]:
            my_docs = result["data"]
            if "data" in my_docs and isinstance(my_docs["data"], list):
                self.log_test("15. GET /api/staff/documents/me", True, 
                            f"Retrieved {len(my_docs['data'])} own documents")
            else:
                self.log_test("15. GET /api/staff/documents/me", False, "Invalid response format")
                success = False
        else:
            self.log_test("15. GET /api/staff/documents/me", False, f"Status: {result['status_code']}")
            success = False
        
        # 16. GET /api/staff/documents/me/unacknowledged-count
        result = self.make_request("GET", "staff/documents/me/unacknowledged-count", 
                                 token=self.tokens["admin"], expected_status=200)
        if result["success"]:
            count_data = result["data"]
            if "count" in count_data:
                unack_count = count_data["count"]
                self.log_test("16. GET /api/staff/documents/me/unacknowledged-count", True, 
                            f"Unacknowledged count: {unack_count} (should be 1)")
                
                # 17. POST /api/staff/documents/{document_id}/acknowledge
                if "test_document_id" in self.test_data and unack_count > 0:
                    result = self.make_request("POST", f"staff/documents/{self.test_data['test_document_id']}/acknowledge", 
                                             {}, self.tokens["admin"], expected_status=200)
                    if result["success"]:
                        self.log_test("17. POST /api/staff/documents/{id}/acknowledge", True, 
                                    "Document acknowledged")
                        
                        # 18. Check count again - should be 0 now
                        result = self.make_request("GET", "staff/documents/me/unacknowledged-count", 
                                                 token=self.tokens["admin"], expected_status=200)
                        if result["success"] and result["data"].get("count") == 0:
                            self.log_test("18. Unacknowledged count after acknowledgement", True, "Count is now 0")
                        else:
                            self.log_test("18. Unacknowledged count after acknowledgement", False, 
                                        f"Expected 0, got {result['data'].get('count')}")
                            success = False
                    else:
                        self.log_test("17. POST /api/staff/documents/{id}/acknowledge", False, 
                                    f"Status: {result['status_code']}")
                        success = False
            else:
                self.log_test("16. GET /api/staff/documents/me/unacknowledged-count", False, 
                            "Invalid response format")
                success = False
        else:
            self.log_test("16. GET /api/staff/documents/me/unacknowledged-count", False, 
                        f"Status: {result['status_code']}")
            success = False
        
        return success

    def test_daily_overview_with_absences(self):
        """TEST 6: TAGESÜBERSICHT MIT ABWESENHEITEN"""
        print("\n📊 TEST 6: TAGESÜBERSICHT MIT ABWESENHEITEN")
        
        if "admin" not in self.tokens:
            self.log_test("Daily Overview with Absences", False, "Admin token not available")
            return False
        
        # 19. GET /api/timeclock/admin/daily-overview?day_key=2025-01-15
        result = self.make_request("GET", "timeclock/admin/daily-overview", 
                                 {"day_key": "2025-01-15"}, self.tokens["admin"], expected_status=200)
        
        if result["success"]:
            overview_data = result["data"]
            
            # Check if response contains absent array and absent_count in summary
            has_absent_array = "absent" in overview_data
            has_absent_count = "summary" in overview_data and "absent_count" in overview_data["summary"]
            
            if has_absent_array and has_absent_count:
                absent_count = overview_data["summary"]["absent_count"]
                absent_list = overview_data["absent"]
                self.log_test("19. GET /api/timeclock/admin/daily-overview (with absences)", True, 
                            f"Contains absent array ({len(absent_list)} entries) and absent_count ({absent_count})")
                return True
            else:
                self.log_test("19. GET /api/timeclock/admin/daily-overview (with absences)", False, 
                            f"Missing absent array or absent_count. Has absent: {has_absent_array}, Has count: {has_absent_count}")
                return False
        else:
            self.log_test("19. GET /api/timeclock/admin/daily-overview (with absences)", False, 
                        f"Status: {result['status_code']}")
            return False

    def run_all_tests(self):
        """Run all Modul 30 V1.1 tests"""
        print(f"\n🚀 MODUL 30 V1.1 - Backend Testing: Abwesenheiten & Personalakte")
        print(f"🎯 Target: {self.base_url}")
        print("=" * 80)
        
        # Authenticate
        if not self.authenticate():
            print("❌ Authentication failed. Cannot proceed with tests.")
            return False
        
        # Run all test suites
        test_results = []
        
        test_results.append(self.test_absences_employee_perspective())
        test_results.append(self.test_absences_admin_perspective())
        test_results.append(self.test_absences_rejection())
        test_results.append(self.test_documents_admin_upload())
        test_results.append(self.test_documents_employee_perspective())
        test_results.append(self.test_daily_overview_with_absences())
        
        # Summary
        print("\n" + "=" * 80)
        print(f"🏁 TESTING COMPLETE")
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
    tester = Modul30V11Tester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)