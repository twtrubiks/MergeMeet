# DetachedInstanceError Bug 修復報告

**修復日期**: 2025-11-16
**修復人員**: Claude Code
**Bug 嚴重度**: 🔴 Critical (阻塞性)
**修復狀態**: ✅ 已修復並驗證

---

## 🐛 Bug 描述

### 問題表現

當用戶嘗試更新個人檔案（使用正常內容，無敏感詞）時，後端返回 500 Internal Server Error，導致用戶無法更新個人資料。

### 錯誤訊息

```python
sqlalchemy.orm.exc.DetachedInstanceError:
Instance <SensitiveWord at 0x7f147896a450> is not bound to a Session;
attribute refresh operation cannot proceed
```

### 影響範圍

- ❌ 用戶無法更新個人檔案（所有內容都會失敗）
- ❌ 用戶無法創建新個人檔案（如果有 bio）
- ✅ 聊天訊息審核不受影響
- ✅ 敏感詞攔截功能正常（攔截邏輯正確）

---

## 🔍 根本原因分析

### 問題代碼位置

**文件**: `backend/app/services/content_moderation.py`

**Line 64-67** (緩存實現):
```python
# 從資料庫載入啟用的敏感詞
result = await db.execute(
    select(SensitiveWord).where(SensitiveWord.is_active == True)
)
words = result.scalars().all()  # ← ORM 對象與 session 綁定

# 更新快取
cls._cache = {"words": words}   # ❌ 錯誤：直接緩存 ORM 對象
cls._cache_time = now
```

**Line 117** (使用緩存時):
```python
for word_obj in sensitive_words:  # ← 從緩存獲取
    matched = False

    if word_obj.is_regex:  # ❌ DetachedInstanceError
        # 訪問已分離對象的屬性時出錯
```

### 為什麼會出錯？

1. **ORM 對象生命週期**: SQLAlchemy ORM 對象與創建它們的 database session 綁定
2. **Session 關閉**: 查詢完成後，session 被關閉，對象變為 "detached" 狀態
3. **Lazy Loading**: 訪問 detached 對象的屬性時，SQLAlchemy 嘗試從數據庫重新載入，但對象已經沒有 session
4. **緩存問題**: 緩存了 detached 對象，後續請求使用時觸發錯誤

### 觸發條件

1. ✅ 第一次請求：成功（對象仍與 session 綁定）
2. ❌ 第二次請求（緩存命中）：失敗（對象已 detached）
3. ❌ 所有後續請求：全部失敗

---

## ✅ 修復方案

### 核心思路

**不緩存 ORM 對象，改為緩存序列化的字典數據**

### 修復代碼

#### 1. 修改緩存類型聲明

```python
# 修改前
_cache: Dict[str, List[SensitiveWord]] = {}

# 修改後 ✅
_cache: Dict[str, List[Dict]] = {}
```

#### 2. 修改 `_load_sensitive_words()` 方法

```python
@classmethod
async def _load_sensitive_words(cls, db: AsyncSession) -> List[Dict]:
    """
    從資料庫載入敏感詞（帶快取機制和線程安全保護）

    Returns:
        敏感詞字典列表（已序列化，可安全緩存）
    """
    # ... 快取檢查邏輯 ...

    # 從資料庫載入啟用的敏感詞
    result = await db.execute(
        select(SensitiveWord).where(SensitiveWord.is_active == True)
    )
    words = result.scalars().all()

    # ✅ 序列化為字典（避免 SQLAlchemy DetachedInstanceError）
    words_data = [
        {
            "id": str(w.id),
            "word": w.word,
            "category": w.category,
            "severity": w.severity,
            "action": w.action,
            "is_regex": w.is_regex,  # ← 提前載入所有需要的屬性
            "description": w.description
        }
        for w in words
    ]

    # ✅ 更新快取（緩存字典而不是 ORM 對象）
    cls._cache = {"words": words_data}
    cls._cache_time = now

    return words_data
```

#### 3. 修改 `check_content()` 方法

