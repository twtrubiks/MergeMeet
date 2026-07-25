"""照片審核功能測試"""

import io
import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import InterestTag, Photo, Profile
from app.models.user import User
from app.services.photo_moderation import PhotoModerationService

# ========== Fixtures ==========


@pytest_asyncio.fixture
async def test_user(test_db: AsyncSession):
    """建立測試用戶"""
    user = User(
        id=uuid.uuid4(),
        email="photo_test@example.com",
        password_hash="$2b$12$dummy_hash_for_testing",
        date_of_birth=date(1995, 1, 1),
        is_active=True,
        email_verified=True,
        trust_score=50,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_profile(test_db: AsyncSession, test_user: User):
    """建立測試個人檔案"""
    profile = Profile(
        id=uuid.uuid4(),
        user_id=test_user.id,
        display_name="測試用戶",
        gender="male",
        bio="這是測試簡介",
    )
    test_db.add(profile)
    await test_db.commit()
    await test_db.refresh(profile)
    return profile


@pytest_asyncio.fixture
async def admin_user(test_db: AsyncSession):
    """建立管理員用戶"""
    admin = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        password_hash="$2b$12$dummy_hash_for_testing",
        date_of_birth=date(1990, 1, 1),
        is_active=True,
        email_verified=True,
        is_admin=True,
        trust_score=100,
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def pending_photo(test_db: AsyncSession, test_profile: Profile):
    """建立待審核照片"""
    photo = Photo(
        id=uuid.uuid4(),
        profile_id=test_profile.id,
        url="/uploads/photos/test/test_photo.jpg",
        thumbnail_url="/uploads/photos/test/test_photo_thumb.jpg",
        display_order=0,
        is_profile_picture=True,
        moderation_status="PENDING",
        file_size=102400,
        width=800,
        height=600,
        mime_type="image/jpeg",
    )
    test_db.add(photo)
    await test_db.commit()
    await test_db.refresh(photo)
    return photo


@pytest_asyncio.fixture
async def approved_photo(test_db: AsyncSession, test_profile: Profile):
    """建立已審核照片"""
    photo = Photo(
        id=uuid.uuid4(),
        profile_id=test_profile.id,
        url="/uploads/photos/test/approved_photo.jpg",
        thumbnail_url="/uploads/photos/test/approved_photo_thumb.jpg",
        display_order=1,
        is_profile_picture=False,
        moderation_status="APPROVED",
        reviewed_at=datetime.now(UTC),
        file_size=204800,
        width=1200,
        height=900,
        mime_type="image/jpeg",
    )
    test_db.add(photo)
    await test_db.commit()
    await test_db.refresh(photo)
    return photo


@pytest.fixture
def sample_image_bytes():
    """產生測試用 JPEG 圖片"""
    img = Image.new("RGB", (800, 600), color="blue")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    buffer.seek(0)
    return buffer.read()


# ========== Service Tests ==========


@pytest.mark.asyncio
class TestPhotoModerationService:
    """PhotoModerationService 測試"""

    async def test_get_pending_photos_success(self, test_db: AsyncSession, pending_photo: Photo):
        """測試：成功取得待審核照片列表"""
        photos, total = await PhotoModerationService.get_pending_photos(
            db=test_db, page=1, page_size=20
        )

        assert total >= 1
        assert any(p["id"] == str(pending_photo.id) for p in photos)

    async def test_get_pending_photos_excludes_approved(
        self, test_db: AsyncSession, approved_photo: Photo
    ):
        """測試：已審核照片不在待審核列表中"""
        photos, total = await PhotoModerationService.get_pending_photos(db=test_db)

        # 已審核照片不應出現在待審核列表
        assert not any(p["id"] == str(approved_photo.id) for p in photos)

    async def test_get_pending_photos_with_status_filter(
        self, test_db: AsyncSession, approved_photo: Photo
    ):
        """測試：使用狀態篩選"""
        photos, total = await PhotoModerationService.get_pending_photos(
            db=test_db, status="APPROVED"
        )

        assert any(p["id"] == str(approved_photo.id) for p in photos)

    async def test_review_photo_approve_success(
        self, test_db: AsyncSession, pending_photo: Photo, admin_user: User
    ):
        """測試：成功批准照片"""
        success, message = await PhotoModerationService.review_photo(
            db=test_db, photo_id=pending_photo.id, admin_id=admin_user.id, status="APPROVED"
        )

        assert success is True
        assert "完成" in message

        # 驗證狀態已更新
        await test_db.refresh(pending_photo)
        assert pending_photo.moderation_status == "APPROVED"
        assert pending_photo.reviewed_by == admin_user.id
        assert pending_photo.reviewed_at is not None

    async def test_review_photo_reject_success(
        self, test_db: AsyncSession, pending_photo: Photo, admin_user: User
    ):
        """測試：成功拒絕照片"""
        success, message = await PhotoModerationService.review_photo(
            db=test_db,
            photo_id=pending_photo.id,
            admin_id=admin_user.id,
            status="REJECTED",
            rejection_reason="包含不當內容",
        )

        assert success is True

        await test_db.refresh(pending_photo)
        assert pending_photo.moderation_status == "REJECTED"
        assert pending_photo.rejection_reason == "包含不當內容"

    async def test_review_photo_reject_without_reason_fails(
        self, test_db: AsyncSession, pending_photo: Photo, admin_user: User
    ):
        """測試：拒絕時未提供原因應失敗"""
        success, message = await PhotoModerationService.review_photo(
            db=test_db,
            photo_id=pending_photo.id,
            admin_id=admin_user.id,
            status="REJECTED",
            # 缺少 rejection_reason
        )

        assert success is False
        assert "必須提供原因" in message

    async def test_review_photo_invalid_status_fails(
        self, test_db: AsyncSession, pending_photo: Photo, admin_user: User
    ):
        """測試：無效狀態應失敗"""
        success, message = await PhotoModerationService.review_photo(
            db=test_db, photo_id=pending_photo.id, admin_id=admin_user.id, status="INVALID"
        )

        assert success is False
        assert "無效" in message

    async def test_review_nonexistent_photo_fails(self, test_db: AsyncSession, admin_user: User):
        """測試：審核不存在的照片應失敗"""
        fake_id = uuid.uuid4()
        success, message = await PhotoModerationService.review_photo(
            db=test_db, photo_id=fake_id, admin_id=admin_user.id, status="APPROVED"
        )

        assert success is False
        assert "不存在" in message

    async def test_get_stats(
        self, test_db: AsyncSession, pending_photo: Photo, approved_photo: Photo
    ):
        """測試：取得統計數據"""
        stats = await PhotoModerationService.get_stats(test_db)

        assert "pending_photos" in stats
        assert "approved_photos" in stats
        assert "rejected_photos" in stats
        assert stats["pending_photos"] >= 1
        assert stats["approved_photos"] >= 1

    async def test_get_photo_detail(self, test_db: AsyncSession, pending_photo: Photo):
        """測試：取得照片詳情"""
        detail = await PhotoModerationService.get_photo_detail(test_db, pending_photo.id)

        assert detail is not None
        assert detail["id"] == str(pending_photo.id)
        assert detail["url"] == pending_photo.url
        assert detail["moderation_status"] == "PENDING"

    async def test_get_photo_detail_nonexistent(self, test_db: AsyncSession):
        """測試：取得不存在照片的詳情"""
        fake_id = uuid.uuid4()
        detail = await PhotoModerationService.get_photo_detail(test_db, fake_id)
        assert detail is None

    async def test_mask_email(self):
        """測試：Email 遮罩"""
        assert PhotoModerationService._mask_email("test@example.com") == "t***t@example.com"
        assert PhotoModerationService._mask_email("ab@example.com") == "a***@example.com"
        assert PhotoModerationService._mask_email("") == ""
        assert PhotoModerationService._mask_email("noemail") == "noemail"


@pytest.mark.asyncio
class TestTrustScoreIntegration:
    """信任分數整合測試"""

    async def test_rejected_photo_decreases_trust_score(
        self, test_db: AsyncSession, pending_photo: Photo, admin_user: User, test_user: User
    ):
        """測試：照片被拒絕時扣除信任分數"""
        initial_score = test_user.trust_score

        await PhotoModerationService.review_photo(
            db=test_db,
            photo_id=pending_photo.id,
            admin_id=admin_user.id,
            status="REJECTED",
            rejection_reason="違規內容",
        )

        await test_db.refresh(test_user)
        # content_violation 扣 3 分
        assert test_user.trust_score == initial_score - 3

    async def test_approved_photo_does_not_change_trust_score(
        self, test_db: AsyncSession, pending_photo: Photo, admin_user: User, test_user: User
    ):
        """測試：照片通過審核不影響信任分數"""
        initial_score = test_user.trust_score

        await PhotoModerationService.review_photo(
            db=test_db, photo_id=pending_photo.id, admin_id=admin_user.id, status="APPROVED"
        )

        await test_db.refresh(test_user)
        assert test_user.trust_score == initial_score


# ========== Photo Model Tests ==========


@pytest.mark.asyncio
class TestPhotoModel:
    """Photo 模型測試"""

    async def test_new_photo_default_status_is_pending(
        self, test_db: AsyncSession, test_profile: Profile
    ):
        """測試：新建照片預設狀態為 PENDING"""
        photo = Photo(
            profile_id=test_profile.id,
            url="/uploads/test.jpg",
            thumbnail_url="/uploads/test_thumb.jpg",
        )
        test_db.add(photo)
        await test_db.commit()
        await test_db.refresh(photo)

        assert photo.moderation_status == "PENDING"
        assert photo.reviewed_by is None
        assert photo.reviewed_at is None
        assert photo.rejection_reason is None

    async def test_photo_has_auto_moderation_fields(
        self, test_db: AsyncSession, test_profile: Profile
    ):
        """測試：照片有自動審核欄位"""
        photo = Photo(
            profile_id=test_profile.id,
            url="/uploads/test.jpg",
            auto_moderation_score=85,
            auto_moderation_labels='["safe", "portrait"]',
        )
        test_db.add(photo)
        await test_db.commit()
        await test_db.refresh(photo)

        assert photo.auto_moderation_score == 85
        assert photo.auto_moderation_labels == '["safe", "portrait"]'


# ========== Rejection Takedown Tests ==========


@pytest.mark.asyncio
class TestRejectionTakedown:
    """照片駁回下架鏈測試"""

    async def test_reject_primary_promotes_next_photo(
        self,
        test_db: AsyncSession,
        pending_photo: Photo,
        approved_photo: Photo,
        admin_user: User,
    ):
        """駁回主頭像後，主頭像遞補到下一張未被駁回的照片"""
        success, _ = await PhotoModerationService.review_photo(
            db=test_db,
            photo_id=pending_photo.id,
            admin_id=admin_user.id,
            status="REJECTED",
            rejection_reason="違規內容",
        )

        assert success is True
        await test_db.refresh(pending_photo)
        await test_db.refresh(approved_photo)
        assert pending_photo.is_profile_picture is False
        assert approved_photo.is_profile_picture is True

    async def test_reject_last_photo_marks_profile_incomplete(
        self,
        test_db: AsyncSession,
        test_profile: Profile,
        pending_photo: Photo,
        admin_user: User,
    ):
        """駁回唯一照片後，檔案完整度轉為 False（自動退出探索池）"""
        # 補齊興趣讓檔案先處於完整狀態
        tags = [
            InterestTag(name=f"下架測試-{uuid.uuid4().hex[:6]}", category="lifestyle")
            for _ in range(3)
        ]
        for tag in tags:
            test_db.add(tag)
        await test_db.commit()

        await test_db.refresh(test_profile, ["interests"])
        test_profile.interests.extend(tags)
        test_profile.is_complete = True
        await test_db.commit()

        await PhotoModerationService.review_photo(
            db=test_db,
            photo_id=pending_photo.id,
            admin_id=admin_user.id,
            status="REJECTED",
            rejection_reason="違規內容",
        )

        await test_db.refresh(test_profile)
        assert test_profile.is_complete is False

    async def test_reject_quarantines_photo_file(
        self, test_db: AsyncSession, pending_photo: Photo, admin_user: User
    ):
        """駁回後實體檔案移入隔離區（下架但保留供申訴審閱）"""
        with patch(
            "app.services.photo_moderation.file_storage.quarantine_photo",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_quarantine:
            success, _ = await PhotoModerationService.review_photo(
                db=test_db,
                photo_id=pending_photo.id,
                admin_id=admin_user.id,
                status="REJECTED",
                rejection_reason="違規內容",
            )

        assert success is True
        mock_quarantine.assert_awaited_once_with(pending_photo.url)

    async def test_rejected_photo_cannot_be_rereviewed(
        self, test_db: AsyncSession, pending_photo: Photo, admin_user: User
    ):
        """REJECTED 為終態：檔案已下架，不可重審復活（申訴成功應重新上傳）"""
        await PhotoModerationService.review_photo(
            db=test_db,
            photo_id=pending_photo.id,
            admin_id=admin_user.id,
            status="REJECTED",
            rejection_reason="違規內容",
        )

        success, message = await PhotoModerationService.review_photo(
            db=test_db,
            photo_id=pending_photo.id,
            admin_id=admin_user.id,
            status="APPROVED",
        )

        assert success is False
        assert "重新上傳" in message

    async def test_approve_keeps_primary_and_file(
        self, test_db: AsyncSession, pending_photo: Photo, admin_user: User
    ):
        """通過審核不影響主頭像，檔案也不會被隔離"""
        with patch(
            "app.services.photo_moderation.file_storage.quarantine_photo",
            new_callable=AsyncMock,
        ) as mock_quarantine:
            success, _ = await PhotoModerationService.review_photo(
                db=test_db,
                photo_id=pending_photo.id,
                admin_id=admin_user.id,
                status="APPROVED",
            )

        assert success is True
        mock_quarantine.assert_not_awaited()
        await test_db.refresh(pending_photo)
        assert pending_photo.is_profile_picture is True
