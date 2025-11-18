#!/usr/bin/env python3
"""
Performance Baseline Testing Script
Week 9-10: Measure current API response times and identify bottlenecks
"""

import requests
import time
import statistics
import json
from datetime import datetime
from typing import Dict, List, Tuple

# Configuration
BASE_URL = "http://localhost:5000"
NUM_REQUESTS = 10  # Number of requests per endpoint for averaging
WARMUP_REQUESTS = 2  # Warmup requests to exclude from measurements

# Color codes for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


def measure_endpoint(url: str, method: str = 'GET', data: dict = None,
                     headers: dict = None) -> Dict:
    """
    Measure response time for a single endpoint.

    Returns:
        dict: Statistics including min, max, avg, median, p95, p99
    """
    times = []
    status_codes = []
    errors = []

    # Warmup requests
    for _ in range(WARMUP_REQUESTS):
        try:
            if method == 'GET':
                requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                requests.post(url, json=data, headers=headers, timeout=10)
        except Exception:
            pass

    # Actual measurements
    for i in range(NUM_REQUESTS):
        try:
            start = time.time()

            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)

            elapsed = (time.time() - start) * 1000  # Convert to milliseconds

            times.append(elapsed)
            status_codes.append(response.status_code)

        except Exception as e:
            errors.append(str(e))

    if not times:
        return {
            'error': 'All requests failed',
            'errors': errors
        }

    # Calculate statistics
    times_sorted = sorted(times)
    p95_index = int(len(times_sorted) * 0.95)
    p99_index = int(len(times_sorted) * 0.99)

    return {
        'min': round(min(times), 2),
        'max': round(max(times), 2),
        'avg': round(statistics.mean(times), 2),
        'median': round(statistics.median(times), 2),
        'p95': round(times_sorted[p95_index] if p95_index < len(times_sorted) else times_sorted[-1], 2),
        'p99': round(times_sorted[p99_index] if p99_index < len(times_sorted) else times_sorted[-1], 2),
        'stddev': round(statistics.stdev(times) if len(times) > 1 else 0, 2),
        'success_rate': round((len(times) / NUM_REQUESTS) * 100, 1),
        'status_codes': list(set(status_codes)),
        'num_requests': NUM_REQUESTS
    }


def format_result(name: str, stats: Dict, target_ms: float = 200) -> str:
    """Format results with color coding based on performance targets."""
    if 'error' in stats:
        return f"{RED}✗ {name}: {stats['error']}{RESET}"

    avg = stats['avg']
    p95 = stats['p95']

    # Color code based on performance
    if p95 < target_ms * 0.5:  # Less than 50% of target
        color = GREEN
        status = "EXCELLENT"
    elif p95 < target_ms:  # Less than target
        color = GREEN
        status = "GOOD"
    elif p95 < target_ms * 1.5:  # Within 150% of target
        color = YELLOW
        status = "ACCEPTABLE"
    else:  # Above 150% of target
        color = RED
        status = "NEEDS OPTIMIZATION"

    result = f"{color}✓ {name}{RESET}\n"
    result += f"  Avg: {avg}ms | Median: {stats['median']}ms | P95: {p95}ms | P99: {stats['p99']}ms\n"
    result += f"  Min: {stats['min']}ms | Max: {stats['max']}ms | StdDev: {stats['stddev']}ms\n"
    result += f"  Success Rate: {stats['success_rate']}% | Status: {color}{status}{RESET}"

    return result


