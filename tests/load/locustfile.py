"""
Locust Load Testing Script for CCR API Manager
Week 9-10: Phase 5 - Load Testing

Usage:
    # Run with 10 users
    locust -f scripts/locustfile.py --headless -u 10 -r 2 -t 60s --host http://localhost:5000

    # Run with 50 users
    locust -f scripts/locustfile.py --headless -u 50 -r 5 -t 60s --host http://localhost:5000

    # Run with 100 users
    locust -f scripts/locustfile.py --headless -u 100 -r 10 -t 60s --host http://localhost:5000

    # Run with web UI
    locust -f scripts/locustfile.py --host http://localhost:5000
"""

from locust import HttpUser, task, between, events
import json
import random
import time


class CCRAPIUser(HttpUser):
    """
    Simulates a typical CCR API Manager user.

    Behaviors:
    - Search for APIs (most common)
    - View audit logs
    - Check audit statistics
    - Get suggestions for platforms/environments
    - View specific API details
    """

    # Wait time between tasks (1-3 seconds)
    wait_time = between(1, 3)

    def on_start(self):
        """Called when a simulated user starts."""
        # Simulate checking health endpoint on startup
        self.client.get("/health")

    @task(40)
    def search_apis(self):
        """
        Search for APIs (40% of requests).
        Most common user action.
        """
        search_queries = [
            "",  # Empty search (get all)
            "user",
            "api",
            "service",
            "Platform = IP4",
            "Status = RUNNING",
            "Platform = IP3 AND Environment = prd"
        ]

        query = random.choice(search_queries)
        params = {
            "q": query,
            "page": 1,
            "page_size": random.choice([10, 20, 50])
        }

        with self.client.get("/api/search", params=params, name="/api/search", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(20)
    def view_audit_logs(self):
        """
        View audit logs (20% of requests).
        Common for checking recent changes.
        """
        params = {
            "limit": random.choice([20, 50, 100]),
            "skip": 0
        }

        with self.client.get("/api/audit/logs", params=params, name="/api/audit/logs", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(15)
    def view_audit_stats(self):
        """
        View audit statistics (15% of requests).
        Dashboard view - should be heavily cached.
        """
        with self.client.get("/api/audit/stats", name="/api/audit/stats", catch_response=True) as response:
            if response.status_code == 200:
                # Verify caching is working
                data = response.json()
                if "data" in data and "total_logs" in data["data"]:
                    response.success()
                else:
                    response.failure("Invalid response structure")
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(10)
    def get_platform_suggestions(self):
        """
        Get platform suggestions (10% of requests).
        Auto-complete functionality.
        """
        with self.client.get("/api/suggestions/platforms", name="/api/suggestions/platforms", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(10)
    def get_environment_suggestions(self):
        """
        Get environment suggestions (10% of requests).
        Auto-complete functionality.
        """
        with self.client.get("/api/suggestions/environments", name="/api/suggestions/environments", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(3)
    def filter_audit_logs_by_action(self):
        """
        Filter audit logs by action (3% of requests).
        More specific audit queries.
        """
        actions = ["CREATE", "UPDATE_STATUS", "DELETE_API_DEPLOYMENT"]
        params = {
            "action": random.choice(actions),
            "limit": 50
        }

        with self.client.get("/api/audit/logs", params=params, name="/api/audit/logs?action", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(2)
    def health_check(self):
        """
        Health check (2% of requests).
        Monitoring/health checks.
        """
        with self.client.get("/health", name="/health", catch_response=True) as response:
            if response.status_code == 200 and "status" in response.json():
                response.success()
            else:
                response.failure(f"Health check failed")


# Event handlers for custom metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts."""
    print("\n" + "="*70)
    print("CCR API Manager - Load Testing Started")
    print("="*70)
    print(f"Host: {environment.host}")
    print(f"Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}")
    print("="*70 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops."""
    print("\n" + "="*70)
    print("CCR API Manager - Load Testing Complete")
    print("="*70)

    # Print summary statistics
    stats = environment.stats
    print("\nRequest Statistics:")
    print(f"  Total Requests: {stats.total.num_requests}")
    print(f"  Total Failures: {stats.total.num_failures}")
    print(f"  Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"  Min Response Time: {stats.total.min_response_time:.2f}ms")
    print(f"  Max Response Time: {stats.total.max_response_time:.2f}ms")
    print(f"  Requests/sec: {stats.total.total_rps:.2f}")
    print(f"  Failure Rate: {(stats.total.num_failures / stats.total.num_requests * 100) if stats.total.num_requests > 0 else 0:.2f}%")

    print("\nPercentile Response Times:")
    print(f"  50th percentile: {stats.total.get_response_time_percentile(0.5):.2f}ms")
    print(f"  75th percentile: {stats.total.get_response_time_percentile(0.75):.2f}ms")
    print(f"  90th percentile: {stats.total.get_response_time_percentile(0.90):.2f}ms")
    print(f"  95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"  99th percentile: {stats.total.get_response_time_percentile(0.99):.2f}ms")

    print("\n" + "="*70 + "\n")
