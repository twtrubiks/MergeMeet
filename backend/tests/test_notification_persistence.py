"""
通知持久化功能測試 (TDD)

========== 測試範圍 ==========
1. Notification Model 測試
2. Notification API 測試 (5 端點)
3. 通知自動建立測試 (Like/Match/Message 觸發)
============================
"""
import pytest
import uuid
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.notification import Notification
from app.models.profile import Profile, InterestTag
from app.models.match import Match, Message
from app.websocket.manager import manager


# ==================== Fixtures ====================

@pytest.fixture
async def test_user_with_token(client: AsyncClient, test_db: AsyncSession):
    """創建測試用戶並返回 token"""
    response = await client.post("/api/auth/register", json={
        "email": "notify_test@example.com",
        "password": "Test1234!",
        "date_of_birth": "1995-01-01"
    })
    assert response.status_code == 201
    token = response.json()["access_token"]

    result = await test_db.execute(
        select(User).where(User.email == "notify_test@example.com")
    )
    user = result.scalar_one()

    return {
        "token": token,
        "user_id": str(user.id),
        "user": user
    }


@pytest.fixture
async def notification_users(client: AsyncClient, test_db: AsyncSession):
    """創建用於通知測試的用戶（Alice 和 Bob）含完整檔案"""
    from io import BytesIO
    from PIL import Image

    # 註冊 Alice
    response_a = await client.post("/api/auth/register", json={
        "email": "alice.persist@example.com",
        "password": "Alice1234!",
        "date_of_birth": "1995-06-15"
    })
    assert response_a.status_code == 201
    token_a = response_a.json()["access_token"]

    # 註冊 Bob
    response_b = await client.post("/api/auth/register", json={
        "email": "bob.persist@example.com",
        "password": "Bob12345!",
        "date_of_birth": "1990-03-20"
    })
    assert response_b.status_code == 201
    token_b = response_b.json()["access_token"]

    # 取得用戶 ID
    result = await test_db.execute(
        select(User).where(User.email == "alice.persist@example.com")
    )
    alice = result.scalar_one()

    result = await test_db.execute(
        select(User).where(User.email == "bob.persist@example.com")
    )
    bob = result.scalar_one()

    # 建立 Profile
    await client.post("/api/profile",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "display_name": "Alice Persist",
            "gender": "female",
            "bio": "測試通知持久化",
            "location": {"latitude": 25.0330, "longitude": 121.5654}
        }
    )
    await client.patch("/api/profile",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "min_age_preference": 25,
            "max_age_preference": 45,
            "max_distance_km": 50,
            "gender_preference": "male"
        }
    )

    await client.post("/api/profile",
        headers={"Authorization": f"Bearer {token_b}"},
        json={
            "display_name": "Bob Persist",
            "gender": "male",
            "bio": "測試通知持久化",
            "location": {"latitude": 25.0500, "longitude": 121.5500}
        }
    )
    await client.patch("/api/profile",
        headers={"Authorization": f"Bearer {token_b}"},
        json={
            "min_age_preference": 22,
            "max_age_preference": 40,
            "max_distance_km": 30,
            "gender_preference": "female"
        }
    )

    # 建立興趣標籤
    result = await test_db.execute(select(InterestTag).limit(3))
    existing_tags = result.scalars().all()

    if len(existing_tags) < 3:
        tags_to_create = [
            InterestTag(name="音樂P", category="entertainment", icon="🎵"),
            InterestTag(name="電影P", category="entertainment", icon="🎬"),
            InterestTag(name="旅遊P", category="lifestyle", icon="✈️"),
        ]
        for tag in tags_to_create:
            test_db.add(tag)
        await test_db.commit()

        result = await test_db.execute(select(InterestTag).limit(3))
        existing_tags = result.scalars().all()

    tag_ids = [str(tag.id) for tag in existing_tags[:3]]

    await client.put("/api/profile/interests",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"interest_ids": tag_ids}
    )
    await client.put("/api/profile/interests",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"interest_ids": tag_ids}
    )

    # 上傳照片
    def create_test_image():
        img = Image.new('RGB', (100, 100), color='blue')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        return buffer

    await client.post("/api/profile/photos",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"file": ("photo.jpg", create_test_image(), "image/jpeg")}
    )
    await client.post("/api/profile/photos",
        headers={"Authorization": f"Bearer {token_b}"},
        files={"file": ("photo.jpg", create_test_image(), "image/jpeg")}
    )

    return {
        "alice": {"token": token_a, "user_id": str(alice.id), "user": alice},
        "bob": {"token": token_b, "user_id": str(bob.id), "user": bob}
    }


