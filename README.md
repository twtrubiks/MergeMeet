# 🎉 MergeMeet 交友平台

基於 FastAPI + Vue 3 的現代化交友平台 MVP

## 📋 專案資訊

- **版本**: 1.0.0 MVP
- **開發週期**: 6.5 週
- **技術棧**:
  - 後端: Python 3.11+ / FastAPI
  - 前端: Vue 3 / Vite
  - 資料庫: PostgreSQL 16 + PostGIS
  - 快取: Redis 7.x

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
```

## 📊 專案結構

```
mergemeet/
├── backend/                # 後端 FastAPI 應用
│   ├── app/
│   │   ├── api/           # API 路由
│   │   ├── core/          # 核心配置
│   │   ├── models/        # 資料庫模型
│   │   ├── schemas/       # Pydantic Schemas
│   │   ├── services/      # 業務邏輯
│   │   └── main.py        # 主應用
│   ├── tests/             # 測試
│   ├── uploads/           # 檔案上傳
│   └── requirements.txt   # Python 依賴
│
├── frontend/              # 前端 Vue 3 應用
│   ├── src/
│   │   ├── components/    # Vue 組件
│   │   ├── views/         # 頁面
│   │   ├── stores/        # Pinia Stores
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

# 查看資料庫（pgAdmin）
docker-compose --profile admin up -d pgadmin
open http://localhost:5050
```

## 📝 核心功能

### MVP 功能
- ✅ 用戶註冊/登入（Email 驗證）
- ✅ 個人檔案管理（照片、興趣）
- ✅ 配對系統（瀏覽、喜歡、自動配對）
- ✅ 即時聊天（WebSocket）
- ✅ 安全機制（舉報、封鎖）
- ✅ 推薦演算法（興趣 + 地理位置）
- ✅ 管理後台

### 未來擴充（Phase 2）
- ❌ 實名制驗證
- ❌ 視訊通話
- ❌ 付費功能
- ❌ AI 智能配對

## 🎯 開發進度

參考 `MergeMeet_Development_Docs/00_進度追蹤表.md`

## 📚 文檔

完整開發文檔請參考：[MergeMeet_Development_Docs](../MergeMeet_Development_Docs/)

- [專案概述](../MergeMeet_Development_Docs/01_專案概述.md)
- [技術架構](../MergeMeet_Development_Docs/02_技術架構.md)
- [週次開發計畫](../MergeMeet_Development_Docs/04_週次開發計畫.md)
- [後端實作指南](../MergeMeet_Development_Docs/05_後端實作指南_完整版.md)
- [前端實作指南](../MergeMeet_Development_Docs/06_前端實作指南.md)

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

## 📄 授權

本專案為學習與開發用途

## 👥 團隊

- 後端工程師: 1-2 人
- 前端工程師: 1-2 人
- 專案經理: 1 人

---

**開發愉快！** 🚀