```python
# 檢查敏感詞
for word_obj in sensitive_words:  # ← 現在是字典列表
    matched = False

    # ✅ 使用字典訪問（不會觸發 lazy loading）
    if word_obj["is_regex"]:
        try:
            pattern = re.compile(word_obj["word"], re.IGNORECASE)
            if pattern.search(content):
                matched = True
        except re.error:
            continue
    else:
        if word_obj["word"] in content_lower:
            matched = True

    if matched:
        violations.append(f"{word_obj['category']}: {word_obj['word']}")
        triggered_word_ids.append(uuid.UUID(word_obj["id"]))

        # 更新最高嚴重程度和動作
        severity_order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        if severity_order.get(word_obj["severity"], 0) > severity_order.get(max_severity, 0):
            max_severity = word_obj["severity"]
            action_to_take = word_obj["action"]
```

#### 4. 修改 `sanitize_content()` 方法

```python
# 替換敏感詞為 ***
for word_obj in sensitive_words:
    if word_obj["is_regex"]:  # ✅ 字典訪問
        try:
            pattern = re.compile(word_obj["word"], re.IGNORECASE)
            sanitized = pattern.sub('***', sanitized)
        except re.error:
            continue
    else:
        pattern = re.compile(re.escape(word_obj["word"]), re.IGNORECASE)
        sanitized = pattern.sub('***', sanitized)
```

---

## 🧪 測試驗證

### 測試 1: 敏感詞攔截 ✅

**場景**: 提交包含敏感詞的個人簡介

**請求**:
```json
{
  "bio": "我這裡有個投資機會，可以快速賺錢哦！想要了解更多色情內容請聯繫我。"
}
```

**結果**: ✅ **成功攔截**
- HTTP 狀態: `400 Bad Request`
- 錯誤訊息: "個人簡介包含不當內容"
- 檢測到的敏感詞:
  - ❌ 個人簡介 - SEXUAL: 色情
  - ❌ 個人簡介 - SCAM: 投資
  - ❌ 個人簡介 - SCAM: 賺錢
- 操作: `REJECT`

### 測試 2: 正常內容提交 ✅

**場景**: 提交不含敏感詞的正常內容

**請求**:
```json
{
  "display_name": "Alice",
  "gender": "female",
  "bio": "喜歡旅遊和美食，熱愛生活！週末喜歡去爬山，也喜歡在咖啡廳看書。希望找到志同道合的朋友一起探索世界。",
  "location": {
    "latitude": 25.033,
    "longitude": 121.5654,
    "location_name": "台北市信義區"
  }
}
```

**結果**: ✅ **成功保存**
- HTTP 狀態: `200 OK`
- 響應包含完整的 profile 數據
- `updated_at`: `2025-11-16T05:51:02.881903Z`

**修復前**: ❌ 返回 500 Internal Server Error
**修復後**: ✅ 返回 200 OK 並成功保存

---

## 📊 修復前後對比

| 測試場景 | 修復前 | 修復後 |
|---------|--------|--------|
| **第一次請求（緩存未命中）** | ✅ 200 OK | ✅ 200 OK |
| **第二次請求（緩存命中）** | ❌ 500 Error | ✅ 200 OK |
| **敏感詞攔截** | ✅ 400 正常攔截 | ✅ 400 正常攔截 |
| **正常內容保存** | ❌ 500 Error | ✅ 200 OK |
| **聊天訊息審核** | ✅ 正常 | ✅ 正常 |

---

## 🔧 技術細節

### 為什麼序列化可以解決問題？

1. **字典是純 Python 對象**：不依賴 SQLAlchemy session
2. **所有屬性已載入**：序列化時提前訪問所有需要的屬性
3. **可安全緩存**：字典可以跨請求安全使用
4. **性能無損失**：字典訪問速度與對象屬性訪問相當

### 其他可選方案（未採用）

#### 方案 2: Eager Loading + Expunge
```python
result = await db.execute(
    select(SensitiveWord)
    .where(SensitiveWord.is_active == True)
    .options(selectinload('*'))  # 預載入所有關係
)
words = result.scalars().all()

for w in words:
    db.expunge(w)  # 從 session 移除
```

