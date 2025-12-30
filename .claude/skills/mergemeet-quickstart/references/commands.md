# 指令參考

> 僅列出專案特有指令。通用 Git/Linux 知識請直接詢問 Claude。

---

## Docker

```bash
# 啟動/停止
docker compose up -d
docker compose stop
docker compose down -v          # 完全清理（含資料卷）⚠️

# 狀態與日誌
docker compose ps
docker compose logs -f postgres

# 進入容器
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet
docker exec -it mergemeet-redis redis-cli
```

---

## 資料庫

### psql 指令

```bash
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet
```

```sql
\dt                    -- 列出資料表
\d+ users              -- 查看表結構
\q                     -- 退出
```

### Alembic 遷移

```bash
cd backend
alembic current                                    # 當前版本
alembic revision --autogenerate -m "描述"          # 生成遷移
alembic upgrade head                               # 執行遷移
alembic downgrade -1                               # 回退一版
```

### 備份

```bash
docker exec mergemeet-db pg_dump -U mergemeet mergemeet > backup.sql
docker exec -i mergemeet-db psql -U mergemeet -d mergemeet < backup.sql
```

---

## 後端

```bash
cd backend

# 啟動
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 依賴
pip install -r requirements.txt

# 程式碼品質
black app/
flake8 app/
mypy app/
isort app/
```

---

## 前端

```bash
cd frontend

# 啟動
npm run dev

# 建置
npm run build
npm run preview

# 依賴
npm install
rm -rf node_modules package-lock.json && npm install  # 清理重裝

# 程式碼品質
npm run lint
npm run lint:fix
```

---

## 測試

### 後端 (pytest)

```bash
cd backend
pytest -v                              # 詳細輸出
pytest -v --cov=app                    # 覆蓋率
pytest --cov=app --cov-report=html     # HTML 報告
pytest tests/test_profile.py           # 特定檔案
pytest -x                              # 失敗即停
pytest --lf                            # 重跑失敗
```

### 前端 (vitest)

```bash
cd frontend
npm run test
npm run test:coverage
```

---

## API 測試

```bash
# 健康檢查
curl http://localhost:8000/health

# 登入
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}'

# 需認證的端點
curl http://localhost:8000/api/profile \
  -H "Authorization: Bearer $TOKEN"
```
