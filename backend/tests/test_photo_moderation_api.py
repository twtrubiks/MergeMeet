"""照片審核 API 測試"""
import io
import uuid
from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Photo, Profile
from app.models.user import User
from app.core.security import create_access_token


# ========== Fixtures ==========


@pytest_asyncio.fixture
async def test_user(test_db: AsyncSession):
    """建立測試用戶"""
    user = User(
        id=uuid.uuid4(),
        email="user@example.com",
        password_hash="$2b$12$dummy_hash",
        date_of_birth=date(1995, 1, 1),
        is_active=True,
        email_verified=True,
        trust_score=50
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(test_db: AsyncSession):
    """建立管理員用戶"""
    admin = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        password_hash="$2b$12$dummy_hash",
        date_of_birth=date(1990, 1, 1),
        is_active=True,
        email_verified=True,
        is_admin=True,
        trust_score=100
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def test_profile(test_db: AsyncSession, test_user: User):
    """建立測試個人檔案"""
    profile = Profile(
        id=uuid.uuid4(),
        user_id=test_user.id,
        display_name="測試用戶",
        gender="male",
        bio="測試簡介"
    )
    test_db.add(profile)
    await test_db.commit()
    await test_db.refresh(profile)
    return profile


@pytest_asyncio.fixture
async def pending_photo(test_db: AsyncSession, test_profile: Profile):
    """建立待審核照片"""
    photo = Photo(
        id=uuid.uuid4(),
        profile_id=test_profile.id,
        url="/uploads/photos/test/pending.jpg",
        thumbnail_url="/uploads/photos/test/pending_thumb.jpg",
        display_order=0,
        is_profile_picture=True,
        moderation_status="PENDING",
        file_size=102400,
        width=800,
        height=600,
        mime_type="image/jpeg"
    )
    test_db.add(photo)
    await test_db.commit()
    await test_db.refresh(photo)
    return photo


@pytest.fixture
def user_token(test_user: User):
    """一般用戶 Token"""
    return create_access_token(data={"sub": str(test_user.id)})


@pytest.fixture
def admin_token(admin_user: User):
    """管理員 Token"""
    return create_access_token(data={"sub": str(admin_user.id)})


@pytest.fixture
def sample_image_bytes():
    """產生測試用 JPEG 圖片"""
    img = Image.new('RGB', (800, 600), color='blue')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer.read()


# ========== API Tests ==========


@pytest.mark.asyncio
class TestPhotoModerationAPIPermissions:
    """照片審核 API 權限測試"""

    async def test_get_pending_photos_requires_admin(
        self, client: AsyncClient, user_token: str
    ):
        """測試：一般用戶無法存取待審核照片列表"""
        response = await client.get(
            "/api/admin/photos/pending",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403

    async def test_get_pending_photos_requires_auth(
        self, client: AsyncClient
    ):
        """測試：未認證無法存取待審核照片列表"""
        response = await client.get("/api/admin/photos/pending")
        assert response.status_code == 401

    async def test_review_photo_requires_admin(
        self, client: AsyncClient, user_token: str, pending_photo: Photo
    ):
        """測試：一般用戶無法審核照片"""
        response = await client.post(
            f"/api/admin/photos/{pending_photo.id}/review",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"status": "APPROVED"}
        )
        assert response.status_code == 403


@pytest.mark.asyncio
class TestGetPendingPhotosAPI:
    """取得待審核照片 API 測試"""

    async def test_get_pending_photos_success(
        self, client: AsyncClient, admin_token: str, pending_photo: Photo
    ):
        """測試：管理員成功取得待審核照片"""
        response = await client.get(
            "/api/admin/photos/pending",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "photos" in data
        assert "total" in data
        assert data["total"] >= 1

    async def test_get_pending_photos_with_pagination(
        self, client: AsyncClient, admin_token: str
    ):
        """測試：分頁功能"""
        response = await client.get(
            "/api/admin/photos/pending?page=1&page_size=10",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    async def test_get_pending_photos_with_status_filter(
        self, client: AsyncClient, admin_token: str
    ):
        """測試：狀態篩選"""
        response = await client.get(
            "/api/admin/photos/pending?status=PENDING",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200


@pytest.mark.asyncio
class TestGetPhotoStatsAPI:
    """照片統計 API 測試"""

    async def test_get_photo_stats_success(
        self, client: AsyncClient, admin_token: str, pending_photo: Photo
    ):
        """測試：成功取得統計數據"""
        response = await client.get(
            "/api/admin/photos/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_photos" in data
        assert "pending_photos" in data
        assert "approved_photos" in data
        assert "rejected_photos" in data
        assert "today_pending" in data
        assert "today_reviewed" in data


@pytest.mark.asyncio
class TestGetPhotoDetailAPI:
    """照片詳情 API 測試"""

    async def test_get_photo_detail_success(
        self, client: AsyncClient, admin_token: str, pending_photo: Photo
    ):
        """測試：成功取得照片詳情"""
        response = await client.get(
            f"/api/admin/photos/{pending_photo.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(pending_photo.id)
        assert data["moderation_status"] == "PENDING"

    async def test_get_photo_detail_not_found(
        self, client: AsyncClient, admin_token: str
    ):
        """測試：照片不存在"""
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/admin/photos/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 404

    async def test_get_photo_detail_invalid_id(
        self, client: AsyncClient, admin_token: str
    ):
        """測試：無效照片 ID"""
        response = await client.get(
            "/api/admin/photos/invalid-uuid",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # FastAPI 使用 UUID 類型註解，無效 UUID 會返回 422 Validation Error
        assert response.status_code == 422


@pytest.mark.asyncio
class TestReviewPhotoAPI:
    """審核照片 API 測試"""

    async def test_approve_photo_success(
        self, client: AsyncClient, admin_token: str, pending_photo: Photo
    ):
        """測試：成功批准照片"""
        response = await client.post(
            f"/api/admin/photos/{pending_photo.id}/review",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "APPROVED"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "APPROVED"

    async def test_reject_photo_with_reason_success(
        self, client: AsyncClient, admin_token: str, pending_photo: Photo
    ):
        """測試：成功拒絕照片（附原因）"""
        response = await client.post(
            f"/api/admin/photos/{pending_photo.id}/review",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "status": "REJECTED",
                "rejection_reason": "照片包含不當內容"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "REJECTED"

    async def test_reject_photo_without_reason_fails(
        self, client: AsyncClient, admin_token: str, pending_photo: Photo
    ):
        """測試：拒絕照片未提供原因應失敗"""
        response = await client.post(
            f"/api/admin/photos/{pending_photo.id}/review",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "REJECTED"}
        )

        assert response.status_code == 400

    async def test_review_photo_invalid_status(
        self, client: AsyncClient, admin_token: str, pending_photo: Photo
    ):
        """測試：無效審核狀態"""
        response = await client.post(
            f"/api/admin/photos/{pending_photo.id}/review",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "INVALID"}
        )

        assert response.status_code == 422  # Pydantic validation error

    async def test_review_nonexistent_photo(
        self, client: AsyncClient, admin_token: str
    ):
        """測試：審核不存在的照片"""
        fake_id = uuid.uuid4()
        response = await client.post(
            f"/api/admin/photos/{fake_id}/review",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "APPROVED"}
        )

        assert response.status_code == 400


@pytest.mark.asyncio
class TestPhotoUploadWithModeration:
    """照片上傳審核狀態測試"""

    async def test_uploaded_photo_has_pending_status(
        self, client: AsyncClient, test_user: User, test_profile: Profile,
        user_token: str, sample_image_bytes
    ):
        """測試：上傳的照片狀態為 PENDING"""
        with patch('app.services.file_storage.file_storage.save_photo') as mock_save:
            mock_save.return_value = (
                str(uuid.uuid4()),
                "/uploads/photos/test/new.jpg",
                "/uploads/photos/test/new_thumb.jpg"
            )

            response = await client.post(
                "/api/profile/photos",
                headers={"Authorization": f"Bearer {user_token}"},
                files={"file": ("test.jpg", io.BytesIO(sample_image_bytes), "image/jpeg")}
            )

            assert response.status_code == 201
            data = response.json()
            assert data["moderation_status"] == "PENDING"
