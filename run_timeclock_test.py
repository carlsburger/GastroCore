#!/usr/bin/env python3
"""
Run only the Timeclock Regression Test
"""

import sys
sys.path.append('/app')

from backend_test import GastroCoreAPITester

def main():
    tester = GastroCoreAPITester()
    
    print("🚀 Starting Timeclock Regression Test")
    print("=" * 80)
    
    # First authenticate
    print("🔐 Authenticating...")
    auth_success = tester.test_authentication()
    if not auth_success:
        print("❌ Authentication failed")
        return False
    
    # Run the specific timeclock regression test
    print("\n⏰ Running Timeclock Regression Test...")
    success = tester.test_timeclock_regression_mini_fix()
    
    # Summary
    print("\n" + "=" * 80)
    print(f"🏁 TIMECLOCK REGRESSION TEST COMPLETE")
    print(f"Tests run: {tester.tests_run}")
    print(f"Tests passed: {tester.tests_passed}")
    print(f"Tests failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success rate: {(tester.tests_passed / tester.tests_run * 100):.1f}%")
    
    if tester.failed_tests:
        print(f"\n❌ Failed tests:")
        for test in tester.failed_tests:
            print(f"  - {test['name']}: {test['details']}")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)