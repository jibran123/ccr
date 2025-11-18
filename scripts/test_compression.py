#!/usr/bin/env python3
"""
Test script for verifying gzip compression effectiveness
Week 9-10: API Optimization Phase
"""

import requests
import time

BASE_URL = "http://localhost:5000"

# Color codes
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


def test_compression():
    """Test compression on various endpoints."""
    print(f"\n{BOLD}{BLUE}Testing Response Compression{RESET}\n")

    endpoints = [
        "/api/search?q=user&limit=50",
        "/api/audit/logs?limit=100",
        "/api/audit/stats",
        "/api/suggestions/platforms",
        "/api/suggestions/environments"
    ]

    for endpoint in endpoints:
        url = f"{BASE_URL}{endpoint}"

        # Test without compression
        print(f"\n{BOLD}Testing: {endpoint}{RESET}")
        response_uncompressed = requests.get(url)
        size_uncompressed = len(response_uncompressed.content)

        # Test with compression
        headers = {'Accept-Encoding': 'gzip'}
        response_compressed = requests.get(url, headers=headers)

        # Check if actually compressed
        is_compressed = 'gzip' in response_compressed.headers.get('Content-Encoding', '')

        if is_compressed:
            size_compressed = int(response_compressed.headers.get('Content-Length', 0))
            if size_compressed == 0:
                # Length not in header, measure raw
                size_compressed = len(response_compressed.content)

            savings = ((size_uncompressed - size_compressed) / size_uncompressed) * 100

            print(f"  Uncompressed: {size_uncompressed} bytes")
            print(f"  Compressed:   {size_compressed} bytes")
            print(f"  {GREEN}Savings: {savings:.1f}%{RESET}")
        else:
            print(f"  Size: {size_uncompressed} bytes")
            print(f"  {YELLOW}Not compressed (response too small < 500 bytes){RESET}")


def main():
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}CCR API Manager - Compression Test{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"Testing: {BASE_URL}\n")

    test_compression()

    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{GREEN}Test Complete!{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")


if __name__ == "__main__":
    main()
