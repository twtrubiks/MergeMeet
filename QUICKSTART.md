# 🚀 MergeMeet 快速開始指南

## 📊 專案狀態總覽

### ✅ 已完成週次（Week 1-5）

| Week | 功能 | 後端 | 前端 | 測試 | 狀態 |
|------|------|------|------|------|------|
| Week 0.5 | 環境設置 | ✅ | ✅ | ✅ | ✅ 完成 |
| Week 1 | 認證系統 | ✅ | ✅ | ✅ | ✅ 完成 |
| Week 2 | 個人檔案 | ✅ | ✅ | ✅ | ✅ 完成 |
| Week 3 | 探索與配對 | ✅ | ✅ | ✅ | ✅ 完成 |
| Week 4 | 即時聊天 | ✅ | ✅ | ✅ | ✅ 完成 |
| Week 5 | 安全功能與管理後台 | ✅ | ✅ | ✅ | ✅ 完成 |
| Week 6 | 測試與部署 | 🔄 | 🔄 | 🔄 | 🔄 進行中 |

### 📁 專案結構概覽

```
mergemeet/
├── backend/              ✅ 後端 FastAPI 應用
│   ├── app/
│   │   ├── api/         ✅ API 路由 (9 個模組)
│   │   │   ├── auth.py           # Week 1: 認證系統
│   │   │   ├── profile.py        # Week 2: 個人檔案
│   │   │   ├── discovery.py      # Week 3: 探索與配對
│   │   │   ├── messages.py       # Week 4: 聊天訊息 API
│   │   │   ├── websocket.py      # Week 4: WebSocket
│   │   │   ├── safety.py         # Week 5: 封鎖/舉報
│   │   │   ├── admin.py          # Week 5: 管理後台
│   │   │   ├── moderation.py     # Week 5: 內容審核
│   │   │   └── notifications.py  # Week 6: 通知系統
│   │   ├── core/        ✅ 核心配置
│   │   ├── models/      ✅ 資料庫模型 (9 個模型)
│   │   ├── schemas/     ✅ Pydantic Schemas
│   │   ├── services/    ✅ 業務邏輯
│   │   │   └── content_moderation.py  # 內容審核
│   │   ├── websocket/   ✅ WebSocket 管理
│   │   └── main.py      ✅ 主應用
│   ├── tests/           ✅ 測試框架 (265+ 個測試)
│   └── uploads/         ✅ 檔案上傳目錄
│
├── frontend/            ✅ 前端 Vue 3 應用
│   ├── src/
│   │   ├── components/  ✅ Vue 組件 (16 個)
│   │   ├── views/       ✅ 頁面 (13 個頁面)
│   │   ├── stores/      ✅ Pinia Stores (7 個)
│   │   ├── composables/ ✅ Vue Composables
│   │   ├── router/      ✅ Vue Router
│   │   └── api/         ✅ API 客戶端
│   └── package.json     ✅ Node.js 依賴
│
├── scripts/             ✅ 工具腳本
│   ├── setup.sh        ✅ 環境設置
│   ├── dev.sh          ✅ 啟動開發
│   ├── test.sh         ✅ 執行測試
│   └── check.sh        ✅ 狀態檢查
│
├── docker-compose.yml   ✅ Docker 配置
└── README.md           ✅ 專案說明
```

---

## 🚀 一鍵啟動

### 方法 1: 使用腳本（推薦）

```bash
# 1. 設置開發環境（首次執行）
./scripts/setup.sh

# 2. 啟動開發伺服器
./scripts/dev.sh

# 3. 執行測試
./scripts/test.sh

# 4. 檢查服務狀態
./scripts/check.sh
```

### 方法 2: 手動啟動

#### 步驟 1: 啟動資料庫

```bash
docker compose up -d postgres redis
```

#### 步驟 2: 啟動後端

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### 步驟 3: 啟動前端（另一個終端）

```bash
cd frontend
npm install
npm run dev
```

### 訪問應用

- **前端**: http://localhost:5173
- **後端 API**: http://localhost:8000
- **API 文檔**: http://localhost:8000/docs
- **管理後台**: http://localhost:5173/admin/login

