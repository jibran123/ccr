#!/usr/bin/env python3
"""
Test script to examine data structure in MongoDB
and verify field names for the CCR API Manager
"""

from pymongo import MongoClient
import json
from pprint import pprint

# MongoDB connection
MONGO_HOST = 'localhost'  # Change to 'mongo' if running inside container
MONGO_PORT = 27017
MONGO_DB = 'ccr'
MONGO_COLLECTION = 'apis'

def test_data_structure():
    """Test and examine the data structure in MongoDB."""
    
    try:
        # Connect to MongoDB
        client = MongoClient(MONGO_HOST, MONGO_PORT, serverSelectionTimeoutMS=5000)
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]
        
        print(f"Connected to MongoDB: {MONGO_HOST}:{MONGO_PORT}")
        print(f"Database: {MONGO_DB}, Collection: {MONGO_COLLECTION}")
        print("=" * 60)
        
        # Get document count
        count = collection.count_documents({})
        print(f"Total documents: {count}")
        print("=" * 60)
        
        # Get a sample document
        sample = collection.find_one({})
        
        if sample:
            print("Sample document structure:")
            print("-" * 40)
            
            # Print top-level fields
            print("Top-level fields:")
            for key in sample.keys():
                value_type = type(sample[key]).__name__
                print(f"  - {key}: {value_type}")
            
            print("\n" + "-" * 40)
            
            # Check Platform structure
            if 'Platform' in sample:
                platform = sample['Platform']
                
                if isinstance(platform, list) and len(platform) > 0:
                    print("Platform is an ARRAY structure")
                    print(f"Number of platforms: {len(platform)}")
                    
                    # Examine first platform
                    first_platform = platform[0]
                    print("\nFirst Platform fields:")
                    for key in first_platform.keys():
                        value_type = type(first_platform[key]).__name__
                        print(f"  - {key}: {value_type}")
                    
                    # Check Environment structure
                    if 'Environment' in first_platform:
                        env = first_platform['Environment']
                        if isinstance(env, list) and len(env) > 0:
                            print(f"\nEnvironment is an ARRAY with {len(env)} items")
                            first_env = env[0]
                            print("First Environment fields:")
                            for key in first_env.keys():
                                value_type = type(first_env[key]).__name__
                                if key == 'Properties':
                                    print(f"  - {key}: {value_type} ({len(first_env[key])} items)")
                                else:
                                    value = first_env[key]
                                    if isinstance(value, str) and len(value) > 50:
                                        value = value[:50] + "..."
                                    print(f"  - {key}: {value_type} = {value}")
                            
                            # Show Properties if present
                            if 'Properties' in first_env:
                                print("\nSample Properties (first 5):")
                                props = first_env['Properties']
                                for i, (key, value) in enumerate(list(props.items())[:5]):
                                    if isinstance(value, str) and len(value) > 50:
                                        value = value[:50] + "..."
                                    print(f"    {key}: {value}")
                        else:
                            print(f"\nEnvironment field exists but is not an array or is empty")
                    else:
                        print("\nNo Environment field in Platform")
                        
                elif isinstance(platform, str):
                    print("Platform is a STRING (old structure)")
                    print(f"Platform value: {platform}")
                else:
                    print(f"Platform has unexpected type: {type(platform)}")
            else:
                print("No Platform field found")
            
            print("\n" + "=" * 60)
            print("Full sample document (formatted):")
            print(json.dumps(sample, default=str, indent=2)[:2000])  # First 2000 chars
            
        else:
            print("No documents found in collection")
        
        # Test search for specific API
        print("\n" + "=" * 60)
        print("Testing search for 'ivp-test-app-blue':")
        result = collection.find_one({'API Name': 'ivp-test-app-blue'})
        if not result:
            result = collection.find_one({'api_name': 'ivp-test-app-blue'})
        if not result:
            result = collection.find_one({'apiName': 'ivp-test-app-blue'})
        
        if result:
            print("Found API!")
            # Count deployments
            if 'Platform' in result and isinstance(result['Platform'], list):
                total_deployments = 0
                for platform in result['Platform']:
                    if 'Environment' in platform and isinstance(platform['Environment'], list):
                        total_deployments += len(platform['Environment'])
                    else:
                        total_deployments += 1
                print(f"Total deployments: {total_deployments}")
        else:
            print("API not found with any field name variation")
        
        client.close()
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_data_structure()