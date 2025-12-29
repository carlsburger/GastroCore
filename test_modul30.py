#!/usr/bin/env python3
"""
Modul 30 Testing: Timeclock + Shifts V2
Focused test runner for the specific review request
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend_test import GastroCoreAPITester

def main():
    """Run Modul 30 tests specifically"""
    print("🚀 Starting Modul 30 Tests: Timeclock + Shifts V2")
    print("=" * 80)
    
    tester = GastroCoreAPITester()
    
    # Test sequence for Modul 30
    test_results = []
    
    # 1. Seed data and authentication
    print("\n🌱 Setting up test environment...")
    test_results.append(tester.test_seed_data())
    test_results.append(tester.test_authentication())
    
    # 2. Run Modul 30 specific tests
    print("\n⏰ MODUL 30: TIMECLOCK STATE MACHINE TESTING:")
    test_results.append(tester.test_modul30_timeclock_state_machine())
    
    print("\n📋 MODUL 30: SHIFTS V2 TESTING:")
    test_results.append(tester.test_modul30_shifts_v2())
    
    print("\n📊 MODUL 30: ADMIN OVERVIEW TESTING:")
    test_results.append(tester.test_modul30_admin_overview())
    
    # Summary
    print("\n" + "=" * 80)
    print(f"🏁 MODUL 30 TESTING COMPLETE")
    print(f"Tests run: {tester.tests_run}")
    print(f"Tests passed: {tester.tests_passed}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run*100):.1f}%")
    
    if tester.failed_tests:
        print(f"\n❌ FAILED TESTS ({len(tester.failed_tests)}):")
        for test in tester.failed_tests:
            print(f"  • {test['name']}: {test['details']}")
    else:
        print("\n✅ ALL MODUL 30 TESTS PASSED!")
    
    return tester.tests_passed == tester.tests_run

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)