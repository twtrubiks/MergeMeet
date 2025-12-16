"""Moderation API 端點測試

測試敏感詞管理 API 的序列化和權限控制。
確保 Schema 中的 UUID 類型正確序列化。
"""
import pytest
import pytest_asyncio
import uuid
from datetime import date
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.moderation import SensitiveWord
from app.core.security import get_password_hash


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
        is_admin=True
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
        is_admin=False
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, admin_user: User) -> dict:
    """獲取管理員認證 Headers"""
    response = await client.post("/api/auth/admin-login", json={
        "email": "admin_test@example.com",
        "password": "Admin123"
    })
    token = response.json()["access_token"]
    # 清除 cookies，讓測試使用純 Bearer Token 認證
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def normal_headers(client: AsyncClient, normal_user: User) -> dict:
    """獲取一般用戶認證 Headers"""
    response = await client.post("/api/auth/login", json={
        "email": "normal_test@example.com",
        "password": "Normal123"
    })
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
            is_active=True
        ),
        SensitiveWord(
            id=uuid.uuid4(),
            word="測試敏感詞2",
            category="SCAM",
            severity="MEDIUM",
            action="WARN",
            is_regex=False,
            is_active=True
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
        self,
        client: AsyncClient,
        admin_headers: dict,
        sensitive_words: list
    ):
        """測試：管理員成功獲取敏感詞列表"""
        response = await client.get(
            "/api/moderation/sensitive-words",
            headers=admin_headers
        )

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

    async def test_get_sensitive_words_forbidden(
        self,
        client: AsyncClient,
        normal_headers: dict
    ):
        """測試：非管理員返回 403"""
        response = await client.get(
            "/api/moderation/sensitive-words",
            headers=normal_headers
        )

        assert response.status_code == 403


# ==================== 新增敏感詞 API 測試 ====================

@pytest.mark.asyncio
class TestCreateSensitiveWord:
    """POST /api/moderation/sensitive-words 測試"""

    async def test_create_sensitive_word_success(
        self,
        client: AsyncClient,
        admin_headers: dict
    ):
        """測試：管理員成功新增敏感詞"""
        new_word = {
            "word": "新測試敏感詞",
            "category": "HARASSMENT",
            "severity": "HIGH",
            "action": "REJECT"
        }

        response = await client.post(
            "/api/moderation/sensitive-words",
            json=new_word,
            headers=admin_headers
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
        self,
        client: AsyncClient,
        admin_headers: dict,
        sensitive_words: list
    ):
        """測試：重複敏感詞返回 400"""
        duplicate_word = {
            "word": "測試敏感詞1",  # 已存在
            "category": "SEXUAL",
            "severity": "HIGH",
            "action": "REJECT"
        }

        response = await client.post(
            "/api/moderation/sensitive-words",
            json=duplicate_word,
            headers=admin_headers
        )

        assert response.status_code == 400
        assert "已存在" in response.json()["detail"]


# ==================== 統計 API 測試 ====================

@pytest.mark.asyncio
class TestModerationStats:
    """GET /api/moderation/stats 測試"""

    async def test_get_moderation_stats_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        sensitive_words: list
    ):
        """測試：管理員成功獲取統計數據"""
        response = await client.get(
            "/api/moderation/stats",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        # 驗證統計欄位存在且為數字
        assert isinstance(data["total_sensitive_words"], int)
        assert isinstance(data["active_sensitive_words"], int)
        assert isinstance(data["total_appeals"], int)
        assert isinstance(data["pending_appeals"], int)
        assert data["total_sensitive_words"] >= 2
