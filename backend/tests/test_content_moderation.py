"""內容審核服務測試 - 使用 PostgreSQL"""

import json
import uuid
from datetime import date, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.moderation import ModerationLog, SensitiveWord
from app.models.user import User
from app.services.content_moderation import ContentModerationService


@pytest_asyncio.fixture
async def test_user(test_db: AsyncSession):
    """創建測試用戶"""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash="dummy_hash",
        date_of_birth=date(1990, 1, 1),
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def sensitive_words(test_db: AsyncSession):
    """創建測試敏感詞"""
    words = [
        SensitiveWord(
            id=uuid.uuid4(),
            word="色情",
            category="SEXUAL",
            severity="HIGH",
            action="REJECT",
            is_regex=False,
            is_active=True,
        ),
        SensitiveWord(
            id=uuid.uuid4(),
            word="18禁",
            category="SEXUAL",
            severity="HIGH",
            action="REJECT",
            is_regex=False,
            is_active=True,
        ),
        SensitiveWord(
            id=uuid.uuid4(),
            word="投資",
            category="SCAM",
            severity="LOW",
            action="WARN",
            is_regex=False,
            is_active=True,
        ),
        SensitiveWord(
            id=uuid.uuid4(),
            word="約炮",
            category="HARASSMENT",
            severity="HIGH",
            action="REJECT",
            is_regex=False,
            is_active=True,
        ),
        SensitiveWord(
            id=uuid.uuid4(),
            word="匯款",
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

    # 清除快取以確保載入新的敏感詞
    await ContentModerationService.clear_cache()

    return words


@pytest_asyncio.fixture
async def regex_words(test_db: AsyncSession):
    """正則敏感詞（含一個無效正則，排在最前面）與英文純文字敏感詞"""
    words = [
        SensitiveWord(
            id=uuid.uuid4(),
            word="([",  # 無效正則：應被略過，不影響其他詞
            category="OTHER",
            severity="CRITICAL",
            action="AUTO_BAN",
            is_regex=True,
            is_active=True,
        ),
        SensitiveWord(
            id=uuid.uuid4(),
            word=r"free\s*money",
            category="SCAM",
            severity="HIGH",
            action="REJECT",
            is_regex=True,
            is_active=True,
        ),
        SensitiveWord(
            id=uuid.uuid4(),
            word="spam",
            category="OTHER",
            severity="LOW",
            action="WARN",
            is_regex=False,
            is_active=True,
        ),
    ]
    test_db.add_all(words)
    await test_db.commit()
    await ContentModerationService.clear_cache()
    return words


@pytest.mark.asyncio
class TestContentModerationBasic:
    """基本內容審核測試"""

    async def test_check_safe_content(
        self, test_db: AsyncSession, test_user: User, sensitive_words
    ):
        """測試正常安全內容"""
        content = "你好，很高興認識你！"
        is_approved, violations, word_ids, action = await ContentModerationService.check_content(
            content, test_db, test_user.id, "TEXT"
        )

        assert is_approved is True
        assert len(violations) == 0
        assert action == "APPROVED"

    @pytest.mark.parametrize("content", ["", None])
    async def test_check_empty_or_none_content(self, test_db: AsyncSession, content):
        """測試空內容或 None"""
        is_approved, violations, word_ids, action = await ContentModerationService.check_content(
            content, test_db, None, "TEXT"
        )

        assert is_approved is True
        assert len(violations) == 0
        assert action == "APPROVED"


@pytest.mark.asyncio
class TestSensitiveWords:
    """敏感詞測試"""

    @pytest.mark.parametrize(
        "content,expected_word,expected_action",
        [
            ("想要看色情影片嗎？", "色情", "REJECT"),
            ("18禁的內容", "18禁", "REJECT"),
            ("加入我們的投資計畫", "投資", "WARN"),
            ("約炮嗎", "約炮", "REJECT"),
            ("請匯款到這個帳號", "匯款", "WARN"),
        ],
    )
    async def test_detect_sensitive_words(
        self,
        test_db: AsyncSession,
        test_user: User,
        sensitive_words,
        content: str,
        expected_word: str,
        expected_action: str,
    ):
        """測試敏感詞偵測（涵蓋色情、18禁、金融詐騙、性交易、聯絡方式）"""
        is_approved, violations, word_ids, action = await ContentModerationService.check_content(
            content, test_db, test_user.id, "MESSAGE"
        )

        # WARN 動作仍然算通過，但有違規
        if expected_action == "WARN":
            assert is_approved is True
        else:  # REJECT
            assert is_approved is False

        assert len(violations) > 0
        assert any(expected_word in v for v in violations)
        assert action == expected_action


@pytest.mark.asyncio
class TestSuspiciousPatterns:
    """可疑模式測試"""

    async def test_detect_line_id(self, test_db: AsyncSession, test_user: User, sensitive_words):
        """測試 LINE ID 偵測"""
        content = "加我LINE: abc123"
        is_approved, violations, word_ids, action = await ContentModerationService.check_content(
            content, test_db, test_user.id, "MESSAGE"
        )

        # 可疑模式預設為 WARN，仍算通過但有警告
        assert is_approved is True
        assert violations == [r"包含可疑內容: line\s*[:：]?\s*\w+"]
        assert action == "WARN"

    async def test_detect_phone_number(
        self, test_db: AsyncSession, test_user: User, sensitive_words
    ):
        """測試電話號碼偵測"""
        content = "我的電話是 0912345678"
        is_approved, violations, word_ids, action = await ContentModerationService.check_content(
            content, test_db, test_user.id, "MESSAGE"
        )

        assert is_approved is True  # WARN 仍算通過
        assert len(violations) > 0

    @pytest.mark.parametrize(
        "content", ["點擊這個連結 http://scam.com", "訪問 https://suspicious-site.com 獲取更多資訊"]
    )
    async def test_detect_url(
        self, test_db: AsyncSession, test_user: User, sensitive_words, content: str
    ):
        """測試 URL 偵測（HTTP/HTTPS）"""
        is_approved, violations, word_ids, action = await ContentModerationService.check_content(
            content, test_db, test_user.id, "MESSAGE"
        )

        assert is_approved is True  # WARN 仍算通過
        assert len(violations) > 0

    async def test_detect_wechat_id(self, test_db: AsyncSession, test_user: User, sensitive_words):
        """測試 WeChat ID 偵測"""
        content = "加我 wechat: myid123"
        is_approved, violations, word_ids, action = await ContentModerationService.check_content(
            content, test_db, test_user.id, "MESSAGE"
        )

        assert is_approved is True  # WARN 仍算通過
        assert len(violations) > 0

    @pytest.mark.parametrize(
        "content",
        [
            "只需 $100 就能獲得",
            "NT$5000 投資回報",
            "USD1000 快速賺錢",
        ],
    )
    async def test_detect_money_amount(
        self, test_db: AsyncSession, test_user: User, sensitive_words, content: str
    ):
        """測試金額偵測"""
        is_approved, violations, word_ids, action = await ContentModerationService.check_content(
            content, test_db, test_user.id, "MESSAGE"
        )

        assert is_approved is True  # WARN 仍算通過
        assert len(violations) > 0


@pytest.mark.asyncio
class TestContentSanitization:
    """內容清理測試"""

    async def test_sanitize_sensitive_words(self, test_db: AsyncSession, sensitive_words):
        """測試敏感詞替換"""
        content = "這裡有色情內容"
        sanitized = await ContentModerationService.sanitize_content(content, test_db)

        assert sanitized == "這裡有***內容"

    async def test_sanitize_url(self, test_db: AsyncSession, sensitive_words):
        """測試 URL 移除"""
        content = "訪問 http://example.com 查看"
        sanitized = await ContentModerationService.sanitize_content(content, test_db)

        assert sanitized == "訪問 [已移除連結] 查看"

    async def test_sanitize_regex_and_case_insensitive(self, test_db: AsyncSession, regex_words):
        """測試正則與純文字敏感詞皆不分大小寫替換；無效正則被略過而非中斷後續替換"""
        content = "Get FREE   Money, no SPAM"
        sanitized = await ContentModerationService.sanitize_content(content, test_db)

        assert sanitized == "Get ***, no ***"

    @pytest.mark.parametrize("content,expected", [("", ""), (None, None)])
    async def test_sanitize_empty_or_none_content(self, test_db: AsyncSession, content, expected):
        """測試空內容或 None 清理"""
        sanitized = await ContentModerationService.sanitize_content(content, test_db)
        assert sanitized == expected


@pytest.mark.asyncio
class TestProfileContentCheck:
    """個人檔案內容審核測試"""

    async def test_check_safe_profile(
        self, test_db: AsyncSession, test_user: User, sensitive_words
    ):
        """測試安全的個人檔案"""
        bio = "我喜歡旅遊和美食"
        interests = ["旅遊", "美食", "攝影"]

        is_approved, violations, action = await ContentModerationService.check_profile_content(
            db=test_db, user_id=test_user.id, bio=bio, interests=interests
        )

        assert is_approved is True
        assert len(violations) == 0

    async def test_check_unsafe_bio(self, test_db: AsyncSession, test_user: User, sensitive_words):
        """測試包含敏感詞的個人簡介（WARN 級別）"""
        bio = "想要投資賺錢嗎？"

        is_approved, violations, action = await ContentModerationService.check_profile_content(
            db=test_db, user_id=test_user.id, bio=bio
        )

        # "投資" 是 WARN 級別，仍然通過但有警告
        assert is_approved is True
        assert violations == ["個人簡介 - SCAM: 投資"]
        assert action == "WARN"

    async def test_check_rejected_bio(
        self, test_db: AsyncSession, test_user: User, sensitive_words
    ):
        """測試包含嚴重敏感詞的個人簡介（REJECT 級別）"""
        bio = "約炮嗎"

        is_approved, violations, action = await ContentModerationService.check_profile_content(
            db=test_db, user_id=test_user.id, bio=bio
        )

        # "約炮" 是 REJECT 級別，不通過
        assert is_approved is False
        assert len(violations) > 0
        assert action == "REJECT"

    async def test_check_unsafe_interests(
        self, test_db: AsyncSession, test_user: User, sensitive_words
    ):
        """測試包含敏感詞的興趣標籤"""
        interests = ["旅遊", "色情", "攝影"]

        is_approved, violations, action = await ContentModerationService.check_profile_content(
            db=test_db, user_id=test_user.id, interests=interests
        )

        assert is_approved is False
        assert violations == ["興趣標籤 '色情' - SEXUAL: 色情"]
        assert action == "REJECT"

    async def test_check_warned_interest(
        self, test_db: AsyncSession, test_user: User, sensitive_words
    ):
        """測試興趣標籤只命中 WARN 級別：通過但仍回報違規"""
        is_approved, violations, action = await ContentModerationService.check_profile_content(
            db=test_db, user_id=test_user.id, interests=["投資"]
        )

        assert (is_approved, action) == (True, "WARN")
        assert violations == ["興趣標籤 '投資' - SCAM: 投資"]

    async def test_later_warning_does_not_downgrade_reject(
        self, test_db: AsyncSession, test_user: User, sensitive_words
    ):
        """測試簡介已被拒絕時，後面興趣標籤的 WARN 不會把結果降級成通過"""
        is_approved, violations, action = await ContentModerationService.check_profile_content(
            db=test_db, user_id=test_user.id, bio="約炮嗎", interests=["投資"]
        )

        assert (is_approved, action) == (False, "REJECT")
        assert violations == ["個人簡介 - HARASSMENT: 約炮", "興趣標籤 '投資' - SCAM: 投資"]

    @pytest.fixture
    async def auto_ban_word(self, test_db: AsyncSession, sensitive_words):
        test_db.add(
            SensitiveWord(
                word="炸彈",
                category="VIOLENCE",
                severity="CRITICAL",
                action="AUTO_BAN",
                is_regex=False,
                is_active=True,
            )
        )
        await test_db.commit()
        await ContentModerationService.clear_cache()

    @pytest.mark.parametrize("field", ["bio", "interests"])
    async def test_auto_ban_word_rejects_profile(
        self, test_db: AsyncSession, test_user: User, auto_ban_word, field: str
    ):
        """測試命中 AUTO_BAN 敏感詞時不通過，且動作為 AUTO_BAN"""
        kwargs = {"bio": "我有炸彈"} if field == "bio" else {"interests": ["炸彈"]}

        is_approved, _, action = await ContentModerationService.check_profile_content(
            db=test_db, user_id=test_user.id, **kwargs
        )

        assert (is_approved, action) == (False, "AUTO_BAN")

    async def test_later_reject_does_not_downgrade_auto_ban(
        self, test_db: AsyncSession, test_user: User, auto_ban_word
    ):
        """測試簡介命中 AUTO_BAN 時，之後興趣標籤的 REJECT 不會把動作降級"""
        is_approved, violations, action = await ContentModerationService.check_profile_content(
            db=test_db, user_id=test_user.id, bio="我有炸彈", interests=["色情"]
        )

        assert (is_approved, action) == (False, "AUTO_BAN")
        assert violations == ["個人簡介 - VIOLENCE: 炸彈", "興趣標籤 '色情' - SEXUAL: 色情"]

    async def test_profile_violations_logged_as_profile(
        self, test_db: AsyncSession, test_user: User, sensitive_words
    ):
        """測試簡介與興趣標籤的違規都以 PROFILE 類型記錄在該用戶名下"""
        await ContentModerationService.check_profile_content(
            db=test_db, user_id=test_user.id, bio="想投資嗎", interests=["色情"]
        )

        result = await test_db.execute(
            select(ModerationLog).where(ModerationLog.user_id == test_user.id)
        )
        logs = result.scalars().all()
        assert sorted((log.original_content, log.content_type) for log in logs) == [
            ("想投資嗎", "PROFILE"),
            ("色情", "PROFILE"),
        ]

    async def test_check_profile_with_none_values(
        self, test_db: AsyncSession, test_user: User, sensitive_words
    ):
        """測試 None 值的個人檔案"""
        is_approved, violations, action = await ContentModerationService.check_profile_content(
            db=test_db, user_id=test_user.id, bio=None, interests=None
        )

        assert is_approved is True
        assert len(violations) == 0


@pytest.mark.asyncio
class TestMessageContentCheck:
    """聊天訊息內容審核測試"""

    async def test_check_safe_message(
        self, test_db: AsyncSession, test_user: User, sensitive_words
    ):
        """測試安全的聊天訊息"""
        message = "今天天氣真好，要不要一起去喝咖啡？"

        is_approved, violations, action = await ContentModerationService.check_message_content(
            message, test_db, test_user.id
        )

        assert is_approved is True
        assert len(violations) == 0

    async def test_check_warned_message(
        self, test_db: AsyncSession, test_user: User, sensitive_words
    ):
        """測試包含可疑內容的聊天訊息（WARN 級別）"""
        message = "加我LINE: abc123，我們私下聊"

        is_approved, violations, action = await ContentModerationService.check_message_content(
            message, test_db, test_user.id
        )

        # 可疑模式是 WARN，仍然通過但有警告
        assert is_approved is True
        assert len(violations) > 0
        assert action == "WARN"

    async def test_check_rejected_message(
        self, test_db: AsyncSession, test_user: User, sensitive_words
    ):
        """測試包含嚴重敏感詞的聊天訊息（REJECT 級別）"""
        message = "色情影片"

        is_approved, violations, action = await ContentModerationService.check_message_content(
            message, test_db, test_user.id
        )

        assert is_approved is False
        assert len(violations) > 0
        assert action == "REJECT"


@pytest.mark.asyncio
class TestModerationLogging:
    """審核日誌測試"""

    async def test_moderation_log_created(
        self, test_db: AsyncSession, test_user: User, sensitive_words
    ):
        """測試審核日誌是否正確創建"""
        content = "色情內容"

        is_approved, violations, action = await ContentModerationService.check_message_content(
            content, test_db, test_user.id
        )

        # 日誌由獨立 session 提交，重新查詢即可看到
        result = await test_db.execute(
            select(ModerationLog).where(ModerationLog.user_id == test_user.id)
        )
        logs = result.scalars().all()

        assert is_approved is False
        assert len(logs) == 1
        log = logs[0]
        assert log.content_type == "MESSAGE"
        assert log.original_content == content
        assert log.is_approved is False
        assert log.action_taken == "REJECT"
        assert json.loads(log.violations) == violations
        assert "色情" in log.violations  # ensure_ascii=False：後台可直接閱讀中文
        triggered = next(w for w in sensitive_words if w.word == "色情")
        assert json.loads(log.triggered_word_ids) == [str(triggered.id)]

    async def test_suspicious_pattern_log_has_no_word_ids(
        self, test_db: AsyncSession, test_user: User, sensitive_words
    ):
        """測試只命中可疑模式（未命中敏感詞）時仍記錄日誌，且 triggered_word_ids 為空"""
        is_approved, _, _, action = await ContentModerationService.check_content(
            "看這裡 https://example.com", test_db, test_user.id, "MESSAGE"
        )

        result = await test_db.execute(
            select(ModerationLog).where(ModerationLog.user_id == test_user.id)
        )
        log = result.scalar_one()
        assert (is_approved, action) == (True, "WARN")
        assert log.is_approved is True
        assert log.triggered_word_ids is None

    async def test_clean_content_not_logged(
        self, test_db: AsyncSession, test_user: User, sensitive_words
    ):
        """測試正常內容不寫審核日誌（避免每則聊天訊息都進日誌表）"""
        await ContentModerationService.check_content("你好", test_db, test_user.id, "MESSAGE")

        result = await test_db.execute(select(ModerationLog))
        assert result.scalars().all() == []

    async def test_violation_without_user_not_logged(self, test_db: AsyncSession, sensitive_words):
        """測試未提供 user_id 時只回傳審核結果，不寫日誌"""
        is_approved, _, _, _ = await ContentModerationService.check_content(
            "色情內容", test_db, None, "MESSAGE"
        )

        result = await test_db.execute(select(ModerationLog))
        assert is_approved is False
        assert result.scalars().all() == []


@pytest.mark.asyncio
class TestEdgeCases:
    """邊界案例測試"""

    async def test_case_insensitive_detection(
        self, test_db: AsyncSession, test_user: User, sensitive_words
    ):
        """測試大小寫不敏感偵測"""
        # 測試英文關鍵詞大小寫
        content1 = "加我LINE: abc123"
        content2 = "加我line: abc123"
        content3 = "加我Line: abc123"

        result1 = await ContentModerationService.check_content(
            content1, test_db, test_user.id, "MESSAGE"
        )
        result2 = await ContentModerationService.check_content(
            content2, test_db, test_user.id, "MESSAGE"
        )
        result3 = await ContentModerationService.check_content(
            content3, test_db, test_user.id, "MESSAGE"
        )

        # 都應該被偵測到（WARN 級別，仍通過）
        assert result1[0] is True  # is_approved
        assert result2[0] is True
        assert result3[0] is True
        assert len(result1[1]) > 0  # violations
        assert len(result2[1]) > 0
        assert len(result3[1]) > 0

    async def test_multiple_violations(
        self, test_db: AsyncSession, test_user: User, sensitive_words
    ):
        """測試多重違規"""
        content = "色情網站 http://bad.com 快加我LINE: baduser"

        is_approved, violations, word_ids, action = await ContentModerationService.check_content(
            content, test_db, test_user.id, "MESSAGE"
        )

        # 應該因為"色情"被拒絕（REJECT 優先級最高）
        assert is_approved is False
        # 應該至少有 3 個違規：色情、URL、LINE ID
        assert len(violations) >= 3
        assert action == "REJECT"

    async def test_long_content(self, test_db: AsyncSession, test_user: User, sensitive_words):
        """測試長內容"""
        content = "正常內容 " * 100 + " 色情 " + "正常內容 " * 100

        is_approved, violations, word_ids, action = await ContentModerationService.check_content(
            content, test_db, test_user.id, "MESSAGE"
        )

        assert is_approved is False
        assert len(violations) > 0


@pytest.mark.asyncio
class TestCaching:
    """快取機制測試"""

    async def test_cache_mechanism(self, test_db: AsyncSession, test_user: User, sensitive_words):
        """測試敏感詞快取機制"""
        content = "色情內容"

        # 第一次呼叫（會載入並快取）
        result1 = await ContentModerationService.check_content(
            content, test_db, test_user.id, "MESSAGE"
        )

        # 停用該詞：快取期間仍沿用舊詞庫（因此管理 API 異動後必須 clear_cache）
        await test_db.execute(
            update(SensitiveWord).where(SensitiveWord.word == "色情").values(is_active=False)
        )
        await test_db.commit()
        result2 = await ContentModerationService.check_content(
            content, test_db, test_user.id, "MESSAGE"
        )

        await ContentModerationService.clear_cache()
        result3 = await ContentModerationService.check_content(
            content, test_db, test_user.id, "MESSAGE"
        )

        assert result1[0] is False
        assert result2[0] is False  # 命中快取
        assert result3[0] is True  # 清除快取後重新載入

    async def test_memory_cache_expires_after_ttl(
        self, test_db: AsyncSession, test_user: User, sensitive_words
    ):
        """測試內存快取超過 TTL 後重新從資料庫載入"""
        await ContentModerationService.check_content("色情內容", test_db, test_user.id, "MESSAGE")
        await test_db.execute(
            update(SensitiveWord).where(SensitiveWord.word == "色情").values(is_active=False)
        )
        await test_db.commit()

        # 把快取時間往前推到剛好過期
        ContentModerationService._cache_time -= timedelta(
            seconds=ContentModerationService._cache_ttl
        )
        is_approved, _, _, _ = await ContentModerationService.check_content(
            "色情內容", test_db, test_user.id, "MESSAGE"
        )

        assert is_approved is True

    async def test_clear_cache(self, test_db: AsyncSession):
        """測試清除快取"""
        # 清除快取不應該拋出異常
        await ContentModerationService.clear_cache()

        # 再次清除也應該正常
        await ContentModerationService.clear_cache()


@pytest.mark.asyncio
class TestRegexSensitiveWords:
    """正則敏感詞測試"""

    async def test_regex_word_matches_case_insensitively(
        self, test_db: AsyncSession, test_user: User, regex_words
    ):
        """測試正則敏感詞不分大小寫比對"""
        is_approved, violations, word_ids, action = await ContentModerationService.check_content(
            "Get FREE   Money now", test_db, test_user.id, "MESSAGE"
        )

        assert (is_approved, action) == (False, "REJECT")
        assert violations == [r"SCAM: free\s*money"]
        assert word_ids == [regex_words[1].id]

    async def test_plain_word_matches_case_insensitively(
        self, test_db: AsyncSession, test_user: User, regex_words
    ):
        """測試英文純文字敏感詞不分大小寫比對"""
        is_approved, violations, word_ids, action = await ContentModerationService.check_content(
            "NO SPAM please", test_db, test_user.id, "MESSAGE"
        )

        assert (is_approved, action) == (True, "WARN")
        assert violations == ["OTHER: spam"]
        assert word_ids == [regex_words[2].id]

    async def test_invalid_regex_never_matches(
        self, test_db: AsyncSession, test_user: User, regex_words
    ):
        """測試無效正則視為不命中（不拋錯、不誤判）"""
        is_approved, violations, _, action = await ContentModerationService.check_content(
            "([ 括號", test_db, test_user.id, "MESSAGE"
        )

        assert (is_approved, violations, action) == (True, [], "APPROVED")


class TestSeverityPriority:
    """多個敏感詞同時命中時的嚴重程度排序"""

    @staticmethod
    def _word(word: str, severity: str, action: str) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "word": word,
            "category": "OTHER",
            "severity": severity,
            "action": action,
            "is_regex": False,
        }

    @pytest.mark.parametrize(
        "lower,higher",
        [
            (("LOW", "WARN"), ("MEDIUM", "REJECT")),
            (("MEDIUM", "WARN"), ("HIGH", "REJECT")),
            (("HIGH", "REJECT"), ("CRITICAL", "AUTO_BAN")),
        ],
    )
    @pytest.mark.parametrize("higher_first", [False, True])
    def test_highest_severity_decides_action(self, lower, higher, higher_first):
        """測試以最高嚴重程度那個詞的動作為準，與詞庫順序無關"""
        words = [self._word("甲", *lower), self._word("乙", *higher)]
        if higher_first:
            words.reverse()

        violations, word_ids, max_severity, action = (
            ContentModerationService._check_sensitive_words(words, "甲乙", "甲乙")
        )

        assert (max_severity, action) == higher
        assert len(violations) == len(word_ids) == 2


@pytest.mark.asyncio
class TestRedisCache:
    """Redis 快取測試（正式環境路徑；其餘測試未設定 Redis，走內存快取）"""

    @pytest.fixture(autouse=True)
    def _restore_redis_state(self, monkeypatch):
        """測試後還原 class 層級的 Redis 狀態，避免影響其他測試"""
        monkeypatch.setattr(ContentModerationService, "_redis", None)
        monkeypatch.setattr(ContentModerationService, "_use_redis", False)

    async def test_words_cached_to_redis(
        self, test_db: AsyncSession, test_user: User, sensitive_words, mock_redis
    ):
        """測試從資料庫載入的敏感詞寫入 Redis（含 TTL）"""
        await ContentModerationService.set_redis(mock_redis)
        assert ContentModerationService.is_using_redis() is True

        await ContentModerationService.check_content("你好", test_db, test_user.id, "MESSAGE")

        mock_redis.set.assert_called_once()
        (key, payload), kwargs = mock_redis.set.call_args
        assert key == "moderation:words"
        assert kwargs == {"ex": 300}
        assert "色情" in payload  # ensure_ascii=False
        assert {w["word"] for w in json.loads(payload)} == {w.word for w in sensitive_words}

    async def test_redis_cache_hit_skips_db(
        self, test_db: AsyncSession, test_user: User, mock_redis
    ):
        """測試 Redis 有快取時直接使用（資料庫中沒有這個詞）"""
        cached = [
            {
                "id": str(uuid.uuid4()),
                "word": "暗號",
                "category": "OTHER",
                "severity": "HIGH",
                "action": "REJECT",
                "is_regex": False,
            }
        ]
        mock_redis._storage["moderation:words"] = json.dumps(cached, ensure_ascii=False)
        await ContentModerationService.set_redis(mock_redis)

        is_approved, violations, _, _ = await ContentModerationService.check_content(
            "對暗號", test_db, test_user.id, "MESSAGE"
        )

        assert is_approved is False
        assert violations == ["OTHER: 暗號"]

    async def test_redis_error_falls_back_to_db(
        self, test_db: AsyncSession, test_user: User, sensitive_words, mock_redis_error
    ):
        """測試 Redis 故障時回退資料庫，審核照常運作，且之後不再讀寫 Redis"""
        await ContentModerationService.set_redis(mock_redis_error)

        results = [
            await ContentModerationService.check_content(
                "色情內容", test_db, test_user.id, "MESSAGE"
            )
            for _ in range(2)
        ]

        assert [r[0] for r in results] == [False, False]
        assert ContentModerationService.is_using_redis() is False
        mock_redis_error.get.assert_called_once()  # 第二次不再嘗試故障的 Redis
        mock_redis_error.set.assert_not_called()

    async def test_clear_cache_deletes_redis_key(self, mock_redis):
        """測試清除快取時一併刪除 Redis 中的敏感詞快取（否則其他 worker 仍讀到舊詞庫）"""
        mock_redis._storage["moderation:words"] = "[]"
        await ContentModerationService.set_redis(mock_redis)

        await ContentModerationService.clear_cache()

        assert "moderation:words" not in mock_redis._storage

    async def test_clear_cache_tolerates_redis_error(self, mock_redis_error):
        """測試 Redis 故障時清除快取不拋錯"""
        await ContentModerationService.set_redis(mock_redis_error)

        await ContentModerationService.clear_cache()

        mock_redis_error.delete.assert_called_once_with("moderation:words")
