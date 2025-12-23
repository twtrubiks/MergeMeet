# 🎉 MergeMeet 交友平台

基於 FastAPI + Vue 3 的現代化交友平台 MVP

## 📋 專案資訊

- **版本**: 1.0.0 MVP
- **開發進度**: ✅ Week 1-6 已完成
- **技術棧**:
  - 後端: Python 3.11+ / FastAPI / SQLAlchemy 2.0 Async
  - 前端: Vue 3 / Vite / Pinia
  - 資料庫: PostgreSQL 16 + PostGIS
  - 快取: Redis 7.x
  - 即時通訊: WebSocket

## 🚀 快速開始

### 前置需求

- Docker & Docker Compose
- Python 3.11+
- Node.js 20+

### 一鍵設置

```bash
# 1. 設置開發環境
./scripts/setup.sh

# 2. 啟動開發伺服器
./scripts/dev.sh

# 3. 訪問應用
# 前端: http://localhost:5173
# 後端: http://localhost:8000
# API 文檔: http://localhost:8000/docs
```

### 手動設置

#### 1. 啟動資料庫服務

```bash
docker-compose up -d postgres redis
```

#### 2. 設置後端

```bash
cd backend

# 建立虛擬環境
python3 -m venv venv
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt
pip install -r requirements-test.txt

# 複製環境變數
cp .env.example .env

# 啟動後端
uvicorn app.main:app --reload
```

#### 3. 設置前端

```bash
cd frontend

# 安裝依賴
npm install

# 啟動前端
npm run dev
```

## 🧪 測試

```bash
# 執行所有測試
./scripts/test.sh

# 或手動執行
cd backend
pytest -v --cov=app

# 測試統計
# - 總測試數: 287+ 個
# - 覆蓋率: >80%
```

## 📊 專案結構

