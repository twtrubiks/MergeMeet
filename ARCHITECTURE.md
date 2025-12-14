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
代碼規模: 約 18,700 行（後端 6,752 行 + 前端 11,687 行 + 測試 4,029 行）
上線準備度: 82%
最後審查: 2025-12-09
```

### 1.2 專案目標

**主要目標：**
- 提供安全、有趣的線上交友體驗
- 透過興趣和地理位置幫助用戶找到合適對象
- 建立基於配對的即時聊天平台

**技術目標：**
- ✅ 建立可擴展的技術架構
- ✅ 達到 80% 以上測試覆蓋率（已達成）
- ✅ API 回應時間 < 200ms (p95)

---

## 2. 系統架構

### 2.1 整體架構圖

```
┌─────────────────────────────────────────────────────────┐
│                     用戶端 (Browser)                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │           Vue.js 3 Frontend                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │   │
│  │  │  Views   │  │  Pinia   │  │  WebSocket   │  │   │
│  │  │Components│  │  Stores  │  │    Client    │  │   │
│  │  │  (13個)  │  │  (7個)   │  │ (Composable) │  │   │
│  │  └──────────┘  └──────────┘  └──────────────┘  │   │
│  └─────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS / WSS
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │  API Routes  │  │  Services   │  │  WebSocket   │  │
│  │   (9個模組)   │  │(內容審核)   │  │   Manager    │  │
│  └──────┬───────┘  └──────┬──────┘  └──────┬───────┘  │
│         │                  │                 │          │
│         └──────────┬───────┴─────────────────┘          │
│                    ▼                                     │
│            ┌──────────────┐                             │
│            │  SQLAlchemy  │                             │
│            │   2.0 Async  │                             │
│            │     ORM      │                             │
│            └──────┬───────┘                             │
└────────────────────┼──────────────────────────────────┘
                     │
        ┌────────────┴─────────────┐
        ▼                          ▼
┌───────────────┐          ┌──────────────┐
│  PostgreSQL   │          │    Redis     │
│   16 + PostGIS│          │      7.x     │
│               │          │              │
│  - Users      │          │  - Cache     │
│  - Profiles   │          │  - Sessions  │
│  - Matches    │          │  (未來擴充)  │
│  - Messages   │          │              │
│  - Reports    │          └──────────────┘
└───────────────┘
```

### 2.2 技術棧詳細說明

#### 後端技術棧

| 技術 | 版本 | 用途 | 狀態 |
|------|------|------|------|
| **Python** | 3.11+ | 主要開發語言 | ✅ |
| **FastAPI** | 0.109+ | Web 框架 | ✅ |
| **SQLAlchemy** | 2.0 | ORM（Async） | ✅ |
| **PostgreSQL** | 16 | 主資料庫 | ✅ |
| **PostGIS** | 3.4+ | 地理位置查詢 | ✅ |
| **Redis** | 7.x | 快取/Session/登入限制 | 🔄 部分使用 |
| **Pydantic** | 2.5+ | 資料驗證 | ✅ |
| **JWT** | python-jose | 認證機制 | ✅ |
| **aiosmtplib** | 3.0+ | Email 發送服務 | ✅ |
| **Mailpit** | latest | Email 測試工具（開發） | ✅ |
| **Alembic** | 1.13+ | 資料庫遷移 | ✅ |
| **pytest** | 7.4+ | 測試框架 | ✅ |

#### 前端技術棧

| 技術 | 版本 | 用途 | 狀態 |
|------|------|------|------|
| **Vue.js** | 3.x | 前端框架 | ✅ |
| **Vite** | 5.x | 建構工具 | ✅ |
| **Pinia** | 2.x | 狀態管理 | ✅ |
| **Vue Router** | 4.x | 路由管理 | ✅ |
| **Axios** | 1.x | HTTP 客戶端 | ✅ |
| **WebSocket API** | 原生 | 即時通訊 | ✅ |

### 2.3 資料庫架構

#### 資料模型關係圖

```
┌─────────────┐
│    User     │ (用戶基本資料)
├─────────────┤
│ id (PK)     │
│ email       │◄──────┐
│ password    │       │
│ trust_score │       │ 1:1
│ warning_cnt │       │
└─────────────┘       │
                      │
                ┌─────┴──────┐
                │  Profile   │ (個人檔案)
                ├────────────┤
                │ id (PK)    │
                │ user_id    │
                │ bio        │
                │ location   │ (PostGIS Point)
                └────────────┘
                      │ 1:N
                      ▼
                ┌────────────┐
                │   Photo    │ (照片)
                ├────────────┤
                │ id (PK)    │
                │ profile_id │
                │ file_path  │
                │ is_primary │
                └────────────┘

