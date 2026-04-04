# 🏗️ MergeMeet 架構文檔

## 📋 文檔目的

本文檔整合專案的核心架構設計、技術選型、開發策略與實作進度，作為開發團隊的技術參考指南。

---

## 1. 專案概述

### 1.1 專案定義

```yaml
專案名稱: MergeMeet
專案類型: Web-based Dating Platform (網頁版交友平台)
目標市場: 台灣（初期）
目標用戶: 18歲以上成年人
開發階段: MVP (Minimum Viable Product)
當前狀態: Week 1-6 已完成
```

### 1.2 專案目標

**主要目標：**
- 提供安全、有趣的線上交友體驗
- 透過興趣和地理位置幫助用戶找到合適對象
- 建立基於配對的即時聊天平台

**技術目標：**
- ✅ 建立可擴展的技術架構
- ✅ 達到 80% 以上測試覆蓋率（已達成）

---

## 2. 系統架構

### 2.1 整體架構圖

```
┌──────────────────────────────────────────────────────────┐
│                     用戶端 (Browser)                      │
│  ┌──────────────────────────────────────────────────┐    │
│  │           Vue.js 3 Frontend                      │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │    │
│  │  │  Views   │  │  Pinia   │  │  WebSocket   │    │    │
│  │  │Components│  │  Stores  │  │    Client    │    │    │
│  │  └──────────┘  └──────────┘  └──────────────┘    │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────┬───────────────────────────────────┘
                       │ HTTPS / WSS
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                       │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐    │
│  │  API Routes  │  │  Services   │  │  WebSocket   │    │
│  │              │  │             │  │   Manager    │    │
│  └──────┬───────┘  └──────┬──────┘  └──────┬───────┘    │
│         │                 │                │            │
│         └──────────┬──────┴────────────────┘            │
│                    ▼                                    │
│            ┌──────────────┐                             │
│            │  SQLAlchemy  │                             │
│            │   2.0 Async  │                             │
│            │     ORM      │                             │
│            └───────┬──────┘                             │
└────────────────────┼────────────────────────────────────┘
                     │
        ┌────────────┴─────────────┐
        ▼                          ▼
┌───────────────┐          ┌──────────────┐
│  PostgreSQL   │          │    Redis     │
│ 17 + PostGIS  │          │     8.x      │
│               │          │              │
│  - Users      │          │  - Cache     │
│  - Profiles   │          │  - Sessions  │
│  - Matches    │          │  - 登入限制   │
│  - Messages   │          │              │
│  - Reports    │          └──────────────┘
└───────────────┘
```

### 2.2 技術棧詳細說明

#### 後端技術棧

| 技術 | 版本 | 用途 | 狀態 |
|------|------|------|------|
| **Python** | 3.13+ | 主要開發語言 | ✅ |
| **FastAPI** | 0.135+ | Web 框架 | ✅ |
| **SQLAlchemy** | 2.0 | ORM（Async） | ✅ |
| **PostgreSQL** | 17 | 主資料庫 | ✅ |
| **PostGIS** | 3.5+ | 地理位置查詢 | ✅ |
| **Redis** | 8.x | 快取/Session/登入限制 | 🔄 部分使用 |
| **Pydantic** | 2.12+ | 資料驗證 | ✅ |
| **JWT** | PyJWT | 認證機制 | ✅ |
| **aiosmtplib** | 5.1+ | Email 發送服務 | ✅ |
| **Mailpit** | latest | Email 測試工具（開發） | ✅ |
| **Alembic** | 1.18+ | 資料庫遷移 | ✅ |
| **pytest** | 9.0+ | 測試框架 | ✅ |
| **Ruff** | 0.15+ | Linter + Formatter | ✅ |
| **pre-commit** | 4.0+ | Git Hook 管理 | ✅ |

#### 前端技術棧

| 技術 | 版本 | 用途 | 狀態 |
|------|------|------|------|
| **Vue.js** | 3.x | 前端框架 | ✅ |
| **Vite** | 8.x | 建構工具 | ✅ |
| **Pinia** | 3.x | 狀態管理 | ✅ |
| **Vue Router** | 5.x | 路由管理 | ✅ |
| **Axios** | 1.x | HTTP 客戶端 | ✅ |
| **WebSocket API** | 原生 | 即時通訊 | ✅ |
| **ESLint** | 10.x | Linter | ✅ |
| **Prettier** | 3.x | Formatter | ✅ |

### 2.3 資料庫架構

#### 資料模型關係圖

