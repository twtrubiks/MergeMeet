# 完整指令參考

## 目錄

- [Docker 相關](#docker-相關)
- [資料庫操作](#資料庫操作)
- [後端開發](#後端開發)
- [前端開發](#前端開發)
- [測試相關](#測試相關)
- [Git 操作](#git-操作)

---

## Docker 相關

### 基本操作

```bash
# 啟動所有服務
docker compose up -d

# 停止所有服務
docker compose stop

# 停止並刪除容器
docker compose down

# 完全清理（包含資料卷）⚠️
docker compose down -v

# 查看容器狀態
docker compose ps

# 查看容器日誌
docker compose logs postgres
docker compose logs redis
docker compose logs -f postgres  # 持續追蹤

# 重啟特定服務
docker compose restart postgres
docker compose restart redis

# 重建容器
docker compose up -d --build
```

### 進入容器

```bash
# 進入 PostgreSQL 容器
docker exec -it mergemeet-db bash
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet

# 進入 Redis 容器
docker exec -it mergemeet-redis redis-cli
docker exec -it mergemeet-redis sh
```

### 檢查資源使用

```bash
# 查看容器資源使用
docker stats

# 查看容器詳細資訊
docker inspect mergemeet-db

# 查看容器網路
docker network ls
docker network inspect mergemeet_default
```

---

## 資料庫操作

### PostgreSQL 基本指令

```bash
# 進入資料庫
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet

# 在容器內執行
\dt                          # 列出所有資料表
\d+ users                    # 查看 users 表結構
\d+ matches                  # 查看 matches 表結構
\l                           # 列出所有資料庫
\du                          # 列出所有角色
\q                           # 退出

# 查看索引
\di

# 查看外鍵
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY';
```

### 資料查詢

```bash
# 查看用戶數量
SELECT COUNT(*) FROM users;

# 查看最近註冊的用戶
SELECT id, email, created_at FROM users
ORDER BY created_at DESC LIMIT 10;

# 查看配對數量
SELECT COUNT(*) FROM matches;

# 查看聊天訊息統計
SELECT
    sender_id,
    COUNT(*) as message_count
FROM messages
GROUP BY sender_id
ORDER BY message_count DESC;

# 查看地理位置資料（PostGIS）
SELECT id, ST_AsText(location) FROM users WHERE location IS NOT NULL;
```

### 備份與還原

```bash
# 備份資料庫
docker exec mergemeet-db pg_dump -U mergemeet mergemeet > backup_$(date +%Y%m%d).sql

# 還原資料庫
docker exec -i mergemeet-db psql -U mergemeet -d mergemeet < backup_20240101.sql

# 備份特定資料表
docker exec mergemeet-db pg_dump -U mergemeet -t users mergemeet > users_backup.sql
```

### Alembic 遷移

```bash
cd backend

# 查看當前版本
alembic current

# 查看遷移歷史
alembic history

# 生成新遷移
alembic revision --autogenerate -m "Add new column to users"

# 執行遷移
alembic upgrade head

# 回退一個版本
alembic downgrade -1

# 回退到特定版本
alembic downgrade <revision_id>

# 查看 SQL（不執行）
alembic upgrade head --sql
```

---

## 後端開發

### 啟動服務

```bash
cd backend

# 開發模式（自動重載）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 生產模式
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 指定 workers（生產環境）
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### 依賴管理

```bash
# 安裝依賴
pip install -r requirements.txt

# 更新依賴
pip install --upgrade -r requirements.txt

# 產生依賴清單
pip freeze > requirements.txt

# 安裝開發依賴
pip install -r requirements-dev.txt
```

### API 測試

```bash
# 健康檢查
curl http://localhost:8000/health

# 測試登入
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}'

# 測試需要認證的端點
curl -X GET http://localhost:8000/api/profile \
  -H "Authorization: Bearer YOUR_TOKEN"

# 測試上傳檔案
curl -X POST http://localhost:8000/api/profile/photos \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/image.jpg"
```

### 程式碼品質

```bash
# 格式化程式碼
black app/

# 檢查程式碼品質
flake8 app/

# 型別檢查
mypy app/

# 自動排序 imports
isort app/
```

---

## 前端開發

### 啟動服務

```bash
cd frontend

# 開發模式
npm run dev

# 建置生產版本
npm run build

# 預覽建置結果
npm run preview
```

### 依賴管理

```bash
# 安裝依賴
npm install

# 安裝新套件
npm install axios
npm install -D @types/node  # 開發依賴

# 更新依賴
npm update

# 移除套件
npm uninstall axios

# 清理並重裝
rm -rf node_modules package-lock.json
npm install
```

### 程式碼品質

```bash
# ESLint 檢查
npm run lint

# 自動修復
npm run lint:fix

# 格式化程式碼（若使用 Prettier）
npm run format

# 型別檢查（若使用 TypeScript）
npm run type-check
```

### 建置與部署

```bash
# 建置
npm run build

# 預覽建置（使用 vite preview）
npm run preview

# 分析打包大小
npm run build -- --report
```

---

## 測試相關

### 後端測試

```bash
cd backend

# 執行所有測試
pytest

# 詳細輸出
pytest -v

# 非常詳細的輸出
pytest -vv

# 顯示 print 輸出
pytest -s

# 測試覆蓋率
pytest --cov=app

# 產生 HTML 覆蓋率報告
pytest --cov=app --cov-report=html

# 顯示缺少覆蓋的程式碼行
pytest --cov=app --cov-report=term-missing

# 測試特定檔案
pytest tests/test_profile.py

# 測試特定類別
pytest tests/test_profile.py::TestProfile

# 測試特定函數
pytest tests/test_profile.py::test_get_profile

# 使用標記運行測試
pytest -m "slow"
pytest -m "not slow"

# 失敗時停止
pytest -x

# 並行測試（需要 pytest-xdist）
pytest -n 4

# 重跑失敗的測試
pytest --lf
```

### 前端測試

```bash
cd frontend

# 執行測試
npm run test

# 監聽模式
npm run test:watch

# 覆蓋率
npm run test:coverage

# UI 模式
npm run test:ui
```

#### 測試概況

- **測試框架**: Vitest + Vue Test Utils
- **測試數量**: 86 個
- **測試文件**:

| 文件 | 測試數量 | 說明 |
|------|----------|------|
| `tests/stores/discovery.spec.js` | 23 | 探索配對 Store（瀏覽、喜歡、跳過、配對） |
| `tests/stores/user.spec.js` | 20 | 用戶認證 Store（註冊、登入、登出、Token） |
| `tests/composables/useWebSocket.spec.js` | 14 | WebSocket Composable（連接狀態、API） |
| `tests/components/chat/MessageBubble.spec.js` | 29 | 訊息氣泡組件（文字、圖片、已讀狀態） |

#### 測試重點

- **Stores**: 狀態管理邏輯、API 呼叫、錯誤處理
- **Composables**: WebSocket 連接管理、訊息處理
- **Components**: UI 渲染、事件處理、Props 驗證

> **注意**: 前端測試著重於核心業務邏輯（Stores），後端有完整的 API 測試覆蓋（287+ 個測試）。

---

## Git 操作

### 基本操作

```bash
# 查看狀態
git status

# 查看變更
git diff
git diff --staged

# 查看日誌
git log
git log --oneline
git log --oneline --graph --all

# 查看特定檔案的歷史
git log -- backend/app/api/profile.py
```

### 分支管理

```bash
# 查看分支
git branch
git branch -a  # 包含遠端分支

# 創建分支
git checkout -b feature/user-profile

# 切換分支
git checkout main
git switch main  # 新語法

# 刪除分支
git branch -d feature/user-profile
git branch -D feature/user-profile  # 強制刪除

# 重命名分支
git branch -m old-name new-name
```

### 提交與推送

```bash
# 添加檔案
git add .
git add backend/app/api/profile.py

# 提交
git commit -m "feat: 新增個人檔案照片上傳功能"

# 修改上一次提交
git commit --amend

# 推送
git push origin feature/user-profile

# 強制推送（小心使用）⚠️
git push -f origin feature/user-profile
```

### 同步與合併

```bash
# 拉取最新變更
git pull origin main

# Fetch + Merge
git fetch origin
git merge origin/main

# Rebase
git rebase main

# 解決衝突後
git add .
git rebase --continue
# 或
git merge --continue
```

### 標籤管理

```bash
# 查看標籤
git tag

# 創建標籤
git tag v1.0.0

# 創建帶註解的標籤
git tag -a v1.0.0 -m "Release version 1.0.0"

# 推送標籤
git push origin v1.0.0
git push origin --tags  # 推送所有標籤
```

---

## 系統診斷

### 檢查端口占用

```bash
# 檢查端口 8000（後端）
lsof -i :8000
netstat -tulnp | grep 8000

# 檢查端口 5173（前端）
lsof -i :5173

# 檢查端口 5432（PostgreSQL）
lsof -i :5432

# 殺死占用端口的進程
kill -9 <PID>
```

### 檢查服務狀態

```bash
# 檢查後端 API
curl -I http://localhost:8000/health

# 檢查前端
curl -I http://localhost:5173

# 檢查資料庫連接
pg_isready -h localhost -p 5432

# 檢查 Redis
redis-cli ping
```

---

## 效能監控

### 後端效能

```bash
# 使用 py-spy 分析效能
py-spy top --pid <uvicorn_pid>

# 記錄效能報告
py-spy record -o profile.svg --pid <uvicorn_pid>

# 查看 SQL 查詢效能
# 在 PostgreSQL 中啟用查詢日誌
```

### 資料庫效能

```sql
-- 查看慢查詢
SELECT * FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- 查看表大小
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 查看索引使用情況
SELECT * FROM pg_stat_user_indexes;
```

---

**提示**: 這些指令可以組合使用，建立自己的工作流程腳本。
