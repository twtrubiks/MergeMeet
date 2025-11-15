"""內容審核服務 - 基於資料庫的動態敏感詞管理"""
from typing import Tuple, List, Optional, Dict
import re
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import json

from app.models.moderation import SensitiveWord, ModerationLog


class ContentModerationService:
    """內容審核服務 - 負責檢測敏感詞和不當內容"""

    # 快取敏感詞（避免每次都查詢資料庫）
    _cache: Dict[str, List[SensitiveWord]] = {}
    _cache_time: Optional[datetime] = None
    _cache_ttl: int = 300  # 快取 5 分鐘

    # 可疑模式（正則表達式）- 保留靜態模式
    SUSPICIOUS_PATTERNS = [
        r'\b\d{10,16}\b',  # 可能的信用卡號或手機號碼
        r'line\s*[:：]?\s*\w+',  # LINE ID
        r'wechat\s*[:：]?\s*\w+',  # WeChat ID
        r'(?:http|https)://\S+',  # URL 連結
        r'\$\d+|NT\$?\d+|USD?\d+',  # 金額
    ]

    @classmethod
    async def _load_sensitive_words(cls, db: AsyncSession) -> List[SensitiveWord]:
        """
        從資料庫載入敏感詞（帶快取機制）

        Args:
            db: 資料庫 session

        Returns:
            敏感詞列表
        """
        now = datetime.now()

        # 檢查快取是否有效
        if cls._cache_time and (now - cls._cache_time).total_seconds() < cls._cache_ttl:
            return cls._cache.get("words", [])

        # 從資料庫載入啟用的敏感詞
        result = await db.execute(
            select(SensitiveWord).where(SensitiveWord.is_active == True)
        )
        words = result.scalars().all()

        # 更新快取
        cls._cache = {"words": words}
        cls._cache_time = now

        return words

    @classmethod
    def clear_cache(cls):
        """清除敏感詞快取"""
        cls._cache = {}
        cls._cache_time = None

    @classmethod
    async def check_content(
        cls,
        content: str,
        db: AsyncSession,
        user_id: Optional[uuid.UUID] = None,
        content_type: str = "TEXT"
    ) -> Tuple[bool, List[str], List[uuid.UUID], str]:
        """
        檢查內容是否包含敏感詞或不當內容

        Args:
            content: 要檢查的內容
            db: 資料庫 session
            user_id: 用戶 ID（用於日誌記錄）
            content_type: 內容類型（MESSAGE, PROFILE, PHOTO）

        Returns:
            (is_approved, violations, triggered_word_ids, action):
            (是否通過, 違規項目列表, 觸發的敏感詞ID, 應採取的動作)
        """
        if not content:
            return True, [], [], "APPROVED"

        violations = []
        triggered_word_ids = []
        max_severity = "LOW"
        action_to_take = "APPROVED"

        content_lower = content.lower()

        # 載入敏感詞
        sensitive_words = await cls._load_sensitive_words(db)

        # 檢查敏感詞
        for word_obj in sensitive_words:
            matched = False

            if word_obj.is_regex:
                # 正則表達式匹配
                try:
                    pattern = re.compile(word_obj.word, re.IGNORECASE)
                    if pattern.search(content):
                        matched = True
                except re.error:
                    # 正則表達式無效，跳過
                    continue
            else:
                # 簡單字串匹配
                if word_obj.word in content_lower:
                    matched = True

            if matched:
                violations.append(f"{word_obj.category}: {word_obj.word}")
                triggered_word_ids.append(word_obj.id)

                # 更新最高嚴重程度和動作
                severity_order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
                if severity_order.get(word_obj.severity, 0) > severity_order.get(max_severity, 0):
                    max_severity = word_obj.severity
                    action_to_take = word_obj.action

        # 檢查可疑模式
        for pattern in cls.SUSPICIOUS_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                violations.append(f"包含可疑內容: {pattern}")
                # 可疑模式預設為 WARN
                if action_to_take == "APPROVED":
                    action_to_take = "WARN"

        # 判斷是否通過
        is_approved = action_to_take in ["APPROVED", "WARN"]

        # 記錄審核日誌
        if user_id and (violations or not is_approved):
            await cls._log_moderation(
                db=db,
                user_id=user_id,
                content_type=content_type,
                content=content,
                is_approved=is_approved,
                violations=violations,
                triggered_word_ids=triggered_word_ids,
                action_taken=action_to_take
            )

        return is_approved, violations, triggered_word_ids, action_to_take

    @classmethod
    async def _log_moderation(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        content_type: str,
        content: str,
        is_approved: bool,
        violations: List[str],
        triggered_word_ids: List[uuid.UUID],
        action_taken: str
    ):
        """
        記錄審核日誌

        Args:
            db: 資料庫 session
            user_id: 用戶 ID
            content_type: 內容類型
            content: 原始內容
            is_approved: 是否通過
            violations: 違規項目
            triggered_word_ids: 觸發的敏感詞 ID
            action_taken: 採取的動作
        """
        log = ModerationLog(
            user_id=user_id,
            content_type=content_type,
            original_content=content,
            is_approved=is_approved,
            violations=json.dumps(violations, ensure_ascii=False) if violations else None,
            triggered_word_ids=json.dumps([str(wid) for wid in triggered_word_ids]) if triggered_word_ids else None,
            action_taken=action_taken
        )

        db.add(log)
        # 不自動 commit，由調用者決定何時提交
        # 這樣可以避免在其他事務中調用時產生問題
        await db.flush()

    @classmethod
    async def sanitize_content(cls, content: str, db: AsyncSession) -> str:
        """
        清理內容，移除或替換敏感詞

        Args:
            content: 原始內容
            db: 資料庫 session

        Returns:
            清理後的內容
        """
        if not content:
            return content

        sanitized = content

        # 載入敏感詞
        sensitive_words = await cls._load_sensitive_words(db)

        # 替換敏感詞為 ***
        for word_obj in sensitive_words:
            if word_obj.is_regex:
                try:
                    pattern = re.compile(word_obj.word, re.IGNORECASE)
                    sanitized = pattern.sub('***', sanitized)
                except re.error:
                    continue
            else:
                pattern = re.compile(re.escape(word_obj.word), re.IGNORECASE)
                sanitized = pattern.sub('***', sanitized)

        # 移除可疑的 URL
        sanitized = re.sub(r'(?:http|https)://\S+', '[已移除連結]', sanitized)

        return sanitized

    @classmethod
    async def check_profile_content(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        bio: str = None,
        interests: List[str] = None
    ) -> Tuple[bool, List[str], str]:
        """
        檢查個人檔案內容

        Args:
            db: 資料庫 session
            user_id: 用戶 ID
            bio: 個人簡介
            interests: 興趣列表

        Returns:
            (is_approved, violations, action): (是否通過, 違規項目列表, 應採取的動作)
        """
        all_violations = []
        all_triggered_word_ids = []
        max_action = "APPROVED"

        # 檢查個人簡介
        if bio:
            is_approved, violations, word_ids, action = await cls.check_content(
                bio, db, user_id, "PROFILE"
            )
            if not is_approved or violations:
                all_violations.extend([f"個人簡介 - {v}" for v in violations])
                all_triggered_word_ids.extend(word_ids)
                if action in ["AUTO_BAN", "REJECT"]:
                    max_action = action
                elif action == "WARN" and max_action == "APPROVED":
                    max_action = "WARN"

        # 檢查興趣標籤
        if interests:
            for interest in interests:
                is_approved, violations, word_ids, action = await cls.check_content(
                    interest, db, user_id, "PROFILE"
                )
                if not is_approved or violations:
                    all_violations.extend([f"興趣標籤 '{interest}' - {v}" for v in violations])
                    all_triggered_word_ids.extend(word_ids)
                    if action in ["AUTO_BAN", "REJECT"]:
                        max_action = action
                    elif action == "WARN" and max_action == "APPROVED":
                        max_action = "WARN"

        is_approved = max_action in ["APPROVED", "WARN"]
        return is_approved, all_violations, max_action

    @classmethod
    async def check_message_content(
        cls,
        message: str,
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> Tuple[bool, List[str], str]:
        """
        檢查聊天訊息內容

        Args:
            message: 聊天訊息
            db: 資料庫 session
            user_id: 用戶 ID

        Returns:
            (is_approved, violations, action): (是否通過, 違規項目列表, 應採取的動作)
        """
        is_approved, violations, word_ids, action = await cls.check_content(
            message, db, user_id, "MESSAGE"
        )
        return is_approved, violations, action