┌─────────────┐       ┌─────────────┐
│    Like     │       │    Match    │ (配對記錄)
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ liker_id    │───┐   │ user1_id    │
│ liked_id    │   └──▶│ user2_id    │
│ created_at  │       │ status      │
└─────────────┘       │ matched_at  │
                      └─────────────┘
                            │ 1:N
                            ▼
                      ┌─────────────┐
                      │   Message   │ (聊天訊息)
                      ├─────────────┤
                      │ id (PK)     │
                      │ match_id    │
                      │ sender_id   │
                      │ content     │
                      │ is_read     │
                      └─────────────┘

┌──────────────┐      ┌─────────────┐
│ BlockedUser  │      │   Report    │ (舉報記錄)
├──────────────┤      ├─────────────┤
│ id (PK)      │      │ id (PK)     │
│ blocker_id   │      │ reporter_id │
│ blocked_id   │      │ reported_id │
│ reason       │      │ report_type │
│ created_at   │      │ reason      │
└──────────────┘      │ status      │
                      └─────────────┘

┌──────────────┐
│ Notification │ (通知記錄 - 持久化)
├──────────────┤
│ id (PK)      │
│ user_id      │
│ type         │ (message/match/liked)
│ title        │
│ content      │
│ data (JSONB) │
│ is_read      │
│ created_at   │
└──────────────┘
```

---

## 3. 已實作功能清單（Week 1-5）

### ✅ Week 1: 認證系統

#### 後端實作
- [x] User 資料模型（含 trust_score, warning_count）
- [x] JWT Token 生成與驗證
- [x] Refresh Token 機制
- [x] 密碼加密（bcrypt）
- [x] 登入失敗次數限制（5 次失敗後鎖定 15 分鐘，使用 Redis）
- [x] **API 端點：**
  - POST `/api/auth/register` - 用戶註冊
  - POST `/api/auth/login` - 用戶登入（含登入限制）
  - POST `/api/auth/verify-email` - Email 驗證
  - POST `/api/auth/refresh` - 刷新 Token
  - POST `/api/auth/logout` - 登出
  - POST `/api/auth/admin-login` - 管理員登入（含登入限制）

#### 前端實作
- [x] Register.vue - 註冊頁面
- [x] Login.vue - 登入頁面
- [x] AdminLogin.vue - 管理員登入
- [x] auth.js Store - 認證狀態管理

#### 測試
- [x] 12+ 個測試案例（含登入限制 9 個）
- [x] 測試覆蓋率 >80%

---

### ✅ Week 2: 個人檔案

#### 後端實作
- [x] Profile 資料模型
- [x] Photo 資料模型（1-6 張照片）
- [x] InterestTag 資料模型
- [x] 照片上傳服務（圖片壓縮、縮圖）
- [x] PostGIS 地理位置支援
- [x] **API 端點：**
  - GET `/api/profile/` - 取得個人檔案
  - PUT `/api/profile/` - 更新個人檔案
  - POST `/api/profile/photos/` - 上傳照片
  - DELETE `/api/profile/photos/{photo_id}/` - 刪除照片
  - PUT `/api/profile/photos/{photo_id}/primary/` - 設定主照片
  - GET `/api/profile/interest-tags/` - 取得興趣標籤
  - PUT `/api/profile/interests/` - 更新興趣

#### 前端實作
- [x] Profile.vue - 個人檔案編輯頁面
- [x] PhotoUploader.vue - 照片上傳組件
- [x] InterestSelector.vue - 興趣選擇器
- [x] profile.js Store - 個人檔案狀態管理

#### 測試
- [x] 15+ 個測試案例

---

### ✅ Week 3: 探索與配對

#### 後端實作
- [x] Like 資料模型
- [x] Match 資料模型
- [x] 配對演算法（興趣相似度 + 地理距離）
- [x] 配對分數計算（0-100%）
- [x] PostGIS 地理查詢優化
- [x] **API 端點：**
  - GET `/api/discovery/browse/` - 瀏覽候選人
  - POST `/api/discovery/like/{user_id}/` - 喜歡用戶
  - POST `/api/discovery/pass/{user_id}/` - 跳過用戶
  - GET `/api/discovery/matches/` - 取得配對列表
  - DELETE `/api/discovery/matches/{match_id}/` - 取消配對

#### 前端實作
- [x] Discovery.vue - 探索頁面（Tinder 風格卡片）
- [x] Matches.vue - 配對列表
- [x] MatchModal.vue - 配對成功彈窗
- [x] discovery.js Store - 探索狀態管理
- [x] match.js Store - 配對狀態管理
- [x] 滑動手勢支援（卡片拖拽）

#### 測試
- [x] 10+ 個測試案例

---

### ✅ Week 4: 即時聊天

#### 後端實作
- [x] Message 資料模型
- [x] WebSocket 連接管理器（manager.py）
- [x] 聊天室管理
- [x] 訊息持久化
- [x] 打字指示器（Typing Indicator）
- [x] 已讀回條（Read Receipts）
- [x] **API 端點：**
  - WebSocket `/ws` - WebSocket 連接
  - GET `/api/messages/conversations/` - 對話列表
  - GET `/api/messages/matches/{match_id}/messages/` - 聊天記錄
  - POST `/api/messages/messages/read/` - 標記已讀
  - DELETE `/api/messages/messages/{message_id}/` - 刪除訊息

#### 前端實作
- [x] ChatList.vue - 聊天列表頁面
- [x] Chat.vue - 即時聊天頁面
- [x] MessageBubble.vue - 訊息氣泡組件
- [x] useWebSocket.js - WebSocket Composable
- [x] chat.js Store - 聊天狀態管理
- [x] 自動重連機制
- [x] 未讀訊息計數

#### 測試
- [x] 8+ 個測試案例

---

### ✅ Week 5: 安全功能與管理後台

#### 後端實作 - 安全功能

##### 封鎖系統
- [x] BlockedUser 資料模型（Week 3 已建立）
- [x] 封鎖自動取消配對
- [x] **API 端點：**
  - POST `/api/safety/block/{user_id}` - 封鎖用戶
  - DELETE `/api/safety/block/{user_id}` - 解除封鎖
  - GET `/api/safety/blocked` - 取得封鎖列表

##### 舉報系統
- [x] Report 資料模型
- [x] 5 種舉報類型（INAPPROPRIATE, HARASSMENT, FAKE, SCAM, OTHER）
- [x] 舉報自動增加警告次數
- [x] **API 端點：**
  - POST `/api/safety/report` - 舉報用戶
  - GET `/api/safety/reports` - 取得我的舉報記錄

##### 內容審核
- [x] content_moderation.py 服務
- [x] 敏感詞檢測（8 種類型）
- [x] 可疑模式檢測（電話、URL、LINE ID、金額等）
- [x] 內容清理與替換
- [x] 動態敏感詞管理

#### 後端實作 - 管理後台
- [x] 管理員權限檢查（is_admin dependency）
- [x] **API 端點：**
  - GET `/api/admin/stats` - 統計數據
  - GET `/api/admin/reports` - 查看舉報列表
  - PUT `/api/admin/reports/{report_id}` - 處理舉報
  - PUT `/api/admin/users/{user_id}/ban` - 封禁用戶
  - PUT `/api/admin/users/{user_id}/unban` - 解封用戶

#### 前端實作
- [x] Blocked.vue - 封鎖列表頁面
- [x] ReportModal.vue - 舉報彈窗（整合到 Discovery.vue）
- [x] AdminDashboard.vue - 管理員儀表板
- [x] safety.js Store - 安全功能狀態管理
- [x] user.js Store - 用戶狀態管理

#### 測試
- [x] 13 個封鎖/舉報測試
- [x] 34 個內容審核測試
- [x] 總計 47+ 測試案例

---

## 4. 待實作功能（Week 6 與未來）

### ✅ 已完成功能

#### 地理位置功能
- [x] 地理位置自動定位（瀏覽器 Geolocation API）
- [x] 位置模糊化保護隱私（±500m-1km 隨機偏移）
- [x] 反向地理編碼（GPS 座標 → 台灣城市）
- [x] 支援 22 個台灣城市自動偵測
- [x] PostGIS 地理位置查詢

#### WebSocket 安全功能
- [x] 首次訊息認證機制（Token 不暴露在 URL）
- [x] Token 黑名單檢查
- [x] Token 過期驗證
- [x] Token 類型驗證（access token）
- [x] 認證超時機制（5 秒）
- [x] 並發安全（asyncio.Lock）
- [x] 心跳 ping/pong 機制
- [x] 異常連接自動清理
- [x] 訊息內容審核
- [x] 自動重連機制

#### 推播通知功能
- [x] 新訊息通知（接收者不在聊天室時發送）
- [x] 新配對通知（互相喜歡時向雙方發送）
- [x] 有人喜歡你通知（單方喜歡時向被喜歡者發送）
- [x] 通知鈴鐺 UI 組件
- [x] 未讀通知計數
- [x] 通知列表管理
- [x] 標記已讀功能
- [x] 點擊通知導航功能

#### 通知持久化功能（2025-12-14 完成）
- [x] Notification 資料模型（PostgreSQL + JSONB）
- [x] 通知 API（5 個端點）
- [x] 通知自動建立（Like/Match/Message 時寫入 DB）
- [x] 前端 API 整合（登入時載入通知）
- [x] 頁面重整後通知保留
- [x] 17 個後端測試案例（TDD）

### 🔄 Week 6: 測試與部署（進行中）

#### 測試優化
- [ ] 補充邊界案例測試
- [ ] E2E 測試關鍵流程
- [ ] 效能測試（負載測試）
- [ ] 安全測試（滲透測試）

#### 效能優化
- [ ] API 回應時間優化
- [ ] 資料庫查詢優化（添加索引）
- [ ] 前端打包優化（Code Splitting）
- [ ] Redis 快取實作
- [ ] CDN 配置（圖片）

#### 部署準備
- [ ] Docker 生產環境映像
- [ ] Nginx 反向代理配置
- [ ] 環境變數管理
- [ ] CI/CD Pipeline
- [ ] 監控與日誌系統

#### 安全強化
- [ ] Rate Limiting（API 限流）
- [ ] SQL Injection 防護（已有部分）
- [ ] XSS 防護（已有部分）
- [ ] CSRF Token
- [ ] Content Security Policy (CSP)

---

### 🔮 未來擴充功能（Phase 2）

#### 認證增強
- [ ] 社交媒體登入（Google, Facebook）
- [ ] 兩步驟驗證（2FA）
- [ ] 手機號碼驗證
- [ ] 實名制驗證（身份證、駕照）

#### 付費功能
- [ ] VIP 會員機制
- [ ] Super Like（超級喜歡）
- [ ] 無限次喜歡
- [ ] 查看誰喜歡我
- [ ] 回溯功能（Rewind）

#### 社交功能
- [ ] 用戶動態（限時動態）
- [ ] 線下活動配對
- [ ] 群組聊天
- [ ] 語音訊息
- [ ] 視訊通話（WebRTC）

#### 推薦系統
- [ ] AI 智能配對（機器學習）
- [ ] 個性化推薦演算法
- [ ] 行為分析優化

#### 通知系統
- [ ] 推播通知（FCM）
- [ ] Email 通知
- [ ] SMS 通知

---

## 5. 開發策略

### 5.1 TDD 開發流程

我們採用測試驅動開發（Test-Driven Development）：

```
1. ⭕ 紅燈（Red）
   └─ 先寫測試，測試失敗

