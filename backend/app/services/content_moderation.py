"""內容審核服務 - 基於資料庫的動態敏感詞管理

支援 Redis 快取（優先）和內存回退。
當 Redis 不可用時，自動回退到內存快取並記錄警告。

Redis Key 設計：
- moderation:words - 敏感詞列表 (value: JSON 序列化, TTL: 300 秒)
"""
from typing import Tuple, List, Optional, Dict
from collections import OrderedDict
import re
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import json
import asyncio
import logging

import redis.asyncio as aioredis

from app.models.moderation import SensitiveWord, ModerationLog

logger = logging.getLogger(__name__)

# Redis Key 常量
REDIS_KEY_SENSITIVE_WORDS = "moderation:words"


class ContentModerationService:
    """內容審核服務 - 負責檢測敏感詞和不當內容

    支援 Redis 快取（優先）和內存回退。
    當 Redis 不可用時，自動回退到內存快取並記錄警告。
    """

    # Redis 連線
    _redis: Optional[aioredis.Redis] = None
    _use_redis: bool = False

    # 內存回退快取
    _cache: OrderedDict = OrderedDict()  # 使用 OrderedDict 支持 LRU 策略
    _cache_time: Dict[str, datetime] = {}  # 每個快取項的時間戳
    _cache_ttl: int = 300  # 快取 5 分鐘
    _max_cache_size: int = 500  # 最大快取項數
    _cache_lock: Optional[asyncio.Lock] = None  # 快取鎖（延遲初始化）

    # 可疑模式（正則表達式）- 保留靜態模式
    SUSPICIOUS_PATTERNS = [
        r'\b\d{10,16}\b',  # 可能的信用卡號或手機號碼
        r'line\s*[:：]?\s*\w+',  # LINE ID
        r'wechat\s*[:：]?\s*\w+',  # WeChat ID
        r'(?:http|https)://\S+',  # URL 連結
        r'\$\d+|NT\$?\d+|USD?\d+',  # 金額
    ]

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        """獲取或創建快取鎖（延遲初始化避免事件循環問題）"""
        if cls._cache_lock is None:
            cls._cache_lock = asyncio.Lock()
        return cls._cache_lock

    @classmethod
    async def set_redis(cls, redis_client: aioredis.Redis) -> None:
        """設置或更新 Redis 連線

        Args:
            redis_client: Redis 連線
        """
        cls._redis = redis_client
        cls._use_redis = True
        logger.info("ContentModerationService Redis connection configured")

    @classmethod
    def is_using_redis(cls) -> bool:
        """檢查是否正在使用 Redis

        Returns:
            bool: True 如果使用 Redis，False 如果使用內存回退
        """
        return cls._use_redis and cls._redis is not None

    @classmethod
    async def _try_load_from_redis(cls) -> Optional[List[Dict]]:
        """嘗試從 Redis 載入敏感詞

        Returns:
            敏感詞列表（如果快取命中），否則 None
        """
        if not (cls._redis and cls._use_redis):
            return None

        try:
            cached = await cls._redis.get(REDIS_KEY_SENSITIVE_WORDS)
            if cached:
                logger.debug("Sensitive words loaded from Redis cache")
                return json.loads(cached)
        except aioredis.RedisError as e:
            logger.warning(
                f"Redis unavailable for sensitive words, "
                f"falling back to memory: {e}"
            )
            cls._use_redis = False

        return None

    @classmethod
    def _try_load_from_memory_cache(cls, cache_key: str) -> Optional[List[Dict]]:
        """嘗試從內存快取載入敏感詞

        Args:
            cache_key: 快取鍵

        Returns:
            敏感詞列表（如果快取有效），否則 None
        """
        now = datetime.now()
        cache_timestamp = cls._cache_time.get(cache_key)

        if not cache_timestamp:
            return None

        if (now - cache_timestamp).total_seconds() >= cls._cache_ttl:
            return None

        cached_words = cls._cache.get(cache_key)
        if cached_words is not None:
            cls._cache.move_to_end(cache_key)
            logger.debug("Sensitive words loaded from memory cache")
            return cached_words

        return None

    @classmethod
    async def _cache_to_redis(cls, words_data: List[Dict]) -> None:
        """將敏感詞快取到 Redis

        Args:
            words_data: 敏感詞列表
        """
        if not (cls._redis and cls._use_redis):
            return

        try:
            await cls._redis.setex(
                REDIS_KEY_SENSITIVE_WORDS,
                cls._cache_ttl,
                json.dumps(words_data, ensure_ascii=False)
            )
            logger.info(f"Sensitive words cached to Redis ({len(words_data)} words)")
        except aioredis.RedisError as e:
            logger.warning(f"Failed to cache sensitive words to Redis: {e}")

    @classmethod
    def _cache_to_memory(cls, cache_key: str, words_data: List[Dict]) -> None:
        """將敏感詞快取到內存

        Args:
            cache_key: 快取鍵
            words_data: 敏感詞列表
        """
        if len(cls._cache) >= cls._max_cache_size:
            oldest_key = next(iter(cls._cache))
            cls._cache.pop(oldest_key)
            cls._cache_time.pop(oldest_key, None)
            logger.warning(f"Memory cache evicted due to size limit: {oldest_key}")

        cls._cache[cache_key] = words_data
        cls._cache_time[cache_key] = datetime.now()
        logger.info(f"Sensitive words cached to memory ({len(words_data)} words)")

    @classmethod
    async def _load_sensitive_words(cls, db: AsyncSession) -> List[Dict]:
        """
        從 Redis 或資料庫載入敏感詞（協調器函數）

        優先順序：
        1. Redis 快取（如果可用）
        2. 內存快取（如果有效）
        3. 資料庫載入（快取失效時）

        Args:
            db: 資料庫 session

        Returns:
            敏感詞字典列表（已序列化，可安全緩存）
        """
        # 1. 嘗試從 Redis 讀取
        redis_result = await cls._try_load_from_redis()
        if redis_result is not None:
            return redis_result

        cache_key = "words"

        # 2. 嘗試內存快取（需要鎖保護）
        async with cls._get_lock():
            memory_result = cls._try_load_from_memory_cache(cache_key)
            if memory_result is not None:
                return memory_result

            # 3. 快取失效，從資料庫載入啟用的敏感詞
            result = await db.execute(
                select(SensitiveWord).where(SensitiveWord.is_active.is_(True))
            )
            words = result.scalars().all()

            # 序列化為字典（避免 SQLAlchemy DetachedInstanceError）
            words_data = [
                {
                    "id": str(w.id),
                    "word": w.word,
                    "category": w.category,
                    "severity": w.severity,
                    "action": w.action,
                    "is_regex": w.is_regex,
                    "description": w.description
                }
                for w in words
            ]

            # 4. 存入 Redis
            await cls._cache_to_redis(words_data)

            # 5. 存入內存快取
            cls._cache_to_memory(cache_key, words_data)

            return words_data

    @classmethod
    async def clear_cache(cls):
        """清除敏感詞快取（Redis + 內存）"""
        # 清除 Redis 快取
        if cls._redis and cls._use_redis:
            try:
                await cls._redis.delete(REDIS_KEY_SENSITIVE_WORDS)
                logger.info("Redis cache cleared for sensitive words")
            except aioredis.RedisError as e:
                logger.warning(f"Failed to clear Redis cache: {e}")

        # 清除內存快取
        async with cls._get_lock():
            cls._cache.clear()
            cls._cache_time.clear()
            logger.info("Memory cache cleared")

    @classmethod
    def _match_sensitive_word(
        cls,
        word_obj: Dict,
        content: str,
        content_lower: str
    ) -> bool:
        """匹配單個敏感詞

        Args:
            word_obj: 敏感詞字典
            content: 原始內容
            content_lower: 小寫內容

        Returns:
            是否匹配成功
        """
        if word_obj["is_regex"]:
            try:
                pattern = re.compile(word_obj["word"], re.IGNORECASE)
                return bool(pattern.search(content))
            except re.error:
                return False
        return word_obj["word"] in content_lower

    @classmethod
    def _check_sensitive_words(
        cls,
        sensitive_words: List[Dict],
        content: str,
        content_lower: str
    ) -> Tuple[List[str], List[uuid.UUID], Optional[str], str]:
        """檢查所有敏感詞

        Args:
            sensitive_words: 敏感詞列表
            content: 原始內容
            content_lower: 小寫內容

        Returns:
            (violations, triggered_word_ids, max_severity, action_to_take)
        """
        violations = []
        triggered_word_ids = []
        max_severity = None
        action_to_take = "APPROVED"
        severity_order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

        for word_obj in sensitive_words:
            if not cls._match_sensitive_word(word_obj, content, content_lower):
                continue

            violations.append(f"{word_obj['category']}: {word_obj['word']}")
            triggered_word_ids.append(uuid.UUID(word_obj["id"]))

            # 更新最高嚴重程度
            current_severity = severity_order.get(word_obj["severity"], 0)
            max_severity_value = (
                severity_order.get(max_severity, 0) if max_severity else 0
            )

            if current_severity > max_severity_value:
                max_severity = word_obj["severity"]
                action_to_take = word_obj["action"]

        return violations, triggered_word_ids, max_severity, action_to_take

    @classmethod
    def _check_suspicious_patterns(
        cls,
        content: str,
        current_violations: List[str],
        current_action: str
    ) -> Tuple[List[str], str]:
        """檢查可疑模式

        Args:
            content: 原始內容
            current_violations: 當前違規列表
            current_action: 當前動作

        Returns:
            (updated_violations, updated_action)
        """
        violations = current_violations.copy()
        action_to_take = current_action

        for pattern in cls.SUSPICIOUS_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                violations.append(f"包含可疑內容: {pattern}")
                if action_to_take == "APPROVED":
                    action_to_take = "WARN"

        return violations, action_to_take

    @staticmethod
    def _should_log_moderation(
        user_id: Optional[uuid.UUID],
        violations: List[str],
        is_approved: bool
    ) -> bool:
        """判斷是否需要記錄審核日誌

        Args:
            user_id: 用戶 ID
            violations: 違規列表
            is_approved: 是否通過

        Returns:
            是否需要記錄日誌
        """
        return bool(user_id and (violations or not is_approved))

    @classmethod
    async def check_content(
        cls,
        content: str,
        db: AsyncSession,
        user_id: Optional[uuid.UUID] = None,
        content_type: str = "TEXT"
    ) -> Tuple[bool, List[str], List[uuid.UUID], str]:
        """
        檢查內容是否包含敏感詞或不當內容（協調器函數）

        Args:
            content: 要檢查的內容
            db: 資料庫 session
            user_id: 用戶 ID（用於日誌記錄）
            content_type: 內容類型（MESSAGE, PROFILE, PHOTO）

        Returns:
            (is_approved, violations, triggered_word_ids, action):
            (是否通過, 違規項目列表, 觸發的敏感詞ID, 應採取的動作)
        """
        # 空內容直接通過
        if not content:
            return True, [], [], "APPROVED"

        content_lower = content.lower()

        # 1. 載入敏感詞
        sensitive_words = await cls._load_sensitive_words(db)

        # 2. 檢查敏感詞
        violations, triggered_word_ids, _, action_to_take = cls._check_sensitive_words(
            sensitive_words, content, content_lower
        )

        # 3. 檢查可疑模式
        violations, action_to_take = cls._check_suspicious_patterns(
            content, violations, action_to_take
        )

        # 4. 判斷是否通過
        is_approved = action_to_take in ["APPROVED", "WARN"]

        # 5. 記錄審核日誌
        if cls._should_log_moderation(user_id, violations, is_approved):
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
        記錄審核日誌（獨立事務，確保日誌永久保存）

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
        from app.core.database import AsyncSessionLocal

        # 使用獨立的資料庫 session 確保審核日誌永久保存
        # 即使主事務回滾，審核記錄也會保留（審計需求）
        async with AsyncSessionLocal() as log_db:
            try:
                log = ModerationLog(
                    user_id=user_id,
                    content_type=content_type,
                    original_content=content,
                    is_approved=is_approved,
                    violations=(
                        json.dumps(violations, ensure_ascii=False)
                        if violations else None
                    ),
                    triggered_word_ids=(
                        json.dumps([str(wid) for wid in triggered_word_ids])
                        if triggered_word_ids else None
                    ),
                    action_taken=action_taken
                )

                log_db.add(log)
                await log_db.commit()
            except Exception as e:
                # 日誌記錄失敗不應影響主流程
                logger.error(f"Failed to log moderation: {e}", exc_info=True)
                await log_db.rollback()

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
            if word_obj["is_regex"]:
                try:
                    pattern = re.compile(word_obj["word"], re.IGNORECASE)
                    sanitized = pattern.sub('***', sanitized)
                except re.error:
                    continue
            else:
                pattern = re.compile(re.escape(word_obj["word"]), re.IGNORECASE)
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
