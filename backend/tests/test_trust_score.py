"""信任分數服務測試"""

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services import trust_score as trust_score_module
from app.services.trust_score import TrustScoreService


@pytest_asyncio.fixture
async def test_user(test_db: AsyncSession):
    """創建測試用戶"""
    user = User(
        id=uuid.uuid4(),
        email="trust_test@example.com",
        password_hash="dummy_hash",
        date_of_birth=date(1995, 1, 1),
        is_active=True,
        trust_score=50,  # 預設分數
        warning_count=0,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def low_trust_user(test_db: AsyncSession):
    """創建低信任分數用戶"""
    user = User(
        id=uuid.uuid4(),
        email="low_trust@example.com",
        password_hash="dummy_hash",
        date_of_birth=date(1995, 1, 1),
        is_active=True,
        trust_score=15,  # 低於閾值 20
        warning_count=5,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
def mock_redis():
    """Mock Redis 連線"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.ttl = AsyncMock(return_value=-2)
    return redis


# =============================================================================
# 測試：分數調整
# =============================================================================
@pytest.mark.asyncio
class TestTrustScoreAdjustments:
    """測試信任分數調整邏輯"""

    async def test_email_verified_increases_score(self, test_db: AsyncSession, test_user: User):
        """測試：Email 驗證增加 5 分"""
        initial_score = test_user.trust_score

        new_score = await TrustScoreService.adjust_score(test_db, test_user.id, "email_verified")

        await test_db.refresh(test_user)
        assert new_score == initial_score + 5
        assert test_user.trust_score == initial_score + 5

    async def test_received_like_increases_score(self, test_db: AsyncSession, test_user: User):
        """測試：被喜歡增加 1 分"""
        initial_score = test_user.trust_score

        new_score = await TrustScoreService.adjust_score(test_db, test_user.id, "received_like")

        await test_db.refresh(test_user)
        assert new_score == initial_score + 1
        assert test_user.trust_score == initial_score + 1

    async def test_match_created_increases_score(self, test_db: AsyncSession, test_user: User):
        """測試：配對成功增加 2 分"""
        initial_score = test_user.trust_score

        new_score = await TrustScoreService.adjust_score(test_db, test_user.id, "match_created")

        await test_db.refresh(test_user)
        assert new_score == initial_score + 2
        assert test_user.trust_score == initial_score + 2

    async def test_report_confirmed_decreases_score(self, test_db: AsyncSession, test_user: User):
        """測試：舉報確認減少 10 分"""
        initial_score = test_user.trust_score

        new_score = await TrustScoreService.adjust_score(test_db, test_user.id, "report_confirmed")

        await test_db.refresh(test_user)
        assert new_score == initial_score - 10
        assert test_user.trust_score == initial_score - 10

    async def test_content_violation_decreases_score(self, test_db: AsyncSession, test_user: User):
        """測試：發送違規內容減少 3 分"""
        initial_score = test_user.trust_score

        new_score = await TrustScoreService.adjust_score(test_db, test_user.id, "content_violation")

        await test_db.refresh(test_user)
        assert new_score == initial_score - 3
        assert test_user.trust_score == initial_score - 3

    async def test_blocked_decreases_score(self, test_db: AsyncSession, test_user: User):
        """測試：被封鎖減少 2 分"""
        initial_score = test_user.trust_score

        new_score = await TrustScoreService.adjust_score(test_db, test_user.id, "blocked")

        await test_db.refresh(test_user)
        assert new_score == initial_score - 2
        assert test_user.trust_score == initial_score - 2


# =============================================================================
# 測試：分數邊界
# =============================================================================
@pytest.mark.asyncio
class TestScoreBoundaries:
    """測試分數邊界處理"""

    async def test_score_never_exceeds_max(self, test_db: AsyncSession, test_user: User):
        """測試：分數不會超過 100"""
        # 設定高分數
        test_user.trust_score = 98
        await test_db.commit()

        # 嘗試增加 5 分（email_verified）
        new_score = await TrustScoreService.adjust_score(test_db, test_user.id, "email_verified")

        await test_db.refresh(test_user)
        assert new_score == TrustScoreService.MAX_SCORE
        assert test_user.trust_score == TrustScoreService.MAX_SCORE

    async def test_score_never_below_min(self, test_db: AsyncSession, test_user: User):
        """測試：分數不會低於 0"""
        # 設定低分數
        test_user.trust_score = 3
        await test_db.commit()

        # 嘗試減少 10 分（report_confirmed）
        new_score = await TrustScoreService.adjust_score(test_db, test_user.id, "report_confirmed")

        await test_db.refresh(test_user)
        assert new_score == TrustScoreService.MIN_SCORE
        assert test_user.trust_score == TrustScoreService.MIN_SCORE

    async def test_invalid_action_raises_error(self, test_db: AsyncSession, test_user: User):
        """測試：無效的動作會拋出錯誤"""
        with pytest.raises(ValueError, match="未知的行為類型"):
            await TrustScoreService.adjust_score(test_db, test_user.id, "invalid_action")

    async def test_unknown_user_raises_error(self, test_db: AsyncSession):
        """測試：調整不存在的用戶會拋錯並指出是哪個用戶（不可靜默略過）"""
        user_id = uuid.uuid4()

        with pytest.raises(ValueError, match=f"用戶不存在: {user_id}"):
            await TrustScoreService.adjust_score(test_db, user_id, "email_verified")


# =============================================================================
# 測試：獲取分數
# =============================================================================
@pytest.mark.asyncio
class TestGetScore:
    """測試獲取分數功能"""

    async def test_get_score_returns_current_score(self, test_db: AsyncSession, test_user: User):
        """測試：獲取當前分數"""
        score = await TrustScoreService.get_score(test_db, test_user.id)
        assert score == test_user.trust_score

    async def test_get_score_user_not_found(self, test_db: AsyncSession):
        """測試：用戶不存在時返回預設分數"""
        fake_user_id = uuid.uuid4()
        score = await TrustScoreService.get_score(test_db, fake_user_id)
        assert score == TrustScoreService.DEFAULT_SCORE


# =============================================================================
# 測試：受限狀態
# =============================================================================
@pytest.mark.asyncio
class TestRestrictions:
    """測試受限狀態檢查"""

    async def test_normal_user_not_restricted(self, test_db: AsyncSession, test_user: User):
        """測試：正常用戶不受限"""
        is_restricted = await TrustScoreService.is_restricted(test_db, test_user.id)
        assert is_restricted is False

    async def test_low_trust_user_is_restricted(self, test_db: AsyncSession, low_trust_user: User):
        """測試：低信任用戶受限"""
        is_restricted = await TrustScoreService.is_restricted(test_db, low_trust_user.id)
        assert is_restricted is True

    async def test_boundary_score_not_restricted(self, test_db: AsyncSession, test_user: User):
        """測試：剛好 20 分不受限"""
        test_user.trust_score = 20
        await test_db.commit()

        is_restricted = await TrustScoreService.is_restricted(test_db, test_user.id)
        assert is_restricted is False


# =============================================================================
# 測試：訊息速率限制
# =============================================================================
@pytest.mark.asyncio
class TestMessageRateLimiting:
    """測試訊息速率限制"""

    async def test_normal_user_no_limit(self, test_db: AsyncSession, test_user: User, mock_redis):
        """測試：正常用戶無訊息限制"""
        can_send, remaining = await TrustScoreService.check_message_rate_limit(
            test_user.id, test_user.trust_score, mock_redis
        )
        assert can_send is True
        assert remaining == -1  # -1 表示無限制

    async def test_low_trust_user_has_limit(
        self, test_db: AsyncSession, low_trust_user: User, mock_redis
    ):
        """測試：低信任用戶有訊息限制"""
        # 模擬已發送 5 則訊息
        mock_redis.get.return_value = b"5"

        can_send, remaining = await TrustScoreService.check_message_rate_limit(
            low_trust_user.id, low_trust_user.trust_score, mock_redis
        )

        assert can_send is True
        assert remaining == TrustScoreService.LOW_TRUST_MESSAGE_LIMIT - 5

    async def test_exceeded_limit_blocks_message(
        self, test_db: AsyncSession, low_trust_user: User, mock_redis
    ):
        """測試：超過限制後無法發送訊息"""
        # 模擬已達上限
        mock_redis.get.return_value = str(TrustScoreService.LOW_TRUST_MESSAGE_LIMIT).encode()

        can_send, remaining = await TrustScoreService.check_message_rate_limit(
            low_trust_user.id, low_trust_user.trust_score, mock_redis
        )

        assert can_send is False
        assert remaining == 0

    async def test_record_message_increments_counter(
        self, test_db: AsyncSession, low_trust_user: User, mock_redis
    ):
        """測試：記錄訊息會增加計數器"""
        await TrustScoreService.record_message_sent(low_trust_user.id, mock_redis)

        mock_redis.incr.assert_called_once()
        mock_redis.expire.assert_called_once()

    async def test_threshold_score_not_rate_limited(self, mock_redis):
        """測試：信任分數剛好 20（閾值）不受限，與 is_restricted 的 < 20 一致"""
        can_send, remaining = await TrustScoreService.check_message_rate_limit(
            uuid.uuid4(), TrustScoreService.RESTRICTION_THRESHOLD, mock_redis
        )

        assert (can_send, remaining) == (True, -1)
        mock_redis.get.assert_not_called()

    async def test_low_trust_user_no_messages_today(self, mock_redis):
        """測試：今日尚未發訊（Redis 無計數）→ 額度完整"""
        can_send, remaining = await TrustScoreService.check_message_rate_limit(
            uuid.uuid4(), 15, mock_redis
        )

        assert (can_send, remaining) == (True, TrustScoreService.LOW_TRUST_MESSAGE_LIMIT)

    async def test_last_message_of_the_day_allowed(self, mock_redis):
        """測試：已發 19 則時仍可發第 20 則"""
        mock_redis.get.return_value = str(TrustScoreService.LOW_TRUST_MESSAGE_LIMIT - 1).encode()

        can_send, remaining = await TrustScoreService.check_message_rate_limit(
            uuid.uuid4(), 15, mock_redis
        )

        assert (can_send, remaining) == (True, 1)

    async def test_record_and_check_share_daily_key(self, mock_redis):
        """測試：記錄與檢查使用同一個當日計數 key，且 TTL 24 小時

        兩個函式各自組 key，任一邊格式跑掉，低信任用戶的每日上限就形同虛設。
        """
        counts: dict[str, int] = {}

        async def incr(key):
            counts[key] = counts.get(key, 0) + 1
            return counts[key]

        async def get(key):
            return str(counts[key]).encode() if key in counts else None

        mock_redis.incr.side_effect = incr
        mock_redis.get.side_effect = get
        user_id = uuid.uuid4()

        for _ in range(TrustScoreService.LOW_TRUST_MESSAGE_LIMIT):
            await TrustScoreService.record_message_sent(user_id, mock_redis)
        can_send, remaining = await TrustScoreService.check_message_rate_limit(
            user_id, 15, mock_redis
        )

        assert (can_send, remaining) == (False, 0)
        key = f"trust:daily_messages:{user_id}:{datetime.now(UTC):%Y-%m-%d}"
        assert list(counts) == [key]
        mock_redis.expire.assert_called_with(key, 86400)

    async def test_daily_key_uses_utc_date_on_utc8_host(self, mock_redis, monkeypatch):
        """測試：當日計數 key 以 UTC 日期命名，與主機時區無關

        模擬部署在 UTC+8 主機的台灣時間 1/2 00:30（UTC 仍是 1/1）。記錄與檢查若有一邊
        誤用不帶時區的 now()，凌晨 0–8 點兩邊會用不同日期的 key，每日上限失效。
        """
        utc_now = datetime(2026, 1, 1, 16, 30, tzinfo=UTC)

        class _Utc8Datetime(datetime):
            @classmethod
            def now(cls, tz=None):
                if tz is None:
                    return (utc_now + timedelta(hours=8)).replace(tzinfo=None)
                return utc_now.astimezone(tz)

        monkeypatch.setattr(trust_score_module, "datetime", _Utc8Datetime)
        mock_redis.incr = AsyncMock(return_value=1)
        user_id = uuid.uuid4()

        await TrustScoreService.record_message_sent(user_id, mock_redis)
        await TrustScoreService.check_message_rate_limit(user_id, 15, mock_redis)

        key = f"trust:daily_messages:{user_id}:2026-01-01"
        mock_redis.incr.assert_called_once_with(key)
        mock_redis.get.assert_called_once_with(key)


# =============================================================================
# 測試：多次調整
# =============================================================================
@pytest.mark.asyncio
class TestMultipleAdjustments:
    """測試多次分數調整"""

    async def test_cumulative_positive_adjustments(self, test_db: AsyncSession, test_user: User):
        """測試：累積正向調整"""
        initial_score = test_user.trust_score

        # 連續正向行為
        await TrustScoreService.adjust_score(test_db, test_user.id, "email_verified")
        await TrustScoreService.adjust_score(test_db, test_user.id, "received_like")
        await TrustScoreService.adjust_score(test_db, test_user.id, "match_created")

        await test_db.refresh(test_user)
        expected_score = initial_score + 5 + 1 + 2
        assert test_user.trust_score == expected_score

    async def test_cumulative_negative_adjustments(self, test_db: AsyncSession, test_user: User):
        """測試：累積負向調整"""
        initial_score = test_user.trust_score

        # 連續負向行為
        await TrustScoreService.adjust_score(test_db, test_user.id, "report_confirmed")
        await TrustScoreService.adjust_score(test_db, test_user.id, "blocked")

        await test_db.refresh(test_user)
        expected_score = initial_score - 10 - 2
        assert test_user.trust_score == expected_score

    async def test_mixed_adjustments(self, test_db: AsyncSession, test_user: User):
        """測試：混合調整"""
        initial_score = test_user.trust_score

        # 正向
        await TrustScoreService.adjust_score(test_db, test_user.id, "received_like")
        # 負向
        await TrustScoreService.adjust_score(test_db, test_user.id, "report_confirmed")

        await test_db.refresh(test_user)
        expected_score = initial_score + 1 - 10
        assert test_user.trust_score == expected_score


# =============================================================================
# 測試：正向互動
# =============================================================================
@pytest.mark.asyncio
class TestPositiveInteraction:
    """測試正向互動獎勵"""

    async def test_positive_interaction_increases_score(
        self, test_db: AsyncSession, test_user: User
    ):
        """測試：正向互動增加 1 分"""
        initial_score = test_user.trust_score

        new_score = await TrustScoreService.adjust_score(
            test_db, test_user.id, "positive_interaction"
        )

        await test_db.refresh(test_user)
        assert new_score == initial_score + 1
        assert test_user.trust_score == initial_score + 1

    async def test_positive_interaction_multiple_times(
        self, test_db: AsyncSession, test_user: User
    ):
        """測試：多次正向互動累積"""
        initial_score = test_user.trust_score

        # 模擬 3 次正向互動（每日上限）
        await TrustScoreService.adjust_score(test_db, test_user.id, "positive_interaction")
        await TrustScoreService.adjust_score(test_db, test_user.id, "positive_interaction")
        await TrustScoreService.adjust_score(test_db, test_user.id, "positive_interaction")

        await test_db.refresh(test_user)
        assert test_user.trust_score == initial_score + 3

    async def test_positive_interaction_with_max_score(
        self, test_db: AsyncSession, test_user: User
    ):
        """測試：正向互動不會超過最高分數"""
        test_user.trust_score = 100
        await test_db.commit()

        new_score = await TrustScoreService.adjust_score(
            test_db, test_user.id, "positive_interaction"
        )

        await test_db.refresh(test_user)
        assert new_score == TrustScoreService.MAX_SCORE
        assert test_user.trust_score == TrustScoreService.MAX_SCORE
