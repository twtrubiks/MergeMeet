#!/usr/bin/env python3
"""
測試用戶設置腳本
快速創建 Alice 和 Bob 帳號並自動配對，方便測試聊天功能

使用方法:
    python setup_test_users.py

要求:
    - 後端 API 運行在 http://localhost:8000
    - PostgreSQL 資料庫運行在 localhost:5432
"""

import requests
import psycopg2
from psycopg2.extras import DictCursor
import sys
from datetime import datetime

# 配置
API_BASE_URL = "http://localhost:8000"
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "mergemeet",
    "user": "mergemeet",
    "password": "mergemeet"
}

# 測試帳號資訊
USERS = [
    {
        "email": "alice@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01",
        "display_name": "Alice",
        "gender": "female",
        "bio": "Hi, I'm Alice! Love coffee and hiking ☕🏔️",
        "location_name": "Taipei, Taiwan",
        "latitude": 25.0330,
        "longitude": 121.5654,
        "min_age": 20,
        "max_age": 40,
        "max_distance_km": 50,
        "gender_preference": "male"
    },
    {
        "email": "bob@example.com",
        "password": "Password123",
        "date_of_birth": "1993-06-15",
        "display_name": "Bob",
        "gender": "male",
        "bio": "Hi, I'm Bob! Foodie and movie lover 🍕🎬",
        "location_name": "Taipei, Taiwan",
        "latitude": 25.0330,
        "longitude": 121.5654,
        "min_age": 20,
        "max_age": 40,
        "max_distance_km": 50,
        "gender_preference": "female"
    }
]


def print_header(text):
    """打印標題"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_success(text):
    """打印成功訊息"""
    print(f"✅ {text}")


def print_error(text):
    """打印錯誤訊息"""
    print(f"❌ {text}")


def print_info(text):
    """打印資訊"""
    print(f"ℹ️  {text}")


def get_db_connection():
    """連接資料庫"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print_error(f"資料庫連接失敗: {e}")
        return None


def cleanup_existing_users():
    """清理現有的測試帳號"""
    print_header("清理現有測試資料")

    conn = get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        # 獲取要刪除的用戶 ID
        cursor.execute(
            "SELECT id, email FROM users WHERE email IN (%s, %s)",
            (USERS[0]["email"], USERS[1]["email"])
        )
        existing_users = cursor.fetchall()

        if existing_users:
            print_info(f"發現 {len(existing_users)} 個現有測試帳號")
            for user_id, email in existing_users:
                print_info(f"  - {email}")

            # 刪除用戶（CASCADE 會自動刪除相關資料）
            cursor.execute(
                "DELETE FROM users WHERE email IN (%s, %s)",
                (USERS[0]["email"], USERS[1]["email"])
            )
            conn.commit()
            print_success(f"已刪除 {len(existing_users)} 個測試帳號及相關資料")
        else:
            print_info("沒有發現現有測試帳號")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print_error(f"清理失敗: {e}")
        if conn:
            conn.close()
        return False