# ==================== TestNotificationModel ====================

class TestNotificationModel:
    """Notification Model 測試"""

    @pytest.mark.asyncio
    async def test_create_notification_message_type(self, test_db: AsyncSession, test_user_with_token):
        """測試：建立 notification_message 類型通知"""
        user = test_user_with_token["user"]

        notification = Notification(
            user_id=user.id,
            type="notification_message",
            title="Bob 發送了訊息",
            content="你好嗎？",
            data={
                "match_id": str(uuid.uuid4()),
                "sender_id": str(uuid.uuid4()),
                "sender_name": "Bob"
            }
        )
        test_db.add(notification)
        await test_db.commit()
        await test_db.refresh(notification)

        assert notification.id is not None
        assert notification.type == "notification_message"
        assert notification.title == "Bob 發送了訊息"
        assert notification.is_read is False
        assert notification.data["sender_name"] == "Bob"

    @pytest.mark.asyncio
    async def test_create_notification_match_type(self, test_db: AsyncSession, test_user_with_token):
        """測試：建立 notification_match 類型通知"""
        user = test_user_with_token["user"]

        notification = Notification(
            user_id=user.id,
            type="notification_match",
            title="新配對！",
            content="你和 Alice 配對成功！",
            data={
                "match_id": str(uuid.uuid4()),
                "matched_user_id": str(uuid.uuid4()),
                "matched_user_name": "Alice",
                "matched_user_avatar": "/uploads/alice.jpg"
            }
        )
        test_db.add(notification)
        await test_db.commit()

        assert notification.type == "notification_match"
        assert notification.data["matched_user_name"] == "Alice"

    @pytest.mark.asyncio
    async def test_create_notification_liked_type(self, test_db: AsyncSession, test_user_with_token):
        """測試：建立 notification_liked 類型通知"""
        user = test_user_with_token["user"]

        notification = Notification(
            user_id=user.id,
            type="notification_liked",
            title="有人喜歡你！",
            content=None,
            data={}
        )
        test_db.add(notification)
        await test_db.commit()

        assert notification.type == "notification_liked"
        assert notification.data == {}

    @pytest.mark.asyncio
    async def test_notification_user_relationship(self, test_db: AsyncSession, test_user_with_token):
        """測試：Notification 與 User 關聯"""
        user = test_user_with_token["user"]

        notification = Notification(
            user_id=user.id,
            type="notification_liked",
            title="有人喜歡你！"
        )
        test_db.add(notification)
        await test_db.commit()
        await test_db.refresh(notification)

        # 驗證關聯
        assert notification.user_id == user.id

    @pytest.mark.asyncio
    async def test_notification_default_values(self, test_db: AsyncSession, test_user_with_token):
        """測試：Notification 預設值"""
        user = test_user_with_token["user"]

        notification = Notification(
            user_id=user.id,
            type="notification_message",
            title="測試"
        )
        test_db.add(notification)
        await test_db.commit()
        await test_db.refresh(notification)

        assert notification.is_read is False
        assert notification.created_at is not None
        assert notification.data == {} or notification.data is None


# ==================== TestNotificationAPI ====================

