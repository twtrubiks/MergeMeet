"""內容審核服務"""
from typing import Tuple, List
import re


class ContentModerationService:
    """內容審核服務 - 負責檢測敏感詞和不當內容"""

    # 敏感詞列表（實際應用應從資料庫載入）
    SENSITIVE_WORDS = {
        # 色情相關
        "色情", "裸露", "成人", "18禁",
        # 詐騙相關
        "詐騙", "匯款", "轉帳", "投資", "賺錢", "兼職", "加賴",
        # 騷擾相關
        "約炮", "一夜情", "援交",
        # 個人資訊（過度分享）
        "身分證", "信用卡", "銀行帳號",
        # 暴力相關
        "殺", "死", "暴力",
    }

    # 可疑模式（正則表達式）
    SUSPICIOUS_PATTERNS = [
        r'\b\d{10,16}\b',  # 可能的信用卡號或手機號碼
        r'line\s*[:：]?\s*\w+',  # LINE ID
        r'wechat\s*[:：]?\s*\w+',  # WeChat ID
        r'(?:http|https)://\S+',  # URL 連結
        r'\$\d+|NT\$?\d+|USD?\d+',  # 金額
    ]

    @classmethod
    def check_content(cls, content: str) -> Tuple[bool, List[str]]:
        """
        檢查內容是否包含敏感詞或不當內容

        Args:
            content: 要檢查的內容

        Returns:
            (is_safe, violations): (是否安全, 違規項目列表)
        """
        if not content:
            return True, []

        violations = []
        content_lower = content.lower()

        # 檢查敏感詞
        for word in cls.SENSITIVE_WORDS:
            if word in content_lower:
                violations.append(f"包含敏感詞: {word}")

        # 檢查可疑模式
        for pattern in cls.SUSPICIOUS_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                violations.append(f"包含可疑內容: {pattern}")

        is_safe = len(violations) == 0
        return is_safe, violations

    @classmethod
    def sanitize_content(cls, content: str) -> str:
        """
        清理內容，移除或替換敏感詞

        Args:
            content: 原始內容

        Returns:
            清理後的內容
        """
        if not content:
            return content

        sanitized = content

        # 替換敏感詞為 ***
        for word in cls.SENSITIVE_WORDS:
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            sanitized = pattern.sub('***', sanitized)

        # 移除可疑的 URL
        sanitized = re.sub(r'(?:http|https)://\S+', '[已移除連結]', sanitized)

        return sanitized

    @classmethod
    def check_profile_content(cls, bio: str = None, interests: List[str] = None) -> Tuple[bool, List[str]]:
        """
        檢查個人檔案內容

        Args:
            bio: 個人簡介
            interests: 興趣列表

        Returns:
            (is_safe, violations): (是否安全, 違規項目列表)
        """
        violations = []

        # 檢查個人簡介
        if bio:
            is_safe, bio_violations = cls.check_content(bio)
            if not is_safe:
                violations.extend([f"個人簡介 - {v}" for v in bio_violations])

        # 檢查興趣標籤
        if interests:
            for interest in interests:
                is_safe, interest_violations = cls.check_content(interest)
                if not is_safe:
                    violations.extend([f"興趣標籤 '{interest}' - {v}" for v in interest_violations])

        return len(violations) == 0, violations

    @classmethod
    def check_message_content(cls, message: str) -> Tuple[bool, List[str]]:
        """
        檢查聊天訊息內容

        Args:
            message: 聊天訊息

        Returns:
            (is_safe, violations): (是否安全, 違規項目列表)
        """
        return cls.check_content(message)

    @classmethod
    def add_sensitive_word(cls, word: str) -> None:
        """
        新增敏感詞（僅用於測試或動態更新）

        Args:
            word: 敏感詞
        """
        cls.SENSITIVE_WORDS.add(word.lower())

    @classmethod
    def remove_sensitive_word(cls, word: str) -> None:
        """
        移除敏感詞

        Args:
            word: 敏感詞
        """
        cls.SENSITIVE_WORDS.discard(word.lower())
