#!/bin/bash
#
# MergeMeet 測試帳號設置腳本
# 快速創建 Alice 和 Bob 帳號並自動配對，方便測試聊天功能
#
# 使用方法:
#     ./setup_test_users.sh
#
# 要求:
#     - 後端 API 運行在 http://localhost:8000
#     - PostgreSQL 容器名稱為 mergemeet_postgres
#

set -e  # 遇到錯誤立即停止

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
API_BASE_URL="http://localhost:8000"
DB_CONTAINER="mergemeet_postgres"
DB_USER="mergemeet"
DB_NAME="mergemeet"

# 測試帳號資訊
ALICE_EMAIL="alice@example.com"
ALICE_PASSWORD="Password123"
ALICE_DOB="1995-01-01"
ALICE_NAME="Alice"
ALICE_GENDER="female"
ALICE_BIO="Hi, I'm Alice! Love coffee and hiking ☕🏔️"

BOB_EMAIL="bob@example.com"
BOB_PASSWORD="Password123"
BOB_DOB="1993-06-15"
BOB_NAME="Bob"
BOB_GENDER="male"
BOB_BIO="Hi, I'm Bob! Foodie and movie lover 🍕🎬"

# 共用設置
LOCATION_NAME="Taipei, Taiwan"
LATITUDE=25.0330
LONGITUDE=121.5654
MIN_AGE=20
MAX_AGE=40
MAX_DISTANCE=50

