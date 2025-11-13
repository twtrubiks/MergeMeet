"""內容審核服務測試"""
import pytest
from app.services.content_moderation import ContentModerationService


class TestContentModerationBasic:
    """基本內容審核測試"""

    @pytest.mark.unit
    def test_check_safe_content(self):
        """測試正常安全內容"""
        content = "你好，很高興認識你！"
        is_safe, violations = ContentModerationService.check_content(content)

        assert is_safe is True
        assert len(violations) == 0

    @pytest.mark.unit
    def test_check_empty_content(self):
        """測試空內容"""
        is_safe, violations = ContentModerationService.check_content("")

        assert is_safe is True
        assert len(violations) == 0

    @pytest.mark.unit
    def test_check_none_content(self):
        """測試 None 內容"""
        is_safe, violations = ContentModerationService.check_content(None)

        assert is_safe is True
        assert len(violations) == 0


class TestSensitiveWords:
    """敏感詞測試"""

    @pytest.mark.unit
    @pytest.mark.parametrize("content,expected_word", [
        ("想要看色情影片嗎？", "色情"),
        ("這裡有裸露的照片", "裸露"),
        ("18禁的內容", "18禁"),
        ("請匯款到這個帳號", "匯款"),
        ("加入我們的投資計畫", "投資"),
        ("兼職賺錢機會", "兼職"),
        ("約炮嗎", "約炮"),
        ("一夜情", "一夜情"),
    ])
    def test_detect_sensitive_words(self, content: str, expected_word: str):
        """測試敏感詞偵測"""
        is_safe, violations = ContentModerationService.check_content(content)

        assert is_safe is False
        assert len(violations) > 0
        assert any(expected_word in v for v in violations)


class TestSuspiciousPatterns:
    """可疑模式測試"""

    @pytest.mark.unit
    def test_detect_line_id(self):
        """測試 LINE ID 偵測"""
        content = "加我LINE: abc123"
        is_safe, violations = ContentModerationService.check_content(content)

        assert is_safe is False
        assert len(violations) > 0

    @pytest.mark.unit
    def test_detect_phone_number(self):
        """測試電話號碼偵測"""
        content = "我的電話是 0912345678"
        is_safe, violations = ContentModerationService.check_content(content)

        assert is_safe is False
        assert len(violations) > 0

    @pytest.mark.unit
    def test_detect_url(self):
        """測試 URL 偵測"""
        content = "點擊這個連結 http://scam.com"
        is_safe, violations = ContentModerationService.check_content(content)

        assert is_safe is False
        assert len(violations) > 0

    @pytest.mark.unit
    def test_detect_https_url(self):
        """測試 HTTPS URL 偵測"""
        content = "訪問 https://suspicious-site.com 獲取更多資訊"
        is_safe, violations = ContentModerationService.check_content(content)

        assert is_safe is False
        assert len(violations) > 0

    @pytest.mark.unit
    def test_detect_wechat_id(self):
        """測試 WeChat ID 偵測"""
        content = "加我 wechat: myid123"
        is_safe, violations = ContentModerationService.check_content(content)

        assert is_safe is False
        assert len(violations) > 0

    @pytest.mark.unit
    @pytest.mark.parametrize("content", [
        "只需 $100 就能獲得",
        "NT$5000 投資回報",
        "USD1000 快速賺錢",
    ])
    def test_detect_money_amount(self, content: str):
        """測試金額偵測"""
        is_safe, violations = ContentModerationService.check_content(content)

        assert is_safe is False
        assert len(violations) > 0


class TestContentSanitization:
    """內容清理測試"""

    @pytest.mark.unit
    def test_sanitize_sensitive_words(self):
        """測試敏感詞替換"""
        content = "這裡有色情內容"
        sanitized = ContentModerationService.sanitize_content(content)

        assert "色情" not in sanitized
        assert "***" in sanitized

    @pytest.mark.unit
    def test_sanitize_url(self):
        """測試 URL 移除"""
        content = "訪問 http://example.com 查看"
        sanitized = ContentModerationService.sanitize_content(content)

        assert "http://example.com" not in sanitized
        assert "[已移除連結]" in sanitized

    @pytest.mark.unit
    def test_sanitize_empty_content(self):
        """測試空內容清理"""
        sanitized = ContentModerationService.sanitize_content("")
        assert sanitized == ""

    @pytest.mark.unit
    def test_sanitize_none_content(self):
        """測試 None 內容清理"""
        sanitized = ContentModerationService.sanitize_content(None)
        assert sanitized is None