```
mergemeet/
├── backend/                # 後端 FastAPI 應用
│   ├── app/
│   │   ├── api/           # API 路由 (9 個模組)
│   │   │   ├── auth.py           # 認證系統 (註冊/登入/JWT)
│   │   │   ├── profile.py        # 個人檔案管理
│   │   │   ├── discovery.py      # 探索與配對
│   │   │   ├── messages.py       # 聊天訊息 REST API
│   │   │   ├── websocket.py      # WebSocket 即時聊天
│   │   │   ├── safety.py         # 安全功能 (封鎖/舉報)
│   │   │   ├── admin.py          # 管理後台
│   │   │   ├── moderation.py     # 內容審核
│   │   │   └── notifications.py  # 通知系統
│   │   ├── core/          # 核心配置
│   │   ├── models/        # 資料庫模型 (9 個模型)
│   │   │   ├── user.py           # User, trust_score
│   │   │   ├── profile.py        # Profile, Photo, InterestTag
│   │   │   ├── match.py          # Like, Match, Message, BlockedUser
│   │   │   ├── report.py         # Report (舉報記錄)
│   │   │   └── notification.py   # Notification (通知記錄)
│   │   ├── schemas/       # Pydantic Schemas
│   │   ├── services/      # 業務邏輯
│   │   │   ├── content_moderation.py  # 內容審核
│   │   │   ├── trust_score.py         # 信任分數系統
│   │   │   ├── matching_service.py    # 配對算法
│   │   │   └── login_limiter.py       # 登入限制
│   │   ├── websocket/     # WebSocket 管理
│   │   │   └── manager.py        # 連接管理器
│   │   └── main.py        # 主應用
│   ├── tests/             # 測試 (265+ 個測試案例)
│   ├── uploads/           # 檔案上傳
│   └── requirements.txt   # Python 依賴
│
├── frontend/              # 前端 Vue 3 應用
│   ├── src/
│   │   ├── components/    # Vue 組件 (16 個)
│   │   │   ├── chat/
│   │   │   │   ├── MessageBubble.vue
│   │   │   │   ├── ChatImagePicker.vue
│   │   │   │   └── ImagePreviewModal.vue
│   │   │   ├── ui/
│   │   │   │   ├── AnimatedButton.vue
│   │   │   │   ├── FloatingInput.vue
│   │   │   │   ├── HeartLoader.vue
│   │   │   │   ├── GlassCard.vue
│   │   │   │   ├── Badge.vue
│   │   │   │   └── FeatureCard.vue
│   │   │   ├── layout/NavBar.vue
│   │   │   ├── InterestSelector.vue
│   │   │   ├── NotificationBell.vue
│   │   │   ├── PhotoUploader.vue
│   │   │   ├── UserDetailModal.vue
│   │   │   ├── MatchModal.vue
│   │   │   └── ReportModal.vue
│   │   ├── views/         # 頁面 (13 個頁面)
│   │   │   ├── Register.vue      # 註冊頁面
│   │   │   ├── Login.vue         # 登入頁面
│   │   │   ├── ForgotPassword.vue # 忘記密碼
│   │   │   ├── ResetPassword.vue  # 重置密碼
│   │   │   ├── Home.vue          # 首頁
│   │   │   ├── Profile.vue       # 個人檔案
│   │   │   ├── Discovery.vue     # 探索配對 (含舉報按鈕)
│   │   │   ├── Matches.vue       # 配對列表
│   │   │   ├── ChatList.vue      # 聊天列表
│   │   │   ├── Chat.vue          # 即時聊天
│   │   │   ├── Blocked.vue       # 封鎖列表
│   │   │   └── admin/
│   │   │       ├── AdminLogin.vue     # 管理員登入
│   │   │       └── AdminDashboard.vue # 管理員儀表板
│   │   ├── stores/        # Pinia Stores (7 個)
│   │   │   ├── auth.js           # 認證狀態
│   │   │   ├── profile.js        # 個人檔案狀態
│   │   │   ├── discovery.js      # 探索配對狀態
│   │   │   ├── match.js          # 配對狀態
│   │   │   ├── chat.js           # 聊天狀態
│   │   │   ├── safety.js         # 安全功能狀態
│   │   │   └── user.js           # 用戶狀態
│   │   ├── composables/   # Vue Composables
│   │   │   └── useWebSocket.js   # WebSocket 連接管理
│   │   ├── router/        # Vue Router
│   │   └── api/           # API 客戶端
│   └── package.json       # Node.js 依賴
│
├── scripts/               # 工具腳本
│   ├── setup.sh          # 環境設置
│   ├── dev.sh            # 啟動開發
│   ├── test.sh           # 執行測試
│   └── check.sh          # 狀態檢查
│
└── docker-compose.yml     # Docker 配置
```

## 🔧 開發工具

```bash
# 檢查服務狀態
./scripts/check.sh

# 查看 API 文檔
open http://localhost:8000/docs

# 查看 Mailpit Email 測試工具
open http://localhost:8025
# 可查看所有發送的郵件（註冊驗證碼、密碼重置連結等）

# 查看資料庫（pgAdmin）
docker-compose --profile admin up -d pgadmin
open http://localhost:5050
```

## 📝 核心功能

### ✅ Week 1: 認證系統
- 用戶註冊（Email + 密碼）
- 用戶登入（JWT Token）
- Email 驗證（Mailpit 真實郵件發送）
- 密碼重置功能（忘記密碼 / 重設密碼）
- 登入失敗次數限制（5 次失敗後鎖定 15 分鐘，使用 Redis）
- Token 刷新機制
- 管理員登入（is_admin 權限檢查）

### ✅ Week 2: 個人檔案
- 個人資料管理（姓名、生日、性別、bio）
- 照片上傳（最多 6 張，含主照片，單檔限制 5MB）
- 照片審核申訴功能（被拒照片可提出申訴）
- 興趣標籤選擇（多選）
- 地理位置設定（經緯度）
- 配對偏好設定（年齡範圍、最大距離、性別偏好）
- 檔案上傳服務（圖片壓縮）

### ✅ Week 3: 探索與配對
- 探索頁面（Tinder 風格卡片）
- 用戶詳情查看（點擊卡片查看完整資料）
- 喜歡/跳過功能（滑動手勢）
- 雙向喜歡自動配對
- 配對演算法（5 維度：興趣 50 分 + 距離 20 分 + 活躍度 20 分 + 完整度 5 分 + 信任分數 5 分）
- 配對列表頁面
- 配對分數計算（0-100 分）