```
┌───────────────────────────┐
│           User            │  (用戶基本資料)
├───────────────────────────┤
│ id (PK)                   │
│ email                     │
│ password_hash             │
│ email_verified            │
│ date_of_birth             │
│ trust_score               │
│ warning_count             │
│ is_active                 │
│ is_admin                  │
│ ban_reason                │
│ banned_until              │
│ password_reset_token      │
│ password_reset_expires    │
│ created_at                │
│ updated_at                │
└─────────────┬─────────────┘
              │
              │ 1:1
              ▼
┌───────────────────────────┐
│          Profile          │  (個人檔案)
├───────────────────────────┤
│ id (PK)                   │
│ user_id (FK)              │
│ display_name              │  ← 顯示名稱
│ bio                       │
│ gender                    │
│ location (PostGIS Point)  │
│ location_name             │
│ min_age_preference        │
│ max_age_preference        │
│ max_distance_km           │
│ gender_preference         │
│ is_complete               │
│ is_visible                │
│ last_active               │
│ created_at                │
│ updated_at                │
└─────────────┬─────────────┘
              │
      ┌───────┴──────────────────────────────────┐
      │ 1:N(一對多)                               │ N:M (多對多)
      ▼                                          ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│          Photo          │     │       InterestTag       │  (興趣標籤)
│                         │     ├─────────────────────────┤
├─────────────────────────┤     │ id (PK)                 │
│ id (PK)                 │     │ name                    │
│ profile_id (FK)         │     │ category                │
│ url                     │     │ icon                    │
│ thumbnail_url           │     │ is_active               │
│ is_profile_picture      │     │ created_at              │
│ display_order           │     └─────────────────────────┘
│ file_size               │
│ width                   │
│ height                  │
│ mime_type               │
│ moderation_status       │  ← 審核狀態 (pending/approved/rejected)
│ rejection_reason        │
│ reviewed_by             │
│ reviewed_at             │
│ auto_moderation_score   │
│ auto_moderation_labels  │
│ created_at              │
└─────────────────────────┘


┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│      Like       │     │      Pass       │     │      Match      │  (配對記錄)
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (PK)         │     │ id (PK)         │     │ id (PK)         │
│ from_user_id    │     │ from_user_id    │     │ user1_id        │
│ to_user_id      │     │ to_user_id      │     │ user2_id        │
│ created_at      │     │ passed_at       │     │ status          │
└────────┬────────┘     └────────┬────────┘     │ matched_at      │
         │                       │              │ unmatched_at    │
         │                       │              │ unmatched_by    │
         ▼                       ▼              └────────┬────────┘
   永久不再出現           24小時內不出現                     │
   在探索頁              24小時後重新出現                    │
         │                       │                       │
         └───────────┬───────────┘                       │
                     │                                   │
                     └────── 互相喜歡時建立 Match ─────────┘
                                    │
                                    │ 1:N (一對多)
                                    ▼
                          ┌─────────────────────┐
                          │       Message       │  (聊天訊息)
                          ├─────────────────────┤
                          │ id (PK)             │
                          │ match_id (FK)       │
                          │ sender_id           │
                          │ content             │
                          │ message_type        │  (TEXT/IMAGE/GIF)
                          │ is_read (DateTime)  │  ← 讀取時間
                          │ deleted_at          │  (軟刪除)
                          │ sent_at             │
                          └─────────────────────┘


┌─────────────────────┐          ┌─────────────────────┐
│     BlockedUser     │          │        Report       │  (舉報記錄)
├─────────────────────┤          ├─────────────────────┤
│ id (PK)             │          │ id (PK)             │
│ blocker_id          │          │ reporter_id         │
│ blocked_id          │          │ reported_user_id    │
│ reason              │          │ report_type         │
│ created_at          │          │ reason              │
└─────────────────────┘          │ evidence            │
                                 │ status              │
                                 │ admin_notes         │  ← 管理員備註
                                 │ reviewed_by         │
                                 │ reviewed_at         │
                                 │ created_at          │
                                 │ updated_at          │
                                 └─────────────────────┘


┌─────────────────────┐
│     Notification    │  (通知記錄 - 持久化)
├─────────────────────┤
│ id (PK)             │  ← WebSocket 通知包含此 ID
│ user_id             │
│ type                │  (message/match/liked)
│ title               │
│ content             │
│ data (JSONB)        │
│ is_read             │  ← 前端透過 API 標記已讀
│ created_at          │
└─────────────────────┘

**WebSocket 通知 Payload**（所有類型都包含 `notification_id` 供前端標記已讀）:

| 類型                 | 欄位                                                    |
|----------------------|---------------------------------------------------------|
| notification_message | notification_id, match_id, sender_id, sender_name, preview, timestamp |
| notification_match   | notification_id, match_id, matched_user_id, matched_user_name, matched_user_avatar, timestamp |
| notification_liked   | notification_id, timestamp                              |


┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│    SensitiveWord    │   │    ContentAppeal    │   │    ModerationLog    │
├─────────────────────┤   ├─────────────────────┤   ├─────────────────────┤
│ id (PK)             │   │ id (PK)             │   │ id (PK)             │
│ word                │   │ user_id             │   │ user_id             │
│ category            │   │ appeal_type         │   │ content_type        │
│ severity            │   │ rejected_content    │   │ original_content    │
│ action              │   │ violations          │   │ is_approved         │
│ (WARN/REJECT/       │   │ reason              │   │ violations          │
│  AUTO_BAN)          │   │ status              │   │ triggered_word_ids  │
│ is_active           │   │ admin_response      │   │ action_taken        │
│ is_regex            │   │ reviewed_by         │   │ created_at          │
│ description         │   │ reviewed_at         │   └─────────────────────┘
│ created_by          │   │ created_at          │
│ created_at          │   │ updated_at          │
│ updated_at          │   └─────────────────────┘
└─────────────────────┘
```