class TestProfileContentCheck:
    """個人檔案內容審核測試"""

    @pytest.mark.unit
    def test_check_safe_profile(self):
        """測試安全的個人檔案"""
        bio = "我喜歡旅遊和美食"
        interests = ["旅遊", "美食", "攝影"]

        is_safe, violations = ContentModerationService.check_profile_content(
            bio=bio,
            interests=interests
        )

        assert is_safe is True
        assert len(violations) == 0

    @pytest.mark.unit
    def test_check_unsafe_bio(self):
        """測試包含敏感詞的個人簡介"""
        bio = "想要投資賺錢嗎？"

        is_safe, violations = ContentModerationService.check_profile_content(bio=bio)

        assert is_safe is False
        assert len(violations) > 0
        assert any("個人簡介" in v for v in violations)

    @pytest.mark.unit
    def test_check_unsafe_interests(self):
        """測試包含敏感詞的興趣標籤"""
        interests = ["旅遊", "色情", "攝影"]

        is_safe, violations = ContentModerationService.check_profile_content(
            interests=interests
        )

        assert is_safe is False
        assert len(violations) > 0
        assert any("興趣標籤" in v for v in violations)

    @pytest.mark.unit
    def test_check_profile_with_none_values(self):
        """測試 None 值的個人檔案"""
        is_safe, violations = ContentModerationService.check_profile_content(
            bio=None,
            interests=None
        )

        assert is_safe is True
        assert len(violations) == 0


class TestMessageContentCheck:
    """聊天訊息內容審核測試"""

    @pytest.mark.unit
    def test_check_safe_message(self):
        """測試安全的聊天訊息"""
        message = "今天天氣真好，要不要一起去喝咖啡？"

        is_safe, violations = ContentModerationService.check_message_content(message)

        assert is_safe is True
        assert len(violations) == 0

    @pytest.mark.unit
    def test_check_unsafe_message(self):
        """測試包含敏感內容的聊天訊息"""
        message = "加我LINE: abc123，我們私下聊"

        is_safe, violations = ContentModerationService.check_message_content(message)

        assert is_safe is False
        assert len(violations) > 0


class TestDynamicSensitiveWords:
    """動態敏感詞管理測試"""

    @pytest.mark.unit
    def test_add_sensitive_word(self):
        """測試新增敏感詞"""
        # 新增自訂敏感詞
        ContentModerationService.add_sensitive_word("測試敏感詞")

        # 檢查是否能偵測到
        is_safe, violations = ContentModerationService.check_content("這是測試敏感詞")

        assert is_safe is False
        assert len(violations) > 0

        # 清理：移除測試用敏感詞
        ContentModerationService.remove_sensitive_word("測試敏感詞")

    @pytest.mark.unit
    def test_remove_sensitive_word(self):
        """測試移除敏感詞"""
        # 先新增
        ContentModerationService.add_sensitive_word("臨時詞")

        # 確認可以偵測
        is_safe_before, _ = ContentModerationService.check_content("這是臨時詞")
        assert is_safe_before is False

        # 移除
        ContentModerationService.remove_sensitive_word("臨時詞")

        # 確認無法偵測
        is_safe_after, _ = ContentModerationService.check_content("這是臨時詞")
        assert is_safe_after is True


class TestEdgeCases:
    """邊界案例測試"""

    @pytest.mark.unit
    def test_case_insensitive_detection(self):
        """測試大小寫不敏感偵測"""
        # 中文通常沒有大小寫，但測試英文關鍵詞
        content1 = "加我LINE: abc123"
        content2 = "加我line: abc123"
        content3 = "加我Line: abc123"

        is_safe1, _ = ContentModerationService.check_content(content1)
        is_safe2, _ = ContentModerationService.check_content(content2)
        is_safe3, _ = ContentModerationService.check_content(content3)

        assert is_safe1 is False
        assert is_safe2 is False
        assert is_safe3 is False

    @pytest.mark.unit
    def test_multiple_violations(self):
        """測試多重違規"""
        content = "色情網站 http://bad.com 快加我LINE: baduser"

        is_safe, violations = ContentModerationService.check_content(content)

        assert is_safe is False
        # 應該至少有 3 個違規：色情、URL、LINE ID
        assert len(violations) >= 3

    @pytest.mark.unit
    def test_long_content(self):
        """測試長內容"""
        content = "正常內容 " * 100 + " 色情 " + "正常內容 " * 100

        is_safe, violations = ContentModerationService.check_content(content)

        assert is_safe is False
        assert len(violations) > 0
