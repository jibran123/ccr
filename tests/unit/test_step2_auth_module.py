#!/usr/bin/env python3
"""Test authentication module (Step 2)."""

from app import create_app
from app.utils.auth import generate_token, validate_token, AuthError

print("=" * 60)
print("Step 2: Testing Authentication Module")
print("=" * 60)

app = create_app()

with app.app_context():
    print("\n✅ TEST 1: Generate Token")
    try:
        token_data = generate_token('john.doe', 'admin', 24)
        print(f"  ✓ Token generated successfully")
        print(f"  Username: {token_data['username']}")
        print(f"  Role: {token_data['role']}")
        print(f"  Token: {token_data['token'][:50]}...")
        print(f"  Expires: {token_data['expires_at']}")
        
        # Save token for next test
        token = token_data['token']
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import sys
        sys.exit(1)
    
    print("\n✅ TEST 2: Validate Token")
    try:
        payload = validate_token(token)
        print(f"  ✓ Token validated successfully")
        print(f"  Username: {payload['username']}")
        print(f"  Role: {payload['role']}")
        
        # Verify values match
        assert payload['username'] == 'john.doe', "Username mismatch"
        assert payload['role'] == 'admin', "Role mismatch"
        print(f"  ✓ Payload values verified")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import sys
        sys.exit(1)
    
    print("\n✅ TEST 3: Invalid Token")
    try:
        validate_token("invalid.token.here")
        print(f"  ✗ Should have rejected invalid token")
        import sys
        sys.exit(1)
    except AuthError as e:
        print(f"  ✓ Correctly rejected invalid token")
        print(f"  Error: {e.message}")
    
    print("\n✅ TEST 4: Different Roles")
    for role in ['admin', 'user', 'readonly']:
        try:
            token_data = generate_token(f'{role}_user', role, 1)
            print(f"  ✓ Generated token for role: {role}")
        except Exception as e:
            print(f"  ✗ Failed for role {role}: {e}")
            import sys
            sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ All authentication module tests passed!")
    print("=" * 60)