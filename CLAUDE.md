# MergeMeet 開發指南

## 項目簡介
MergeMeet 是一個基於地理位置的社交配對應用，採用 FastAPI + Vue 3 架構開發。

## 技術棧
- **後端**: FastAPI + SQLAlchemy + PostgreSQL + PostGIS + Redis
- **前端**: Vue 3 + Vite + Pinia + Vue Router
- **認證**: JWT Token
- **即時通訊**: WebSocket（規劃中）

## 環境要求
- Python 3.11+ (參考 `/backend/.python-version`)
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+ (含 PostGIS 擴展)
- Redis 7+

## 快速啟動

### 1. 啟動基礎服務
```bash
# 啟動 PostgreSQL 和 Redis
docker compose up -d
```

### 2. 啟動後端
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

後端 API 文檔: http://localhost:8000/docs

### 3. 啟動前端
```bash
cd frontend
npm run dev
```

前端應用: http://localhost:5173/

### API 測試
```bash
# 使用 Swagger UI
http://localhost:8000/docs

# 或使用 pytest
cd backend
pytest tests/
```

## 目錄結構
```
mergemeet/
├── backend/                 # FastAPI 後端
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # SQLAlchemy 模型
│   │   ├── schemas/        # Pydantic schemas
│   │   └── services/       # 業務邏輯
│   └── tests/              # 後端測試
├── frontend/                # Vue 3 前端
│   ├── src/
│   │   ├── components/     # Vue 組件
│   │   ├── views/          # 頁面視圖
│   │   ├── stores/         # Pinia stores
│   │   └── router/         # 路由配置
└── docker-compose.yml       # Docker 配置

```

## 常用指令

### 資料庫操作
```bash
# 進入 PostgreSQL 容器
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet

# 查看資料庫
\dt
\d+ users
```

### 清理與重置
```bash
# 停止並清理容器
docker compose down -v

# 重建資料庫
docker compose up -d
cd backend
alembic upgrade head
```

## 開發建議

### Git Commit 規範
使用語義化提交訊息（中文）:
- `feat: 新增功能描述`
- `fix: 修復問題描述`
- `refactor: 重構代碼描述`
- `test: 測試相關描述`
- `docs: 文檔更新描述`

## 相關文件
- `README.md`: 項目總覽
- `QUICKSTART.md`: 快速開始指南
- `MergeMeet_Development_Docs/`: 詳細開發文檔
- `00_進度追蹤表.md`: 週進度追蹤

## 問題回報
如遇到問題，請提供以下資訊:
1. 錯誤訊息或截圖
2. 復現步驟
3. 瀏覽器開發者工具的 Console 和 Network 日誌
4. 後端 uvicorn 的終端輸出