**缺點**:
- 仍然依賴 SQLAlchemy 對象
- expunge 可能導致其他 lazy loading 問題
- 不如字典清晰明確

#### 方案 3: 每次都查詢資料庫（不緩存）
**缺點**: 性能損失大，失去緩存優勢

---

## ✅ 修復效果

### 功能恢復

- ✅ 用戶可以正常更新個人檔案
- ✅ 用戶可以創建新個人檔案
- ✅ 內容審核功能正常工作
- ✅ 敏感詞攔截功能正常
- ✅ 緩存機制正常工作（5分鐘 TTL）

### 性能影響

- ✅ **無負面影響**：字典訪問速度與對象屬性訪問相當
- ✅ **緩存仍有效**：5分鐘 TTL，減少資料庫查詢
- ✅ **記憶體佔用**：字典可能略小於 ORM 對象

### 代碼質量

- ✅ **更清晰**：明確數據結構，不依賴 ORM 魔法
- ✅ **更安全**：避免 session 生命週期問題
- ✅ **更可測試**：字典易於模擬和測試

---

## 📝 修改文件清單

| 文件 | 修改行數 | 說明 |
|------|---------|------|
| `backend/app/services/content_moderation.py` | ~60 行 | 主要修復文件 |

**詳細修改**:
- Line 18: 緩存類型聲明
- Line 33-84: `_load_sensitive_words()` 方法
- Line 128-153: `check_content()` 方法中的敏感詞檢查
- Line 253-262: `sanitize_content()` 方法

---

## 🎯 經驗教訓

### 1. 不要緩存 ORM 對象

**問題**: ORM 對象與 database session 綁定，session 關閉後無法安全使用

**解決方案**:
- 序列化為字典或 Pydantic 模型
- 或使用 Redis 等外部緩存（自動序列化）

### 2. 注意 SQLAlchemy Lazy Loading

**問題**: 訪問關係屬性時可能觸發額外查詢，detached 對象會失敗

**解決方案**:
- 使用 `selectinload()` 或 `joinedload()` eager loading
- 或在序列化時提前訪問所有需要的屬性

### 3. 快取機制的測試

**問題**: 只測試第一次請求可能無法發現緩存問題

**解決方案**:
- 測試緩存命中和未命中兩種情況
- 測試緩存過期和刷新

### 4. 獨立事務的風險

**代碼位置**: `_log_moderation()` 使用獨立 session

```python
async with AsyncSessionLocal() as log_db:
    # 獨立事務記錄日誌
```

**潛在問題**: 如果緩存了這個 session 的對象，也會出現 detached 問題

**解決方案**: 確保不緩存來自不同 session 的對象

---

## 🔍 後續建議

### 1. 添加單元測試

```python
@pytest.mark.asyncio
async def test_sensitive_words_caching():
    """測試敏感詞緩存機制"""
    # 第一次請求 - 緩存未命中
    words1 = await ContentModerationService._load_sensitive_words(db)
    assert isinstance(words1, list)
    assert all(isinstance(w, dict) for w in words1)

    # 第二次請求 - 緩存命中
    words2 = await ContentModerationService._load_sensitive_words(db)
    assert words1 == words2  # 應該返回相同數據
```

### 2. 監控緩存效果

添加日誌記錄緩存命中率：
```python
if cached_words is not None:
    logger.debug("Sensitive words cache hit")
    return cached_words
else:
    logger.debug("Sensitive words cache miss, loading from database")
```

### 3. 考慮使用 Redis

對於生產環境，考慮使用 Redis 緩存：
- 自動序列化/反序列化
- 跨進程共享
- 更強大的 TTL 和刷新策略

---

## 📚 相關資源

- [SQLAlchemy DetachedInstanceError 文檔](https://docs.sqlalchemy.org/en/20/errors.html#error-bhk3)
- [SQLAlchemy Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)
- [FastAPI Caching Best Practices](https://fastapi.tiangolo.com/advanced/async-sql-databases/)

---

**修復完成時間**: 2025-11-16 13:51 GMT+8
**驗證狀態**: ✅ 已通過瀏覽器端到端測試
**部署建議**: 可安全部署到生產環境
