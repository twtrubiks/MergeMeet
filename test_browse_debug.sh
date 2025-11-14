#!/bin/bash

echo "=== 測試 Browse API ==="
echo ""

# 登入 Alice
echo "1. 登入 Alice..."
LOGIN=$(curl -s -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "alice.test@example.com", "password": "Alice1234"}')

TOKEN=$(echo "$LOGIN" | jq -r '.access_token')
echo "Token: ${TOKEN:0:30}..."
echo ""

# 呼叫 browse API
echo "2. 呼叫 browse API..."
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X GET "http://localhost:8000/api/discovery/browse/?limit=10" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d':' -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE")

echo "HTTP Status: $HTTP_CODE"
echo "Response Body:"
echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
echo ""

# 檢查資料庫
echo "3. 檢查資料庫中的候選人..."
docker exec mergemeet_postgres psql -U mergemeet -d mergemeet -c "
SELECT
  u.email,
  p.display_name,
  p.gender,
  p.is_complete
FROM users u
JOIN profiles p ON u.id = p.user_id
WHERE u.email LIKE '%test%'
ORDER BY u.email;
"
