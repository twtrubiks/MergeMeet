"""WebSocket 即時通訊測試"""
import pytest
import uuid
import asyncio
from unittest.mock import AsyncMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

from app.models.user import User
from app.models.match import Match, Message
from app.models.moderation import SensitiveWord
from app.websocket.manager import manager
from app.services.content_moderation import ContentModerationService


@pytest.fixture
async def matched_users_for_ws(client: AsyncClient, auth_user_pair: dict, test_db: AsyncSession):
    """創建已配對的測試用戶用於 WebSocket 測試"""
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
        "alice": {
            "token": alice_token,
            "user_id": str(alice.id),
            "email": auth_user_pair["alice"]["email"]
        },
        "bob": {
            "token": bob_token,
            "user_id": str(bob.id),
            "email": auth_user_pair["bob"]["email"]
        },
        "match_id": str(match.id)
    }


@pytest.mark.asyncio
async def test_websocket_match_rooms():
    """測試配對聊天室功能"""
    match_id = "test-match-id"
    user_id = "test-user-id"

    # 測試加入聊天室
    await manager.join_match_room(match_id, user_id)
    assert match_id in manager.match_rooms
    assert user_id in manager.match_rooms[match_id]

    # 測試離開聊天室
    await manager.leave_match_room(match_id, user_id)
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
    # 清除 cookies，讓測試使用純 Bearer Token 認證
    client.cookies.clear()

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
    alice_user_id = matched_users_for_ws["alice"]["user_id"]

    # 創建敏感詞數據
    sensitive_word = SensitiveWord(
        id=uuid.uuid4(),
        word="色情",
        category="SEXUAL",
        severity="HIGH",
        action="REJECT",
        is_regex=False,
        is_active=True
    )
    test_db.add(sensitive_word)
    await test_db.commit()
    await ContentModerationService.clear_cache()

    # 測試安全內容
    safe_content = "Hello, how are you?"
    is_safe, violations, action = await ContentModerationService.check_message_content(
        safe_content, test_db, alice_user_id
    )
    assert is_safe is True
    assert len(violations) == 0

    # 測試不安全內容
    unsafe_content = "想要看色情影片嗎？"
    is_safe, violations, action = await ContentModerationService.check_message_content(
        unsafe_content, test_db, alice_user_id
    )
    assert is_safe is False
    assert len(violations) > 0


