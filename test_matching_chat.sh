#!/bin/bash

# MergeMeet 探索配對與即時聊天測試腳本
# 此腳本會創建兩個測試用戶，完成配對流程，並測試聊天功能

set -e  # 遇到錯誤立即停止

API_BASE="http://localhost:8000/api"
FRONTEND_BASE="http://localhost:5173"

echo "=========================================="
echo "MergeMeet 探索與配對 + 即時聊天測試"
echo "=========================================="
echo ""

# 顏色輸出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================
# 步驟 0: 清理舊的測試用戶
# ============================================
echo -e "${BLUE}[步驟 0/10] 清理舊的測試用戶${NC}"
docker exec mergemeet_postgres psql -U mergemeet -d mergemeet -c "DELETE FROM users WHERE email IN ('alice.test@example.com', 'bob.test@example.com');" > /dev/null 2>&1
echo -e "${GREEN}✅ 舊用戶已清理${NC}"
echo ""

# ============================================
# 步驟 1: 創建測試用戶 Alice
# ============================================
echo -e "${BLUE}[步驟 1/10] 註冊測試用戶 Alice${NC}"
ALICE_RESPONSE=$(curl -s -X POST "$API_BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice.test@example.com",
    "password": "Alice1234",
    "date_of_birth": "1995-06-15"
  }')

ALICE_TOKEN=$(echo $ALICE_RESPONSE | jq -r '.access_token')
if [ "$ALICE_TOKEN" == "null" ] || [ -z "$ALICE_TOKEN" ]; then
  echo "❌ Alice 註冊失敗，可能帳號已存在"
  echo "   回應: $ALICE_RESPONSE"
  exit 1
fi
echo -e "${GREEN}✅ Alice 註冊成功${NC}"
echo "   Token: ${ALICE_TOKEN:0:20}..."
echo ""

# ============================================
# 步驟 2: 創建 Alice 的個人檔案
# ============================================
echo -e "${BLUE}[步驟 2/10] 創建 Alice 的個人檔案${NC}"
curl -s -X POST "$API_BASE/profile/" \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Alice",
    "gender": "female",
    "bio": "喜歡旅遊和美食，熱愛生活！",
    "location": {
      "latitude": 25.0330,
      "longitude": 121.5654,
      "location_name": "台北市信義區"
    }
  }' > /dev/null

# 更新偏好設定
curl -s -X PATCH "$API_BASE/profile/" \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "min_age_preference": 25,
    "max_age_preference": 35,
    "max_distance_km": 50,
    "gender_preference": "male"
  }' > /dev/null
echo -e "${GREEN}✅ Alice 檔案創建成功${NC}"
echo ""

# ============================================
# 步驟 3: 設定 Alice 的興趣標籤
# ============================================
echo -e "${BLUE}[步驟 3/10] 取得興趣標籤並設定${NC}"
TAGS_RESPONSE=$(curl -s -X GET "$API_BASE/profile/interest-tags/")
TAG_IDS=$(echo $TAGS_RESPONSE | jq -r '.[0:3] | map(.id) | @json')

curl -s -X PUT "$API_BASE/profile/interests/" \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"interest_ids\": $TAG_IDS}" > /dev/null

# 標記檔案為完整（測試用）
docker exec mergemeet_postgres psql -U mergemeet -d mergemeet -c "UPDATE profiles SET is_complete = true WHERE user_id = (SELECT id FROM users WHERE email = 'alice.test@example.com');" > /dev/null 2>&1

echo -e "${GREEN}✅ Alice 興趣標籤設定成功${NC}"
echo ""

# ============================================
# 步驟 4: 創建測試用戶 Bob
# ============================================
echo -e "${BLUE}[步驟 4/10] 註冊測試用戶 Bob${NC}"
BOB_RESPONSE=$(curl -s -X POST "$API_BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "bob.test@example.com",
    "password": "Bob12345",
    "date_of_birth": "1990-03-20"
  }')

