"""Moderation API 端點測試

測試敏感詞管理 API 的序列化和權限控制。
確保 Schema 中的 UUID 類型正確序列化。
"""

import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.moderation import ContentAppeal, SensitiveWord
from app.models.profile import Photo, Profile
from app.models.user import User

# ==================== Fixtures ====================


@pytest_asyncio.fixture
async def admin_user(test_db: AsyncSession) -> User:
    """創建管理員用戶"""
    user = User(
        id=uuid.uuid4(),
        email="admin_test@example.com",
        password_hash=get_password_hash("Admin123"),
        date_of_birth=date(1990, 1, 1),
        is_active=True,
        is_admin=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def normal_user(test_db: AsyncSession) -> User:
    """創建一般用戶（非管理員）"""
    user = User(
        id=uuid.uuid4(),
        email="normal_test@example.com",
        password_hash=get_password_hash("Normal123"),
        date_of_birth=date(1990, 1, 1),
        is_active=True,
        is_admin=False,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, admin_user: User) -> dict:
    """獲取管理員認證 Headers"""
    response = await client.post(
        "/api/auth/admin-login", json={"email": "admin_test@example.com", "password": "Admin123"}
    )
    token = response.json()["access_token"]
    # 清除 cookies，讓測試使用純 Bearer Token 認證
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def normal_headers(client: AsyncClient, normal_user: User) -> dict:
    """獲取一般用戶認證 Headers"""
    response = await client.post(
        "/api/auth/login", json={"email": "normal_test@example.com", "password": "Normal123"}
    )
    token = response.json()["access_token"]
    # 清除 cookies，讓測試使用純 Bearer Token 認證
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def sensitive_words(test_db: AsyncSession) -> list:
    """創建測試敏感詞"""
    words = [
        SensitiveWord(
            id=uuid.uuid4(),
            word="測試敏感詞1",
            category="SEXUAL",
            severity="HIGH",
            action="REJECT",
            is_regex=False,
            is_active=True,
        ),
        SensitiveWord(
            id=uuid.uuid4(),
            word="測試敏感詞2",
            category="SCAM",
            severity="MEDIUM",
            action="WARN",
            is_regex=False,
            is_active=True,
        ),
    ]
    for word in words:
        test_db.add(word)
    await test_db.commit()
    return words


# ==================== 敏感詞列表 API 測試 ====================


@pytest.mark.asyncio
class TestGetSensitiveWords:
    """GET /api/moderation/sensitive-words 測試"""

    async def test_get_sensitive_words_success(
        self, client: AsyncClient, admin_headers: dict, sensitive_words: list
    ):
        """測試：管理員成功獲取敏感詞列表"""
        response = await client.get("/api/moderation/sensitive-words", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()

        # 驗證結構
        assert "words" in data
        assert "total" in data
        assert data["total"] >= 2

        # 驗證 UUID 序列化正確（關鍵測試點）
        for word in data["words"]:
            assert "id" in word
            # UUID 應該是有效的 UUID 字串格式
            uuid.UUID(word["id"])  # 如果格式錯誤會拋出異常

    async def test_get_sensitive_words_unauthorized(self, client: AsyncClient):
        """測試：無 Token 返回 401 Unauthorized"""
        response = await client.get("/api/moderation/sensitive-words")

        assert response.status_code == 401

    async def test_get_sensitive_words_forbidden(self, client: AsyncClient, normal_headers: dict):
        """測試：非管理員返回 403"""
        response = await client.get("/api/moderation/sensitive-words", headers=normal_headers)

        assert response.status_code == 403


# ==================== 新增敏感詞 API 測試 ====================


@pytest.mark.asyncio
class TestCreateSensitiveWord:
    """POST /api/moderation/sensitive-words 測試"""

    async def test_create_sensitive_word_success(self, client: AsyncClient, admin_headers: dict):
        """測試：管理員成功新增敏感詞"""
        new_word = {
            "word": "新測試敏感詞",
            "category": "HARASSMENT",
            "severity": "HIGH",
            "action": "REJECT",
        }

        response = await client.post(
            "/api/moderation/sensitive-words", json=new_word, headers=admin_headers
        )

        assert response.status_code == 201
        data = response.json()

        # 驗證 UUID 序列化正確
        assert "id" in data
        uuid.UUID(data["id"])  # 驗證 UUID 格式

        # 驗證內容
        assert data["word"] == "新測試敏感詞"
        assert data["category"] == "HARASSMENT"

    async def test_create_sensitive_word_duplicate(
        self, client: AsyncClient, admin_headers: dict, sensitive_words: list
    ):
        """測試：重複敏感詞返回 400"""
        duplicate_word = {
            "word": "測試敏感詞1",  # 已存在
            "category": "SEXUAL",
            "severity": "HIGH",
            "action": "REJECT",
        }

        response = await client.post(
            "/api/moderation/sensitive-words", json=duplicate_word, headers=admin_headers
        )

        assert response.status_code == 400
        assert "已存在" in response.json()["detail"]


# ==================== 統計 API 測試 ====================


@pytest.mark.asyncio
class TestModerationStats:
    """GET /api/moderation/stats 測試"""

    async def test_get_moderation_stats_success(
        self, client: AsyncClient, admin_headers: dict, sensitive_words: list
    ):
        """測試：管理員成功獲取統計數據"""
        response = await client.get("/api/moderation/stats", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()

        # 驗證統計欄位存在且為數字
        assert isinstance(data["total_sensitive_words"], int)
        assert isinstance(data["active_sensitive_words"], int)
        assert isinstance(data["total_appeals"], int)
        assert isinstance(data["pending_appeals"], int)
        assert data["total_sensitive_words"] >= 2


# ==================== 申訴審核 API 測試 ====================


@pytest_asyncio.fixture
async def photo_appeal(test_db: AsyncSession, normal_user: User) -> ContentAppeal:
    """建立照片類申訴（照片已駁回、實體檔案在隔離區）"""
    appeal = ContentAppeal(
        id=uuid.uuid4(),
        user_id=normal_user.id,
        appeal_type="PHOTO",
        rejected_content="/uploads/photos/test-user/rejected.jpg",
        violations='["垃圾內容"]',
        reason="這張照片是我本人的生活照，並沒有任何違規內容，請重新審視。",
    )
    test_db.add(appeal)
    await test_db.commit()
    await test_db.refresh(appeal)
    return appeal


@pytest.mark.asyncio
class TestReviewAppeal:
    """POST /api/moderation/appeals/{id}/review 測試"""

    async def test_approve_refunds_trust_score_and_purges_quarantine(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        admin_headers: dict,
        normal_user: User,
        photo_appeal: ContentAppeal,
    ):
        """申訴通過：退還信任分（content_violation 的鏡像 +3）並清除隔離檔案"""
        normal_user.trust_score = 40
        await test_db.commit()

        with patch("app.api.moderation.file_storage.delete_quarantined_photo") as mock_purge:
            response = await client.post(
                f"/api/moderation/appeals/{photo_appeal.id}/review",
                headers=admin_headers,
                json={"status": "APPROVED", "admin_response": "確認為誤判，造成不便敬請見諒"},
            )

        assert response.status_code == 200
        assert response.json()["status"] == "APPROVED"

        await test_db.refresh(normal_user)
        assert normal_user.trust_score == 43

        mock_purge.assert_called_once_with("/uploads/photos/test-user/rejected.jpg")

    async def test_reject_appeal_no_refund_but_purges_quarantine(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        admin_headers: dict,
        normal_user: User,
        photo_appeal: ContentAppeal,
    ):
        """申訴駁回：不退分，但照片申訴已審結、隔離檔案一樣清除"""
        normal_user.trust_score = 40
        await test_db.commit()

        with patch("app.api.moderation.file_storage.delete_quarantined_photo") as mock_purge:
            response = await client.post(
                f"/api/moderation/appeals/{photo_appeal.id}/review",
                headers=admin_headers,
                json={"status": "REJECTED", "admin_response": "經複審後確認仍屬違規內容"},
            )

        assert response.status_code == 200
        assert response.json()["status"] == "REJECTED"

        await test_db.refresh(normal_user)
        assert normal_user.trust_score == 40

        mock_purge.assert_called_once_with("/uploads/photos/test-user/rejected.jpg")

    async def test_approve_non_photo_appeal_refunds_without_purge(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        admin_headers: dict,
        normal_user: User,
    ):
        """非照片類申訴通過：退分但不動隔離區"""
        appeal = ContentAppeal(
            id=uuid.uuid4(),
            user_id=normal_user.id,
            appeal_type="MESSAGE",
            rejected_content="被誤判的訊息內容",
            violations='["測試敏感詞"]',
            reason="這句話只是日常對話，沒有任何違規意圖，請重新審視。",
        )
        test_db.add(appeal)
        normal_user.trust_score = 40
        await test_db.commit()

        with patch("app.api.moderation.file_storage.delete_quarantined_photo") as mock_purge:
            response = await client.post(
                f"/api/moderation/appeals/{appeal.id}/review",
                headers=admin_headers,
                json={"status": "APPROVED", "admin_response": "經複審確認為系統誤判"},
            )

        assert response.status_code == 200

        await test_db.refresh(normal_user)
        assert normal_user.trust_score == 43

        mock_purge.assert_not_called()

    async def test_review_appeal_requires_admin(
        self,
        client: AsyncClient,
        normal_headers: dict,
        photo_appeal: ContentAppeal,
    ):
        """一般用戶無法審核申訴"""
        response = await client.post(
            f"/api/moderation/appeals/{photo_appeal.id}/review",
            headers=normal_headers,
            json={"status": "APPROVED", "admin_response": "回覆"},
        )
        assert response.status_code == 403


# ==================== 申訴建立與照片還原測試 ====================


@pytest_asyncio.fixture
async def rejected_photo(test_db: AsyncSession, normal_user: User) -> Photo:
    """建立 normal_user 名下的駁回照片"""
    profile = Profile(
        id=uuid.uuid4(),
        user_id=normal_user.id,
        display_name="申訴測試用戶",
        gender="female",
        bio="測試簡介",
    )
    test_db.add(profile)
    await test_db.commit()

    photo = Photo(
        id=uuid.uuid4(),
        profile_id=profile.id,
        url=f"/uploads/photos/{normal_user.id}/rejected.jpg",
        thumbnail_url=f"/uploads/photos/{normal_user.id}/rejected_thumb.jpg",
        display_order=0,
        is_profile_picture=False,
        moderation_status="REJECTED",
        rejection_reason="仇恨言論",
        file_size=102400,
        width=800,
        height=600,
        mime_type="image/jpeg",
    )
    test_db.add(photo)
    await test_db.commit()
    await test_db.refresh(photo)
    return photo


APPEAL_REASON = "這張照片是我本人的生活照，並沒有任何違規內容，請重新審視，謝謝。"


@pytest.mark.asyncio
class TestCreateAppeal:
    """POST /api/moderation/appeals 測試（防重複與歸屬驗證）"""

    async def test_create_photo_appeal_success(
        self, client: AsyncClient, normal_headers: dict, rejected_photo: Photo
    ):
        """本人的駁回照片可以申訴"""
        response = await client.post(
            "/api/moderation/appeals",
            headers=normal_headers,
            json={
                "appeal_type": "PHOTO",
                "rejected_content": rejected_photo.url,
                "violations": '["仇恨言論"]',
                "reason": APPEAL_REASON,
            },
        )
        assert response.status_code == 201
        assert response.json()["status"] == "PENDING"

    async def test_duplicate_appeal_blocked(
        self, client: AsyncClient, normal_headers: dict, rejected_photo: Photo
    ):
        """同一內容不可重複申訴（防重複退分刷分）"""
        payload = {
            "appeal_type": "PHOTO",
            "rejected_content": rejected_photo.url,
            "violations": '["仇恨言論"]',
            "reason": APPEAL_REASON,
        }
        first = await client.post("/api/moderation/appeals", headers=normal_headers, json=payload)
        assert first.status_code == 201

        second = await client.post("/api/moderation/appeals", headers=normal_headers, json=payload)
        assert second.status_code == 400
        assert "已提出過申訴" in second.json()["detail"]

    async def test_appeal_nonexistent_photo_blocked(
        self, client: AsyncClient, normal_headers: dict
    ):
        """不存在的照片 URL 不可申訴"""
        response = await client.post(
            "/api/moderation/appeals",
            headers=normal_headers,
            json={
                "appeal_type": "PHOTO",
                "rejected_content": "/uploads/photos/nobody/ghost.jpg",
                "violations": '["垃圾內容"]',
                "reason": APPEAL_REASON,
            },
        )
        assert response.status_code == 400
        assert "只能申訴自己被駁回的照片" in response.json()["detail"]

    async def test_appeal_non_rejected_photo_blocked(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        normal_headers: dict,
        rejected_photo: Photo,
    ):
        """非駁回狀態的照片不可申訴（還原後不可再申訴）"""
        rejected_photo.moderation_status = "APPROVED"
        await test_db.commit()

        response = await client.post(
            "/api/moderation/appeals",
            headers=normal_headers,
            json={
                "appeal_type": "PHOTO",
                "rejected_content": rejected_photo.url,
                "violations": '["仇恨言論"]',
                "reason": APPEAL_REASON,
            },
        )
        assert response.status_code == 400
        assert "只能申訴自己被駁回的照片" in response.json()["detail"]


@pytest.mark.asyncio
class TestAppealPhotoRestore:
    """申訴通過還原照片測試"""

    async def test_approve_restores_photo(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        admin_headers: dict,
        normal_user: User,
        rejected_photo: Photo,
    ):
        """申訴通過：照片還原為 APPROVED、清駁回原因、補主頭像、檔案搬回、不清隔離檔"""
        appeal = ContentAppeal(
            id=uuid.uuid4(),
            user_id=normal_user.id,
            appeal_type="PHOTO",
            rejected_content=rejected_photo.url,
            violations='["仇恨言論"]',
            reason=APPEAL_REASON,
        )
        test_db.add(appeal)
        await test_db.commit()

        with (
            patch(
                "app.services.photo_moderation.file_storage.get_quarantined_path",
                return_value="/quarantine/rejected.jpg",
            ),
            patch(
                "app.services.photo_moderation.file_storage.restore_photo",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_restore,
            patch("app.api.moderation.file_storage.delete_quarantined_photo") as mock_purge,
        ):
            response = await client.post(
                f"/api/moderation/appeals/{appeal.id}/review",
                headers=admin_headers,
                json={"status": "APPROVED", "admin_response": "確認為誤判，照片已恢復上架"},
            )

        assert response.status_code == 200

        await test_db.refresh(rejected_photo)
        assert rejected_photo.moderation_status == "APPROVED"
        assert rejected_photo.rejection_reason is None
        # 原本沒有主頭像，還原的照片遞補
        assert rejected_photo.is_profile_picture is True

        mock_restore.assert_awaited_once_with(rejected_photo.url)
        mock_purge.assert_not_called()

    async def test_approve_not_owned_photo_no_restore(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        admin_headers: dict,
        admin_user: User,
        rejected_photo: Photo,
    ):
        """申訴人非照片擁有者：不還原、也不動他人的隔離檔"""
        appeal = ContentAppeal(
            id=uuid.uuid4(),
            user_id=admin_user.id,  # 申訴人不是照片擁有者
            appeal_type="PHOTO",
            rejected_content=rejected_photo.url,
            violations='["仇恨言論"]',
            reason=APPEAL_REASON,
        )
        test_db.add(appeal)
        await test_db.commit()

        with (
            patch(
                "app.services.photo_moderation.file_storage.restore_photo",
                new_callable=AsyncMock,
            ) as mock_restore,
            patch("app.api.moderation.file_storage.delete_quarantined_photo") as mock_purge,
        ):
            response = await client.post(
                f"/api/moderation/appeals/{appeal.id}/review",
                headers=admin_headers,
                json={"status": "APPROVED", "admin_response": "測試用歸屬不符情境回覆"},
            )

        assert response.status_code == 200

        await test_db.refresh(rejected_photo)
        assert rejected_photo.moderation_status == "REJECTED"
        mock_restore.assert_not_awaited()
        mock_purge.assert_not_called()

    async def test_approve_quarantine_file_missing_no_restore(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        admin_headers: dict,
        normal_user: User,
        rejected_photo: Photo,
    ):
        """隔離檔不存在：不改狀態（避免公開面出現破圖），也不清檔"""
        appeal = ContentAppeal(
            id=uuid.uuid4(),
            user_id=normal_user.id,
            appeal_type="PHOTO",
            rejected_content=rejected_photo.url,
            violations='["仇恨言論"]',
            reason=APPEAL_REASON,
        )
        test_db.add(appeal)
        await test_db.commit()

        with (
            patch(
                "app.services.photo_moderation.file_storage.get_quarantined_path",
                return_value=None,
            ),
            patch("app.api.moderation.file_storage.delete_quarantined_photo") as mock_purge,
        ):
            response = await client.post(
                f"/api/moderation/appeals/{appeal.id}/review",
                headers=admin_headers,
                json={"status": "APPROVED", "admin_response": "測試用隔離檔遺失情境回覆"},
            )

        assert response.status_code == 200

        await test_db.refresh(rejected_photo)
        assert rejected_photo.moderation_status == "REJECTED"
        mock_purge.assert_not_called()
