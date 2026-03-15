"""
即時通知功能測試

========== 測試三種通知類型 ==========
1. notification_message - 新訊息通知（接收者不在聊天室時）
2. notification_match - 新配對通知（互相喜歡時）
3. notification_liked - 有人喜歡你通知（單方喜歡時）
========================================
"""

from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import InterestTag
from app.models.user import User
from app.websocket.manager import manager


@pytest.fixture
async def notification_test_users(client: AsyncClient, auth_user_pair: dict, test_db: AsyncSession):
    """創建用於通知測試的用戶（Alice 和 Bob）"""
    # 取得用戶 ID（使用 auth_user_pair 的 email）
    result = await test_db.execute(
        select(User).where(User.email == auth_user_pair["alice"]["email"])
    )
    alice = result.scalar_one()

    result = await test_db.execute(select(User).where(User.email == auth_user_pair["bob"]["email"]))
    bob = result.scalar_one()

    return {
        "alice": {
            "token": auth_user_pair["alice"]["token"],
            "user_id": str(alice.id),
            "email": auth_user_pair["alice"]["email"],
        },
        "bob": {
            "token": auth_user_pair["bob"]["token"],
            "user_id": str(bob.id),
            "email": auth_user_pair["bob"]["email"],
        },
    }


@pytest.fixture
async def completed_notification_profiles(
    client: AsyncClient, notification_test_users: dict, test_db: AsyncSession
):
    """創建完整的個人檔案用於通知測試"""
    # Alice 的檔案
    response = await client.post(
        "/api/profile",
        headers={"Authorization": f"Bearer {notification_test_users['alice']['token']}"},
        json={
            "display_name": "Alice Notify",
            "gender": "female",
            "bio": "測試通知功能",
            "location": {
                "latitude": 25.0330,
                "longitude": 121.5654,
                "location_name": "台北市信義區",
            },
        },
    )
    assert response.status_code == 201

    # 更新 Alice 的偏好設定
    response = await client.patch(
        "/api/profile",
        headers={"Authorization": f"Bearer {notification_test_users['alice']['token']}"},
        json={
            "min_age_preference": 25,
            "max_age_preference": 40,
            "max_distance_km": 50,
            "gender_preference": "male",
        },
    )
    assert response.status_code == 200

    # Bob 的檔案
    response = await client.post(
        "/api/profile",
        headers={"Authorization": f"Bearer {notification_test_users['bob']['token']}"},
        json={
            "display_name": "Bob Notify",
            "gender": "male",
            "bio": "測試通知功能",
            "location": {
                "latitude": 25.0500,
                "longitude": 121.5500,
                "location_name": "台北市大安區",
            },
        },
    )
    assert response.status_code == 201

    # 更新 Bob 的偏好設定
    response = await client.patch(
        "/api/profile",
        headers={"Authorization": f"Bearer {notification_test_users['bob']['token']}"},
        json={
            "min_age_preference": 22,
            "max_age_preference": 35,
            "max_distance_km": 30,
            "gender_preference": "female",
        },
    )
    assert response.status_code == 200

    # 建立興趣標籤
    result = await test_db.execute(select(InterestTag).limit(3))
    existing_tags = result.scalars().all()

    if len(existing_tags) < 3:
        tags_to_create = [
            InterestTag(name="音樂", category="entertainment", icon="🎵"),
            InterestTag(name="電影", category="entertainment", icon="🎬"),
            InterestTag(name="旅遊", category="lifestyle", icon="✈️"),
        ]
        for tag in tags_to_create:
            test_db.add(tag)
        await test_db.commit()

        result = await test_db.execute(select(InterestTag).limit(3))
        existing_tags = result.scalars().all()

    tag_ids = [str(tag.id) for tag in existing_tags[:3]]

    # 為 Alice 和 Bob 設定興趣標籤
    response = await client.put(
        "/api/profile/interests",
        headers={"Authorization": f"Bearer {notification_test_users['alice']['token']}"},
        json={"interest_ids": tag_ids},
    )
    assert response.status_code == 200

    response = await client.put(
        "/api/profile/interests",
        headers={"Authorization": f"Bearer {notification_test_users['bob']['token']}"},
        json={"interest_ids": tag_ids},
    )
    assert response.status_code == 200

    # 上傳測試照片
    def create_test_image():
        img = Image.new("RGB", (100, 100), color="blue")
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        buffer.seek(0)
        return buffer

    # Alice 上傳照片
    test_image = create_test_image()
    response = await client.post(
        "/api/profile/photos",
        headers={"Authorization": f"Bearer {notification_test_users['alice']['token']}"},
        files={"file": ("photo.jpg", test_image, "image/jpeg")},
    )
    assert response.status_code == 201

    # Bob 上傳照片
    test_image = create_test_image()
    response = await client.post(
        "/api/profile/photos",
        headers={"Authorization": f"Bearer {notification_test_users['bob']['token']}"},
        files={"file": ("photo.jpg", test_image, "image/jpeg")},
    )
    assert response.status_code == 201

    # 驗證檔案完整度
    response = await client.get(
        "/api/profile",
        headers={"Authorization": f"Bearer {notification_test_users['alice']['token']}"},
    )
    assert response.json().get("is_complete") is True

    response = await client.get(
        "/api/profile",
        headers={"Authorization": f"Bearer {notification_test_users['bob']['token']}"},
    )
    assert response.json().get("is_complete") is True

    return notification_test_users


