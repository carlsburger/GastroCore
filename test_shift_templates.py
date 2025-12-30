#!/usr/bin/env python3
"""
Shift Templates V2 Migration Testing Script
Tests the specific endpoints mentioned in the review request
"""

import sys
import os
sys.path.append('/app')

from backend_test import GastroCoreAPITester

def main():
    """Run only the Shift Templates V2 Migration tests"""
    print("🔄 Shift Templates V2 Migration - Backend Testing")
    print("=" * 60)
    
    # Initialize tester with backend URL from frontend .env
    tester = GastroCoreAPITester()
    
    # Test authentication first
    print("\n🔐 Authenticating...")
    auth_success = tester.test_authentication()
    
    if not auth_success:
        print("❌ Authentication failed. Cannot proceed with tests.")
        return False
    
    # Run the shift templates migration tests
    print("\n🔄 Running Shift Templates V2 Migration Tests...")
    migration_success = tester.test_shift_templates_v2_migration()
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 SHIFT TEMPLATES V2 MIGRATION TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"❌ Tests failed: {len(tester.failed_tests)}")
    
    if tester.failed_tests:
        print("\n🔍 FAILED TESTS:")
        for test in tester.failed_tests:
            print(f"  ❌ {test['name']}: {test['details']}")
    
    success_rate = (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0
    print(f"\n📈 Success rate: {success_rate:.1f}%")
    
    if migration_success:
        print("🎉 Shift Templates V2 Migration tests completed successfully!")
    else:
        print("⚠️ Some Shift Templates V2 Migration tests failed.")
    
    return migration_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)