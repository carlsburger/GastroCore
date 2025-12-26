#!/usr/bin/env python3
"""
Event-Pricing + Reservierung Integration Test
Tests the specific scenarios requested in the review
"""

import requests
import sys
import json
from datetime import datetime, timedelta

class EventPricingTester:
    def __init__(self):
        # Use the backend URL from frontend .env
        try:
            with open('/app/frontend/.env', 'r') as f:
                for line in f:
                    if line.startswith('REACT_APP_BACKEND_URL='):
                        self.base_url = line.split('=', 1)[1].strip()
                        break
        except:
            self.base_url = "http://localhost:8001"
        
        self.admin_token = None
        self.test_data = {}
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

    def make_request(self, method: str, endpoint: str, data: dict = None, expected_status: int = 200):
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
        
        credentials = {"email": "admin@carlsburg.de", "password": "Carlsburg2025!"}
        result = self.make_request("POST", "auth/login", credentials, expected_status=200)
        
        if result["success"] and "access_token" in result["data"]:
            self.admin_token = result["data"]["access_token"]
            self.log_test("Admin authentication", True, "Successfully authenticated")
            return True
        else:
            self.log_test("Admin authentication", False, f"Status: {result['status_code']}")
            return False

    def test_event_pricing_integration(self):
        """Test Event-Pricing + Reservierung Integration as requested"""
        print("\n🎯 Testing Event-Pricing + Reservierung Integration...")
        
        integration_success = True
        
        # Test A: POST /api/reservations mit event_id (Schnitzel satt, 4 Personen)
        print("\n📝 Test A: Schnitzel satt (4 Personen, keine Anzahlung)")
        schnitzel_event_id = "9f5b382a-c9de-444c-9b0a-5a198af9e948"
        reservation_data_a = {
            "guest_name": "Test Familie Müller",
            "guest_phone": "+49 170 1111111",
            "guest_email": "mueller@example.de",
            "party_size": 4,
            "date": "2025-12-27",
            "time": "18:00",
            "event_id": schnitzel_event_id
        }
        
        result = self.make_request("POST", "reservations", reservation_data_a, expected_status=200)
        if result["success"]:
            reservation_a = result["data"]
            expected_total = 119.60  # 29.90 * 4
            if (reservation_a.get("status") == "neu" and 
                reservation_a.get("total_price") == expected_total and
                reservation_a.get("payment_mode") == "none"):
                self.log_test("Test A: Schnitzel satt (4 Personen, keine Anzahlung)", True, 
                            f"Status: {reservation_a.get('status')}, Total: {reservation_a.get('total_price')}€, Payment: {reservation_a.get('payment_mode')}")
                self.test_data["reservation_a_id"] = reservation_a["id"]
            else:
                self.log_test("Test A: Schnitzel satt", False, 
                            f"Expected: status=neu, total=119.60, payment=none. Got: status={reservation_a.get('status')}, total={reservation_a.get('total_price')}, payment={reservation_a.get('payment_mode')}")
                integration_success = False
        else:
            self.log_test("Test A: Schnitzel satt", False, f"Status: {result['status_code']}, Data: {result.get('data', {})}")
            integration_success = False
        
        # Test B: POST /api/reservations mit event_id + variant_code (Gänsemenü "main_only", 4 Personen)
        print("\n📝 Test B: Gänsemenü main_only (4 Personen, 20€ Anzahlung)")
        gaense_event_id = "8048b07b-0bb1-4334-86e3-ba8c282eee8b"
        reservation_data_b = {
            "guest_name": "Test Familie Weber",
            "guest_phone": "+49 170 2222222",
            "guest_email": "weber@example.de",
            "party_size": 4,
            "date": "2025-12-27",
            "time": "19:00",
            "event_id": gaense_event_id,
            "variant_code": "main_only"
        }
        
        result = self.make_request("POST", "reservations", reservation_data_b, expected_status=200)
        if result["success"]:
            reservation_b = result["data"]
            expected_total = 139.60  # 34.90 * 4
            expected_due = 80.00     # 20.00 * 4
            if (reservation_b.get("status") == "pending_payment" and 
                reservation_b.get("total_price") == expected_total and
                reservation_b.get("amount_due") == expected_due):
                self.log_test("Test B: Gänsemenü main_only (4 Personen, 20€ Anzahlung)", True, 
                            f"Status: {reservation_b.get('status')}, Total: {reservation_b.get('total_price')}€, Due: {reservation_b.get('amount_due')}€")
                self.test_data["reservation_b_id"] = reservation_b["id"]
            else:
                self.log_test("Test B: Gänsemenü main_only", False, 
                            f"Expected: status=pending_payment, total=139.60, due=80.00. Got: status={reservation_b.get('status')}, total={reservation_b.get('total_price')}, due={reservation_b.get('amount_due')}")
                integration_success = False
        else:
            self.log_test("Test B: Gänsemenü main_only", False, f"Status: {result['status_code']}, Data: {result.get('data', {})}")
            integration_success = False
        
        # Test C: POST /api/reservations mit event_id + variant_code (Valentinstag "menu_classic", 2 Personen)
        print("\n📝 Test C: Valentinstag menu_classic (2 Personen, 30€ Anzahlung)")
        valentinstag_event_id = "d0f79627-f047-41fe-9ec8-64965ff81b60"
        reservation_data_c = {
            "guest_name": "Test Paar Schmidt",
            "guest_phone": "+49 170 3333333",
            "guest_email": "schmidt@example.de",
            "party_size": 2,
            "date": "2025-12-27",
            "time": "20:00",
            "event_id": valentinstag_event_id,
            "variant_code": "menu_classic"
        }
        
        result = self.make_request("POST", "reservations", reservation_data_c, expected_status=200)
        if result["success"]:
            reservation_c = result["data"]
            expected_total = 119.80  # 59.90 * 2
            expected_due = 60.00     # 30.00 * 2
            if (reservation_c.get("status") == "pending_payment" and 
                reservation_c.get("total_price") == expected_total and
                reservation_c.get("amount_due") == expected_due):
                self.log_test("Test C: Valentinstag menu_classic (2 Personen, 30€ Anzahlung)", True, 
                            f"Status: {reservation_c.get('status')}, Total: {reservation_c.get('total_price')}€, Due: {reservation_c.get('amount_due')}€")
                self.test_data["reservation_c_id"] = reservation_c["id"]
            else:
                self.log_test("Test C: Valentinstag menu_classic", False, 
                            f"Expected: status=pending_payment, total=119.80, due=60.00. Got: status={reservation_c.get('status')}, total={reservation_c.get('total_price')}, due={reservation_c.get('amount_due')}")
                integration_success = False
        else:
            self.log_test("Test C: Valentinstag menu_classic", False, f"Status: {result['status_code']}, Data: {result.get('data', {})}")
            integration_success = False
        
        # Test D: POST /api/events/reservations/{id}/confirm-payment
        print("\n📝 Test D: Confirm payment (80€, bar)")
        if "reservation_b_id" in self.test_data:
            result = self.make_request("POST", f"events/reservations/{self.test_data['reservation_b_id']}/confirm-payment?amount_paid=80&payment_method=bar", 
                                     {}, expected_status=200)
            if result["success"]:
                payment_response = result["data"]
                if payment_response.get("success"):
                    self.log_test("Test D: Confirm payment (80€, bar)", True, 
                                f"Payment confirmed: {payment_response.get('message')}")
                    
                    # Verify reservation status changed
                    verify_result = self.make_request("GET", f"reservations/{self.test_data['reservation_b_id']}", expected_status=200)
                    if verify_result["success"]:
                        updated_res = verify_result["data"]
                        if (updated_res.get("status") == "bestätigt" and 
                            updated_res.get("payment_status") == "paid"):
                            self.log_test("Test D: Verify status after payment", True, 
                                        f"Status: {updated_res.get('status')}, Payment: {updated_res.get('payment_status')}")
                        else:
                            self.log_test("Test D: Verify status after payment", False, 
                                        f"Expected: status=bestätigt, payment_status=paid. Got: status={updated_res.get('status')}, payment_status={updated_res.get('payment_status')}")
                            integration_success = False
                else:
                    self.log_test("Test D: Confirm payment", False, f"Payment not successful: {payment_response}")
                    integration_success = False
            else:
                self.log_test("Test D: Confirm payment", False, f"Status: {result['status_code']}, Data: {result.get('data', {})}")
                integration_success = False
        
        # Test E: GET /api/events/reservations/pending-payments
        print("\n📝 Test E: Get pending payments")
        result = self.make_request("GET", "events/reservations/pending-payments", expected_status=200)
        if result["success"]:
            pending_data = result["data"]
            pending_reservations = pending_data.get("reservations", [])
            total_pending = pending_data.get("total", 0)
            self.log_test("Test E: Get pending payments", True, 
                        f"Found {total_pending} pending payment reservations")
            
            # Check if our test reservation C is in the list
            if "reservation_c_id" in self.test_data:
                found_c = any(r["id"] == self.test_data["reservation_c_id"] for r in pending_reservations)
                if found_c:
                    self.log_test("Test E: Verify test reservation C in pending list", True)
                else:
                    self.log_test("Test E: Verify test reservation C in pending list", False, 
                                "Test reservation C not found in pending payments")
                    integration_success = False
        else:
            self.log_test("Test E: Get pending payments", False, f"Status: {result['status_code']}, Data: {result.get('data', {})}")
            integration_success = False
        
        # Test F: POST /api/events/reservations/expire-unpaid
        print("\n📝 Test F: Expire unpaid reservations")
        result = self.make_request("POST", "events/reservations/expire-unpaid", expected_status=200)
        if result["success"]:
            expire_response = result["data"]
            expired_count = expire_response.get("expired_count", 0)
            self.log_test("Test F: Expire unpaid reservations", True, 
                        f"Expired {expired_count} reservations (should be 0 for fresh reservations)")
        else:
            self.log_test("Test F: Expire unpaid reservations", False, f"Status: {result['status_code']}, Data: {result.get('data', {})}")
            integration_success = False
        
        return integration_success

    def run_tests(self):
        """Run all Event-Pricing integration tests"""
        print(f"🚀 Starting Event-Pricing + Reservierung Integration Tests")
        print(f"🎯 Target: {self.base_url}")
        print("=" * 80)
        
        # Authenticate
        if not self.authenticate():
            print("❌ Authentication failed, cannot proceed")
            return False
        
        # Run the integration test
        success = self.test_event_pricing_integration()
        
        # Print summary
        print("\n" + "=" * 80)
        print(f"🏁 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.failed_tests:
            print(f"\n❌ Failed Tests ({len(self.failed_tests)}):")
            for test in self.failed_tests:
                print(f"  - {test['name']}: {test['details']}")
        else:
            print("\n✅ All tests passed!")
        
        return success

if __name__ == "__main__":
    tester = EventPricingTester()
    success = tester.run_tests()
    sys.exit(0 if success else 1)