### 2.4 PostGIS 地理位置查詢

#### 為什麼使用 PostGIS

MergeMeet 作為交友平台，**地理位置搜索是核心功能**：
- 用戶需要找到「附近的人」
- 配對算法需要計算用戶間的實際距離
- 距離是配對評分的重要因素（佔 20%）

**技術選型理由**：

| 方案 | 優點 | 缺點 | 結論 |
|------|------|------|------|
| **PostGIS** | 精確球面計算、原生 SQL 支援、高效空間索引 | 需要額外擴展 | ✅ 採用 |
| 應用層計算 | 簡單 | 效能差、無法利用索引 | ❌ |
| Elasticsearch Geo | 全文搜索整合 | 額外維護成本 | ❌ |

#### Docker 映像選擇

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgis/postgis:17-3.5
```

**版本說明**：
- **PostgreSQL 17**：2024-09 發布，效能優化、JSON_TABLE 支援
- **PostGIS 3.5**：2024 年發布，支援最新空間函數
- **官方映像**：由 PostGIS 團隊維護，預先安裝擴展

#### 資料類型選擇

```python
# backend/app/models/profile.py
from geoalchemy2 import Geography

class Profile(Base):
    # 使用 Geography 類型（而非 Geometry）
    location = Column(Geography(geometry_type='POINT', srid=4326))
```

**Geography vs Geometry**：

| 特性 | Geography | Geometry |
|------|-----------|----------|
| 座標系統 | 球面（地球表面） | 平面（笛卡爾） |
| 距離計算 | 公尺（精確） | 座標單位（需轉換） |
| 適用範圍 | 全球 | 小區域（城市級） |
| 效能 | 稍慢 | 較快 |
| **本專案選擇** | ✅ 採用 | - |

**選擇 Geography 的原因**：
- 交友平台用戶分布全台灣，需要精確的球面距離
- `ST_Distance` 直接返回公尺，無需額外轉換
- 未來擴展到其他國家時無需修改

#### 使用的 PostGIS 函數

| 函數 | 用途 | 使用位置 |
|------|------|----------|
| `ST_MakePoint(lng, lat)` | 從經緯度創建點 | 創建/更新個人檔案 |
| `ST_SetSRID(..., 4326)` | 設定座標系統 | 創建/更新個人檔案 |
| `ST_Distance(a, b, true)` | 計算球面距離（公尺） | 配對算法距離評分 |
| `ST_DWithin(a, b, dist, true)` | 範圍內篩選 | 探索功能距離過濾 |

**代碼範例**：

```python
# 1. 創建位置點（create_profile 函數）
from geoalchemy2.functions import ST_MakePoint, ST_SetSRID

profile.location = ST_SetSRID(
    ST_MakePoint(longitude, latitude),  # 注意：經度在前
    4326
)

# 2. 計算距離（get_discovery_candidates 函數）
from sqlalchemy import func

distance_km = (
    func.ST_Distance(
        Profile.location,
        my_profile.location,
        True  # use_spheroid=True
    ) / 1000
).label('distance_km')

# 3. 範圍篩選（get_discovery_candidates 函數）
from geoalchemy2.functions import ST_DWithin

ST_DWithin(
    Profile.location,
    my_profile.location,
    max_distance_km * 1000,  # 公里轉公尺
    True
)
```

#### 效能優化

- 使用 `ST_DWithin` 而非 `ST_Distance < X`（可利用 GIST 索引）
- 距離計算作為 SELECT 欄位，避免二次查詢
- `selectinload` 預載入關聯資料

#### ORM 整合（GeoAlchemy2）

```txt
# backend/requirements.txt
geoalchemy2==0.14.3
```

**GeoAlchemy2 功能**：
- SQLAlchemy 2.0 Async 支援
- 自動類型轉換（WKB ↔ Python）
- PostGIS 函數映射（`ST_*` → Python 函數）

#### 測試配置

```python
# backend/tests/conftest.py
async with engine.begin() as conn:
    # 測試資料庫需要啟用 PostGIS 擴展
    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
