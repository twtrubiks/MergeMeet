# 故障排除指南

> 本文件只記錄專案特有的問題。通用問題（CORS、JWT、Axios 等）請直接詢問 Claude。

## 目錄

- [PostGIS 問題](#postgis-問題)
- [Alembic 遷移問題](#alembic-遷移問題)
- [連接池問題](#連接池問題)

---

## PostGIS 問題

### 問題：PostGIS 函數找不到

**錯誤訊息**:
```
sqlalchemy.exc.ProgrammingError: function st_distance(geometry, geometry) does not exist
```

**診斷**:
```bash
# 檢查 PostGIS 擴展是否存在
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet -c \
  "SELECT * FROM pg_extension WHERE extname = 'postgis';"

# 檢查 PostGIS 版本
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet -c \
  "SELECT PostGIS_version();"
```

**解決方案**:
```bash
# 啟用 PostGIS 擴展
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet -c \
  "CREATE EXTENSION IF NOT EXISTS postgis;"
```

---

## Alembic 遷移問題

### 問題：找不到遷移版本

**錯誤訊息**:
```
alembic.util.exc.CommandError: Can't locate revision identified by 'abc123'
```

**診斷**:
```bash
cd backend
alembic current   # 當前版本
alembic history   # 遷移歷史
```

**解決方案**:

```bash
# 方案 A：重置（開發環境）
docker compose down -v
docker compose up -d
sleep 10
cd backend && alembic upgrade head

# 方案 B：標記為已完成（資料表已存在）
alembic stamp head
```

### 問題：資料表不存在

**錯誤訊息**:
```
sqlalchemy.exc.ProgrammingError: relation "users" does not exist
```

**解決方案**:
```bash
cd backend
alembic upgrade head
```

---

## 連接池問題

### 問題：連接池耗盡

**錯誤訊息**:
```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached
```

**診斷**:
```bash
# 檢查活動連接數
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet -c \
  "SELECT COUNT(*) FROM pg_stat_activity;"
```

**解決方案**:

```python
# backend/app/core/database.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600,
)
```

或重啟資料庫：
```bash
docker compose restart postgres
```

---

## 其他問題

常見問題已在 [SKILL.md](../SKILL.md) 的故障排除章節說明：
- 資料庫連接問題
- CORS 錯誤
- API 404（尾隨斜線問題）

通用問題請直接詢問 Claude。