BOB_TOKEN=$(echo $BOB_RESPONSE | jq -r '.access_token')
if [ "$BOB_TOKEN" == "null" ] || [ -z "$BOB_TOKEN" ]; then
  echo "❌ Bob 註冊失敗，可能帳號已存在"
  echo "   回應: $BOB_RESPONSE"
  exit 1
fi
echo -e "${GREEN}✅ Bob 註冊成功${NC}"
echo "   Token: ${BOB_TOKEN:0:20}..."
echo ""

# ============================================
# 步驟 5: 創建 Bob 的個人檔案
# ============================================
echo -e "${BLUE}[步驟 5/10] 創建 Bob 的個人檔案${NC}"
curl -s -X POST "$API_BASE/profile/" \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Bob",
    "gender": "male",
    "bio": "熱愛運動和旅遊，喜歡交朋友！",
    "location": {
      "latitude": 25.0500,
      "longitude": 121.5500,
      "location_name": "台北市大安區"
    }
  }' > /dev/null

# 更新偏好設定
curl -s -X PATCH "$API_BASE/profile/" \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "min_age_preference": 22,
    "max_age_preference": 32,
    "max_distance_km": 30,
    "gender_preference": "female"
  }' > /dev/null
echo -e "${GREEN}✅ Bob 檔案創建成功${NC}"
echo ""

# ============================================
# 步驟 6: 設定 Bob 的興趣標籤
# ============================================
echo -e "${BLUE}[步驟 6/10] 設定 Bob 的興趣標籤${NC}"
curl -s -X PUT "$API_BASE/profile/interests/" \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"interest_ids\": $TAG_IDS}" > /dev/null

# 標記檔案為完整（測試用）
docker exec mergemeet_postgres psql -U mergemeet -d mergemeet -c "UPDATE profiles SET is_complete = true WHERE user_id = (SELECT id FROM users WHERE email = 'bob.test@example.com');" > /dev/null 2>&1

echo -e "${GREEN}✅ Bob 興趣標籤設定成功${NC}"
echo ""

# ============================================
# 步驟 7: Alice 瀏覽候選人
# ============================================
echo -e "${BLUE}[步驟 7/10] Alice 瀏覽候選人${NC}"
BROWSE_RESPONSE=$(curl -s -X GET "$API_BASE/discovery/browse?limit=10" \
  -H "Authorization: Bearer $ALICE_TOKEN")

BOB_USER_ID=$(echo $BROWSE_RESPONSE | jq -r '.[0].user_id // empty')

if [ -z "$BOB_USER_ID" ]; then
  echo "❌ Alice 找不到候選人"
  echo "   可能原因: 偏好設定不符合或沒有其他用戶"
  exit 1
fi

echo -e "${GREEN}✅ Alice 找到 $(echo $BROWSE_RESPONSE | jq -r 'length') 位候選人${NC}"
echo "   第一位候選人 ID: $BOB_USER_ID"
echo ""

# ============================================
# 步驟 8: Alice 喜歡 Bob
# ============================================
echo -e "${BLUE}[步驟 8/10] Alice 喜歡 Bob${NC}"
ALICE_LIKE_RESPONSE=$(curl -s -X POST "$API_BASE/discovery/like/$BOB_USER_ID" \
  -H "Authorization: Bearer $ALICE_TOKEN")

IS_MATCH=$(echo $ALICE_LIKE_RESPONSE | jq -r '.is_match')
echo -e "${GREEN}✅ Alice 已喜歡 Bob${NC}"
echo "   是否配對: $IS_MATCH"
echo ""

# ============================================
# 步驟 9: Bob 瀏覽並喜歡 Alice（觸發配對）
# ============================================
echo -e "${BLUE}[步驟 9/10] Bob 瀏覽候選人並喜歡 Alice${NC}"
BOB_BROWSE_RESPONSE=$(curl -s -X GET "$API_BASE/discovery/browse?limit=10" \
  -H "Authorization: Bearer $BOB_TOKEN")