2. 🟢 綠燈（Green）
   └─ 寫最簡單的程式碼讓測試通過

3. 🔵 重構（Refactor）
   └─ 優化程式碼，保持測試通過
```

**實際範例（Week 5 封鎖功能）：**

```python
# 1. 先寫測試 (test_safety.py)
async def test_block_user_success():
    """測試：成功封鎖用戶"""
    response = await client.post(f"/api/safety/block/{bob.id}")
    assert response.status_code == 201

# 2. 實作功能 (safety.py)
@router.post("/block/{user_id}")
async def block_user(user_id: str, ...):
    new_block = BlockedUser(...)
    db.add(new_block)
    await db.commit()
    return {"blocked": True}

# 3. 重構優化
# - 添加驗證邏輯
# - 添加錯誤處理
# - 優化資料庫查詢
```

### 5.2 Git 工作流程

**分支策略：**
```
main (生產環境)
  └─ develop (開發環境)
      ├─ feature/week-1-auth
      ├─ feature/week-2-profile
      ├─ feature/week-3-matching
      ├─ feature/week-4-chat
      └─ feature/week-5-safety
```

**Commit 訊息規範：**
```
feat: 新功能
fix: 修復 Bug
docs: 文檔更新
test: 測試相關
refactor: 重構
style: 程式碼格式
perf: 效能優化
```

**實際範例：**
```bash
git commit -m "feat: 實作封鎖功能（Block Feature）

