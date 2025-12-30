# 信任分數系統（Trust Score System）

## 📋 系統概述

信任分數系統是 MergeMeet 平台的信譽管理機制，透過自動追蹤用戶行為來維護平台健康度與安全性。

### 核心目標

1. **獎勵正向行為** - 鼓勵用戶完成驗證、積極互動
2. **懲罰負向行為** - 遏制違規、騷擾、詐騙等不當行為
3. **優化配對品質** - 優先推薦高信任度用戶
4. **自動功能限制** - 限制低信任用戶的破壞行為

---

## 🎯 分數系統設計

### 分數範圍

| 分數範圍 | 狀態 | 說明 |
|----------|------|------|
| 70-100 | 高度信任 | 配對排序優先，無限制 |
| 50-69 | 正常 | 新用戶預設值，正常使用 |
| 30-49 | 需關注 | 配對排序略降，建議改善行為 |
| 20-29 | 受限 | 配對排序大幅降低，每日訊息上限 20 則 |
| 0-19 | 高度可疑 | 配對不推薦，嚴格訊息限制 |

**預設分數**: 50（新用戶註冊時）

---

## 📊 分數調整規則

### 正向行為（加分）

| 行為 | 分數變化 | 觸發條件 | 實作位置 |
|------|----------|----------|----------|
| Email 驗證完成 | **+5** | 首次驗證 Email 成功 | `auth.py` verify_email |
| 被喜歡 | **+1** | 其他用戶喜歡你 | `discovery.py` like_user |
| 配對成功 | **+2** | 雙方互相喜歡 | `discovery.py` like_user |
| 正向互動 | **+1** | 用戶輪流發送訊息時雙方各獲得（上一發送者≠當前發送者才算回應，每配對每日三次，每人每日上限 +3） | `websocket.py` handle_chat_message |

### 負向行為（扣分）

| 行為 | 分數變化 | 觸發條件 | 實作位置 |
|------|----------|----------|----------|
| 被舉報 | **-5** | 其他用戶舉報你 | `safety.py` report_user |
| 舉報被確認 | **-10** | 管理員確認舉報成立 | `admin.py` review_report |
| 發送違規內容 | **-3** | 訊息包含敏感詞/可疑模式 | `websocket.py` handle_chat_message |
| 被封鎖 | **-2** | 其他用戶封鎖你 | `safety.py` block_user |

---

## 🔧 技術實作

### 服務層設計

**檔案位置**: `backend/app/services/trust_score.py`

#### 核心方法

```python
class TrustScoreService:
    # 常數定義
    MIN_SCORE = 0
    MAX_SCORE = 100
    DEFAULT_SCORE = 50
    RESTRICTION_THRESHOLD = 20
    LOW_TRUST_MESSAGE_LIMIT = 20

    # 主要方法
    async def adjust_score(db, user_id, action, reason=None) -> int
    async def get_score(db, user_id) -> int
    async def is_restricted(db, user_id) -> bool
    async def check_message_rate_limit(user_id, trust_score, redis) -> (bool, int)
    async def record_message_sent(user_id, redis) -> int
```

### 調用範例

```python
# Email 驗證加分
await TrustScoreService.adjust_score(db, user.id, "email_verified")

# 被舉報扣分
await TrustScoreService.adjust_score(db, reported_user_id, "reported")

# 檢查訊息限制
can_send, remaining = await TrustScoreService.check_message_rate_limit(
    user_id, trust_score, redis
)
```

---

## 🎲 配對算法整合

### 權重分配（總分 100）

| 維度 | 權重 | 說明 |
|------|------|------|
| 興趣匹配 | 50 分 | 每個共同興趣 10 分 |
| 距離 | 20 分 | 越近分數越高 |
| 活躍度 | 20 分 | 最近活躍分數越高 |
| 完整度 | 5 分 | 照片數量 + 自我介紹 |
| **信任分數** | **5 分** | **新增維度** |

### 信任分數映射

```python
trust_score >= 70  →  5.0 分（高度信任）
trust_score >= 50  →  4.0 分（正常）
trust_score >= 30  →  2.5 分（需關注）
trust_score >= 20  →  1.0 分（受限）
trust_score < 20   →  0.0 分（高度可疑）
```

**實作位置**: `backend/app/services/matching_service.py` `_calculate_trust_score_weight()`

---

## 🚫 功能限制機制

### 訊息發送限制

**觸發條件**: `trust_score < 20`

**限制內容**:
- 每日訊息上限：20 則
- 計數重置：每日午夜（UTC）
- 超過限制：拒絕發送並回傳錯誤

**Redis Key 設計**:
```
trust:daily_messages:{user_id}:{YYYY-MM-DD}
TTL: 86400 秒（24 小時）
```

**正向互動配對計數**:
```
trust:positive_interaction:{match_id}:{YYYY-MM-DD}
TTL: 86400 秒（24 小時）
值: 整數 1-N（使用 INCR 原子遞增，≤3 時給予獎勵）
```

**實作位置**: `backend/app/api/websocket.py` `handle_chat_message()`

### 檢查流程

