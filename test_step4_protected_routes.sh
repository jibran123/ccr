#!/bin/bash

# Test Protected Routes (Step 4)
# Tests with AUTH_ENABLED=false (should work without token)

set -e

BASE_URL="http://localhost:5000"

echo "============================================================"
echo "Step 4: Testing Protected Routes (Auth Disabled)"
echo "============================================================"
echo ""
echo "AUTH_ENABLED=false - All requests should work WITHOUT token"
echo ""

# Test 1: Deploy without token (should work - auth disabled)
echo "✅ TEST 1: POST /api/deploy (no token)"
DEPLOY=$(curl -s -X POST "$BASE_URL/api/deploy" \
  -H "Content-Type: application/json" \
  -d '{
    "api_name": "test-step4-api",
    "platform_id": "IP4",
    "environment_id": "tst",
    "version": "1.0.0",
    "status": "RUNNING",
    "updated_by": "step4-test",
    "properties": {"test": "step4"}
  }')

echo "$DEPLOY" | jq .
STATUS=$(echo "$DEPLOY" | jq -r '.status')

if [ "$STATUS" == "success" ]; then
    echo "✅ PASS: Deploy works without token (auth disabled)"
else
    echo "❌ FAIL: Deploy should work without token when auth disabled"
    exit 1
fi

# Test 2: Update without token (should work)
echo ""
echo "✅ TEST 2: PATCH /api/apis/.../status (no token)"
UPDATE=$(curl -s -X PATCH "$BASE_URL/api/apis/test-step4-api/platforms/IP4/environments/tst/status" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "STOPPED",
    "updated_by": "step4-test"
  }')

echo "$UPDATE" | jq .
STATUS=$(echo "$UPDATE" | jq -r '.status')

if [ "$STATUS" == "success" ]; then
    echo "✅ PASS: Update works without token (auth disabled)"
else
    echo "❌ FAIL: Update should work without token when auth disabled"
    exit 1
fi

# Test 3: Delete without token (should work)
echo ""
echo "✅ TEST 3: DELETE /api/apis/... (no token)"
DELETE=$(curl -s -X DELETE "$BASE_URL/api/apis/test-step4-api/platforms/IP4/environments/tst")

echo "$DELETE" | jq .
STATUS=$(echo "$DELETE" | jq -r '.status')

if [ "$STATUS" == "success" ]; then
    echo "✅ PASS: Delete works without token (auth disabled)"
else
    echo "❌ FAIL: Delete should work without token when auth disabled"
    exit 1
fi

# Test 4: Search still works (no token needed)
echo ""
echo "✅ TEST 4: GET /api/search (no token)"
SEARCH=$(curl -s "$BASE_URL/api/search?q=blue")
STATUS=$(echo "$SEARCH" | jq -r '.status')

if [ "$STATUS" == "success" ]; then
    echo "✅ PASS: Search works without token"
else
    echo "❌ FAIL: Search should work without token"
    exit 1
fi

echo ""
echo "============================================================"
echo "✅ All Step 4 tests PASSED!"
echo ""
echo "SUMMARY:"
echo "- @require_auth() decorators added to protected routes"
echo "- With AUTH_ENABLED=false, all routes work WITHOUT token"
echo "- No regression - existing functionality intact"
echo ""
echo "NEXT: Step 5 will enable authentication and test with tokens"
echo "============================================================"