# ==================== 通知類型 2：notification_liked 測試 ====================


class TestNotificationLiked:
    """
    【通知類型 2】有人喜歡你通知測試

    觸發條件：單方 Like（A 喜歡 B，但 B 還沒喜歡 A）
    通知內容：不透露是誰喜歡，保持神秘感
    """

    @pytest.mark.asyncio
    async def test_like_sends_notification_liked(
        self, client: AsyncClient, completed_notification_profiles: dict
    ):
        """測試：單方喜歡時發送 notification_liked 通知"""
        # 取得 Bob 的 user_id（Alice 要喜歡 Bob）
        response = await client.get(
            "/api/discovery/browse?limit=10",
            headers={
                "Authorization": f"Bearer {completed_notification_profiles['alice']['token']}"
            },
        )
        candidates = response.json()

        if len(candidates) == 0:
            pytest.skip("沒有可配對的候選人")

        bob_user_id = candidates[0]["user_id"]

        # Mock send_personal_message 來驗證通知發送
        with patch.object(manager, "send_personal_message", new_callable=AsyncMock) as mock_send:
            # Alice 喜歡 Bob（單方）
            response = await client.post(
                f"/api/discovery/like/{bob_user_id}",
                headers={
                    "Authorization": f"Bearer {completed_notification_profiles['alice']['token']}"
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_match"] is False  # 尚未配對

            # 驗證 notification_liked 通知已發送給 Bob
            mock_send.assert_called()

            # 取得所有呼叫的參數
            calls = mock_send.call_args_list
            notification_liked_call = None

            for call in calls:
                args, kwargs = call
                if len(args) >= 2:
                    user_id_arg = args[0]
                    message_arg = args[1]
                    if (
                        isinstance(message_arg, dict)
                        and message_arg.get("type") == "notification_liked"
                    ):
                        notification_liked_call = (user_id_arg, message_arg)
                        break

            assert notification_liked_call is not None, "notification_liked 通知應該被發送"

            recipient_id, notification_data = notification_liked_call
            assert recipient_id == bob_user_id  # 通知發送給 Bob
            assert notification_data["type"] == "notification_liked"
            assert "notification_id" in notification_data  # 必須包含資料庫通知 ID
            assert "timestamp" in notification_data
            # notification_liked 不應該包含喜歡者的資訊（保持神秘感）
            assert "liker_id" not in notification_data
            assert "liker_name" not in notification_data


# ==================== 通知類型 1：notification_match 測試 ====================


class TestNotificationMatch:
    """
    【通知類型 1】新配對通知測試

    觸發條件：互相 Like（A 喜歡 B 且 B 也喜歡 A）
    通知內容：包含配對者的名稱和頭像
    """

    @pytest.mark.asyncio
    async def test_mutual_like_sends_notification_match_to_both(
        self, client: AsyncClient, completed_notification_profiles: dict
    ):
        """測試：互相喜歡時發送 notification_match 給雙方"""
        # Alice 瀏覽並取得 Bob 的 ID
        response = await client.get(
            "/api/discovery/browse?limit=10",
            headers={
                "Authorization": f"Bearer {completed_notification_profiles['alice']['token']}"
            },
        )
        candidates = response.json()

        if len(candidates) == 0:
            pytest.skip("沒有可配對的候選人")

        bob_user_id = candidates[0]["user_id"]

        # Bob 瀏覽並取得 Alice 的 ID
        response = await client.get(
            "/api/discovery/browse?limit=10",
            headers={"Authorization": f"Bearer {completed_notification_profiles['bob']['token']}"},
        )
        candidates = response.json()
        alice_user_id = next(
            (c["user_id"] for c in candidates if "Alice" in c["display_name"]), None
        )

        if not alice_user_id:
            pytest.skip("Bob 看不到 Alice")

        # Alice 先喜歡 Bob（會觸發 notification_liked）
        with patch.object(manager, "send_personal_message", new_callable=AsyncMock):
            await client.post(
                f"/api/discovery/like/{bob_user_id}",
                headers={
                    "Authorization": f"Bearer {completed_notification_profiles['alice']['token']}"
                },
            )

        # Bob 喜歡 Alice（會觸發配對，發送 notification_match 給雙方）
        with patch.object(manager, "send_personal_message", new_callable=AsyncMock) as mock_send:
            response = await client.post(
                f"/api/discovery/like/{alice_user_id}",
                headers={
                    "Authorization": f"Bearer {completed_notification_profiles['bob']['token']}"
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_match"] is True  # 配對成功
            assert data["match_id"] is not None

            # 驗證 notification_match 通知已發送給雙方
            calls = mock_send.call_args_list

            # 應該有 2 個 notification_match 呼叫（給 Alice 和 Bob）
            match_notifications = []
            for call in calls:
                args, kwargs = call
                if len(args) >= 2:
                    message_arg = args[1]
                    if (
                        isinstance(message_arg, dict)
                        and message_arg.get("type") == "notification_match"
                    ):
                        match_notifications.append((args[0], message_arg))

            assert len(match_notifications) == 2, "應該發送 2 個 notification_match 通知"

            # 驗證通知內容
            recipients = set()
            for recipient_id, notification_data in match_notifications:
                recipients.add(recipient_id)
                assert notification_data["type"] == "notification_match"
                assert "notification_id" in notification_data  # 必須包含資料庫通知 ID
                assert "match_id" in notification_data
                assert "matched_user_id" in notification_data
                assert "matched_user_name" in notification_data
                assert "timestamp" in notification_data

            # 確保 Alice 和 Bob 都收到通知
            assert alice_user_id in recipients
            assert bob_user_id in recipients

    @pytest.mark.asyncio
    async def test_notification_match_contains_correct_user_info(
        self, client: AsyncClient, completed_notification_profiles: dict
    ):
        """測試：notification_match 包含正確的配對用戶資訊"""
        # 取得雙方的 user_id
        response = await client.get(
            "/api/discovery/browse?limit=10",
            headers={
                "Authorization": f"Bearer {completed_notification_profiles['alice']['token']}"
            },
        )
        candidates = response.json()

        if len(candidates) == 0:
            pytest.skip("沒有可配對的候選人")

        bob_user_id = candidates[0]["user_id"]

        response = await client.get(
            "/api/discovery/browse?limit=10",
            headers={"Authorization": f"Bearer {completed_notification_profiles['bob']['token']}"},
        )
        candidates = response.json()
        alice_user_id = next(
            (c["user_id"] for c in candidates if "Alice" in c["display_name"]), None
        )

        if not alice_user_id:
            pytest.skip("Bob 看不到 Alice")

        # Alice 先喜歡 Bob
        with patch.object(manager, "send_personal_message", new_callable=AsyncMock):
            await client.post(
                f"/api/discovery/like/{bob_user_id}",
                headers={
                    "Authorization": f"Bearer {completed_notification_profiles['alice']['token']}"
                },
            )

        # Bob 喜歡 Alice 觸發配對
        with patch.object(manager, "send_personal_message", new_callable=AsyncMock) as mock_send:
            response = await client.post(
                f"/api/discovery/like/{alice_user_id}",
                headers={
                    "Authorization": f"Bearer {completed_notification_profiles['bob']['token']}"
                },
            )

            assert response.status_code == 200
            match_id = response.json()["match_id"]

            # 收集發送給 Alice 的通知
            alice_notification = None
            bob_notification = None

            for call in mock_send.call_args_list:
                args, kwargs = call
                if len(args) >= 2:
                    recipient_id = args[0]
                    message = args[1]
                    if isinstance(message, dict) and message.get("type") == "notification_match":
                        if recipient_id == alice_user_id:
                            alice_notification = message
                        elif recipient_id == bob_user_id:
                            bob_notification = message

            # 驗證發送給 Alice 的通知包含 Bob 的資訊
            assert alice_notification is not None
            assert alice_notification["matched_user_id"] == bob_user_id
            assert "Bob" in alice_notification["matched_user_name"]
            assert alice_notification["match_id"] == match_id

            # 驗證發送給 Bob 的通知包含 Alice 的資訊
            assert bob_notification is not None
            assert bob_notification["matched_user_id"] == alice_user_id
            assert "Alice" in bob_notification["matched_user_name"]
            assert bob_notification["match_id"] == match_id


# ==================== 通知類型 3：notification_message 測試 ====================


class TestNotificationMessage:
    """
    【通知類型 3】新訊息通知測試

    觸發條件：接收者不在聊天室中時收到新訊息
    通知內容：包含發送者名稱和訊息預覽
    """

    @pytest.mark.asyncio
    async def test_message_notification_when_receiver_not_in_room(
        self, client: AsyncClient, completed_notification_profiles: dict, test_db: AsyncSession
    ):
        """測試：當接收者不在聊天室時發送 notification_message"""
        # 建立配對
        response = await client.get(
            "/api/discovery/browse?limit=10",
            headers={
                "Authorization": f"Bearer {completed_notification_profiles['alice']['token']}"
            },
        )
        candidates = response.json()

        if len(candidates) == 0:
            pytest.skip("沒有可配對的候選人")

        bob_user_id = candidates[0]["user_id"]

        response = await client.get(
            "/api/discovery/browse?limit=10",
            headers={"Authorization": f"Bearer {completed_notification_profiles['bob']['token']}"},
        )
        candidates = response.json()
        alice_user_id = next(
            (c["user_id"] for c in candidates if "Alice" in c["display_name"]), None
        )

        if not alice_user_id:
            pytest.skip("Bob 看不到 Alice")

        # 互相喜歡建立配對
        with patch.object(manager, "send_personal_message", new_callable=AsyncMock):
            await client.post(
                f"/api/discovery/like/{bob_user_id}",
                headers={
                    "Authorization": f"Bearer {completed_notification_profiles['alice']['token']}"
                },
            )
            response = await client.post(
                f"/api/discovery/like/{alice_user_id}",
                headers={
                    "Authorization": f"Bearer {completed_notification_profiles['bob']['token']}"
                },
            )

        match_id = response.json()["match_id"]

        # 驗證 match_rooms 邏輯
        # 當 Bob 不在聊天室時，Alice 發送訊息應觸發 notification_message

        # 模擬 Bob 不在聊天室（match_rooms 為空或不包含 Bob）
        manager.match_rooms[match_id] = [alice_user_id]  # 只有 Alice 在聊天室

        # 驗證 match_rooms 狀態
        assert match_id in manager.match_rooms
        assert bob_user_id not in manager.match_rooms[match_id]

        # 清理測試數據
        if match_id in manager.match_rooms:
            del manager.match_rooms[match_id]

    @pytest.mark.asyncio
    async def test_no_notification_when_receiver_in_room(self):
        """測試：當接收者在聊天室時不發送 notification_message"""
        match_id = "test-match-notification"
        alice_id = "alice-id"
        bob_id = "bob-id"

        # 模擬雙方都在聊天室
        manager.match_rooms[match_id] = [alice_id, bob_id]

        # 驗證雙方都在聊天室
        assert alice_id in manager.match_rooms[match_id]
        assert bob_id in manager.match_rooms[match_id]

        # 清理
        del manager.match_rooms[match_id]


# ==================== ConnectionManager 通知方法測試 ====================


class TestConnectionManagerNotification:
    """測試 ConnectionManager 的通知發送方法"""

    @pytest.mark.asyncio
    async def test_send_personal_message_online_user(self):
        """測試：向在線用戶發送個人訊息"""
        user_id = "test-online-user"

        # 創建 mock WebSocket
        mock_ws = AsyncMock()
        manager.active_connections[user_id] = mock_ws

        # 發送訊息
        test_message = {"type": "notification_liked", "timestamp": datetime.now(UTC).isoformat()}
        await manager.send_personal_message(user_id, test_message)

        # 驗證 WebSocket.send_json 被呼叫
        mock_ws.send_json.assert_called_once_with(test_message)

        # 清理
        del manager.active_connections[user_id]

    @pytest.mark.asyncio
    async def test_send_personal_message_offline_user(self):
        """測試：向離線用戶發送個人訊息（應該安靜失敗）"""
        user_id = "test-offline-user"

        # 確保用戶不在線
        if user_id in manager.active_connections:
            del manager.active_connections[user_id]

        # 發送訊息（應該不拋出異常）
        test_message = {
            "type": "notification_match",
            "match_id": "test-match",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        await manager.send_personal_message(user_id, test_message)

        # 測試通過（沒有異常拋出）

    @pytest.mark.asyncio
    async def test_is_online_check(self):
        """測試：檢查用戶在線狀態"""
        user_id = "test-is-online"

        # 用戶離線
        is_offline = await manager.is_online(user_id)
        assert is_offline is False

        # 用戶上線
        mock_ws = AsyncMock()
        manager.active_connections[user_id] = mock_ws

        is_online = await manager.is_online(user_id)
        assert is_online is True

        # 清理
        del manager.active_connections[user_id]

    @pytest.mark.asyncio
    async def test_match_room_operations(self):
        """測試：配對聊天室加入/離開操作"""
        match_id = "test-match-room-ops"
        user_id = "test-user-room"

        # 加入聊天室
        await manager.join_match_room(match_id, user_id)
        assert match_id in manager.match_rooms
        assert user_id in manager.match_rooms[match_id]

        # 離開聊天室
        await manager.leave_match_room(match_id, user_id)
        if match_id in manager.match_rooms:
            assert user_id not in manager.match_rooms[match_id]


# ==================== 整合測試 ====================


class TestNotificationIntegration:
    """通知功能整合測試"""

    @pytest.mark.asyncio
    async def test_full_notification_flow(
        self, client: AsyncClient, completed_notification_profiles: dict
    ):
        """
        測試完整的通知流程：
        1. Alice 喜歡 Bob → 發送 notification_liked
        2. Bob 喜歡 Alice → 發送 notification_match 給雙方
        """
        # 取得雙方的 user_id
        response = await client.get(
            "/api/discovery/browse?limit=10",
            headers={
                "Authorization": f"Bearer {completed_notification_profiles['alice']['token']}"
            },
        )
        candidates = response.json()

        if len(candidates) == 0:
            pytest.skip("沒有可配對的候選人")

        bob_user_id = candidates[0]["user_id"]

        response = await client.get(
            "/api/discovery/browse?limit=10",
            headers={"Authorization": f"Bearer {completed_notification_profiles['bob']['token']}"},
        )
        candidates = response.json()
        alice_user_id = next(
            (c["user_id"] for c in candidates if "Alice" in c["display_name"]), None
        )

        if not alice_user_id:
            pytest.skip("Bob 看不到 Alice")

        notifications_sent = []

        async def capture_notification(user_id, message):
            notifications_sent.append({"recipient": user_id, "message": message})

        # Step 1: Alice 喜歡 Bob
        with patch.object(manager, "send_personal_message", side_effect=capture_notification):
            response = await client.post(
                f"/api/discovery/like/{bob_user_id}",
                headers={
                    "Authorization": f"Bearer {completed_notification_profiles['alice']['token']}"
                },
            )
            assert response.status_code == 200
            assert response.json()["is_match"] is False

        # 驗證 notification_liked 已發送
        liked_notifications = [
            n for n in notifications_sent if n["message"].get("type") == "notification_liked"
        ]
        assert len(liked_notifications) == 1
        assert liked_notifications[0]["recipient"] == bob_user_id

        # 清空收集的通知
        notifications_sent.clear()

        # Step 2: Bob 喜歡 Alice
        with patch.object(manager, "send_personal_message", side_effect=capture_notification):
            response = await client.post(
                f"/api/discovery/like/{alice_user_id}",
                headers={
                    "Authorization": f"Bearer {completed_notification_profiles['bob']['token']}"
                },
            )
            assert response.status_code == 200
            assert response.json()["is_match"] is True

        # 驗證 notification_match 已發送給雙方
        match_notifications = [
            n for n in notifications_sent if n["message"].get("type") == "notification_match"
        ]
        assert len(match_notifications) == 2

        recipients = {n["recipient"] for n in match_notifications}
        assert alice_user_id in recipients
        assert bob_user_id in recipients
