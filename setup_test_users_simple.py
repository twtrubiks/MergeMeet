#!/usr/bin/env python3
"""
MergeMeet 測試帳號快速設置腳本
創建 Alice 和 Bob 帳號並自動配對

使用方法: python3 setup_test_users_simple.py
要求: 後端 API 運行在 http://localhost:8000
"""

import requests
import subprocess
import sys
import json

API_BASE = "http://localhost:8000"
DB_CONTAINER = "mergemeet_postgres"

# 測試帳號
USERS = {
    "alice": {
        "email": "alice@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01",
        "display_name": "Alice",
        "gender": "female",
        "bio": "Hi, I'm Alice! Love coffee and hiking ☕🏔️",
        "gender_preference": "male"
    },
    "bob": {
        "email": "bob@example.com",
        "password": "Password123",
        "date_of_birth": "1993-06-15",
        "display_name": "Bob",
        "gender": "male",
        "bio": "Hi, I'm Bob! Foodie and movie lover 🍕🎬",
        "gender_preference": "female"
    }
}

COMMON = {
    "location_name": "Taipei, Taiwan",
    "latitude": 25.0330,
    "longitude": 121.5654,
    "min_age_preference": 20,
    "max_age_preference": 40,
    "max_distance_km": 50
}


def run_sql(sql):
    """執行 SQL 命令"""
    cmd = [
        "docker", "exec", DB_CONTAINER,
        "psql", "-U", "mergemeet", "-d", "mergemeet",
        "-t", "-c", sql
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()


def cleanup():
    """清理現有測試帳號"""
    print("\n" + "="*60)
    print("  清理現有測試資料")
    print("="*60 + "\n")

    sql = f"DELETE FROM users WHERE email IN ('{USERS['alice']['email']}', '{USERS['bob']['email']}');"
    run_sql(sql)
    print("✅ 清理完成\n")


def register_and_create_profile(user_key):
    """註冊用戶並創建個人檔案"""
    user = USERS[user_key]

    print(f"📝 創建用戶: {user['display_name']} ({user['email']})")

    # 1. 註冊
    try:
        response = requests.post(
            f"{API_BASE}/api/auth/register",
            json={
                "email": user["email"],
                "password": user["password"],
                "date_of_birth": user["date_of_birth"]
            },
            timeout=10
        )

        if response.status_code not in [200, 201]:
            print(f"❌ 註冊失敗: {response.text}")
            return None

        token = response.json()["access_token"]
        print(f"  ✅ 註冊成功")

    except Exception as e:
        print(f"❌ 註冊錯誤: {e}")
        return None

    # 2. 創建個人檔案
    try:
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.post(
            f"{API_BASE}/api/profile",
            json={
                "display_name": user["display_name"],
                "gender": user["gender"],
                "bio": user["bio"],
                "location_name": COMMON["location_name"],
                "latitude": COMMON["latitude"],
                "longitude": COMMON["longitude"]
            },
            headers=headers,
            timeout=10
        )

        if response.status_code not in range(200, 300):
            print(f"❌ 創建檔案失敗: {response.text}")
            return None

        print(f"  ✅ 個人檔案創建成功")

    except Exception as e:
        print(f"❌ 創建檔案錯誤: {e}")
        return None

    # 3. 設置配對偏好
    try:
        response = requests.patch(
            f"{API_BASE}/api/profile",
            json={
                "min_age_preference": COMMON["min_age_preference"],
                "max_age_preference": COMMON["max_age_preference"],
                "max_distance_km": COMMON["max_distance_km"],
                "gender_preference": user["gender_preference"]
            },
            headers=headers,
            timeout=10
        )

        if response.status_code not in range(200, 300):
            print(f"❌ 設置偏好失敗: {response.text}")
            return None

        print(f"  ✅ 配對偏好設置完成")

    except Exception as e:
        print(f"❌ 設置偏好錯誤: {e}")
        return None

    # 獲取用戶 ID
    sql = f"SELECT id FROM users WHERE email = '{user['email']}';"
    user_id = run_sql(sql)

    return user_id


def create_match(alice_id, bob_id):
    """創建配對"""
    print("\n" + "="*60)
    print("  創建配對")
    print("="*60 + "\n")

    # 確保 user1_id < user2_id
    if alice_id > bob_id:
        user1_id, user2_id = bob_id, alice_id
    else:
        user1_id, user2_id = alice_id, bob_id

    # 創建互相喜歡
    sql1 = f"""
        INSERT INTO likes (id, from_user_id, to_user_id, created_at)
        VALUES (gen_random_uuid(), '{alice_id}', '{bob_id}', NOW())
        ON CONFLICT DO NOTHING;
    """
    sql2 = f"""
        INSERT INTO likes (id, from_user_id, to_user_id, created_at)
        VALUES (gen_random_uuid(), '{bob_id}', '{alice_id}', NOW())
        ON CONFLICT DO NOTHING;
    """
    run_sql(sql1)
    run_sql(sql2)

    # 創建配對
    sql3 = f"""
        INSERT INTO matches (id, user1_id, user2_id, status, matched_at)
        VALUES (gen_random_uuid(), '{user1_id}', '{user2_id}', 'ACTIVE', NOW())
        ON CONFLICT DO NOTHING
        RETURNING id;
    """
    match_id = run_sql(sql3)

    if match_id:
        print(f"✅ 配對創建成功")
        print(f"   Match ID: {match_id}")
    else:
        print("ℹ️  配對可能已存在")


def verify():
    """驗證設置"""
    print("\n" + "="*60)
    print("  驗證設置")
    print("="*60 + "\n")

    # 檢查用戶和檔案
    sql = f"""
        SELECT u.email, p.display_name, p.gender, p.is_complete
        FROM users u
        JOIN profiles p ON u.id = p.user_id
        WHERE u.email IN ('{USERS['alice']['email']}', '{USERS['bob']['email']}')
        ORDER BY u.email;
    """
    cmd = [
        "docker", "exec", DB_CONTAINER,
        "psql", "-U", "mergemeet", "-d", "mergemeet",
        "-c", sql
    ]
    subprocess.run(cmd)

    # 檢查配對
    sql = f"""
        SELECT m.id as match_id,
               u1.email as user1_email,
               u2.email as user2_email,
               m.status
        FROM matches m
        JOIN users u1 ON m.user1_id = u1.id
        JOIN users u2 ON m.user2_id = u2.id
        WHERE (u1.email IN ('{USERS['alice']['email']}', '{USERS['bob']['email']}')
           OR u2.email IN ('{USERS['alice']['email']}', '{USERS['bob']['email']}'))
          AND m.status = 'ACTIVE';
    """
    cmd = [
        "docker", "exec", DB_CONTAINER,
        "psql", "-U", "mergemeet", "-d", "mergemeet",
        "-c", sql
    ]
    subprocess.run(cmd)


def print_login_info():
    """打印登入資訊"""
    print("\n" + "="*60)
    print("  登入資訊")
    print("="*60 + "\n")

    print("🌐 前端 URL: http://localhost:5173")
    print("📨 訊息頁面: http://localhost:5173/messages\n")

    for i, (key, user) in enumerate(USERS.items(), 1):
        print(f"帳號 {i}: {user['display_name']}")
        print(f"  Email: {user['email']}")
        print(f"  密碼:  {user['password']}\n")

    print("💡 測試建議:")
    print("  1. 用 Alice 登入瀏覽器 A")
    print("  2. 用 Bob 登入瀏覽器 B (或無痕模式)")
    print("  3. 兩邊都前往「訊息」頁面")
    print("  4. 開始測試聊天功能！\n")


def main():
    """主函數"""
    print("\n" + "="*60)
    print("  MergeMeet 測試帳號設置工具")
    print("="*60)
    print("此腳本將創建 Alice 和 Bob 帳號並自動配對\n")

    # 1. 清理
    cleanup()

    # 2. 創建用戶
    print("="*60)
    print("  創建測試帳號")
    print("="*60 + "\n")

    alice_id = register_and_create_profile("alice")
    if not alice_id:
        print("\n❌ Alice 創建失敗")
        sys.exit(1)

    print()
    bob_id = register_and_create_profile("bob")
    if not bob_id:
        print("\n❌ Bob 創建失敗")
        sys.exit(1)

    # 3. 創建配對
    create_match(alice_id, bob_id)

    # 4. 驗證
    verify()

    # 5. 登入資訊
    print_login_info()

    print("="*60)
    print("  ✅ 設置完成！")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  腳本已被用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
