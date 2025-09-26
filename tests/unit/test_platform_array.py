#!/usr/bin/env python3
"""Test script for Platform array structure"""

import requests
import json
from datetime import datetime

BASE_URL = 'http://localhost:5000/api'

def test_create_api_with_multiple_platforms():
    """Test creating an API with multiple platforms and environments"""
    
    print("Testing Platform Array Structure...")
    print("=" * 50)
    
    # Test API deployments
    test_apis = [
        {
            'api_name': 'test-multi-platform-api',
            'platform_id': 'IP4',
            'environment_id': 'dev',
            'status': 'RUNNING',
            'updated_by': 'john.doe',
            'properties': {
                'api.id': '1234567',
                'version': '1.0.0',
                'endpoint': 'https://api.example.com'
            }
        },
        {
            'api_name': 'test-multi-platform-api',
            'platform_id': 'IP4',
            'environment_id': 'tst',
            'status': 'RUNNING',
            'updated_by': 'jane.smith',
            'properties': {
                'api.id': '1234567',
                'version': '1.0.1',
                'endpoint': 'https://test-api.example.com'
            }
        },
        {
            'api_name': 'test-multi-platform-api',
            'platform_id': 'OpenShift',
            'environment_id': 'dev',
            'status': 'DEPLOYING',
            'updated_by': 'admin',
            'properties': {
                'api.id': '1234567',
                'version': '1.0.0',
                'cluster': 'openshift-dev'
            }
        }
    ]
    
    for api_data in test_apis:
        print(f"\nDeploying {api_data['api_name']} to {api_data['platform_id']}/{api_data['environment_id']}:")
        
        response = requests.post(f'{BASE_URL}/apis/deploy', json=api_data)
        print(f"  Status: {response.status_code}")
        if response.status_code in [200, 201]:
            print(f"  Response: {response.json()}")
        else:
            print(f"  Error: {response.text}")
    
    # Fetch the API to see the structure
    print("\n" + "=" * 50)
    print("Fetching all APIs to verify structure...")
    
    response = requests.get(f'{BASE_URL}/apis?q=test-multi-platform')
    if response.status_code == 200:
        data = response.json()
        print(f"Found {len(data['apis'])} deployments")
        
        for api in data['apis']:
            print(f"  - {api['apiName']} | {api['platform']}/{api['environment']} | {api['status']}")
    
    # Test property search
    print("\n" + "=" * 50)
    print("Testing property search...")
    
    response = requests.get(f'{BASE_URL}/apis/search/properties?key=api.id&value=1234567')
    if response.status_code == 200:
        data = response.json()
        print(f"Found {data['total']} deployments with api.id=1234567")
        for api in data['apis']:
            print(f"  - {api['apiName']} on {api['platform']}/{api['environment']}")

if __name__ == '__main__':
    test_create_api_with_multiple_platforms()