```

#### 常見問題排除

**錯誤 1**：`function st_distance does not exist`
```bash
# 解決方案：啟用 PostGIS 擴展
docker exec mergemeet_postgres psql -U mergemeet -d mergemeet \
  -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

**錯誤 2**：距離計算結果為 `None`
```python
# 原因：用戶未設定位置
# 解決：檢查 location 是否為空
if profile.location is None:
    distance_km = None
```

#### 相關文件

| 文件 | 說明 |
|------|------|
| `backend/app/models/profile.py` | Profile 模型定義（location 欄位） |
| `backend/app/api/profile.py` | 位置設定 API |
| `backend/app/api/discovery.py` | 距離搜索邏輯 |
| `docs/MATCHING_ALGORITHM.md` | 配對算法（距離評分） |

---

## 3. 功能與路線圖

> 功能清單和開發路線圖已獨立維護，避免重複：

| 文檔 | 說明 |
|------|------|
| **[FEATURES.md](FEATURES.md)** | 已完成功能清單（Week 1-6 詳細說明） |
| **[ROADMAP.md](ROADMAP.md)** | 技術路線圖（未來開發規劃） |

---

## 4. 開發策略

> 詳見 **Skill: mergemeet-quickstart** 的 [workflows.md](../.claude/skills/mergemeet-quickstart/references/workflows.md)

包含：
- Git 工作流程與分支策略
- Conventional Commits 規範
- TDD 測試流程（覆蓋率 >80%）
- CI/CD 與發布流程

程式碼規範詳見 Skills：**[backend-dev-fastapi](../.claude/skills/backend-dev-fastapi/SKILL.md)**、**[frontend-dev-vue3](../.claude/skills/frontend-dev-vue3/SKILL.md)**

---

## 5. API 端點

> 完整 API 文檔請參閱：http://localhost:8000/docs

---

## 6. 前端架構

| 目錄 | 說明 |
|------|------|
| `src/views/` | 頁面組件 |
| `src/components/` | 共用組件 |
| `src/stores/` | Pinia 狀態管理 |
| `src/composables/` | Vue Composables |
| `src/api/` | API 客戶端 |
| `src/router/` | 路由配置 |

---

## 7. 測試架構

### 7.1 測試概況

| 項目 | 說明 |
|------|------|
| 測試檔案位置 | `backend/tests/` |
| 測試案例數 | 詳見 `pytest --collect-only` |
| 覆蓋率目標 | >80% |
| 測試框架 | pytest + pytest-asyncio |

> 最新測試統計請參考 [README.md](../README.md#-測試) 或執行 `pytest -v --cov=app`

### 7.2 測試工具

```python
# pytest 配置
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"

# 測試命令
pytest -v                    # 詳細輸出
pytest --cov=app            # 測試覆蓋率
pytest tests/test_safety.py # 特定檔案
pytest -m unit              # 特定標記
```

---

## 8. 安全措施

> 詳細安全策略請參考 **[SECURITY.md](SECURITY.md)**

**已實作的安全機制：**
- HttpOnly Cookie + CSRF 防護
- JWT 認證（Access + Refresh Token）
- 密碼雜湊（bcrypt + SHA256 預處理）
- SQL 注入防護（SQLAlchemy ORM）
- XSS 防護（輸入驗證 + 輸出編碼）
- WebSocket Token 驗證 + 異常連接清理
- 登入失敗限制（Redis，5 次/15 分鐘）
- 信任分數系統（自動行為監控）
- 內容審核系統（敏感詞過濾）

---

## 9. 關鍵決策記錄

### 9.1 技術選型

**選擇 FastAPI（而非 Django）：**
- ✅ 原生支援 Async/Await
- ✅ 自動生成 API 文檔
- ✅ 優秀的效能表現
- ✅ 現代化的開發體驗

**選擇 Vue 3（而非 React）：**
- ✅ Composition API 更直覺
- ✅ 輕量級框架
- ✅ 優秀的中文文檔
- ✅ 學習曲線較平緩

**選擇 PostgreSQL + PostGIS：**
- ✅ 強大的地理位置查詢
- ✅ JSONB 支援
- ✅ 完善的關聯式資料庫
- ✅ 免費開源

### 9.2 架構決策

**採用前後端分離：**
- ✅ 前後端獨立開發
- ✅ 更好的可擴展性
- ✅ 支援多端（Web、Mobile）

**使用 WebSocket（而非長輪詢）：**
- ✅ 真正的即時通訊
- ✅ 減少伺服器負載
- ✅ 更好的用戶體驗

**TDD 開發方式：**
- ✅ 提高程式碼品質
- ✅ 重構更安全
- ✅ 文檔化測試案例

---

**文檔版本：** 2.8.0
**最後更新：** 2025-12-26
**維護者：** MergeMeet Development Team

---

**Happy Coding!**
