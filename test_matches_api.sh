#!/bin/bash

# 測試配對列表 API

echo "=== 測試 MergeMeet 配對列表 API ==="
echo ""

# 1. 登入 Alice
echo "1. 登入 Alice..."
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice.test@example.com",
    "password": "Alice1234"
  }')

echo "登入回應: $LOGIN_RESPONSE"
echo ""

# 提取 access_token
ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$ACCESS_TOKEN" ]; then
  echo "❌ 登入失敗，無法取得 token"
  exit 1
fi

echo "✅ 登入成功，token: ${ACCESS_TOKEN:0:20}..."
echo ""

# 2. 測試配對列表 API (不帶斜線)
echo "2. 測試 GET /api/discovery/matches (不帶斜線)..."
MATCHES_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X GET "http://localhost:8000/api/discovery/matches" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

HTTP_CODE=$(echo "$MATCHES_RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d':' -f2)
RESPONSE_BODY=$(echo "$MATCHES_RESPONSE" | sed 's/HTTP_CODE:[0-9]*//')

echo "HTTP 狀態碼: $HTTP_CODE"
echo "回應內容:"
echo "$RESPONSE_BODY" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE_BODY"
echo ""

# 3. 測試配對列表 API (帶斜線) - 預期會 307 重定向
echo "3. 測試 GET /api/discovery/matches/ (帶斜線)..."
MATCHES_RESPONSE_SLASH=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X GET "http://localhost:8000/api/discovery/matches/" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

HTTP_CODE_SLASH=$(echo "$MATCHES_RESPONSE_SLASH" | grep -o "HTTP_CODE:[0-9]*" | cut -d':' -f2)
echo "HTTP 狀態碼: $HTTP_CODE_SLASH"
echo ""

# 總結
echo "=== 測試總結 ==="
if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ /api/discovery/matches 正常運作 (HTTP 200)"
else
  echo "❌ /api/discovery/matches 異常 (HTTP $HTTP_CODE)"
fi

if [ "$HTTP_CODE_SLASH" = "307" ]; then
  echo "⚠️  /api/discovery/matches/ 會觸發 307 重定向 (需要避免使用)"
fi