### ✅ Week 4: 即時聊天
- WebSocket 連接管理
- 即時訊息發送/接收
- 訊息內容審核與錯誤提示（敏感詞攔截、警告通知）
- 圖片/GIF 訊息（上傳、縮圖、預覽）
- 打字指示器（Typing Indicator）
- 已讀回條（Read Receipts）
- 聊天記錄分頁載入
- 對話列表（最後訊息預覽）
- 未讀訊息計數
- 訊息軟刪除
- 自動重連機制

### ✅ Week 5: 安全功能與管理後台

#### 安全功能
- **封鎖系統**
  - 封鎖/解除封鎖用戶
  - 封鎖自動取消配對
  - 封鎖列表頁面
  - 被封鎖用戶不出現在探索頁面

- **舉報系統**
  - 5 種舉報類型（不當內容、騷擾、假帳號、詐騙、其他）
  - 舉報原因必填（至少 10 字）
  - 證據說明（選填）
  - 舉報自動增加被舉報用戶警告次數
  - 我的舉報記錄頁面（/my-reports，查看自己提交的所有舉報）

- **內容審核**
  - 敏感詞檢測（色情、詐騙、暴力、騷擾等）
  - 可疑模式檢測（電話、URL、LINE ID、金額等）
  - 自動過濾不當內容
  - 違規自動增加警告次數
  - 動態敏感詞管理

- **信任分數系統**（2025-12-14 新增）
  - 自動分數調整（正向：Email 驗證 +5、被喜歡 +1、配對 +2）
  - 自動分數懲罰（負向：被舉報 -5、違規內容 -3、被封鎖 -2）
  - 配對算法整合（5 分權重，影響排序）
  - 低信任用戶限制（< 20 分每日訊息上限 20 則）
  - 分數範圍：0-100（預設 50）

#### 管理後台
- **統計儀表板**
  - 用戶統計（總數、今日新增、活躍用戶）
  - 配對統計（總配對數、配對率）
  - 訊息統計（總訊息數、今日訊息）
  - 舉報統計（待處理、已處理、總數）

- **舉報管理**
  - 查看所有舉報
  - 舉報狀態篩選（待處理/審核中/已處理/已駁回）
  - 舉報詳情查看（舉報人、被舉報人、原因、證據）
  - 處理操作（批准、拒絕、警告、封禁用戶）

- **用戶管理**
  - 用戶列表
  - Email 搜尋與狀態篩選（精準查找用戶）
  - 封禁/解封用戶（支援設定封禁天數與原因）
  - 查看用戶警告次數
  - 查看用戶信任分數

### ✅ Week 6: 通知系統與 UI 優化

#### 通知中心
- **通知中心頁面** (/notifications)
  - 完整通知歷史列表
  - 通知類型：新訊息、新配對、系統通知
  - 未讀/已讀狀態管理
  - 個別刪除通知功能
- **通知下拉選單**（導航欄鈴鐺圖標）
  - 顯示最近通知
  - 未讀數量角標
  - 快速跳轉至通知中心

#### UI/UX 優化
- 配對偏好設定 UI（設定頁面）
  - 年齡範圍滑桿（18-99 歲）
  - 最大距離滑桿（1-500 公里）
  - 性別偏好選擇器（四種選項）
- 用戶詳情查看模態框（探索頁面）
- 照片審核申訴界面（被拒照片可申訴）
- 訊息內容審核錯誤提示（敏感詞攔截警告）

## 🎯 技術亮點

### 後端
- ✅ FastAPI 異步框架
- ✅ SQLAlchemy 2.0 Async ORM
- ✅ JWT 認證 + Refresh Token
- ✅ Email 服務整合（Mailpit 開發環境 / SendGrid 生產環境）
- ✅ 密碼重置功能（Token 一次性使用、30分鐘有效期）
- ✅ WebSocket 即時通訊
- ✅ PostGIS 地理位置查詢
- ✅ Redis 快取（未來擴充）
- ✅ 內容審核系統
- ✅ 測試覆蓋率 >80%

