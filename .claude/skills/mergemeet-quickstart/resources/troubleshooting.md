# 詳細故障排除指南

## 目錄

- [後端問題](#後端問題)
- [前端問題](#前端問題)
- [資料庫問題](#資料庫問題)
- [WebSocket 問題](#websocket-問題)
- [Docker 問題](#docker-問題)
- [效能問題](#效能問題)

---

## 後端問題

### 問題 1: 無法連接到資料庫

**錯誤訊息**:
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError)
could not connect to server: Connection refused
```

**診斷步驟**:
```bash
# 1. 檢查 PostgreSQL 是否運行
docker compose ps | grep postgres

# 2. 檢查端口是否開放
lsof -i :5432

# 3. 測試資料庫連接
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet -c "SELECT 1;"

# 4. 查看資料庫日誌
docker compose logs postgres
```

**解決方案**:

**方案 A**: 重啟資料庫
```bash
docker compose restart postgres
# 等待 5-10 秒讓服務啟動
docker compose ps
```

**方案 B**: 檢查環境變數
```bash
# 確認 backend/.env 檔案
cat backend/.env

# 必須包含
DATABASE_URL=postgresql+asyncpg://mergemeet:password@localhost:5432/mergemeet
```

**方案 C**: 完全重建
```bash
docker compose down -v
docker compose up -d
# 等待資料庫啟動
sleep 10
cd backend
alembic upgrade head
```

---

### 問題 2: ImportError 或模組找不到

**錯誤訊息**:
```
ImportError: cannot import name 'User' from 'app.models'
ModuleNotFoundError: No module named 'app.models.user'
```

**診斷步驟**:
```bash
# 1. 檢查 Python 路徑
python -c "import sys; print('\n'.join(sys.path))"

# 2. 檢查檔案是否存在
ls -la backend/app/models/

# 3. 檢查 __init__.py
cat backend/app/models/__init__.py
```

**解決方案**:

**方案 A**: 確認從正確的目錄運行
```bash
# 必須從 backend/ 目錄運行
cd backend
uvicorn app.main:app --reload
```

**方案 B**: 檢查 __init__.py
```python
# backend/app/models/__init__.py 必須包含
from .user import User
from .profile import Profile
# ... 其他模型
```

**方案 C**: 重裝依賴
```bash
cd backend
pip install --upgrade -r requirements.txt
```

---

### 問題 3: Pydantic 驗證錯誤

**錯誤訊息**:
```
pydantic.error_wrappers.ValidationError:
1 validation error for UserCreate
email
  field required (type=value_error.missing)
```

**診斷步驟**:
```bash
# 檢查請求 payload
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"pass123"}' \
  -v
```

**解決方案**:

**方案 A**: 檢查 Schema 定義
```python
# backend/app/schemas/user.py
class UserCreate(BaseModel):
    email: str
    password: str
    # 確認所有必填欄位
```

**方案 B**: 檢查前端請求
```javascript
// 確認所有必填欄位都有傳送
await axios.post('/api/auth/register', {
  email: email,
  password: password,
  // 缺少欄位？
})
```

---

### 問題 4: JWT Token 無效

**錯誤訊息**:
```
HTTPException: Could not validate credentials
401 Unauthorized
```

**診斷步驟**:
```bash
# 1. 檢查 Token 格式
echo $TOKEN | cut -d. -f2 | base64 -d

# 2. 測試 Token
curl -X GET http://localhost:8000/api/profile \
  -H "Authorization: Bearer $TOKEN" \
  -v
```

**解決方案**:

**方案 A**: 重新登入取得新 Token
```bash
# 登入
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}' \
  | jq -r '.access_token'
```

**方案 B**: 檢查 SECRET_KEY
```bash
# backend/.env
SECRET_KEY=your-secret-key-here  # 不可為空
```

**方案 C**: 檢查 Token 過期時間
```python
# backend/app/core/config.py
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 天
```

---

## 前端問題

### 問題 5: CORS 錯誤

**錯誤訊息**:
```
Access to XMLHttpRequest at 'http://localhost:8000/api/profile'
from origin 'http://localhost:5173' has been blocked by CORS policy
```

**診斷步驟**:
```bash
# 1. 檢查後端 CORS 設定
grep -A 10 "CORS" backend/app/core/config.py

# 2. 測試 OPTIONS 請求
curl -X OPTIONS http://localhost:8000/api/profile \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" \
  -v
```

**解決方案**:

**方案 A**: 更新 CORS 設定
```python
# backend/app/core/config.py
class Settings(BaseSettings):
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
```

**方案 B**: 更新 main.py
```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**方案 C**: 重啟後端
```bash
# CORS 設定變更需要重啟
cd backend
uvicorn app.main:app --reload
```

---

### 問題 6: API 請求返回 404

**錯誤訊息**:
```
GET http://localhost:8000/api/profile/ 404 (Not Found)
```

**診斷步驟**:
```bash
# 1. 檢查 Swagger UI
open http://localhost:8000/docs

# 2. 測試正確的 URL（無斜線）
curl http://localhost:8000/api/profile
curl http://localhost:8000/api/profile/  # 404

# 3. 檢查路由定義
grep -rn "@router" backend/app/api/
```

**解決方案**:

⚠️ **最常見原因**: URL 有尾隨斜線

**方案 A**: 移除前端 URL 的斜線
```javascript
// ❌ 錯誤
await axios.get('/api/profile/')

// ✅ 正確
await axios.get('/api/profile')
```

**方案 B**: 檢查後端路由定義
```python
# ❌ 錯誤
@router.get("/")

# ✅ 正確
@router.get("")
```

**方案 C**: 使用 Skill 檢查
```bash
使用 Skill: api-routing-standards
```

---

### 問題 7: Axios 攔截器未生效

**症狀**: Authorization header 未自動添加

**診斷步驟**:
```javascript
// 在 Console 測試
console.log(axios.defaults.headers.common['Authorization'])

// 檢查攔截器
axios.interceptors.request.use(config => {
  console.log('Request config:', config)
  return config
})
```

**解決方案**:

**方案 A**: 確認攔截器設定
```javascript
// frontend/src/api/axios.js
import axios from 'axios'

axios.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)
```

**方案 B**: 使用 Axios 實例
```javascript
// 創建專用實例
const api = axios.create({
  baseURL: 'http://localhost:8000'
})

api.interceptors.request.use(/* ... */)

// 使用實例
await api.get('/api/profile')
```

---

## 資料庫問題

### 問題 8: Alembic 遷移失敗

**錯誤訊息**:
```
alembic.util.exc.CommandError: Can't locate revision identified by 'abc123'
sqlalchemy.exc.ProgrammingError: relation "users" does not exist
```

**診斷步驟**:
```bash
# 1. 檢查遷移版本
alembic current

# 2. 檢查遷移歷史
alembic history

# 3. 檢查資料表
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet -c "\dt"
```

**解決方案**:

**方案 A**: 重置遷移（開發環境）⚠️
```bash
# 刪除所有資料
docker compose down -v
docker compose up -d

# 重新執行遷移
cd backend
alembic upgrade head
```

**方案 B**: 標記為已完成
```bash
# 如果資料表已存在但 alembic 不知道
alembic stamp head
```

**方案 C**: 手動修復
```bash
# 查看 SQL 但不執行
alembic upgrade head --sql > migration.sql

# 手動執行或編輯 SQL
docker exec -i mergemeet-db psql -U mergemeet -d mergemeet < migration.sql
```

---

### 問題 9: 連接池耗盡

**錯誤訊息**:
```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached
```

**診斷步驟**:
```bash
# 1. 檢查活動連接數
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet -c \
  "SELECT COUNT(*) FROM pg_stat_activity;"

# 2. 查看連接詳情
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet -c \
  "SELECT pid, usename, application_name, state FROM pg_stat_activity;"
```

**解決方案**:

**方案 A**: 增加連接池大小
```python
# backend/app/core/database.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,           # 從 5 增加
    max_overflow=40,        # 從 10 增加
    pool_pre_ping=True,
    pool_recycle=3600,      # 1 小時回收連接
)
```

**方案 B**: 確保正確關閉 session
```python
# 使用依賴注入，自動關閉
async def get_profile(db: AsyncSession = Depends(get_db)):
    # session 會自動關閉
    pass

# 或使用 context manager
async with get_db() as db:
    # ...
    pass
```

**方案 C**: 重啟資料庫
```bash
docker compose restart postgres
```

---

### 問題 10: PostGIS 函數找不到

**錯誤訊息**:
```
sqlalchemy.exc.ProgrammingError: function st_distance(geometry, geometry) does not exist
```

**診斷步驟**:
```bash
# 1. 檢查 PostGIS 擴展
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet -c \
  "SELECT * FROM pg_extension WHERE extname = 'postgis';"

# 2. 檢查 PostGIS 版本
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet -c \
  "SELECT PostGIS_version();"
```

**解決方案**:

**方案 A**: 啟用 PostGIS 擴展
```bash
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet -c \
  "CREATE EXTENSION IF NOT EXISTS postgis;"
```

**方案 B**: 重建資料庫
```bash
# docker-compose.yml 確保有初始化腳本
volumes:
  - ./init.sql:/docker-entrypoint-initdb.d/init.sql

# init.sql 內容
CREATE EXTENSION IF NOT EXISTS postgis;
```

---

## WebSocket 問題

### 問題 11: WebSocket 連接失敗

**錯誤訊息**:
```
WebSocket connection to 'ws://localhost:8000/ws' failed
```

**診斷步驟**:
```bash
# 1. 測試 WebSocket 端點
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  http://localhost:8000/ws

# 2. 檢查後端日誌
# 查找 WebSocket 相關訊息

# 3. 在瀏覽器 Console 測試
const ws = new WebSocket('ws://localhost:8000/ws?token=YOUR_TOKEN')
ws.onopen = () => console.log('Connected')
ws.onerror = (error) => console.error('Error:', error)
```

**解決方案**:

**方案 A**: 確認 Token 傳遞
```javascript
// 前端
const token = localStorage.getItem('token')
const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`)
```

**方案 B**: 檢查後端 WebSocket 路由
```python
# backend/app/api/websocket.py
@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    await websocket.accept()
    # ...
```

**方案 C**: 檢查防火牆/代理
```bash
# 確認端口開放
lsof -i :8000
```

---

### 問題 12: WebSocket 頻繁斷線

**症狀**: 連接建立後幾秒就斷開

**解決方案**:

**方案 A**: 實作心跳機制
```javascript
// 前端
let heartbeatInterval

ws.onopen = () => {
  heartbeatInterval = setInterval(() => {
    ws.send(JSON.stringify({ type: 'ping' }))
  }, 30000)  // 每 30 秒
}

ws.onclose = () => {
  clearInterval(heartbeatInterval)
}
```

```python
# 後端
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            if data.get('type') == 'ping':
                await websocket.send_json({'type': 'pong'})
    except WebSocketDisconnect:
        # 清理
        pass
```

**方案 B**: 自動重連
```javascript
function connectWebSocket() {
  const ws = new WebSocket('ws://localhost:8000/ws')

  ws.onclose = () => {
    console.log('Disconnected, reconnecting in 3s...')
    setTimeout(connectWebSocket, 3000)
  }

  return ws
}
```

---

## Docker 問題

### 問題 13: 容器無法啟動

**錯誤訊息**:
```
Error response from daemon: driver failed programming external connectivity
```

**診斷步驟**:
```bash
# 1. 檢查端口占用
lsof -i :5432
lsof -i :6379

# 2. 查看容器日誌
docker compose logs
```

**解決方案**:

**方案 A**: 停止占用端口的服務
```bash
# 找到 PID
lsof -i :5432

# 停止服務
kill -9 <PID>

# 或停止本地 PostgreSQL
sudo systemctl stop postgresql
```

**方案 B**: 更改端口映射
```yaml
# docker-compose.yml
services:
  postgres:
    ports:
      - "5433:5432"  # 使用 5433 而不是 5432
```

---

## 效能問題

### 問題 14: API 回應緩慢

**診斷步驟**:
```bash
# 1. 測試回應時間
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/profile

# curl-format.txt 內容:
time_total: %{time_total}s

# 2. 檢查資料庫查詢
# 在 PostgreSQL 啟用慢查詢日誌

# 3. 使用 py-spy 分析
py-spy top --pid <uvicorn_pid>
```

**解決方案**:

**方案 A**: 添加資料庫索引
```python
# backend/app/models/user.py
class User(Base):
    __tablename__ = "users"

    email = Column(String, unique=True, index=True)  # 添加索引
    created_at = Column(DateTime, index=True)        # 添加索引
```

**方案 B**: 使用查詢優化
```python
# 使用 selectinload 避免 N+1 問題
from sqlalchemy.orm import selectinload

result = await db.execute(
    select(User).options(selectinload(User.profile))
)
```

**方案 C**: 添加快取
```python
from functools import lru_cache

@lru_cache(maxsize=128)
async def get_user_profile(user_id: str):
    # ...
    pass
```

---

**提示**: 如果問題仍未解決，檢查錯誤日誌並使用 Claude Code 的 Skills 系統尋求幫助！
