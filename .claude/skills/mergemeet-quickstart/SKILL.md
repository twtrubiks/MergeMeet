---
name: mergemeet-quickstart
description: MergeMeet 專案完整開發指南，包含啟動流程、常用指令、故障排除、工具使用（Context7、Chrome DevTools）、Git 規範、測試流程。涵蓋 FastAPI、Vue 3、PostgreSQL、PostGIS、Redis、Docker 等技術棧的開發實踐。
---

# MergeMeet 快速開發指南

## 📋 目的

提供 MergeMeet 專案的完整開發流程指南，包含環境設定、開發工作流、常用工具、故障排除等。

---

## 📚 何時使用此 Skill

**自動觸發**：
- 提到「啟動」、「開發流程」、「設定環境」
- 查詢「如何」開發、測試、部署
- 故障排除相關問題

**手動使用**：
```bash
使用 Skill: mergemeet-quickstart
```

---

## 🚀 快速啟動流程

### Step 1: 啟動基礎服務

```bash
# 啟動 PostgreSQL 和 Redis
docker compose up -d

# 檢查服務狀態
docker compose ps

# 預期輸出
# NAME                 IMAGE                 STATUS
# mergemeet-db         postgis/postgis       Up
# mergemeet-redis      redis:alpine          Up
```

### Step 2: 啟動後端服務

```bash
cd backend

# 安裝依賴（首次）
pip install -r requirements.txt

# 啟動 FastAPI
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# ✅ 成功訊息
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
```

**後端 API 文檔**: http://localhost:8000/docs

### Step 3: 啟動前端服務

```bash
cd frontend

# 安裝依賴（首次）
npm install

# 啟動開發伺服器
npm run dev

# ✅ 成功訊息
# VITE ready in 500ms
# ➜  Local:   http://localhost:5173/
```

**前端應用**: http://localhost:5173/

### Step 4: 驗證環境

```bash
# 1. 檢查後端健康狀態
curl http://localhost:8000/health

# 2. 檢查資料庫連接
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet -c "\dt"

# 3. 在瀏覽器打開前端，檢查 Console 無錯誤
```

---

## 🔧 常用指令

### 資料庫操作

```bash
# 進入 PostgreSQL 容器
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet

# 常用 SQL 指令
\dt                          # 查看所有資料表
\d+ users                    # 查看 users 表結構
\l                           # 查看所有資料庫
\q                           # 退出

# 查詢範例
SELECT * FROM users LIMIT 5;
SELECT COUNT(*) FROM matches;

# 執行 SQL 檔案
docker exec -i mergemeet-db psql -U mergemeet -d mergemeet < script.sql
```

### 資料庫遷移 (Alembic)

```bash
cd backend

# 生成新遷移
alembic revision --autogenerate -m "Add new field"

# 執行遷移
alembic upgrade head

# 回退遷移
alembic downgrade -1

# 查看遷移歷史
alembic history

# 查看當前版本
alembic current
```

### 測試指令

```bash
# 後端測試
cd backend

# 執行所有測試
pytest

# 詳細輸出
pytest -v

# 測試覆蓋率
pytest --cov=app --cov-report=html

# 測試特定檔案
pytest tests/test_profile.py

# 測試特定函數
pytest tests/test_profile.py::test_get_profile

# 前端測試（若有配置）
cd frontend
npm run test
npm run test:coverage
```

### Docker 操作

```bash
# 查看容器狀態
docker compose ps

# 查看容器日誌
docker compose logs postgres
docker compose logs redis
docker compose logs -f postgres  # 持續追蹤

# 停止服務
docker compose stop

# 停止並刪除容器
docker compose down

# 完全清理（包含資料卷）
docker compose down -v

# 重建容器
docker compose up -d --build

# 進入容器 shell
docker exec -it mergemeet-db bash
docker exec -it mergemeet-redis redis-cli
```

### Git 操作

```bash
# 查看狀態
git status

# 創建功能分支
git checkout -b feature/user-profile

# 提交變更
git add .
git commit -m "feat: 新增個人檔案照片上傳功能"

# 推送分支
git push origin feature/user-profile

# 切回主分支
git checkout main

# 更新本地分支
git pull origin main
```