---

## ✨ 已完成的功能

### Week 1: 認證系統 ✅

**後端 API (`app/api/auth.py`):**
- ✅ POST `/api/auth/register` - 用戶註冊
- ✅ POST `/api/auth/login` - 用戶登入
- ✅ POST `/api/auth/verify-email` - Email 驗證
- ✅ POST `/api/auth/refresh` - 刷新 Token
- ✅ POST `/api/auth/logout` - 登出
- ✅ POST `/api/auth/admin-login` - 管理員登入

**前端頁面:**
- ✅ `Register.vue` - 註冊頁面
- ✅ `Login.vue` - 登入頁面
- ✅ `AdminLogin.vue` - 管理員登入

**資料模型:**
- ✅ `User` - 用戶模型（含 trust_score, warning_count）

**測試:** 12+ 個測試案例

---

### Week 2: 個人檔案 ✅

**後端 API (`app/api/profile.py`):**
- ✅ GET `/api/profile/` - 取得個人檔案
- ✅ PUT `/api/profile/` - 更新個人檔案
- ✅ POST `/api/profile/photos/` - 上傳照片
- ✅ DELETE `/api/profile/photos/{photo_id}/` - 刪除照片
- ✅ PUT `/api/profile/photos/{photo_id}/primary/` - 設定主照片
- ✅ GET `/api/profile/interest-tags/` - 取得興趣標籤
- ✅ PUT `/api/profile/interests/` - 更新興趣

**前端頁面:**
- ✅ `Profile.vue` - 個人檔案頁面

**前端組件:**
- ✅ `PhotoUploader.vue` - 照片上傳組件
- ✅ `InterestSelector.vue` - 興趣選擇器

**資料模型:**
- ✅ `Profile` - 個人檔案
- ✅ `Photo` - 照片
- ✅ `InterestTag` - 興趣標籤

**測試:** 15+ 個測試案例

---

### Week 3: 探索與配對 ✅

**後端 API (`app/api/discovery.py`):**
- ✅ GET `/api/discovery/browse/` - 瀏覽候選人
- ✅ POST `/api/discovery/like/{user_id}/` - 喜歡用戶
- ✅ POST `/api/discovery/pass/{user_id}/` - 跳過用戶
- ✅ GET `/api/discovery/matches/` - 取得配對列表
- ✅ DELETE `/api/discovery/matches/{match_id}/` - 取消配對

**前端頁面:**
- ✅ `Discovery.vue` - 探索頁面（Tinder 風格卡片）
- ✅ `Matches.vue` - 配對列表

**前端組件:**
- ✅ `MatchModal.vue` - 配對成功彈窗

**資料模型:**
- ✅ `Like` - 喜歡記錄
- ✅ `Match` - 配對記錄

**核心功能:**
- ✅ 配對演算法（興趣相似度 + 地理距離）
- ✅ 配對分數計算（0-100%）
- ✅ 滑動手勢支援

**測試:** 10+ 個測試案例

---

### Week 4: 即時聊天 ✅

**後端 API (`app/api/messages.py`):**
- ✅ GET `/api/messages/conversations/` - 對話列表
- ✅ GET `/api/messages/matches/{match_id}/messages/` - 聊天記錄
- ✅ POST `/api/messages/messages/read/` - 標記已讀
- ✅ DELETE `/api/messages/messages/{message_id}/` - 刪除訊息

**WebSocket API (`app/api/websocket.py`):**
- ✅ WebSocket `/ws` - WebSocket 連接
- ✅ 即時訊息發送/接收
- ✅ 打字指示器
- ✅ 已讀回條

**前端頁面:**
- ✅ `ChatList.vue` - 聊天列表
- ✅ `Chat.vue` - 即時聊天頁面

**前端組件:**
- ✅ `MessageBubble.vue` - 訊息氣泡組件

**前端 Composables:**
- ✅ `useWebSocket.js` - WebSocket 連接管理

**資料模型:**
- ✅ `Message` - 訊息記錄