- 新增 BlockedUser API 端點
- 封鎖自動取消配對
- 新增 7 個測試案例
- 前端封鎖列表頁面

Closes #123"
```

### 5.3 程式碼規範

#### 後端規範（Python）
```python
# 使用 Type Hints
async def block_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    pass

# 使用 Pydantic 驗證
class BlockUserRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)

# 錯誤處理
if not target_user:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="用戶不存在"
    )
```

#### 前端規範（Vue 3）
```javascript
// Composition API
<script setup>
import { ref, computed } from 'vue'

const blockedUsers = ref([])
const loading = ref(false)

const hasBlockedUsers = computed(() => blockedUsers.value.length > 0)
</script>

// 命名規範
// - 組件：PascalCase (ReportModal.vue)
// - 變數：camelCase (showReportModal)
// - 常數：UPPER_CASE (MAX_PHOTOS)
```

---

## 6. API 端點總覽

### 6.1 認證相關（/api/auth）
| 方法 | 端點 | 說明 | 狀態 |
|------|------|------|------|
| POST | `/register` | 用戶註冊 | ✅ |
| POST | `/login` | 用戶登入 | ✅ |
| POST | `/verify-email` | Email 驗證 | ✅ |
| POST | `/resend-verification` | 重發驗證碼 | ✅ |
| POST | `/forgot-password` | 忘記密碼（發送重置郵件） | ✅ |
| GET | `/verify-reset-token` | 驗證重置 Token | ✅ |
| POST | `/reset-password` | 重置密碼 | ✅ |
| POST | `/refresh` | 刷新 Token | ✅ |
| POST | `/logout` | 登出 | ✅ |
| POST | `/admin-login` | 管理員登入 | ✅ |

### 6.2 個人檔案（/api/profile）
| 方法 | 端點 | 說明 | 狀態 |
|------|------|------|------|
| GET | `/` | 取得個人檔案 | ✅ |
| PUT | `/` | 更新個人檔案 | ✅ |
| POST | `/photos/` | 上傳照片 | ✅ |
| DELETE | `/photos/{id}/` | 刪除照片 | ✅ |
| PUT | `/photos/{id}/primary/` | 設定主照片 | ✅ |
| GET | `/interest-tags/` | 取得興趣標籤 | ✅ |
| PUT | `/interests/` | 更新興趣 | ✅ |

### 6.3 探索與配對（/api/discovery）
| 方法 | 端點 | 說明 | 狀態 |
|------|------|------|------|
| GET | `/browse/` | 瀏覽候選人 | ✅ |
| POST | `/like/{user_id}/` | 喜歡用戶 | ✅ |
| POST | `/pass/{user_id}/` | 跳過用戶 | ✅ |
| GET | `/matches/` | 配對列表 | ✅ |
| DELETE | `/matches/{id}/` | 取消配對 | ✅ |

### 6.4 聊天訊息（/api/messages）
| 方法 | 端點 | 說明 | 狀態 |
|------|------|------|------|
| GET | `/conversations/` | 對話列表 | ✅ |
| GET | `/matches/{id}/messages/` | 聊天記錄 | ✅ |
| POST | `/messages/read/` | 標記已讀 | ✅ |
| POST | `/matches/{id}/upload-image/` | 上傳聊天圖片/GIF | ✅ |
| DELETE | `/messages/{id}/` | 刪除訊息 | ✅ |

### 6.5 WebSocket（/ws）
| 類型 | 端點 | 說明 | 狀態 |
|------|------|------|------|
| WebSocket | `/ws` | WebSocket 連接 | ✅ |

### 6.6 安全功能（/api/safety）
| 方法 | 端點 | 說明 | 狀態 |
|------|------|------|------|
| POST | `/block/{user_id}` | 封鎖用戶 | ✅ |
| DELETE | `/block/{user_id}` | 解除封鎖 | ✅ |
| GET | `/blocked` | 封鎖列表 | ✅ |
| POST | `/report` | 舉報用戶 | ✅ |
| GET | `/reports` | 舉報記錄 | ✅ |

### 6.7 管理後台（/api/admin）
| 方法 | 端點 | 說明 | 狀態 |
|------|------|------|------|
| GET | `/stats` | 統計數據 | ✅ |
| GET | `/reports` | 舉報列表 | ✅ |
| PUT | `/reports/{id}` | 處理舉報 | ✅ |
| PUT | `/users/{id}/ban` | 封禁用戶 | ✅ |
| PUT | `/users/{id}/unban` | 解封用戶 | ✅ |

### 6.8 通知（/api/notifications）
| 方法 | 端點 | 說明 | 狀態 |
|------|------|------|------|
| GET | `` | 取得通知列表（分頁） | ✅ |
| GET | `/unread-count` | 取得未讀數量 | ✅ |
| PUT | `/{id}/read` | 標記單個為已讀 | ✅ |
| PUT | `/read-all` | 標記全部已讀 | ✅ |
| DELETE | `/{id}` | 刪除單個通知 | ✅ |

**總計：49+ 個 API 端點**（含密碼重置、圖片訊息上傳、通知等）

---

## 7. 前端架構

### 7.1 頁面結構

```
src/views/
├── Home.vue              # 首頁
├── Register.vue          # 註冊頁面
├── Login.vue             # 登入頁面
├── ForgotPassword.vue    # 忘記密碼頁面
├── ResetPassword.vue     # 重置密碼頁面
├── Profile.vue           # 個人檔案
├── Discovery.vue         # 探索配對（含舉報按鈕）
├── Matches.vue           # 配對列表
├── ChatList.vue          # 聊天列表
├── Chat.vue              # 即時聊天
├── Blocked.vue           # 封鎖列表
└── admin/
    ├── AdminLogin.vue    # 管理員登入
    └── AdminDashboard.vue # 管理員儀表板