def register_user(user_data):
    """註冊用戶"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/auth/register",
            json={
                "email": user_data["email"],
                "password": user_data["password"],
                "date_of_birth": user_data["date_of_birth"]
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print_success(f"註冊成功: {user_data['email']}")
            return data["access_token"]
        else:
            print_error(f"註冊失敗: {user_data['email']} - {response.text}")
            return None

    except Exception as e:
        print_error(f"註冊請求失敗: {e}")
        return None


def create_profile(user_data, access_token):
    """創建個人檔案"""
    try:
        headers = {"Authorization": f"Bearer {access_token}"}

        # 創建基本檔案
        response = requests.post(
            f"{API_BASE_URL}/api/profile",
            json={
                "display_name": user_data["display_name"],
                "gender": user_data["gender"],
                "bio": user_data["bio"],
                "location_name": user_data["location_name"],
                "latitude": user_data["latitude"],
                "longitude": user_data["longitude"]
            },
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            print_error(f"創建檔案失敗: {response.text}")
            return False

        # 設置配對偏好
        response = requests.patch(
            f"{API_BASE_URL}/api/profile",
            json={
                "min_age_preference": user_data["min_age"],
                "max_age_preference": user_data["max_age"],
                "max_distance_km": user_data["max_distance_km"],
                "gender_preference": user_data["gender_preference"]
            },
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            print_error(f"設置偏好失敗: {response.text}")
            return False

        print_success(f"個人檔案創建成功: {user_data['display_name']}")
        return True

    except Exception as e:
        print_error(f"創建檔案請求失敗: {e}")
        return False


def get_user_id(email):
    """獲取用戶 ID"""
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            return str(result[0])
        return None

    except Exception as e:
        print_error(f"獲取用戶 ID 失敗: {e}")
        if conn:
            conn.close()
        return None


def create_match_in_db(user1_id, user2_id):
    """直接在資料庫中創建配對"""
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        # 確保 user1_id < user2_id (資料庫約束)
        if user1_id > user2_id:
            user1_id, user2_id = user2_id, user1_id

        # 創建互相喜歡的記錄
        cursor.execute("""
            INSERT INTO likes (id, from_user_id, to_user_id, created_at)
            VALUES (gen_random_uuid(), %s, %s, NOW())
            ON CONFLICT DO NOTHING
        """, (user1_id, user2_id))

        cursor.execute("""
            INSERT INTO likes (id, from_user_id, to_user_id, created_at)
            VALUES (gen_random_uuid(), %s, %s, NOW())
            ON CONFLICT DO NOTHING
        """, (user2_id, user1_id))

        # 創建配對記錄
        cursor.execute("""
            INSERT INTO matches (id, user1_id, user2_id, status, matched_at)
            VALUES (gen_random_uuid(), %s, %s, 'ACTIVE', NOW())
            ON CONFLICT DO NOTHING
            RETURNING id
        """, (user1_id, user2_id))

        match_id = cursor.fetchone()
        conn.commit()

        cursor.close()
        conn.close()

        if match_id:
            print_success(f"配對創建成功: Match ID = {match_id[0]}")
            return True
        else:
            print_info("配對可能已存在")
            return True

    except Exception as e:
        print_error(f"創建配對失敗: {e}")
        if conn:
            conn.close()
        return False


def verify_setup():
    """驗證設置是否成功"""
    print_header("驗證設置")

    conn = get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor(cursor_factory=DictCursor)

        # 檢查用戶
        cursor.execute("""
            SELECT u.email, p.display_name, p.gender, p.is_complete
            FROM users u
            JOIN profiles p ON u.id = p.user_id
            WHERE u.email IN (%s, %s)
            ORDER BY u.email
        """, (USERS[0]["email"], USERS[1]["email"]))

        users = cursor.fetchall()

        if len(users) == 2:
            print_success("用戶和個人檔案設置完成:")
            for user in users:
                status = "完整" if user["is_complete"] else "未完整"
                print(f"  📝 {user['display_name']} ({user['email']}) - {user['gender']} - {status}")
        else:
            print_error(f"用戶數量不正確: {len(users)}/2")
            return False

        # 檢查配對
        cursor.execute("""
            SELECT m.id, m.status, m.matched_at,
                   u1.email as user1_email,
                   u2.email as user2_email
            FROM matches m
            JOIN users u1 ON m.user1_id = u1.id
            JOIN users u2 ON m.user2_id = u2.id
            WHERE (u1.email IN (%s, %s) OR u2.email IN (%s, %s))
              AND m.status = 'ACTIVE'
        """, (USERS[0]["email"], USERS[1]["email"], USERS[0]["email"], USERS[1]["email"]))

        matches = cursor.fetchall()

        if len(matches) == 1:
            match = matches[0]
            print_success("配對設置完成:")
            print(f"  💑 {match['user1_email']} ↔️  {match['user2_email']}")
            print(f"  🆔 Match ID: {match['id']}")
            print(f"  📅 配對時間: {match['matched_at']}")
        else:
            print_error(f"配對數量不正確: {len(matches)}/1")
            return False

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print_error(f"驗證失敗: {e}")
        if conn:
            conn.close()
        return False


def print_login_info():
    """打印登入資訊"""
    print_header("登入資訊")

    print("🌐 前端 URL: http://localhost:5173")
    print("📨 訊息頁面: http://localhost:5173/messages")
    print()

    for i, user in enumerate(USERS, 1):
        print(f"帳號 {i}: {user['display_name']}")
        print(f"  Email: {user['email']}")
        print(f"  密碼:  {user['password']}")
        print()

    print("💡 測試建議:")
    print("  1. 用 Alice 登入瀏覽器 A")
    print("  2. 用 Bob 登入瀏覽器 B (或無痕模式)")
    print("  3. 兩邊都前往「訊息」頁面")
    print("  4. 開始測試聊天功能！")
    print()


def main():
    """主函數"""
    print_header("MergeMeet 測試帳號設置工具")
    print("此腳本將創建 Alice 和 Bob 帳號並自動配對")
    print()

    # 1. 清理現有資料
    if not cleanup_existing_users():
        print_error("清理失敗，腳本終止")
        sys.exit(1)

    # 2. 註冊用戶並創建檔案
    print_header("創建測試帳號")

    user_ids = []
    for user_data in USERS:
        # 註冊
        access_token = register_user(user_data)
        if not access_token:
            print_error(f"無法註冊 {user_data['email']}，腳本終止")
            sys.exit(1)

        # 創建檔案
        if not create_profile(user_data, access_token):
            print_error(f"無法創建檔案 {user_data['email']}，腳本終止")
            sys.exit(1)

        # 獲取用戶 ID
        user_id = get_user_id(user_data["email"])
        if user_id:
            user_ids.append(user_id)
        else:
            print_error(f"無法獲取用戶 ID {user_data['email']}，腳本終止")
            sys.exit(1)

    # 3. 創建配對
    print_header("創建配對")

    if len(user_ids) == 2:
        if not create_match_in_db(user_ids[0], user_ids[1]):
            print_error("配對創建失敗，腳本終止")
            sys.exit(1)
    else:
        print_error("用戶 ID 數量不正確，腳本終止")
        sys.exit(1)

    # 4. 驗證
    if not verify_setup():
        print_error("驗證失敗")
        sys.exit(1)

    # 5. 打印登入資訊
    print_login_info()

    print_header("✅ 設置完成！")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  腳本已被用戶中斷")
        sys.exit(1)
    except Exception as e:
        print_error(f"未預期的錯誤: {e}")
        sys.exit(1)