class TestNotificationAPI:
    """Notification API 測試"""

    @pytest.mark.asyncio
    async def test_get_notifications_list_empty(self, client: AsyncClient, test_user_with_token):
        """測試：取得空的通知列表"""
        response = await client.get(
            "/api/notifications",
            headers={"Authorization": f"Bearer {test_user_with_token['token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert data["notifications"] == []
        assert data["total"] == 0
        assert data["unread_count"] == 0

    @pytest.mark.asyncio
    async def test_get_notifications_list_with_data(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        test_user_with_token
    ):
        """測試：取得有資料的通知列表"""
        user = test_user_with_token["user"]

        # 建立測試通知
        notification1 = Notification(
            user_id=user.id,
            type="notification_liked",
            title="有人喜歡你！"
        )
        notification2 = Notification(
            user_id=user.id,
            type="notification_match",
            title="新配對！",
            data={"match_id": str(uuid.uuid4())}
        )
        test_db.add(notification1)
        test_db.add(notification2)
        await test_db.commit()

        response = await client.get(
            "/api/notifications",
            headers={"Authorization": f"Bearer {test_user_with_token['token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["notifications"]) == 2
        assert data["total"] == 2
        assert data["unread_count"] == 2

    @pytest.mark.asyncio
    async def test_get_notifications_pagination(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        test_user_with_token
    ):
        """測試：通知列表分頁"""
        user = test_user_with_token["user"]

        # 建立 5 個通知
        for i in range(5):
            notification = Notification(
                user_id=user.id,
                type="notification_liked",
                title=f"通知 {i}"
            )
            test_db.add(notification)
        await test_db.commit()

        # 取得前 2 個
        response = await client.get(
            "/api/notifications?limit=2&offset=0",
            headers={"Authorization": f"Bearer {test_user_with_token['token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["notifications"]) == 2
        assert data["total"] == 5

        # 取得後 2 個
        response = await client.get(
            "/api/notifications?limit=2&offset=2",
            headers={"Authorization": f"Bearer {test_user_with_token['token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["notifications"]) == 2

    @pytest.mark.asyncio
    async def test_get_notifications_unread_only(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        test_user_with_token
    ):
        """測試：只取得未讀通知"""
        user = test_user_with_token["user"]

        # 建立 2 個未讀 + 1 個已讀
        notification1 = Notification(
            user_id=user.id,
            type="notification_liked",
            title="未讀 1",
            is_read=False
        )
        notification2 = Notification(
            user_id=user.id,
            type="notification_liked",
            title="未讀 2",
            is_read=False
        )
        notification3 = Notification(
            user_id=user.id,
            type="notification_liked",
            title="已讀",
            is_read=True
        )
        test_db.add_all([notification1, notification2, notification3])
        await test_db.commit()

        response = await client.get(
            "/api/notifications?unread_only=true",
            headers={"Authorization": f"Bearer {test_user_with_token['token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["notifications"]) == 2
        assert all(n["is_read"] is False for n in data["notifications"])

    @pytest.mark.asyncio
    async def test_get_unread_count_zero(self, client: AsyncClient, test_user_with_token):
        """測試：取得未讀數量（為 0）"""
        response = await client.get(
            "/api/notifications/unread-count",
            headers={"Authorization": f"Bearer {test_user_with_token['token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["unread_count"] == 0

    @pytest.mark.asyncio
    async def test_get_unread_count_with_unread(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        test_user_with_token
    ):
        """測試：取得未讀數量（有未讀）"""
        user = test_user_with_token["user"]

        # 建立 3 個未讀通知
        for _ in range(3):
            notification = Notification(
                user_id=user.id,
                type="notification_liked",
                title="有人喜歡你！"
            )
            test_db.add(notification)
        await test_db.commit()

        response = await client.get(
            "/api/notifications/unread-count",
            headers={"Authorization": f"Bearer {test_user_with_token['token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["unread_count"] == 3

    @pytest.mark.asyncio
    async def test_mark_single_notification_as_read(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        test_user_with_token
    ):
        """測試：標記單個通知為已讀"""
        user = test_user_with_token["user"]

        notification = Notification(
            user_id=user.id,
            type="notification_liked",
            title="有人喜歡你！",
            is_read=False
        )
        test_db.add(notification)
        await test_db.commit()
        await test_db.refresh(notification)

        response = await client.put(
            f"/api/notifications/{notification.id}/read",
            headers={"Authorization": f"Bearer {test_user_with_token['token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # 驗證資料庫
        await test_db.refresh(notification)
        assert notification.is_read is True

    @pytest.mark.asyncio
    async def test_mark_all_notifications_as_read(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        test_user_with_token
    ):
        """測試：標記全部通知為已讀"""
        user = test_user_with_token["user"]

        # 建立 3 個未讀通知
        notifications = []
        for _ in range(3):
            notification = Notification(
                user_id=user.id,
                type="notification_liked",
                title="有人喜歡你！",
                is_read=False
            )
            test_db.add(notification)
            notifications.append(notification)
        await test_db.commit()

        response = await client.put(
            "/api/notifications/read-all",
            headers={"Authorization": f"Bearer {test_user_with_token['token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # 驗證未讀數量為 0
        response = await client.get(
            "/api/notifications/unread-count",
            headers={"Authorization": f"Bearer {test_user_with_token['token']}"}
        )
        assert response.json()["unread_count"] == 0

    @pytest.mark.asyncio
    async def test_delete_notification(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        test_user_with_token
    ):
        """測試：刪除通知"""
        user = test_user_with_token["user"]

        notification = Notification(
            user_id=user.id,
            type="notification_liked",
            title="有人喜歡你！"
        )
        test_db.add(notification)
        await test_db.commit()
        await test_db.refresh(notification)
        notification_id = notification.id

        response = await client.delete(
            f"/api/notifications/{notification_id}",
            headers={"Authorization": f"Bearer {test_user_with_token['token']}"}
        )

        assert response.status_code == 200

        # 驗證已刪除
        result = await test_db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: AsyncClient):
        """測試：未授權存取"""
        response = await client.get("/api/notifications")
        assert response.status_code in [401, 403]

        response = await client.get("/api/notifications/unread-count")
        assert response.status_code in [401, 403]


# ==================== TestNotificationAutoCreate ====================

class TestNotificationAutoCreate:
    """通知自動建立測試（Like/Match/Message 觸發時寫入 DB）"""

    @pytest.mark.asyncio
    async def test_like_creates_notification_liked_in_db(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        notification_users: dict
    ):
        """測試：單方 Like 時在 DB 建立 notification_liked"""
        alice = notification_users["alice"]
        bob = notification_users["bob"]

        # Alice 瀏覽取得 Bob
        response = await client.get(
            "/api/discovery/browse?limit=10",
            headers={"Authorization": f"Bearer {alice['token']}"}
        )
        candidates = response.json()
        if len(candidates) == 0:
            pytest.skip("沒有可配對的候選人")

        bob_user_id = candidates[0]["user_id"]

        # Mock WebSocket 發送
        with patch.object(manager, 'send_personal_message', new_callable=AsyncMock):
            # Alice 喜歡 Bob
            response = await client.post(
                f"/api/discovery/like/{bob_user_id}",
                headers={"Authorization": f"Bearer {alice['token']}"}
            )
            assert response.status_code == 200
            assert response.json()["is_match"] is False

        # 驗證 DB 中有 notification_liked 通知
        result = await test_db.execute(
            select(Notification).where(
                Notification.user_id == uuid.UUID(bob_user_id),
                Notification.type == "notification_liked"
            )
        )
        notification = result.scalar_one_or_none()

        assert notification is not None, "應該在 DB 建立 notification_liked"
        assert notification.type == "notification_liked"
        assert notification.is_read is False

    @pytest.mark.asyncio
    async def test_match_creates_notification_match_in_db(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        notification_users: dict
    ):
        """測試：互相 Like 時在 DB 建立 notification_match 給雙方"""
        alice = notification_users["alice"]
        bob = notification_users["bob"]

        # 取得雙方 user_id
        response = await client.get(
            "/api/discovery/browse?limit=10",
            headers={"Authorization": f"Bearer {alice['token']}"}
        )
        candidates = response.json()
        if len(candidates) == 0:
            pytest.skip("沒有可配對的候選人")
        bob_user_id = candidates[0]["user_id"]

        response = await client.get(
            "/api/discovery/browse?limit=10",
            headers={"Authorization": f"Bearer {bob['token']}"}
        )
        candidates = response.json()
        alice_user_id = next(
            (c["user_id"] for c in candidates if "Alice" in c["display_name"]),
            None
        )
        if not alice_user_id:
            pytest.skip("Bob 看不到 Alice")

        # Alice 先喜歡 Bob
        with patch.object(manager, 'send_personal_message', new_callable=AsyncMock):
            await client.post(
                f"/api/discovery/like/{bob_user_id}",
                headers={"Authorization": f"Bearer {alice['token']}"}
            )

        # Bob 喜歡 Alice（觸發配對）
        with patch.object(manager, 'send_personal_message', new_callable=AsyncMock):
            response = await client.post(
                f"/api/discovery/like/{alice_user_id}",
                headers={"Authorization": f"Bearer {bob['token']}"}
            )
            assert response.status_code == 200
            assert response.json()["is_match"] is True

        # 驗證 DB 中有給 Alice 的 notification_match
        result = await test_db.execute(
            select(Notification).where(
                Notification.user_id == uuid.UUID(alice_user_id),
                Notification.type == "notification_match"
            )
        )
        alice_notification = result.scalar_one_or_none()
        assert alice_notification is not None, "Alice 應該收到 notification_match"

        # 驗證 DB 中有給 Bob 的 notification_match
        result = await test_db.execute(
            select(Notification).where(
                Notification.user_id == uuid.UUID(bob_user_id),
                Notification.type == "notification_match"
            )
        )
        bob_notification = result.scalar_one_or_none()
        assert bob_notification is not None, "Bob 應該收到 notification_match"
