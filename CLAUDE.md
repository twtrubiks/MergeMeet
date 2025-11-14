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

## ⚠️ API Routing 重要規範

### FastAPI 尾隨斜線 (Trailing Slash) 規則

**統一標準**: 本專案所有 API 端點**一律不使用**尾隨斜線，符合 RESTful API 業界標準。

### ✅ 正確的 URL 格式（無尾隨斜線）

```bash
# Profile API
POST   /api/profile                    # 創建個人檔案
GET    /api/profile                    # 獲取個人檔案
PATCH  /api/profile                    # 更新個人檔案
PUT    /api/profile/interests          # 設定興趣標籤
POST   /api/profile/photos             # 上傳照片
DELETE /api/profile/photos/{photo_id}  # 刪除照片
GET    /api/profile/interest-tags      # 獲取興趣標籤列表

# Discovery API
GET    /api/discovery/browse           # 瀏覽候選人
POST   /api/discovery/like/{user_id}   # 喜歡用戶
POST   /api/discovery/pass/{user_id}   # 跳過用戶
GET    /api/discovery/matches          # 查看配對列表

# Messages API
GET    /api/messages/conversations                # 查看對話列表
GET    /api/messages/matches/{match_id}/messages  # 查看聊天記錄
POST   /api/messages/messages/read                # 標記訊息為已讀
DELETE /api/messages/messages/{message_id}        # 刪除訊息

# Safety API
POST   /api/safety/block/{user_id}     # 封鎖用戶
GET    /api/safety/blocked             # 查看封鎖列表
POST   /api/safety/report              # 舉報用戶

# Auth API
POST   /api/auth/register              # 用戶註冊
POST   /api/auth/login                 # 用戶登入
POST   /api/auth/refresh               # 刷新 Token
```

### ❌ 錯誤示例（加了尾隨斜線會導致 404 錯誤）

```bash
# 所有端點都不應該有尾隨斜線
POST /api/profile/                     → 404 Not Found ❌
GET  /api/discovery/browse/            → 404 Not Found ❌
POST /api/discovery/like/{user_id}/    → 404 Not Found ❌
GET  /api/messages/conversations/      → 404 Not Found ❌
```

**註**: FastAPI 已配置 `redirect_slashes=False`，因此帶斜線的請求直接返回 404，不會重定向。

### FastAPI Router 定義規範

所有 router 定義統一**不使用**尾隨斜線：
```python
# ✅ 正確 - 所有端點都不使用尾隨斜線
@router.post("", ...)                      # POST /api/profile
@router.get("", ...)                       # GET /api/profile
@router.put("/interests", ...)             # PUT /api/profile/interests
@router.get("/browse", ...)                # GET /api/discovery/browse
@router.post("/like/{user_id}", ...)       # POST /api/discovery/like/{id}

# ❌ 錯誤 - 不要使用尾隨斜線
@router.post("/", ...)                     # 會導致前端 404 錯誤
@router.put("/interests/", ...)            # 會導致前端 404 錯誤
```

### FastAPI 配置

在 `backend/app/main.py` 中，已配置 FastAPI 禁用自動重定向：

```python
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    redirect_slashes=False,  # 禁用自動重定向
)
```

這確保了：
- ✅ 不帶斜線的 URL 正常工作 (HTTP 200)
- ✅ 帶斜線的 URL 直接返回 404 (不會重定向)
- ✅ 避免 Authorization Header 在重定向中丟失

### 測試時注意事項

1. **curl 測試**時務必檢查 HTTP status code
   ```bash
   curl -w "\nHTTP: %{http_code}\n" -X GET "..."
   # HTTP: 200 ✅ 正確
   # HTTP: 404 ❌ URL 格式錯誤（有尾隨斜線）
   ```

2. **前端 axios** 請求時，確保**所有 URL 都不使用尾隨斜線**
   ```javascript
   // ✅ 正確 - 無尾隨斜線
   await axios.get('/api/profile')
   await axios.post('/api/profile', data)
   await axios.put('/api/profile/interests', data)
   await axios.get('/api/discovery/browse')
   await axios.post(`/api/discovery/like/${userId}`)
   await axios.get('/api/messages/conversations')

   // ❌ 錯誤 - 加了尾隨斜線會返回 404
   await axios.get('/api/profile/')
   await axios.put('/api/profile/interests/', data)
   await axios.post(`/api/discovery/like/${userId}/`)
   ```

3. **測試腳本**中的所有 API 呼叫都必須遵守**無尾隨斜線**規則

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