```python
1. 用戶發送訊息
   ↓
2. 檢查 trust_score
   ↓
3. 若 < 20，查詢 Redis 計數
   ↓
4. 若超過 20 則，拒絕發送
   ↓
5. 若未超過，增加計數並允許發送
```

---

## 🧪 測試覆蓋

### 測試檔案

**位置**: `backend/tests/test_trust_score.py`

### 測試分類

| 類別 | 用途 |
|------|------|
| `TestTrustScoreAdjustments` | 各種行為的分數調整 |
| `TestScoreBoundaries` | 分數邊界處理 |
| `TestGetScore` | 分數查詢 |
| `TestRestrictions` | 功能限制判斷 |
| `TestMessageRateLimiting` | 訊息速率限制 |
| `TestMultipleAdjustments` | 累積調整 |
| `TestPositiveInteractionMatchLimit` | 正向互動配對限制（位於 test_websocket.py） |

### 測試執行

```bash
# 查看完整測試清單
pytest tests/test_trust_score.py --collect-only -q

# 執行所有信任分數測試
pytest tests/test_trust_score.py -v
```

### 整合測試

驗證各 API 端點觸發分數調整：

```bash
# Email 驗證測試
pytest tests/test_auth.py::test_verify_email_success -v

# 配對測試
pytest tests/test_discovery.py::test_mutual_like_creates_match -v

# 舉報測試
pytest tests/test_safety.py::test_report_user_success -v
```

---

## 🔄 工作流程範例

### 場景 1：正常用戶成長路徑

```
新用戶註冊
├─ 初始分數: 50
├─ Email 驗證: +5 → 55
├─ 被 3 人喜歡: +3 → 58
├─ 配對成功 2 次: +4 → 62
├─ 正向互動 3 次（每日上限）: +3 → 65
└─ 最終分數: 65（正常用戶）
```

### 場景 2：違規用戶降級路徑

```
正常用戶
├─ 初始分數: 50
├─ 發送違規內容: -3 → 47
├─ 被舉報 2 次: -10 → 37
├─ 舉報被確認: -10 → 27
└─ 最終分數: 27（需關注）
```

### 場景 3：嚴重違規用戶

```
問題用戶
├─ 初始分數: 50
├─ 被舉報 3 次: -15 → 35
├─ 舉報確認 2 次: -20 → 15
├─ 被封鎖 3 次: -6 → 9
└─ 最終分數: 9（受限模式）
    ├─ 配對排序極低
    ├─ 每日訊息上限 20 則
    └─ 建議管理員審查
```

---

## 🛡️ 安全考量

### 1. 並發安全

所有分數調整使用資料庫事務保證原子性：

```python
async def adjust_score(...):
    # 查詢用戶
    user = await db.execute(select(User).where(User.id == user_id))

    # 計算新分數
    new_score = user.trust_score + adjustment

    # 更新分數（事務保證）
    user.trust_score = new_score
    await db.commit()  # 原子操作
```

### 2. 分數邊界保護

```python
# 確保分數在 0-100 範圍內
new_score = max(MIN_SCORE, min(MAX_SCORE, new_score))
```

### 3. Redis 快取失敗回退

訊息限制功能在 Redis 異常時自動回退，不影響正常用戶：

```python
try:
    # Redis 操作
    ...
except Exception:
    # 異常時允許發送（不阻擋用戶）
    return True, None
```

### 4. 配對獎勵原子計數

使用 Redis INCR 原子操作確保併發安全：

```python
# 原子遞增，返回新值（若 key 不存在，初始化為 0 再加 1）
match_count = await redis.incr(match_reward_key)
if match_count == 1:
    await redis.expire(match_reward_key, 86400)  # 設定 TTL
if match_count > 3:
    return  # 超過每配對每日上限，不獎勵
```

**原子性保證**：
- 即使多個請求同時到達，INCR 保證每個請求獲得唯一的遞增值
- 避免 check-then-set 競態條件（舊實作使用 `exists()` + `setex()` 有此問題）

---

## 🔮 未來擴展

詳見 **[ROADMAP.md](ROADMAP.md#信任分數系統增強)**

---

## 🧮 配對排序影響範例

### 範例候選人比較

**用戶 A** (高信任度)
```
興趣匹配: 30 分（3 個共同興趣）
距離: 15 分（8 km）
活躍度: 20 分（30 分鐘前）
完整度: 5 分（6 張照片 + 自介）
信任分數: 5 分（trust_score = 75）
─────────────────────────
總分: 75 分
```

**用戶 B** (低信任度)
```
興趣匹配: 30 分（3 個共同興趣）
距離: 15 分（8 km）
活躍度: 20 分（30 分鐘前）
完整度: 5 分（6 張照片 + 自介）
信任分數: 0 分（trust_score = 15）
─────────────────────────
總分: 70 分
```

**結果**: 用戶 A 排序優先於用戶 B（即使其他條件相同）

---

## 🐛 已知限制

1. **無自動恢復機制**
   - 沒有隨時間自動恢復機制
   - 用戶需透過正向行為（被喜歡、配對成功）手動提升

2. **無歷史記錄**
   - 不記錄分數變化歷史
   - 無法追蹤具體扣分原因

3. **單一閾值**
   - 僅有一個限制閾值（20 分）
   - 未來可考慮多級限制