### 前端
- ✅ Vue 3 Composition API
- ✅ Pinia 狀態管理
- ✅ Vue Router 路由守衛
- ✅ Axios 攔截器
- ✅ WebSocket Composable
- ✅ 響應式設計（RWD）
- ✅ 滑動手勢支援
- ✅ 載入狀態與錯誤處理

### DevOps
- ✅ Docker Compose（PostgreSQL + Redis + Mailpit）
- ✅ Mailpit Email 測試工具（開發環境）
- ✅ 一鍵設置腳本
- ✅ 自動化測試
- ✅ API 文檔自動生成（Swagger）

## 📈 測試統計

```bash
# 測試案例分佈
- Week 1 (認證): 21+ 個測試（含登入限制 9 個）
- Week 2 (個人檔案): 15+ 個測試
- Week 3 (探索配對): 10+ 個測試
- Week 4 (即時聊天): 8+ 個測試
- Week 5 (安全功能): 47+ 個測試
  - 封鎖/舉報: 13 個
  - 內容審核: 34 個
- Week 6 (通知持久化): 17 個測試
- 信任分數系統: 22 個測試（2025-12-14 新增）

總計: 287+ 個測試案例
覆蓋率: >80%
```

## 🔮 未來擴充（Phase 2）

- ❌ 實名制驗證（身份證、駕照）
- ❌ 視訊通話（WebRTC）
- ❌ 付費功能（VIP、Super Like）
- ❌ AI 智能配對（機器學習）
- ❌ 推播通知（FCM）
- ❌ 社群動態（限時動態）
- ❌ 活動配對（線下活動）

## 🎯 開發進度

| Week | 功能 | 狀態 |
|------|------|------|
| Week 0.5 | 環境設置 | ✅ 完成 |
| Week 1 | 認證系統 | ✅ 完成 |
| Week 2 | 個人檔案 | ✅ 完成 |
| Week 3 | 探索與配對 | ✅ 完成 |
| Week 4 | 即時聊天 | ✅ 完成 |
| Week 5 | 安全功能與管理後台 | ✅ 完成 |
| Week 6 | 通知系統與 UI 優化 | ✅ 完成 |

## 📚 文檔

完整開發文檔請參考專案內文件：

- [README.md](./README.md) - 專案總覽
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) - 技術架構
- [docs/INDEX.md](./docs/INDEX.md) - 文檔索引

## 🐛 故障排除

### 後端啟動失敗
- 確認資料庫服務已啟動：`docker-compose ps`
- 檢查環境變數：確認 `.env` 檔案存在
- 查看日誌：`docker-compose logs postgres`

### 前端無法連接後端
- 確認後端已啟動：`curl http://localhost:8000/health`
- 檢查 CORS 設定：確認 `backend/app/core/config.py` 中的 CORS 設定

### 資料庫連接失敗
- 重啟資料庫：`docker-compose restart postgres`
- 檢查連接字串：確認 `.env` 中的 `DATABASE_URL`

### WebSocket 連接失敗
- 確認後端 WebSocket 端點運行中
- 檢查瀏覽器 Console 錯誤
- 確認用戶已登入（需要 JWT Token）

## 🔐 預設管理員帳號

```
Email: admin@mergemeet.com
Password: admin123

注意：生產環境請務必修改預設密碼！
```

## 📄 授權

本專案為學習與開發用途

## 👥 貢獻者

- **專案架構**: Claude (Anthropic AI)
- **後端開發**: twtrubiks + Claude
- **前端開發**: twtrubiks + Claude
- **安全功能**: Claude
- **測試**: Claude + twtrubiks

---

**開發愉快！** 🚀

## 📌 相關連結

- [FastAPI 文檔](https://fastapi.tiangolo.com/)
- [Vue 3 文檔](https://vuejs.org/)
- [Pinia 文檔](https://pinia.vuejs.org/)
- [SQLAlchemy 文檔](https://www.sqlalchemy.org/)
