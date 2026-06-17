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
| 舉報被確認 | **-10** | 管理員確認舉報成立 | `admin.py` review_report |
| 發送違規內容 | **-3** | 訊息包含敏感詞/可疑模式 | `websocket.py` handle_chat_message |
| 被封鎖 | **-2** | 其他用戶封鎖你 | `safety.py` block_user |

### 恢復行為（加分，上限為預設分 50）

| 行為 | 分數變化 | 觸發條件 | 實作位置 |
|------|----------|----------|----------|
| 舉報被駁回 | **+5** | 管理員駁回舉報（每筆舉報僅補償一次） | `admin.py` review_report |
| 每日自動恢復 | **+1** | 低於 50 分的活躍用戶，每日批次執行 | `trust_score_recovery.py` |

> 恢復行為（`RECOVERY_ACTIONS`）以預設分 50 為上限且不降低現有分數：
> 被誤報用戶可逐步翻身，真正違規者無法靠時間恢復高信任狀態。

---

## 🔄 自動恢復機制

低信任分數會降低配對排序權重，導致被推薦機率減少，形成「被誤報 → 沒有互動 → 無法加分」的惡性循環。自動恢復機制提供兩條出路：

### 1. 每日衰減恢復

- **規則**: `trust_score < 50` 的用戶每日 +1，封頂於 50
- **排除**: 軟刪除（`deleted_at`）與停權（`is_active = False`）用戶
- **執行方式**: lifespan 背景任務每小時檢查，以 Redis 日期鎖（`trust:daily_recovery:{YYYY-MM-DD}`，SET NX，TTL 48h）確保每日只執行一次（應用重啟不重複加分；執行失敗時釋放鎖讓下一輪重試）
- **審計**: 每筆恢復寫入 `trust_score_logs`（action = `daily_recovery`）
- **恢復速度**: 舉報成立一次（-10）約需 10 天自然恢復，違規成本仍然顯著

### 2. 舉報駁回補償

- **規則**: 管理員駁回舉報（REJECTED）時，被舉報用戶 +5（上限 50）
- **防重複**: 僅在舉報「首次轉為 REJECTED」時發放，重複審核不重複加分
- **審計**: 寫入 `trust_score_logs`（action = `report_rejected`，reason 含舉報 ID）

**實作位置**:
- 服務: `backend/app/services/trust_score_recovery.py`
- 駁回補償: `backend/app/api/admin.py` `review_report()`
- 測試: `backend/tests/test_trust_score_recovery.py`

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

# 舉報確認扣分（管理員審核通過後才執行，reason 寫入審計日誌）
await TrustScoreService.adjust_score(
    db, reported_user_id, "report_confirmed", reason=f"舉報 {report.id} 成立"
)

# 檢查訊息限制
can_send, remaining = await TrustScoreService.check_message_rate_limit(
    user_id, trust_score, redis
)
```

---

## 📜 審計日誌（trust_score_logs）

每次 `adjust_score` 都會在**同一交易**中寫入一筆變更日誌，供用戶對扣分提出爭議時追溯原因與時間點。

### 表結構

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | UUID | 主鍵 |
| user_id | UUID | 用戶 ID（FK，CASCADE 刪除） |
| action | String(50) | 行為類型（ADJUSTMENTS 的 key） |
| adjustment | Integer | 名目調整值（實際變化受 0-100 邊界影響，以 new_score 為準） |
| new_score | Integer | 調整後的實際分數 |
| reason | Text | 調整原因（可選，如舉報 ID） |
| created_at | timestamptz | 變更時間 |

複合索引 `(user_id, created_at)` 支援依用戶查詢歷史。

### 管理員查詢端點

```
GET /api/admin/users/{user_id}/trust-logs?limit=50
```

回傳該用戶的變更歷史（最新在前，limit 1-200，預設 50），需管理員權限。

**實作位置**:
- Model: `backend/app/models/trust_score_log.py`
- Migration: `backend/alembic/versions/011_add_trust_score_logs.py`
- 端點: `backend/app/api/admin.py` `get_user_trust_logs()`
- 測試: `backend/tests/test_trust_score_log.py`

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
| `TestAdjustScoreWritesLog` | 審計日誌寫入（位於 test_trust_score_log.py） |
| `TestTrustLogsEndpoint` | 管理員日誌查詢端點（位於 test_trust_score_log.py） |
| `TestDailyRecovery` 等 | 每日衰減恢復與舉報駁回補償（位於 test_trust_score_recovery.py） |

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
├─ 舉報確認 2 次: -20 → 27
└─ 最終分數: 27（需關注）
```

### 場景 3：嚴重違規用戶

```
問題用戶
├─ 初始分數: 50
├─ 舉報確認 3 次: -30 → 20
├─ 被封鎖 3 次: -6 → 14
└─ 最終分數: 14（受限模式）
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

1. **單一閾值**
   - 僅有一個限制閾值（20 分）
   - 未來可考慮多級限制
