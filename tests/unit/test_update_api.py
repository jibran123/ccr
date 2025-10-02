#!/usr/bin/env python3
"""
Test script for UPDATE API functionality.
Tests all UPDATE endpoints with various scenarios.
"""

import requests
import json
from datetime import datetime

BASE_URL = 'http://localhost:5000/api'

def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_response(response, operation):
    """Print formatted response."""
    print(f"\n{operation}:")
    print(f"  Status: {response.status_code}")
    try:
        data = response.json()
        print(f"  Response: {json.dumps(data, indent=2)}")
    except:
        print(f"  Response: {response.text}")

def test_full_update():
    """Test full update (PUT)."""
    print_section("TEST 1: Full Update (PUT)")
    
    # First create a deployment
    print("\n1. Creating initial deployment...")
    create_data = {
        'api_name': 'test-update-api',
        'platform_id': 'IP4',
        'environment_id': 'tst',
        'status': 'DEPLOYING',
        'updated_by': 'test.user',
        'properties': {
            'api.id': '999888',
            'version': '1.0.0',
            'initial': 'true'
        }
    }
    
    response = requests.post(f'{BASE_URL}/deploy', json=create_data)
    print_response(response, "Create")
    
    # Now do a full update
    print("\n2. Full update - replacing all fields...")
    update_data = {
        'status': 'RUNNING',
        'updated_by': 'admin',
        'properties': {
            'api.id': '999888',
            'version': '2.0.0',
            'updated': 'true',
            'new_field': 'new_value'
        }
    }
    
    response = requests.put(
        f'{BASE_URL}/apis/test-update-api/platforms/IP4/environments/tst',
        json=update_data
    )
    print_response(response, "Full Update")

def test_partial_update():
    """Test partial update (PATCH)."""
    print_section("TEST 2: Partial Update (PATCH)")
    
    print("\n1. Partial update - updating only status...")
    update_data = {
        'status': 'STOPPED',
        'updated_by': 'operator'
    }
    
    response = requests.patch(
        f'{BASE_URL}/apis/test-update-api/platforms/IP4/environments/tst',
        json=update_data
    )
    print_response(response, "Partial Update (Status Only)")
    
    print("\n2. Partial update - adding new properties...")
    update_data = {
        'updated_by': 'developer',
        'properties': {
            'debug': 'false',
            'logging.level': 'INFO'
        }
    }
    
    response = requests.patch(
        f'{BASE_URL}/apis/test-update-api/platforms/IP4/environments/tst',
        json=update_data
    )
    print_response(response, "Partial Update (Properties)")
    
    print("\n3. Verify properties were merged...")
    response = requests.get(
        f'{BASE_URL}/apis/test-update-api/platforms/IP4/environments/tst'
    )
    print_response(response, "Get Deployment")

def test_status_update():
    """Test status-only update."""
    print_section("TEST 3: Status-Only Update")
    
    print("\n1. Changing status to RUNNING...")
    update_data = {
        'status': 'RUNNING',
        'updated_by': 'monitoring-system'
    }
    
    response = requests.patch(
        f'{BASE_URL}/apis/test-update-api/platforms/IP4/environments/tst/status',
        json=update_data
    )
    print_response(response, "Status Update")

def test_properties_update():
    """Test properties-only update."""
    print_section("TEST 4: Properties-Only Update")
    
    print("\n1. Updating specific properties...")
    update_data = {
        'updated_by': 'config-manager',
        'properties': {
            'version': '2.1.0',
            'feature.flag': 'enabled',
            'cache.ttl': '3600'
        }
    }
    
    response = requests.patch(
        f'{BASE_URL}/apis/test-update-api/platforms/IP4/environments/tst/properties',
        json=update_data
    )
    print_response(response, "Properties Update")
    
    print("\n2. Verify all properties are present...")
    response = requests.get(
        f'{BASE_URL}/apis/test-update-api/platforms/IP4/environments/tst'
    )
    print_response(response, "Get Deployment")