```

**總計：13 個頁面**（新增密碼重置相關頁面）

### 7.2 組件結構

```
src/components/
├── InterestSelector.vue      # 興趣選擇器
├── NotificationBell.vue      # 通知鈴鐺
├── PhotoUploader.vue         # 照片上傳器
├── UserDetailModal.vue       # 用戶詳情模態框
├── MatchModal.vue            # 配對成功彈窗
├── ReportModal.vue           # 舉報彈窗
├── layout/
│   └── NavBar.vue            # 導航欄
├── chat/
│   ├── MessageBubble.vue     # 訊息氣泡
│   ├── ChatImagePicker.vue   # 圖片選擇器
│   └── ImagePreviewModal.vue # 圖片預覽模態框
└── ui/
    ├── AnimatedButton.vue    # 動畫按鈕
    ├── FloatingInput.vue     # 浮動輸入框
    ├── HeartLoader.vue       # 愛心載入動畫
    ├── GlassCard.vue         # 玻璃卡片
    ├── Badge.vue             # 徽章組件
    └── FeatureCard.vue       # 功能卡片
```

**總計：16 個組件**（含 UI 組件）

### 7.3 狀態管理（Pinia Stores）

```
src/stores/
├── auth.js       # 認證狀態（登入、Token）
├── profile.js    # 個人檔案狀態
├── discovery.js  # 探索配對狀態
├── match.js      # 配對列表狀態
├── chat.js       # 聊天狀態（含 WebSocket）
├── safety.js     # 安全功能（封鎖、舉報）
└── user.js       # 用戶全域狀態
```

**總計：7 個 Stores**

### 7.4 Composables

```
src/composables/
└── useWebSocket.js  # WebSocket 連接管理
    ├── connect()         # 連接
    ├── disconnect()      # 斷開
    ├── sendMessage()     # 發送訊息
    ├── onMessage()       # 接收訊息
    └── reconnect()       # 自動重連