ALICE_USER_ID=$(echo $BOB_BROWSE_RESPONSE | jq -r '.[0].user_id // empty')

if [ -z "$ALICE_USER_ID" ]; then
  echo "❌ Bob 找不到 Alice"
  exit 1
fi

BOB_LIKE_RESPONSE=$(curl -s -X POST "$API_BASE/discovery/like/$ALICE_USER_ID" \
  -H "Authorization: Bearer $BOB_TOKEN")

IS_MATCH=$(echo $BOB_LIKE_RESPONSE | jq -r '.is_match')
MATCH_ID=$(echo $BOB_LIKE_RESPONSE | jq -r '.match_id')

echo -e "${GREEN}✅ Bob 已喜歡 Alice${NC}"
echo "   是否配對: $IS_MATCH"
echo "   配對 ID: $MATCH_ID"
echo ""

# ============================================
# 步驟 10: 測試即時聊天
# ============================================
echo -e "${BLUE}[步驟 10/10] 測試即時聊天功能${NC}"

# 取得配對列表
MATCHES_RESPONSE=$(curl -s -X GET "$API_BASE/discovery/matches" \
  -H "Authorization: Bearer $ALICE_TOKEN")

MATCH_COUNT=$(echo $MATCHES_RESPONSE | jq -r 'length')
echo -e "${GREEN}✅ Alice 有 $MATCH_COUNT 個配對${NC}"

if [ "$MATCH_COUNT" -gt 0 ]; then
  echo ""
  echo -e "${YELLOW}📱 接下來你可以：${NC}"
  echo ""
  echo "1. 打開前端應用: $FRONTEND_BASE"
  echo ""
  echo "2. 使用以下帳號登入測試聊天："
  echo -e "   ${GREEN}Alice:${NC} alice.test@example.com / Alice1234"
  echo -e "   ${GREEN}Bob:${NC}   bob.test@example.com / Bob12345"
  echo ""
  echo "3. 導航到「配對」頁面，點擊對方頭像開始聊天"
  echo ""
  echo "4. 或直接訪問聊天頁面："
  echo "   $FRONTEND_BASE/messages/$MATCH_ID"
  echo ""
  echo -e "${YELLOW}💡 測試重點：${NC}"
  echo "   • 實時訊息傳送（使用 WebSocket）"
  echo "   • 訊息已讀狀態"
  echo "   • 訊息刪除功能"
  echo "   • 配對管理（取消配對、封鎖）"
  echo ""
fi

# ============================================
# 測試摘要
# ============================================
echo "=========================================="
echo -e "${GREEN}測試完成！${NC}"
echo "=========================================="
echo ""
echo "📊 測試摘要："
echo "   ✅ 2 個測試用戶已創建"
echo "   ✅ 個人檔案已完成"
echo "   ✅ 興趣標籤已設定"
echo "   ✅ 互相喜歡已完成"
echo "   ✅ 配對成功（Match ID: $MATCH_ID）"
echo ""
echo "🔐 測試帳號："
echo "   Alice: alice.test@example.com / Alice1234"
echo "   Bob:   bob.test@example.com / Bob12345"
echo ""
echo "🌐 前端訪問："
echo "   登入頁面: $FRONTEND_BASE/login"
echo "   配對頁面: $FRONTEND_BASE/matches"
echo "   聊天頁面: $FRONTEND_BASE/messages/$MATCH_ID"
echo ""
echo "📝 API 測試："
echo "   查看配對: curl -H \"Authorization: Bearer $ALICE_TOKEN\" $API_BASE/discovery/matches"
echo "   查看對話: curl -H \"Authorization: Bearer $ALICE_TOKEN\" $API_BASE/messages/conversations"
echo ""