def test_update_nonexistent():
    """Test updating non-existent deployment."""
    print_section("TEST 5: Update Non-Existent Deployment")
    
    print("\n1. Trying to update deployment that doesn't exist...")
    update_data = {
        'status': 'RUNNING',
        'updated_by': 'test',
        'properties': {}
    }
    
    response = requests.patch(
        f'{BASE_URL}/apis/nonexistent-api/platforms/IP4/environments/tst',
        json=update_data
    )
    print_response(response, "Update Non-Existent")

def test_invalid_status():
    """Test updating with invalid status."""
    print_section("TEST 6: Invalid Status Update")
    
    print("\n1. Trying to update with invalid status...")
    update_data = {
        'status': 'INVALID_STATUS',
        'updated_by': 'test'
    }
    
    response = requests.patch(
        f'{BASE_URL}/apis/test-update-api/platforms/IP4/environments/tst/status',
        json=update_data
    )
    print_response(response, "Invalid Status")

def test_get_deployment():
    """Test getting deployment details."""
    print_section("TEST 7: Get Deployment Details")
    
    print("\n1. Getting current deployment details...")
    response = requests.get(
        f'{BASE_URL}/apis/test-update-api/platforms/IP4/environments/tst'
    )
    print_response(response, "Get Deployment")

def test_delete_deployment():
    """Test deleting a deployment."""
    print_section("TEST 8: Delete Deployment")
    
    print("\n1. Deleting deployment...")
    response = requests.delete(
        f'{BASE_URL}/apis/test-update-api/platforms/IP4/environments/tst'
    )
    print_response(response, "Delete Deployment")
    
    print("\n2. Verify deployment is gone...")
    response = requests.get(
        f'{BASE_URL}/apis/test-update-api/platforms/IP4/environments/tst'
    )
    print_response(response, "Get Deleted Deployment")

def test_multiple_environments():
    """Test updating one environment doesn't affect others."""
    print_section("TEST 9: Multiple Environments")
    
    print("\n1. Creating deployment in TST...")
    create_data = {
        'api_name': 'multi-env-api',
        'platform_id': 'IP4',
        'environment_id': 'tst',
        'status': 'RUNNING',
        'updated_by': 'test',
        'properties': {'env': 'tst', 'version': '1.0'}
    }
    response = requests.post(f'{BASE_URL}/deploy', json=create_data)
    print_response(response, "Create TST")
    
    print("\n2. Creating deployment in PRD...")
    create_data['environment_id'] = 'prd'
    create_data['properties'] = {'env': 'prd', 'version': '1.0'}
    response = requests.post(f'{BASE_URL}/deploy', json=create_data)
    print_response(response, "Create PRD")
    
    print("\n3. Updating only TST...")
    update_data = {
        'status': 'STOPPED',
        'updated_by': 'operator',
        'properties': {'env': 'tst', 'version': '2.0'}
    }
    response = requests.put(
        f'{BASE_URL}/apis/multi-env-api/platforms/IP4/environments/tst',
        json=update_data
    )
    print_response(response, "Update TST")
    
    print("\n4. Verify PRD is unchanged...")
    response = requests.get(
        f'{BASE_URL}/apis/multi-env-api/platforms/IP4/environments/prd'
    )
    print_response(response, "Get PRD")
    
    print("\n5. Cleanup...")
    requests.delete(f'{BASE_URL}/apis/multi-env-api/platforms/IP4/environments/tst')
    requests.delete(f'{BASE_URL}/apis/multi-env-api/platforms/IP4/environments/prd')

def run_all_tests():
    """Run all update tests."""
    print("\n" + "🚀" * 30)
    print("  UPDATE API TEST SUITE")
    print("🚀" * 30)
    
    try:
        test_full_update()
        test_partial_update()
        test_status_update()
        test_properties_update()
        test_update_nonexistent()
        test_invalid_status()
        test_get_deployment()
        test_multiple_environments()
        test_delete_deployment()  # Run delete last
        
        print("\n" + "✅" * 30)
        print("  ALL TESTS COMPLETED")
        print("✅" * 30 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_all_tests()