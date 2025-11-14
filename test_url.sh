#!/bin/bash

TOKEN=$(curl -s -X POST "http://localhost:8000/api/auth/login" -H "Content-Type: application/json" -d '{"email": "alice.test@example.com", "password": "Alice1234"}' | jq -r '.access_token')

echo "測試不同的 URL:"
echo ""

echo "1. /api/discovery/browse?limit=10 (無結尾斜線):"
curl -s -w "\nHTTP: %{http_code}\n" -X GET "http://localhost:8000/api/discovery/browse?limit=10" \
  -H "Authorization: Bearer $TOKEN"
echo ""
echo ""

echo "2. /api/discovery/browse/?limit=10 (有結尾斜線):"
curl -s -w "\nHTTP: %{http_code}\n" -X GET "http://localhost:8000/api/discovery/browse/?limit=10" \
  -H "Authorization: Bearer $TOKEN"
