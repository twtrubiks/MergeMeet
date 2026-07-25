"""照片審核服務

負責照片的審核流程管理、狀態轉換、信任分數整合。
預留自動審核擴展接口。
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.models.moderation import ModerationLog
from app.models.profile import Photo, Profile, check_profile_completeness
from app.models.user import User
from app.services.file_storage import file_storage
from app.services.trust_score import TrustScoreService

logger = logging.getLogger(__name__)


class PhotoModerationService:
    """照片審核服務"""

    # 審核狀態常量
    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"

    # 違規類型
    VIOLATION_TYPES = {
        "NUDITY": "裸露內容",
        "VIOLENCE": "暴力內容",
        "HATE": "仇恨言論",
        "FAKE": "假照片/非本人",
        "SPAM": "垃圾內容",
        "OTHER": "其他違規",
    }

    # Session factory（供測試注入）
    _session_factory: async_sessionmaker | None = None

    @classmethod
    def set_session_factory(cls, factory: async_sessionmaker) -> None:
        """設定 session factory（供測試注入）

        Args:
            factory: SQLAlchemy async session maker
        """
        cls._session_factory = factory

    @classmethod
    def reset_session_factory(cls) -> None:
        """重設 session factory 為預設（正式環境）"""
        cls._session_factory = None

    @classmethod
    def _get_session_factory(cls) -> async_sessionmaker:
        """取得要使用的 session factory

        Returns:
            注入的 factory（如果有設定），否則預設的 AsyncSessionLocal
        """
        if cls._session_factory is not None:
            return cls._session_factory
        from app.core.database import AsyncSessionLocal

        return AsyncSessionLocal

    @classmethod
    async def get_pending_photos(
        cls, db: AsyncSession, page: int = 1, page_size: int = 20, status: str | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        """
        取得待審核照片列表

        Args:
            db: 資料庫 Session
            page: 頁碼
            page_size: 每頁數量
            status: 篩選狀態（可選）

        Returns:
            (photos, total): 照片列表和總數
        """
        # 建立基礎查詢
        query = (
            select(Photo, Profile, User)
            .join(Profile, Photo.profile_id == Profile.id)
            .join(User, Profile.user_id == User.id)
        )

        # 狀態篩選
        if status:
            query = query.where(Photo.moderation_status == status)
        else:
            query = query.where(Photo.moderation_status == cls.STATUS_PENDING)

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 分頁和排序（最舊的優先審核）
        offset = (page - 1) * page_size
        query = query.order_by(Photo.created_at.asc()).offset(offset).limit(page_size)

        result = await db.execute(query)
        rows = result.all()

        photos = []
        for photo, profile, user in rows:
            photos.append(
                {
                    "id": str(photo.id),
                    "url": photo.url,
                    "thumbnail_url": photo.thumbnail_url,
                    "profile_id": str(profile.id),
                    "user_id": str(user.id),
                    "user_email": cls._mask_email(user.email),
                    "display_name": profile.display_name,
                    "moderation_status": photo.moderation_status,
                    "created_at": photo.created_at.isoformat() if photo.created_at else None,
                    "file_size": photo.file_size,
                    "width": photo.width,
                    "height": photo.height,
                }
            )

        return photos, total

    @classmethod
    async def get_photo_detail(cls, db: AsyncSession, photo_id: uuid.UUID) -> dict[str, Any] | None:
        """
        取得照片詳情

        Args:
            db: 資料庫 Session
            photo_id: 照片 ID

        Returns:
            照片詳情或 None
        """
        query = (
            select(Photo, Profile, User)
            .join(Profile, Photo.profile_id == Profile.id)
            .join(User, Profile.user_id == User.id)
            .where(Photo.id == photo_id)
        )

        result = await db.execute(query)
        row = result.first()

        if not row:
            return None

        photo, profile, user = row
        return {
            "id": str(photo.id),
            "url": photo.url,
            "thumbnail_url": photo.thumbnail_url,
            "profile_id": str(profile.id),
            "user_id": str(user.id),
            "user_email": cls._mask_email(user.email),
            "display_name": profile.display_name,
            "moderation_status": photo.moderation_status,
            "rejection_reason": photo.rejection_reason,
            "reviewed_at": photo.reviewed_at.isoformat() if photo.reviewed_at else None,
            "created_at": photo.created_at.isoformat() if photo.created_at else None,
            "file_size": photo.file_size,
            "width": photo.width,
            "height": photo.height,
            "mime_type": photo.mime_type,
            "auto_moderation_score": photo.auto_moderation_score,
            "auto_moderation_labels": photo.auto_moderation_labels,
        }

    @classmethod
    async def review_photo(
        cls,
        db: AsyncSession,
        photo_id: uuid.UUID,
        admin_id: uuid.UUID,
        status: str,
        rejection_reason: str | None = None,
    ) -> tuple[bool, str]:
        """
        審核照片

        Args:
            db: 資料庫 Session
            photo_id: 照片 ID
            admin_id: 管理員 ID
            status: 審核結果 (APPROVED/REJECTED)
            rejection_reason: 拒絕原因

        Returns:
            (success, message): 操作結果
        """
        # 驗證狀態
        if status not in [cls.STATUS_APPROVED, cls.STATUS_REJECTED]:
            return False, "無效的審核狀態"

        if status == cls.STATUS_REJECTED and not rejection_reason:
            return False, "拒絕時必須提供原因"

        # 查詢照片
        result = await db.execute(
            select(Photo).options(selectinload(Photo.profile)).where(Photo.id == photo_id)
        )
        photo = result.scalar_one_or_none()

        if not photo:
            return False, "照片不存在"

        # REJECTED 不可經此端點重審：重新上架的正規途徑是申訴通過
        # （restore_photo_from_appeal）或用戶重新上傳
        if photo.moderation_status == cls.STATUS_REJECTED:
            return False, "照片已駁回下架，重新上架請透過申訴或重新上傳"

        # 取得用戶檔案（含照片與興趣：駁回時需遞補主頭像並重算完整度）
        profile_result = await db.execute(
            select(Profile)
            .options(selectinload(Profile.photos), selectinload(Profile.interests))
            .where(Profile.id == photo.profile_id)
        )
        profile = profile_result.scalar_one_or_none()
        if not profile:
            return False, "個人檔案不存在"

        # 更新照片狀態
        photo.moderation_status = status
        photo.reviewed_by = admin_id
        photo.reviewed_at = datetime.now(UTC)

        if status == cls.STATUS_REJECTED:
            photo.rejection_reason = rejection_reason

            # 下架：駁回照片不可再作為主頭像，並重算檔案完整度
            # （沒有未駁回照片時 is_complete 轉為 False，用戶自動退出探索池）
            if photo.is_profile_picture:
                profile.reassign_primary_photo()
            profile.is_complete = check_profile_completeness(profile)

            # 扣除信任分數
            await TrustScoreService.adjust_score(db, profile.user_id, "content_violation")

        # 記錄審核日誌
        await cls._log_moderation(
            db=db,
            user_id=profile.user_id,
            photo_id=photo_id,
            is_approved=(status == cls.STATUS_APPROVED),
            rejection_reason=rejection_reason,
        )

        await db.commit()

        # 實體檔案移入隔離區：即刻下架但保留供申訴審閱，
        # 申訴審結後由 review_appeal 清除（best-effort：搬移失敗不影響審核結果）
        if status == cls.STATUS_REJECTED and not await file_storage.quarantine_photo(photo.url):
            logger.warning(f"Rejected photo file not quarantined: {photo.url}")

        return True, "審核完成"

    # 申訴還原結果代碼（供 review_appeal 決定隔離檔案處置）
    RESTORE_RESTORED = "RESTORED"  # 已還原，檔案已搬回上傳目錄
    RESTORE_NOT_FOUND = "NOT_FOUND"  # 照片記錄不存在（用戶已刪除），隔離檔可清
    RESTORE_NOT_OWNED = "NOT_OWNED"  # 照片不屬於申訴人，不可動他人的隔離檔
    RESTORE_NOT_REJECTED = "NOT_REJECTED"  # 照片已非駁回狀態（如已被先前申訴還原）
    RESTORE_FILE_MISSING = "FILE_MISSING"  # 隔離檔不存在，還原會產生破圖，不改狀態

    @classmethod
    async def restore_photo_from_appeal(
        cls, db: AsyncSession, photo_url: str, appellant_user_id: uuid.UUID
    ) -> str:
        """
        申訴通過後還原照片（重新上架）

        照片狀態直接改 APPROVED（管理員審申訴時已人工看過圖），
        並補主頭像、重算檔案完整度。不負責 commit，由呼叫端統一提交。

        Args:
            db: 資料庫 Session
            photo_url: 照片 URL（來自申訴的 rejected_content，用戶提交、不可信）
            appellant_user_id: 申訴人 ID（用於歸屬驗證）

        Returns:
            RESTORE_* 結果代碼
        """
        result = await db.execute(select(Photo).where(Photo.url == photo_url))
        photo = result.scalar_one_or_none()
        if not photo:
            return cls.RESTORE_NOT_FOUND

        profile_result = await db.execute(
            select(Profile)
            .options(selectinload(Profile.photos), selectinload(Profile.interests))
            .where(Profile.id == photo.profile_id)
        )
        profile = profile_result.scalar_one_or_none()
        if not profile or profile.user_id != appellant_user_id:
            return cls.RESTORE_NOT_OWNED

        if photo.moderation_status != cls.STATUS_REJECTED:
            return cls.RESTORE_NOT_REJECTED

        if file_storage.get_quarantined_path(photo_url) is None:
            return cls.RESTORE_FILE_MISSING

        photo.moderation_status = cls.STATUS_APPROVED
        photo.rejection_reason = None

        # 駁回時主頭像可能已被遞補；若目前沒有主頭像，還原的這張補上
        if not any(p.is_profile_picture for p in profile.photos):
            photo.is_profile_picture = True
        profile.is_complete = check_profile_completeness(profile)

        # 實體檔案搬回（best-effort：失敗僅記錄警告，照片仍為 APPROVED 可由用戶重傳補救）
        if not await file_storage.restore_photo(photo_url):
            logger.warning(f"Restored photo file not moved back: {photo_url}")

        return cls.RESTORE_RESTORED

    @classmethod
    async def get_stats(cls, db: AsyncSession) -> dict[str, int]:
        """
        取得照片審核統計

        Args:
            db: 資料庫 Session

        Returns:
            統計數據字典
        """
        # 總數統計
        total_result = await db.execute(select(func.count(Photo.id)))
        total = total_result.scalar() or 0

        # 各狀態統計
        pending_result = await db.execute(
            select(func.count(Photo.id)).where(Photo.moderation_status == cls.STATUS_PENDING)
        )
        pending = pending_result.scalar() or 0

        approved_result = await db.execute(
            select(func.count(Photo.id)).where(Photo.moderation_status == cls.STATUS_APPROVED)
        )
        approved = approved_result.scalar() or 0

        rejected_result = await db.execute(
            select(func.count(Photo.id)).where(Photo.moderation_status == cls.STATUS_REJECTED)
        )
        rejected = rejected_result.scalar() or 0

        # 今日統計
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

        today_pending_result = await db.execute(
            select(func.count(Photo.id)).where(
                Photo.moderation_status == cls.STATUS_PENDING, Photo.created_at >= today_start
            )
        )
        today_pending = today_pending_result.scalar() or 0

        today_reviewed_result = await db.execute(
            select(func.count(Photo.id)).where(Photo.reviewed_at >= today_start)
        )
        today_reviewed = today_reviewed_result.scalar() or 0

        return {
            "total_photos": total,
            "pending_photos": pending,
            "approved_photos": approved,
            "rejected_photos": rejected,
            "today_pending": today_pending,
            "today_reviewed": today_reviewed,
        }

    @classmethod
    async def _log_moderation(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        photo_id: uuid.UUID,
        is_approved: bool,
        rejection_reason: str | None,
    ) -> None:
        """記錄審核日誌（使用獨立事務確保日誌不遺失）"""
        SessionFactory = cls._get_session_factory()
        async with SessionFactory() as log_db:
            try:
                log = ModerationLog(
                    user_id=user_id,
                    content_type="PHOTO",
                    original_content=str(photo_id),
                    is_approved=is_approved,
                    violations=json.dumps(
                        [rejection_reason] if rejection_reason else [], ensure_ascii=False
                    ),
                    action_taken="APPROVED" if is_approved else "REJECTED",
                )
                log_db.add(log)
                await log_db.commit()
            except Exception as e:
                logger.error(f"Failed to log photo moderation: {e}")
                await log_db.rollback()

    @staticmethod
    def _mask_email(email: str) -> str:
        """遮罩 Email（保護隱私）"""
        if not email or "@" not in email:
            return email
        local, domain = email.split("@", 1)
        masked_local = (  # noqa: SIM108
            local[0] + "***" if len(local) <= 2 else local[0] + "***" + local[-1]
        )
        return f"{masked_local}@{domain}"

    # ==================== 自動審核擴展接口 ====================

    @classmethod
    async def auto_moderate(
        cls, photo_id: uuid.UUID, image_data: bytes, db: AsyncSession
    ) -> tuple[bool, int, list[str]]:
        """
        自動審核接口（預留擴展）

        Args:
            photo_id: 照片 ID
            image_data: 圖片二進制數據
            db: 資料庫 Session

        Returns:
            (should_auto_approve, confidence_score, detected_labels)

        注意：此方法目前為占位符，未來可整合:
        - AWS Rekognition
        - Google Cloud Vision
        - Azure Computer Vision
        - 自建 ML 模型
        """
        # TODO: 整合第三方圖片審核 API
        # 目前返回預設值，需人工審核
        return False, 0, []

    @classmethod
    async def process_auto_moderation_result(
        cls, db: AsyncSession, photo_id: uuid.UUID, score: int, labels: list[str]
    ) -> None:
        """
        處理自動審核結果（預留擴展）

        Args:
            db: 資料庫 Session
            photo_id: 照片 ID
            score: 信心分數 (0-100)
            labels: 檢測到的標籤
        """
        result = await db.execute(select(Photo).where(Photo.id == photo_id))
        photo = result.scalar_one_or_none()

        if photo:
            photo.auto_moderation_score = score
            photo.auto_moderation_labels = json.dumps(labels, ensure_ascii=False)

            # 可選：高信心度自動審核
            # AUTO_APPROVE_THRESHOLD = 95
            # if score >= AUTO_APPROVE_THRESHOLD and not any_suspicious_label(labels):
            #     photo.moderation_status = cls.STATUS_APPROVED
            #     photo.reviewed_at = datetime.now(timezone.utc)

            await db.commit()