**核心功能:**
- ✅ WebSocket 連接管理器 (`websocket/manager.py`)
- ✅ 自動重連機制
- ✅ 未讀訊息計數
- ✅ 聊天記錄分頁載入

**測試:** 8+ 個測試案例

---

### Week 5: 安全功能與管理後台 ✅

#### 安全功能

**封鎖系統 (`app/api/safety.py`):**
- ✅ POST `/api/safety/block/{user_id}` - 封鎖用戶
- ✅ DELETE `/api/safety/block/{user_id}` - 解除封鎖
- ✅ GET `/api/safety/blocked` - 取得封鎖列表

**舉報系統 (`app/api/safety.py`):**
- ✅ POST `/api/safety/report` - 舉報用戶
- ✅ GET `/api/safety/reports` - 取得我的舉報記錄

**內容審核 (`app/services/content_moderation.py`):**
- ✅ 敏感詞檢測（8 種類型）
- ✅ 可疑模式檢測（電話、URL、LINE、金額等）
- ✅ 內容清理與替換
- ✅ 動態敏感詞管理

**前端頁面:**
- ✅ `Blocked.vue` - 封鎖列表頁面

**前端組件:**
- ✅ `ReportModal.vue` - 舉報彈窗（整合到 Discovery.vue）

**資料模型:**
- ✅ `BlockedUser` - 封鎖記錄
- ✅ `Report` - 舉報記錄

**測試:** 13 個封鎖/舉報測試 + 34 個內容審核測試

---

### Week 6: 通知持久化 ✅

**後端 API (`app/api/notifications.py`):**
- ✅ GET `/api/notifications` - 取得通知列表（分頁）
- ✅ GET `/api/notifications/unread-count` - 取得未讀數量
- ✅ PUT `/api/notifications/{id}/read` - 標記單個為已讀
- ✅ PUT `/api/notifications/read-all` - 標記全部已讀
- ✅ DELETE `/api/notifications/{id}` - 刪除單個通知

**資料模型:**
- ✅ `Notification` - 通知記錄（含 JSONB data 欄位）

**核心功能:**
- ✅ 通知自動建立（Like/Match/Message 時寫入 DB）
- ✅ 前端 API 整合（登入時載入通知）
- ✅ 頁面重整後通知保留
- ✅ 通知鈴鐺 UI 組件

**測試:** 17 個測試案例（TDD 開發）

---

#### 管理後台

**後端 API (`app/api/admin.py`):**
- ✅ GET `/api/admin/stats` - 統計數據
- ✅ GET `/api/admin/reports` - 查看舉報列表
- ✅ PUT `/api/admin/reports/{report_id}` - 處理舉報
- ✅ PUT `/api/admin/users/{user_id}/ban` - 封禁用戶
- ✅ PUT `/api/admin/users/{user_id}/unban` - 解封用戶

**前端頁面:**
- ✅ `AdminDashboard.vue` - 管理員儀表板

**核心功能:**
- ✅ 統計卡片（用戶、配對、訊息、舉報）
- ✅ 舉報管理界面
- ✅ 用戶管理（封禁/解封）
- ✅ 管理員權限檢查

---

## 📊 檔案統計

### 後端
- **API 模組**: 9 個
- **資料模型**: 9 個模型 (User, Profile, Photo, InterestTag, Like, Match, Message, BlockedUser, Report, Notification)
- **測試檔案**: 15+ 個
- **測試案例**: 265+ 個
- **測試覆蓋率**: >80%

### 前端
- **頁面**: 13 個
- **組件**: 16 個
- **Stores**: 7 個 (auth, profile, discovery, match, chat, safety, user)
- **Composables**: 1 個 (useWebSocket)

---

## 🎯 功能驗收標準

### Week 1: 認證系統
- ✅ 可以註冊新用戶
- ✅ 可以登入並取得 JWT Token
- ✅ 可以驗證 Email
- ✅ 可以刷新 Token
- ✅ 管理員可以登入
- ✅ 測試覆蓋率 > 80%

