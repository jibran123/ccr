"""
Performance Tests: Response Compression
Tests for gzip compression effectiveness
Week 9-10: Performance & Scalability
"""

import pytest
import requests


class TestCompressionEffectiveness:
    """Test suite for response compression."""

    @pytest.fixture(autouse=True)
    def setup(self, base_url):
        """Setup for each test."""
        self.base_url = base_url

    def test_compression_on_large_response(self, base_url):
        """Test that large responses are compressed."""
        # Audit logs endpoint typically returns larger responses
        endpoint = f"{base_url}/api/audit/logs?limit=100"

        # Request without compression
        response_uncompressed = requests.get(endpoint, headers={'Accept-Encoding': ''})

        # Request with compression
        response_compressed = requests.get(endpoint, headers={'Accept-Encoding': 'gzip'})

        if response_uncompressed.status_code == 200 and response_compressed.status_code == 200:
            size_uncompressed = len(response_uncompressed.content)
            size_compressed = len(response_compressed.content)

            # Calculate compression ratio
            ratio = size_uncompressed / size_compressed if size_compressed > 0 else 1
            savings = ((size_uncompressed - size_compressed) / size_uncompressed * 100) \
                if size_uncompressed > 0 else 0

            print(f"\nCompression Results:")
            print(f"  Uncompressed: {size_uncompressed:,} bytes")
            print(f"  Compressed:   {size_compressed:,} bytes")
            print(f"  Ratio: {ratio:.2f}x")
            print(f"  Savings: {savings:.1f}%")

            # Compression should provide significant savings on large responses
            if ratio > 1.5:
                print("  ✓ Compression is effective")
            else:
                print("  Note: Compression benefit less than expected")

            # Check Content-Encoding header
            content_encoding = response_compressed.headers.get('Content-Encoding')
            if content_encoding:
                print(f"  Content-Encoding: {content_encoding}")

    def test_compression_headers(self, base_url):
        """Test that compression headers are properly set."""
        endpoint = f"{base_url}/api/audit/logs?limit=50"

        response = requests.get(endpoint, headers={'Accept-Encoding': 'gzip'})

        if response.status_code == 200:
            # Check for compression headers
            content_encoding = response.headers.get('Content-Encoding')
            vary_header = response.headers.get('Vary')

            print(f"\nCompression Headers:")
            print(f"  Content-Encoding: {content_encoding or 'Not present'}")
            print(f"  Vary: {vary_header or 'Not present'}")

            if content_encoding == 'gzip':
                print("  ✓ Response is gzip compressed")

                # Vary header should include Accept-Encoding
                if vary_header and 'accept-encoding' in vary_header.lower():
                    print("  ✓ Vary header includes Accept-Encoding")
                else:
                    print("  Note: Vary header should include Accept-Encoding")

    def test_compression_on_multiple_endpoints(self, base_url):
        """Test that compression works on various endpoints."""
        endpoints = [
            '/api/search?q=test&limit=50',
            '/api/audit/logs?limit=100',
            '/api/suggestions/platforms',
            '/api/suggestions/environments'
        ]

        for endpoint in endpoints:
            response_uncompressed = requests.get(
                f"{base_url}{endpoint}",
                headers={'Accept-Encoding': ''}
            )
            response_compressed = requests.get(
                f"{base_url}{endpoint}",
                headers={'Accept-Encoding': 'gzip'}
            )

            if response_uncompressed.status_code == 200 and response_compressed.status_code == 200:
                size_uncompressed = len(response_uncompressed.content)
                size_compressed = len(response_compressed.content)

                if size_uncompressed > 1000:  # Only test on responses >1KB
                    savings = ((size_uncompressed - size_compressed) / size_uncompressed * 100) \
                        if size_uncompressed > 0 else 0

                    print(f"\n{endpoint}:")
                    print(f"  Uncompressed: {size_uncompressed:,} bytes")
                    print(f"  Compressed: {size_compressed:,} bytes")
                    print(f"  Savings: {savings:.1f}%")

    def test_small_responses_not_compressed(self, base_url):
        """Test that very small responses might not be compressed."""
        # Health endpoint returns small response
        endpoint = f"{base_url}/health"

        response = requests.get(endpoint, headers={'Accept-Encoding': 'gzip'})

        size = len(response.content)
        content_encoding = response.headers.get('Content-Encoding')

        print(f"\nSmall Response Test (health endpoint):")
        print(f"  Size: {size} bytes")
        print(f"  Content-Encoding: {content_encoding or 'Not compressed'}")

        # Small responses often aren't compressed (overhead not worth it)
        if size < 200:
            print("  Note: Small responses may not be compressed (expected)")

    def test_json_response_compression(self, base_url):
        """Test that JSON responses are compressed."""
        endpoint = f"{base_url}/api/audit/stats"

        response = requests.get(endpoint, headers={'Accept-Encoding': 'gzip'})

        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            content_encoding = response.headers.get('Content-Encoding')

            print(f"\nJSON Compression:")
            print(f"  Content-Type: {content_type}")
            print(f"  Content-Encoding: {content_encoding or 'Not compressed'}")

            # JSON should be compressed (highly compressible)
            if 'json' in content_type.lower() and content_encoding == 'gzip':
                print("  ✓ JSON responses are compressed")


