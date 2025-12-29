#!/usr/bin/env python3
"""
GastroCore FULL QA AUDIT Sprint 1-7
Re-test nach Bug-Fixes - Vollständiger QA Audit Sprint 1-7
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class GastroCoreFullQAAudit:
    def __init__(self, base_url: str = "https://systemcheck.preview.emergentagent.com"):
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

    def test_sprint1_auth_rbac(self):
        """Sprint 1: AUTH & RBAC - Complete Test Suite"""
        print("\n🔐 SPRINT 1: AUTH & RBAC")
        print("-" * 50)
        
        sprint1_success = True
        
        # 1. POST /api/auth/login mit Admin - MUSS jetzt funktionieren
        result = self.make_request("POST", "auth/login", self.credentials["admin"], expected_status=200)
        if result["success"] and "access_token" in result["data"]:
            self.tokens["admin"] = result["data"]["access_token"]
            self.log_test("POST /api/auth/login (Admin)", True, "Admin login successful")
        else:
            self.log_test("POST /api/auth/login (Admin)", False, f"Status: {result['status_code']}")
            sprint1_success = False
        
        # 2. POST /api/auth/login mit Schichtleiter
        result = self.make_request("POST", "auth/login", self.credentials["schichtleiter"], expected_status=200)
        if result["success"] and "access_token" in result["data"]:
            self.tokens["schichtleiter"] = result["data"]["access_token"]
            self.log_test("POST /api/auth/login (Schichtleiter)", True)
        else:
            self.log_test("POST /api/auth/login (Schichtleiter)", False, f"Status: {result['status_code']}")
            sprint1_success = False
        
        # 3. POST /api/auth/login mit Mitarbeiter
        result = self.make_request("POST", "auth/login", self.credentials["mitarbeiter"], expected_status=200)
        if result["success"] and "access_token" in result["data"]:
            self.tokens["mitarbeiter"] = result["data"]["access_token"]
            self.log_test("POST /api/auth/login (Mitarbeiter)", True)
        else:
            self.log_test("POST /api/auth/login (Mitarbeiter)", False, f"Status: {result['status_code']}")
            sprint1_success = False
        
        # 4. GET /api/auth/me
        if "admin" in self.tokens:
            result = self.make_request("GET", "auth/me", token=self.tokens["admin"], expected_status=200)
            if result["success"]:
                user_data = result["data"]
                if user_data.get("role") == "admin":
                    self.log_test("GET /api/auth/me", True, f"Role: {user_data.get('role')}")
                else:
                    self.log_test("GET /api/auth/me", False, f"Unexpected role: {user_data.get('role')}")
                    sprint1_success = False
            else:
                self.log_test("GET /api/auth/me", False, f"Status: {result['status_code']}")
                sprint1_success = False
        
        # 5. RBAC: Mitarbeiter darf NICHT auf /api/reservations zugreifen
        if "mitarbeiter" in self.tokens:
            result = self.make_request("GET", "reservations", token=self.tokens["mitarbeiter"], expected_status=403)
            if result["success"]:
                self.log_test("RBAC: Mitarbeiter blocked from /api/reservations", True, "403 Forbidden as expected")
            else:
                self.log_test("RBAC: Mitarbeiter blocked from /api/reservations", False, f"Expected 403, got {result['status_code']}")
                sprint1_success = False
        
        return sprint1_success

    def test_sprint2_reservations(self):
        """Sprint 2: RESERVIERUNGEN - Complete Test Suite"""
        print("\n📅 SPRINT 2: RESERVIERUNGEN")
        print("-" * 50)
        
        sprint2_success = True
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 1. GET /api/reservations (Admin/Schichtleiter)
        if "schichtleiter" in self.tokens:
            result = self.make_request("GET", "reservations", token=self.tokens["schichtleiter"], expected_status=200)
            if result["success"]:
                reservations = result["data"]
                self.log_test("GET /api/reservations (Schichtleiter)", True, f"Retrieved {len(reservations)} reservations")
            else:
                self.log_test("GET /api/reservations (Schichtleiter)", False, f"Status: {result['status_code']}")
                sprint2_success = False
        
        # 2. POST /api/reservations
        if "schichtleiter" in self.tokens:
            reservation_data = {
                "guest_name": "QA Test Familie",
                "guest_phone": "+49 170 1234567",
                "guest_email": "qatest@example.de",
                "party_size": 4,
                "date": today,
                "time": "19:00",
                "notes": "QA Audit Test Reservation"
            }
            
            result = self.make_request("POST", "reservations", reservation_data, 
                                     self.tokens["schichtleiter"], expected_status=200)
            if result["success"] and "id" in result["data"]:
                reservation_id = result["data"]["id"]
                self.test_data["qa_reservation_id"] = reservation_id
                self.log_test("POST /api/reservations", True, f"Created reservation ID: {reservation_id}")
            else:
                self.log_test("POST /api/reservations", False, f"Status: {result['status_code']}")
                sprint2_success = False
        
        # 3. PATCH /api/reservations/{id}/status (neu → bestaetigt → angekommen → abgeschlossen)
        if "qa_reservation_id" in self.test_data and "schichtleiter" in self.tokens:
            reservation_id = self.test_data["qa_reservation_id"]
            
            # neu → bestaetigt
            result = self.make_request("PATCH", f"reservations/{reservation_id}/status?new_status=bestaetigt", 
                                     {}, self.tokens["schichtleiter"], expected_status=200)
            if result["success"]:
                self.log_test("Status: neu → bestaetigt", True)
            else:
                self.log_test("Status: neu → bestaetigt", False, f"Status: {result['status_code']}")
                sprint2_success = False
            
            # bestaetigt → angekommen
            result = self.make_request("PATCH", f"reservations/{reservation_id}/status?new_status=angekommen", 
                                     {}, self.tokens["schichtleiter"], expected_status=200)
            if result["success"]:
                self.log_test("Status: bestaetigt → angekommen", True)
            else:
                self.log_test("Status: bestaetigt → angekommen", False, f"Status: {result['status_code']}")
                sprint2_success = False
            
            # angekommen → abgeschlossen
            result = self.make_request("PATCH", f"reservations/{reservation_id}/status?new_status=abgeschlossen", 
                                     {}, self.tokens["schichtleiter"], expected_status=200)
            if result["success"]:
                self.log_test("Status: angekommen → abgeschlossen", True)
            else:
                self.log_test("Status: angekommen → abgeschlossen", False, f"Status: {result['status_code']}")
                sprint2_success = False
        
        # 4. Walk-ins: POST /api/walk-ins
        if "schichtleiter" in self.tokens:
            walk_in_data = {
                "guest_name": "QA Walk-In Test",
                "guest_phone": "+49 170 9999999",
                "party_size": 2,
                "notes": "QA Audit Walk-In Test"
            }
            
            result = self.make_request("POST", "walk-ins", walk_in_data, 
                                     self.tokens["schichtleiter"], expected_status=200)
            if result["success"]:
                walk_in = result["data"]
                if walk_in.get("status") == "angekommen":
                    self.log_test("POST /api/walk-ins", True, "Walk-in created with status 'angekommen'")
                else:
                    self.log_test("POST /api/walk-ins", False, f"Expected status 'angekommen', got {walk_in.get('status')}")
                    sprint2_success = False
            else:
                self.log_test("POST /api/walk-ins", False, f"Status: {result['status_code']}")
                sprint2_success = False
        
        return sprint2_success

    def test_sprint3_public_booking(self):
        """Sprint 3: PUBLIC BOOKING - Complete Test Suite"""
        print("\n🌐 SPRINT 3: PUBLIC BOOKING")
        print("-" * 50)
        
        sprint3_success = True
        test_date = "2025-12-25"
        
        # 1. POST /api/public/book
        booking_data = {
            "guest_name": "QA Public Test",
            "guest_phone": "+49 170 5555555",
            "guest_email": "qapublic@example.de",
            "party_size": 2,
            "date": test_date,
            "time": "18:00",
            "occasion": "QA Test",
            "notes": "QA Audit Public Booking Test",
            "language": "de"
        }
        
        result = self.make_request("POST", "public/book", booking_data, expected_status=200)
        if result["success"]:
            booking_response = result["data"]
            if booking_response.get("success"):
                if booking_response.get("waitlist"):
                    self.log_test("POST /api/public/book", True, "Added to waitlist (restaurant full)")
                    self.test_data["public_waitlist_id"] = booking_response.get("waitlist_id")
                else:
                    self.log_test("POST /api/public/book", True, "Reservation created")
                    self.test_data["public_reservation_id"] = booking_response.get("reservation_id")
            else:
                self.log_test("POST /api/public/book", False, f"Booking failed: {booking_response}")
                sprint3_success = False
        else:
            self.log_test("POST /api/public/book", False, f"Status: {result['status_code']}")
            sprint3_success = False
        
        # 2. GET /api/public/availability?date=2025-12-25&party_size=2
        availability_params = {"date": test_date, "party_size": 2}
        result = self.make_request("GET", "public/availability", availability_params, expected_status=200)
        if result["success"]:
            availability = result["data"]
            if "available" in availability and "slots" in availability:
                self.log_test("GET /api/public/availability", True, 
                            f"Available: {availability.get('available')}, Slots: {len(availability.get('slots', []))}")
            else:
                self.log_test("GET /api/public/availability", False, "Missing required fields")
                sprint3_success = False
        else:
            self.log_test("GET /api/public/availability", False, f"Status: {result['status_code']}")
            sprint3_success = False
        
        return sprint3_success

    def test_sprint4_waitlist(self):
        """Sprint 4: WAITLIST - Complete Test Suite"""
        print("\n📋 SPRINT 4: WAITLIST")
        print("-" * 50)
        
        sprint4_success = True
        
        # 1. GET /api/waitlist
        if "schichtleiter" in self.tokens:
            result = self.make_request("GET", "waitlist", token=self.tokens["schichtleiter"], expected_status=200)
            if result["success"]:
                waitlist = result["data"]
                self.log_test("GET /api/waitlist", True, f"Retrieved {len(waitlist)} waitlist entries")
            else:
                self.log_test("GET /api/waitlist", False, f"Status: {result['status_code']}")
                sprint4_success = False
        
        # 2. POST /api/waitlist
        if "schichtleiter" in self.tokens:
            waitlist_data = {
                "guest_name": "QA Waitlist Test",
                "guest_phone": "+49 170 7777777",
                "guest_email": "qawaitlist@example.de",
                "party_size": 4,
                "date": "2025-12-25",
                "preferred_time": "18:30",
                "priority": 3,
                "notes": "QA Audit Waitlist Test",
                "language": "de"
            }
            
            result = self.make_request("POST", "waitlist", waitlist_data, 
                                     self.tokens["schichtleiter"], expected_status=200)
            if result["success"] and "id" in result["data"]:
                waitlist_id = result["data"]["id"]
                self.test_data["qa_waitlist_id"] = waitlist_id
                self.log_test("POST /api/waitlist", True, f"Created waitlist entry ID: {waitlist_id}")
            else:
                self.log_test("POST /api/waitlist", False, f"Status: {result['status_code']}")
                sprint4_success = False
        
        # 3. POST /api/waitlist/{id}/convert?time=18:30 - MUSS jetzt funktionieren
        if "qa_waitlist_id" in self.test_data and "schichtleiter" in self.tokens:
            waitlist_id = self.test_data["qa_waitlist_id"]
            
            result = self.make_request("POST", f"waitlist/{waitlist_id}/convert?time=18:30", 
                                     {}, self.tokens["schichtleiter"], expected_status=200)
            if result["success"]:
                converted_reservation = result["data"]
                if "id" in converted_reservation:
                    self.log_test("POST /api/waitlist/{id}/convert", True, 
                                f"Converted to reservation ID: {converted_reservation['id']}")
                else:
                    self.log_test("POST /api/waitlist/{id}/convert", False, "No reservation ID returned")
                    sprint4_success = False
            else:
                self.log_test("POST /api/waitlist/{id}/convert", False, f"Status: {result['status_code']}")
                sprint4_success = False
        
        return sprint4_success

    def test_sprint5_guest_management(self):
        """Sprint 5: GUEST MANAGEMENT - Complete Test Suite"""
        print("\n👥 SPRINT 5: GUEST MANAGEMENT")
        print("-" * 50)
        
        sprint5_success = True
        
        # 1. GET /api/guests?search=%2B49 - MUSS jetzt funktionieren (escaped +)
        if "schichtleiter" in self.tokens:
            # Test with + character that was previously causing regex errors
            result = self.make_request("GET", "guests", {"search": "+49"}, 
                                     self.tokens["schichtleiter"], expected_status=200)
            if result["success"]:
                guests = result["data"]
                self.log_test("GET /api/guests?search=+49", True, f"Search with + character successful, found {len(guests)} guests")
            else:
                self.log_test("GET /api/guests?search=+49", False, f"Status: {result['status_code']}")
                sprint5_success = False
        
        # 2. POST /api/guests
        if "schichtleiter" in self.tokens:
            guest_data = {
                "phone": "+49 170 8888888",
                "email": "qaguest@example.de",
                "name": "QA Test Guest",
                "flag": "none",
                "no_show_count": 0,
                "notes": "QA Audit Test Guest"
            }
            
            result = self.make_request("POST", "guests", guest_data, 
                                     self.tokens["schichtleiter"], expected_status=200)
            if result["success"] and "id" in result["data"]:
                guest_id = result["data"]["id"]
                self.test_data["qa_guest_id"] = guest_id
                self.log_test("POST /api/guests", True, f"Created guest ID: {guest_id}")
            else:
                # Guest might already exist
                if result["status_code"] == 409:
                    self.log_test("POST /api/guests", True, "Guest already exists (409 Conflict)")
                else:
                    self.log_test("POST /api/guests", False, f"Status: {result['status_code']}")
                    sprint5_success = False
        
        # 3. PATCH /api/guests/{id} - Flag setzen
        if "qa_guest_id" in self.test_data and "schichtleiter" in self.tokens:
            guest_id = self.test_data["qa_guest_id"]
            update_data = {"flag": "greylist", "notes": "QA Test - marked as greylist"}
            
            result = self.make_request("PATCH", f"guests/{guest_id}", update_data, 
                                     self.tokens["schichtleiter"], expected_status=200)
            if result["success"]:
                updated_guest = result["data"]
                if updated_guest.get("flag") == "greylist":
                    self.log_test("PATCH /api/guests/{id} (flag)", True, "Flag updated to greylist")
                else:
                    self.log_test("PATCH /api/guests/{id} (flag)", False, f"Flag not updated correctly: {updated_guest.get('flag')}")
                    sprint5_success = False
            else:
                self.log_test("PATCH /api/guests/{id} (flag)", False, f"Status: {result['status_code']}")
                sprint5_success = False
        
        return sprint5_success

    def test_sprint6_payments(self):
        """Sprint 6: PAYMENTS - Complete Test Suite"""
        print("\n💰 SPRINT 6: PAYMENTS")
        print("-" * 50)
        
        sprint6_success = True
        
        # 1. GET /api/payments/rules
        if "admin" in self.tokens:
            result = self.make_request("GET", "payments/rules", token=self.tokens["admin"], expected_status=200)
            if result["success"]:
                rules = result["data"]
                self.log_test("GET /api/payments/rules", True, f"Retrieved {len(rules)} payment rules")
            else:
                self.log_test("GET /api/payments/rules", False, f"Status: {result['status_code']}")
                sprint6_success = False
        
        # 2. POST /api/payments/rules
        if "admin" in self.tokens:
            rule_data = {
                "name": "QA Test Payment Rule",
                "entity_type": "reservation",
                "min_party_size": 8,
                "amount": 50.00,
                "currency": "EUR",
                "is_active": True,
                "description": "QA Audit Test Payment Rule"
            }
            
            result = self.make_request("POST", "payments/rules", rule_data, 
                                     self.tokens["admin"], expected_status=200)
            if result["success"] and "id" in result["data"]:
                rule_id = result["data"]["id"]
                self.test_data["qa_payment_rule_id"] = rule_id
                self.log_test("POST /api/payments/rules", True, f"Created payment rule ID: {rule_id}")
            else:
                self.log_test("POST /api/payments/rules", False, f"Status: {result['status_code']}")
                sprint6_success = False
        
        # 3. GET /api/payments/check-required?entity_type=reservation&entity_id=XXX&party_size=10
        if "qa_reservation_id" in self.test_data and "schichtleiter" in self.tokens:
            reservation_id = self.test_data["qa_reservation_id"]
            check_params = {
                "entity_type": "reservation",
                "entity_id": reservation_id,
                "party_size": 10
            }
            
            result = self.make_request("GET", "payments/check-required", check_params, 
                                     self.tokens["schichtleiter"], expected_status=200)
            if result["success"]:
                payment_check = result["data"]
                if "required" in payment_check:
                    self.log_test("GET /api/payments/check-required", True, 
                                f"Payment required: {payment_check.get('required')}")
                else:
                    self.log_test("GET /api/payments/check-required", False, "Missing 'required' field")
                    sprint6_success = False
            else:
                self.log_test("GET /api/payments/check-required", False, f"Status: {result['status_code']}")
                sprint6_success = False
        
        # 4. GET /api/payments/transactions
        if "admin" in self.tokens:
            result = self.make_request("GET", "payments/transactions", token=self.tokens["admin"], expected_status=200)
            if result["success"]:
                transactions = result["data"]
                self.log_test("GET /api/payments/transactions", True, f"Retrieved {len(transactions)} transactions")
            else:
                self.log_test("GET /api/payments/transactions", False, f"Status: {result['status_code']}")
                sprint6_success = False
        
        # 5. GET /api/payments/logs
        if "admin" in self.tokens:
            result = self.make_request("GET", "payments/logs", token=self.tokens["admin"], expected_status=200)
            if result["success"]:
                logs = result["data"]
                self.log_test("GET /api/payments/logs", True, f"Retrieved {len(logs)} payment logs")
            else:
                self.log_test("GET /api/payments/logs", False, f"Status: {result['status_code']}")
                sprint6_success = False
        
        return sprint6_success

    def test_sprint7_staff_dienstplan(self):
        """Sprint 7: STAFF & DIENSTPLAN - Complete Test Suite"""
        print("\n👥 SPRINT 7: STAFF & DIENSTPLAN")
        print("-" * 50)
        
        sprint7_success = True
        
        # 1. GET /api/staff/work-areas
        if "admin" in self.tokens:
            result = self.make_request("GET", "staff/work-areas", token=self.tokens["admin"], expected_status=200)
            if result["success"]:
                work_areas = result["data"]
                self.log_test("GET /api/staff/work-areas", True, f"Retrieved {len(work_areas)} work areas")
            else:
                self.log_test("GET /api/staff/work-areas", False, f"Status: {result['status_code']}")
                sprint7_success = False
        
        # 2. GET /api/staff/members
        if "admin" in self.tokens:
            result = self.make_request("GET", "staff/members", token=self.tokens["admin"], expected_status=200)
            if result["success"]:
                members = result["data"]
                self.log_test("GET /api/staff/members", True, f"Retrieved {len(members)} staff members")
            else:
                self.log_test("GET /api/staff/members", False, f"Status: {result['status_code']}")
                sprint7_success = False
        
        # 3. POST /api/staff/schedules
        if "admin" in self.tokens:
            schedule_data = {
                "staff_member_id": "test-staff-id",
                "date": "2025-12-25",
                "shift_start": "09:00",
                "shift_end": "17:00",
                "work_area": "kitchen",
                "notes": "QA Audit Test Schedule"
            }
            
            result = self.make_request("POST", "staff/schedules", schedule_data, 
                                     self.tokens["admin"], expected_status=200)
            if result["success"]:
                schedule = result["data"]
                self.log_test("POST /api/staff/schedules", True, f"Created schedule ID: {schedule.get('id')}")
            else:
                self.log_test("POST /api/staff/schedules", False, f"Status: {result['status_code']}")
                sprint7_success = False
        
        # 4. GET /api/staff/hours-overview
        if "admin" in self.tokens:
            result = self.make_request("GET", "staff/hours-overview", token=self.tokens["admin"], expected_status=200)
            if result["success"]:
                overview = result["data"]
                self.log_test("GET /api/staff/hours-overview", True, "Hours overview retrieved")
            else:
                self.log_test("GET /api/staff/hours-overview", False, f"Status: {result['status_code']}")
                sprint7_success = False
        
        return sprint7_success

    def test_sprint8_steuerburo(self):
        """Sprint 8: STEUERBÜRO - Complete Test Suite"""
        print("\n🏛️ SPRINT 8: STEUERBÜRO")
        print("-" * 50)
        
        sprint8_success = True
        
        # 1. GET /api/taxoffice/settings
        if "admin" in self.tokens:
            result = self.make_request("GET", "taxoffice/settings", token=self.tokens["admin"], expected_status=200)
            if result["success"]:
                settings = result["data"]
                self.log_test("GET /api/taxoffice/settings", True, f"Retrieved tax office settings with {len(settings)} fields")
            else:
                self.log_test("GET /api/taxoffice/settings", False, f"Status: {result['status_code']}")
                sprint8_success = False
        
        # 2. POST /api/taxoffice/jobs (export_type: monthly_hours)
        if "admin" in self.tokens:
            job_data = {
                "export_type": "monthly_hours",
                "year": 2025,
                "month": 12,
                "description": "QA Audit Monthly Hours Export"
            }
            
            result = self.make_request("POST", "taxoffice/jobs", job_data, 
                                     self.tokens["admin"], expected_status=200)
            if result["success"] and "id" in result["data"]:
                job_id = result["data"]["id"]
                self.test_data["qa_tax_job_id"] = job_id
                self.log_test("POST /api/taxoffice/jobs (monthly_hours)", True, f"Created job ID: {job_id}")
            else:
                self.log_test("POST /api/taxoffice/jobs (monthly_hours)", False, f"Status: {result['status_code']}")
                sprint8_success = False
        
        # 3. GET /api/taxoffice/jobs/{id}/download/0
        if "qa_tax_job_id" in self.test_data and "admin" in self.tokens:
            job_id = self.test_data["qa_tax_job_id"]
            
            # First check if job is ready
            result = self.make_request("GET", f"taxoffice/jobs/{job_id}", 
                                     token=self.tokens["admin"], expected_status=200)
            if result["success"]:
                job_status = result["data"].get("status")
                if job_status == "ready":
                    # Try to download
                    url = f"{self.base_url}/api/taxoffice/jobs/{job_id}/download/0"
                    headers = {'Authorization': f'Bearer {self.tokens["admin"]}'}
                    
                    try:
                        response = requests.get(url, headers=headers)
                        if response.status_code == 200:
                            self.log_test("GET /api/taxoffice/jobs/{id}/download/0", True, 
                                        f"Downloaded file, size: {len(response.content)} bytes")
                        else:
                            self.log_test("GET /api/taxoffice/jobs/{id}/download/0", False, 
                                        f"Download failed: {response.status_code}")
                            sprint8_success = False
                    except Exception as e:
                        self.log_test("GET /api/taxoffice/jobs/{id}/download/0", False, f"Error: {str(e)}")
                        sprint8_success = False
                else:
                    self.log_test("GET /api/taxoffice/jobs/{id}/download/0", False, f"Job not ready, status: {job_status}")
                    sprint8_success = False
            else:
                self.log_test("GET /api/taxoffice/jobs/{id}/download/0", False, f"Job check failed: {result['status_code']}")
                sprint8_success = False
        
        return sprint8_success

    def test_sprint9_loyalty(self):
        """Sprint 9: LOYALTY - Complete Test Suite"""
        print("\n🎁 SPRINT 9: LOYALTY")
        print("-" * 50)
        
        sprint9_success = True
        
        # 1. POST /api/customer/request-otp (ohne Auth)
        otp_data = {
            "phone": "+49 170 1111111",
            "language": "de"
        }
        
        result = self.make_request("POST", "customer/request-otp", otp_data, expected_status=200)
        if result["success"]:
            otp_response = result["data"]
            if "message" in otp_response:
                self.log_test("POST /api/customer/request-otp", True, "OTP request successful")
            else:
                self.log_test("POST /api/customer/request-otp", False, "Missing message in response")
                sprint9_success = False
        else:
            self.log_test("POST /api/customer/request-otp", False, f"Status: {result['status_code']}")
            sprint9_success = False
        
        # 2. GET /api/loyalty/settings (Admin)
        if "admin" in self.tokens:
            result = self.make_request("GET", "loyalty/settings", token=self.tokens["admin"], expected_status=200)
            if result["success"]:
                settings = result["data"]
                self.log_test("GET /api/loyalty/settings", True, f"Retrieved loyalty settings with {len(settings)} fields")
            else:
                self.log_test("GET /api/loyalty/settings", False, f"Status: {result['status_code']}")
                sprint9_success = False
        
        # 3. GET /api/loyalty/rewards
        if "admin" in self.tokens:
            result = self.make_request("GET", "loyalty/rewards", token=self.tokens["admin"], expected_status=200)
            if result["success"]:
                rewards = result["data"]
                self.log_test("GET /api/loyalty/rewards", True, f"Retrieved {len(rewards)} loyalty rewards")
            else:
                self.log_test("GET /api/loyalty/rewards", False, f"Status: {result['status_code']}")
                sprint9_success = False
        
        return sprint9_success

    def test_audit_logs(self):
        """AUDIT LOGS - Complete Test Suite"""
        print("\n📋 AUDIT LOGS")
        print("-" * 50)
        
        audit_success = True
        
        # GET /api/audit-logs (Admin only)
        if "admin" in self.tokens:
            result = self.make_request("GET", "audit-logs", {"limit": 100}, 
                                     self.tokens["admin"], expected_status=200)
            if result["success"]:
                logs = result["data"]
                self.log_test("GET /api/audit-logs", True, f"Retrieved {len(logs)} audit log entries")
                
                # Check for status change logs
                status_change_logs = [log for log in logs if log.get("action") == "status_change"]
                if status_change_logs:
                    self.log_test("Audit Logs: Status changes logged", True, 
                                f"Found {len(status_change_logs)} status change entries")
                else:
                    self.log_test("Audit Logs: Status changes logged", False, "No status change entries found")
                    audit_success = False
            else:
                self.log_test("GET /api/audit-logs", False, f"Status: {result['status_code']}")
                audit_success = False
        
        return audit_success

    def run_full_qa_audit(self):
        """Run complete QA audit for all sprints"""
        print("🚀 FULL QA AUDIT Sprint 1-7 - GastroCore Backend API")
        print("=" * 80)
        print("RE-TEST nach Bug-Fixes - Vollständiger QA Audit Sprint 1-7")
        print("=" * 80)
        
        # Track sprint results
        sprint_results = {}
        
        # Run all sprint tests
        sprint_results["Sprint 1"] = self.test_sprint1_auth_rbac()
        sprint_results["Sprint 2"] = self.test_sprint2_reservations()
        sprint_results["Sprint 3"] = self.test_sprint3_public_booking()
        sprint_results["Sprint 4"] = self.test_sprint4_waitlist()
        sprint_results["Sprint 5"] = self.test_sprint5_guest_management()
        sprint_results["Sprint 6"] = self.test_sprint6_payments()
        sprint_results["Sprint 7"] = self.test_sprint7_staff_dienstplan()
        sprint_results["Sprint 8"] = self.test_sprint8_steuerburo()
        sprint_results["Sprint 9"] = self.test_sprint9_loyalty()
        sprint_results["Audit Logs"] = self.test_audit_logs()
        
        # Summary
        print("\n" + "=" * 80)
        print("🏁 FULL QA AUDIT COMPLETE")
        print("=" * 80)
        
        # Sprint summary
        print("\n📊 SPRINT RESULTS:")
        for sprint, success in sprint_results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status} - {sprint}")
        
        # Overall summary
        print(f"\nTests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        # Failed tests
        if self.failed_tests:
            print(f"\n❌ FAILED TESTS ({len(self.failed_tests)}):")
            for test in self.failed_tests:
                print(f"  • {test['name']}: {test['details']}")
        
        # Overall assessment
        passed_sprints = sum(1 for success in sprint_results.values() if success)
        total_sprints = len(sprint_results)
        
        print(f"\n🎯 GESAMTBEWERTUNG:")
        print(f"Sprints bestanden: {passed_sprints}/{total_sprints}")
        
        if passed_sprints == total_sprints:
            print("🟢 BETRIEBSFÄHIG: Alle Sprints erfolgreich")
            print("🟢 RELEASE-READY: System bereit für Produktion")
        elif passed_sprints >= total_sprints * 0.8:
            print("🟡 BETRIEBSFÄHIG: Hauptfunktionen arbeiten")
            print("🟡 RELEASE-READY: Mit kleineren Einschränkungen")
        else:
            print("🔴 NICHT BETRIEBSFÄHIG: Kritische Probleme vorhanden")
            print("🔴 NICHT RELEASE-READY: Weitere Entwicklung erforderlich")
        
        return passed_sprints == total_sprints


if __name__ == "__main__":
    tester = GastroCoreFullQAAudit()
    success = tester.run_full_qa_audit()
    sys.exit(0 if success else 1)