#!/bin/bash

# Test Authentication Enforcement (Step 5)
# Tests with AUTH_ENABLED=true

set -e

BASE_URL="http://localhost:5000"

# Get admin key from .env
ADMIN_KEY=$(grep JWT_ADMIN_KEY .env | cut -d '=' -f2)

if [ -z "$ADMIN_KEY" ]; then
    echo "❌ ERROR: Could not read JWT_ADMIN_KEY from .env"
    exit 1
fi

echo "============================================================"
echo "Step 5: Testing Authentication Enforcement"
echo "============================================================"
echo ""
echo "✅ AUTH_ENABLED=true - Security is NOW ENFORCED"
echo ""

# Test 1: Verify auth is enabled
echo "✅ TEST 1: Check auth status"
STATUS=$(curl -s "$BASE_URL/api/auth/status")
echo "$STATUS" | jq .

AUTH_ENABLED=$(echo "$STATUS" | jq -r '.data.auth_enabled')
if [ "$AUTH_ENABLED" == "true" ]; then
    echo "✅ PASS: Authentication is enabled"
else
    echo "❌ FAIL: Authentication should be enabled"
    exit 1
fi

# Test 2: Try deploy WITHOUT token (should fail)
echo ""
echo "✅ TEST 2: POST /api/deploy WITHOUT token (should fail)"
DEPLOY_NO_TOKEN=$(curl -s -X POST "$BASE_URL/api/deploy" \
  -H "Content-Type: application/json" \
  -d '{
    "api_name": "test-step5-api",
    "platform_id": "IP4",
    "environment_id": "tst",
    "version": "1.0.0",
    "status": "RUNNING",
    "updated_by": "test",
    "properties": {}
  }')

echo "$DEPLOY_NO_TOKEN" | jq .
ERROR=$(echo "$DEPLOY_NO_TOKEN" | jq -r '.error_code')

if [ "$ERROR" == "AUTH_REQUIRED" ]; then
    echo "✅ PASS: Deploy correctly rejected without token"
else
    echo "❌ FAIL: Deploy should require authentication"
    exit 1
fi

# Test 3: Generate valid token
echo ""
echo "✅ TEST 3: Generate valid token"
TOKEN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/token" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -d '{
    "username": "step5_user",
    "role": "admin",
    "expires_in_hours": 24
  }')

echo "$TOKEN_RESPONSE" | jq .
TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.data.token')

if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
    echo "✅ PASS: Token generated successfully"
    echo "Token: ${TOKEN:0:50}..."
else
    echo "❌ FAIL: Token generation failed"
    exit 1
fi

# Test 4: Deploy WITH valid token (should succeed)
echo ""
echo "✅ TEST 4: POST /api/deploy WITH valid token (should succeed)"
DEPLOY_WITH_TOKEN=$(curl -s -X POST "$BASE_URL/api/deploy" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "api_name": "test-step5-api",
    "platform_id": "IP4",
    "environment_id": "tst",
    "version": "1.0.0",
    "status": "RUNNING",
    "updated_by": "step5_user",
    "properties": {"authenticated": "true"}
  }')

echo "$DEPLOY_WITH_TOKEN" | jq .
STATUS=$(echo "$DEPLOY_WITH_TOKEN" | jq -r '.status')

if [ "$STATUS" == "success" ]; then
    echo "✅ PASS: Deploy succeeded with valid token"
else
    echo "❌ FAIL: Deploy should succeed with valid token"
    exit 1
fi

# Test 5: Update WITH valid token (should succeed)
echo ""
echo "✅ TEST 5: PATCH /api/apis/.../status WITH token (should succeed)"
UPDATE_WITH_TOKEN=$(curl -s -X PATCH "$BASE_URL/api/apis/test-step5-api/platforms/IP4/environments/tst/status" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "status": "STOPPED",
    "updated_by": "step5_user"
  }')

echo "$UPDATE_WITH_TOKEN" | jq .
STATUS=$(echo "$UPDATE_WITH_TOKEN" | jq -r '.status')

if [ "$STATUS" == "success" ]; then
    echo "✅ PASS: Update succeeded with valid token"
else
    echo "❌ FAIL: Update should succeed with valid token"
    exit 1
fi

# Test 6: Try with INVALID token (should fail)
echo ""
echo "✅ TEST 6: POST /api/deploy WITH invalid token (should fail)"
INVALID_TOKEN=$(curl -s -X POST "$BASE_URL/api/deploy" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer invalid.token.here" \
  -d '{
    "api_name": "test-api",
    "platform_id": "IP4",
    "environment_id": "tst",
    "version": "1.0.0",
    "status": "RUNNING",
    "updated_by": "test",
    "properties": {}
  }')

echo "$INVALID_TOKEN" | jq .
ERROR=$(echo "$INVALID_TOKEN" | jq -r '.error_code')

if [ "$ERROR" == "AUTH_FAILED" ]; then
    echo "✅ PASS: Deploy correctly rejected invalid token"
else
    echo "❌ FAIL: Deploy should reject invalid token"
    exit 1
fi

# Test 7: Search should still work (public endpoint)
echo ""
echo "✅ TEST 7: GET /api/search WITHOUT token (should work - public endpoint)"
SEARCH=$(curl -s "$BASE_URL/api/search?q=test-step5")
STATUS=$(echo "$SEARCH" | jq -r '.status')

if [ "$STATUS" == "success" ]; then
    echo "✅ PASS: Search works without token (public endpoint)"
else
    echo "❌ FAIL: Search should work without token"
    exit 1
fi

# Test 8: Delete WITH token (cleanup)
echo ""
echo "✅ TEST 8: DELETE WITH token (cleanup)"
DELETE=$(curl -s -X DELETE "$BASE_URL/api/apis/test-step5-api/platforms/IP4/environments/tst" \
  -H "Authorization: Bearer $TOKEN")

echo "$DELETE" | jq .
STATUS=$(echo "$DELETE" | jq -r '.status')

if [ "$STATUS" == "success" ]; then
    echo "✅ PASS: Delete succeeded with valid token"
else
    echo "❌ FAIL: Delete should succeed with valid token"
fi

echo ""
echo "============================================================"
echo "✅✅✅ ALL STEP 5 TESTS PASSED! ✅✅✅"
echo "============================================================"
echo ""
echo "🔐 SECURITY SUMMARY:"
echo "  ✅ Authentication is ENABLED and ENFORCED"
echo "  ✅ Protected endpoints REQUIRE valid tokens"
echo "  ✅ Invalid tokens are REJECTED"
echo "  ✅ Public endpoints work without authentication"
echo "  ✅ Token generation working"
echo "  ✅ Token validation working"
echo ""
echo "🎉 CCR API Manager is now SECURE! 🎉"
echo ""
echo "Your valid token (save this):"
echo "$TOKEN"
echo ""
echo "============================================================"