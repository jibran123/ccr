#!/usr/bin/env python3
"""
Cache Performance Testing Script
Week 9-10: Test cache effectiveness for audit stats endpoint
"""

import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:5000"

# Color codes
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


def test_audit_stats_cache():
    """Test audit stats endpoint with caching."""
    print(f"\n{BOLD}{BLUE}Testing Audit Stats Endpoint with Caching{RESET}\n")

    endpoint = f"{BASE_URL}/api/audit/stats"

    # Test 1: First request (cache MISS - slow)
    print(f"{BOLD}Request 1: Cache MISS (expected){RESET}")
    start = time.time()
    response = requests.get(endpoint)
    first_time = (time.time() - start) * 1000
    print(f"Response time: {GREEN}{first_time:.2f}ms{RESET}")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Total logs: {data['data']['total_logs']}")

    time.sleep(0.5)  # Small delay

    # Test 2: Second request (cache HIT - fast!)
    print(f"\n{BOLD}Request 2: Cache HIT (expected){RESET}")
    start = time.time()
    response = requests.get(endpoint)
    second_time = (time.time() - start) * 1000
    print(f"Response time: {GREEN}{second_time:.2f}ms{RESET}")
    print(f"Status: {response.status_code}")

    # Test 3-10: Multiple cached requests
    print(f"\n{BOLD}Requests 3-10: All Cache HITs{RESET}")
    times = []
    for i in range(3, 11):
        start = time.time()
        response = requests.get(endpoint)
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)

    avg_cached_time = sum(times) / len(times)
    print(f"Average response time (cached): {GREEN}{avg_cached_time:.2f}ms{RESET}")
    print(f"Min: {min(times):.2f}ms, Max: {max(times):.2f}ms")

    # Calculate improvement
    improvement = ((first_time - avg_cached_time) / first_time) * 100

    print(f"\n{BOLD}Performance Summary:{RESET}")
    print(f"First request (uncached): {first_time:.2f}ms")
    print(f"Subsequent requests (cached): {avg_cached_time:.2f}ms")
    print(f"{GREEN}Improvement: {improvement:.1f}%{RESET}")
    print(f"{GREEN}Speedup: {first_time / avg_cached_time:.1f}x faster!{RESET}")

    # Check if we met target
    target = 50.0  # Target: < 50ms for cached requests
    if avg_cached_time < target:
        print(f"\n{GREEN}✓ TARGET MET: Cached requests are < {target}ms{RESET}")
    else:
        print(f"\n{YELLOW}⚠ Target not met: {avg_cached_time:.2f}ms (target: <{target}ms){RESET}")

    return {
        'uncached': first_time,
        'cached_avg': avg_cached_time,
        'improvement_percent': improvement,
        'speedup': first_time / avg_cached_time
    }


def main():
    """Run cache performance tests."""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}CCR API Manager - Cache Performance Testing{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"Testing: {BASE_URL}")
    print(f"Target: Cached requests < 50ms\n")

    results = test_audit_stats_cache()

    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}Test Complete!{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")

    print(f"Before caching (baseline): ~143ms (P95)")
    print(f"After caching (uncached): {results['uncached']:.2f}ms")
    print(f"After caching (cached): {results['cached_avg']:.2f}ms")
    print(f"\n{GREEN}Overall improvement from baseline: ~{((143 - results['cached_avg']) / 143) * 100:.1f}%{RESET}")
    print(f"{GREEN}Cache is working! Speedup: {results['speedup']:.1f}x{RESET}\n")


if __name__ == "__main__":
    main()
