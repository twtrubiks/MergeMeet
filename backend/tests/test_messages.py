"""聊天訊息 REST API 測試"""
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import AsyncMock, patch

from app.models.user import User
from app.models.match import Match, Message


@pytest.fixture
async def matched_users(client: AsyncClient, auth_user_pair: dict, test_db: AsyncSession):
    """創建已配對的測試用戶"""
    alice_token = auth_user_pair["alice"]["token"]
    bob_token = auth_user_pair["bob"]["token"]

    # 創建 Alice 的檔案（注意：URL 無尾隨斜線）
    await client.post("/api/profile",
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

    # 創建 Bob 的檔案（注意：URL 無尾隨斜線）
    await client.post("/api/profile",
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

    # 獲取用戶 ID（使用 auth_user_pair 的 email）
    result = await test_db.execute(select(User).where(User.email == auth_user_pair["alice"]["email"]))
    alice = result.scalar_one()

    result = await test_db.execute(select(User).where(User.email == auth_user_pair["bob"]["email"]))
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
        "alice": {"token": alice_token, "user_id": str(alice.id)},
        "bob": {"token": bob_token, "user_id": str(bob.id)},
        "match_id": str(match.id)
    }


@pytest.mark.asyncio
async def test_get_chat_history_empty(client: AsyncClient, matched_users: dict):
    """測試取得空的聊天記錄"""
    match_id = matched_users["match_id"]
    alice_token = matched_users["alice"]["token"]

    response = await client.get(
        f"/api/messages/matches/{match_id}/messages",
        headers={"Authorization": f"Bearer {alice_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["messages"] == []
    assert data["total"] == 0
    assert data["has_more"] is False
    assert data["next_cursor"] is None


@pytest.mark.asyncio
async def test_get_chat_history_with_messages(client: AsyncClient, matched_users: dict, test_db: AsyncSession):
    """測試取得有訊息的聊天記錄"""
    match_id = matched_users["match_id"]
    alice_token = matched_users["alice"]["token"]
    alice_user_id = matched_users["alice"]["user_id"]

    # 直接在資料庫創建訊息
    for i in range(5):
        message = Message(
            match_id=match_id,
            sender_id=alice_user_id,
            content=f"Test message {i+1}",
            message_type="TEXT"
        )
        test_db.add(message)
    await test_db.commit()

    # 取得聊天記錄
    response = await client.get(
        f"/api/messages/matches/{match_id}/messages",
        headers={"Authorization": f"Bearer {alice_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 5
    assert data["total"] == 5
    assert data["has_more"] is False
    assert data["next_cursor"] is None


@pytest.mark.asyncio
async def test_get_chat_history_cursor_pagination(client: AsyncClient, matched_users: dict, test_db: AsyncSession):
    """測試 cursor-based 聊天記錄分頁"""
    from datetime import datetime, timedelta

    match_id = matched_users["match_id"]
    alice_token = matched_users["alice"]["token"]
    alice_user_id = matched_users["alice"]["user_id"]

    # 創建 15 條訊息（確保有時間間隔以便排序）
    base_time = datetime.now()
    for i in range(15):
        message = Message(
            match_id=match_id,
            sender_id=alice_user_id,
            content=f"Test message {i+1}",
            message_type="TEXT"
        )
        # 手動設置 sent_at 確保順序
        message.sent_at = base_time + timedelta(seconds=i)
        test_db.add(message)
        await test_db.flush()
    await test_db.commit()

    # 初次載入（不傳 before_id）- 取最新 10 條
    response = await client.get(
        f"/api/messages/matches/{match_id}/messages?limit=10",
        headers={"Authorization": f"Bearer {alice_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 10
    assert data["total"] == 15
    assert data["has_more"] is True
    assert data["next_cursor"] is not None

    # 驗證訊息順序（舊的在前）- 最新 10 條是 message 6-15
    assert data["messages"][0]["content"] == "Test message 6"
    assert data["messages"][-1]["content"] == "Test message 15"

    # 載入更多（使用 cursor）- 應該取到剩餘 5 條
    next_cursor = data["next_cursor"]
    response = await client.get(
        f"/api/messages/matches/{match_id}/messages?before_id={next_cursor}&limit=10",
        headers={"Authorization": f"Bearer {alice_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 5
    assert data["has_more"] is False
    assert data["next_cursor"] is None

    # 驗證訊息順序
    assert data["messages"][0]["content"] == "Test message 1"
    assert data["messages"][-1]["content"] == "Test message 5"


@pytest.mark.asyncio
async def test_get_chat_history_invalid_cursor(client: AsyncClient, matched_users: dict, test_db: AsyncSession):
    """測試無效 cursor 的情況"""
    match_id = matched_users["match_id"]
    alice_token = matched_users["alice"]["token"]
    alice_user_id = matched_users["alice"]["user_id"]

    # 創建一些訊息
    for i in range(5):
        message = Message(
            match_id=match_id,
            sender_id=alice_user_id,
            content=f"Test message {i+1}",
            message_type="TEXT"
        )
        test_db.add(message)
    await test_db.commit()

    # 使用不存在的 cursor
    fake_cursor = "00000000-0000-0000-0000-000000000000"
    response = await client.get(
        f"/api/messages/matches/{match_id}/messages?before_id={fake_cursor}",
        headers={"Authorization": f"Bearer {alice_token}"}
    )

    # 應該返回最新訊息（cursor 不存在時忽略條件）
    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 5


@pytest.mark.asyncio
async def test_get_chat_history_boundary(client: AsyncClient, matched_users: dict, test_db: AsyncSession):
    """測試邊界條件：訊息數量剛好等於 limit"""
    match_id = matched_users["match_id"]
    alice_token = matched_users["alice"]["token"]
    alice_user_id = matched_users["alice"]["user_id"]

    # 創建剛好 10 條訊息
    for i in range(10):
        message = Message(
            match_id=match_id,
            sender_id=alice_user_id,
            content=f"Test message {i+1}",
            message_type="TEXT"
        )
        test_db.add(message)
    await test_db.commit()

    # 請求 limit=10
    response = await client.get(
        f"/api/messages/matches/{match_id}/messages?limit=10",
        headers={"Authorization": f"Bearer {alice_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 10
    assert data["has_more"] is False
    assert data["next_cursor"] is None


@pytest.mark.asyncio
async def test_get_chat_history_unauthorized(client: AsyncClient, matched_users: dict):
    """測試未授權用戶無法查看聊天記錄"""
    # 創建第三個用戶
    response = await client.post("/api/auth/register", json={
        "email": "charlie@example.com",
        "password": "Charlie123",
        "date_of_birth": "1992-01-01"
    })
    charlie_token = response.json()["access_token"]
    # 清除 cookies，讓測試使用純 Bearer Token 認證
    client.cookies.clear()

    match_id = matched_users["match_id"]

    # Charlie 嘗試查看 Alice 和 Bob 的聊天記錄
    response = await client.get(
        f"/api/messages/matches/{match_id}/messages",
        headers={"Authorization": f"Bearer {charlie_token}"}
    )

    assert response.status_code == 404
    assert "不存在或您無權查看" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_conversations_empty(client: AsyncClient, matched_users: dict):
    """測試取得空的對話列表"""
    alice_token = matched_users["alice"]["token"]

    response = await client.get(
        "/api/messages/conversations",
        headers={"Authorization": f"Bearer {alice_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # 應該有一個配對但沒有訊息
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_conversations_with_messages(client: AsyncClient, matched_users: dict, test_db: AsyncSession):
    """測試取得有訊息的對話列表"""
    match_id = matched_users["match_id"]
    alice_token = matched_users["alice"]["token"]
    bob_user_id = matched_users["bob"]["user_id"]

    # Bob 發送訊息給 Alice
    message = Message(
        match_id=match_id,
        sender_id=bob_user_id,
        content="Hello Alice!",
        message_type="TEXT"
    )
    test_db.add(message)
    await test_db.commit()
    await test_db.refresh(message)

    # Alice 查看對話列表
    response = await client.get(
        "/api/messages/conversations",
        headers={"Authorization": f"Bearer {alice_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1

    # 檢查第一個對話
    conversation = data[0]
    assert "match_id" in conversation
    assert "other_user_id" in conversation
    assert "other_user_name" in conversation
    assert "last_message" in conversation
    # ✅ 檢查 last_message 是否為 None 再訪問
    assert conversation["last_message"] is not None, "last_message 應該不為 None"
    assert conversation["last_message"]["content"] == "Hello Alice!"
    assert "unread_count" in conversation


@pytest.mark.asyncio
async def test_get_conversations_unread_count(client: AsyncClient, matched_users: dict, test_db: AsyncSession):
    """測試對話列表的未讀訊息計數"""
    match_id = matched_users["match_id"]
    alice_token = matched_users["alice"]["token"]
    bob_user_id = matched_users["bob"]["user_id"]

    # Bob 發送 3 條訊息給 Alice
    for i in range(3):
        message = Message(
            match_id=match_id,
            sender_id=bob_user_id,
            content=f"Message {i+1}",
            message_type="TEXT"
        )
        test_db.add(message)
    await test_db.commit()

    # Alice 查看對話列表
    response = await client.get(
        "/api/messages/conversations",
        headers={"Authorization": f"Bearer {alice_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    conversation = data[0]
    assert conversation["unread_count"] == 3


@pytest.mark.asyncio
async def test_mark_messages_as_read(client: AsyncClient, matched_users: dict, test_db: AsyncSession):
    """測試標記訊息為已讀"""
    match_id = matched_users["match_id"]
    alice_token = matched_users["alice"]["token"]
    bob_user_id = matched_users["bob"]["user_id"]

    # Bob 發送訊息給 Alice
    message = Message(
        match_id=match_id,
        sender_id=bob_user_id,
        content="Hello Alice!",
        message_type="TEXT"
    )
    test_db.add(message)
    await test_db.commit()
    await test_db.refresh(message)

    # 確認訊息未讀
    assert message.is_read is None

    # Alice 標記訊息為已讀
    response = await client.post(
        "/api/messages/messages/read",
        headers={"Authorization": f"Bearer {alice_token}"},
        json={"message_ids": [str(message.id)]}
    )

    assert response.status_code == 204

    # 驗證訊息已標記為已讀
    await test_db.refresh(message)
    assert message.is_read is not None


@pytest.mark.asyncio
async def test_mark_multiple_messages_as_read(client: AsyncClient, matched_users: dict, test_db: AsyncSession):
    """測試批量標記訊息為已讀"""
    match_id = matched_users["match_id"]
    alice_token = matched_users["alice"]["token"]
    bob_user_id = matched_users["bob"]["user_id"]

    # Bob 發送多條訊息
    message_ids = []
    for i in range(3):
        message = Message(
            match_id=match_id,
            sender_id=bob_user_id,
            content=f"Message {i+1}",
            message_type="TEXT"
        )
        test_db.add(message)
        await test_db.flush()
        message_ids.append(str(message.id))
    await test_db.commit()

    # Alice 批量標記為已讀
    response = await client.post(
        "/api/messages/messages/read",
        headers={"Authorization": f"Bearer {alice_token}"},
        json={"message_ids": message_ids}
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_cannot_mark_own_messages_as_read(client: AsyncClient, matched_users: dict, test_db: AsyncSession):
    """測試無法標記自己的訊息為已讀"""
    match_id = matched_users["match_id"]
    alice_token = matched_users["alice"]["token"]
    alice_user_id = matched_users["alice"]["user_id"]

    # Alice 發送訊息
    message = Message(
        match_id=match_id,
        sender_id=alice_user_id,
        content="My message",
        message_type="TEXT"
    )
    test_db.add(message)
    await test_db.commit()
    await test_db.refresh(message)

    # Alice 嘗試標記自己的訊息為已讀
    response = await client.post(
        "/api/messages/messages/read",
        headers={"Authorization": f"Bearer {alice_token}"},
        json={"message_ids": [str(message.id)]}
    )

    # 應該成功但不更新（因為是自己的訊息）
    assert response.status_code == 204

    # 驗證訊息仍未讀
    await test_db.refresh(message)
    assert message.is_read is None


@pytest.mark.asyncio
async def test_delete_message_success(client: AsyncClient, matched_users: dict, test_db: AsyncSession):
    """測試成功刪除訊息"""
    match_id = matched_users["match_id"]
    alice_token = matched_users["alice"]["token"]
    alice_user_id = matched_users["alice"]["user_id"]

    # Alice 發送訊息
    message = Message(
        match_id=match_id,
        sender_id=alice_user_id,
        content="Test message",
        message_type="TEXT"
    )
    test_db.add(message)
    await test_db.commit()
    await test_db.refresh(message)

    # Alice 刪除訊息
    response = await client.delete(
        f"/api/messages/messages/{message.id}",
        headers={"Authorization": f"Bearer {alice_token}"}
    )

    assert response.status_code == 204

    # 驗證訊息已軟刪除
    await test_db.refresh(message)
    assert message.deleted_at is not None


@pytest.mark.asyncio
async def test_delete_message_not_owner(client: AsyncClient, matched_users: dict, test_db: AsyncSession):
    """測試無法刪除他人的訊息"""
    match_id = matched_users["match_id"]
    alice_token = matched_users["alice"]["token"]
    bob_token = matched_users["bob"]["token"]
    bob_user_id = matched_users["bob"]["user_id"]

    # Bob 發送訊息
    message = Message(
        match_id=match_id,
        sender_id=bob_user_id,
        content="Bob's message",
        message_type="TEXT"
    )
    test_db.add(message)
    await test_db.commit()
    await test_db.refresh(message)

    # Alice 嘗試刪除 Bob 的訊息
    response = await client.delete(
        f"/api/messages/messages/{message.id}",
        headers={"Authorization": f"Bearer {alice_token}"}
    )

    assert response.status_code == 403
    assert "只能刪除自己的訊息" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_nonexistent_message(client: AsyncClient, matched_users: dict):
    """測試刪除不存在的訊息"""
    alice_token = matched_users["alice"]["token"]
    fake_message_id = "00000000-0000-0000-0000-000000000000"

    response = await client.delete(
        f"/api/messages/messages/{fake_message_id}",
        headers={"Authorization": f"Bearer {alice_token}"}
    )

    assert response.status_code == 404
    assert "訊息不存在" in response.json()["detail"]


@pytest.mark.asyncio
async def test_deleted_messages_not_in_history(client: AsyncClient, matched_users: dict, test_db: AsyncSession):
    """測試已刪除的訊息不出現在聊天記錄中"""
    match_id = matched_users["match_id"]
    alice_token = matched_users["alice"]["token"]
    alice_user_id = matched_users["alice"]["user_id"]

    # 創建兩條訊息
    message1 = Message(
        match_id=match_id,
        sender_id=alice_user_id,
        content="Message 1",
        message_type="TEXT"
    )
    message2 = Message(
        match_id=match_id,
        sender_id=alice_user_id,
        content="Message 2",
        message_type="TEXT"
    )
    test_db.add(message1)
    test_db.add(message2)
    await test_db.commit()
    await test_db.refresh(message1)

    # 刪除第一條訊息
    await client.delete(
        f"/api/messages/messages/{message1.id}",
        headers={"Authorization": f"Bearer {alice_token}"}
    )

    # 查看聊天記錄
    response = await client.get(
        f"/api/messages/matches/{match_id}/messages",
        headers={"Authorization": f"Bearer {alice_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 1  # 只應該看到一條訊息
    assert data["messages"][0]["content"] == "Message 2"


@pytest.mark.asyncio
async def test_delete_message_websocket_broadcast(client: AsyncClient, matched_users: dict, test_db: AsyncSession):
    """測試刪除訊息時 WebSocket 廣播通知"""

    match_id = matched_users["match_id"]
    alice_token = matched_users["alice"]["token"]
    alice_user_id = matched_users["alice"]["user_id"]

    # Alice 發送訊息
    message = Message(
        match_id=match_id,
        sender_id=alice_user_id,
        content="Test message to delete",
        message_type="TEXT"
    )
    test_db.add(message)
    await test_db.commit()
    await test_db.refresh(message)
    message_id = str(message.id)

    # Mock WebSocket manager 的 send_to_match 方法
    with patch('app.websocket.manager.manager.send_to_match', new_callable=AsyncMock) as mock_send:
        # Alice 刪除訊息
        response = await client.delete(
            f"/api/messages/messages/{message_id}",
            headers={"Authorization": f"Bearer {alice_token}"}
        )

        assert response.status_code == 204

        # 驗證 WebSocket 廣播被調用
        mock_send.assert_called_once()

        # 驗證廣播的參數
        call_args = mock_send.call_args
        assert call_args[0][0] == match_id  # match_id

        broadcast_data = call_args[0][1]  # 廣播的數據
        assert broadcast_data["type"] == "message_deleted"
        assert broadcast_data["message_id"] == message_id
        assert broadcast_data["match_id"] == match_id
        assert broadcast_data["deleted_by"] == alice_user_id

        # 驗證排除了刪除者
        assert call_args[1]["exclude_user"] == alice_user_id


@pytest.mark.asyncio
async def test_delete_message_websocket_event_format(client: AsyncClient, matched_users: dict, test_db: AsyncSession):
    """測試刪除訊息 WebSocket 事件格式正確性"""

    match_id = matched_users["match_id"]
    bob_token = matched_users["bob"]["token"]
    bob_user_id = matched_users["bob"]["user_id"]

    # Bob 發送訊息
    message = Message(
        match_id=match_id,
        sender_id=bob_user_id,
        content="Bob's test message",
        message_type="TEXT"
    )
    test_db.add(message)
    await test_db.commit()
    await test_db.refresh(message)

    # Mock WebSocket manager
    with patch('app.websocket.manager.manager.send_to_match', new_callable=AsyncMock) as mock_send:
        # Bob 刪除訊息
        await client.delete(
            f"/api/messages/messages/{message.id}",
            headers={"Authorization": f"Bearer {bob_token}"}
        )

        # 獲取廣播的事件數據
        broadcast_data = mock_send.call_args[0][1]

        # 驗證事件包含所有必要欄位
        required_fields = ["type", "message_id", "match_id", "deleted_by"]
        for field in required_fields:
            assert field in broadcast_data, f"Missing required field: {field}"

        # 驗證事件類型
        assert broadcast_data["type"] == "message_deleted"

        # 驗證 UUID 格式
        assert uuid.UUID(broadcast_data["message_id"])
        assert uuid.UUID(broadcast_data["match_id"])
        assert uuid.UUID(broadcast_data["deleted_by"])
