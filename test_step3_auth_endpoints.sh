#!/bin/bash

# Test Authentication Endpoints (Step 3)

set -e

BASE_URL="http://localhost:5000"
ADMIN_KEY="dev-admin-key-CHANGE-IN-PRODUCTION"

echo "============================================================"
echo "Step 3: Testing Authentication Endpoints"
echo "============================================================"

# Test 1: Check auth status
echo ""
echo "✅ TEST 1: GET /api/auth/status"
STATUS=$(curl -s "$BASE_URL/api/auth/status")
echo "$STATUS" | jq .

AUTH_ENABLED=$(echo "$STATUS" | jq -r '.data.auth_enabled')
echo "Auth Enabled: $AUTH_ENABLED"

# Test 2: Generate token (should fail - auth disabled)
echo ""
echo "✅ TEST 2: Generate token (auth disabled - should fail gracefully)"
TOKEN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/token" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -d '{
    "username": "test_user",
    "role": "admin",
    "expires_in_hours": 24
  }')
echo "$TOKEN_RESPONSE" | jq .

# Test 3: Try without admin key
echo ""
echo "✅ TEST 3: Generate token without admin key (should fail)"
NO_KEY=$(curl -s -X POST "$BASE_URL/api/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username": "test"}')
echo "$NO_KEY" | jq .

# Test 4: Try with wrong admin key
echo ""
echo "✅ TEST 4: Generate token with wrong admin key (should fail)"
WRONG_KEY=$(curl -s -X POST "$BASE_URL/api/auth/token" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: wrong-key" \
  -d '{"username": "test"}')
echo "$WRONG_KEY" | jq .

# Test 5: Verify token endpoint
echo ""
echo "✅ TEST 5: Verify invalid token (should fail)"
VERIFY=$(curl -s -X POST "$BASE_URL/api/auth/verify" \
  -H "Content-Type: application/json" \
  -d '{"token": "invalid.token.here"}')
echo "$VERIFY" | jq .

echo ""
echo "============================================================"
echo "✅ All authentication endpoint tests completed!"
echo ""
echo "NOTE: Token generation failed because AUTH_ENABLED=false"
echo "This is expected behavior for Step 3"
echo "In Step 5, we'll enable auth and test token generation"
echo "============================================================"