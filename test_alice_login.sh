#!/bin/bash

ALICE_EMAIL="alice.test@example.com"
ALICE_PASSWORD="Alice1234"

echo "測試 Alice 登入..."

LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "alice.test@example.com", "password": "Alice1234"}')

ALICE_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$ALICE_TOKEN" != "null" ] && [ -n "$ALICE_TOKEN" ]; then
  echo "✅ Alice 登入成功"
  echo "Token: ${ALICE_TOKEN:0:30}..."
  echo ""

  echo "測試 browse API:"
  curl -s -X GET "http://localhost:8000/api/discovery/browse/?limit=10" \
    -H "Authorization: Bearer $ALICE_TOKEN" | jq '.'
else
  echo "❌ Alice 登入失敗"
  echo "回應: $LOGIN_RESPONSE"
fi
