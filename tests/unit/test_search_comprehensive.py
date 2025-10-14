#!/usr/bin/env python3
"""
Comprehensive Search Test Script
Tests all search functionality to verify the fix works correctly.
"""

import requests
import json
from typing import Dict, List

BASE_URL = 'http://localhost:5000/api'

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{bcolors.HEADER}{bcolors.BOLD}{'=' * 70}{bcolors.ENDC}")
    print(f"{bcolors.HEADER}{bcolors.BOLD}{text:^70}{bcolors.ENDC}")
    print(f"{bcolors.HEADER}{bcolors.BOLD}{'=' * 70}{bcolors.ENDC}\n")

def print_test(test_name):
    print(f"{bcolors.OKCYAN}📝 TEST: {test_name}{bcolors.ENDC}")

def print_pass(message):
    print(f"  {bcolors.OKGREEN}✅ PASS: {message}{bcolors.ENDC}")

def print_fail(message):
    print(f"  {bcolors.FAIL}❌ FAIL: {message}{bcolors.ENDC}")

def print_info(message):
    print(f"  {bcolors.OKBLUE}ℹ️  {message}{bcolors.ENDC}")

def search(query: str) -> Dict:
    """Perform search and return results."""
    response = requests.get(f'{BASE_URL}/search', params={'q': query, 'page_size': 100})
    if response.status_code == 200:
        return response.json()
    else:
        print_fail(f"HTTP {response.status_code}: {response.text}")
        return {'data': []}

def verify_result_count(results: List, expected_min: int, expected_max: int, test_name: str):
    """Verify result count is within expected range."""
    count = len(results)
    if expected_min <= count <= expected_max:
        print_pass(f"{test_name}: Found {count} results (expected {expected_min}-{expected_max})")
        return True
    else:
        print_fail(f"{test_name}: Found {count} results (expected {expected_min}-{expected_max})")
        return False

def verify_all_match(results: List, field: str, value: str, test_name: str):
    """Verify all results have specific field value."""
    mismatches = [r for r in results if r.get(field) != value]
    if not mismatches:
        print_pass(f"{test_name}: All {len(results)} results have {field}={value}")
        return True
    else:
        print_fail(f"{test_name}: {len(mismatches)} results don't match {field}={value}")
        for m in mismatches[:3]:
            print_info(f"Mismatch: {m.get('API Name')} has {field}={m.get(field)}")
        return False

def verify_contains(results: List, text: str, test_name: str):
    """Verify results contain text in any field."""
    matching = []
    for r in results:
        found = False
        for field in ['API Name', 'PlatformID', 'Environment', 'Status', 'UpdatedBy', 'Version']:
            value = str(r.get(field, '')).lower()
            if text.lower() in value:
                found = True
                break
        if found:
            matching.append(r)
    
    if matching:
        print_pass(f"{test_name}: {len(matching)}/{len(results)} results contain '{text}'")
        return True
    else:
        print_fail(f"{test_name}: No results contain '{text}'")
        return False

def test_simple_text_search():
    """Test simple text search with word boundaries."""
    print_header("TEST 1: SIMPLE TEXT SEARCH")
    
    # Test 1.1: "blue" should match "ivp-test-app-blue"
    print_test("1.1: Search 'blue'")
    data = search('blue')
    results = data.get('data', [])
    verify_result_count(results, 1, 10, "blue search")
    verify_contains(results, 'blue', "Contains 'blue'")
    
    # Test 1.2: "tst" should NOT match "test" (word boundary)
    print_test("1.2: Search 'tst' (word boundary)")
    data = search('tst')
    results = data.get('data', [])
    print_info(f"Found {len(results)} results")
    
    # Check no results contain "test" but not "tst"
    bad_matches = []
    for r in results:
        api_name = r.get('API Name', '').lower()
        if 'test' in api_name and 'tst' not in api_name:
            bad_matches.append(r)
    
    if not bad_matches:
        print_pass("No false matches with 'test' (correct word boundary)")
    else:
        print_fail(f"Found {len(bad_matches)} false matches with 'test'")
    
    # Test 1.3: "IP4" should NOT match "IP3" or "IP5"
    print_test("1.3: Search 'IP4' (word boundary)")
    data = search('IP4')
    results = data.get('data', [])
    
    # All results should have Platform = "IP4"
    ip3_or_ip5 = [r for r in results if r.get('PlatformID') in ['IP3', 'IP5']]
    if not ip3_or_ip5:
        print_pass("No false matches with IP3 or IP5")
    else:
        print_fail(f"Found {len(ip3_or_ip5)} false matches with IP3/IP5")