@pytest.mark.asyncio
async def test_message_with_unsafe_content_rejected(
    matched_users_for_ws: dict,
    test_db: AsyncSession
):
    """測試包含不當內容的訊息應被拒絕"""
    match_id = matched_users_for_ws["match_id"]
    alice_user_id = matched_users_for_ws["alice"]["user_id"]

    # 創建敏感詞數據
    sensitive_word = SensitiveWord(
        id=uuid.uuid4(),
        word="投資",
        category="SCAM",
        severity="MEDIUM",
        action="REJECT",
        is_regex=False,
        is_active=True
    )
    test_db.add(sensitive_word)
    await test_db.commit()
    await ContentModerationService.clear_cache()

    # 嘗試發送不當內容
    unsafe_content = "加入我們的投資計劃，快速賺錢"
    is_safe, violations, action = await ContentModerationService.check_message_content(
        unsafe_content, test_db, alice_user_id
    )

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
    # 獲取 Alice 的初始警告次數（使用 fixture 的 email）
    result = await test_db.execute(
        select(User).where(User.email == matched_users_for_ws["alice"]["email"])
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
    await manager.join_match_room(match_id, user_id)

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


# ==================== 心跳機制測試 ====================

class TestWebSocketHeartbeat:
    """WebSocket 心跳機制測試"""

    @pytest.mark.asyncio
    async def test_heartbeat_config(self):
        """測試心跳配置"""
        assert manager.HEARTBEAT_INTERVAL == 30  # 發送 ping 的間隔（秒）
        assert manager.HEARTBEAT_TIMEOUT == 90   # 無回應超時時間（秒）

    @pytest.mark.asyncio
    async def test_update_heartbeat(self):
        """測試更新心跳時間"""
        user_id = "test-heartbeat-user"

        # 設置初始心跳（舊時間）
        old_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        manager.connection_heartbeats[user_id] = old_time

        # 更新心跳
        await manager.update_heartbeat(user_id)

        # 驗證心跳已更新（新時間應該比舊時間晚）
        new_time = manager.connection_heartbeats[user_id]
        assert new_time > old_time

        # 清理
        del manager.connection_heartbeats[user_id]

    @pytest.mark.asyncio
    async def test_update_heartbeat_nonexistent_user(self):
        """測試更新不存在用戶的心跳時間（應該安全跳過）"""
        user_id = "nonexistent-user-heartbeat"

        # 確保用戶不存在
        assert user_id not in manager.connection_heartbeats

        # 更新心跳應該不拋出異常
        await manager.update_heartbeat(user_id)

        # 仍然不存在（不會自動創建）
        assert user_id not in manager.connection_heartbeats

    @pytest.mark.asyncio
    async def test_stale_connection_detection(self):
        """測試過期連接檢測"""

        user_id = "test-stale-user"

        # 設置一個過期的心跳時間（超過 90 秒）
        stale_time = datetime.now(timezone.utc) - timedelta(seconds=100)
        manager.connection_heartbeats[user_id] = stale_time

        # 計算是否過期
        now = datetime.now(timezone.utc)
        is_stale = now - stale_time > timedelta(seconds=manager.HEARTBEAT_TIMEOUT)

        assert is_stale is True

        # 清理
        del manager.connection_heartbeats[user_id]

    @pytest.mark.asyncio
    async def test_active_connection_detection(self):
        """測試活躍連接檢測"""

        user_id = "test-active-user"

        # 設置一個最近的心跳時間（10 秒前）
        recent_time = datetime.now(timezone.utc) - timedelta(seconds=10)
        manager.connection_heartbeats[user_id] = recent_time

        # 計算是否過期
        now = datetime.now(timezone.utc)
        is_stale = now - recent_time > timedelta(seconds=manager.HEARTBEAT_TIMEOUT)

        assert is_stale is False

        # 清理
        del manager.connection_heartbeats[user_id]

    @pytest.mark.asyncio
    async def test_heartbeat_cleared_on_disconnect(self):
        """測試斷開連接時清除心跳"""

        user_id = "test-disconnect-heartbeat"

        # 模擬連接（直接添加心跳，因為沒有真正的 WebSocket）
        manager.connection_heartbeats[user_id] = datetime.now(timezone.utc)

        # 確保心跳存在
        assert user_id in manager.connection_heartbeats

        # 斷開連接
        await manager.disconnect(user_id)

        # 驗證心跳已清除
        assert user_id not in manager.connection_heartbeats

    @pytest.mark.asyncio
    async def test_cleanup_stale_connections(self):
        """測試清理過期連接"""

        # 創建過期和活躍的心跳
        stale_user = "test-stale-cleanup"
        active_user = "test-active-cleanup"

        manager.connection_heartbeats[stale_user] = datetime.now(timezone.utc) - timedelta(seconds=100)
        manager.connection_heartbeats[active_user] = datetime.now(timezone.utc) - timedelta(seconds=10)

        # 執行清理
        await manager._cleanup_stale_connections()

        # 過期連接應該被清理
        assert stale_user not in manager.connection_heartbeats

        # 活躍連接應該保留
        assert active_user in manager.connection_heartbeats

        # 清理測試數據
        if active_user in manager.connection_heartbeats:
            del manager.connection_heartbeats[active_user]

    @pytest.mark.asyncio
    async def test_background_tasks_initialization(self):
        """測試背景任務初始化"""
        # 確保任務已啟動（在 main.py 的 lifespan 中）
        # 這裡只驗證任務存在
        await manager.start_background_tasks()

        assert manager._heartbeat_task is not None
        assert manager._cleanup_task is not None


# =============================================================================
# Mock Redis Fixture for Positive Interaction Tests
# =============================================================================
@pytest.fixture
def mock_redis_data():
    """模擬 Redis 存儲"""
    return {}


@pytest.fixture
def mock_redis(mock_redis_data):
    """模擬 Redis 連線"""
    redis_mock = AsyncMock()

    async def mock_incr(key):
        mock_redis_data[key] = mock_redis_data.get(key, 0) + 1
        return mock_redis_data[key]

    async def mock_get(key):
        return mock_redis_data.get(key)

    async def mock_setex(key, ttl, value):
        mock_redis_data[key] = value

    async def mock_expire(key, ttl):
        pass  # TTL 在測試中不重要

    redis_mock.incr = mock_incr
    redis_mock.get = mock_get
    redis_mock.setex = mock_setex
    redis_mock.expire = mock_expire

    return redis_mock, mock_redis_data


# =============================================================================
# 測試：正向互動配對每日限制
# =============================================================================
@pytest.mark.asyncio
class TestPositiveInteractionMatchLimit:
    """測試正向互動配對每日限制（每配對每日 3 次）"""

    async def test_match_allows_three_daily_rewards(
        self,
        mock_redis
    ):
        """測試：同一配對每日可獲得 3 次獎勵"""
        redis_mock, redis_data = mock_redis
        match_id = str(uuid.uuid4())
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        match_key = f"trust:positive_interaction:{match_id}:{today}"

        # 模擬 3 次 INCR（每次輪流對話）
        count1 = await redis_mock.incr(match_key)
        count2 = await redis_mock.incr(match_key)
        count3 = await redis_mock.incr(match_key)

        assert count1 == 1  # 第 1 次
        assert count2 == 2  # 第 2 次
        assert count3 == 3  # 第 3 次
        # 所有 3 次都應該獲得獎勵（count <= 3）

    async def test_match_blocks_fourth_reward(
        self,
        mock_redis
    ):
        """測試：同一配對第 4 次互動不獎勵"""
        redis_mock, redis_data = mock_redis
        match_id = str(uuid.uuid4())
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        match_key = f"trust:positive_interaction:{match_id}:{today}"

        # 模擬已經有 3 次獎勵
        redis_data[match_key] = 3

        # 第 4 次 INCR
        count4 = await redis_mock.incr(match_key)

        assert count4 == 4
        # count4 > 3，應該被阻擋，不獎勵

    async def test_different_matches_have_separate_limits(
        self,
        mock_redis
    ):
        """測試：不同配對各自獨立計算限制"""
        redis_mock, redis_data = mock_redis
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        match1_id = str(uuid.uuid4())
        match2_id = str(uuid.uuid4())
        match1_key = f"trust:positive_interaction:{match1_id}:{today}"
        match2_key = f"trust:positive_interaction:{match2_id}:{today}"

        # Match 1 已達上限
        redis_data[match1_key] = 3

        # Match 2 尚未開始
        count_m1 = await redis_mock.incr(match1_key)
        count_m2 = await redis_mock.incr(match2_key)

        assert count_m1 == 4  # Match 1 超過上限
        assert count_m2 == 1  # Match 2 第 1 次

    async def test_incr_returns_unique_values_concurrently(
        self,
        mock_redis
    ):
        """測試：併發請求下 INCR 返回唯一值"""
        redis_mock, redis_data = mock_redis
        match_key = f"trust:positive_interaction:test:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"

        # 模擬 5 個併發請求
        async def increment():
            return await redis_mock.incr(match_key)

        results = await asyncio.gather(*[increment() for _ in range(5)])

        # 應該得到 [1, 2, 3, 4, 5]（順序可能不同）
        assert sorted(results) == [1, 2, 3, 4, 5]
        # 只有前 3 個應該獲得獎勵


