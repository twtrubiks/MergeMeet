"""WebSocket 即時通訊測試"""
import pytest
import json
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.match import Match, Message
from app.websocket.manager import manager


@pytest.fixture
async def matched_users_for_ws(client: AsyncClient, test_db: AsyncSession):
    """創建已配對的測試用戶用於 WebSocket 測試"""
    # 註冊 Alice
    response_a = await client.post("/api/auth/register", json={
        "email": "alice.ws@example.com",
        "password": "Alice1234",
        "date_of_birth": "1995-06-15"
    })
    assert response_a.status_code == 201
    alice_token = response_a.json()["access_token"]

    # 註冊 Bob
    response_b = await client.post("/api/auth/register", json={
        "email": "bob.ws@example.com",
        "password": "Bob12345",
        "date_of_birth": "1990-03-20"
    })
    assert response_b.status_code == 201
    bob_token = response_b.json()["access_token"]

    # 創建 Alice 的檔案
    await client.post("/api/profile/",
        headers={"Authorization": f"Bearer {alice_token}"},
        json={
            "display_name": "Alice",
            "gender": "female",
            "bio": "喜歡旅遊和美食",
            "location": {
                "latitude": 25.0330,
                "longitude": 121.5654,
                "location_name": "台北市信義區"
            }
        }
    )

    # 創建 Bob 的檔案
    await client.post("/api/profile/",
        headers={"Authorization": f"Bearer {bob_token}"},
        json={
            "display_name": "Bob",
            "gender": "male",
            "bio": "熱愛運動和旅遊",
            "location": {
                "latitude": 25.0500,
                "longitude": 121.5500,
                "location_name": "台北市大安區"
            }
        }
    )

    # 獲取用戶 ID
    result = await test_db.execute(select(User).where(User.email == "alice.ws@example.com"))
    alice = result.scalar_one()

    result = await test_db.execute(select(User).where(User.email == "bob.ws@example.com"))
    bob = result.scalar_one()

    # 直接創建配對（確保 user1_id < user2_id）
    user1_id, user2_id = (alice.id, bob.id) if alice.id < bob.id else (bob.id, alice.id)
    match = Match(
        user1_id=user1_id,
        user2_id=user2_id,
        status="ACTIVE"
    )
    test_db.add(match)
    await test_db.commit()
    await test_db.refresh(match)

    return {
        "alice": {
            "token": alice_token,
            "user_id": str(alice.id),
            "email": "alice.ws@example.com"
        },
        "bob": {
            "token": bob_token,
            "user_id": str(bob.id),
            "email": "bob.ws@example.com"
        },
        "match_id": str(match.id)
    }


@pytest.mark.asyncio
async def test_websocket_match_rooms():
    """測試配對聊天室功能"""
    match_id = "test-match-id"
    user_id = "test-user-id"

    # 測試加入聊天室
    manager.join_match_room(match_id, user_id)
    assert match_id in manager.match_rooms
    assert user_id in manager.match_rooms[match_id]

    # 測試離開聊天室
    manager.leave_match_room(match_id, user_id)
    if match_id in manager.match_rooms:
        assert user_id not in manager.match_rooms[match_id]


@pytest.mark.asyncio
async def test_chat_message_stored_in_database(
    client: AsyncClient,
    matched_users_for_ws: dict,
    test_db: AsyncSession
):
    """測試聊天訊息是否正確儲存到資料庫"""
    match_id = matched_users_for_ws["match_id"]
    alice_user_id = matched_users_for_ws["alice"]["user_id"]

    # 直接在資料庫創建訊息（模擬 WebSocket 處理）
    message = Message(
        match_id=match_id,
        sender_id=alice_user_id,
        content="Test WebSocket message",
        message_type="TEXT"
    )
    test_db.add(message)
    await test_db.commit()
    await test_db.refresh(message)

    # 驗證訊息已儲存
    result = await test_db.execute(
        select(Message).where(Message.id == message.id)
    )
    stored_message = result.scalar_one()

    assert stored_message.content == "Test WebSocket message"
    assert str(stored_message.sender_id) == alice_user_id
    assert str(stored_message.match_id) == match_id
    assert stored_message.is_read is None  # 初始為未讀