### Week 2: 個人檔案
- ✅ 可以上傳照片（最多 6 張）
- ✅ 可以設定主照片
- ✅ 可以刪除照片
- ✅ 可以選擇興趣標籤
- ✅ 可以設定地理位置
- ✅ 測試覆蓋率 > 80%

### Week 3: 探索與配對
- ✅ 可以瀏覽候選人
- ✅ 可以喜歡/跳過候選人
- ✅ 雙向喜歡自動配對
- ✅ 配對列表正常顯示
- ✅ 配對分數正確計算
- ✅ 測試覆蓋率 > 80%

### Week 4: 即時聊天
- ✅ 可以即時發送訊息
- ✅ 可以即時接收訊息
- ✅ 打字指示器正常運作
- ✅ 已讀回條正常顯示
- ✅ WebSocket 自動重連
- ✅ 測試覆蓋率 > 80%

### Week 5: 安全功能與管理後台
- ✅ 可以封鎖/解除封鎖用戶
- ✅ 可以舉報不當用戶
- ✅ 內容審核正常過濾敏感詞
- ✅ 管理員可以查看統計
- ✅ 管理員可以處理舉報
- ✅ 違規用戶警告計數增加
- ✅ 測試覆蓋率 > 80%

---

## 🧪 測試指令

```bash
# 執行所有測試
cd backend
pytest -v

# 執行特定測試
pytest tests/test_auth.py -v
pytest tests/test_profile.py -v
pytest tests/test_discovery.py -v
pytest tests/test_safety.py -v
pytest tests/test_content_moderation.py -v

# 查看測試覆蓋率
pytest --cov=app --cov-report=html

# 執行特定標記的測試
pytest -m unit -v
```

---

## 🔐 測試帳號

### 一般用戶
```
Email: test@example.com
Password: Test123456!

# 或自行註冊
```

### 管理員
```
Email: admin@mergemeet.com
Password: admin123

⚠️ 注意：生產環境請務必修改預設密碼！
```

---

## 📝 API 文檔

訪問 http://localhost:8000/docs 查看完整的 API 文檔（Swagger UI）

### API 端點總覽

#### 認證 (`/api/auth`)
- POST `/register` - 註冊
- POST `/login` - 登入
- POST `/verify-email` - 驗證 Email
- POST `/refresh` - 刷新 Token
- POST `/logout` - 登出
- POST `/admin-login` - 管理員登入

#### 個人檔案 (`/api/profile`)
- GET `/` - 取得個人檔案
- PUT `/` - 更新個人檔案
- POST `/photos/` - 上傳照片
- DELETE `/photos/{id}/` - 刪除照片
- PUT `/photos/{id}/primary/` - 設定主照片
- GET `/interest-tags/` - 取得興趣標籤
- PUT `/interests/` - 更新興趣

#### 探索與配對 (`/api/discovery`)
- GET `/browse/` - 瀏覽候選人
- POST `/like/{user_id}/` - 喜歡
- POST `/pass/{user_id}/` - 跳過
- GET `/matches/` - 配對列表
- DELETE `/matches/{id}/` - 取消配對

#### 聊天訊息 (`/api/messages`)
- GET `/conversations/` - 對話列表
- GET `/matches/{id}/messages/` - 聊天記錄
- POST `/messages/read/` - 標記已讀
- DELETE `/messages/{id}/` - 刪除訊息

#### WebSocket (`/ws`)
- WebSocket 連接（需要 JWT Token）

#### 安全功能 (`/api/safety`)
- POST `/block/{user_id}` - 封鎖
- DELETE `/block/{user_id}` - 解除封鎖
- GET `/blocked` - 封鎖列表
- POST `/report` - 舉報
- GET `/reports` - 舉報記錄

#### 管理後台 (`/api/admin`)
- GET `/stats` - 統計數據
- GET `/reports` - 舉報列表
- PUT `/reports/{id}` - 處理舉報
- PUT `/users/{id}/ban` - 封禁用戶
- PUT `/users/{id}/unban` - 解封用戶

---

## 🛠️ 開發工具

### 資料庫管理（pgAdmin）

```bash
docker-compose --profile admin up -d pgadmin
open http://localhost:5050

# 登入資訊
Email: admin@admin.com
Password: admin
```