```

---

## 8. 測試架構

### 8.1 測試統計

```
後端測試：
├── Week 1 (認證): 21+ 個測試
│   ├── 認證功能: 12 個
│   └── 登入限制: 9 個
├── Week 2 (檔案): 15+ 個測試
├── Week 3 (配對): 10+ 個測試
├── Week 4 (聊天): 8+ 個測試
├── Week 5 (安全): 47+ 個測試
│   ├── 封鎖/舉報: 13 個
│   └── 內容審核: 34 個
└── Week 6 (通知持久化): 17 個測試
    ├── Model 測試: 5 個
    ├── API 測試: 10 個
    └── 自動建立測試: 2 個

總計: 246 個測試案例
覆蓋率: >80%
```

### 8.2 測試工具

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

## 9. 部署架構（待實作）

### 9.1 生產環境架構（規劃中）

```
Internet
    │
    ▼
┌─────────────────┐
│   Cloudflare    │ (CDN + DDoS Protection)
│   (DNS/CDN)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Nginx       │ (反向代理 + SSL)
│  Load Balancer  │
└────────┬────────┘
         │
    ┌────┴─────┐
    │          │
    ▼          ▼
┌────────┐ ┌────────┐
│FastAPI │ │FastAPI │ (多個實例)
│Instance│ │Instance│
└────┬───┘ └────┬───┘
     │          │
     └────┬─────┘
          ▼
    ┌──────────────┐
    │ PostgreSQL   │ (主從複製)
    │   (Primary)  │
    └──────────────┘
          │
          ▼
    ┌──────────────┐
    │    Redis     │ (快取/Session)
    │   Cluster    │
    └──────────────┘