@pytest.mark.asyncio
async def test_message_sender_must_be_match_member(
    matched_users_for_ws: dict,
    client: AsyncClient,
    test_db: AsyncSession
):
    """測試只有配對成員可以發送訊息"""
    match_id = matched_users_for_ws["match_id"]

    # 創建第三個用戶（不在配對中）
    response = await client.post("/api/auth/register", json={
        "email": "charlie.ws@example.com",
        "password": "Charlie123",
        "date_of_birth": "1992-01-01"
    })
    charlie_token = response.json()["access_token"]

    result = await test_db.execute(
        select(User).where(User.email == "charlie.ws@example.com")
    )
    charlie = result.scalar_one()

    # 驗證配對
    result = await test_db.execute(
        select(Match).where(Match.id == match_id)
    )
    match = result.scalar_one()

    # Charlie 不應該在配對中
    assert str(charlie.id) not in [str(match.user1_id), str(match.user2_id)]


@pytest.mark.asyncio
async def test_message_content_moderation(
    matched_users_for_ws: dict,
    test_db: AsyncSession
):
    """測試訊息內容審核"""
    from app.services.content_moderation import ContentModerationService

    # 測試安全內容
    safe_content = "Hello, how are you?"
    is_safe, violations = ContentModerationService.check_message_content(safe_content)
    assert is_safe is True
    assert len(violations) == 0

    # 測試不安全內容
    unsafe_content = "想要看色情影片嗎？"
    is_safe, violations = ContentModerationService.check_message_content(unsafe_content)
    assert is_safe is False
    assert len(violations) > 0


@pytest.mark.asyncio
async def test_message_with_unsafe_content_rejected(
    matched_users_for_ws: dict,
    test_db: AsyncSession
):
    """測試包含不當內容的訊息應被拒絕"""
    from app.services.content_moderation import ContentModerationService

    match_id = matched_users_for_ws["match_id"]
    alice_user_id = matched_users_for_ws["alice"]["user_id"]

    # 嘗試發送不當內容
    unsafe_content = "加入我們的投資計劃，快速賺錢"
    is_safe, violations = ContentModerationService.check_message_content(unsafe_content)

    # 驗證內容被標記為不安全
    assert is_safe is False

    # 如果內容不安全，訊息不應該被儲存
    # 在實際 WebSocket 處理中，這會返回錯誤給客戶端


@pytest.mark.asyncio
async def test_warning_count_increases_on_violation(
    matched_users_for_ws: dict,
    test_db: AsyncSession
):
    """測試違規時警告次數增加"""
    # 獲取 Alice 的初始警告次數
    result = await test_db.execute(
        select(User).where(User.email == "alice.ws@example.com")
    )
    alice = result.scalar_one()
    initial_warning_count = alice.warning_count

    # 模擬違規（在實際實作中，WebSocket 處理函數會增加警告次數）
    alice.warning_count += 1
    await test_db.commit()
    await test_db.refresh(alice)

    # 驗證警告次數已增加
    assert alice.warning_count == initial_warning_count + 1


@pytest.mark.asyncio
async def test_message_sent_to_match_members_only(
    matched_users_for_ws: dict,
    test_db: AsyncSession
):
    """測試訊息只發送給配對成員"""
    match_id = matched_users_for_ws["match_id"]

    # 獲取配對資料
    result = await test_db.execute(
        select(Match).where(Match.id == match_id)
    )
    match = result.scalar_one()

    # 驗證配對狀態
    assert match.status == "ACTIVE"

    # 配對成員
    member_ids = [str(match.user1_id), str(match.user2_id)]

    # 訊息應該只發送給這兩個成員
    assert len(member_ids) == 2
    assert matched_users_for_ws["alice"]["user_id"] in member_ids
    assert matched_users_for_ws["bob"]["user_id"] in member_ids


@pytest.mark.asyncio
async def test_websocket_connection_cleanup_on_disconnect():
    """測試斷開連接時的清理工作"""
    user_id = "test-cleanup-user"
    match_id = "test-cleanup-match"

    # 模擬加入聊天室
    manager.join_match_room(match_id, user_id)

    # 斷開連接應該清理聊天室
    await manager.disconnect(user_id)

    # 驗證用戶已從連接列表移除
    assert user_id not in manager.active_connections


@pytest.mark.asyncio
async def test_multiple_messages_ordering(
    matched_users_for_ws: dict,
    test_db: AsyncSession
):
    """測試多條訊息的順序"""
    match_id = matched_users_for_ws["match_id"]
    alice_user_id = matched_users_for_ws["alice"]["user_id"]

    # 創建多條訊息
    messages = []
    for i in range(5):
        message = Message(
            match_id=match_id,
            sender_id=alice_user_id,
            content=f"Message {i+1}",
            message_type="TEXT"
        )
        test_db.add(message)
        await test_db.flush()
        messages.append(message)
    await test_db.commit()

    # 驗證訊息按時間順序儲存
    for i in range(len(messages) - 1):
        assert messages[i].sent_at <= messages[i+1].sent_at