def main():
    """Run performance baseline tests."""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}CCR API Manager - Performance Baseline Testing{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")
    print(f"Base URL: {BASE_URL}")
    print(f"Requests per endpoint: {NUM_REQUESTS} (after {WARMUP_REQUESTS} warmup)")
    print(f"Target: P95 < 200ms\n")
    print(f"{BOLD}Starting baseline measurements...{RESET}\n")

    results = {}

    # Test 1: Health Check
    print(f"{BOLD}1. Health Check Endpoint{RESET}")
    stats = measure_endpoint(f"{BASE_URL}/health")
    results['health_check'] = stats
    print(format_result("GET /health", stats, target_ms=50))
    print()

    # Test 2: Main Page
    print(f"{BOLD}2. Main Page (Search UI){RESET}")
    stats = measure_endpoint(f"{BASE_URL}/")
    results['main_page'] = stats
    print(format_result("GET /", stats, target_ms=100))
    print()

    # Test 3: Audit Page
    print(f"{BOLD}3. Audit Page{RESET}")
    stats = measure_endpoint(f"{BASE_URL}/audit")
    results['audit_page'] = stats
    print(format_result("GET /audit", stats, target_ms=100))
    print()

    # Test 4: Search API - Simple Query
    print(f"{BOLD}4. Search API - Simple Query{RESET}")
    stats = measure_endpoint(f"{BASE_URL}/api/search?query=test")
    results['search_simple'] = stats
    print(format_result("GET /api/search?query=test", stats, target_ms=200))
    print()

    # Test 5: Search API - Complex Query
    print(f"{BOLD}5. Search API - Complex Query with Filters{RESET}")
    stats = measure_endpoint(
        f"{BASE_URL}/api/search?query=Platform%20%3D%20IP4%20AND%20Environment%20%3D%20tst"
    )
    results['search_complex'] = stats
    print(format_result("GET /api/search (complex)", stats, target_ms=200))
    print()

    # Test 6: Suggestions API
    print(f"{BOLD}6. Suggestions API{RESET}")
    stats = measure_endpoint(f"{BASE_URL}/api/suggestions?field=api_name&query=test")
    results['suggestions'] = stats
    print(format_result("GET /api/suggestions", stats, target_ms=100))
    print()

    # Test 7: Audit Logs - Recent
    print(f"{BOLD}7. Audit Logs - Recent{RESET}")
    stats = measure_endpoint(f"{BASE_URL}/api/audit/recent?hours=24")
    results['audit_recent'] = stats
    print(format_result("GET /api/audit/recent", stats, target_ms=200))
    print()

    # Test 8: Audit Logs - Filtered
    print(f"{BOLD}8. Audit Logs - Filtered Query{RESET}")
    stats = measure_endpoint(f"{BASE_URL}/api/audit/logs?limit=50")
    results['audit_filtered'] = stats
    print(format_result("GET /api/audit/logs", stats, target_ms=200))
    print()

    # Test 9: Audit Statistics
    print(f"{BOLD}9. Audit Statistics{RESET}")
    stats = measure_endpoint(f"{BASE_URL}/api/audit/stats")
    results['audit_stats'] = stats
    print(format_result("GET /api/audit/stats", stats, target_ms=200))
    print()

    # Test 10: Audit Actions
    print(f"{BOLD}10. Audit Actions List{RESET}")
    stats = measure_endpoint(f"{BASE_URL}/api/audit/actions")
    results['audit_actions'] = stats
    print(format_result("GET /api/audit/actions", stats, target_ms=50))
    print()

    # Summary
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}Summary{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")

    # Identify slowest endpoints
    endpoints_by_p95 = sorted(
        [(name, stats.get('p95', 999999)) for name, stats in results.items() if 'error' not in stats],
        key=lambda x: x[1],
        reverse=True
    )

    print(f"{BOLD}Slowest Endpoints (by P95):{RESET}")
    for i, (name, p95) in enumerate(endpoints_by_p95[:5], 1):
        color = RED if p95 > 200 else YELLOW if p95 > 100 else GREEN
        print(f"  {i}. {name}: {color}{p95}ms{RESET}")

    # Calculate overall metrics
    all_p95s = [stats['p95'] for stats in results.values() if 'error' not in stats]
    all_avgs = [stats['avg'] for stats in results.values() if 'error' not in stats]

    print(f"\n{BOLD}Overall Metrics:{RESET}")
    print(f"  Average P95: {round(statistics.mean(all_p95s), 2)}ms")
    print(f"  Average Response Time: {round(statistics.mean(all_avgs), 2)}ms")
    print(f"  Endpoints meeting target (P95 < 200ms): {sum(1 for p95 in all_p95s if p95 < 200)}/{len(all_p95s)}")

    # Recommendations
    print(f"\n{BOLD}Recommendations:{RESET}")
    slow_endpoints = [name for name, p95 in endpoints_by_p95 if p95 > 200]
    if slow_endpoints:
        print(f"  {RED}⚠ NEEDS OPTIMIZATION:{RESET}")
        for endpoint in slow_endpoints:
            print(f"    - {endpoint}")
    else:
        print(f"  {GREEN}✓ All endpoints meeting performance targets!{RESET}")

    # Save results to file
    output_file = f"performance_baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'config': {
                'base_url': BASE_URL,
                'num_requests': NUM_REQUESTS,
                'warmup_requests': WARMUP_REQUESTS
            },
            'results': results,
            'summary': {
                'avg_p95': round(statistics.mean(all_p95s), 2),
                'avg_response_time': round(statistics.mean(all_avgs), 2),
                'endpoints_meeting_target': sum(1 for p95 in all_p95s if p95 < 200),
                'total_endpoints': len(all_p95s)
            }
        }, f, indent=2)

    print(f"\n{BOLD}Results saved to: {output_file}{RESET}\n")


if __name__ == "__main__":
    main()