### Redis 管理（RedisInsight - 可選）

```bash
docker run -d --name redisinsight -p 8001:8001 redislabs/redisinsight:latest
open http://localhost:8001
```

### 查看 Docker 日誌

```bash
# 查看所有服務日誌
docker-compose logs -f

# 查看特定服務日誌
docker-compose logs -f postgres
docker-compose logs -f redis
```

---

## 🐛 常見問題與解決方案

### 1. 資料庫連接失敗

**問題:** `could not connect to server`

**解決:**
```bash
# 檢查資料庫狀態
docker-compose ps

# 重啟資料庫
docker-compose restart postgres

# 查看日誌
docker-compose logs postgres
```

### 2. 前端無法連接後端

**問題:** `Network Error` 或 CORS 錯誤

**解決:**
```bash
# 確認後端運行中
curl http://localhost:8000/health

# 檢查 CORS 設定
# 編輯 backend/app/core/config.py
# 確認 CORS_ORIGINS 包含 http://localhost:5173
```

### 3. WebSocket 連接失敗

**問題:** WebSocket 無法連接

**解決:**
- 確認用戶已登入（需要 JWT Token）
- 檢查瀏覽器 Console 錯誤
- 確認後端 WebSocket 端點運行中
- 查看後端日誌

### 4. 照片上傳失敗

**問題:** 上傳照片時出錯

**解決:**
```bash
# 確認 uploads 目錄存在且有寫入權限
mkdir -p backend/uploads
chmod 755 backend/uploads

# 檢查圖片大小（限制 5MB）
# 檢查圖片格式（支援 JPG, PNG, GIF）
```

### 5. 測試失敗

**問題:** `pytest` 執行失敗

**解決:**
```bash
# 確認測試依賴已安裝
pip install -r requirements-test.txt

# 確認測試資料庫配置
# 編輯 backend/.env
# 設定 TEST_DATABASE_URL

# 清理測試快取
pytest --cache-clear
```

---

## 📈 下一步：Week 6 - 測試與部署

### 待完成任務

#### 部署準備
- [ ] 生產環境配置
- [ ] 環境變數管理
- [ ] Docker 生產映像
- [ ] Nginx 反向代理配置

#### 效能優化
- [ ] API 回應時間優化
- [ ] 資料庫查詢優化
- [ ] 前端打包優化
- [ ] Redis 快取實作

#### 安全強化
- [ ] Rate Limiting
- [ ] SQL Injection 防護
- [ ] XSS 防護
- [ ] HTTPS 配置

#### 監控與日誌
- [ ] 應用監控
- [ ] 錯誤追蹤
- [ ] 日誌管理
- [ ] 效能監控

---

## 📚 相關文檔

- [README.md](./README.md) - 專案總覽
- [ARCHITECTURE.md](./ARCHITECTURE.md) - 技術架構
- [docs/INDEX.md](./docs/INDEX.md) - 文檔索引

---

## 🎉 恭喜！

您已完成 MergeMeet 交友平台的核心功能開發（Week 1-5）！

**已實現的功能：**
- ✅ 完整的用戶認證系統
- ✅ 個人檔案與照片管理
- ✅ Tinder 風格的探索與配對
- ✅ 即時聊天功能（WebSocket）
- ✅ 安全功能（封鎖、舉報、內容審核）
- ✅ 管理員後台系統
- ✅ 265+ 個測試案例
- ✅ 完整的 API 文檔

**專案統計：**
- 📝 總程式碼行數：~15,000+ 行
- 🧪 測試案例：70+ 個
- 📊 測試覆蓋率：>80%
- ⏱️ 開發時間：5 週
- 🎯 功能完成度：100%（MVP）

**技術棧：**
- 後端：Python 3.11 + FastAPI + SQLAlchemy 2.0
- 前端：Vue 3 + Vite + Pinia
- 資料庫：PostgreSQL 16 + PostGIS
- 即時通訊：WebSocket
- 測試：pytest + Vue Test Utils

---

**開發愉快！** 🚀