# 函數定義
print_header() {
    echo -e "\n${BLUE}============================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}============================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

check_prerequisites() {
    print_header "檢查前置條件"

    # 檢查 API 是否運行
    if curl -s -f "${API_BASE_URL}/docs" > /dev/null 2>&1; then
        print_success "後端 API 正在運行"
    else
        print_error "後端 API 未運行，請先啟動: cd backend && uvicorn app.main:app --reload"
        exit 1
    fi

    # 檢查資料庫容器
    if docker ps | grep -q ${DB_CONTAINER}; then
        print_success "資料庫容器正在運行"
    else
        print_error "資料庫容器未運行，請先啟動: docker compose up -d"
        exit 1
    fi
}

cleanup_existing_users() {
    print_header "清理現有測試資料"

    # 檢查是否存在測試帳號
    EXISTING=$(docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -t -c \
        "SELECT COUNT(*) FROM users WHERE email IN ('${ALICE_EMAIL}', '${BOB_EMAIL}');")

    if [ "${EXISTING}" -gt 0 ]; then
        print_info "發現 ${EXISTING} 個現有測試帳號，正在刪除..."

        docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -c \
            "DELETE FROM users WHERE email IN ('${ALICE_EMAIL}', '${BOB_EMAIL}');" > /dev/null

        print_success "已刪除現有測試帳號及相關資料"
    else
        print_info "沒有發現現有測試帳號"
    fi
}

register_user() {
    local email=$1
    local password=$2
    local dob=$3
    local display_name=$4

    print_info "註冊用戶: ${display_name} (${email})"

    RESPONSE=$(curl -s -X POST "${API_BASE_URL}/api/auth/register" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"${email}\",\"password\":\"${password}\",\"date_of_birth\":\"${dob}\"}")

    # 檢查是否成功
    if echo "${RESPONSE}" | grep -q "access_token"; then
        TOKEN=$(echo "${RESPONSE}" | grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//')
        print_success "註冊成功: ${display_name}"
        echo "${TOKEN}"
    else
        print_error "註冊失敗: ${display_name}"
        echo "${RESPONSE}"
        exit 1
    fi
}

create_profile() {
    local token=$1
    local display_name=$2
    local gender=$3
    local bio=$4

    print_info "創建個人檔案: ${display_name}"

    # 創建基本檔案
    RESPONSE=$(curl -s -X POST "${API_BASE_URL}/api/profile" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${token}" \
        -d "{\"display_name\":\"${display_name}\",\"gender\":\"${gender}\",\"bio\":\"${bio}\",\"location_name\":\"${LOCATION_NAME}\",\"latitude\":${LATITUDE},\"longitude\":${LONGITUDE}}")

    if echo "${RESPONSE}" | grep -q "id"; then
        print_success "個人檔案創建成功: ${display_name}"
    else
        print_error "個人檔案創建失敗: ${display_name}"
        echo "${RESPONSE}"
        exit 1
    fi

    # 設置配對偏好
    local gender_pref
    if [ "${gender}" == "female" ]; then
        gender_pref="male"
    else
        gender_pref="female"
    fi

    curl -s -X PATCH "${API_BASE_URL}/api/profile" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${token}" \
        -d "{\"min_age_preference\":${MIN_AGE},\"max_age_preference\":${MAX_AGE},\"max_distance_km\":${MAX_DISTANCE},\"gender_preference\":\"${gender_pref}\"}" > /dev/null

    print_success "配對偏好設置完成: ${display_name}"
}

create_match() {
    print_header "創建配對"

    # 獲取用戶 ID
    ALICE_ID=$(docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -t -c \
        "SELECT id FROM users WHERE email = '${ALICE_EMAIL}';" | tr -d ' ')

    BOB_ID=$(docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -t -c \
        "SELECT id FROM users WHERE email = '${BOB_EMAIL}';" | tr -d ' ')

    if [ -z "${ALICE_ID}" ] || [ -z "${BOB_ID}" ]; then
        print_error "無法獲取用戶 ID"
        exit 1
    fi

    # 確保 user1_id < user2_id
    if [[ "${ALICE_ID}" < "${BOB_ID}" ]]; then
        USER1_ID="${ALICE_ID}"
        USER2_ID="${BOB_ID}"
    else
        USER1_ID="${BOB_ID}"
        USER2_ID="${ALICE_ID}"
    fi

    # 創建互相喜歡的記錄
    docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -c \
        "INSERT INTO likes (id, from_user_id, to_user_id, created_at)
         VALUES (gen_random_uuid(), '${ALICE_ID}', '${BOB_ID}', NOW())
         ON CONFLICT DO NOTHING;" > /dev/null

    docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -c \
        "INSERT INTO likes (id, from_user_id, to_user_id, created_at)
         VALUES (gen_random_uuid(), '${BOB_ID}', '${ALICE_ID}', NOW())
         ON CONFLICT DO NOTHING;" > /dev/null

    # 創建配對記錄
    MATCH_ID=$(docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -t -c \
        "INSERT INTO matches (id, user1_id, user2_id, status, matched_at)
         VALUES (gen_random_uuid(), '${USER1_ID}', '${USER2_ID}', 'ACTIVE', NOW())
         ON CONFLICT DO NOTHING
         RETURNING id;" | tr -d ' ')

    if [ -n "${MATCH_ID}" ]; then
        print_success "配對創建成功"
        print_info "Match ID: ${MATCH_ID}"
    else
        print_info "配對可能已存在"
    fi
}

verify_setup() {
    print_header "驗證設置"

    # 檢查用戶和個人檔案
    USERS_COUNT=$(docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -t -c \
        "SELECT COUNT(*) FROM users u
         JOIN profiles p ON u.id = p.user_id
         WHERE u.email IN ('${ALICE_EMAIL}', '${BOB_EMAIL}');" | tr -d ' ')

    if [ "${USERS_COUNT}" -eq 2 ]; then
        print_success "用戶和個人檔案設置完成 (2/2)"

        # 顯示詳細資訊
        docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -c \
            "SELECT u.email, p.display_name, p.gender, p.is_complete
             FROM users u
             JOIN profiles p ON u.id = p.user_id
             WHERE u.email IN ('${ALICE_EMAIL}', '${BOB_EMAIL}')
             ORDER BY u.email;"
    else
        print_error "用戶數量不正確: ${USERS_COUNT}/2"
        exit 1
    fi

    # 檢查配對
    MATCHES_COUNT=$(docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -t -c \
        "SELECT COUNT(*) FROM matches m
         JOIN users u1 ON m.user1_id = u1.id
         JOIN users u2 ON m.user2_id = u2.id
         WHERE (u1.email IN ('${ALICE_EMAIL}', '${BOB_EMAIL}')
            OR u2.email IN ('${ALICE_EMAIL}', '${BOB_EMAIL}'))
           AND m.status = 'ACTIVE';" | tr -d ' ')

    if [ "${MATCHES_COUNT}" -eq 1 ]; then
        print_success "配對設置完成 (1/1)"

        # 顯示配對詳細資訊
        docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -c \
            "SELECT m.id as match_id,
                    u1.email as user1_email,
                    u2.email as user2_email,
                    m.status,
                    m.matched_at
             FROM matches m
             JOIN users u1 ON m.user1_id = u1.id
             JOIN users u2 ON m.user2_id = u2.id
             WHERE (u1.email IN ('${ALICE_EMAIL}', '${BOB_EMAIL}')
                OR u2.email IN ('${ALICE_EMAIL}', '${BOB_EMAIL}'))
               AND m.status = 'ACTIVE';"
    else
        print_error "配對數量不正確: ${MATCHES_COUNT}/1"
        exit 1
    fi
}

print_login_info() {
    print_header "登入資訊"

    echo "🌐 前端 URL: http://localhost:5173"
    echo "📨 訊息頁面: http://localhost:5173/messages"
    echo ""
    echo "帳號 1: ${ALICE_NAME}"
    echo "  Email: ${ALICE_EMAIL}"
    echo "  密碼:  ${ALICE_PASSWORD}"
    echo ""
    echo "帳號 2: ${BOB_NAME}"
    echo "  Email: ${BOB_EMAIL}"
    echo "  密碼:  ${BOB_PASSWORD}"
    echo ""
    echo "💡 測試建議:"
    echo "  1. 用 Alice 登入瀏覽器 A"
    echo "  2. 用 Bob 登入瀏覽器 B (或無痕模式)"
    echo "  3. 兩邊都前往「訊息」頁面"
    echo "  4. 開始測試聊天功能！"
    echo ""
}

# 主程序
main() {
    print_header "MergeMeet 測試帳號設置工具"
    echo "此腳本將創建 Alice 和 Bob 帳號並自動配對"

    # 1. 檢查前置條件
    check_prerequisites

    # 2. 清理現有資料
    cleanup_existing_users

    # 3. 註冊用戶並創建檔案
    print_header "創建測試帳號"

    ALICE_TOKEN=$(register_user "${ALICE_EMAIL}" "${ALICE_PASSWORD}" "${ALICE_DOB}" "${ALICE_NAME}")
    create_profile "${ALICE_TOKEN}" "${ALICE_NAME}" "${ALICE_GENDER}" "${ALICE_BIO}"

    BOB_TOKEN=$(register_user "${BOB_EMAIL}" "${BOB_PASSWORD}" "${BOB_DOB}" "${BOB_NAME}")
    create_profile "${BOB_TOKEN}" "${BOB_NAME}" "${BOB_GENDER}" "${BOB_BIO}"

    # 4. 創建配對
    create_match

    # 5. 驗證
    verify_setup

    # 6. 打印登入資訊
    print_login_info

    print_header "✅ 設置完成！"
}

# 執行主程序
main