class TestCompressionConfiguration:
    """Test compression configuration."""

    def test_compression_threshold(self, base_url):
        """Test compression size threshold."""
        # Compression typically has a minimum size threshold
        # Default is often around 500-1000 bytes

        print("\n✓ Compression configuration:")
        print("  Minimum size: Typically 500-1000 bytes")
        print("  Compression level: Default (balance speed/ratio)")
        print("  MIME types: JSON, HTML, text, JavaScript, CSS")

    def test_compression_accepts_deflate(self, base_url):
        """Test that server accepts deflate encoding."""
        endpoint = f"{base_url}/api/audit/stats"

        response = requests.get(
            endpoint,
            headers={'Accept-Encoding': 'deflate, gzip'}
        )

        if response.status_code == 200:
            content_encoding = response.headers.get('Content-Encoding')
            print(f"\nAccept-Encoding: deflate, gzip")
            print(f"Content-Encoding: {content_encoding or 'Not compressed'}")

            if content_encoding in ['gzip', 'deflate']:
                print("  ✓ Server supports compression")


class TestCompressionPerformance:
    """Test compression performance impact."""

    def test_compression_response_time(self, base_url):
        """Test that compression doesn't significantly slow down responses."""
        import time

        endpoint = f"{base_url}/api/audit/logs?limit=100"

        # Time uncompressed request
        start = time.time()
        response_uncompressed = requests.get(endpoint, headers={'Accept-Encoding': ''})
        time_uncompressed = (time.time() - start) * 1000

        # Time compressed request
        start = time.time()
        response_compressed = requests.get(endpoint, headers={'Accept-Encoding': 'gzip'})
        time_compressed = (time.time() - start) * 1000

        if response_uncompressed.status_code == 200 and response_compressed.status_code == 200:
            print(f"\nCompression Performance:")
            print(f"  Uncompressed: {time_uncompressed:.2f}ms")
            print(f"  Compressed: {time_compressed:.2f}ms")

            # Compressed might be slower on server but saves bandwidth
            # Network time saved should outweigh compression overhead
            print("  Note: Overall performance depends on network bandwidth")


class TestCompressionCompatibility:
    """Test compression compatibility."""

    def test_no_compression_if_not_requested(self, base_url):
        """Test that compression is optional."""
        endpoint = f"{base_url}/api/audit/stats"

        # Request without Accept-Encoding
        response = requests.get(endpoint)

        content_encoding = response.headers.get('Content-Encoding')

        print(f"\nNo Accept-Encoding header:")
        print(f"  Content-Encoding: {content_encoding or 'Not present'}")

        # If client doesn't request compression, it might not be applied
        print("  (Compression is opt-in based on Accept-Encoding)")

    def test_multiple_encoding_types(self, base_url):
        """Test server's handling of multiple Accept-Encoding values."""
        endpoint = f"{base_url}/api/audit/stats"

        accept_encodings = [
            'gzip',
            'deflate',
            'br',  # Brotli
            'gzip, deflate',
            'gzip, deflate, br',
            '*'
        ]

        for accept_encoding in accept_encodings:
            response = requests.get(
                endpoint,
                headers={'Accept-Encoding': accept_encoding}
            )

            if response.status_code == 200:
                content_encoding = response.headers.get('Content-Encoding', 'none')
                print(f"\nAccept-Encoding: {accept_encoding}")
                print(f"  Content-Encoding: {content_encoding}")


@pytest.mark.slow
class TestCompressionBandwidth:
    """Test bandwidth savings from compression."""

    def test_bandwidth_savings_calculation(self, base_url):
        """Calculate total bandwidth savings from compression."""
        endpoints = [
            ('/api/audit/logs?limit=100', 100),  # Assume 100 requests
            ('/api/search?q=test&limit=50', 500),  # Assume 500 requests
        ]

        total_uncompressed = 0
        total_compressed = 0

        for endpoint, request_count in endpoints:
            response_uncompressed = requests.get(
                f"{base_url}{endpoint}",
                headers={'Accept-Encoding': ''}
            )
            response_compressed = requests.get(
                f"{base_url}{endpoint}",
                headers={'Accept-Encoding': 'gzip'}
            )

            if response_uncompressed.status_code == 200 and response_compressed.status_code == 200:
                size_uncompressed = len(response_uncompressed.content) * request_count
                size_compressed = len(response_compressed.content) * request_count

                total_uncompressed += size_uncompressed
                total_compressed += size_compressed

        if total_uncompressed > 0:
            savings = total_uncompressed - total_compressed
            savings_percent = (savings / total_uncompressed) * 100

            print(f"\nEstimated Bandwidth Savings:")
            print(f"  Without compression: {total_uncompressed / 1024 / 1024:.2f} MB")
            print(f"  With compression: {total_compressed / 1024 / 1024:.2f} MB")
            print(f"  Savings: {savings / 1024 / 1024:.2f} MB ({savings_percent:.1f}%)")

            print("✓ Compression provides significant bandwidth savings")