def test_attribute_search():
    """Test attribute search (exact, case sensitive)."""
    print_header("TEST 2: ATTRIBUTE SEARCH")
    
    # Test 2.1: Platform = IP4
    print_test("2.1: Platform = IP4")
    data = search('Platform = IP4')
    results = data.get('data', [])
    verify_result_count(results, 1, 50, "Platform=IP4")
    verify_all_match(results, 'PlatformID', 'IP4', "All Platform=IP4")
    
    # Test 2.2: Environment = tst
    print_test("2.2: Environment = tst")
    data = search('Environment = tst')
    results = data.get('data', [])
    verify_result_count(results, 1, 50, "Environment=tst")
    verify_all_match(results, 'Environment', 'tst', "All Environment=tst")
    
    # Test 2.3: Status = RUNNING
    print_test("2.3: Status = RUNNING")
    data = search('Status = RUNNING')
    results = data.get('data', [])
    verify_all_match(results, 'Status', 'RUNNING', "All Status=RUNNING")
    
    # Test 2.4: API NAME = ivp-test-app-blue
    print_test("2.4: API NAME = ivp-test-app-blue")
    data = search('API NAME = ivp-test-app-blue')
    results = data.get('data', [])
    verify_all_match(results, 'API Name', 'ivp-test-app-blue', "All API Name match")

def test_properties_search():
    """Test properties search (case sensitive, string values)."""
    print_header("TEST 3: PROPERTIES SEARCH")
    
    # Test 3.1: Properties : debug.logging = false
    print_test("3.1: Properties : debug.logging = false")
    data = search('Properties : debug.logging = false')
    results = data.get('data', [])
    
    if results:
        print_pass(f"Found {len(results)} results with debug.logging=false")
        
        # Verify properties
        correct = 0
        for r in results:
            props = r.get('Properties', {})
            if props.get('debug.logging') == 'false':
                correct += 1
        
        if correct == len(results):
            print_pass(f"All {correct} results have debug.logging='false' (string)")
        else:
            print_fail(f"Only {correct}/{len(results)} have correct property")
    else:
        print_fail("No results found for debug.logging=false")
    
    # Test 3.2: Properties : env = tst
    print_test("3.2: Properties : env = tst")
    data = search('Properties : env = tst')
    results = data.get('data', [])
    
    if results:
        print_pass(f"Found {len(results)} results with env=tst")
    else:
        print_fail("No results found for env=tst")

def test_combined_and_search():
    """Test AND operator (strict row-level matching)."""
    print_header("TEST 4: COMBINED SEARCH (AND)")
    
    # Test 4.1: tst AND Platform = IP4
    print_test("4.1: tst AND Platform = IP4")
    data = search('tst AND Platform = IP4')
    results = data.get('data', [])
    
    if results:
        print_pass(f"Found {len(results)} results")
        
        # All must have Platform = IP4
        verify_all_match(results, 'PlatformID', 'IP4', "All have Platform=IP4")
    else:
        print_fail("No results found")
    
    # Test 4.2: Platform = IP4 AND Environment = tst
    print_test("4.2: Platform = IP4 AND Environment = tst")
    data = search('Platform = IP4 AND Environment = tst')
    results = data.get('data', [])
    
    if results:
        verify_all_match(results, 'PlatformID', 'IP4', "All Platform=IP4")
        verify_all_match(results, 'Environment', 'tst', "All Environment=tst")
    else:
        print_fail("No results found")

def test_combined_or_search():
    """Test OR operator (loose matching)."""
    print_header("TEST 5: COMBINED SEARCH (OR)")
    
    # Test 5.1: Platform = IP3 OR Platform = IP4
    print_test("5.1: Platform = IP3 OR Platform = IP4")
    data = search('Platform = IP3 OR Platform = IP4')
    results = data.get('data', [])
    
    if results:
        print_pass(f"Found {len(results)} results")
        
        # Check all are IP3 or IP4
        valid = [r for r in results if r.get('PlatformID') in ['IP3', 'IP4']]
        if len(valid) == len(results):
            print_pass("All results are IP3 or IP4")
        else:
            print_fail(f"Only {len(valid)}/{len(results)} are IP3 or IP4")
    else:
        print_fail("No results found")

def test_empty_search():
    """Test empty search returns all."""
    print_header("TEST 6: EMPTY SEARCH")
    
    print_test("6.1: Empty search (should return all)")
    data = search('')
    results = data.get('data', [])
    
    if len(results) > 0:
        print_pass(f"Found {len(results)} results (all deployments)")
    else:
        print_fail("Empty search returned nothing")

def run_all_tests():
    """Run all test suites."""
    print(f"\n{bcolors.BOLD}{bcolors.HEADER}")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "COMPREHENSIVE SEARCH TEST SUITE" + " " * 22 + "║")
    print("╚" + "═" * 68 + "╝")
    print(f"{bcolors.ENDC}\n")
    
    try:
        test_simple_text_search()
        test_attribute_search()
        test_properties_search()
        test_combined_and_search()
        test_combined_or_search()
        test_empty_search()
        
        print_header("ALL TESTS COMPLETED")
        print(f"{bcolors.OKGREEN}✅ Check results above for any failures{bcolors.ENDC}\n")
        
    except Exception as e:
        print_fail(f"Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_all_tests()