```

### 9.2 Docker 配置

```yaml
# docker-compose.yml (生產環境)
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    ports:
      - "80:80"

  postgres:
    image: postgis/postgis:16-3.4
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
```

---

## 10. 效能目標

### 10.1 已達成指標

| 指標 | 目標 | 當前值 | 狀態 |
|------|------|--------|------|
| 測試覆蓋率 | >80% | >80% | ✅ |
| 後端啟動時間 | <5s | ~3s | ✅ |
| 前端首次載入 | <3s | ~2s | ✅ |
| WebSocket 連接 | <1s | ~500ms | ✅ |

### 10.2 待優化指標

| 指標 | 目標 | 當前值 | 狀態 |
|------|------|--------|------|
| API 回應時間 (p95) | <200ms | ~150ms | ✅ |
| 資料庫查詢時間 | <50ms | ~30ms | ✅ |
| Redis 快取命中率 | >80% | N/A | 🔄 |
| 並發用戶數 | >1000 | 未測試 | 🔄 |

---

## 11. 安全措施

### 11.1 已實作

- ✅ **認證安全**
  - JWT Token 認證
  - 密碼 bcrypt 加密
  - Token 過期機制
  - Refresh Token

- ✅ **資料驗證**
  - Pydantic Schema 驗證
  - 輸入長度限制
  - 類型檢查

- ✅ **內容安全**
  - 敏感詞過濾
  - 可疑模式檢測
  - XSS 防護（部分）

- ✅ **用戶安全**
  - 封鎖機制
  - 舉報系統
  - 警告計數
  - 管理員審核

### 11.2 待加強

- [ ] Rate Limiting（API 限流）
- [ ] CSRF Protection
- [ ] Content Security Policy
- [ ] SQL Injection 防護強化
- [ ] 檔案上傳安全掃描
- [ ] 日誌與監控

---

## 12. 關鍵決策記錄

### 12.1 技術選型

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

### 12.2 架構決策

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

## 13. 專案統計

### 13.1 程式碼統計

```
後端（Python）:
  - 檔案數: ~50 個
  - 程式碼行數: ~8,000 行
  - 測試行數: ~3,000 行

前端（Vue/JS）:
  - 檔案數: ~30 個
  - 程式碼行數: ~7,000 行
  - 組件數: 29 個（13 頁面 + 16 組件）

總計: ~18,000 行程式碼
```

### 13.2 功能統計

```
✅ 已完成:
  - 9 個 API 模組（含通知）
  - 9 個資料模型（含 Notification）
  - 49+ 個 API 端點
  - 13 個前端頁面
  - 16 個 Vue 組件
  - 7 個 Pinia Stores
  - 246 個測試案例

🔄 進行中:
  - Week 6: 測試與部署

🔮 未來計畫:
  - Phase 2 付費功能
  - Phase 3 社交功能