**完整 Git 規範**: 見 [workflows.md](resources/workflows.md)

---

## 🐛 故障排除

### 後端無法啟動

**問題**: `sqlalchemy.exc.OperationalError: could not connect to server`

**解決方法**:
```bash
# 1. 檢查資料庫是否運行
docker compose ps

# 2. 重啟資料庫
docker compose restart postgres

# 3. 檢查環境變數
cat backend/.env

# 4. 測試連接
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet -c "SELECT 1;"
```

### 前端無法連接後端

**問題**: `Network Error` 或 `CORS Error`

**解決方法**:
```bash
# 1. 確認後端運行
curl http://localhost:8000/health

# 2. 檢查 CORS 設定
# 編輯 backend/app/core/config.py
# 確認 CORS_ORIGINS 包含 "http://localhost:5173"

# 3. 檢查前端 API URL
# 編輯 frontend/src/config.js
# 確認 API_BASE_URL = "http://localhost:8000"

# 4. 清除瀏覽器快取並重新載入
```

### API 返回 404 錯誤

**問題**: `404 Not Found` 儘管路由已定義

**最常見原因**: ⚠️ **URL 有尾隨斜線**

**解決方法**:
```python
# ❌ 錯誤 - 後端使用斜線
@router.get("/")
@router.post("/interests/")

# ✅ 正確 - 無斜線
@router.get("")
@router.post("/interests")
```

```javascript
// ❌ 錯誤 - 前端使用斜線
await axios.get('/api/profile/')

// ✅ 正確 - 無斜線
await axios.get('/api/profile')
```

**詳細檢查**:
1. 使用 Swagger UI: http://localhost:8000/docs
2. 確認路由定義無尾隨斜線
3. 確認前端請求無尾隨斜線
4. 查看 **Skill: api-routing-standards**

### WebSocket 連接失敗

**問題**: WebSocket 無法連接或頻繁斷線

**解決方法**:
```bash
# 1. 確認後端 WebSocket 端點
curl -i -N -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  http://localhost:8000/ws

# 2. 檢查瀏覽器 Console
# 應該看到 "WebSocket connection established"

# 3. 確認用戶已登入（需要 JWT Token）

# 4. 檢查後端日誌
# 查找 WebSocket 相關錯誤訊息
```

### 資料庫連接池耗盡

**問題**: `TimeoutError: QueuePool limit exceeded`

**解決方法**:
```python
# 編輯 backend/app/core/database.py
# 增加連接池大小
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,        # 從 5 增加到 20
    max_overflow=40,     # 從 10 增加到 40
    pool_pre_ping=True,
)
```

**更多故障排除**: 見 [troubleshooting.md](resources/troubleshooting.md)

---

## 🔍 開發工具

### Context7 MCP - 查詢官方文檔

**用途**: 即時查詢 FastAPI、Vue 3、Pinia 等官方文檔

**使用方法**:
```bash
# 1. 解析 library ID
context7: resolve-library-id "fastapi"

# 2. 查詢文檔
context7: get-library-docs "/fastapi" topic="routing"
context7: get-library-docs "/fastapi" topic="async" mode="code"

# 常用 library IDs
/fastapi                  # FastAPI
/vuejs/core              # Vue 3
/vuejs/pinia             # Pinia
/sqlalchemy              # SQLAlchemy
/pydantic                # Pydantic
```

**常用查詢主題**:
- FastAPI: `"routing"`, `"dependencies"`, `"websocket"`, `"testing"`
- Vue 3: `"composition api"`, `"reactivity"`, `"lifecycle"`
- Pinia: `"state"`, `"actions"`, `"getters"`
- SQLAlchemy: `"async orm"`, `"relationships"`, `"queries"`

**Mode 選項**:
- `mode="code"` - 程式碼範例（預設）
- `mode="info"` - 概念性文檔

### Chrome DevTools MCP - 前端測試

**用途**: 測試前端功能、檢查錯誤、驗證 API 請求

