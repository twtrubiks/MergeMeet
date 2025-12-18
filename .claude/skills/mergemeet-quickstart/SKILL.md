---
name: mergemeet-quickstart
description: 設定 MergeMeet 開發環境、執行服務、排除故障或學習開發流程時使用此 skill。涵蓋 Docker、FastAPI、Vue 3、PostgreSQL、Redis、測試和常用指令。
---

# MergeMeet 快速入門指南

## 目的

提供 MergeMeet 專案的完整開發流程指南，包含環境設定、常用指令和故障排除。

---

## 快速開始（3 步驟）

### 步驟 1：啟動基礎設施

```bash
# 啟動 PostgreSQL 和 Redis
docker compose up -d

# 驗證服務
docker compose ps
# 預期結果: mergemeet-db (Up), mergemeet-redis (Up)
```

### 步驟 2：啟動後端

```bash
cd backend

# 安裝依賴（首次）
pip install -r requirements.txt

# 啟動 FastAPI
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API 文件: http://localhost:8000/docs

### 步驟 3：啟動前端

```bash
cd frontend

# 安裝依賴（首次）
npm install

# 啟動開發伺服器
npm run dev
```

應用程式: http://localhost:5173/

---

## 常用指令

### 資料庫

```bash
# 連接到 PostgreSQL
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet

# 常用 SQL 指令
\dt                    # 列出資料表
\d+ users              # 描述資料表
\q                     # 退出
```

### 資料庫遷移（Alembic）

```bash
cd backend

alembic revision --autogenerate -m "Add new field"
alembic upgrade head
alembic downgrade -1
alembic history
```

### 測試

```bash
cd backend

pytest                           # 執行所有測試
pytest -v                        # 詳細輸出
pytest --cov=app                 # 含覆蓋率
pytest tests/test_profile.py    # 特定檔案
```

### Docker

```bash
docker compose ps                # 狀態
docker compose logs -f postgres  # 追蹤日誌
docker compose down              # 停止
docker compose down -v           # 停止並移除資料卷
```

---

## 故障排除

### 後端無法啟動

**錯誤**: `sqlalchemy.exc.OperationalError: could not connect to server`

```bash
# 檢查資料庫是否運行
docker compose ps

# 重啟資料庫
docker compose restart postgres

# 測試連接
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet -c "SELECT 1;"
```

### 前端無法連接後端

**錯誤**: `Network Error` 或 `CORS Error`

```bash
# 驗證後端是否運行
curl http://localhost:8000/health

# 檢查 backend/app/core/config.py 中的 CORS 設定
# 確保 CORS_ORIGINS 包含 "http://localhost:5173"
```

### API 返回 404

**最常見原因**: URL 有尾隨斜線

```python
# 錯誤
@router.get("/")           # 404

# 正確
@router.get("")
```

```javascript
// 錯誤
await axios.get('/api/profile/')   // 404

// 正確
await axios.get('/api/profile')
```

詳細資訊請參考 **api-routing-standards** skill。

---

## 參考資料

詳細資訊請參考：

| 主題 | 檔案 |
|------|------|
| 所有指令 | [commands.md](references/commands.md) |
| 故障排除 | [troubleshooting.md](references/troubleshooting.md) |
| 開發工具 | [tools.md](references/tools.md) |
| Git 工作流程 | [workflows.md](references/workflows.md) |

---

## 相關 Skills

- **api-routing-standards** - API 路由規則
- **backend-dev-fastapi** - 後端開發
- **frontend-dev-vue3** - 前端開發
- **project-audit** - 專案健康檢查