```

---

## 14. 學習資源

### 14.1 官方文檔

- [FastAPI 文檔](https://fastapi.tiangolo.com/)
- [SQLAlchemy 文檔](https://docs.sqlalchemy.org/)
- [Vue 3 文檔](https://vuejs.org/)
- [Pinia 文檔](https://pinia.vuejs.org/)
- [PostgreSQL 文檔](https://www.postgresql.org/docs/)
- [PostGIS 文檔](https://postgis.net/documentation/)

### 14.2 專案相關文檔

- [README.md](./README.md) - 專案總覽
- [QUICKSTART.md](./QUICKSTART.md) - 快速開始指南
- [docs/INDEX.md](./docs/INDEX.md) - 文檔索引

---

## 15. 聯絡資訊

**專案倉庫：** [GitHub Repository]

**團隊成員：**
- 後端開發: twtrubiks + Claude (AI)
- 前端開發: twtrubiks + Claude (AI)
- 安全功能: Claude (AI)
- 測試: Claude (AI) + twtrubiks

**技術支援：**
- GitHub Issues: [提交問題]
- Email: [聯絡信箱]

---

---

## 16. 已知問題與技術債務

### 16.1 P0 - 阻塞性問題（上線前必須解決）

| ID | 問題 | 位置 | 工作量 | 影響 | 狀態 |
|----|------|------|--------|------|------|
| ~~P0-1~~ | ~~密碼重置功能缺失~~ | auth.py | 2-3 小時 | 用戶流失 | ✅ 已完成 |
| ~~P0-2~~ | ~~Email 服務未整合~~ | auth.py | 2-4 小時 | 假帳號氾濫 | ✅ 已完成 |
| ~~P0-3~~ | ~~登入失敗無限制~~ | auth.py | 1 小時 | 暴力破解風險 | ✅ 已完成 |
| P0-4 | 全局速率限制缺失 | main.py | 1 小時 | DoS 攻擊風險 | ❌ 待實作 |

**已完成 P0 項目（2025-12-12）**：
- ✅ P0-1: 密碼重置功能（3 個 API 端點 + 2 個前端頁面）
- ✅ P0-2: Email 服務整合（Mailpit + aiosmtplib + 美觀 HTML 模板）
- ✅ P0-3: 登入失敗次數限制（5 次失敗後鎖定 15 分鐘，使用 Redis）

### 16.2 P1 - 高優先級（本週內處理）

| ID | 問題 | 工作量 | 狀態 |
|----|------|--------|------|
| P1-2 | 照片審核機制 | 4-8 小時 | ❌ 待實作 |
| P1-3 | 每日喜歡次數限制 | 2 小時 | ❌ 待實作 |
| ~~P1-4~~ | ~~圖片/GIF 訊息~~ | 4-6 小時 | ✅ 已完成 |
| P1-5 | WebSocket 單實例限制 | 1 週 | ❌ 待實作 |
| P1-6 | Match 表查詢效率 | 4 小時 | ❌ 待實作 |
| P1-7 | 監控與日誌系統 | 3-4 小時 | ❌ 待實作 |

**已完成 P1 項目**：
- ✅ P1-4: 圖片/GIF 訊息（上傳端點 + 縮圖 + WebSocket 傳輸 + UI 組件）

### 16.3 技術債務清單

| 項目 | 狀態 | 說明 |
|------|------|------|
| Redis 整合 | 🔄 部分使用 | 登入限制已使用 Redis，快取/Session 待實作 |
| Token 黑名單 | ❌ 使用內存 | 需改用 Redis |
| 內容審核快取 | ⚠️ 類變數 | 需改用 Redis |
| 驗證碼存儲 | ❌ 內存 | 需改用 Redis |
| 檔案儲存 | ⚠️ 本地模擬 | 需整合 AWS S3 |

---

## 17. 技術路線圖

### Phase 1: 安全修復（1-2 週）

**目標**: 解決所有阻塞性安全問題

- [ ] 添加全局速率限制（slowapi）
- [x] 實作登入失敗次數限制（Redis，5 次/15 分鐘鎖定）
- [x] 實現密碼重置功能
- [x] 整合 Email 發送服務

**已完成**:
- [x] 推播通知系統
- [x] 密碼重置功能
- [x] Email 服務整合（Mailpit）
- [x] 登入失敗次數限制

### Phase 2: 功能完善（2-4 週）

**目標**: 提升用戶體驗和留存率

- [ ] 整合推播通知（FCM）
- [ ] 實作圖片/GIF 訊息
- [ ] 地理位置自動定位
- [ ] 照片審核機制（AWS Rekognition）
- [ ] 每日喜歡次數限制
- [ ] 整合 AWS S3 檔案儲存

### Phase 3: 可擴展性（4-6 週）

**目標**: 支援水平擴展和大規模用戶

- [ ] Redis Token 黑名單
- [ ] Redis 內容審核快取
- [ ] Redis WebSocket Pub/Sub
- [ ] 優化 Match 表查詢
- [ ] CDN 配置
- [ ] 監控和告警（Sentry, Prometheus）

### Phase 4: 變現功能（6-8 週）

**目標**: 建立收入來源

- [ ] VIP 會員系統
- [ ] Super Like 功能
- [ ] Boost 曝光功能
- [ ] 查看誰喜歡我
- [ ] 回溯功能

---

## 18. 上線準備度評估

### MVP 必備功能檢查表

| 分類 | 功能 | 狀態 | 阻塞性 |
|------|------|------|--------|
| **認證** | 註冊/登入 | ✅ 完成 | - |
| | 密碼重置 | ✅ 完成 | - |
| | Email 驗證 | ✅ 完成（Mailpit） | - |
| | 登入失敗限制 | ✅ 完成 | - |
| **個人檔案** | 建立檔案 | ✅ 完成 | - |
| | 上傳照片 | ✅ 完成 | - |
| | 地理位置自動定位 | ✅ 完成 | - |
| | 照片審核 | ❌ 缺失 | 是 |
| **配對** | 探索功能 | ✅ 完成 | - |
| | 配對演算法 | ✅ 完成 | - |
| **聊天** | 即時訊息 | ✅ 完成 | - |
| | WebSocket 安全認證 | ✅ 完成 | - |
| | 推播通知 | ✅ 完成 | - |
| **安全** | 封鎖/舉報 | ✅ 完成 | - |
| | 內容審核 | ✅ 完成 | - |

### 技術基礎設施

| 項目 | 狀態 |
|------|------|
| 資料庫遷移 | ✅ 完成 |
| API 文檔 | ✅ 完成 |
| 測試覆蓋率 | ✅ 80% |
| Docker 配置 | ✅ 完成 |
| 監控/日誌 | ❌ 缺失 |
| Rate Limiting | ❌ 缺失 |

**整體準備度**: 82% (密碼重置 + Email 服務 + 地理位置自動定位 + WebSocket Token 改進 + 推播通知 + 登入失敗限制已完成)

---

**文檔版本：** 2.3.0
**最後更新：** 2025-12-14（新增通知持久化功能）
**維護者：** MergeMeet Development Team

---

**Happy Coding! 🚀**