**測試流程**:
1. 打開前端應用: http://localhost:5173
2. 開啟 Chrome DevTools (F12)
3. 執行以下檢查：

**Console 檢查**:
```javascript
// 檢查是否有錯誤
// ❌ 紅色錯誤訊息 → 需要修復
// ✅ 無錯誤 → 正常

// 檢查 API 請求
console.log('Testing API...')
```

**Network 檢查**:
- 確認 API 請求 URL **無尾隨斜線**
- 檢查狀態碼: 200 (成功), 404 (錯誤)
- 查看請求/回應 payload
- 確認 Authorization header

**Application 檢查**:
- LocalStorage: 檢查 JWT Token
- Cookies: 檢查 session
- Service Workers: 檢查註冊狀態

**Vue DevTools**:
- 檢查 Pinia stores 狀態
- 查看組件層級結構
- 追蹤 events

**完整工具指南**: 見 [tools.md](resources/tools.md)

---

## 💡 開發建議

### Git Commit 規範

使用語義化提交訊息（中文或英文）:

```bash
feat: 新增個人檔案照片上傳功能
fix: 修復配對演算法計算錯誤
refactor: 重構 WebSocket 連接管理器
test: 新增內容審核測試案例
docs: 更新 API 文檔
style: 格式化程式碼
chore: 更新依賴版本
```

### 開發流程

1. **開始新功能前** - 查看相關 Skill
   ```bash
   使用 Skill: backend-dev-fastapi
   使用 Skill: frontend-dev-vue3
   ```

2. **編寫程式碼時** - Skills 會自動觸發提供指引
   - 編輯 API 路由 → `api-routing-standards` 強制觸發
   - 編輯後端 → `backend-dev-fastapi` 建議
   - 編輯前端 → `frontend-dev-vue3` 建議

3. **完成功能後** - 執行測試確保覆蓋率
   ```bash
   pytest --cov=app --cov-report=term-missing
   ```

4. **提交前檢查**
   - [ ] API URL 無尾隨斜線
   - [ ] 測試通過
   - [ ] 覆蓋率 >80%
   - [ ] 無 ESLint 錯誤
   - [ ] Console 無錯誤

### TDD 開發流程

```bash
# 1. 先寫測試
def test_create_user():
    response = client.post("/api/users", json=user_data)
    assert response.status_code == 201

# 2. 執行測試（會失敗）
pytest tests/test_users.py::test_create_user

# 3. 寫程式碼直到測試通過
@router.post("")
async def create_user(...):
    # 實作...
    return user

# 4. 重構
# 改進程式碼品質但保持測試通過
```

---

## 📖 資源檔案導覽

| 需要... | 閱讀此檔案 |
|--------|----------|
| 完整常用指令清單 | [commands.md](resources/commands.md) |
| 詳細故障排除步驟 | [troubleshooting.md](resources/troubleshooting.md) |
| Context7 & DevTools 使用 | [tools.md](resources/tools.md) |
| Git & 測試工作流程 | [workflows.md](resources/workflows.md) |

---

## 🔗 相關 Skills

- **api-routing-standards** - API 路由規範（最重要）
- **backend-dev-fastapi** - FastAPI 開發完整指南
- **frontend-dev-vue3** - Vue 3 開發完整指南
- **database-planning** - 資料庫設計標準
- **testing-guide** - 測試策略與 TDD
- **product-management** - 產品需求管理

---

## 📝 核心原則

1. 🚨 **API URL 無尾隨斜線** - 所有端點不使用 `/` 結尾
2. 🎓 **使用 Skills 系統** - 開發時參考相關 Skill
3. ⚡ **Async 優先** - 後端使用 async/await
4. 🧩 **Composition API** - 前端使用 `<script setup>`
5. 🧪 **測試驅動** - TDD 開發流程，覆蓋率 >80%
6. 📚 **查詢文檔** - 使用 Context7 MCP
7. 🔍 **前端測試** - 使用 Chrome DevTools MCP

---

**Skill 狀態**: ✅ COMPLETE
**強制等級**: 💡 SUGGEST (Domain)
**優先級**: HIGH
**行數**: < 500 行 ✅
