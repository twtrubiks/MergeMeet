"""
聊天訊息分頁測試腳本

用途: 清除並新增測試訊息，驗證 Cursor-based Pagination
執行: python -m scripts.test_pagination
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from uuid import UUID
from typing import Optional

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, func
import httpx

from app.core.config import settings
from app.core.database import engine, AsyncSessionLocal
from app.models.user import User
from app.models.match import Match, Message


async def login(client: httpx.AsyncClient, email: str, password: str) -> str:
    """登入並取得 JWT token"""
    response = await client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )

    if response.status_code != 200:
        raise Exception(f"登入失敗: {response.status_code} - {response.text}")

    data = response.json()
    return data["access_token"]


async def get_user_id(db: AsyncSession, email: str) -> UUID:
    """從資料庫查詢用戶 ID"""
    result = await db.execute(
        select(User.id).where(User.email == email)
    )
    user_id = result.scalar_one_or_none()
    if not user_id:
        raise Exception(f"找不到用戶: {email}")
    return user_id


async def get_match_id(db: AsyncSession, alice_id: UUID, bob_id: UUID) -> Optional[UUID]:
    """查詢 Alice 和 Bob 的配對 ID"""
    # 確保 user1_id < user2_id (Match 模型的約束)
    user1_id = min(alice_id, bob_id, key=lambda x: str(x))
    user2_id = max(alice_id, bob_id, key=lambda x: str(x))

    result = await db.execute(
        select(Match.id).where(
            and_(
                Match.user1_id == user1_id,
                Match.user2_id == user2_id
            )
        )
    )
    match_id = result.scalar_one_or_none()
    return match_id


async def clear_messages(db: AsyncSession, match_id: UUID) -> int:
    """刪除指定配對的所有訊息（硬刪除）"""
    result = await db.execute(
        delete(Message).where(Message.match_id == match_id)
    )
    await db.commit()
    return result.rowcount


async def create_test_messages(
    db: AsyncSession,
    match_id: UUID,
    alice_id: UUID,
    bob_id: UUID,
    count: int = 53
) -> int:
    """新增測試訊息（輪流發送）"""
    base_time = datetime.utcnow()
    messages = []

    for i in range(1, count + 1):
        # 奇數由 Alice 發送，偶數由 Bob 發送
        sender_id = alice_id if i % 2 == 1 else bob_id
        sender_name = "Alice" if i % 2 == 1 else "Bob"

        message = Message(
            match_id=match_id,
            sender_id=sender_id,
            content=f"[#{i:03d}] 測試訊息 - {sender_name}",
            message_type="TEXT",
            sent_at=base_time + timedelta(seconds=i)
        )
        messages.append(message)

    db.add_all(messages)
    await db.commit()
    return len(messages)


async def verify_pagination(client: httpx.AsyncClient, token: str, match_id: str) -> None:
    """驗證分頁功能"""
    print("\n" + "="*60)
    print("🔍 驗證分頁功能")
    print("="*60)

    # 第一頁（不傳 before_id）
    print("\n📄 測試第一頁...")
    response = await client.get(
        f"/api/messages/matches/{match_id}/messages",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code != 200:
        print(f"❌ 取得第一頁失敗: {response.status_code}")
        print(response.text)
        return

    page1 = response.json()

    # 驗證第一頁
    assert page1["total"] == 53, f"總數錯誤: 期望 53，實際 {page1['total']}"
    assert len(page1["messages"]) == 50, f"第一頁訊息數錯誤: 期望 50，實際 {len(page1['messages'])}"
    assert page1["has_more"] is True, "has_more 應該為 True"
    assert page1["next_cursor"] is not None, "next_cursor 不應該為 None"

    print(f"   ✅ 總訊息數: {page1['total']}")
    print(f"   ✅ 第一頁訊息數: {len(page1['messages'])}")
    print(f"   ✅ has_more: {page1['has_more']}")
    print(f"   ✅ 第一頁第一條: {page1['messages'][0]['content']}")
    print(f"   ✅ 第一頁最後一條: {page1['messages'][-1]['content']}")

    # 第二頁（傳入 next_cursor）
    print("\n📄 測試第二頁...")
    response = await client.get(
        f"/api/messages/matches/{match_id}/messages",
        params={"before_id": page1["next_cursor"]},
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code != 200:
        print(f"❌ 取得第二頁失敗: {response.status_code}")
        print(response.text)
        return

    page2 = response.json()

    # 驗證第二頁
    assert page2["total"] == 53, f"總數錯誤: 期望 53，實際 {page2['total']}"
    assert len(page2["messages"]) == 3, f"第二頁訊息數錯誤: 期望 3，實際 {len(page2['messages'])}"
    assert page2["has_more"] is False, "has_more 應該為 False"
    assert page2["next_cursor"] is None, "next_cursor 應該為 None"

    print(f"   ✅ 第二頁訊息數: {len(page2['messages'])}")
    print(f"   ✅ has_more: {page2['has_more']}")
    print(f"   ✅ next_cursor: {page2['next_cursor']}")
    print(f"   ✅ 第二頁第一條: {page2['messages'][0]['content']}")
    print(f"   ✅ 第二頁最後一條: {page2['messages'][-1]['content']}")

    print("\n✅ 分頁驗證通過！")


async def main():
    """主流程"""
    print("="*60)
    print("🚀 聊天訊息分頁測試腳本")
    print("="*60)

    base_url = "http://localhost:8000"

    async with httpx.AsyncClient(base_url=base_url) as client:
        # 1. 登入
        print("\n🔐 登入中...")
        try:
            alice_token = await login(client, "alice@example.com", "Test1234")
            bob_token = await login(client, "bob@example.com", "Test5678")
            print("   ✅ Alice 登入成功")
            print("   ✅ Bob 登入成功")
        except Exception as e:
            print(f"   ❌ 登入失敗: {e}")
            print("\n💡 提示: 請確保已建立測試帳號:")
            print("   - alice@example.com / Test1234")
            print("   - bob@example.com / Test5678")
            return

        # 2. 查詢用戶 ID 和配對
        async with AsyncSessionLocal() as db:
            print("\n👤 查詢用戶 ID...")
            alice_id = await get_user_id(db, "alice@example.com")
            bob_id = await get_user_id(db, "bob@example.com")
            print(f"   ✅ Alice ID: {alice_id}")
            print(f"   ✅ Bob ID: {bob_id}")

            # 3. 查詢 match_id
            print("\n💑 查詢配對...")
            match_id = await get_match_id(db, alice_id, bob_id)

            if not match_id:
                print("   ❌ 找不到配對")
                print("\n💡 提示: 請先讓 Alice 和 Bob 配對:")
                print("   1. 在瀏覽器中登入 Alice")
                print("   2. 探索用戶並喜歡 Bob")
                print("   3. 登入 Bob 並喜歡 Alice")
                return

            print(f"   ✅ Match ID: {match_id}")

            # 4. 清除舊訊息
            print("\n🗑️  清除舊訊息...")
            deleted = await clear_messages(db, match_id)
            print(f"   ✅ 已刪除 {deleted} 筆舊訊息")

            # 5. 新增 53 筆測試訊息
            print("\n📝 新增測試訊息...")
            created = await create_test_messages(db, match_id, alice_id, bob_id, 53)
            print(f"   ✅ 已新增 {created} 筆測試訊息")
            print(f"   - Alice 發送: 27 筆 (奇數編號)")
            print(f"   - Bob 發送: 26 筆 (偶數編號)")

        # 6. 驗證分頁
        await verify_pagination(client, alice_token, str(match_id))

    # 7. 輸出測試資訊
    print("\n" + "="*60)
    print("🎯 測試準備完成！")
    print("="*60)
    print(f"Match ID: {match_id}")
    print(f"訊息總數: 53")
    print(f"第一頁: 50 筆 (has_more=true)")
    print(f"第二頁: 3 筆 (has_more=false)")
    print("\n📱 請在瀏覽器中測試:")
    print("  視窗 A: alice@example.com / Test1234")
    print("  視窗 B: bob@example.com / Test5678")
    print("\n💡 測試步驟:")
    print("  1. 兩個視窗都登入並進入聊天室")
    print("  2. 應該看到最新的 50 條訊息 (#004-#053)")
    print("  3. 向上滾動觸發「載入更多」")
    print("  4. 應該載入最早的 3 條訊息 (#001-#003)")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
